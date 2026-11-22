"""BLE connections to JK-BMS devices: scanning, connecting, polling, notifications and writes."""
import asyncio
from datetime import datetime

from bleak import BleakClient, BleakScanner

import python.db as db
from python.ble.frames import process_frame
from python.ble.protocol import (
    CHARACTERISTIC_UUID,
    CMD_TYPE_CELL_INFO,
    CMD_TYPE_DEVICE_INFO,
    CMD_TYPE_SETTINGS,
    FRAME_HEADER,
    JK_BMS_OUI,
    MAX_FRAME_SIZE,
    MIN_FRAME_SIZE,
    calculate_crc,
    create_command,
)
from python.data_store import data_store
from python.logger import log
from python.tasks import spawn

# BlueZ cannot run several discoveries at once ("Operation already in progress"), and a scan also
# disturbs active connections, so every scan goes through one lock.
ble_scan_lock = asyncio.Lock()

async def discover_ble_devices(timeout: float = 5.0):
    async with ble_scan_lock:
        return await BleakScanner.discover(timeout=timeout)

# Connected BLE clients (for write commands from the API) and per-device write locks so API writes
# never interleave with the polling loop's commands.
active_clients: dict = {}
ble_write_locks: dict = {}

async def ble_write(device_address: str, client, frame):
    lock = ble_write_locks.setdefault(device_address, asyncio.Lock())
    async with lock:
        await client.write_gatt_char(CHARACTERISTIC_UUID, frame)
    

async def disconnect_if_needed(device_address):
    try:
        client = BleakClient(device_address)
        if client:
            await client.disconnect()
            log("BLE", f"🔴 Forcibly disabled {device_address}.", force=True)
    except Exception as e:
        log("BLE", f"⚠️ Unable to disable {device_address}: {e}", force=True)


# Per-device reassembly buffers. Only touched synchronously from the BLE callback (which runs on the
# event loop), so no lock is needed and packets can never be interleaved/parsed twice.
response_buffers: dict = {}

def handle_ble_notification(device, data: bytearray):
    device_name = device.name
    device_address = device.address.lower()

    if device_address not in active_connections:
        response_buffers.pop(device_address, None)
        log(device_name, f"⚠️ Device {device_address} is not in active_connections, ignore the data.", force=True)
        return

    buffer = response_buffers.setdefault(device_address, bytearray())
    if data[:4] == FRAME_HEADER:  # The beginning of a new frame
        buffer.clear()
    elif not buffer:
        return  # continuation of a frame whose start we missed
    buffer.extend(data)

    if len(buffer) > MAX_FRAME_SIZE:
        buffer.clear()
        return
    if len(buffer) < MIN_FRAME_SIZE:
        return

    # Checking the CRC
    calculated_crc = calculate_crc(buffer[:-1])
    received_crc = buffer[-1]
    if calculated_crc != received_crc:
        log(device_name, f"❌ Invalid CRC: {calculated_crc} != {received_crc}")
        return

    frame = bytes(buffer)  # immutable copy for the parser
    buffer.clear()
    log(device_name, f"🔄 Full frame received {frame[4]}: {frame.hex()}")
    spawn(process_frame(frame, device_name, device_address))


