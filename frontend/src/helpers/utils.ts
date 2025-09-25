import { onBeforeUnmount, ref, watch } from 'vue';
import { eventBus } from '../eventBus';
import { copyToClipboard, Notify } from 'quasar';

export const useSessionStorage = (key: string) => {
  const value = ref(localStorage.getItem(key));

  watch(value, (newValue) => {
    if (newValue === null || newValue === undefined) {
      localStorage.removeItem(key);
      localStorage.removeItem(`${key}_timestamp`);
    } else {
      localStorage.setItem(key, newValue);
      localStorage.setItem(`${key}_timestamp`, new Date().getTime().toString());
    }
  });

  const syncWithStorage = (event: any) => {
    if (event.key === key) {
      value.value = event.newValue;
    }
  };

  window.addEventListener('storage', syncWithStorage);

  eventBus.on('session:remove', (removedKey) => {
    if (removedKey === key) {
      value.value = null;
    }
  });

  onBeforeUnmount(() => {
    window.removeEventListener('storage', syncWithStorage);
    eventBus.off('session:remove');
  });

  return value;
};

export function formatDuration(seconds: number) {
  const units = [
    { label: 'y', seconds: 31536000 }, // 1 year = 365 days
    { label: 'm', seconds: 2592000 }, // 1 month = 30 days
    { label: 'd', seconds: 86400 }, // 1 day = 24 hours
    { label: 'h', seconds: 3600 }, // 1 hour = 60 minutes
    { label: 'min', seconds: 60 }, // 1 minute = 60 seconds
    { label: 's', seconds: 1 }, // 1 second
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
export function calculateAutonomyTime(
  remainingCapacity: number,
  charge_current: number,
  inverterEfficiency = 0.95
) {
  if (charge_current >= 0) {
    return '∞';
  }
  // Consideration of inverter efficiency
  const effectiveCurrent = Math.abs(charge_current) / inverterEfficiency;
  const autonomyTime = remainingCapacity / effectiveCurrent;
  return `${autonomyTime.toFixed(2)} hrs`;
}

/**
 * Calculates the estimated time to fully charge the battery (formatted as H hrs M mins).
 *
 * @param {number} batteryVoltage - Battery voltage in V.
 * @param {number} nominalCapacity - Total (nominal) capacity of the battery in Ah.
 * @param {number} remainingCapacity - Current remaining capacity of the battery in Ah.
 * @param {number} chargePower - Charging power in W (positive value).
 * @param {number} chargerEfficiency - Charger/inverter efficiency (default 0.95).
 * @returns {string} - Estimated charging time (e.g. "2 hrs 30 mins") or "0 hrs" if battery is already full.
 */
export function calculateChargeTime(
  batteryVoltage: number,
  nominalCapacity: number,
  remainingCapacity: number,
  chargePower: number,
  chargerEfficiency = 0.95
): string {
  // Скільки Ah ще треба дозарядити
  const missingCapacityAh = nominalCapacity - remainingCapacity;
  if (missingCapacityAh <= 0) {
    return '0 h (already full)';
  }

  // Скільки кВт·год не вистачає
  const missingEnergyKWh = (batteryVoltage * missingCapacityAh) / 1000;

  // Ефективна потужність заряду з урахуванням ККД (в кВт)
  const effectiveChargePower = (chargePower * chargerEfficiency) / 1000;
  if (effectiveChargePower <= 0) {
    return '∞ (no charging)';
  }

  // Час у годинах
  const chargingTimeHours = missingEnergyKWh / effectiveChargePower;

  // Форматування у години + хвилини
  const hours = Math.floor(chargingTimeHours);
  const minutes = Math.round((chargingTimeHours - hours) * 60);

  if (hours === 0 && minutes === 0) return 'менше хвилини';
  if (hours === 0) return `${minutes} m`;
  if (minutes === 0) return `${hours} h`;

  return `${hours} hrs ${minutes} m`;
}

export function parseManufacturingDate(dateStr: string): string {
  if (!dateStr) return '';
  const year = `20${dateStr.slice(0, 2)}`; // Add 20 to the year
  const month = dateStr.slice(2, 4);
  const day = dateStr.slice(4, 6);
  return `${day}-${month}-${year}`;
}

export function sortDevices<T extends { name: string }>(arr: T[]): T[] {
  return arr?.sort((a, b) => b.name.localeCompare(a.name));
}

const UNIT_MAP = {
  cell_count: { value: '', title: 'Cell Count' },
  nominal_battery_capacity: { value: 'Ah', title: 'Battery Capacity' },
  balance_trigger_voltage: { value: 'V', title: 'Balance Trig. Volt.' },
  start_balance_voltage: { value: 'V', title: 'Start Balance Volt.' },
  max_balance_current: { value: 'A', title: 'Max Balance Current' },
  cell_ovp: { value: 'V', title: 'Cell OVP' },
  cell_request_charge_voltage: { value: 'V', title: 'Vol. Cell RCV' },
  soc_100_voltage: { value: 'V', title: 'SOC-100% Volt.' },
  cell_ovpr: { value: 'V', title: 'Cell OVPR' },
  cell_uvpr: { value: 'V', title: 'Cell UVPR' },
  soc_0_voltage: { value: 'V', title: 'SOC-0% Volt.' },
  cell_uvp: { value: 'V', title: 'Cell UVP' },
  power_off_voltage: { value: 'V', title: 'Power Off Voltage' },
  cell_request_float_voltage: { value: 'V', title: 'Vol. Cell RFV' },
  smart_sleep_voltage: { value: 'V', title: 'Vol. Smart Sleep' },
  smart_sleep: { value: 'h', title: 'Time Smart Sleep' },
  max_charge_current: { value: 'A', title: 'Continued Charge Current' },
  charge_ocp_delay: { value: 's', title: 'Charge OCP Delay' },
  charge_ocp_recovery: { value: 's', title: 'Charge OCPR Time' },
  max_discharge_current: { value: 'A', title: 'Continued Discharge Current' },
  discharge_ocp_delay: { value: 's', title: 'Discharge OCP Delay' },
  discharge_ocp_recovery: { value: 's', title: 'Discharge OCPR Time' },
  charge_otp: { value: '°C', title: 'Charge OTP' },
  charge_otp_recovery: { value: '°C', title: 'Charge OTPR' },
  discharge_otp: { value: '°C', title: 'Discharge OTP' },
  discharge_otp_recovery: { value: '°C', title: 'Discharge OTPR' },
  charge_utpr: { value: '°C', title: 'Charge UTPR' },
  charge_utp: { value: '°C', title: 'Charge UTP' },
  mos_otp: { value: '°C', title: 'MOS OTP' },
  mos_otp_recovery: { value: '°C', title: 'MOS OTPR' },
  short_circuit_protection_delay: { value: 'μs', title: 'SCP Delay (Мікроs)' },
  short_circuit_protection_recovery: { value: 's', title: 'SCPR Time (s)' },
  device_address: { value: '', title: 'Device Address' },
  connection_wire_resistances: { value: 'mΩ', title: 'Con. Wire Res.' },
  charge_switch: { value: '', title: 'Charge (switch, no unit of measurement)' },
  discharge_switch: { value: '', title: 'Discharge (switch, no unit of measurement)' },
  balancer_switch: { value: '', title: 'Balance (switch, no unit of measurement)' },
  heating_enabled: { value: '', title: 'Heating (switch, no unit of measurement)' },
  disable_temperature_sensors: { value: '', title: 'Disable Temp. Sensor (switch)' },
  display_always_on: { value: '', title: 'Display Always On (switch)' },
  special_charger: { value: '', title: 'Special Charger On (switch)' },
  timed_stored_data: { value: '', title: 'Timed Stored Data (switch)' },
  charging_float_mode: { value: '', title: 'Charging Float Mode (switch)' },
  gps_heartbeat: { value: '', title: 'GPS Heartbeat (switch)' },
  disable_pcl_module: { value: '', title: 'Disable PCL Module (switch)' },
  port_switch: { value: '', title: 'Port Switch' },
  precharge_time: { value: 's', title: 'Precharge Time (s)' },
  data_field_enable_control: { value: '', title: 'Data Field Enable Control' },
  controls_bitmask: { value: '', title: 'Controls Bitmask' },

  // Cell info
  charging_status: { value: '', title: 'Charging Status' },
  discharging_status: { value: '', title: 'Discharging Status' },
  precharging_status: { value: '', title: 'Precharging Status' },
  voltage_difference: { value: 'V', title: 'Voltage Difference' },
  average_voltage: { value: 'V', title: 'Average Voltage' },
  cell_voltages: { value: 'V', title: 'Cell Voltages' },
  cell_resistances: { value: 'Ω', title: 'Cell Resistances (Ом)' },
  power_tube_temperature: { value: '°C', title: 'Power Tube Temperature' },
  battery_voltage: { value: 'V', title: 'Battery Voltage' },
  battery_power: { value: 'W', title: 'Battery Power' },
  charge_current: { value: 'A', title: 'Charge Current' },
  temperature_sensor_1: { value: '°C', title: 'Temperature Sensor 1' },
  temperature_sensor_2: { value: '°C', title: 'Temperature Sensor 2' },
  temperature_sensor_3: { value: '°C', title: 'Temperature Sensor 3' },
  temperature_sensor_4: { value: '°C', title: 'Temperature Sensor 4' },
  temperature_sensor_5: { value: '°C', title: 'Temperature Sensor 5' },
  state_of_charge: { value: '%', title: 'State of Charge' },
  remaining_capacity: { value: 'Ah', title: 'Remaining Capacity' },
  nominal_capacity: { value: 'Ah', title: 'Nominal Capacity' },
  cycle_count: { value: '', title: 'Cycle Count' },
  total_cycle_capacity: { value: 'Ah', title: 'Total Cycle Capacity' },
  state_of_health: { value: '%', title: 'State of Health' },
  emergency_time_countdown: { value: 's', title: 'Emergency Time Countdown (s)' },
};

/**
 * Function to get the unit of measurement
 * @param {string} key - Name of the variable
 * @returns {string} - Unit of measurement or empty string if not
 */
type UnitMapKeys = keyof typeof UNIT_MAP;

export function getUnit(key: UnitMapKeys): string {
  const unit = UNIT_MAP[key];
  return `${unit.title} ${unit.value}: `;
}

export function formatTimestamp(timestamp?: any): string {
  if (!timestamp) {
    return 'Invalid timestamp';
  }

  const cleanTimestamp = timestamp.split('.')[0];
  const date = new Date(cleanTimestamp.replace(' ', 'T'));

  if (isNaN(date.getTime())) {
    return 'Invalid date';
  }

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0'); // Months from 0 to 11
  const year = String(date.getFullYear()).slice(2); // Last two digits of the year
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${day}.${month}.${year} ${hours}.${minutes}`;
}

export function getAlertIcon(level: string | undefined): string {
  if (level === 'info') return 'priority_high';
  if (level === 'warning') return 'warning';
  if (level === 'error') return 'error';
  if (level === 'critical') return 'flash_on';
  return '';
}

export function isInstalled() {
  return window?.matchMedia('(display-mode: standalone)')?.matches;
}

export async function copy(value: string | number) {
  copyToClipboard(String(value))
    .then(() => {
      Notify.create({
        message: 'Успішно скопійовано.',
        color: 'green',
        position: 'top',
        timeout: 1000,
      });
    })
    .catch(() => {
      Notify.create({
        message: 'Сталася помилка під час копіювання.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      });
    });
}
