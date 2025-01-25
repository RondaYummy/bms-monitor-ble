import asyncio
from asyncio import Lock
from datetime import datetime, timezone
from copy import deepcopy

import uvicorn
from bleak import BleakClient, BleakScanner
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Query

from colors import *
import db


ENABLE_LOGS = False # True or False
MIN_FRAME_SIZE = 300
MAX_FRAME_SIZE = 320
SERVICE_UUID = "0000FFE0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000FFE1-0000-1000-8000-00805f9b34fb"
CMD_HEADER = bytes([0xAA, 0x55, 0x90, 0xEB])
CMD_TYPE_DEVICE_INFO = 0x97 # 0x03: Device Info Frame
CMD_TYPE_CELL_INFO = 0x96 # 0x02: Cell Info Frame
CMD_TYPE_SETTINGS = 0x95 # 0x01: Settings

# Data store class
class DeviceDataStore:
    def __init__(self):
        self.device_info = {}
        self.cell_info = {}
        self.last_cell_info_update = {}
        self.response_buffers = {}
        self.lock = Lock()

    async def update_last_cell_info_update(self, device_name):
        async with self.lock:
            self.last_cell_info_update[device_name] = datetime.now(timezone.utc)

    async def get_last_cell_info_update(self, device_name):
        async with self.lock:
            return self.last_cell_info_update.get(device_name, None)
        
    async def append_to_buffer(self, device_name, data):
        async with self.lock:
            if device_name not in self.response_buffers:
                self.response_buffers[device_name] = bytearray()
            self.response_buffers[device_name].extend(data)

    async def get_buffer(self, device_name):
        async with self.lock:
            return self.response_buffers.get(device_name, bytearray())

    async def clear_buffer(self, device_name):
        async with self.lock:
            if device_name in self.response_buffers:
                self.response_buffers[device_name].clear()

    async def update_device_info(self, device_name, info):
        async with self.lock:
            self.device_info[device_name] = info

    async def get_device_info(self, device_name=None):
        async with self.lock:
            if device_name:
                return deepcopy(self.device_info.get(device_name))
            return deepcopy(self.device_info)

    async def update_cell_info(self, device_name, info):
        async with self.lock:
            self.cell_info[device_name] = info

    async def get_cell_info(self):
        async with self.lock:
            return deepcopy(self.cell_info)

# Initialize data store
device_data_store = DeviceDataStore()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/api/device-info")
async def get_device_info():
    data = await device_data_store.get_device_info()
    if not data:
        return JSONResponse(content={"message": "No device info available yet."}, status_code=404)
    return data

@app.get("/api/cell-info")
async def get_cell_info():
    cell_info_data = await device_data_store.get_cell_info()
    if not cell_info_data:
        return JSONResponse(content={"message": "No cell info available yet."}, status_code=404)
    return cell_info_data

@app.get("/api/aggregated-data")
async def get_cell_info(days: int = Query(..., ge=1, description="Number of days to fetch data for")):
    aggregated_data = db.fetch_all_data(days=days)
    if not aggregated_data:
        return JSONResponse(content={"message": "No aggregated data available yet."}, status_code=404)
    return aggregated_data

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ble_main())
    asyncio.create_task(db.process_devices())

def calculate_crc(data):
    return sum(data) & 0xFF

def create_command(command_type):
    frame = bytearray(20)
    frame[:4] = CMD_HEADER
    frame[4] = command_type
    frame[19] = calculate_crc(frame[:19])
    return frame

def log(device_name, message, force=False):
    global ENABLE_LOGS
    if ENABLE_LOGS or force:
        current_time = datetime.now().strftime("%d.%m.%y %H:%M")
        print(f"{BLUE}[{device_name}] {MAGENTA}[{current_time}]{RESET} {message}")

