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


        # TEST START
        print(f"ONE")
        grid_power = to_signed(modbus.read_holding_registers(172, 1)[0])
        print(f"TWO")

        try:
            power_3090_raw = modbus.read_holding_registers(3090, 1)[0]
            power_3090 = to_signed(power_3090_raw) 
            power_3090_scaled = power_3090 * 0.1 
            print(f"Grid Power (Reg 3090): {round(power_3090_scaled, 2)} W")
        except Exception as e:
            print(f"Failed to read 3090: {e}")

        try:
            registers_5003 = modbus.read_holding_registers(5003, 2) 
            total_grid_import_kwh = to_signed_32bit(registers_5003[0], registers_5003[1]) / 10
            print(f"Total Grid Import Energy (Reg 5003/5004): {total_grid_import_kwh} kWh")
        except Exception as e:
            print(f"Failed to read 5003/5004: {e}")

        try:
            # 3090 (HI) та 3091 (LO) можуть утворювати 32-бітне значення
            registers_3090 = modbus.read_holding_registers(3090, 2)
            power_3090_32bit = to_signed_32bit(registers_3090[0], registers_3090[1])
            power_3090_32bit_scaled = power_3090_32bit * 0.1 # Або 0.01, спробуйте обидва
            print(f"Grid Power (Reg 3090/3091 - 32-bit, 0.1): {round(power_3090_32bit_scaled, 2)} W")
        except Exception as e:
            print(f"Failed to read 3090/3091: {e}")

        # Перевірка 3093 (як альтернатива)
        try:
            power_3093_raw = modbus.read_holding_registers(3093, 1)[0]
            power_3093 = to_signed(power_3093_raw)
            power_3093_scaled = power_3093 * 0.1
            print(f"Grid Power (Reg 3093 - 0.1): {round(power_3093_scaled, 2)} W")
        except Exception as e:
            print(f"Failed to read 3093: {e}")

        # Grid Power (регістр 508)
        try:
            grid_power_508_raw = modbus.read_holding_registers(508, 1)[0]
            grid_power_508 = to_signed(grid_power_508_raw)
            print(f"Grid Power (Reg 508): {grid_power_508} W") # Масштаб зазвичай 1.0
        except Exception as e:
            print(f"Failed to read 508: {e}")

        # Grid Power (регістр 511)
        try:
            grid_power_511_raw = modbus.read_holding_registers(511, 1)[0]
            grid_power_511 = to_signed(grid_power_511_raw)
            print(f"Grid Power (Reg 511): {grid_power_511} W") # Масштаб зазвичай 1.0
        except Exception as e:
            print(f"Failed to read 511: {e}")

        # Grid Power (регістр 4102)
        try:
            grid_power_4102_raw = modbus.read_holding_registers(4102, 1)[0]
            grid_power_4102 = to_signed(grid_power_4102_raw)
            print(f"Grid Power (Reg 4102): {grid_power_4102} W") # Масштаб зазвичай 1.0
        except Exception as e:
            print(f"Failed to read 4102: {e}")

        print(f"THREE")
        grid_power_raw = modbus.read_holding_registers(172, 1)[0]
        grid_power_signed = to_signed(grid_power_raw)
        print(f"Reg 172: RAW={grid_power_raw}, SIGNED={grid_power_signed}")
        # Поточний Grid Power (регістр 172)
        grid_power_172 = to_signed(modbus.read_holding_registers(172, 1)[0])
        # Альтернативний Grid Power (регістр 170)
        grid_power_170 = to_signed(modbus.read_holding_registers(170, 1)[0])
        print(f"Grid Power (Reg 172): {grid_power_172} W")
        print(f"Grid Power (Reg 170): {grid_power_170} W")
        # TEST END


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