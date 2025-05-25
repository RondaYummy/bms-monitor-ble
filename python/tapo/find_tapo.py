from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import ipaddress
import subprocess
from concurrent.futures import ThreadPoolExecutor
from PyP100 import PyP110
from python.auth.verify_token import verify_token

MAX_WORKERS = 100

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
    except Exception:
        pass
    return None

def try_check_device(ip: str, email: str, password: str):
    try:
        device = PyP110.P110(ip, email, password)
        device.handshake()
        device.login()
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
    except Exception:
        return None

@router.post("/tapo/devices/search", dependencies=[Depends(verify_token)])
def search_tapo_devices(request: ScanRequest):
    try:
        network = ipaddress.ip_network(request.subnet)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid subnet format")

    ip_list = [str(ip) for ip in network.hosts()]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        ping_results = list(executor.map(ping, ip_list))

    alive_ips = [ip for ip in ping_results if ip]

    found_devices = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(lambda ip: try_check_device(ip, request.email, request.password), alive_ips)
        found_devices = [res for res in results if res]

    return {
        "count": len(found_devices),
        "devices": found_devices
    }
