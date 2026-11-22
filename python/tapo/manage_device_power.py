import asyncio
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Path
import json

from python.db import (
    get_all_deye_devices,
    get_all_tapo_devices,
    update_tapo_device_by_ip,
)
from python.auth.verify_token import verify_token
from python.tapo.tapo_service import get_tapo_device
from python.push_notifications import send_push_notification

router = APIRouter(prefix="/power", tags=["Power managment system"])

# Parameters
THRESHOLD_W = 7400                # threshold in watts ( 7400 )
MIN_TOGGLE_INTERVAL_S = 60        # minimum interval between switching of one device
POLL_INTERVAL_S = 5               # inverter polling

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
        # print(f"🔴 Disabled Tapo device {ip} (est {est_power_w:.0f} W) at {time.ctime(now)}")
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
        # print(f"🟢 Enabled Tapo device {ip} at {time.ctime(now)}")
        message = f"🚨 Прилад який ми вимкнули для вирівнення навантаження увімкнено знову."
        asyncio.create_task(send_push_notification("🔌 Навантаження впало", message))
        return True
    except json.decoder.JSONDecodeError as e:
      if ip in disabled_devices:
          disabled_devices.pop(ip, None)
      return True
    except Exception as e:
        # print(f"Помилка типу: {type(e)}")
        # print(f"Помилка в деталях: {e}")
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


                if total_load > THRESHOLD_W:
                    load_to_shed = total_load - THRESHOLD_W
                    message = f"🚨 Навантаження ({total_load:.0f} W) перевищує поріг ({THRESHOLD_W:.0f} W). Скидаємо навантаження!"
                    asyncio.create_task(send_push_notification("⚠️ Увага: Перевантаження", message))

                    tapo_rows = get_all_tapo_devices() or []
                    candidates = [r for r in tapo_rows if r.get("device_on")]
                    if candidates:
                        devices_turned_off_count = 0
                        # sort by estimated consumption (descending) — turn off the most powerful ones for quick savings
                        candidates.sort(key=lambda r: _power_w_from_row(r), reverse=True)
                        for cand in candidates:
                            ip = cand["ip"]
                            now = time.time()
                            # do not switch if we have recently shared (throttle)
                            last = disabled_devices.get(ip, {}).get("last_action", 0)
                            if now - last < MIN_TOGGLE_INTERVAL_S:
                                continue

                            est_power_w = _power_w_from_row(cand)

                            # turn off the first suitable one
                            success = await _disable_tapo_device(cand)
                            if success:
                                devices_turned_off_count += 1
                                # after turning it off, we will exit the loop — let's see the result in the next poll
                                load_to_shed -= est_power_w 
                                # print(f"📉 Скинуто {est_power_w:.0f} W. Залишок для скидання: {load_to_shed:.0f} W.")
                                
                                if load_to_shed <= 0:
                                    # print(f"✅ Цілі досягнуто. Вимкнено {devices_turned_off_count} пристроїв. Зупиняємо вимкнення.")
                                    message = f"🚨 Навантаження вирівняно до позначки ({total_load:.0f} W) шляхом вимкнення {devices_turned_off_count} прилад/ів."
                                    asyncio.create_task(send_push_notification("🔌 Навантаження вирівняно", message))
                                    break # Exit the shutdown cycle if the desired threshold has been reached
                    else:
                        print("ℹ️ No enabled Tapo devices available to disable.")
                else:
                    # Load below threshold — we can try to turn on previously turned off
                    if disabled_devices:
                        tapo_rows = get_all_tapo_devices() or []
                        tapo_map = {r["ip"]: r for r in tapo_rows}
                        headroom = THRESHOLD_W - total_load
                        # Let's try to turn on the devices in order (FIFO or in the saved order)
                        # For reliability, we sort by shutdown time (those that have been shut down longer are turned on earlier).
                        items = sorted(disabled_devices.items(), key=lambda kv: kv[1]["off_since"])

                        for ip, meta in items:
                            now = time.time()
                            last_action = meta.get("last_action", 0)
                            if now - last_action < MIN_TOGGLE_INTERVAL_S:
                                continue
                            est_power = meta.get("power_w", 0.0)
                            row = tapo_map.get(ip)
                            if not row:
                                disabled_devices.pop(ip, None)
                                continue
                            if est_power <= headroom + 50:  # +50W reserve
                                success = await _enable_tapo_device(ip, row.get("email"), row.get("password"))
                                if success:
                                    headroom -= est_power
                                else:
                                    disabled_devices[ip]["last_action"] = now
                            else:
                                print(f"⏳ Not enough headroom to enable {ip} (needs {est_power:.0f} W, headroom {headroom:.0f} W)")
        except Exception as e:
            print(f"❌ Error in manage_tapo_power loop: {e}")
        finally:
            await asyncio.sleep(POLL_INTERVAL_S)

@router.get("/system")
def add_tapo_device_api():
    try:
        disabled_devices_map = disabled_devices.copy()
        devices_list = []
        now = time.time()
        
        for ip, meta in disabled_devices_map.items():
            duration_s = now - meta.get('off_since', now)
            
            device_info = {
                "ip": ip,
                "off_since": meta.get('off_since'), # Timestamp when it was turned off
                "power_w": meta.get('power_w'),     # Expected power (W)
                "duration_s": duration_s,           # Duration of shutdown in seconds
                "last_action": meta.get('last_action'),
            }
            devices_list.append(device_info)
        
        response = {
            "devices": devices_list,
            "threshold": THRESHOLD_W,
            "MIN_TOGGLE_INTERVAL_S": MIN_TOGGLE_INTERVAL_S,
            "POLL_INTERVAL_S": POLL_INTERVAL_S,
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving power manager status: {str(e)}")

@router.delete("/system/{ip}", dependencies=[Depends(verify_token)])
def remove_disabled_tapo_device_api(
    ip: str = Path(..., description="IP-адреса пристрою Tapo для видалення з disabled_devices")
):
    global disabled_devices
    if ip in disabled_devices:
        del disabled_devices[ip]
        return {"status": "success", "message": f"Пристрій {ip} видалено з disabled_devices."}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Пристрій з IP {ip} не знайдено у списку disabled_devices."
        )