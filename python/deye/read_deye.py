import asyncio
import time
from datetime import datetime
from pysolarmanv5 import PySolarmanV5, V5FrameError
from python.data_store import data_store

# This is the local IP address of the WiFi stick connected to the Deye (or Solarman) inverter.
# This stick works as a TCP server that listens to port 8899 and transmits data via the Modbus protocol.
INVERTER_IP = "192.168.31.40"

# This is the serial number of the Wi-Fi stick itself (data logger), not the inverter.
# It is unique for each stick and is usually indicated
# in the local web interface of the Wi-Fi stick (e.g. http://192.168.31.40) or on the sticker of the stick
LOGGER_SN = 2993578387

# This is the Modbus Slave ID, i.e. the internal identifier of the device in the Modbus network.
# For Deye inverters via WiFi stick, it is always 1 (unless you connect directly via RS485 with a different ID).
SLAVE_ID = 1

def to_signed(val):
    return val - 0x10000 if val >= 0x8000 else val

async def read_deye():
    modbus = PySolarmanV5(INVERTER_IP, LOGGER_SN, port=8899, mb_slave_id=SLAVE_ID)
    print("📡 Connection Deye inverter established, reading data...")
    try:
        pv1_power = modbus.read_holding_registers(186, 1)[0]
        pv2_power = modbus.read_holding_registers(187, 1)[0]
        total_pv = pv1_power + pv2_power
        time.sleep(0.1)
        load_power = to_signed(modbus.read_holding_registers(178, 1)[0])
        time.sleep(0.1)
        bat_power = to_signed(modbus.read_holding_registers(190, 1)[0])
        bat_voltage = modbus.read_holding_registers(183, 1)[0] * 0.01
        bat_soc = modbus.read_holding_registers(184, 1)[0]
        time.sleep(0.1)
        grid_power = to_signed(modbus.read_holding_registers(173, 1)[0])
        # grid_power = to_signed(modbus.read_holding_registers(175, 1)[0])
        time.sleep(0.1)
        net_balance = total_pv + grid_power - load_power - bat_power
        
        # Для тестування, в якому байті яка інформація.
        for addr in range(170, 190, 2):
            try:
                regs = modbus.read_holding_registers(addr, 2)
                val32 = (regs[0] << 16) + regs[1]
                signed_val = val32 if val32 < 2**31 else val32 - 2**32
                print(f"Reg {addr}-{addr+1}: raw={regs}, uint32={val32}, signed32={signed_val}")
            except Exception as e:
                print(f"❌ Error reading {addr}: {e}")

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
        await data_store.update_deye_data(data)

    except V5FrameError as err:
        print(f"❌ Modbus error: {err}")
    except Exception as err:
        print(f"❌ Another error: {err}")
    finally:
        modbus.disconnect()

async def run_deye_loop():
    while True:
        await read_deye()
        await asyncio.sleep(5)