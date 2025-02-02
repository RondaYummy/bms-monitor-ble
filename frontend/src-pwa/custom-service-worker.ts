/// <reference lib="webworker" />

declare const self: ServiceWorkerGlobalScope & typeof globalThis & {
  skipWaiting: () => void;
};

import { clientsClaim } from "workbox-core";
import {
  precacheAndRoute,
  cleanupOutdatedCaches,
  createHandlerBoundToURL,
} from "workbox-precaching";
import { registerRoute, NavigationRoute } from "workbox-routing";
import { NetworkFirst } from "workbox-strategies";

// Примусово активуємо Service Worker одразу після установки
self.skipWaiting();
clientsClaim();

// Використання Workbox для попереднього кешування
precacheAndRoute(self.__WB_MANIFEST);

// Очищення застарілих кешів
cleanupOutdatedCaches();

// Обробка запитів на навігацію
registerRoute(
  new NavigationRoute(
    createHandlerBoundToURL(process.env.PWA_FALLBACK_HTML),
    { denylist: [new RegExp(process.env.PWA_SERVICE_WORKER_REGEX), /workbox-(.)*\.js$/] }
  )
);

// Обробка запитів GET
registerRoute(({ url }) => url.pathname.startsWith("/"), new NetworkFirst(), "GET");
registerRoute(({ url }) => /^http/.test(url.pathname), new NetworkFirst(), "GET");

// Логування активації
self.addEventListener("activate", (event) => {
  console.log("customSw -> @activate :: ", event);
  event.waitUntil(self.clients.claim());
});

// Обробка push-повідомлень
self.addEventListener("push", (event: PushEvent) => {
  if (!event.data) {
    console.error("No data in push event.");
    return;
  }

  const data = event.data.json();

  // const options: NotificationOptions = {
  const options: any = {
    body: data.body,
    icon: "https://solar.levych.com:8443/icons/android-chrome-192x192.png",
    tag: `bms-alert-${Date.now()}`,
    requireInteraction: true,
    silent: false,
    renotify: true,
    timestamp: Date.now(),
    vibrate: [200, 100, 200],
  };

  event.waitUntil(self.registration
    .showNotification(data.title, options));
});

self.addEventListener("notificationclick", async (event) => {
  console.log("Notification clicked:", event.notification);

  event.notification.close();

  event.waitUntil(
    (async () => {
      const allClients = await self.clients.matchAll({ type: "window", includeUncontrolled: true });

      // Перевіряємо, чи вкладка вже є у відкритих вікнах
      for (const client of allClients) {
        if (client.url.includes("/settings") && "focus" in client) {
          return client.focus(); // Якщо є — просто фокусуємо її
        }
      }

      return self.clients.openWindow("/settings"); // Якщо вкладки немає — відкриваємо нову
    })()
  );
});
