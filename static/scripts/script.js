document.getElementById('refreshApp').addEventListener('click', async () => {
  console.log('Refreshing app...');
  await refreshApp();
});

// Функція для очищення кешу
async function clearCache() {
  if ('caches' in window) {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName)));
    console.log('All caches cleared.');
  }
}

// Функція для перезавантаження сервісного воркера
async function updateServiceWorker() {
  if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ action: 'skipWaiting' });
    console.log('Service Worker updated. Reloading...');
    window.location.reload();
  }
}

// Виконати очищення кешу та оновлення
async function refreshApp() {
  await clearCache();
  await updateServiceWorker();
}

async function fetchDeviceInfo() {
  try {
    const response = await fetch('/api/device-info');
    if (!response.ok) {
      throw new Error('Failed to fetch device info');
    }
    const data = await response.json();
    console.log('Device Info:', data);
    // Відобразіть дані на сторінці
    document.getElementById('deviceInfo').innerText = JSON.stringify(data, null, 2);
  } catch (error) {
    console.error('Error fetching device info:', error);
    document.getElementById('deviceInfo').innerText = 'Error fetching device info.';
  }
}

// Викликаємо функцію при завантаженні сторінки
document.addEventListener('DOMContentLoaded', () => {
  fetchDeviceInfo();
});
