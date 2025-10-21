/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope &
  typeof globalThis & {
    skipWaiting: () => void;
  };

import { clientsClaim } from 'workbox-core';
import {
  precacheAndRoute,
  cleanupOutdatedCaches,
  createHandlerBoundToURL,
} from 'workbox-precaching';
import { registerRoute, NavigationRoute } from 'workbox-routing';
import { NetworkFirst } from 'workbox-strategies';

self.skipWaiting();
clientsClaim();

precacheAndRoute(self.__WB_MANIFEST);

cleanupOutdatedCaches();

registerRoute(
  new NavigationRoute(createHandlerBoundToURL(process.env.PWA_FALLBACK_HTML), {
    denylist: [new RegExp(process.env.PWA_SERVICE_WORKER_REGEX), /workbox-(.)*\.js$/],
  })
);

registerRoute(({ url }) => url.pathname.startsWith('/'), new NetworkFirst(), 'GET');
registerRoute(({ url }) => /^http/.test(url.pathname), new NetworkFirst(), 'GET');

self.addEventListener('activate', (event) => {
  console.log('customSw -> @activate :: ', event);
  event.waitUntil(self.clients.claim());
});

// TODO: Приклад виклику сповіщення з кнопками дій а нижче хендлер зареєстрвоаний.
// navigator.serviceWorker.getRegistration().then(reg => {
//   reg.showNotification("🔋 Тестова нотифікація", {
//     body: "Це лише тест з консолі",
//     tag: "test-alert",
//     requireInteraction: true,
//     actions: [
//       { action: "open_app", title: "Відкрити" },
//       { action: "close_all", title: "Закрити всі" }
//     ],
//     data: { url: "/#/settings" },
//     icon: "https://solar.levych.com:8443/icons/android-chrome-192x192.png"
//   });
// });
self.addEventListener('notificationclick', (event: NotificationEvent) => {
  console.log('Notification Click: ', event);

  event.notification.close();

  if (event.action === 'close_all') {
    event.waitUntil(
      self.registration.getNotifications().then((notifs) => {
        notifs.filter((n) => n.data?.group === 'device-alerts').forEach((n) => n.close());
      })
    );
    return;
  }
  // event.waitUntil(self.clients.openWindow('https://solar.levych.com:8443/#/settings'));
});

self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) {
    console.error('No data in push event.');
    return;
  }

  const data = event.data.json();

  const options: NotificationOptions & {
    timestamp: number;
    vibrate: number[];
    renotify?: boolean;
    actions: {
      action: string;
      title: string;
    }[];
  } = {
    body: data.body,
    icon: 'https://solar.levych.com:8443/icons/android-chrome-192x192.png',
    tag: `bms-alert-${Date.now()}`,
    requireInteraction: true,
    actions: [{ action: 'close_all', title: 'Закрити всі' }],
    silent: false,
    // renotify: true,
    timestamp: Date.now(),
    vibrate: [200, 100, 200],
    data: { group: 'device-alerts' },
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});
