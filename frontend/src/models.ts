export interface DeviceInfo {
  device_name: string;
  device_uptime: number;
  frame_counter: number;
  frame_type: number;
  hardware_version: string;
  manufacturing_date: string;
  power_on_count: number;
  serial_number: string;
  software_version: string;
  vendor_id: string;
}

export interface Devices {
  [key: string]: DeviceInfo;
}

export interface CellInfo {
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
  total_cycle_capacity: number;
}

export interface Config {
  password: string;
  vapid_public: string;
  n_hours: number;
}

export interface Alert {
  id: number;
  device_address: string;
  device_name: string;
  error_code: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
}

export interface Device {
  address: string;
  name: string;
}

export interface DeviceInfo {
  frame_type: number;
  frame_counter: number;
  vendor_id: string;
  hardware_version: string;
  software_version: string;
  device_uptime: number;
  power_on_count: number;
  device_name: string;
  device_address: string;
  manufacturing_date: string;
  serial_number: string;
  user_data: string;
  connected: boolean;
}

export interface DeviceInfoMap {
  [deviceName: string]: DeviceInfo;
}
