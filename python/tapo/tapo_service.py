import asyncio
import time

from typing import Dict, Any
from PyP100 import PyP110

from python.db import get_all_tapo_devices, update_tapo_device_by_ip, get_tapo_device_by_ip
from python.push_notifications import send_push_notification

# List of models that support energy monitoring
SUPPORTED_ENERGY_MONITORING_MODELS = {"P110", "P110M"}

scheduled_off_tasks: Dict[str, Dict[str, Any]] = {}
scheduled_tasks_lock = asyncio.Lock()

class TapoDevice:
    def __init__(self, ip: str, email: str, password: str):
        self.ip = ip
        self.email = email
        self.password = password
        self.plug = PyP110.P110(ip, email, password)

    def get_info(self):
        return self.plug.getDeviceInfo()

    def get_name(self):
        return self.plug.getDeviceName()

    def getEnergyUsage(self):
        return self.plug.getEnergyUsage()

    def get_status(self) -> dict:
        try:
            info = self.plug.getDeviceInfo()
            relay_state = info.get("device_on", False)

            return {
                "device_on": relay_state,
                "info": info
            }
        except Exception as e:
            print(f"❌ Error getting info from {self.ip}: {e}")
            return {
                "device_on": False,
                "error": str(e)
            }

    def turn_on(self):
        self.plug.turnOn()

    def turn_off(self):
        self.plug.turnOff()

TAPO_CACHE: dict[str, TapoDevice] = {}

def get_tapo_device(ip: str, email: str, password: str) -> TapoDevice:
    if ip not in TAPO_CACHE:
        TAPO_CACHE[ip] = TapoDevice(ip, email, password)
    return TAPO_CACHE[ip]

async def check_and_update_device_status_async(device_row):
    loop = asyncio.get_event_loop()

    def blocking_check():
        try:
            tapo = get_tapo_device(device_row["ip"], device_row["email"], device_row["password"])
            status = tapo.get_status()
            name = tapo.get_name()
            info = status.get("info", {})
            model = info.get("model")

            update_data = {
                "device_on": status.get("device_on", False),
                "name": name,
                "model": model,
                "fw_ver": info.get("fw_ver"),
                "hw_ver": info.get("hw_ver"),
                "device_id": info.get("device_id"),
            }

            # If the device supports energy monitoring, try to read
            if model in SUPPORTED_ENERGY_MONITORING_MODELS:
                try:
                    energy_data = tapo.getEnergyUsage()
                    # Responce example:
                    # {
                    #     'today_runtime': 206, - Час роботи пристрою сьогодні у хвилинах.
                    #     'month_runtime': 206, - Загальний час роботи за поточний місяць у хвилинах.
                    #     'today_energy': 721, - Витрачена енергія сьогодні, у ват-годинах (Wh).
                    #     'month_energy': 721, - Витрачена енергія за місяць, у ват-годинах (Wh).
                    #     'local_time': '2025-05-29 22:03:21', - Поточна дата і час за локальним часом пристрою.
                    #     'electricity_charge': [0, 0, 0], - Масив з 3-х тарифів на електроенергію, якщо задані.
                    #     'current_power': 0 - Поточне споживання електроенергії в вата́х (mW) (реальне).
                    # }

                    current_power = energy_data.get("current_power", 0)
                    update_data["power_watt"] = current_power  / 1000
                except Exception as energy_err:
                    print(f"⚠️ Could not read power usage from {device_row['ip']}: {energy_err}")

            update_tapo_device_by_ip(device_row["ip"], update_data)
        except Exception as e:
            print(f"❌ Failed to update device {device_row['ip']}: {e}")
    await loop.run_in_executor(None, blocking_check)

async def check_all_tapo_devices():
    devices = get_all_tapo_devices()
    semaphore = asyncio.Semaphore(5)  # limit of parallel checks
    async def limited(dev):
        async with semaphore:
            await check_and_update_device_status_async(dev)

    await asyncio.gather(*(limited(d) for d in devices))

async def schedule_turn_off_worker(ip: str):
    async with scheduled_tasks_lock:
        entry = scheduled_off_tasks.get(ip)
        if not entry:
            return
        execute_at_monotonic = entry.get("execute_at_monotonic")
        if execute_at_monotonic is None:
            execute_at = entry.get("execute_at", time.time())
            execute_at_monotonic = time.monotonic() + max(0, execute_at - time.time())
            entry["execute_at_monotonic"] = execute_at_monotonic

    print(f"[TIMER] scheduled for {ip}: execute_at_monotonic={execute_at_monotonic}, now_monotonic={time.monotonic()}")
    try:
        while True:
            remaining = execute_at_monotonic - time.monotonic()
            if remaining <= 0:
                break
            # спимо максимально 1 секунду або менше, якщо залишилось менше
            sleep_for = remaining if remaining < 1.0 else 1.0
            await asyncio.sleep(sleep_for)

        async with scheduled_tasks_lock:
            if ip not in scheduled_off_tasks:
                print(f"[TIMER] {ip} entry removed before execution (cancelled).")
                return

        device = get_tapo_device_by_ip(ip)
        if not device:
            async with scheduled_tasks_lock:
                scheduled_off_tasks.pop(ip, None)
            print(f"[TIMER] Device {ip} not in DB, removed timer.")
            return

        # email = device.get("email")
        # password = device.get("password")
        print(f"[TIMER] executing turn_off for {ip} at {time.time()} (monotonic {time.monotonic()})")
        # loop = asyncio.get_running_loop()
        try:
            # tapo = get_tapo_device(ip, email, password)
            # await loop.run_in_executor(None, tapo.turn_off)v
            tapo = TapoDevice(ip, device["email"], device["password"])
            tapo.turn_off()
            update_tapo_device_by_ip(ip, {"device_on": 0})

            msg = f"🔴 Пристрій {ip} автоматично вимкнений за таймером."
            asyncio.create_task(send_push_notification("🔌 Пристрій вимкнуто", msg))
            print(f"[TIMER] turn_off for {ip} finished.")
        except Exception as e:
            print(f"❌ Error while executing scheduled turn off for {ip}: {e}")
        finally:
            async with scheduled_tasks_lock:
                scheduled_off_tasks.pop(ip, None)

    except asyncio.CancelledError:
        async with scheduled_tasks_lock:
            scheduled_off_tasks.pop(ip, None)
        # print(f"[TIMER] cancelled for {ip}")
        raise
    except Exception as e:
        async with scheduled_tasks_lock:
            scheduled_off_tasks.pop(ip, None)
        print(f"❌ Unexpected error in scheduler worker for {ip}: {e}")
        return