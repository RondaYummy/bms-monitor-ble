import asyncio
import time
from typing import Dict, Any

from python.db import (
    get_all_deye_devices,
    get_all_tapo_devices,
    update_tapo_device_by_ip,
)
from python.tapo.tapo_service import get_tapo_device

# Parameters
THRESHOLD_W = 3900                # threshold in watts
MIN_TOGGLE_INTERVAL_S = 30        # minimum interval between switching of one device
POLL_INTERVAL_S = 2               # inverter polling

# In memory: which devices we turned off and metadata
# disabled_devices[ip] = {"off_since": timestamp, "power_w": <estimated W>, "last_action": timestamp}
disabled_devices: Dict[str, Dict[str, Any]] = {}

# To avoid running multiple shutdowns/startups simultaneously
manage_lock = asyncio.Lock()

def _power_w_from_row(device_row):
    """
    A small helper function: we convert device_row[‘power_watt’] to watts (W).
    In your system, power_watt can sometimes be in kW (for example, 0.1) or in W.
    The rule is simple: if <=20, we consider it to be kW and multiply by 1000.
    Otherwise, we assume it is already in W.
    """
    try:
        pw = device_row.get("power_watt", 0) or 0
        pw = float(pw)
    except Exception:
        return 0.0
    if abs(pw) <= 20:  # quick heuristic test: if <=20 — probably kW
        return pw * 1000.0
    return pw

async def _disable_tapo_device(device_row):
    ip = device_row["ip"]
    email = device_row.get("email")
    password = device_row.get("password")
    now = time.time()

    # change the state in memory first to avoid a race condition
    est_power_w = _power_w_from_row(device_row)

    # perform a blocking operation in the pool
    loop = asyncio.get_running_loop()
    try:
        tapo = get_tapo_device(ip, email, password)
        await loop.run_in_executor(None, tapo.turn_off)
        # Let's update the database: set device_on = 0
        update_tapo_device_by_ip(ip, {"device_on": 0})
        disabled_devices[ip] = {"off_since": now, "power_w": est_power_w, "last_action": now}
        print(f"🔴 Disabled Tapo device {ip} (est {est_power_w:.0f} W) at {time.ctime(now)}")
        return True
    except Exception as e:
        print(f"❌ Failed to disable Tapo {ip}: {e}")
        return False

async def _enable_tapo_device(ip, email, password):
    loop = asyncio.get_running_loop()
    now = time.time()
    try:
        tapo = get_tapo_device(ip, email, password)
        await loop.run_in_executor(None, tapo.turn_on)
        update_tapo_device_by_ip(ip, {"device_on": 1})
        # Let's clear the record of the disabled device
        if ip in disabled_devices:
            disabled_devices.pop(ip, None)
        print(f"🟢 Enabled Tapo device {ip} at {time.ctime(now)}")
        return True
    except Exception as e:
        print(f"❌ Failed to enable Tapo {ip}: {e}")
        return False

async def manage_tapo_power():
    """
    Main loop: every POLL_INTERVAL_S we check load_power.
    """
    global disabled_devices
    print("⚙️ Tapo power manager started")
    while True:
        try:
            async with manage_lock:
                # get all inverters => sum load_power
                # Calls to db are synchronous, so we call them directly (this is a blocking operation).
                deye_devices = get_all_deye_devices() or []
                total_load = 0.0
                for d in deye_devices:
                    try:
                        lp = d.get("load_power") if d else 0
                        if lp is None:
                            lp = 0
                        total_load += float(lp)
                    except Exception:
                        pass

                print(f"🔎 Current total load (sum deye.load_power): {total_load:.1f} W")

                if total_load > THRESHOLD_W:
                    tapo_rows = get_all_tapo_devices() or []
                    candidates = [r for r in tapo_rows if r.get("device_on")]
                    if candidates:
                        # сортуємо по estimated споживанню (descending) — вимикаємо найпотужніший для швидкої економії
                        candidates.sort(key=lambda r: _power_w_from_row(r), reverse=True)
                        for cand in candidates:
                            ip = cand["ip"]
                            now = time.time()
                            # do not switch if we have recently shared (throttle)
                            last = disabled_devices.get(ip, {}).get("last_action", 0)
                            if now - last < MIN_TOGGLE_INTERVAL_S:
                                continue
                            # turn off the first suitable one
                            success = await _disable_tapo_device(cand)
                            if success:
                                # after turning it off, we will exit the loop — let's see the result in the next poll
                                break
                    else:
                        print("ℹ️ No enabled Tapo devices available to disable.")
                else:
                    # Навантаження нижче порогу — можемо спробувати увімкнути раніше вимкнені
                    if disabled_devices:
                        tapo_rows = get_all_tapo_devices() or []
                        tapo_map = {r["ip"]: r for r in tapo_rows}
                        # Розрахуємо поточний запас потужності
                        headroom = THRESHOLD_W - total_load
                        # Спробуємо включати пристрої по порядку (FIFO або за збереженим порядком)
                        # Для надійності сортуємо по часу вимкнення (ті, що довше вимкнені — вмикаємо раніше)
                        items = sorted(disabled_devices.items(), key=lambda kv: kv[1]["off_since"])
                        for ip, meta in items:
                            now = time.time()
                            last_action = meta.get("last_action", 0)
                            if now - last_action < MIN_TOGGLE_INTERVAL_S:
                                continue  # занадто рано
                            est_power = meta.get("power_w", 0.0)
                            # Якщо естімейтовано в кВт то він вже конвертований у W функцією _power_w_from_row
                            # Якщо пристрій не знайдено в БД — пропускаємо
                            row = tapo_map.get(ip)
                            if not row:
                                # очистимо, бо пристрій може бути видалений
                                disabled_devices.pop(ip, None)
                                continue
                            # Якщо пристрій споживає більше, ніж headroom — не вмикаємо зараз
                            if est_power <= headroom + 50:  # +50W запас
                                # Вмикаємо
                                success = await _enable_tapo_device(ip, row.get("email"), row.get("password"))
                                if success:
                                    # зменшуємо headroom
                                    headroom -= est_power
                                    # якщо headroom ще дозволяє — продовжимо включати
                                else:
                                    disabled_devices[ip]["last_action"] = now
                            else:
                                print(f"⏳ Not enough headroom to enable {ip} (needs {est_power:.0f} W, headroom {headroom:.0f} W)")
                                # Продовжимо перевірку наступних (можливо є слабкіші)
        except Exception as e:
            print(f"❌ Error in manage_tapo_power loop: {e}")
        finally:
            await asyncio.sleep(POLL_INTERVAL_S)
