import asyncio
from datetime import datetime

import python.db as db
from python.tapo.tapo_service import TapoDevice
from python.push_notifications import send_push_notification


async def auto_power_manager_loop():
    NO_GENERATION_THRESHOLD_SECONDS = 60 * 5
    last_ok_time = datetime.now()

    while True:
        try:
            config = db.get_config()

            # 🚫 авто-логіка вимкнена
            if not config.get("auto_power_management_enabled"):
                await asyncio.sleep(10)
                continue

            deye_devices = db.get_all_deye_devices()
            tapo_devices = db.get_all_tapo_devices()

            if not deye_devices:
                await asyncio.sleep(10)
                continue

            deye = deye_devices[0]

            total_pv = deye.get("total_pv", 0)
            load_power = deye.get("load_power", 0)

            # ☀️ є генерація → скидаємо таймер
            if total_pv >= load_power:
                last_ok_time = datetime.now()
                await asyncio.sleep(10)
                continue

            diff = (datetime.now() - last_ok_time).total_seconds()

            # ⏳ ще не час вимикати
            if diff < NO_GENERATION_THRESHOLD_SECONDS:
                await asyncio.sleep(10)
                continue

            # 🔥 немає генерації достатньо довго → вимикаємо пристрої по одному
            for device in sorted(tapo_devices, key=lambda x: x.get("ip", "")):

                # 🔄 перед кожним девайсом перевіряємо актуальний стан генерації
                deye = db.get_all_deye_devices()[0]
                total_pv = deye.get("total_pv", 0)
                load_power = deye.get("load_power", 0)

                # ☀️ генерація повернулась → зупиняємо вимикання
                if total_pv >= load_power:
                    break

                if not device.get("auto_power_off_enabled"):
                    continue

                if not device.get("device_on"):
                    continue

                try:
                    tapo = TapoDevice(
                        device["ip"],
                        device["email"],
                        device["password"]
                    )

                    # 🔌 вимикаємо пристрій (sync → thread, щоб не блокувати loop)
                    await asyncio.to_thread(tapo.turn_off)

                    # 🔍 пробуємо отримати метадані (не критично якщо впаде)
                    name = device.get("name")
                    info = {}

                    try:
                        status = await asyncio.to_thread(tapo.get_status)
                        name = await asyncio.to_thread(tapo.get_name) or name
                        info = status.get("info", {}) if status else {}
                    except Exception:
                        pass

                    # 💾 оновлюємо БД ТІЛЬКИ після успішного вимкнення
                    db.update_tapo_device_by_ip(device["ip"], {
                        "device_on": False,
                        "model": info.get("model"),
                        "fw_ver": info.get("fw_ver"),
                        "hw_ver": info.get("hw_ver"),
                        "device_id": info.get("device_id"),
                        **({"name": name} if name else {})
                    })

                    await send_push_notification(
                        "⚡ Авто-вимкнення",
                        f"{name or device['ip']} вимкнено через нестачу генерації"
                    )

                    await asyncio.sleep(2)

                except Exception as e:
                    print(f"❌ Failed to turn off {device['ip']}: {e}")

            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ Auto power manager error: {e}")
            await asyncio.sleep(10)