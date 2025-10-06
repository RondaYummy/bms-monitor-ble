import asyncio
import json

from PyP100 import PyP110

from python.db import get_all_tapo_devices, update_tapo_device_by_ip

# List of models that support energy monitoring
SUPPORTED_ENERGY_MONITORING_MODELS = {"P110", "P110M"}

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