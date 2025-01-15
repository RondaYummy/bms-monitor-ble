import asyncio
from bleak import BleakClient, BleakScanner
from colors import *
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/api/device-info")
def get_device_info():
    print(f"[/api/device-info] {device_info_data}")
    if not device_info_data:
        return JSONResponse(content={"message": "No device info available yet."}, status_code=404)
    return device_info_data

# If the frame starts with 55aaeb9003 it's a device info frame. 55aaeb9002 is a cell info frame.

MIN_FRAME_SIZE = 300
MAX_FRAME_SIZE = 320

SERVICE_UUID = "0000FFE0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000FFE1-0000-1000-8000-00805f9b34fb"

CMD_HEADER = bytes([0xAA, 0x55, 0x90, 0xEB])
CMD_TYPE_DEVICE_INFO = 0x97 # 0x03: Device Info Frame
CMD_TYPE_CELL_INFO = 0x96 # 0x02: Cell Info Frame
# CMD_TYPE_SETTINGS = 0x95 # 0x01: Settings

response_buffer = bytearray()
device_info_data = {}

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ble_main())

def calculate_crc(data):
    return sum(data) & 0xFF

def create_command(command_type):
    frame = bytearray(20)
    frame[:4] = CMD_HEADER
    frame[4] = command_type
    frame[19] = calculate_crc(frame[:19])
    return frame

def log(device_name, message):
    print(f"{BLUE}[{device_name}]{RESET} {message}")

def parse_device_info(data, device_name):
    global device_info_data
    """Parsing Device Info Frame (0x03)."""
    log(device_name, "Parsing Device Info Frame...")

    try:
        log(device_name, f"Raw data: {data.hex()}")
        
        # Checking the header
        if data[:4] != b'\x55\xAA\xEB\x90':
            raise ValueError("Invalid frame header")

        # Extract fields from the frame
        device_info = {
            "frame_type": data[4],
            "frame_counter": data[5],
            "vendor_id": data[6:22].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "hardware_version": data[22:30].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "software_version": data[30:38].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "device_uptime": int.from_bytes(data[38:42], byteorder='little'),
            "power_on_count": int.from_bytes(data[42:46], byteorder='little'),
            "device_name": data[46:62].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "device_passcode": data[62:78].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "manufacturing_date": data[78:86].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "serial_number": data[86:97].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "passcode": data[97:102].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "user_data": data[102:118].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
            "setup_passcode": data[118:134].split(b'\x00', 1)[0].decode('utf-8', errors='ignore'),
        }

        # CRC Validation
        crc_calculated = calculate_crc(data[:-1])
        crc_received = data[-1]
        if crc_calculated != crc_received:
            log(device_name, f"Invalid CRC: {crc_calculated} != {crc_received}")
            return None
        log(device_name, "CRC Valid")

        # Save device-specific info
        device_info_data[device_name] = device_info

        # Logging of parsed information
        log(device_name, "Parsed Device Info:")
        for key, value in device_info.items():
            log(device_name, f"{key}: {value}")

        return device_info

    except Exception as e:
        log(device_name, f"Error parsing Device Info Frame: {e}")
        return None

def parse_device_data(data: bytearray):
    start_index = 5  # The initial index after which useful information begins
    
    # Read each segment sequentially to 0x00
    segments = []
    while start_index < len(data):
        try:
            end_index = data.index(0x00, start_index)  # Find the following 0x00
            segment = data[start_index:end_index].decode('utf-8', errors='ignore')  # Decode
            segments.append(segment)
            start_index = end_index + 1  # Move to the next byte after 0x00
        except ValueError:
            break  # If 0x00 is no longer present, exit the loop
    
    if len(segments) < 5:
        raise ValueError("Insufficient data for parsing")

    device_info = {
        "device_name": segments[0],
        "firmware_version": segments[1],
        "serial_number": segments[2],
        "hardware_version": segments[3],
        "other_info": segments[4:]  # Everything else is additional data
    }
    
    return device_info

