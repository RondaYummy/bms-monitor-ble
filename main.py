import asyncio
from bleak import BleakClient, BleakScanner
from colors import *

# If the frame starts with 55aaeb9003 it's a device info frame. 55aaeb9002 is a cell info frame.

MIN_FRAME_SIZE = 300
MAX_FRAME_SIZE = 320

SERVICE_UUID = "0000FFE0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000FFE1-0000-1000-8000-00805f9b34fb"

CMD_HEADER = bytes([0xAA, 0x55, 0x90, 0xEB])
CMD_TYPE_DEVICE_INFO = 0x97 # 0x03: Інформація про пристрій
CMD_TYPE_CELL_INFO = 0x96 # 0x02: Інформація про ячейки
# CMD_TYPE_SETTINGS = 0x95 # 0x01: Налаштування

response_buffer = bytearray()

def calculate_crc(data):
    return sum(data) & 0xFF

def create_command(command_type):
    frame = bytearray(20)
    frame[:4] = CMD_HEADER
    frame[4] = command_type
    frame[19] = calculate_crc(frame[:19])
    return frame

def log(device_name, message):
    """Додає назву пристрою до логів."""
    print(f"{BLUE}[{device_name}]{RESET} {message}")

def parse_device_info(data, device_name):
    """Парсинг Device Info Frame (0x03)."""
    log(device_name, "Parsing Device Info Frame...")

    try:
        log(device_name, f"Raw data: {data.hex()}")
        
        # Перевірка заголовку
        if data[:4] != b'\x55\xAA\xEB\x90':
            raise ValueError("Invalid frame header")

        # Витягуємо поля з фрейму
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

        # Логування розпарсеної інформації
        log(device_name, "Parsed Device Info:")
        for key, value in device_info.items():
            log(device_name, f"{key}: {value}")

        return device_info

    except Exception as e:
        log(device_name, f"Error parsing Device Info Frame: {e}")
        return None

def parse_device_data(data: bytearray):
    start_index = 5  # Початковий індекс, після якого починається корисна інформація
    
    # Послідовно зчитуємо кожен сегмент до 0x00
    segments = []
    while start_index < len(data):
        try:
            end_index = data.index(0x00, start_index)  # Знаходимо наступний 0x00
            segment = data[start_index:end_index].decode('utf-8', errors='ignore')  # Декодуємо
            segments.append(segment)
            start_index = end_index + 1  # Переміщаємося до наступного байта після 0x00
        except ValueError:
            break  # Якщо 0x00 більше немає, виходимо з циклу
    
    # Видаляємо порожні строки після декодування
    segments = [seg for seg in segments if seg.strip()]

    if len(segments) < 5:
        raise ValueError("Недостатньо даних для парсингу")

    device_info = {
        "device_name": segments[0],
        "firmware_version": segments[1],
        "serial_number": segments[2],
        "hardware_version": segments[3],
        "other_info": segments[4:]  # Усе інше — додаткові дані
    }
    
    return device_info

def parse_cell_info(data, device_name):
    """Парсинг Cell Info Frame (0x02)."""
    log(device_name, "Parsing Cell Info Frame...")
    try:
        num_cells = data[5]  # Кількість ячейок
        cell_voltages = []
        log(device_name, f"Cells: {num_cells}")

        # Початковий байт для напруги ячейок
        start_index = 6
        for i in range(num_cells):
            voltage_raw = int.from_bytes(data[start_index:start_index + 2], byteorder='little')
            voltage = voltage_raw / 1000.0  # Перетворення вольт
            if voltage > 0:  # Додаємо тільки якщо напруга більше 0
                cell_voltages.append((i + 1, voltage))  # Зберігаємо номер ячейки і напругу
            start_index += 2

        cell_info = {
            "num_cells": len(cell_voltages),  # Кількість ячейок з напругою > 0
            "cell_voltages": cell_voltages,
        }

        log(device_name, f"Number of Cells with voltage > 0: {len(cell_voltages)}")
        for cell_num, voltage in cell_voltages:
            if cell_num > 17:
                log(device_name, f"{YELLOW}Cells Wire Resistance {cell_num}: {voltage:.3f} V{RESET}")
            else:
                log(device_name, f"{GREEN}Cell {cell_num}: {voltage:.3f} V{RESET}")

        return cell_info

    except Exception as e:
        log(device_name, f"Error parsing Cell Info Frame: {e}")
        return None

async def notification_handler(sender, data, device_name):
    global response_buffer

    if data[:4] == b'\x55\xAA\xEB\x90':  # Початок нового фрейму
        response_buffer = bytearray()   # Очистка буфера
    response_buffer.extend(data)       # Додавання даних до буфера

    if MIN_FRAME_SIZE <= len(response_buffer) <= MAX_FRAME_SIZE:
        log(device_name, f"Full frame received: {response_buffer.hex()}")

        # Перевірка CRC
        calculated_crc = calculate_crc(response_buffer[:-1])
        received_crc = response_buffer[-1]
        if calculated_crc != received_crc:
            log(device_name, f"Invalid CRC: {calculated_crc} != {received_crc}")
            return

        # Визначення типу фрейму
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

            # Надсилаємо команди для Device Info і Cell Info
            device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
            cell_info_command = create_command(CMD_TYPE_CELL_INFO)

            await client.write_gatt_char(CHARACTERISTIC_UUID, device_info_command)
            log(device.name, f"Device Info command sent: {device_info_command.hex()}")

            await asyncio.sleep(1)  # Очікування між командами

            await client.write_gatt_char(CHARACTERISTIC_UUID, cell_info_command)
            log(device.name, f"Cell Info command sent: {cell_info_command.hex()}")

            await asyncio.sleep(30)  # Час для отримання даних
            await client.stop_notify(CHARACTERISTIC_UUID)
            log(device.name, "Notification stopped")
    except Exception as e:
        log(device.name, f"Error: {str(e)}")

async def main():
    devices = await BleakScanner.discover()
    if not devices:
        print("No BLE devices found.")
        return

    for device in devices:
        await connect_and_run(device)

if __name__ == "__main__":
    asyncio.run(main())
