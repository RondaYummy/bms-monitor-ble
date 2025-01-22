export interface Device {
  average_voltage?: number;
  power_tube_temperature?: number;
  battery_voltage?: number;
  battery_power?: number;
  charge_current?: number;
  temperature_sensor_1?: number;
  temperature_sensor_2?: number;
  state_of_charge?: number;
  remaining_capacity?: number;
  nominal_capacity?: number;
  cycle_count?: number;
  state_of_health?: number;
  cell_voltages: number[];
  cell_resistances: number[];
  charging_status: number;
  discharging_status: number;
  voltage_difference: number;
}

