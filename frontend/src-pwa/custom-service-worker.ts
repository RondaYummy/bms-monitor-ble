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

self.skipWaiting();
clientsClaim();

precacheAndRoute(self.__WB_MANIFEST);

cleanupOutdatedCaches();

registerRoute(
  new NavigationRoute(
    createHandlerBoundToURL(process.env.PWA_FALLBACK_HTML),
    { denylist: [new RegExp(process.env.PWA_SERVICE_WORKER_REGEX), /workbox-(.)*\.js$/] }
  )
);

registerRoute(({ url }) => url.pathname.startsWith("/"), new NetworkFirst(), "GET");
registerRoute(({ url }) => /^http/.test(url.pathname), new NetworkFirst(), "GET");

self.addEventListener("activate", (event) => {
  console.log("customSw -> @activate :: ", event);
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event: PushEvent) => {
  if (!event.data) {
    console.error("No data in push event.");
    return;
  }

  const data = event.data.json();

  const options: NotificationOptions & { timestamp: number; vibrate: number[]; renotify?: boolean; } = {
    body: data.body,
    icon: "https://solar.levych.com:8443/icons/android-chrome-192x192.png",
    tag: `bms-alert-${Date.now()}`,
    requireInteraction: true,
    silent: false,
    // renotify: true,
    timestamp: Date.now(),
    vibrate: [200, 100, 200],
  };

  event.waitUntil(self.registration
    .showNotification(data.title, options));
});
