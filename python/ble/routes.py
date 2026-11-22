"""HTTP API for JK-BMS devices (connect/disconnect, scan, live data, settings and switches)."""
import asyncio
from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import python.db as db
from python.auth.verify_token import AuthContext, require_admin
from python.ble.manager import (
    active_clients,
    active_connections,
    ble_write,
    connect_and_run,
    disconnect_if_needed,
    discover_ble_devices,
    response_buffers,
)
from python.ble.protocol import BMS_SWITCH_REGISTERS, CMD_TYPE_SETTINGS, JK_BMS_OUI, create_command
from python.data_store import data_store
from python.logger import log
from python.push_notifications import send_push_notification
from python.tasks import spawn

router = APIRouter(tags=["JK-BMS"])

@router.get("/device-settings")
async def get_device_settings():
    try:
        setting_info = await data_store.get_setting_info()
        if not setting_info:
            return JSONResponse(content={"message": "No settings available yet."}, status_code=404)

        return list(setting_info.values())
    except Exception as e:
        print(f"❌ Error reading device settings: {e}")
        raise HTTPException(status_code=500, detail="Error reading device settings")

class BmsSwitchRequest(BaseModel):
    switch: Literal["charge", "discharge", "balance"]
    enabled: bool

@router.post("/device-settings/{address}/switch")
async def set_bms_switch(address: str, body: BmsSwitchRequest, ctx: AuthContext = Depends(require_admin)):
    """Turns the charge / discharge / balancer MOSFET switch of a connected JK-BMS on or off.

    After writing, the settings frame is requested again and the new state is returned only once the
    BMS itself reports it (so the UI never shows a state the BMS did not accept).
    """
    address = address.strip().lower()
    client = active_clients.get(address)
    if client is None:
        raise HTTPException(status_code=409, detail="Device is not connected")

    register, field = BMS_SWITCH_REGISTERS[body.switch]
    requested_at = await data_store.get_setting_info_updated_at(address)
    try:
        await ble_write(address, client, create_command(register, 1 if body.enabled else 0, 4))
        await asyncio.sleep(1)
        await ble_write(address, client, create_command(CMD_TYPE_SETTINGS))
    except Exception as e:
        print(f"❌ BMS write failed for {address}: {e}")
        raise HTTPException(status_code=502, detail="Failed to send the command to the BMS")

    settings = None
    for _ in range(20):  # up to ~10 s for the fresh settings frame
        await asyncio.sleep(0.5)
        if (await data_store.get_setting_info_updated_at(address) or 0) > (requested_at or 0):
            settings = await data_store.get_setting_info_by_address(address)
            break

    applied = bool(settings) and bool(settings.get(field)) == body.enabled
    name = (settings or {}).get("name") or address
    state = "увімкнено" if body.enabled else "вимкнено"
    labels = {"charge": "Заряд", "discharge": "Розряд", "balance": "Балансування"}
    print(f"🔧 BMS {name}: {body.switch} -> {body.enabled} by {ctx.username} (applied={applied})")
    if applied:
        spawn(send_push_notification("🔧 JK-BMS", f"{name}: {labels[body.switch]} {state} ({ctx.username})"))
    return {"applied": applied, "confirmed": settings is not None, "settings": settings}

class DeviceRequest(BaseModel):
    address: str
    name: Optional[str] = None

@router.post("/disconnect-device")
async def disconnect_device(body: DeviceRequest = Body(...), ctx: AuthContext = Depends(require_admin)):
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
        response_buffers.pop(device_address, None)
        
        log(device_name, f"✅ Successfully disconnected and disabled the device.")
        return {"message": f"✅ Successfully disconnected from {device_address} and disabled the device."}

    except Exception as e:
        log(device_name, f"❌ BLE disconnect failed: {e}", force=True)
        db.update_device_status(device_address, connected=False, enabled=False)
        raise HTTPException(status_code=500, detail=f"❌ Error disconnecting device: {str(e)}")


@router.post("/connect-device")
async def connect_device(request: DeviceRequest, ctx: AuthContext = Depends(require_admin)):
    try:
        device_address = request.address.strip().lower()
        device_name = request.name.strip() if request.name else device_address

        if not device_address:
            raise HTTPException(status_code=400, detail="Device address is required.")

        await disconnect_if_needed(device_address)
        log("/api/connect-device", f"🔍 Scanning for device {device_address}...", force=True)

        devices = await discover_ble_devices()
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
        existing_task = active_connections.get(device_address)
        if not existing_task or existing_task.done():
            active_connections[device_address] = spawn(connect_and_run(found_device))

        return JSONResponse(content={"message": f"🚀 Connection initiated for {device_address}. Check logs for updates."}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error connecting to device: {e}")
        return JSONResponse(content={"error": "❌ Error connecting to device."}, status_code=500)

@router.get("/devices", dependencies=[Depends(require_admin)])
async def discover_devices():
    try:
        log("API", "🔍 Scanning for new devices...")
        devices = await discover_ble_devices()

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
        print(f"❌ Error searching for devices: {e}")
        raise HTTPException(status_code=500, detail="❌ Error searching for devices.")

@router.get("/device-info")
async def get_device_info():
    data = db.get_all_devices()
    if not data:
        return JSONResponse(content={"message": "No device info available yet."}, status_code=404)
    return data

@router.get("/cell-info")
async def get_cell_info():
    cell_info_data = await data_store.get_cell_info()
    if not cell_info_data:
        return JSONResponse(content={"message": "No cell info available yet."}, status_code=404)
    return cell_info_data
