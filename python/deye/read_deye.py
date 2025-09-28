import asyncio
import time
from datetime import datetime
from pysolarmanv5 import PySolarmanV5, V5FrameError
from python.data_store import data_store
import python.db as db

# This is the local IP address of the WiFi stick connected to the Deye (or Solarman) inverter.
# This stick works as a TCP server that listens to port 8899 and transmits data via the Modbus protocol.
# INVERTER_IP = "192.168.31.40"

# This is the serial number of the Wi-Fi stick itself (data logger), not the inverter.
# It is unique for each stick and is usually indicated
# in the local web interface of the Wi-Fi stick (e.g. http://192.168.31.40) or on the sticker of the stick
# LOGGER_SN = 2993578387

# This is the Modbus Slave ID, i.e. the internal identifier of the device in the Modbus network.
# For Deye inverters via WiFi stick, it is always 1 (unless you connect directly via RS485 with a different ID).
# SLAVE_ID = 1

def safe_read_scaled(modbus, register: int, scale: float, name: str = ""):
    try:
        raw = modbus.read_holding_registers(register, 1)[0]
        if raw in (0, 65535): # frequent “no data” marker
            print(f"⚠️ {name} = {raw} (possibly invalid)")
            return None
        return round(raw * scale, 2)
    except Exception as e:
        print(f"❌ Failed to read {name} (reg {register}): {e}")
        return None
        
def to_signed(val):
    return val - 0x10000 if val >= 0x8000 else val

def to_signed_32bit(hi: int, lo: int) -> int:
    value = (hi << 16) + lo
    return value if value < 0x80000000 else value - 0x100000000

