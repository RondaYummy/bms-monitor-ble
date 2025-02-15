import asyncio
from datetime import datetime
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
import python.battery_alerts as alerts
from python.push_notifications import send_push_startup
from python.push_notifications import router as alerts_router
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
JK_BMS_OUI = {"c8:47:80"} # Separated by a comma, you can add all the beginnings of the JK-BMS devices

TOKEN_LIFETIME_SECONDS = 3600

app = FastAPI()
app.include_router(alerts_router, prefix="/api")
auth_scheme = HTTPBearer()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(ble_main())
    asyncio.create_task(db.process_devices())

    config = db.get_config()
    await send_push_startup(config)

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(auth_scheme)):
    token = credentials.credentials
    if not await data_store.is_token_valid(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/api/login")
async def login(request: Request):
    body = await request.json()
    password = body.get("password", "")
    config = db.get_config()
    log("LOGIN", f"config: {config}")
    if not config or password != config.get("password"):
        raise HTTPException(status_code=401, detail="Invalid password")

    token = str(uuid4())
    await data_store.add_token(token, "admin")

    return {"access_token": token}

class ConfigUpdateRequest(BaseModel):
    password: Optional[str] = None
    VAPID_PUBLIC_KEY: Optional[str] = None
    n_hours: Optional[int] = None
@app.get("/api/configs")
async def get_configs():
    config = db.get_config()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found.")
    
    for key in ["VAPID_PRIVATE_KEY", "password"]:
        config.pop(key, None)
    return config

@app.post("/api/configs", dependencies=[Depends(verify_token)])
async def update_configs(request: ConfigUpdateRequest):
    updated_config = db.update_config(
        password=request.password,
        vapid_public=None,
        vapid_private=None,
        n_hours=request.n_hours
    )
    if not updated_config:
        raise HTTPException(status_code=500, detail="Error updating config.")
    return {"message": "Configuration updated successfully", "config": updated_config}

@app.get("/api/device-settings")
async def get_device_settings():
    try:
        setting_info = await data_store.get_setting_info()
        if not setting_info:
            return JSONResponse(content={"message": "No settings available yet."}, status_code=404)

        return list(setting_info.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting alert: {str(e)}")

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

async def disconnect_if_needed(device_address):
    try:
        client = BleakClient(device_address)
        if client:
            await client.disconnect()
            log("BLE", f"🔴 Forcibly disabled {device_address}.", force=True)
    except Exception as e:
        log("BLE", f"⚠️ Unable to disable {device_address}: {e}", force=True)

class DeviceRequest(BaseModel):
    address: str
    name: Optional[str] = None
@app.post("/api/disconnect-device")
async def disconnect_device(body: DeviceRequest = Body(...), token: str = Depends(verify_token)):
    device_address = body.address.strip().lower()
    device_name = body.name.strip() if body.name else device_address
    if not device_address:
        raise HTTPException(status_code=400, detail="Device address is required.")
    
    try:
        existing_device = db.get_device_by_address(device_address)
        if not existing_device:
            raise HTTPException(status_code=404, detail="🚫 Device not found in the database.")

        if not existing_device["connected"]:
            return JSONResponse(content={"message": f"✅ Device {device_address} is already disconnected."}, status_code=200)

        log(device_name, f"🔌 Disconnecting device {device_address}...")

        task = active_connections.get(device_address)
        if task:
            task.cancel()
            del active_connections[device_address]
            log(device_name, f"🔴 {device_address} removed from active_connections")
        
        await disconnect_if_needed(device_address)

        db.update_device_status(device_address, connected=False, enabled=False)

        await data_store.delete_device_data(device_name)
        
        log(device_name, f"✅ Successfully disconnected and disabled the device.")
        return {"message": f"✅ Successfully disconnected from {device_address} and disabled the device."}

    except Exception as e:
        log(device_name, f"❌ BLE disconnect failed: {e}", force=True)
        db.update_device_status(device_address, connected=False, enabled=False)
        raise HTTPException(status_code=500, detail=f"❌ Error disconnecting device: {str(e)}")


@app.post("/api/connect-device")
async def connect_device(request: DeviceRequest, token: str = Depends(verify_token)):
    try:
        device_address = request.address.strip().lower()
        device_name = request.name.strip() if request.name else device_address

        if not device_address:
            raise HTTPException(status_code=400, detail="Device address is required.")

        await disconnect_if_needed(device_address)
        log("/api/connect-device", f"🔍 Scanning for device {device_address}...", force=True)

        devices = await BleakScanner.discover()
        log("/api/connect-device", f"FOUND DEVICES: {devices}", force=True)
        found_device = next((device for device in devices if device.address.lower() == device_address), None)

        if not found_device:
            log("/api/connect-device", f"Device {device_address} not found...", force=True)
            return JSONResponse(content={"error": f"Device {device_address} not found."}, status_code=200)

        log("/api/connect-device", f"✅ Device {device_address} found, attempting connection...", force=True)

        existing_device = db.get_device_by_address(device_address)
        if not existing_device:
            existing_device = db.insert_device(address=device_address, name=device_name)

        if existing_device and existing_device["connected"]:
            return JSONResponse(content={"message": f"✅ Device {device_address} is already connected."}, status_code=200)

        db.update_device_status(device_address, connected=True, enabled=True)

        log("/api/connect-device", f"🚀 Connection initiated for {found_device}.", force=True)
        task = asyncio.create_task(connect_and_run(found_device))
        active_connections[device_address] = task
        db.update_device_status(device_address, connected=True, enabled=True)

        return JSONResponse(content={"message": f"🚀 Connection initiated for {device_address}. Check logs for updates."}, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": f"❌ Error connecting to device: {str(e)}"}, status_code=500)


@app.get("/api/devices")
async def discover_devices():
    try:
        log("API", "🔍 Scanning for new devices...")
        devices = await BleakScanner.discover()

        allowed_devices = db.get_all_devices()
        allowed_addresses = {device["address"].lower() for device in allowed_devices}

        new_devices = [
            {"name": device.name, "address": device.address.lower()}
            for device in devices
            if device.name and device.address.lower().startswith(tuple(JK_BMS_OUI))
            and device.address.lower() not in allowed_addresses
        ]
        if not new_devices:
            return JSONResponse(content={"message": "No new JK-BMS devices found."}, status_code=404)

        return {"devices": new_devices}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error searching for devices: {str(e)}")


@app.get("/api/device-info")
async def get_device_info():
    data = db.get_all_devices()
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

def calculate_crc(data):
    return sum(data) % 256

def create_command(command_type):
    frame = bytearray(20)
    frame[:4] = CMD_HEADER
    frame[4] = command_type
    frame[19] = calculate_crc(frame[:19])
    return frame
    
def log(device_name, message, force=False):
    global ENABLE_LOGS
    if ENABLE_LOGS or force:
        current_time = datetime.now().strftime("%d.%m.%y %H:%M:%S")
        print(f"{BLUE}[{device_name}] {MAGENTA}[{current_time}]{RESET} {message}")

async def parse_device_info(data, device_name, device_address):
    """Parsing Device Info Frame (0x03)."""
    log(device_name, "Parsing Device Info Frame...")
    try:
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
            "enabled": True
        }
        
        # Save device-specific info
        db.update_device(
            device_address,
            frame_type=device_info["frame_type"],
            frame_counter=device_info["frame_counter"],
            vendor_id=device_info["vendor_id"],
            hardware_version=device_info["hardware_version"],
            software_version=device_info["software_version"],
            device_uptime=device_info["device_uptime"],
            power_on_count=device_info["power_on_count"],
            name=device_info["device_name"],
            manufacturing_date=device_info["manufacturing_date"],
            serial_number=device_info["serial_number"],
            user_data=device_info["user_data"],
            connected=device_info["connected"],
            enabled=device_info["enabled"]
        )

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
    log(device_name, "🔍 Parsing Setting Info Frame...")
    try:
        setting_info = {
            "name": device_name,
            "address": device_address,

            # [MAIN] Base Settings
            "cell_count": data[114], # Cell Count
            "nominal_battery_capacity": int.from_bytes(data[130:134], "little") * 0.001, # Battery Capacity (Ah)
            "balance_trigger_voltage": int.from_bytes(data[26:30], "little") * 0.001, # Balance Trig. Volt.(V)
            # Calibrating Volt.(V)
            # Calibrating Curr.(A)

            
            # [MAIN] Advance Settings
            "start_balance_voltage": int.from_bytes(data[138:142], "little") * 0.001, # Start Balance Volt.(V)
            "max_balance_current": int.from_bytes(data[78:82], "little") * 0.001, # Max Balance Cur.(A)
            "cell_ovp": int.from_bytes(data[18:22], "little") * 0.001, # Cell OVP(V)
            "cell_request_charge_voltage": int.from_bytes(data[38:42], "little") * 0.001, # Vol. Cell RCV(V)
            "soc_100_voltage": int.from_bytes(data[30:34], "little") * 0.001, # SOC-100% Volt.(V)
            "cell_ovpr": int.from_bytes(data[22:26], "little") * 0.001, # Cell  OVPR(V)
            "cell_uvpr": int.from_bytes(data[14:18], "little") * 0.001, # Cell UCPR(V)
            "soc_0_voltage": int.from_bytes(data[34:38], "little") * 0.001, # SOC-0% Volt.(V)
            "cell_uvp": int.from_bytes(data[10:14], "little") * 0.001, # Cell UVP(V)
            "power_off_voltage": int.from_bytes(data[46:50], "little") * 0.001, # Power Off Vol.(V)
            "cell_request_float_voltage": int.from_bytes(data[42:46], "little") * 0.001, # Vol. Cell RFV(V)
            "smart_sleep_voltage": int.from_bytes(data[6:10], "little") * 0.001, # Vol. Smart Sleep(V)
            "smart_sleep": data[286], # Time Smart Sleep(h)
            "max_charge_current": int.from_bytes(data[50:54], "little") * 0.001, # Continued Charge Curr.(A)
            "charge_ocp_delay": int.from_bytes(data[54:58], "little"), # Charge OCP Delay(s)
            "charge_ocp_recovery": int.from_bytes(data[58:62], "little"), # Charge OCPR Time(s)
            "max_discharge_current": int.from_bytes(data[62:66], "little") * 0.001, # Continued Discharge Curr.(A)
            "discharge_ocp_delay": int.from_bytes(data[66:70], "little"), # Discharge OCP Delay(s)
            "discharge_ocp_recovery": int.from_bytes(data[70:74], "little"), # Discharge OCPR Time(s)
            "charge_otp": int.from_bytes(data[82:86], "little") * 0.1, # Charge OTP(°c)
            "charge_otp_recovery": int.from_bytes(data[86:90], "little") * 0.1, # Charge OTPR(°c)
            "discharge_otp": int.from_bytes(data[90:94], "little") * 0.1, # Discharge OTP(°c)
            "discharge_otp_recovery": int.from_bytes(data[94:98], "little") * 0.1, # Discharge OTPR(°c)
            "charge_utp_recovery": int.from_bytes(data[102:106], "little", signed=True) * 0.1, # Charge UTPR(°c)
            "charge_utp": int.from_bytes(data[98:102], "little", signed=True) * 0.1, # Charge UTP(°c)
            "mos_otp": int.from_bytes(data[106:110], "little", signed=True) * 0.1, # MOS OTP(°c)
            "mos_otp_recovery": int.from_bytes(data[110:114], "little", signed=True) * 0.1, # MOS OTPR(°c)
            "short_circuit_protection_delay": int.from_bytes(data[134:138], "little"), # SCP Delay(???)
            "short_circuit_protection_recovery": int.from_bytes(data[74:78], "little"), # SCPR Time(s)
            "device_address": data[270], # Device Addr.
            # Data Stored Period(S)
            # RCV Time(H)
            # RFV Time(H)
            # Emerg. Time(Min)
            # User Private Data
            # User Data 2
            # UART1 Protocol No.
            # UART2 Protocol No.
            # CAN Protocol No.
            # LCD Buzzer Trigger
            # LCD Buzzer Trigger Val
            # LCD Buzzer Release Val
            # DRY 1 Trigger
            # DRY 1 Release Val


            # [MAIN] Con. Wire Res. Settings
            "connection_wire_resistances": [int.from_bytes(data[i:i+4], "little") * 0.001 for i in range(142, 270, 4)], # Con, Wire Res.01-12 (???)


            # [MAIN] Control Settings
            "charge_switch": bool(data[118]), # Charge
            "discharge_switch": bool(data[122]), # Discharge
            "balancer_switch": bool(data[126]), # Balance
            # Emergency
            "heating_enabled": None, # Heating
            "disable_temperature_sensors": None, # Disable Temp. Sensor
            "display_always_on": None, # Display Always On
            "special_charger": None, # Special Charger On
            "smart_sleep": None, # Smart Sleep On
            "timed_stored_data": None, # Timed Stored Data
            "charging_float_mode": None, # Charging Float Mode
            # DRY ARM Intermittent
            # Discharge OCP 2
            # Discharge OCP 3
            # Time....


            # [MAIN] Unknown
            "gps_heartbeat": None,
            "disable_pcl_module": None,
            "port_switch": None,
            "precharge_time": data[274],
            "data_field_enable_control": data[287],
            "controls_bitmask": int.from_bytes(data[282:284], "little"),
        }

        # Parse data from bitmask
        bitmask = int.from_bytes(data[282:284], "little")
        setting_info["heating_enabled"] = bool(bitmask & 0b0000000000000001)  # bit0
        setting_info["disable_temperature_sensors"] = bool(bitmask & 0b0000000000000010)  # bit1
        setting_info["gps_heartbeat"] = bool(bitmask & 0b0000000000000100)  # bit2
        setting_info["port_switch"] = "RS485" if bitmask & 0b0000000000001000 else "CAN"  # bit3
        setting_info["display_always_on"] = bool(bitmask & 0b0000000000010000)  # bit4
        setting_info["special_charger"] = bool(bitmask & 0b0000000000100000)  # bit5
        setting_info["smart_sleep"] = bool(bitmask & 0b0000000001000000)  # bit6
        setting_info["disable_pcl_module"] = bool(bitmask & 0b0000000010000000)  # bit7
        setting_info["timed_stored_data"] = bool(bitmask & 0b0000000100000000)  # bit8
        setting_info["charging_float_mode"] = bool(bitmask & 0b0000001000000000)  # bit9

        await data_store.update_setting_info(device_address, setting_info)

        log(device_name, "✅ Successfully disassembled Setting Info Frame:", force=True)
        for key, value in setting_info.items():
            log(device_name, f"{key}: {value}", force=True)

        return setting_info

    except Exception as e:
        log(device_name, f"❌ Parsing error Setting Info Frame: {e}", force=True)
        return None

async def parse_cell_info(data, device_name, device_address):
    """Parsing Cell Info Frame (0x02)."""
    try:
        log(device_name, "Parsing Cell Info Frame...")
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

        await data_store.update_cell_info(device_name, cell_info)
        await alerts.evaluate_alerts(device_address=device_address, device_name=device_name, cell_info=cell_info)

        if await are_all_allowed_devices_connected_and_have_data():
            db.update_aggregated_data(device_name=device_name, device_address=device_address, current=charge_current, power=battery_power)
        return cell_info

    except Exception as e:
        log(device_name, f"Error parsing Cell Info Frame: {e}", force=True)
        return None

async def notification_handler(device, data):
    device_name = device.name
    device_address = device.address.lower()

    task = active_connections.get(device_address)
    if not task:
        await data_store.clear_buffer(device_name)
        log(device_name, f"⚠️ Device {device_address} is not in active_connections, ignore the data.", force=True)
        return

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
            log(device_name, f"❌ Invalid CRC: {calculated_crc} != {received_crc}")
            return
        log(device.name, f"🔄 Received notification {buffer[4]}: {buffer.hex()}")

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
            log(device_name, f"❌ Unknown frame type {frame_type}: {buffer}", force=True)
            await data_store.clear_buffer(device_name)

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
                        asyncio.create_task(notification_handler(device, data))

                    await client.start_notify(CHARACTERISTIC_UUID, handle_notification)
                    db.update_device_status(device_address, connected=True, enabled=True)
                    log(device.name, f"🟢 Connected and notification started", force=True)

                    while True:
                        # Check if the device is still connected
                        device_info_data = db.get_device_by_address(device.address)
                        if not device_info_data or not device_info_data.get("connected", False):
                            log(device.name, "❌ Device has been disconnected. Stopping polling.", force=True)
                            break

                        # if not device_info_data or "frame_type" not in device_info_data:
                        #     # If the device information is not yet saved, send the command
                        #     device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
                        #     await client.write_gatt_char(CHARACTERISTIC_UUID, device_info_command)
                        #     log(device.name, f"📲 Device Info command sent: {device_info_command.hex()}", force=True)
                        #     await asyncio.sleep(2)

                        # Checking whether to send cell_info_command
                        last_update = await data_store.get_last_cell_info_update(device.name)
                        if not last_update or (datetime.now() - last_update).total_seconds() > 30:
                            device_info_command = create_command(CMD_TYPE_DEVICE_INFO)
                            await client.write_gatt_char(CHARACTERISTIC_UUID, device_info_command)
                            log(device.name, f"📢 Device Info command sent: {device_info_command.hex()}", force=True)
                            await asyncio.sleep(2)

                            cell_info_command = create_command(CMD_TYPE_CELL_INFO)
                            await client.write_gatt_char(CHARACTERISTIC_UUID, cell_info_command)
                            log(device.name, f"✅ Command successfully sent: {cell_info_command.hex()}", force=True)
                            log(device.name, f"Last update: {last_update}. Now: {datetime.now()}", force=True)
                            await asyncio.sleep(2)

                            settings_info = await data_store.get_setting_info_by_address(device_address)
                            if not settings_info:
                                setting_info_command = create_command(CMD_TYPE_SETTINGS)
                                await client.write_gatt_char(CHARACTERISTIC_UUID, setting_info_command)
                                log(device.name, f"⚙️ Setting Info command sent: {setting_info_command.hex()}", force=True)
                            
                        await asyncio.sleep(10)

            except Exception as e:
                log(device.name, f"❌ Connection error: {str(e)}", force=True)
            finally:
                log(device.name, "🔄 Retrying connection in 10 seconds...", force=True)
                await asyncio.sleep(10)

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

ble_scan_lock = asyncio.Lock()
active_connections = {}

async def ble_main():
    async with ble_scan_lock:
        try:
            while True:  # 🔥 Internal scanning and connection cycle
                log("ble_main", "Start ble_main...", force=True)
                allowed_devices = db.get_all_devices(only_enabled=True)
                allowed_addresses = {device["address"] for device in allowed_devices}
                connected_addresses = {
                    device["address"].lower() for device in allowed_devices if device["connected"]
                }

                # Skip scanning if all allowed devices are already connected
                if allowed_addresses.issubset(connected_addresses):
                    log("ble_main", "✅ All allowed devices are already connected. Skipping scan.", force=True)
                    await asyncio.sleep(60)
                    continue

                log("ble_main", "🔍 Start scanning for devices...", force=True)
                devices = await BleakScanner.discover()
                filtered_devices = await filter_devices(devices)

                if not filtered_devices:
                    log("ble_main", "⚠️ No new JK-BMS BLE devices found.", force=True)
                    await asyncio.sleep(15)
                    continue
                log("ble_main", F"DEVICES: {filtered_devices}", force=True)

                tasks = []
                for device in filtered_devices:
                    device_address = device.address.lower()
                    log(device.name, f"🔌 Connecting to allowed device: {device.address}", force=True)

                    # Create a connection task
                    task = asyncio.create_task(connect_and_run(device))
                    active_connections[device_address] = task  # Add to active
                    tasks.append(task)

                    await asyncio.sleep(5)  # Delay between connections

                if tasks:
                    await asyncio.gather(*tasks)  # We are waiting for all connections to be made

                # Remove completed tasks from the list of active connections
                for device_address in list(active_connections.keys()):
                    task = active_connections[device_address]
                    if task.done() or task.cancelled():
                        del active_connections[device_address]
                    elif task.exception():
                        log(device_address, f"❌ Task failed with error: {task.exception()}", force=True)
                        task.cancel()
                        del active_connections[device_address]
                
                await asyncio.sleep(20) # Waiting before the next scan

        except Exception as e:
            log("ble_main", f"❌ BLE scan error: {str(e)}", force=True)
            await asyncio.sleep(5)
                                    
def is_device_address_in_cell_info(device_address, cell_info):
    for device_data in cell_info.values():
        if device_data.get("device_address") == device_address:
            return True
    return False

async def are_all_allowed_devices_connected_and_have_data() -> bool:
    allowed_devices = db.get_all_devices()
    allowed_addresses = {device["address"].lower() for device in allowed_devices if device["enabled"]}
    connected_addresses = {device["address"].lower() for device in allowed_devices if device["connected"]}

    if not allowed_addresses.issubset(connected_addresses):
        log("CHECK DEVICES", "❌ Not all allowed devices are connected", force=True)
        return False

    cell_info = await data_store.get_cell_info()
    for device_address in allowed_addresses:
        if not is_device_address_in_cell_info(device_address, cell_info):
            log("CHECK DEVICES", f"❌ Device [{device_address}] has no data.", force=True)
            return False
    return True

def start_services():
    db.create_table()
    db.set_all_devices_disconnected()
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start_services()
