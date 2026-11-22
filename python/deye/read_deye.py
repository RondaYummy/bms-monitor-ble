import asyncio
import time
from datetime import datetime, timezone

from pysolarmanv5 import PySolarmanV5, V5FrameError

import python.db as db
from python.energy import FLUSH_INTERVAL_SECONDS, accumulator as energy_accumulator

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

POLL_INTERVAL_SECONDS = 3
SOCKET_TIMEOUT_SECONDS = 10

# Registers are read in a few contiguous blocks instead of ~30 single-register requests:
# every request is a full TCP round trip to the Wi-Fi stick.
BLOCK_STATS = (70, 17)       # 70..86   daily/total battery, grid and load counters
BLOCK_PV_TOTALS = (96, 13)   # 96..108  total PV (u32 @96) and daily PV (@108)
BLOCK_REALTIME = (169, 23)   # 169..191 grid/load/battery/PV instant values

# One persistent connection per logger (re-created after any error).
_clients: dict = {}


def to_signed(val):
    return val - 0x10000 if val >= 0x8000 else val


def to_signed_32bit(hi: int, lo: int) -> int:
    value = (hi << 16) + lo
    return value if value < 0x80000000 else value - 0x100000000


def _get_client(ip: str, serial_number: int, slave_id: int) -> PySolarmanV5:
    key = (ip, serial_number, slave_id)
    client = _clients.get(key)
    if client is None:
        client = PySolarmanV5(ip, serial_number, port=8899, mb_slave_id=slave_id,
                              socket_timeout=SOCKET_TIMEOUT_SECONDS)
        _clients[key] = client
    return client


def _drop_client(ip: str, serial_number: int, slave_id: int):
    client = _clients.pop((ip, serial_number, slave_id), None)
    if client is not None:
        try:
            client.disconnect()
        except Exception:
            pass


def _read_block(modbus, block):
    start, count = block
    values = modbus.read_holding_registers(start, count)
    return lambda register: values[register - start]


def _read_deye_blocking(ip: str, serial_number: int, slave_id: int) -> dict:
    """Synchronous Modbus I/O — always executed in a worker thread."""
    modbus = _get_client(ip, serial_number, slave_id)

    rt = _read_block(modbus, BLOCK_REALTIME)
    st = _read_block(modbus, BLOCK_STATS)
    pv = _read_block(modbus, BLOCK_PV_TOTALS)

    pv1_power = rt(186)
    pv2_power = rt(187)
    total_pv = pv1_power + pv2_power
    load_power = to_signed(rt(178))
    grid_power = to_signed(rt(169))  # >0 import from grid, <0 export
    bat_power = to_signed(rt(190))
    bat_voltage = rt(183) * 0.01
    bat_soc = rt(184)
    net_balance = total_pv + grid_power - load_power - bat_power

    data = {
        "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "pv1_power": pv1_power,
        "pv2_power": pv2_power,
        "total_pv": total_pv,
        "load_power": load_power,
        "grid_power": grid_power,
        "battery_power": bat_power,
        "battery_voltage": bat_voltage,
        "battery_soc": bat_soc,
        "net_balance": net_balance,

        "stat_daily_pv": pv(108) * 0.1,
        "stat_total_pv": ((pv(97) << 16) + pv(96)) * 0.1,
        "stat_daily_bat_discharge": st(71) * 0.1,
        "stat_daily_grid_in": st(76) * 0.1,
        "stat_daily_grid_out": st(77) * 0.1,
        "stat_total_grid_out": ((st(82) << 16) | st(81)) * 0.1,
        "stat_total_load": ((st(86) << 16) | st(85)) * 0.1,

        "daily_bat_charge": st(70) * 0.1,
        "total_bat_charge": ((st(73) << 16) + st(72)) * 0.1,
        "total_bat_discharge": ((st(75) << 16) | st(74)) * 0.1,
        "grid_in": ((st(80) << 16) | st(78)) * 0.1,
        "daily_load": st(84) * 0.1,
    }
    # register * 0.1 / 0.01 -> 12.299999999999999 etc.: keep two decimals
    return {k: round(v, 2) if isinstance(v, float) else v for k, v in data.items()}


async def read_deye_for_device(ip: str, serial_number: int, slave_id: int = 1):
    try:
        # Never run blocking socket I/O on the event loop: it would freeze BLE handling and the API.
        data = await asyncio.to_thread(_read_deye_blocking, ip, serial_number, slave_id)
        await asyncio.to_thread(db.update_deye_device_data, ip, data)
        energy_accumulator.record(ip, data)  # hourly kWh history for the economics report
    except V5FrameError as err:
        print(f"❌ Modbus error on {ip}: {err}")
        _drop_client(ip, serial_number, slave_id)
    except Exception as err:
        print(f"❌ General error on {ip}: {err}")
        _drop_client(ip, serial_number, slave_id)


async def run_deye_loop():
    last_flush = time.monotonic()
    while True:
        try:
            devices = db.get_all_deye_devices()
            tasks = [
                read_deye_for_device(
                    device["ip"],
                    int(device["serial_number"]),
                    int(device.get("slave_id") or 1)
                )
                for device in devices if device.get("device_on", 1)
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            print(f"❌ Error in Deye loop: {e}")
        if time.monotonic() - last_flush >= FLUSH_INTERVAL_SECONDS:
            last_flush = time.monotonic()
            try:
                await asyncio.to_thread(energy_accumulator.flush)
            except Exception as e:
                print(f"❌ Energy flush failed: {e}")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
