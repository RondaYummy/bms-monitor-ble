import asyncio
from datetime import datetime
import os
import yaml
from uuid import uuid4
from typing import Optional

import uvicorn
from bleak import BleakClient, BleakScanner
from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Depends,
    Query
)
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from fastapi import Body

from python.colors import *
import python.db as db
from python.jk_bms_parser import parse_device_info, parse_setting_info
from python.data_store import data_store

with open('configs/error_codes.yaml', 'r') as file:
    error_codes = yaml.safe_load(file)

ENABLE_LOGS = False # True or False

MIN_FRAME_SIZE = 300
MAX_FRAME_SIZE = 320
SERVICE_UUID = "0000FFE0-0000-1000-8000-00805f9b34fb"
CHARACTERISTIC_UUID = "0000FFE1-0000-1000-8000-00805f9b34fb"
CMD_HEADER = bytes([0xAA, 0x55, 0x90, 0xEB])
CMD_TYPE_DEVICE_INFO = 0x97 # 0x03: Device Info Frame
CMD_TYPE_CELL_INFO = 0x96 # 0x02: Cell Info Frame
CMD_TYPE_SETTINGS = 0x95 # 0x01: Settings
JK_BMS_OUI = {"c8:47:80"} # Через кому можна додати усі початки дял девайсів від JK-BMS

PASSWORD = "123456"
TOKEN_LIFETIME_SECONDS = 3600

