document.getElementById('refreshApp')?.addEventListener('click', async () => {
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
