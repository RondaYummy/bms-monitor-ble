from fastapi import APIRouter, Depends, HTTPException, Path
import asyncio
import time

import python.db as db
from python.auth.verify_token import verify_token
from python.tapo.dto import TapoDeviceCreateDto, TapoDeviceUpdateDto, TimerRequestDto
from python.tapo.tapo_service import TapoDevice, schedule_turn_off_worker, scheduled_off_tasks, scheduled_tasks_lock

router = APIRouter(prefix="/tapo", tags=["TP-Link Tapo Devices"])

@router.post("/devices/add", dependencies=[Depends(verify_token)])
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

@router.get("/devices")
def get_all_tapo_devices():
    try:
        devices = db.get_all_tapo_devices()
        now = time.time()
        result = []

        for device in devices:
            device.pop("password", None)
            ip = device.get("ip")
            entry = scheduled_off_tasks.get(ip)
            timer_enabled = bool(entry)
            timer_time_left = 0

            if entry:
                execute_at = entry.get("execute_at", now)
                timer_time_left = max(0, int((execute_at - now) / 60))

            device["timer"] = timer_enabled
            device["timerTimeLeft"] = timer_time_left
            result.append(device)
        
        return {"devices": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error when receiving a list: {str(e)}")

@router.post("/devices/{ip}/on", dependencies=[Depends(verify_token)])
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

@router.post("/devices/{ip}/off", dependencies=[Depends(verify_token)])
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

async def safe_turn_on(ip: str, tapo: TapoDevice):
    try:
        await asyncio.get_running_loop().run_in_executor(None, tapo.turn_on)
    except Exception as e:
        logger.warning(f"Ignored error while turning on Tapo {ip}: {e}")

@router.post("/devices/{ip}/off/timer", dependencies=[Depends(verify_token)])
async def turn_off_device_timer(ip: str, body: TimerRequestDto):
    minutes = body.timer
    seconds = minutes * 60

    now = time.time()
    execute_at = now + seconds

    async with scheduled_tasks_lock:
        if ip in scheduled_off_tasks:
            return {
                "status": "already_scheduled",
                "ip": ip,
                "timer_minutes": scheduled_off_tasks[ip].get("timer_minutes"),
                "execute_at": scheduled_off_tasks[ip].get("execute_at"),
            }

        device = db.get_tapo_device_by_ip(ip)
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")

        entry = {
            "task": None,
            "scheduled_at": now,
            "execute_at": execute_at,
            "timer_minutes": minutes,
        }
        scheduled_off_tasks[ip] = entry
        
        loop = asyncio.get_running_loop()
        tapo = TapoDevice(ip, device["email"], device["password"])
        asyncio.create_task(safe_turn_on(ip, tapo))

        task = asyncio.create_task(schedule_turn_off_worker(ip))
        
        entry["task"] = task

    return {"status": "timer-activated", "ip": ip, "timer_minutes": minutes, "execute_at": execute_at}

@router.delete("/devices/{ip}/off/timer", dependencies=[Depends(verify_token)])
async def cancel_turn_off_timer(ip: str):
    async with scheduled_tasks_lock:
        entry = scheduled_off_tasks.get(ip)
        if not entry:
            raise HTTPException(status_code=404, detail=f"No scheduled timer for device {ip}")

        task: asyncio.Task = entry.get("task")
        if task and not task.done():
            task.cancel()
        scheduled_off_tasks.pop(ip, None)

    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    loop = asyncio.get_running_loop()
    tapo = TapoDevice(ip, device["email"], device["password"])
    await loop.run_in_executor(None, tapo.turn_off)

    return {"status": "cancelled", "ip": ip}

@router.delete("/device/{ip}", dependencies=[Depends(verify_token)])
async def delete_tapo_device(ip: str = Path(..., example="192.168.31.110")):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Tapo device not found")

    success = db.delete_tapo_device_by_ip(ip)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete the Tapo device")
    
    return {"message": f"Tapo device with IP {ip} deleted successfully"}

@router.patch("/device/{ip}", dependencies=[Depends(verify_token)])
def update_tapo_device_config(ip: str, update_data: TapoDeviceUpdateDto):
    device = db.get_tapo_device_by_ip(ip)
    if not device:
        raise HTTPException(status_code=404, detail="Tapo device not found")
    
    try:
        updated_device = db.update_tapo_device_config_by_ip(ip, update_data.dict(exclude_unset=True))
        return {
            "message": f"Device {ip} updated successfully",
            "device": {k: v for k, v in updated_device.items() if k != "password"}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Failed to update device: {e}")

@router.get("/devices/top")
def get_top_priority_devices():
    try:
        devices = db.get_top_priority_tapo_devices()
        now = time.time()
        result = []

        for device in devices:
            device.pop("password", None)

            ip = device.get("ip")
            entry = scheduled_off_tasks.get(ip)

            timer_enabled = bool(entry)
            timer_time_left = 0

            if entry:
                execute_at = entry.get("execute_at", now)
                timer_time_left = max(0, int((execute_at - now) / 60))

            device["timer"] = timer_enabled
            device["timerTimeLeft"] = timer_time_left

            result.append(device)
            
        return {"top_devices": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Failed to retrieve top devices: {e}")
