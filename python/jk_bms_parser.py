from python.data_store import data_store
from python.colors import *
import python.battery_alerts as alerts
import python.db as db
from main import are_all_allowed_devices_connected_and_have_data

def calculate_crc(data):
    return sum(data) & 0xFF

def log(device_name, message, force=False):
    from datetime import datetime
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
        await data_store.update_device_info(device_name, device_info)

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
        log(device_name, f"Setting Header: {data[:5].hex()}", force=True)

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
            "device_address": device_address.lower(),
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
        
        await data_store.update_cell_info(device_name, cell_info)
        await alerts.evaluate_alerts(device_address=device_address, device_name=device_name, cell_info=cell_info)

        if await are_all_allowed_devices_connected_and_have_data():
            db.update_aggregated_data(device_name=device_name, device_address=device_address, current=charge_current, power=battery_power)

        log(device_name, "Parsed Cell Info.")
        return cell_info

    except Exception as e:
        log(device_name, f"Error parsing Cell Info Frame: {e}", force=True)
        return None
