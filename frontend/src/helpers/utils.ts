
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
    { label: 'р', seconds: 31536000 }, // 365 днів
    { label: 'м', seconds: 2592000 }, // 30 днів
    { label: 'д', seconds: 86400 }, // 24 години
    { label: 'г', seconds: 3600 }, // 60 хвилин
    { label: 'хв', seconds: 60 }, // 60 секунд
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
 * Розраховує час автономної роботи системи.
 *
 * @param {number} remainingCapacity - Залишковий заряд батареї в Ah.
 * @param {number} chargeCurrent - Поточне споживання в A.
 * @param {number} inverterEfficiency - Ефективність інвертора (за замовчуванням 0.95).
 * @returns {number|string} - Час автономної роботи в годинах або '∞', якщо споживання дорівнює 0.
 */
export function calculateAutonomyTime(remainingCapacity: number, charge_current: number, inverterEfficiency = 0.95) {
  if (charge_current >= 0) {
    return '∞';
  }

  // Врахування ефективності інвертора
  const effectiveCurrent = Math.abs(charge_current) / inverterEfficiency;

  const autonomyTime = remainingCapacity / effectiveCurrent;
  return `${autonomyTime.toFixed(2)} hrs`;
}

export function parseManufacturingDate(dateStr: string): string {
  const year = `20${dateStr.slice(0, 2)}`; // Add 20 to the year
  const month = dateStr.slice(2, 4);
  const day = dateStr.slice(4, 6);
  return `${day}-${month}-${year}`;
}
