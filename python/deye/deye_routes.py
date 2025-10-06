from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

import python.db as db
from python.auth.verify_token import verify_token

router = APIRouter(prefix="/deye", tags=["Deye Devices"])

class DeviceToggleRequest(BaseModel):
    device_on: bool

class CreateDeyeDeviceRequest(BaseModel):
    ip: str = Field(..., description="IP address of the Deye device")
    serial_number: str = Field(..., description="Serial number of the inverter")
    slave_id: Optional[int] = Field(1, description="Modbus slave ID")
    device_on: Optional[bool] = Field(True, description="Device power state")

@router.get("/devices", summary="Get all Deye devices")
def get_all_deye_devices():
    try:
        return db.get_all_deye_devices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/device/{ip}",
    summary="Delete Deye device by IP",
    dependencies=[Depends(verify_token)]
)
def delete_deye_device(ip: str = Path(..., description="IP address of the Deye device")):
    try:
        deleted = db.delete_deye_device_by_ip(ip)
        if not deleted:
            raise HTTPException(status_code=404, detail="Device not found")
        return {"detail": f"Device {ip} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/devices/{ip}/toggle",
    summary="Toggle device_on state",
    dependencies=[Depends(verify_token)]
)
def toggle_deye_device(ip: str, body: DeviceToggleRequest):
    try:
        existing = db.get_deye_device_by_ip(ip)
        if not existing:
            raise HTTPException(status_code=404, detail="Device not found")
        # db.update_deye_device_data(ip, {"device_on": int(body.device_on)}) # TODO: update status
        return {"detail": f"Device {ip} state updated to {body.device_on}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/device",
    summary="Create new Deye device",
    dependencies=[Depends(verify_token)]
)
def create_deye_device(request: CreateDeyeDeviceRequest):
    try:
        result = db.create_deye_device(
            ip=request.ip,
            serial_number=request.serial_number,
            slave_id=request.slave_id,
            device_on=int(request.device_on)
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))