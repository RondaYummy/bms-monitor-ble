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
