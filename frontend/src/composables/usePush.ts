import { ref } from "vue";

const publicVapidKey = "BHhfESlC5Ns8P5wdIBQrh6X7GkzTShXlTl_OqPiijUG0F_XgbfH3aA0lFJ28dPTRY_NiMiHBx6V8KoW7pFRPyx0";

export function usePush() {
  const pushSubscription = ref<PushSubscription | null>(null);

  async function requestPermission() {
    console.log("🔔 Запит дозволу на сповіщення...");
    const permission = await Notification.requestPermission();

    if (permission !== "granted") {
      console.warn("❌ Користувач відхилив дозвіл на сповіщення.");
      return false;
    }

    console.log("✅ Дозвіл на сповіщення надано.");
    return true;
  }

  async function subscribeToPush() {
    if (!("serviceWorker" in navigator)) {
      console.error("❌ Service Worker не підтримується.");
      return;
    }

    if (!("PushManager" in window)) {
      console.error("❌ Push API не підтримується.");
      return;
    }

    if (!await requestPermission()) {
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;

      const existingSubscription = await registration.pushManager.getSubscription();
      if (existingSubscription) {
        console.log("🔄 Підписка вже існує:", existingSubscription);
        pushSubscription.value = existingSubscription;
        return;
      }

      console.log("📝 Реєстрація нової підписки...");
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicVapidKey),
      });

      pushSubscription.value = subscription;
      console.log("✅ Нова Push Subscription отримана:", subscription);

      await fetch("/api/save-subscription", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(subscription),
      });

    } catch (error) {
      console.error("❌ Помилка підписки на push:", error);
    }
  }

  return { pushSubscription, subscribeToPush };
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return new Uint8Array([...rawData].map((char) => char.charCodeAt(0)));
}