async def read_deye_for_device(ip: str, serial_number: int, slave_id: int = 1):
    print(f"📡 Connecting to Deye inverter at {ip}...")
    modbus = PySolarmanV5(ip, serial_number, port=8899, mb_slave_id=slave_id)

    try:
        pv1_power = modbus.read_holding_registers(186, 1)[0]
        pv2_power = modbus.read_holding_registers(187, 1)[0]
        total_pv = pv1_power + pv2_power
        load_power = to_signed(modbus.read_holding_registers(178, 1)[0])


        grid_power = to_signed(modbus.read_holding_registers(172, 1)[0])

        # TEST START
        # Регістр 170: миттєва потужність з/до мережі
        reg_170 = modbus.read_holding_registers(170, 1)[0]
        if reg_170 >= 0x8000:  # робимо signed
            reg_170 -= 0x10000

        print("⚡ Grid Power (170):", reg_170, "Вт")
        if reg_170 > 0:
            print("➡️ Імпорт з мережі:", reg_170, "Вт")
        elif reg_170 < 0:
            print("⬅️ Експорт у мережу:", abs(reg_170), "Вт")
        else:
            print("⏸️ Немає обміну з мережею")
        # Регістр 170: миттєва потужність з/до мережі

        print(f"ONE")
        try:
            reg_618 = modbus.read_holding_registers(618, 1)[0]  # Grid External Total Active Power (S16)
            print(f"TWO")
            reg_622 = modbus.read_holding_registers(622, 1)[0]  # Grid Side A-phase Power (S16)
            print(f"THREE")
            # Читаємо 32-бітне значення (625 і 626)
            regs_625_626 = modbus.read_holding_registers(625, 2)
            reg_625_626 = (regs_625_626[1] << 16) | regs_625_626[0]
            # Робимо його signed (32-біт)
            if reg_625_626 & 0x80000000:
                reg_625_626 -= 0x100000000

            # Робимо signed для 16-бітних регістрів
            if reg_618 >= 0x8000:
                reg_618 -= 0x10000
            if reg_622 >= 0x8000:
                reg_622 -= 0x10000

            print("🔌 Grid External Total Active Power (618):", reg_618, "Вт")
            print("🔌 Grid Side A-phase Power (622):", reg_622, "Вт")
            print("🔌 Grid Side Total Active Power (625+626):", reg_625_626, "Вт")
        except Exception as e:
            print(f"Failed to read 3090: {e}")
        # TEST END
        # НОВИЙ ТЕСТОВИЙ БЛОК: Фокусуємося на 16-бітних регістрах Grid Power
        print(f"--- Modbus Test Registers Start ---")
        try:
            reg_625_raw = modbus.read_holding_registers(625, 1)[0]
            grid_power_625 = to_signed(reg_625_raw)
            print("🔌 Grid Total Active Power (Reg 625, S16):", grid_power_625, "Вт")
        except Exception as e:
            print(f"❌ Failed to read Reg 625 (16-bit): {e}")

        try:
            reg_622_raw = modbus.read_holding_registers(622, 1)[0]
            grid_power_622 = to_signed(reg_622_raw)
            print("🔌 Grid Side A-phase Power (Reg 622, S16):", grid_power_622, "Вт")
        except Exception as e:
            print(f"❌ Failed to read Reg 622 (16-bit): {e}")
                    
        try:
            grid_power_172 = to_signed(modbus.read_holding_registers(172, 1)[0])
            print("🔌 Grid External Total Power (Reg 172, S16):", grid_power_172, "Вт")
        except Exception as e:
            print(f"❌ Failed to read Reg 172 (16-bit): {e}")

        print(f"--- Modbus Test Registers End ---")
        # Оновлюємо змінну grid_power, яку ви використовуєте в data, на найімовірніше коректну
        # Ми використовуємо 172 як стандартний, але якщо 625 покаже результат, ви можете змінити.
        # Встановіть grid_power = grid_power_625, якщо цей регістр буде працювати.
        # Наразі залишаємо 172, як було у вашій початковій логіці перед тестовим блоком.
        # grid_power = grid_power_625 if 'grid_power_625' in locals() and grid_power_625 is not None else grid_power


        bat_power = to_signed(modbus.read_holding_registers(190, 1)[0])
        bat_voltage = modbus.read_holding_registers(183, 1)[0] * 0.01
        bat_soc = modbus.read_holding_registers(184, 1)[0]
        net_balance = total_pv + grid_power - load_power - bat_power

        # Additional data
        pv1_voltage = modbus.read_holding_registers(279, 1)[0] * 0.1
        pv2_voltage = modbus.read_holding_registers(280, 1)[0] * 0.1
        # pv1_voltage = safe_read_scaled(modbus, 279, 0.1, "pv1_voltage")
        # pv2_voltage = safe_read_scaled(modbus, 280, 0.1, "pv2_voltage")
        pv1_current = modbus.read_holding_registers(281, 1)[0] * 0.01
        pv2_current = modbus.read_holding_registers(282, 1)[0] * 0.01
        load_voltage = modbus.read_holding_registers(258, 1)[0] * 0.1
        load_frequency = modbus.read_holding_registers(259, 1)[0] * 0.01
        bat_current = modbus.read_holding_registers(191, 1)[0] * 0.01
        grid_voltage = modbus.read_holding_registers(173, 1)[0] * 0.1
        grid_frequency = modbus.read_holding_registers(174, 1)[0] * 0.01

        # total_generated_kwh = ((modbus.read_holding_registers(5001, 2)[0] << 16) + modbus.read_holding_registers(5001, 2)[1]) / 10
        # total_load_kwh = ((modbus.read_holding_registers(5003, 2)[0] << 16) + modbus.read_holding_registers(5003, 2)[1]) / 10
        # total_bat_charge_kwh = ((modbus.read_holding_registers(5007, 2)[0] << 16) + modbus.read_holding_registers(5007, 2)[1]) / 10
        # total_bat_discharge_kwh = ((modbus.read_holding_registers(5009, 2)[0] << 16) + modbus.read_holding_registers(5009, 2)[1]) / 10
        additional = {
            "pv1_voltage": pv1_voltage,
            "pv2_voltage": pv2_voltage,
            "pv1_current": pv1_current,
            "pv2_current": pv2_current,
            "load_voltage": load_voltage,
            "load_frequency": load_frequency,
            "bat_current": bat_current,
            "grid_voltage": grid_voltage,
            "grid_frequency": grid_frequency,
            # "total_generated_kwh": total_generated_kwh,
            # "total_load_kwh": total_load_kwh,
            # "total_bat_charge_kwh": total_bat_charge_kwh,
            # "total_bat_discharge_kwh": total_bat_discharge_kwh
        }
        print("📊 Additional metrics:")
        for key, value in additional.items():
            print(f"  {key:<28} = {value}")


        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "pv1_power": pv1_power,
            "pv2_power": pv2_power,
            "total_pv": total_pv,
            "load_power": load_power,
            "grid_power": grid_power,
            "battery_power": bat_power,
            "battery_voltage": bat_voltage,
            "battery_soc": bat_soc,
            "net_balance": net_balance
        }

        db.update_deye_device_data(ip, data)

    except V5FrameError as err:
        print(f"❌ Modbus error on {ip}: {err}")
    except Exception as err:
        print(f"❌ General error on {ip}: {err}")
    finally:
        modbus.disconnect()

async def run_deye_loop():
    while True:
        try:
            devices = db.get_all_deye_devices()
            tasks = [
                read_deye_for_device(
                    device["ip"],
                    int(device["serial_number"]),
                    int(device.get("slave_id", 1))
                )
                for device in devices if device.get("device_on", 1)
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ Error in Deye loop: {e}")
        await asyncio.sleep(3)