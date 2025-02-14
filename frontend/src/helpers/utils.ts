
import { onBeforeUnmount, ref, watch } from "vue";
import { eventBus } from "../eventBus";

export const useSessionStorage = (key: string) => {
  const value = ref(sessionStorage.getItem(key));

  watch(value, (newValue) => {
    if (newValue === null || newValue === undefined) {
      sessionStorage.removeItem(key);
      sessionStorage.removeItem(`${key}_timestamp`);
    } else {
      sessionStorage.setItem(key, newValue);
      sessionStorage.setItem(`${key}_timestamp`, new Date().getTime().toString());
    }
  });

  const syncWithStorage = (event: any) => {
    if (event.key === key) {
      value.value = event.newValue;
    }
  };

  window.addEventListener("storage", syncWithStorage);

  eventBus.on("session:remove", (removedKey) => {
    console.log(removedKey, 'removedKey');
    if (removedKey === key) {
      value.value = null;
    }
  });

  onBeforeUnmount(() => {
    window.removeEventListener("storage", syncWithStorage);
    eventBus.off("session:remove");
  });

  return value;
};

export function formatDuration(seconds: number) {
  const units = [
    { label: 'p', seconds: 31536000 }, // 365 days
    { label: 'm', seconds: 2592000 }, // 30 days
    { label: 'e', seconds: 86400 }, // 24 hours
    { label: 'd', seconds: 3600 }, // 60 minutes
    { label: 'min', seconds: 60 }, // 60 seconds
    { label: 'с', seconds: 1 },
  ];

  const result = [];

  for (const unit of units) {
    const value = Math.floor(seconds / unit.seconds);
    if (value > 0) {
      result.push(`${value}${unit.label}`);
      seconds %= unit.seconds;
    }
  }

  return result.join(', ');
}

export function calculateAveragePerIndex(arrays: Array<any>) {
  if (!arrays.length || !arrays[0]?.length) return [];
  const length = arrays[0].length;
  const averages = Array(length).fill(0);
  for (let i = 0; i < length; i++) {
    let sum = 0;
    for (const array of arrays) {
      if (array[i]) {
        sum += array[i];
      }
    }
    averages[i] = sum / arrays.length;
  }

  return averages;
}

export function calculateAverage(array: any[], field: string) {
  if (array.length === 0) return 0;

  const total = array.reduce((sum, item) => sum + item[field], 0);
  return total / array.length;
}

/**
 * Calculates the battery life of the system.
 *
 * @param {number} remainingCapacity - The remaining battery charge in Ah.
 * @param {number} chargeCurrent - Current consumption in A.
 * @param {number} inverterEfficiency - Inverter efficiency (default 0.95).
 * @returns {number|string} - Battery life in hours or '∞' if consumption is 0.
 */
export function calculateAutonomyTime(remainingCapacity: number, charge_current: number, inverterEfficiency = 0.95) {
  if (charge_current >= 0) {
    return '∞';
  }

  // Consideration of inverter efficiency
  const effectiveCurrent = Math.abs(charge_current) / inverterEfficiency;

  const autonomyTime = remainingCapacity / effectiveCurrent;
  return `${autonomyTime.toFixed(2)} hrs`;
}

export function parseManufacturingDate(dateStr: string): string {
  if (!dateStr) return '';
  const year = `20${dateStr.slice(0, 2)}`; // Add 20 to the year
  const month = dateStr.slice(2, 4);
  const day = dateStr.slice(4, 6);
  return `${day}-${month}-${year}`;
}

