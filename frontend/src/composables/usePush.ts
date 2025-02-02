import { ref } from "vue";

const publicVapidKey = "BHhfESlC5Ns8P5wdIBQrh6X7GkzTShXlTl_OqPiijUG0F_XgbfH3aA0lFJ28dPTRY_NiMiHBx6V8KoW7pFRPyx0";

export function usePush() {
  const pushSubscription = ref<PushSubscription | null>(null);

  async function subscribeToPush() {
    if (!("serviceWorker" in navigator)) {
      console.error("Service Worker не підтримується.");
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicVapidKey),
      });

      pushSubscription.value = subscription;
      console.log("Push Subscription отримано:", subscription);

      // Відправити підписку на сервер
      await fetch("/api/save-subscription", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(subscription),
      });
      setTimeout(async () => {
        await fetch("/api/send-notification", {
          method: "POST",
        }, 5000);
      });

    } catch (error) {
      console.error("Помилка підписки на push:", error);
    }
  }

  return { pushSubscription, subscribeToPush };
}

// Функція перетворення ключа VAPID у Uint8Array
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return new Uint8Array([...rawData].map((char) => char.charCodeAt(0)));
}
