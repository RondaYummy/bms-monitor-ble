from datetime import datetime, timedelta, timezone
from typing import List, TypedDict

import yaml

import python.db as db
from python.alert_thresholds import get_thresholds, render_message
from python.push_notifications import send_push_alerts

with open('configs/error_codes.yaml', 'r', encoding='utf-8') as file:
    error_codes = yaml.safe_load(file)

SEND_ALLOWED_AFTER: datetime = datetime.now(timezone.utc) + timedelta(minutes=3)

class CellInfo(TypedDict):
    device_address: str
    charging_status: int
    discharging_status: int
    precharging_status: int
    voltage_difference: float
    average_voltage: float
    cell_voltages: List[float]
    cell_resistances: List[float]
    power_tube_temperature: float
    battery_voltage: float
    battery_power: float
    charge_current: float
    temperature_sensor_1: float
    temperature_sensor_2: float
    temperature_sensor_3: float
    temperature_sensor_4: float
    temperature_sensor_5: float
    state_of_charge: int
    remaining_capacity: float
    nominal_capacity: float
    cycle_count: int
    total_cycle_capacity: float
    state_of_health: int
    emergency_time_countdown: int

def add_alert(alerts, code, disabled_codes=()):
    code = int(code)
    if code in disabled_codes:
        return
    # Copy: never mutate the shared error_codes dictionary.
    alert = dict(error_codes[code])
    alert["id"] = code
    alerts.append(alert)

def collect_alerts(cell_info: CellInfo, t: dict) -> list:
    """Pure function: which alert codes the current cell info triggers for the given thresholds."""
    alerts = []
    disabled = set(t.get("disabled_codes") or [])
    add = lambda code: add_alert(alerts, code, disabled)

    soc = cell_info["state_of_charge"]
    if soc < t["soc_critical"]:
        add(1001)
    elif soc < t["soc_error"]:
        add(1002)
    elif soc < t["soc_warning_no_charge"] and cell_info["charging_status"] == 0:
        add(1003)

    if cell_info["voltage_difference"] > t["cell_diff_critical"]:
        add(1004)
    elif cell_info["voltage_difference"] > t["cell_diff_error"]:
        add(1005)

    avg = cell_info["average_voltage"]
    if avg < t["avg_cell_low_critical"]:
        add(1006)
    elif avg < t["avg_cell_low_error"]:
        add(1007)
    elif avg > t["avg_cell_high_critical"]:
        add(1008)
    elif avg > t["avg_cell_high_error"]:
        add(1009)

    max_temp = max(cell_info[f"temperature_sensor_{i}"] for i in range(1, 6))
    if max_temp > t["temp_critical"]:
        add(1010)
    elif max_temp > t["temp_error"]:
        add(1011)

    current = cell_info["charge_current"]
    if current > t["charge_current_critical"]:
        add(1012)
    elif current > t["charge_current_error"]:
        add(1013)
    elif current < -t["discharge_current_critical"]:
        add(1014)
    elif current < -t["discharge_current_error"]:
        add(1015)

    # The stricter threshold must be checked first.
    if cell_info["state_of_health"] < t["soh_critical"]:
        add(1017)
    elif cell_info["state_of_health"] < t["soh_error"]:
        add(1016)

    max_resistance = max(cell_info["cell_resistances"], default=0)
    if max_resistance > t["resistance_critical"]:
        add(1018)
    elif max_resistance > t["resistance_error"]:
        add(1019)

    pack = cell_info["battery_voltage"]
    if pack > t["pack_high_critical"]:
        add(1020)
    elif pack > t["pack_high_error"]:
        add(1021)
    elif pack < t["pack_low_critical"]:
        add(1022)
    elif pack < t["pack_low_error"]:
        add(1023)

    # Countdown is in seconds and 0 means "no emergency".
    countdown = cell_info["emergency_time_countdown"]
    if 0 < countdown < t["emergency_critical_min"] * 60:
        add(1024)
    elif 0 < countdown < t["emergency_error_min"] * 60:
        add(1025)

    if cell_info["cycle_count"] > t["cycles_high"]:
        add(1026)
    elif cell_info["cycle_count"] > t["cycles_warning"]:
        add(1027)

    return alerts

async def evaluate_alerts(device_address: str, device_name: str, cell_info: CellInfo):
    if datetime.now(timezone.utc) < SEND_ALLOWED_AFTER:
        return
    try:
        thresholds = get_thresholds()
        alerts = collect_alerts(cell_info, thresholds)
        if not alerts:
            return alerts

        config = db.get_config() or {}
        n_hours = config.get("n_hours") or 12
        for alert in alerts:
            alert_id = int(alert["id"])
            # One failing/duplicate alert must not stop the others from being processed.
            try:
                message = render_message(error_codes[alert_id]["message"], thresholds)
                is_new = db.insert_alert_data(device_address, device_name, alert_id, datetime.now(), n_hours, message)
                if is_new:
                    await send_push_alerts(device_name, {"id": alert_id, "message": message}, config)
                    _publish_live_alert(device_name, alert_id, message, alert.get("level"))
            except Exception as e:
                print(f"❌ Failed to process alert {alert_id} for {device_name}: {e}")

        return alerts
    except Exception as e:
        print(f"❌ evaluate_alerts error for {device_name}: {e}")

def _publish_live_alert(device_name, code, message, level):
    try:
        from python.live import hub  # local import: live.py imports modules that import this one
        hub.publish("alert", {"device_name": device_name, "code": code, "message": message, "level": level})
    except Exception as e:
        print(f"⚠️ Live alert publish failed: {e}")