app = FastAPI()
auth_scheme = HTTPBearer()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    if not await data_store.is_token_valid(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    password = body.get("password", "")
    if password != PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")

    token = str(uuid4())
    await data_store.add_token(token, "admin")

    return {"access_token": token}

class DeleteAlertRequest(BaseModel):
    id: int
@app.post("/api/error-alerts")
async def delete_error_alert(request: DeleteAlertRequest, token: str = Depends(verify_token)):
    try:
        db.delete_alert_by_id(alert_id=request.id)
        return {"message": f"Alert with ID {request.id} has been deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting alert: {str(e)}")
    
@app.get("/api/error-alerts")
async def get_device_info():
    data = db.fetch_all_notifications()
    if not data:
        return JSONResponse(content={"message": "No error alerts available yet."}, status_code=404)
    
    enriched_data = []
    for alert in data:
        if isinstance(alert, tuple):
            alert = {
                "id": alert[0],
                "device_address": alert[1],
                "error_code": alert[2],
                "device_name": alert[3],
                "timestamp": alert[4],
                "level": "",
            }
        error_code = int(alert.get("error_code"))
        message = error_codes.get(error_code, {}).get('message', 'Message not found')
        level = error_codes.get(error_code, {}).get('level', 'Level not found')
        enriched_alert = {**alert, "message": message, "level": level}
        enriched_data.append(enriched_alert)

    return enriched_data

class DeviceRequest(BaseModel):
    address: str
    name: Optional[str] = None
@app.post("/api/disconnect-device")
async def disconnect_device(body: DeviceRequest = Body(...), token: str = Depends(verify_token)):
    ALLOWED_DEVICES_FILE = "configs/allowed_devices.txt"
    device_address = body.address.strip().lower()
    device_name = body.name.strip()

    if not device_address:
        raise HTTPException(status_code=400, detail="Device address is required.")

    try:
        allowed_devices = set()
        if os.path.exists(ALLOWED_DEVICES_FILE):
            with open(ALLOWED_DEVICES_FILE, "r", encoding="utf-8") as file:
                allowed_devices = {line.strip().lower() for line in file if line.strip()}

        if device_address not in allowed_devices:
            raise HTTPException(status_code=404, detail="Device not found in allowed list.")

        device_info = await data_store.get_device_info(device_name)
        print(f"DEV INFO: {device_info}")
        if device_info:
            device_info["connected"] = False
            await data_store.update_device_info(device_name, device_info)

        allowed_devices.remove(device_address)
        with open(ALLOWED_DEVICES_FILE, "w", encoding="utf-8") as file:
            for addr in allowed_devices:
                file.write(f"{addr}\n")

        return {"message": f"Successfully disconnected from {device_address} and removed from allowed list."}

    except Exception as e:
        log(device_name, f"BLE disconnect failed: {e}", force=True)

        device_info = await data_store.get_device_info(device_name)
        if device_info:
            device_info["connected"] = False
            await data_store.update_device_info(device_name, device_info)

        raise HTTPException(status_code=500, detail=f"Error disconnecting device: {str(e)}")

@app.post("/api/connect-device")
async def connect_device(request: DeviceRequest, token: str = Depends(verify_token)):
    ALLOWED_DEVICES_FILE = "configs/allowed_devices.txt"
    try:
        device_address = request.address.strip().lower()
        device_name = request.name.strip()

        if not device_address:
            raise HTTPException(status_code=400, detail="Device address is required.")

        existing_device_info = await data_store.get_device_info(device_address)
        if existing_device_info and existing_device_info.get("connected", False):
            return JSONResponse(content={"message": f"Device {device_address} is already connected."}, status_code=200)

        async with ble_scan_lock:
            log(device_address, "Starting connection process...", force=True)

        allowed_devices = load_allowed_devices()
        if device_address not in allowed_devices:
            with open(ALLOWED_DEVICES_FILE, "a", encoding="utf-8") as file:
                file.write(f"{device_address}\n")

        device = type("Device", (object,), {"address": device_address, "name": device_name})()
        asyncio.create_task(connect_and_run(device))

        return {"message": f"Connection initiated for {device_address}. Check logs for updates."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to device: {str(e)}")

    
@app.get("/api/devices")
async def discover_devices():
    try:
        async with ble_scan_lock:
            log("API", "Start scanning for devices...", force=True)
            devices = await BleakScanner.discover()
        
        allowed_devices = load_allowed_devices()

        device_list = [
            {"name": device.name, "address": device.address.lower()}
            for device in devices
            if device.name and device.address.lower().startswith(tuple(JK_BMS_OUI))
            and device.address.lower() not in allowed_devices
        ]

        if not device_list:
            return JSONResponse(content={"message": "No new JK-BMS devices found."}, status_code=404)

        return {"devices": device_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching for devices: {str(e)}")


@app.get("/api/device-info")
async def get_device_info():
    data = await data_store.get_device_info()
    if not data:
        return JSONResponse(content={"message": "No device info available yet."}, status_code=404)
    return data

@app.get("/api/cell-info")
async def get_cell_info():
    cell_info_data = await data_store.get_cell_info()
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

async def notification_handler(device, data, device_name, device_address):
    if data[:4] == b'\x55\xAA\xEB\x90':  # The beginning of a new frame
        await data_store.clear_buffer(device_name)
    await data_store.append_to_buffer(device_name, data)

    buffer = await data_store.get_buffer(device_name)
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
            await data_store.update_last_cell_info_update(device_name)
            await parse_cell_info(buffer, device_name, device_address)
        elif frame_type == 0x01:
            await parse_setting_info(buffer, device_name, device_address)
        else:
            log(device_name, f"Unknown frame type {frame_type}: {buffer}", force=True)
            await data_store.clear_buffer(device_name)

device_locks = {}
async def connect_and_run(device):
    device_address = device.address.lower()
    
    if device_address not in device_locks:
        device_locks[device_address] = asyncio.Lock()

    async with device_locks[device_address]:
        while True:  # Cycle to reconnect
            try:
                device_info_data = await data_store.get_device_info(device.name)
                if not device_info_data:
                    device_info_data = {
                        "device_name": device.name,
                        "device_address": device.address,
                        "connected": False
                    }
                await data_store.update_device_info(device.name, device_info_data)

                async with BleakClient(device.address) as client:
                    device_info_data["connected"] = True
                    await data_store.update_device_info(device.name, device_info_data)
                    log(device.name, f"Connected and notification started", force=True)

                    def handle_notification(sender, data):
                        asyncio.create_task(notification_handler(device, data, device.name, device.address))

                    await client.start_notify(CHARACTERISTIC_UUID, handle_notification)

                    while True:  # Постійне опитування
                    # Перевіряємо, чи пристрій ще підключений
                        device_info_data = await data_store.get_device_info(device.name)
                        if not device_info_data.get("connected", False):
                            log(device.name, "Device has been disconnected. Stopping polling.", force=True)
                            break

                        device_info_data = await data_store.get_device_info(device.name)
                        if not device_info_data or "frame_type" not in device_info_data:
                            # Якщо інформація про пристрій ще не збережена, надсилаємо команду
                            device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
                            await client.write_gatt_char(CHARACTERISTIC_UUID, device_info_command)
                            log(device.name, f"Device Info command sent: {device_info_command.hex()}")
                            await asyncio.sleep(1)

                        # Перевіряємо, чи потрібно надсилати cell_info_command
                        last_update = await data_store.get_last_cell_info_update(device.name)
                        if not last_update or (datetime.now() - last_update).total_seconds() > 30:
                            cell_info_command = create_command(CMD_TYPE_CELL_INFO)
                            await client.write_gatt_char(CHARACTERISTIC_UUID, cell_info_command)
                            log(device.name, f"Cell Info command sent: {cell_info_command.hex()}")

                        await asyncio.sleep(5)
            except Exception as e:
                log(device.name, f"Error: {str(e)}", force=True)
            finally:
                device_info_data["connected"] = False
                await data_store.update_device_info(device.name, device_info_data)
                log(device.name, "Disconnected, retrying in 5 seconds...", force=True)
                await asyncio.sleep(5)

ble_scan_lock = asyncio.Lock()
async def ble_main():
    while True:
        async with ble_scan_lock:
            log("ble_main", "Start scanning...", force=True)
            try:
                allowed_devices = load_allowed_devices()
                devices = await BleakScanner.discover()

                if not devices:
                    print("No BLE devices found.")
                    await asyncio.sleep(5)
                    continue

                tasks = []
                for device in devices:
                    device_address = device.address.lower()

                    if not any(device_address.startswith(oui) for oui in JK_BMS_OUI):
                        continue  # Skip devices that are not JK-BMS

                    if device_address in allowed_devices: # Check if the device is allowed
                        device_info = await data_store.get_device_info(device.name) # Check if the device is already connected
                        if device_info and device_info.get("connected", False):
                            log(device.name, f"Device {device.name} is already connected, skipping.")
                            continue  # Skip if the device is already connected

                        log(device.name, f"Connecting to allowed device: {device.address}", force=True)
                        tasks.append(asyncio.create_task(connect_and_run(device)))
                        await asyncio.sleep(5)
                if tasks:
                    asyncio.create_task(asyncio.gather(*tasks))
            except Exception as e:
                print(f"BLE scan error: {str(e)}")
                await asyncio.sleep(5)
                                    
def is_device_address_in_cell_info(device_address, cell_info):
    """
    Checks if `device_address' exists in the nested values of `cell_info'.
    """
    for device_data in cell_info.values():
        if device_data.get("device_address") == device_address:
            return True
    return False

async def are_all_allowed_devices_connected_and_have_data() -> bool:
    """
    Checks if all devices from the allowed_devices list are connected
    and whether there is data for each in cell_info.
    """
    allowed_devices = {addr.lower() for addr in load_allowed_devices()}
    connected_devices = await data_store.get_device_info()
    connected_addresses = {
        device_info.get("device_address", "").lower()
        for device_info in connected_devices.values()
        if device_info.get("connected", False)
    }
    log("ALLOWED DEVICES", f"[{allowed_devices}]")
    log("CONNECTED DEVICES", f"[{connected_addresses}]")

    if not allowed_devices.issubset(connected_addresses):
        log("CHECK DEVICES", "All allowed devices are not connected", force=True)
        return False

    cell_info = await data_store.get_cell_info()
    for device_address in allowed_devices:
        if not is_device_address_in_cell_info(device_address, cell_info):
            log("CHECK DEVICES", f"Device [{device_address}] have no data.", force=True)
            return False

    return True

def ensure_allowed_devices_file(filename="configs/allowed_devices.txt"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as file:
            file.write("")

def start_services():
    ensure_allowed_devices_file()
    db.create_table()
    uvicorn.run(app, host="0.0.0.0", port=8000)

def load_allowed_devices(filename="configs/allowed_devices.txt"):
    try:
        with open(filename, 'r') as file:
            allowed_devices = {line.strip().lower() for line in file if line.strip()}
        return allowed_devices
    except FileNotFoundError:
        print(f"Warning: {filename} not found. All devices will be blocked.")
        return set()

if __name__ == "__main__":
    start_services()
