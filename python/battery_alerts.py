from typing import TypedDict, List, Dict, Any
import json
import os

file_path = os.path.join("configs", "error_codes.json")
def load_error_codes(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            error_codes = json.load(file)
        return error_codes
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: Failed to decode JSON - {e}")
        return {}
    
error_codes = load_error_codes(file_path)

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

async def evaluate_alerts(device_name: str, cell_info: CellInfo):
    try:
        alerts = []
        print(f"error_codes: {error_codes}")

        if cell_info["state_of_charge"] < 10:
            alerts.append(error_codes["1001"])
        elif cell_info["state_of_charge"] < 20:
            alerts.append(error_codes["1002"])
        elif cell_info["state_of_charge"] < 30 and cell_info["charging_status"] == 0:
            alerts.append(error_codes["1003"])

        if cell_info["voltage_difference"] > 0.1:
            alerts.append(error_codes["1004"])
        elif cell_info["voltage_difference"] > 0.05:
            alerts.append(error_codes["1005"])

        if cell_info["average_voltage"] < 3.0:
            alerts.append(error_codes["1006"])
        elif cell_info["average_voltage"] < 3.2:
            alerts.append(error_codes["1007"])
        elif cell_info["average_voltage"] > 4.2:
            alerts.append(error_codes["1008"])
        elif cell_info["average_voltage"] > 4.1:
            alerts.append(error_codes["1009"])

        max_temp = max(
            cell_info["temperature_sensor_1"],
            cell_info["temperature_sensor_2"],
            cell_info["temperature_sensor_3"],
            cell_info["temperature_sensor_4"],
            cell_info["temperature_sensor_5"]
        )
        if max_temp > 60:
            alerts.append(error_codes["1010"])
        elif max_temp > 50:
            alerts.append(error_codes["1011"])

        if cell_info["charge_current"] > 100:
            alerts.append(error_codes["1012"])
        elif cell_info["charge_current"] > 80:
            alerts.append(error_codes["1013"])
        elif cell_info["charge_current"] < -100:
            alerts.append(error_codes["1014"])
        elif cell_info["charge_current"] < -80:
            alerts.append(error_codes["1015"])

        if cell_info["state_of_health"] < 90:
            alerts.append(error_codes["1016"])
        elif cell_info["state_of_health"] < 80:
            alerts.append(error_codes["1017"])

        if max(cell_info["cell_resistances"]) > 0.5:
            alerts.append(error_codes["1018"])
        elif max(cell_info["cell_resistances"]) > 0.3:
            alerts.append(error_codes["1019"])

        if cell_info["battery_voltage"] > 60:
            alerts.append(error_codes["1020"])
        elif cell_info["battery_voltage"] > 58:
            alerts.append(error_codes["1021"])
        elif cell_info["battery_voltage"] < 40:
            alerts.append(error_codes["1022"])
        elif cell_info["battery_voltage"] < 44:
            alerts.append(error_codes["1023"])

        if cell_info["emergency_time_countdown"] < 5:
            alerts.append(error_codes["1024"])
        elif cell_info["emergency_time_countdown"] < 10:
            alerts.append(error_codes["1025"])

        for alert in alerts:
            print(f"[{device_name}] ALERT: {alert['message']}", force=True)

        return alerts
    except Exception as e:
        pass
        # print(f"Error EA: {str(e)}")
