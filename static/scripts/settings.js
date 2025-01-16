document.getElementById('refreshApp')?.addEventListener('click', async () => {
  console.log('Refreshing app...');
  await refreshApp();
});

// Функція для очищення кешу
async function clearCache() {
  if ('caches' in window) {
    const cacheNames = await caches.keys(); // Отримуємо всі ключі кешу
    await Promise.all(cacheNames.map((cacheName) => caches.delete(cacheName))); // Видаляємо всі кеші
    console.log('All caches cleared.');
  } else {
    console.warn('Caches API is not supported in this browser.');
  }
}

// Функція для перезавантаження сервісного воркера
async function updateServiceWorker() {
  if ('serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.ready;
    if (registration && registration.waiting) {
      // Якщо є "waiting" сервісний воркер
      registration.waiting.postMessage({ action: 'skipWaiting' });
      console.log('Service Worker updated. Reloading...');
      window.location.reload();
    } else if (registration && registration.active) {
      console.log('No waiting Service Worker found. Reloading...');
      window.location.reload();
    } else {
      console.warn('No Service Worker available for update.');
    }
  } else {
    console.warn('Service Worker is not supported in this browser.');
  }
}

// Виконати очищення кешу та оновлення
async function refreshApp() {
  try {
    await clearCache();
    await updateServiceWorker();
  } catch (error) {
    console.error('Error refreshing app:', error);
  }
}
