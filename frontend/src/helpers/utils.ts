
import { onBeforeUnmount, ref, watch } from "vue";

export const useSessionStorage = (key: string) => {
  const value = ref(sessionStorage.getItem(key));

  watch(value, (newValue) => {
    if (newValue === null || newValue === undefined) {
      sessionStorage.removeItem(key);
    } else {
      sessionStorage.setItem(key, newValue);
    }
  });

  const syncWithStorage = (event: any) => {
    if (event.key === key) {
      value.value = event.newValue;
    }
  };

  window.addEventListener("storage", syncWithStorage);

  onBeforeUnmount(() => {
    window.removeEventListener("storage", syncWithStorage);
  });

  return value;
};

export function formatDuration(seconds: number) {
  const units = [
    { label: 'y', seconds: 31536000 }, // 365 днів
    { label: 'm', seconds: 2592000 }, // 30 днів
    { label: 'd', seconds: 86400 }, // 24 години
    { label: 'h', seconds: 3600 }, // 60 хвилин
    { label: 'min', seconds: 60 }, // 60 секунд
    { label: 's', seconds: 1 },
  ];

  const result = [];

  for (const unit of units) {
    const value = Math.floor(seconds / unit.seconds);
    if (value > 0) {
      result.push(`${value} ${unit.label}`);
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