device_locks = {}
async def connect_and_run(device):
    device_address = device.address.lower()
    
    if device_address not in device_locks:
        device_locks[device_address] = asyncio.Lock()

    async with device_locks[device_address]:
        while True:  # Cycle to reconnect
            try:
                device_info_data = db.get_device_by_address(device_address)

                if not device_info_data:
                    device_info_data = db.insert_device(
                        address=device_address,
                        name=device.name,
                        frame_type=None,
                        frame_counter=None,
                        vendor_id=None,
                        hardware_version=None,
                        software_version=None,
                        device_uptime=None,
                        power_on_count=None,
                        manufacturing_date=None,
                        serial_number=None,
                        user_data=None,
                        connected=False,
                        enabled=True
                        )

                if not device_info_data.get("enabled", False):
                    log(device.name, "❌ Device has been off. Stopping connecting...", force=True)
                    active_connections.pop(device_address, None)
                    device_locks.pop(device_address, None)
                    await disconnect_if_needed(device_address)
                    db.update_device_status(device_address, connected=False, enabled=False)
                    break

                async with BleakClient(device.address) as client:
                    def handle_notification(sender, data):
                        handle_ble_notification(device, data)

                    await client.start_notify(CHARACTERISTIC_UUID, handle_notification)
                    active_clients[device_address] = client
                    db.update_device_status(device_address, connected=True, enabled=True)
                    log(device.name, f"🟢 Connected and notification started", force=True)

                    while True:
                        # Check if the device is still connected
                        device_info_data = db.get_device_by_address(device_address)
                        if not device_info_data or not device_info_data.get("connected", False):
                            log(device.name, "❌ Device has been disconnected. Stopping polling.", force=True)
                            response_buffers.pop(device_address, None)
                            active_connections.pop(device_address, None)
                            break

                        # The key always exists (possibly None), so check the value, not the key.
                        if device_info_data.get("frame_type") is None:
                            # If the device information is not yet saved, send the command
                            device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
                            await ble_write(device_address, client, device_info_command)
                            log(device.name, f"📲 Device Info command sent: {device_info_command.hex()}", force=True)
                            await asyncio.sleep(2)

                        settings_info = await data_store.get_setting_info_by_address(device_address)
                        if not settings_info:
                            setting_info_command = create_command(CMD_TYPE_SETTINGS)
                            await ble_write(device_address, client, setting_info_command)
                            log(device.name, f"⚙️ Setting Info command sent: {setting_info_command.hex()}", force=True)
                            await asyncio.sleep(8)

                        # Checking whether to send cell_info_command
                        last_update = await data_store.get_last_cell_info_update(device.name)
                        if not last_update or (datetime.now() - last_update).total_seconds() > 30:
                            device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
                            await ble_write(device_address, client, device_info_command)
                            log(device.name, f"📢 Device Info command sent: {device_info_command.hex()}", force=True)
                            await asyncio.sleep(2)

                            cell_info_command = create_command(CMD_TYPE_CELL_INFO)
                            await ble_write(device_address, client, cell_info_command)
                            log(device.name, f"✅ Command successfully sent: {cell_info_command.hex()}", force=True)
                            log(device.name, f"Last update: {last_update}. Now: {datetime.now()}", force=True)
                            await asyncio.sleep(2)
                            
                        await asyncio.sleep(8)

            except Exception as e:
                log(device.name, f"❌ Connection error: {str(e)}", force=True)
            finally:
                active_clients.pop(device_address, None)
                log(device.name, "🔄 Retrying connection in 8 seconds...", force=True)
                await asyncio.sleep(8)

async def filter_devices(devices):
    allowed_devices = db.get_all_devices()
    allowed_addresses = {device["address"] for device in allowed_devices if device["enabled"]}
    connected_addresses = {device["address"].lower() for device in allowed_devices if device["connected"]}

    filtered_devices = []
    for device in devices:
        device_address = device.address.lower()
        if not any(device_address.startswith(oui) for oui in JK_BMS_OUI):
            continue
        if device_address in active_connections or device_address in connected_addresses:
            log(device.name, f"⚠️ Device {device.name} is already connected or connecting, skipping.")
            continue
        if device_address not in allowed_addresses:
            continue
        filtered_devices.append(device)
    return filtered_devices

active_connections = {}

def _cleanup_finished_connections():
    for device_address, task in list(active_connections.items()):
        if not task.done():
            continue
        if not task.cancelled() and task.exception():
            log(device_address, f"❌ Connection task failed with error: {task.exception()}", force=True)
        active_connections.pop(device_address, None)

async def ble_main():
    """Scans for enabled-but-not-connected BMS devices and starts a connection task for each.

    Connection tasks run independently (they reconnect by themselves), so this loop never blocks on
    them: devices that show up later are picked up on the next iteration. Errors are handled per
    iteration, so a single BlueZ failure no longer stops auto-connecting until a restart.
    """
    while True:
        try:
            _cleanup_finished_connections()

            allowed_devices = db.get_all_devices(only_enabled=True)
            pending = {
                device["address"].lower() for device in allowed_devices
                if not device["connected"] and device["address"].lower() not in active_connections
            }

            # Skip scanning if every enabled device is already connected/connecting
            if not pending:
                await asyncio.sleep(60)
                continue

            log("ble_main", "🔍 Start scanning for devices...", force=True)
            devices = await discover_ble_devices()
            filtered_devices = await filter_devices(devices)

            if not filtered_devices:
                log("ble_main", "⚠️ No new JK-BMS BLE devices found.")
                await asyncio.sleep(15)
                continue
            log("ble_main", f"DEVICES: {filtered_devices}", force=True)

            for device in filtered_devices:
                device_address = device.address.lower()
                log(device.name, f"🔌 Connecting to allowed device: {device.address}", force=True)
                active_connections[device_address] = spawn(connect_and_run(device))
                await asyncio.sleep(3)  # Delay between connections

            await asyncio.sleep(15)  # Waiting before the next scan

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log("ble_main", f"❌ BLE scan error: {str(e)}", force=True)
            await asyncio.sleep(5)