const UNIT_MAP = {
  cell_count: "",  // Cell Count
  nominal_battery_capacity: "Ah",  // Battery Capacity
  balance_trigger_voltage: "V",  // Balance Trig. Volt.
  start_balance_voltage: "V",  // Start Balance Volt.
  max_balance_current: "A",  // Max Balance Current
  cell_ovp: "V",  // Cell OVP
  cell_request_charge_voltage: "V",  // Vol. Cell RCV
  soc_100_voltage: "V",  // SOC-100% Volt.
  cell_ovpr: "V",  // Cell OVPR
  cell_uvpr: "V",  // Cell UVPR
  soc_0_voltage: "V",  // SOC-0% Volt.
  cell_uvp: "V",  // Cell UVP
  power_off_voltage: "V",  // Power Off Voltage
  cell_request_float_voltage: "V",  // Vol. Cell RFV
  smart_sleep_voltage: "V",  // Vol. Smart Sleep
  smart_sleep: "h",  // Time Smart Sleep
  max_charge_current: "A",  // Continued Charge Current
  charge_ocp_delay: "s",  // Charge OCP Delay
  charge_ocp_recovery: "s",  // Charge OCPR Time
  max_discharge_current: "A",  // Continued Discharge Current
  discharge_ocp_delay: "s",  // Discharge OCP Delay
  discharge_ocp_recovery: "s",  // Discharge OCPR Time
  charge_otp: "°C",  // Charge OTP
  charge_otp_recovery: "°C",  // Charge OTPR
  discharge_otp: "°C",  // Discharge OTP
  discharge_otp_recovery: "°C",  // Discharge OTPR
  charge_utpr: "°C",  // Charge UTPR
  charge_utp: "°C",  // Charge UTP
  mos_otp: "°C",  // MOS OTP
  mos_otp_recovery: "°C",  // MOS OTPR
  short_circuit_protection_delay: "μs",  // SCP Delay (Мікроs)
  short_circuit_protection_recovery: "s",  // SCPR Time (s)
  device_address: "",  // Device Address
  connection_wire_resistances: "Ω",  // Con. Wire Res. (Ом)
  charge_switch: "",  // Charge (switch, no unit of measurement)
  discharge_switch: "",  // Discharge (switch, no unit of measurement)
  balancer_switch: "",  // Balance (switch, no unit of measurement)
  heating_enabled: "",  // Heating (switch, no unit of measurement)
  disable_temperature_sensors: "",  // Disable Temp. Sensor (switch)
  display_always_on: "",  // Display Always On (switch)
  special_charger: "",  // Special Charger On (switch)
  timed_stored_data: "",  // Timed Stored Data (switch)
  charging_float_mode: "",  // Charging Float Mode (switch)
  gps_heartbeat: "",  // GPS Heartbeat (switch)
  disable_pcl_module: "",  // Disable PCL Module (switch)
  port_switch: "",  // Port Switch
  precharge_time: "s",  // Precharge Time (s)
  data_field_enable_control: "",  // Data Field Enable Control
  controls_bitmask: "",  // Controls Bitmask

  // Cell info
  charging_status: "",  // Charging Status
  discharging_status: "",  // Discharging Status
  precharging_status: "",  // Precharging Status
  voltage_difference: "V",  // Voltage Difference
  average_voltage: "V",  // Average Voltage
  cell_voltages: "V",  // Cell Voltages
  cell_resistances: "Ω",  // Cell Resistances (Ом)
  power_tube_temperature: "°C",  // Power Tube Temperature
  battery_voltage: "V",  // Battery Voltage
  battery_power: "W",  // Battery Power
  charge_current: "A",  // Charge Current
  temperature_sensor_1: "°C",  // Temperature Sensor 1
  temperature_sensor_2: "°C",  // Temperature Sensor 2
  temperature_sensor_3: "°C",  // Temperature Sensor 3
  temperature_sensor_4: "°C",  // Temperature Sensor 4
  temperature_sensor_5: "°C",  // Temperature Sensor 5
  state_of_charge: "%",  // State of Charge
  remaining_capacity: "Ah",  // Remaining Capacity
  nominal_capacity: "Ah",  // Nominal Capacity
  cycle_count: "",  // Cycle Count
  total_cycle_capacity: "Ah",  // Total Cycle Capacity
  state_of_health: "%",  // State of Health
  emergency_time_countdown: "s",  // Emergency Time Countdown (s)
};

/**
 * Function to get the unit of measurement
 * @param {string} key - Name of the variable
 * @returns {string} - Unit of measurement or empty string if not
 */
type UnitMapKeys = keyof typeof UNIT_MAP;
export function getUnit(key: UnitMapKeys) {
  return UNIT_MAP[key] || "";
}
