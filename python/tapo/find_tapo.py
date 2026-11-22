import ipaddress
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from PyP100 import PyP110

import python.db as db
from python.auth.verify_token import verify_token

MAX_WORKERS = 100
MAX_SCAN_HOSTS = 1024  # e.g. a /22 — prevents scanning (and DoS-ing) huge ranges like 10.0.0.0/8

router = APIRouter()

class ScanRequest(BaseModel):
    email: str
    password: str
    subnet: str = "192.168.31.0/24"

def ping(ip):
    try:
        result = subprocess.run(["ping", "-c", "1", "-W", "1", str(ip)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            return ip
    except Exception as e:
        print(f"⚠️ Ping exception for {ip}: {e}")
    return None

def try_check_device(ip: str, email: str, password: str):
    try:
        device = PyP110.P110(ip, email, password)
        # See more: https://github.com/almottier/TapoP100?tab=readme-ov-file#plugs---p100-p105-etc
        # device.handshake() # DEPRECATED
        # device.login() # DEPRECATED
        info = device.getDeviceInfo()
        name = device.getDeviceName()
        model = info.get("model", "Unknown")

        return {
            "ip": ip,
            "model": model,
            "name": name,
            "device_id": info.get("device_id"),
            "fw_ver": info.get("fw_ver"),
            "hw_ver": info.get("hw_ver"),
        }
    except Exception as e:
        return None

@router.post("/tapo/devices/search", dependencies=[Depends(verify_token)])
def search_tapo_devices(request: ScanRequest):
    print(f"🌐 Tapo scan in subnet: {request.subnet}")

    try:
        network = ipaddress.ip_network(request.subnet.strip(), strict=False)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subnet format")

    if network.version != 4 or not network.is_private or network.num_addresses > MAX_SCAN_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Only private IPv4 subnets up to {MAX_SCAN_HOSTS} addresses (e.g. /22) can be scanned",
        )

    ip_list = [str(ip) for ip in network.hosts()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        ping_results = list(executor.map(ping, ip_list))

    alive_ips = [ip for ip in ping_results if ip]

    found_devices = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(lambda ip: try_check_device(ip, request.email, request.password), alive_ips)
        found_devices = [res for res in results if res]

    print(f"✅ Found {len(found_devices)} Tapo device(s)")

    new_devices = []
    for d in found_devices:
        existing = db.get_tapo_device_by_ip(d["ip"])
        if existing:
            print(f"🔁 {d['ip']} вже існує в базі, пропускаємо")
        else:
            new_devices.append(d)
    return {
        "count": len(new_devices),
        "devices": new_devices
    }
