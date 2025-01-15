const CACHE_NAME = 'bms-monitor-v1';
const urlsToCache = [
  '/',
  '/static/styles.css',
  '/static/script.js',
  '/static/manifest.json',
  '/static/icons/icon-128x128.png',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-256x256.png',
  '/static/icons/icon-384x384.png',
];

if ('serviceWorker' in navigator) {
  navigator.serviceWorker
    .register('/static/service-worker.js')
    .then((registration) => {
      console.log('Service Worker registered with scope:', registration.scope);
    })
    .catch((err) => {
      console.log('Service Worker registration failed:', err);
    });
}

// Установка сервісного воркера і кешування файлів
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Opened cache');
      return cache.addAll(urlsToCache);
    })
  );
});

// Обробка запитів з кешу
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// Очищення застарілого кешу
self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((cacheName) => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      )
    )
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.action === 'skipWaiting') {
    self.skipWaiting();
  }
});
