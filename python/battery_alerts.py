from datetime import datetime, timedelta, timezone
from typing import List, TypedDict

import yaml

import python.db as db
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

def add_alert(alerts, code):
    # Copy: never mutate the shared error_codes dictionary.
    alert = dict(error_codes[int(code)])
    alert["id"] = int(code)
    alerts.append(alert)

async def evaluate_alerts(device_address: str, device_name: str, cell_info: CellInfo):
    if datetime.now(timezone.utc) < SEND_ALLOWED_AFTER:
        return
    try:
        alerts = []

        if cell_info["state_of_charge"] < 10:
            add_alert(alerts, "1001")
        elif cell_info["state_of_charge"] < 20:
            add_alert(alerts, "1002")
        elif cell_info["state_of_charge"] < 30 and cell_info["charging_status"] == 0:
            add_alert(alerts, "1003")

        if cell_info["voltage_difference"] > 0.1:
            add_alert(alerts, "1004")
        elif cell_info["voltage_difference"] > 0.05:
            add_alert(alerts, "1005")

        if cell_info["average_voltage"] < 3.0:
            add_alert(alerts, "1006")
        elif cell_info["average_voltage"] < 3.2:
            add_alert(alerts, "1007")
        elif cell_info["average_voltage"] > 4.3:
            add_alert(alerts, "1008")
        elif cell_info["average_voltage"] > 4.2:
            add_alert(alerts, "1009")

        max_temp = max(
            cell_info["temperature_sensor_1"],
            cell_info["temperature_sensor_2"],
            cell_info["temperature_sensor_3"],
            cell_info["temperature_sensor_4"],
            cell_info["temperature_sensor_5"]
        )
        if max_temp > 60:
            add_alert(alerts, "1010")
        elif max_temp > 50:
            add_alert(alerts, "1011")

        if cell_info["charge_current"] > 100:
            add_alert(alerts, "1012")
        elif cell_info["charge_current"] > 80:
            add_alert(alerts, "1013")
        elif cell_info["charge_current"] < -100:
            add_alert(alerts, "1014")
        elif cell_info["charge_current"] < -80:
            add_alert(alerts, "1015")

        # The stricter threshold must be checked first, otherwise 1017 could never fire.
        if cell_info["state_of_health"] < 80:
            add_alert(alerts, "1017")
        elif cell_info["state_of_health"] < 90:
            add_alert(alerts, "1016")

        max_resistance = max(cell_info["cell_resistances"], default=0)
        if max_resistance > 0.5:
            add_alert(alerts, "1018")
        elif max_resistance > 0.3:
            add_alert(alerts, "1019")

        if cell_info["battery_voltage"] > 55:
            add_alert(alerts, "1020")
        elif cell_info["battery_voltage"] > 51:
            add_alert(alerts, "1021")
        elif cell_info["battery_voltage"] < 41:
            add_alert(alerts, "1022")
        elif cell_info["battery_voltage"] < 43:
            add_alert(alerts, "1023")

        # Countdown is in seconds and 0 means "no emergency" — previously 0 triggered 1024 permanently.
        emergency_countdown = cell_info["emergency_time_countdown"]
        if 0 < emergency_countdown < 5 * 60:
            add_alert(alerts, "1024")
        elif 0 < emergency_countdown < 10 * 60:
            add_alert(alerts, "1025")

        if cell_info["cycle_count"] > 2000:
            add_alert(alerts, "1026")
        elif cell_info["cycle_count"] > 1500:
            add_alert(alerts, "1027")

        if not alerts:
            return alerts

        config = db.get_config() or {}
        n_hours = config.get("n_hours") or 12
        for alert in alerts:
            alert_id = int(alert["id"])
            # One failing/duplicate alert must not stop the others from being processed.
            try:
                is_new = db.insert_alert_data(device_address, device_name, alert_id, datetime.now(), n_hours)
                if is_new:
                    await send_push_alerts(device_name, {"id": alert_id, "message": error_codes[alert_id]["message"]}, config)
            except Exception as e:
                print(f"❌ Failed to process alert {alert_id} for {device_name}: {e}")

        return alerts
    except Exception as e:
        print(f"❌ evaluate_alerts error for {device_name}: {e}")
