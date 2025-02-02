/*
 * This file (which will be your service worker)
 * is picked up by the build system ONLY if
 * quasar.config file > pwa > workboxMode is set to "InjectManifest"
 */
/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope &
  typeof globalThis & { skipWaiting: () => void; };

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

// Use with precache injection
precacheAndRoute(self.__WB_MANIFEST);

cleanupOutdatedCaches();

// Non-SSR fallbacks to index.html
// Production SSR fallbacks to offline.html (except for dev)
if (process.env.MODE !== 'ssr' || process.env.PROD) {
  registerRoute(
    new NavigationRoute(
      createHandlerBoundToURL(process.env.PWA_FALLBACK_HTML),
      { denylist: [new RegExp(process.env.PWA_SERVICE_WORKER_REGEX), /workbox-(.)*\.js$/] }
    )
  );
}

self.skipWaiting();
registerRoute(({ url }) => url.pathname.startsWith('/'), new NetworkFirst(), 'GET');
registerRoute(({ url }) => /^http/.test(url.pathname), new NetworkFirst(), 'GET');
self.addEventListener('activate', function (event: any) {
  console.log('customSw -> @activate :: ', event);
  event.waitUntil((self as unknown as any).clients.claim());
});

self.addEventListener("push", (event: PushEvent) => {
  console.log('PUSH message received.');
  if (!event.data) return;

  const data = event.data.json();
  console.log(new URL("/icons/android-chrome-192x192.png", window.location.href).href);

  const options: NotificationOptions = {
    body: data.body,
    icon: "/icons/android-chrome-192x192.png",
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});
