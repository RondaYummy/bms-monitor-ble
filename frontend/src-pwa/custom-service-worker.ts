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
import { ExpirationPlugin } from 'workbox-expiration';
import type { WorkboxPlugin } from 'workbox-core/types';

// Workbox plugin classes don't satisfy `exactOptionalPropertyTypes`; this cast is type-only.
// (NetworkFirst already caches only successful responses, so no CacheableResponsePlugin is needed.)
const expiration = (maxEntries: number, maxAgeSeconds: number) =>
  new ExpirationPlugin({ maxEntries, maxAgeSeconds }) as unknown as WorkboxPlugin;

self.skipWaiting();
clientsClaim();

precacheAndRoute(self.__WB_MANIFEST);

cleanupOutdatedCaches();

registerRoute(
  new NavigationRoute(createHandlerBoundToURL(process.env.PWA_FALLBACK_HTML), {
    denylist: [new RegExp(process.env.PWA_SERVICE_WORKER_REGEX), /workbox-(.)*\.js$/],
  })
);

// API: only same-origin GETs, short network timeout and a bounded cache. Previously EVERY GET
// (any origin, every unique /api/aggregated-data?from=..&to=.. URL) was cached forever.
registerRoute(
  // /api/stream (SSE) must never go through a caching strategy: it is an endless response.
  ({ url, sameOrigin }) =>
    sameOrigin && url.pathname.startsWith('/api/') && url.pathname !== '/api/stream',
  new NetworkFirst({
    cacheName: 'api-cache',
    networkTimeoutSeconds: 10,
    plugins: [expiration(50, 24 * 60 * 60)],
  }),
  'GET'
);

// Other same-origin assets that are not in the precache manifest.
registerRoute(
  ({ url, sameOrigin }) => sameOrigin && !url.pathname.startsWith('/api/'),
  new NetworkFirst({
    cacheName: 'runtime-cache',
    plugins: [expiration(100, 30 * 24 * 60 * 60)],
  }),
  'GET'
);

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
  event.notification.close();

  if (event.action === 'close_all') {
    event.waitUntil(
      self.registration.getNotifications().then((notifs) => {
        notifs.filter((n) => n.data?.group === 'device-alerts').forEach((n) => n.close());
      })
    );
    return;
  }
  const url: string = event.notification.data?.url || '/#/';
  // Focus an already open app window (and show the right page), or open the app.
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
      const existing = windows.find((w) => 'focus' in w) as WindowClient | undefined;
      if (existing) {
        return existing.focus().then((w) => (w && 'navigate' in w ? w.navigate(url) : w));
      }
      return self.clients.openWindow(url);
    })
  );
});

interface PushData {
  type?: 'status' | 'alert';
  tag?: string;
  title?: string;
  body?: string;
  badge?: number | null;
}

/** SOC on the app icon (iOS 16.4+/desktop show the number, Android Chrome a dot). */
async function setBadge(value: number | null | undefined) {
  const nav = self.navigator as Navigator & {
    setAppBadge?: (n?: number) => Promise<void>;
    clearAppBadge?: () => Promise<void>;
  };
  try {
    if (value === null || value === undefined) await nav.clearAppBadge?.();
    else await nav.setAppBadge?.(Math.max(0, Math.min(100, Math.round(value))));
  } catch {
    /* badging not supported */
  }
}

self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) {
    console.error('No data in push event.');
    return;
  }

  let data: PushData;
  try {
    data = event.data.json();
  } catch {
    data = { title: 'BMS Monitor', body: event.data.text() };
  }

  if (data.type === 'status') {
    // Live status: always the same tag, so the new one REPLACES the previous notification quietly.
    const statusOptions: NotificationOptions & { renotify?: boolean; timestamp?: number } = {
      body: data.body ?? '',
      icon: '/icons/android-chrome-192x192.png',
      badge: '/icons/favicon-32x32.png',
      tag: data.tag || 'bms-status',
      renotify: false,
      silent: true,
      requireInteraction: false,
      timestamp: Date.now(),
      data: { group: 'status', url: '/#/' },
    };
    event.waitUntil(
      Promise.all([
        self.registration.showNotification(data.title || 'BMS Monitor', statusOptions),
        setBadge(data.badge),
      ])
    );
    return;
  }

  const options: NotificationOptions & {
    timestamp: number;
    vibrate: number[];
    renotify?: boolean;
    actions: {
      action: string;
      title: string;
    }[];
  } = {
    body: data.body ?? '',
    icon: '/icons/android-chrome-192x192.png',
    tag: `bms-alert-${Date.now()}`,
    requireInteraction: true,
    actions: [{ action: 'close_all', title: 'Закрити всі' }],
    silent: false,
    timestamp: Date.now(),
    vibrate: [200, 100, 200],
    data: { group: 'device-alerts', url: '/#/settings' },
  };

  event.waitUntil(self.registration.showNotification(data.title || 'BMS Monitor', options));
});
