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