def parse_cell_info(data, device_name):
    """Parsing Cell Info Frame (0x02)."""
    log(device_name, "Parsing Cell Info Frame...")

    try:
        # Checking the header
        if data[:4] != b'\x55\xAA\xEB\x90':
            raise ValueError("Invalid frame header")

        # Extract cell data
        cell_voltages = []
        start_index = 6  # Initial index for cell tension
        num_cells = 32   # Maximum number of cells
        for i in range(num_cells):
            voltage_raw = int.from_bytes(data[start_index:start_index + 2], byteorder='little')
            voltage = voltage_raw * 0.001  # Conversion of volts
            cell_voltages.append(voltage)
            start_index += 2

        power_tube_temp = int.from_bytes(data[112:114], byteorder='little', signed=True) * 0.1
        battery_voltage = int.from_bytes(data[118:122], byteorder='little') * 0.001
        battery_power = int.from_bytes(data[122:126], byteorder='little') * 0.001
        charge_current = int.from_bytes(data[126:130], byteorder='little', signed=True) * 0.001
        temperature_sensor_1 = int.from_bytes(data[130:132], byteorder='little', signed=True) * 0.1
        temperature_sensor_2 = int.from_bytes(data[132:134], byteorder='little', signed=True) * 0.1
        state_of_charge = data[141]
        remaining_capacity = int.from_bytes(data[142:146], byteorder='little') * 0.001
        nominal_capacity = int.from_bytes(data[146:150], byteorder='little') * 0.001
        cycle_count = int.from_bytes(data[150:154], byteorder='little')
        state_of_health = data[158]

        cell_info = {
            "cell_voltages": cell_voltages,
            "power_tube_temperature": power_tube_temp,
            "battery_voltage": battery_voltage,
            "battery_power": battery_power,
            "charge_current": charge_current,
            "temperature_sensor_1": temperature_sensor_1,
            "temperature_sensor_2": temperature_sensor_2,
            "state_of_charge": state_of_charge,
            "remaining_capacity": remaining_capacity,
            "nominal_capacity": nominal_capacity,
            "cycle_count": cycle_count,
            "state_of_health": state_of_health,
        }

        # CRC Validation
        crc_calculated = calculate_crc(data[:-1])
        crc_received = data[-1]
        if crc_calculated != crc_received:
            log(device_name, f"Invalid CRC: {crc_calculated} != {crc_received}")
            return None
        log(device_name, "CRC Valid")

        log(device_name, "Parsed Cell Info:")
        for key, value in cell_info.items():
            if key == "cell_voltages":
                for idx, voltage in enumerate(value, start=1):
                    log(device_name, f"Cell {idx}: {voltage:.3f} V")
            else:
                log(device_name, f"{key}: {value}")

        return cell_info

    except Exception as e:
        log(device_name, f"Error parsing Cell Info Frame: {e}")
        return None

async def notification_handler(sender, data, device_name):
    global response_buffer

    if data[:4] == b'\x55\xAA\xEB\x90':  # The beginning of a new frame
        response_buffer = bytearray()   # Clear the buffer
    response_buffer.extend(data)       # Adding data to a buffer

    if MIN_FRAME_SIZE <= len(response_buffer) <= MAX_FRAME_SIZE:
        log(device_name, f"Full frame received: {response_buffer.hex()}")

        # Checking the CRC
        calculated_crc = calculate_crc(response_buffer[:-1])
        received_crc = response_buffer[-1]
        if calculated_crc != received_crc:
            log(device_name, f"Invalid CRC: {calculated_crc} != {received_crc}")
            return

        # Determining the frame type
        frame_type = response_buffer[4]
        if frame_type == 0x03:
            parse_device_info(response_buffer, device_name)
        elif frame_type == 0x02:
            parse_cell_info(response_buffer, device_name)
        else:
            log(device_name, f"Unknown frame type: {frame_type}")

async def connect_and_run(device):
    try:
        async with BleakClient(device.address) as client:
            def handle_notification(sender, data):
                asyncio.create_task(notification_handler(sender, data, device.name))

            await client.start_notify(CHARACTERISTIC_UUID, handle_notification)
            log(device.name, f"Connected and notification started")

            # Send commands for Device Info and Cell Info
            device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
            cell_info_command = create_command(CMD_TYPE_CELL_INFO)

            await client.write_gatt_char(CHARACTERISTIC_UUID, device_info_command)
            log(device.name, f"Device Info command sent: {device_info_command.hex()}")

            await asyncio.sleep(1)  # Expectations between teams

            await client.write_gatt_char(CHARACTERISTIC_UUID, cell_info_command)
            log(device.name, f"Cell Info command sent: {cell_info_command.hex()}")

            await asyncio.sleep(30)  # Time to receive data
            await client.stop_notify(CHARACTERISTIC_UUID)
            log(device.name, "Notification stopped")
    except Exception as e:
        log(device.name, f"Error: {str(e)}")

async def ble_main():
    devices = await BleakScanner.discover()
    if not devices:
        print("No BLE devices found.")
        return

    for device in devices:
        await connect_and_run(device)

def start_services():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_services()
