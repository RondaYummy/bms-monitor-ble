export interface DeviceInfo {
  device_name: string
  device_uptime: number
  frame_counter: number
  frame_type: number
  hardware_version: string
  manufacturing_date: string
  power_on_count: number
  serial_number: string
  software_version: string
  vendor_id: string
}

export interface Devices {
  [key: string]: DeviceInfo
}

export interface CellInfo {
  average_voltage?: number
  power_tube_temperature?: number
  battery_voltage?: number
  battery_power?: number
  charge_current?: number
  temperature_sensor_1?: number
  temperature_sensor_2?: number
  state_of_charge?: number
  remaining_capacity?: number
  nominal_capacity?: number
  cycle_count?: number
  state_of_health?: number
  cell_voltages: number[]
  cell_resistances: number[]
  charging_status: number
  discharging_status: number
  voltage_difference: number
  total_cycle_capacity: number
}

export interface SettingInfo {
  name: string // device_name
  address: string // device_address (MAC address)
  cell_count: number // Cell Count
  nominal_battery_capacity: number // Battery Capacity (Ah)
  balance_trigger_voltage: number // Balance Trigger Voltage (V)
  start_balance_voltage: number // Start Balance Voltage (V)
  max_balance_current: number // Max Balance Current (A)
  cell_ovp: number // Cell OVP (V)
  cell_request_charge_voltage: number // Vol. Cell RCV (V)
  soc_100_voltage: number // SOC-100% Voltage (V)
  cell_ovpr: number // Cell OVPR (V)
  cell_uvpr: number // Cell UCPR (V)
  soc_0_voltage: number // SOC-0% Voltage (V)
  cell_uvp: number // Cell UVP (V)
  power_off_voltage: number // Power Off Voltage (V)
  cell_request_float_voltage: number // Vol. Cell RFV (V)
  smart_sleep_voltage: number // Vol. Smart Sleep (V)
  smart_sleep: boolean // Smart Sleep (true/false)
  max_charge_current: number // Continued Charge Current (A)
  charge_ocp_delay: number // Charge OCP Delay (s)
  charge_ocp_recovery: number // Charge OCPR Time (s)
  max_discharge_current: number // Continued Discharge Current (A)
  discharge_ocp_delay: number // Discharge OCP Delay (s)
  discharge_ocp_recovery: number // Discharge OCPR Time (s)
  charge_otp: number // Charge OTP (°C)
  charge_otp_recovery: number // Charge OTPR (°C)
  discharge_otp: number // Discharge OTP (°C)
  discharge_otp_recovery: number // Discharge OTPR (°C)
  charge_utp_recovery: number // Charge UTPR (°C)
  charge_utp: number // Charge UTP (°C)
  mos_otp: number // MOS OTP (°C)
  mos_otp_recovery: number // MOS OTPR (°C)
  short_circuit_protection_delay: number // SCP Delay (μs)
  short_circuit_protection_recovery: number // SCPR Time (s)
  device_address: number // The value obtained from data[270].
  connection_wire_resistances: number[] // Connection Wire Resistances (Ω)
  charge_switch: boolean // Charge (on/off)
  discharge_switch: boolean // Discharge (on/off)
  balancer_switch: boolean // Balance (on/off)
  heating_enabled: boolean // Heating (on/off) або null
  disable_temperature_sensors: boolean // Disable Temp. Sensor
  display_always_on: boolean // Display Always On
  special_charger: boolean // Special Charger On
  timed_stored_data: boolean // Timed Stored Data
  charging_float_mode: boolean // Charging Float Mode
  gps_heartbeat: boolean // GPS Heartbeat
  disable_pcl_module: boolean // Disable PCL Module
  port_switch: string // Port Switch (e.g., "RS485" або "CAN")
  precharge_time: number // Precharge Time (s)
  data_field_enable_control: number // Data Field Enable Control
  controls_bitmask: number // Controls Bitmask
}

export interface Config {
  password: string
  vapid_public: string
  n_hours: number
}

export interface Alert {
  id: number
  device_address: string
  device_name: string
  error_code: string
  level: 'info' | 'warning' | 'error' | 'critical'
  message: string
  timestamp: string
}

export interface Device {
  address: string
  name: string
}

export interface DeviceInfo {
  frame_type: number
  frame_counter: number
  vendor_id: string
  hardware_version: string
  software_version: string
  device_uptime: number
  power_on_count: number
  name: string
  address: string
  manufacturing_date: string
  serial_number: string
  user_data: string
  connected: boolean
  id: number
  added_at: string
  enabled: boolean
}

export interface DeviceInfoMap {
  [deviceName: string]: DeviceInfo
}

export interface Config {
  password: string
  VAPID_PUBLIC_KEY: string
  n_hours: number
}

export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[]
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>
  prompt(): Promise<void>
}

export interface DeyeRealtimeData {
  id: number // Internal database ID (autoincrement)
  ip: string // Device IP address
  serial_number: string // Serial number of the inverter
  slave_id: number // Modbus slave ID (default is 1)
  timestamp: string // ISO timestamp (UTC)
  pv1_power: number // PV1 power (W)
  pv2_power: number // PV2 power (W)
  total_pv: number // Total PV power (W)
  load_power: number // Load power (W)
  grid_power: number // Power to/from the grid (W); positive = import, negative = export
  battery_power: number // Battery power (W); positive = discharge, negative = charge
  battery_voltage: number // Battery voltage (V)
  battery_soc: number // Battery state of charge (%)
  net_balance: number // Net power balance (W)
  device_on: number // Device power state; 1 = on, 0 = off
}

export interface DeyeSafeValues {
  pv1_power: number
  pv2_power: number
  total_pv: number
  load_power: number
  grid_power: number
  battery_power: number
  battery_voltage: number
  battery_soc: number
  net_balance: number
}

export interface TapoDevice {
  id: number;
  ip: string;
  email: string;
  device_on: number; // 1 = увімкнено, 0 = вимкнено
  device_id: string;
  power_watt: number;
  priority: number;
  name: string; // base64-кодоване ім'я (можна декодувати при потребі)
  model: string; // Наприклад, "P100"
  fw_ver: string; // Наприклад, "1.3.7 Build 20230711 Rel. 61904"
  hw_ver: string; // Наприклад, "1.0.0"
  added_at: string; // ISO-датастрока, наприклад "2025-05-20T01:43:17"
}