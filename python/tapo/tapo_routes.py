from fastapi import APIRouter, HTTPException
from dto import TapoDeviceCreateDto
import python.db as db
from python.tapo.tapo_service import TapoDevice
from fastapi import (
    Depends,
)

router = APIRouter()

@router.post("/tapo/devices/add", dependencies=[Depends(verify_token)])
def add_tapo_device_api(device: TapoDeviceCreateDto):
    try:
        try:
            tapo = TapoDevice(device.ip, device.email, device.password)
            info = tapo.get_info()

            added = db.insert_tapo_device(
                ip=device.ip,
                email=device.email,
                password=device.password
            )
            db.update_tapo_device_by_ip(device.ip, info)
        except Exception as conn_err:
            print(f"⚠️ Не вдалося підключитись до пристрою {device.ip}: {conn_err}")

        return {
            "status": "added",
            "device": db.get_tapo_device_by_ip(device.ip)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при додаванні: {str(e)}")

@router.get("/tapo/devices")
def get_all_tapo_devices():
    try:
        devices = db.get_all_tapo_devices()

        for device in devices:
            device.pop("password", None)
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Помилка при отриманні списку: {str(e)}")

@router.post("/tapo/devices/{ip}/on", dependencies=[Depends(verify_token)])
def turn_on_device(ip: str):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Пристрій не знайдено")
    try:
        tapo = TapoDevice(ip, device["email"], device["password"])
        tapo.turn_on()
        db.update_tapo_device_by_ip(ip, {"device_on": True})
        return {"status": "on", "ip": ip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Не вдалося увімкнути пристрій: {str(e)}")

@router.post("/tapo/devices/{ip}/off", dependencies=[Depends(verify_token)])
def turn_off_device(ip: str):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Пристрій не знайдено")
    try:
        tapo = TapoDevice(ip, device["email"], device["password"])
        tapo.turn_off()
        db.update_tapo_device_by_ip(ip, {"device_on": False})
        return {"status": "off", "ip": ip}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Не вдалося вимкнути пристрій: {str(e)}")