async def parse_device_info(data, device_name, device_address):
    """Parsing Device Info Frame (0x03)."""
    log(device_name, "Parsing Device Info Frame...")

    try:
        log(device_name, f"Raw data: {data.hex()}")
        
        # Checking the header
        if data[:4] != b'\x55\xAA\xEB\x90':
            raise ValueError("Invalid frame header")

        # Extract fields from the frame
        device_info = {
            # "setup_passcode": data[118:134].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            # "passcode": data[97:102].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            # "device_passcode": data[62:78].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "frame_type": data[4],
            "frame_counter": data[5],
            "vendor_id": data[6:22].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "hardware_version": data[22:30].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "software_version": data[30:38].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "device_uptime": int.from_bytes(data[38:42], byteorder='little'),
            "power_on_count": int.from_bytes(data[42:46], byteorder='little'),
            "device_name": data[46:62].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "device_address": device_address,
            "manufacturing_date": data[78:86].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "serial_number": data[86:97].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "user_data": data[102:118].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "connected": True,
        }

        # CRC Validation
        crc_calculated = calculate_crc(data[:-1])
        crc_received = data[-1]
        if crc_calculated != crc_received:
            log(device_name, f"Invalid CRC: {crc_calculated} != {crc_received}")
            return None
        
        # Save device-specific info
        await device_data_store.update_device_info(device_name, device_info)

        # Logging of parsed information
        log(device_name, "Parsed Device Info:")
        for key, value in device_info.items():
            log(device_name, f"{key}: {value}")

        return device_info

    except Exception as e:
        log(device_name, f"Error parsing Device Info Frame: {e}", force=True)
        return None
    
async def parse_setting_info(data, device_name, device_address):
    """Parsing Cell Info Frame (0x01)."""
    log(device_name, "Parsing Setting Info Frame...")  

    try:
        log(device_name, f"Setting Header: {data[:4].hex()}", force=True)

    except Exception as e:
        log(device_name, f"Error parsing Setting Info Frame: {e}", force=True)
        return None

async def parse_cell_info(data, device_name, device_address):
    """Parsing Cell Info Frame (0x02)."""
    log(device_name, "Parsing Cell Info Frame...")

    try:
        # Checking the header
        if data[:4] != b'\x55\xAA\xEB\x90':
            log(device_name, f"Unexpected Header: {data[:4].hex()}", force=True)
            raise ValueError("Invalid frame header")
        log(device_name, f"Data Length: {len(data)}")

        # Extract cell data
        cell_voltages = []
        start_index = 6  # Initial index for cell tension
        num_cells = 32   # Maximum number of cells
        for i in range(num_cells):
            voltage_raw = int.from_bytes(data[start_index:start_index + 2], byteorder='little')
            voltage = voltage_raw * 0.001  # Conversion of volts
            cell_voltages.append(voltage)
            start_index += 2

        # Extract cell resistances
        cell_resistances = []
        start_index = 80
        for i in range(num_cells):
            resistance_raw = int.from_bytes(data[start_index:start_index + 2], byteorder='little')
            resistance = resistance_raw * 0.001  # Conversion of resistance
            cell_resistances.append(resistance)
            start_index += 2

        # Filter only those cells that have a voltage > 0
        filtered_voltages = [v for v in cell_voltages if v > 0]
        filtered_resistances = [v for v in cell_resistances if v > 0]

        # TODO need add 32 to pos, after cell resistance?
        power_tube_temp = int.from_bytes(data[112+32:114+32], byteorder='little', signed=True) * 0.1
        battery_voltage = int.from_bytes(data[118+32:122+32], byteorder='little', signed=True) * 0.001
        battery_power = int.from_bytes(data[122+32:126+32], byteorder='little', signed=True) * 0.001
        charge_current = int.from_bytes(data[126+32:130+32], byteorder='little', signed=True) * 0.001
        temperature_sensor_1 = int.from_bytes(data[130+32:132+32], byteorder='little', signed=True) * 0.1
        temperature_sensor_2 = int.from_bytes(data[132+32:134+32], byteorder='little', signed=True) * 0.1

        state_of_charge = data[141+32]
        remaining_capacity = int.from_bytes(data[142+32:146+32], byteorder='little') * 0.001
        nominal_capacity = int.from_bytes(data[146+32:150+32], byteorder='little') * 0.001
        cycle_count = int.from_bytes(data[150+32:154+32], byteorder='little')
        total_cycle_capacity = int.from_bytes(data[154+32:157+32], byteorder='little') * 0.001
        state_of_health = data[158+32]
        charging_status = data[166+32]
        discharging_status = data[167+32]
        precharging_status = data[168+32]

        temperature_sensor_5 = int.from_bytes(data[222+32:224+32], byteorder='little', signed=True) * 0.1
        temperature_sensor_4 = int.from_bytes(data[224+32:226+32], byteorder='little', signed=True) * 0.1
        temperature_sensor_3 = int.from_bytes(data[226+32:228+32], byteorder='little', signed=True) * 0.1
        emergency_time_countdown = int.from_bytes(data[186+32:187+32], byteorder='little')

        average_voltage = sum(filtered_voltages) / len(filtered_voltages)
        voltage_diff = max(filtered_voltages) - min(filtered_voltages)
        
        cell_info = {
            "charging_status": charging_status,
            "discharging_status": discharging_status,
            "precharging_status": precharging_status,
            "voltage_difference": voltage_diff,
            "average_voltage": average_voltage,
            "cell_voltages": filtered_voltages,
            "cell_resistances": filtered_resistances,
            "power_tube_temperature": power_tube_temp,
            "battery_voltage": battery_voltage,
            "battery_power": battery_power,
            "charge_current": charge_current,
            "temperature_sensor_1": temperature_sensor_1,
            "temperature_sensor_2": temperature_sensor_2,
            "temperature_sensor_3": temperature_sensor_3,
            "temperature_sensor_4": temperature_sensor_4,
            "temperature_sensor_5": temperature_sensor_5,
            "state_of_charge": state_of_charge,
            "remaining_capacity": remaining_capacity,
            "nominal_capacity": nominal_capacity,
            "cycle_count": cycle_count,
            "total_cycle_capacity": total_cycle_capacity,
            "state_of_health": state_of_health,
            "emergency_time_countdown": emergency_time_countdown,
        }

        # CRC Validation
        crc_calculated = calculate_crc(data[:-1])
        crc_received = data[-1]
        if crc_calculated != crc_received:
            log(device_name, f"Invalid CRC: {crc_calculated} != {crc_received}")
            return None
        
        await device_data_store.update_cell_info(device_name, cell_info)

        if await are_all_allowed_devices_connected_and_have_data():
            db.update_aggregated_data(device_name=device_name, device_address=device_address, current=charge_current, power=battery_power)

        log(device_name, "Parsed Cell Info:")
        for key, value in cell_info.items():
            if key == "cell_voltages":
                for idx, voltage in enumerate(value, start=1):
                    log(device_name, f"Cell {idx}: {voltage:.3f} V")
            else:
                log(device_name, f"{key}: {value}")

        return cell_info

    except Exception as e:
        log(device_name, f"Error parsing Cell Info Frame: {e}", force=True)
        return None

