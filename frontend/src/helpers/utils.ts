export function formatDuration(seconds: number) {
  const units = [
    { label: 'year', seconds: 31536000 }, // 365 днів
    { label: 'month', seconds: 2592000 }, // 30 днів
    { label: 'day', seconds: 86400 }, // 24 години
    { label: 'hour', seconds: 3600 }, // 60 хвилин
    { label: 'minute', seconds: 60 }, // 60 секунд
    { label: 'second', seconds: 1 },
  ];

  const result = [];

  for (const unit of units) {
    const value = Math.floor(seconds / unit.seconds);
    if (value > 0) {
      result.push(`${value} ${unit.label}${value > 1 ? 's' : ''}`);
      seconds %= unit.seconds; // Залишок секунд
    }
  }

  return result.join(', ');
}

export function calculateAveragePerIndex(arrays: Array<any>) {
  if (!arrays.length || !arrays[0]?.length) return [];
  // Кількість чисел у кожному масиві
  const length = arrays[0].length;
  // Ініціалізація масиву для збереження середніх значень
  const averages = Array(length).fill(0);
  // Обчислення суми для кожного індексу
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
  if (array.length === 0) return 0; // Перевірка на випадок порожнього масиву

  const total = array.reduce((sum, item) => sum + item[field], 0);
  return total / array.length;
}
