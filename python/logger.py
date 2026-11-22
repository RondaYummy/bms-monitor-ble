"""Console logging helper used by the BLE layer (colored, optionally verbose)."""
import os
from datetime import datetime

from python.colors import BLUE, MAGENTA, RESET

# Verbose BLE logging (frame dumps etc.). Enable with BLE_DEBUG=1.
ENABLE_LOGS = os.getenv("BLE_DEBUG", "0") == "1"


def log(device_name, message, force=False):
    if ENABLE_LOGS or force:
        current_time = datetime.now().strftime("%d.%m.%y %H:%M:%S")
        print(f"{BLUE}[{device_name}] {MAGENTA}[{current_time}]{RESET} {message}")
