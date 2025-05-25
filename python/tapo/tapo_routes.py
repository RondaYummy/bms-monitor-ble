from fastapi import APIRouter, HTTPException, Path, Depends
from python.tapo.dto import TapoDeviceCreateDto
import python.db as db
from python.auth.verify_token import verify_token
from python.tapo.tapo_service import TapoDevice

router = APIRouter()
from . import find_tapo

@router.post("/tapo/devices/add", tags=["Tapo"])
def add_tapo_device_api(device: TapoDeviceCreateDto):
    try:
        existing = db.get_tapo_device_by_ip(device.ip)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"⚠️ The device with IP {device.ip} already exists in the database."
            )
        try:
            db.insert_tapo_device(
                ip=device.ip,
                email=device.email,
                password=device.password,
                power_watt=device.power_watt,
                priority=device.priority
            )
        except Exception as conn_err:
            print(f"⚠️ Could not connect to the device {device.ip}: {conn_err}")
        return {
            "status": "added",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding: {str(e)}")

@router.get("/tapo/devices")
def get_all_tapo_devices():
    try:
        devices = db.get_all_tapo_devices()
        for device in devices:
            device.pop("password", None)
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error when receiving a list: {str(e)}")

@router.post("/tapo/devices/{ip}/on", dependencies=[Depends(verify_token)])
def turn_on_device(ip: str):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        tapo = TapoDevice(ip, device["email"], device["password"])
        status = tapo.get_status()
        name = tapo.get_name()
        info = status.get("info", {})
        tapo.turn_on()

        update_data = {
            "device_on": True,
            "name": name,
            "model": info.get("model"),
            "fw_ver": info.get("fw_ver"),
            "hw_ver": info.get("hw_ver"),
            "device_id": info.get("device_id"),
        }
        db.update_tapo_device_by_ip(ip, update_data)
        return {"status": "on", "ip": ip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ The device could not be turned on: {str(e)}")

@router.post("/tapo/devices/{ip}/off", dependencies=[Depends(verify_token)])
def turn_off_device(ip: str):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    try:
        tapo = TapoDevice(ip, device["email"], device["password"])
        status = tapo.get_status()
        name = tapo.get_name()
        info = status.get("info", {})
        tapo.turn_off()

        update_data = {
            "device_on": False,
            "name": name,
            "model": info.get("model"),
            "fw_ver": info.get("fw_ver"),
            "hw_ver": info.get("hw_ver"),
            "device_id": info.get("device_id"),
        }
        db.update_tapo_device_by_ip(ip, update_data)
        return {"status": "off", "ip": ip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ The device could not be turned off: {str(e)}")

@router.delete("/tapo/device/{ip}", dependencies=[Depends(verify_token)])
async def delete_tapo_device(ip: str = Path(..., example="192.168.31.110")):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Tapo device not found")

    success = db.delete_tapo_device_by_ip(ip)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete the Tapo device")
    
    return {"message": f"Tapo device with IP {ip} deleted successfully"}
