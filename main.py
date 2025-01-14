import asyncio
from bleak import BleakClient, BleakScanner

SERVICE_UUID = "0000FFE0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000FFE1-0000-1000-8000-00805f9b34fb"

CMD_HEADER = bytes([0xAA, 0x55, 0x90, 0xEB])
CMD_TYPE_DEVICE_INFO = 0x97
CMD_TYPE_CELL_INFO = 0x96

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
    print(f"[{device_name}] {message}")

def parse_device_info(data, device_name):
    """Парсинг Device Info Frame (0x03)."""
    log(device_name, "Parsing Device Info Frame...")
    device_info = {
        "device_name": data[5:35].decode('utf-8', errors='ignore').strip(),
        "serial_number": data[35:55].decode('utf-8', errors='ignore').strip(),
        "firmware_version": data[55:75].decode('utf-8', errors='ignore').strip(),
        "hardware_version": data[75:95].decode('utf-8', errors='ignore').strip(),
        "other_info": data[95:],
    }

    log(device_name, "Device Info Parsed:")
    for key, value in device_info.items():
        log(device_name, f"{key}: {value}")

    crc_calculated = calculate_crc(data[:-1])
    crc_received = data[-1]

    if crc_calculated != crc_received:
        log(device_name, f"Invalid CRC: {crc_calculated} != {crc_received}")
    else:
        log(device_name, "CRC Valid")

    return device_info

def parse_cell_info(data, device_name):
    """Парсинг Cell Info Frame (0x02)."""
    log(device_name, "Parsing Cell Info Frame...")
    try:
        num_cells = data[5]  # Кількість ячейок
        cell_voltages = []

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

        log(device_name, "Cell Info Parsed:")
        log(device_name, f"Number of Cells with voltage > 0: {len(cell_voltages)}")
        for cell_num, voltage in cell_voltages:
            log(device_name, f"Cell {cell_num}: {voltage:.3f} V")

        return cell_info

    except Exception as e:
        log(device_name, f"Error parsing Cell Info Frame: {e}")
        return None

async def notification_handler(sender, data, device_name):
    if data[:4] == b'\x55\xAA\xEB\x90':
        log(device_name, f"Notification received: {data.hex()}")

        frame_type = data[4]
        if frame_type == 0x03:
            parse_device_info(data, device_name)
        elif frame_type == 0x02:
            parse_cell_info(data, device_name)
        else:
            log(device_name, f"Unknown frame type: {frame_type}")

async def connect_and_run(device):
    try:
        async with BleakClient(device.address) as client:
            # Використовуємо asyncio.create_task для виклику notification_handler
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
