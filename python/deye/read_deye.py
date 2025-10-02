import asyncio
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

# --- КОНСТАНТИ ВАШОЇ БАТАРЕЇ ---
# Максимальна напруга (50В = 100% SOC)
BAT_VOLTAGE_MAX = 50.0 
# Мінімальна напруга (43В = 0% SOC)
BAT_VOLTAGE_MIN = 43.0 
# ---------------------------------

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

def read_u32(modbus, start_reg):
    regs = modbus.read_holding_registers(start_reg, 2)
    return (regs[1] << 16) + regs[0]

async def read_deye_for_device(ip: str, serial_number: int, slave_id: int = 1):
    print(f"📡 Connecting to Deye inverter at {ip}...")
    modbus = PySolarmanV5(ip, serial_number, port=8899, mb_slave_id=slave_id)

    try:
        pv1_power = modbus.read_holding_registers(186, 1)[0]
        pv2_power = modbus.read_holding_registers(187, 1)[0]
        total_pv = pv1_power + pv2_power
        load_power = to_signed(modbus.read_holding_registers(178, 1)[0])

        # --- Grid Power (instant power) ---
        try:
            reg_169_raw = modbus.read_holding_registers(169, 1)[0]
            grid_power = reg_169_raw - 0x10000 if reg_169_raw >= 0x8000 else reg_169_raw
            if grid_power > 0:
                print(f"➡️ Імпорт з мережі: {grid_power} W")
            elif grid_power < 0:
                print(f"⬅️ Експорт у мережу: {abs(grid_power)} W")
            else:
                print("⏸️ Немає обміну з мережею")
        except Exception as e:
            print(f"❌ Failed to read Grid Power (Reg 169): {e}")

        bat_power = to_signed(modbus.read_holding_registers(190, 1)[0])
        bat_voltage = modbus.read_holding_registers(183, 1)[0] * 0.01
        bat_soc = modbus.read_holding_registers(184, 1)[0]
        net_balance = total_pv + grid_power - load_power - bat_power
        # --- Grid Power (instant power) ---

        # --- Accumulative (daily/total) ---
        stat_daily_pv = modbus.read_holding_registers(108, 1)[0] * 0.1
        print(f"✅[ PV ] Виробництво соянчної енергії в день: {stat_daily_pv:.2f} кВт·год")

        raw_total_pv = read_u32(modbus, 0x0060)
        stat_total_pv = raw_total_pv * 0.1
        print(f"✅[ PV ] [ Статистика роботи ] Загальне викробництво: {stat_total_pv:.2f} кВт·год")

        stat_daily_bat_discharge = modbus.read_holding_registers(71, 1)[0] * 0.1
        print(f"✅[Battery] Щоденне споживання ( Від мережі ): {stat_daily_bat_discharge:.2f} кВт·год")

        stat_daily_grid_in = modbus.read_holding_registers(76, 1)[0] * 0.1
        print(f"✅[ Grid ] Кількість придбаної електроенергії в день: {stat_daily_grid_in:.2f} кВт·год")

        stat_daily_grid_out = modbus.read_holding_registers(77, 1)[0] * 0.1
        print(f"✅[ Grid ] Кількість проданої електроенергії в день: {stat_daily_grid_out:.2f} кВт·год")

        total_grid_out_raw = modbus.read_holding_registers(81, 2)
        stat_total_grid_out = (total_grid_out_raw[1] << 16 | total_grid_out_raw[0]) * 0.1
        print(f"✅[ Grid ] [ Статистика роботи ] Загальний вивід до мережі: {stat_total_grid_out:.2f} кВт·год")

        total_load_raw = modbus.read_holding_registers(85, 2)
        stat_total_load = (total_load_raw[1] << 16 | total_load_raw[0]) * 0.1
        print(f"✅[ PV + Grid ] Загальне споживання: {stat_total_load:.2f} кВт·год")

        daily_bat_charge = modbus.read_holding_registers(70, 1)[0] * 0.1
        print(f"[Battery] Денний заряд: {daily_bat_charge:.2f} кВт·год")

        raw_bat_charge = read_u32(modbus, 0x0048)
        total_bat_charge = raw_bat_charge * 0.1
        print(f"[Battery] Загальний заряд: {total_bat_charge:.2f} кВт·год")

        total_bat_discharge_raw = modbus.read_holding_registers(74, 2)
        total_bat_discharge = (total_bat_discharge_raw[1] << 16 | total_bat_discharge_raw[0]) * 0.1 # <<< ВИПРАВЛЕНО
        print(f"[Battery] Загальний розряд: {total_bat_discharge:.2f} кВт·год")

        # raw_grid_in = read_u32(modbus, 0x004E)
        # grid_in = raw_grid_in * 0.1
        # print(f"[ Grid ] Загальна енергія з мережі: {grid_in:.2f} кВт·год")
        grid_in_regs = modbus.read_holding_registers(0x004E, 3) 
        reg_lo = grid_in_regs[0] # 0x004E (Молодше слово, або LO)
        reg_hi = grid_in_regs[2] # 0x0050 (Старше слово, або HI)
        # Об'єднуємо у порядку LO-HI (Старше слово << 16 | Молодше слово)
        raw_grid_in = (reg_hi << 16) | reg_lo 
        grid_in = raw_grid_in * 0.1
        print(f"✅[ Grid ] Загальна енергія з мережі: {grid_in:.2f} кВт·год")

        daily_load = modbus.read_holding_registers(84, 1)[0] * 0.1
        print(f"[ Grid ] Денне споживання навантаження: {daily_load:.2f} кВт·год")
        # print(f"[ Load ] Денне споживання енергії: {daily_load:.2f} + {daily_pv:.2f} = {daily_load + daily_pv:.2f} кВт·год")

        # 1. Читаємо регістри, які вказані у вашій мапі (0x004E та 0x0050)
        raw_grid_in_regs = modbus.read_holding_registers(0x004E, 3) # Читаємо 3 регістри: 4E, 4F, 50
        # 2. Беремо потрібні регістри: 0x004E (LO) та 0x0050 (HI).
        # Зверніть увагу, що 0x004F ігнорується.
        reg_lo = raw_grid_in_regs[0] # 0x004E
        reg_hi = raw_grid_in_regs[2] # 0x0050
        # 3. Об'єднуємо у порядку LO-HI (якщо читання з мережі виявиться HI-LO, змініть порядок)
        raw_grid_in = (reg_hi << 16) | reg_lo 
        grid_in = raw_grid_in * 0.1
        print(f"[ Grid ] Загальна енергія з мережі: {grid_in:.2f} кВт·год") 
        # --- Accumulative (daily/total) ---

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
            "stat_daily_pv": stat_daily_pv,
            "stat_total_pv": stat_total_pv,
            "stat_daily_bat_discharge": stat_daily_bat_discharge,
            "stat_daily_grid_in": stat_daily_grid_in,
            "stat_daily_grid_out": stat_daily_grid_out,
            "stat_total_grid_out": stat_total_grid_out,
            "stat_total_load": stat_total_load,
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
            "net_balance": net_balance,
            
            "stat_daily_pv": stat_daily_pv,
            "stat_total_pv": stat_total_pv,
            "stat_daily_bat_discharge": stat_daily_bat_discharge,
            "stat_daily_grid_in": stat_daily_grid_in,
            "stat_daily_grid_out": stat_daily_grid_out,
            "stat_total_grid_out": stat_total_grid_out,
            "stat_total_load": stat_total_load,
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