async def notification_handler(device, data, device_name, device_address):
    if data[:4] == b'\x55\xAA\xEB\x90':  # The beginning of a new frame
        await device_data_store.clear_buffer(device_name)  # Очистити буфер
    await device_data_store.append_to_buffer(device_name, data)  # Додати нові дані

    buffer = await device_data_store.get_buffer(device_name)
    if MIN_FRAME_SIZE <= len(buffer) <= MAX_FRAME_SIZE:
        log(device_name, f"Full frame received: {buffer.hex()}")

        # Checking the CRC
        calculated_crc = calculate_crc(buffer[:-1])
        received_crc = buffer[-1]
        if calculated_crc != received_crc:
            log(device_name, f"Invalid CRC: {calculated_crc} != {received_crc}")
            return

        # Determining the frame type
        frame_type = buffer[4]
        if frame_type == 0x03:
            await parse_device_info(buffer, device_name, device_address)
        elif frame_type == 0x02:
            await device_data_store.update_last_cell_info_update(device_name)
            await parse_cell_info(buffer, device_name, device_address)
        elif frame_type == 0x01:
            await parse_setting_info(buffer, device_name, device_address)
        else:
            log(device_name, f"Unknown frame type {frame_type}: {buffer}", force=True)
            # Якщо невідомий тип очищую буфер, бо така помилка буде весь час падати
            await device_data_store.clear_buffer(device_name)

