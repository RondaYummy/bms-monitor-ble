from PyP100 import PyP110
from python.db import update_tapo_device_by_ip, get_all_tapo_devices
import asyncio

# IP = "192.168.31.110"
# EMAIL = "basrers199600@gmail.com"
# PASSWORD = "121314Qq"

# def tapo_sync():
#     try:
#         plug = PyP110.P110(IP, EMAIL, PASSWORD)
#         print(f"{plug.getDeviceInfo()}")
#         print(f"{plug.getDeviceName()}")
#         plug.turnOn()
#     except Exception as e:
#         print("❌ Помилка:", e)

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
                "on": False,
                "error": str(e)
            }

    def turn_on(self):
        self.plug.turnOn()

    def turn_off(self):
        self.plug.turnOff()

async def check_and_update_device_status_async(device_row):
    loop = asyncio.get_event_loop()
    def blocking_check():
        tapo = TapoDevice(device_row["ip"], device_row["email"], device_row["password"])
        status = tapo.get_status()
        name = tapo.get_name()
        # оновлюємо тільки поле device_on, name
        update_tapo_device_by_ip(device_row["ip"], {
            "device_on": status["on"],
            "name": name
        })
        print(f"✅ {device_row['ip']} — {'ON' if status['on'] else 'OFF'}")
    await loop.run_in_executor(None, blocking_check)

async def check_all_tapo_devices():
    devices = get_all_tapo_devices()
    semaphore = asyncio.Semaphore(5)  # ліміт паралельних перевірок
    async def limited(dev):
        async with semaphore:
            await check_and_update_device_status_async(dev)

    await asyncio.gather(*(limited(d) for d in devices))