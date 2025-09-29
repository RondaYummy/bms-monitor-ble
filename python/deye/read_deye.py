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

def test_registers(modbus):
    topics = {
        "186": "dc/pv1/power",
        "187": "dc/pv2/power",
        "109": "dc/pv1/voltage",
        "111": "dc/pv2/voltage",
        "110": "dc/pv1/current",
        "112": "dc/pv2/current",
        "108": "day_energy",
        "96": "total_energy",
        "166": "micro_inverter_power",
        "70": "battery/daily_charge",
        "71": "battery/daily_discharge",
        "72": "battery/total_charge",
        "74": "battery/total_discharge",
        "189": "battery/status",
        "190": "battery/power",
        "183": "battery/voltage",
        "184": "battery/soc",
        "191": "battery/current",
        "182": "battery/temperature",
        "169": "ac/total_grid_power",
        "175": "ac/total_power",
        "150": "ac/l1/voltage",
        "151": "ac/l2/voltage",
        "164": "ac/l1/current",
        "165": "ac/l2/current",
        "173": "ac/l1/power",
        "174": "ac/l2/power",
        "76": "ac/daily_energy_bought",
        "77": "ac/daily_energy_sold",
        "78": "ac/total_energy_bought",
        "81": "ac/total_energy_sold",
        "192": "ac/frequency",
        "90": "radiator_temp",
        "91": "ac/temperature",
        "170": "ac/l1/ct/external",
        "167": "ac/l1/ct/internal",
        "171": "ac/l2/ct/external",
        "168": "ac/l2/ct/internal",
        "248": "timeofuse/enabled",
        "250": "timeofuse/time/1",
        "251": "timeofuse/time/2",
        "252": "timeofuse/time/3",
        "253": "timeofuse/time/4",
        "254": "timeofuse/time/5",
        "255": "timeofuse/time/6",
        "256": "timeofuse/power/1",
        "257": "timeofuse/power/2",
        "258": "timeofuse/power/3",
        "259": "timeofuse/power/4",
        "260": "timeofuse/power/5",
        "261": "timeofuse/power/6",
        "262": "timeofuse/voltage/1",
        "263": "timeofuse/voltage/2",
        "264": "timeofuse/voltage/3",
        "265": "timeofuse/voltage/4",
        "266": "timeofuse/voltage/5",
        "267": "timeofuse/voltage/6",
        "268": "timeofuse/soc/1",
        "269": "timeofuse/soc/2",
        "270": "timeofuse/soc/3",
        "271": "timeofuse/soc/4",
        "272": "timeofuse/soc/5",
        "273": "timeofuse/soc/6",
        "274": "timeofuse/enabled/1",
        "275": "timeofuse/enabled/2",
        "276": "timeofuse/enabled/3",
        "277": "timeofuse/enabled/4",
        "278": "timeofuse/enabled/5",
        "279": "timeofuse/enabled/6",
        "312": "bms/1/charging_voltage",
        "313": "bms/1/discharge_voltage",
        "314": "bms/1/charge_current_limit",
        "315": "bms/1/discharge_current_limit",
        "316": "bms/1/soc",
        "317": "bms/1/voltage",
        "318": "bms/1/current",
        "319": "bms/1/temp"
    }
    print("=== 🔍 Start register scan ===")
    for reg, name in topics.items():
        try:
            val = modbus.read_holding_registers(reg, 1)[0]
            # робимо signed для int16
            if val >= 0x8000:
                val -= 0x10000
            print(f"Reg {reg:3d} ({name}): {val}")
        except Exception as e:
            print(f"❌ Failed to read Reg {reg} ({name}): {e}")
    print("=== ✅ End register scan ===")

async def read_deye_for_device(ip: str, serial_number: int, slave_id: int = 1):
    print(f"📡 Connecting to Deye inverter at {ip}...")
    modbus = PySolarmanV5(ip, serial_number, port=8899, mb_slave_id=slave_id)

    try:
        pv1_power = modbus.read_holding_registers(186, 1)[0]
        pv2_power = modbus.read_holding_registers(187, 1)[0]
        total_pv = pv1_power + pv2_power
        load_power = to_signed(modbus.read_holding_registers(178, 1)[0])

        # grid_power = to_signed(modbus.read_holding_registers(172, 1)[0])
        # --- Grid Power (миттєва почтужність) ---
        try:
            reg_169_raw = modbus.read_holding_registers(169, 1)[0]
            grid_power = reg_169_raw - 0x10000 if reg_169_raw >= 0x8000 else reg_169_raw
            print(f"⚡ Grid Power (Reg 169): {grid_power} W")
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