async def connect_and_run(device):
    while True:  # Цикл для перепідключення
        try:
            device_info_data = await device_data_store.get_device_info(device.name)
            if not device_info_data:
                device_info_data = {
                    "device_name": device.name,
                    "device_address": device.address,
                    "connected": False
                }
            await device_data_store.update_device_info(device.name, device_info_data)

            async with BleakClient(device.address) as client:
                device_info_data["connected"] = True
                await device_data_store.update_device_info(device.name, device_info_data)
                log(device.name, f"Connected and notification started", force=True)

                def handle_notification(sender, data):
                    asyncio.create_task(notification_handler(device, data, device.name, device.address))

                await client.start_notify(CHARACTERISTIC_UUID, handle_notification)

                while True:  # Постійне опитування
                # Перевіряємо, чи пристрій ще підключений
                    device_info_data = await device_data_store.get_device_info(device.name)
                    if not device_info_data.get("connected", False):
                        log(device.name, "Device has been disconnected. Stopping polling.", force=True)
                        break

                    device_info_data = await device_data_store.get_device_info(device.name)
                    if not device_info_data or "frame_type" not in device_info_data:
                        # Якщо інформація про пристрій ще не збережена, надсилаємо команду
                        device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
                        await client.write_gatt_char(CHARACTERISTIC_UUID, device_info_command)
                        log(device.name, f"Device Info command sent: {device_info_command.hex()}")
                        await asyncio.sleep(1)

                    # Перевіряємо, чи потрібно надсилати cell_info_command
                    last_update = await device_data_store.get_last_cell_info_update(device.name)
                    if not last_update or (datetime.now(timezone.utc) - last_update).total_seconds() > 30:
                        cell_info_command = create_command(CMD_TYPE_CELL_INFO)
                        await client.write_gatt_char(CHARACTERISTIC_UUID, cell_info_command)
                        log(device.name, f"Cell Info command sent: {cell_info_command.hex()}")

                    await asyncio.sleep(10)
        except Exception as e:
            log(device.name, f"Error: {str(e)}", force=True)
        finally:
            device_info_data["connected"] = False
            await client.disconnect()
            await device_data_store.update_device_info(device.name, device_info_data)
            log(device.name, "Disconnected, retrying in 5 seconds...", force=True)
            await asyncio.sleep(5)

async def ble_main():
    allowed_devices = load_allowed_devices()

    while True:
        devices = await BleakScanner.discover()
        if not devices:
            print("No BLE devices found.")
            await asyncio.sleep(10)
            continue

        tasks = []
        for device in devices:
            # Перевіряємо, чи пристрій дозволений
            if device.address.lower() in allowed_devices:
                # Перевіряємо, чи пристрій уже підключений
                device_info = await device_data_store.get_device_info(device.name)
                if device_info and device_info.get("connected", False):
                    log(device.name, f"Device {device.name} is already connected, skipping.")
                    continue  # Пропускаємо, якщо пристрій вже підключений

                log(device.name, f"Connecting to allowed device: {device.address}", force=True)
                tasks.append(asyncio.create_task(connect_and_run(device)))
                await asyncio.sleep(10)
        # Чекаємо завершення всіх задач (теоретично вони працюватимуть нескінченно)
        if tasks:
            await asyncio.gather(*tasks)
        else:
            await asyncio.sleep(10)

async def are_all_allowed_devices_connected_and_have_data() -> bool:
    """
    Перевіряє, чи всі пристрої зі списку allowed_devices підключені
    та чи є для кожного дані в cell_info.
    """
    allowed_devices = {addr.lower() for addr in load_allowed_devices()}
    connected_devices = await device_data_store.get_device_info()
    connected_addresses = {
        device_info.get("device_address", "").lower()
        for device_info in connected_devices.values()
        if device_info.get("connected", False)
    }

    # Перевіряємо, чи всі дозволені пристрої підключені
    if not allowed_devices.issubset(connected_addresses):
        log("CHECK DEVICES", "All allowed devices are not connected", force=True)
        return False

    # Перевіряємо, чи є дані cell_info для кожного підключеного пристрою
    cell_info = await device_data_store.get_cell_info()
    for device_address in allowed_devices:
        if device_address not in cell_info:
            log("CHECK DEVICES", f"Device [{device_address}] have no data.", force=True)
            return False

    return True

def start_services():
    db.create_table()
    uvicorn.run(app, host="0.0.0.0", port=8000)

def load_allowed_devices(filename="allowed_devices.txt"):
    try:
        with open(filename, 'r') as file:
            allowed_devices = {line.strip().lower() for line in file if line.strip()}
        return allowed_devices
    except FileNotFoundError:
        print(f"Warning: {filename} not found. All devices will be blocked.")
        return set()

if __name__ == "__main__":
    start_services()
