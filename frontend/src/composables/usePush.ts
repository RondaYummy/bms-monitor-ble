import { ref } from 'vue';
import { Notify } from 'quasar';
import { useConfigStore } from 'src/stores/config';
import { api } from '../boot/axios';

export function usePush() {
  const pushSubscription = ref<PushSubscription | null>(null);

  async function requestPermission() {
    console.log('🔔 Запит дозволу на сповіщення...');
    const permission = await Notification.requestPermission();

    if (permission !== 'granted') {
      console.warn('❌ Користувач відхилив дозвіл на сповіщення.');
      return false;
    }

    console.log('✅ Дозвіл на сповіщення надано.');
    return true;
  }

  async function subscribeToPush() {
    if (!('serviceWorker' in navigator)) {
      console.error('❌ Service Worker не підтримується.');
      return;
    }
    if (!('PushManager' in window)) {
      console.error('❌ Push API не підтримується.');
      return;
    }
    if (!(await requestPermission())) {
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;

      const existingSubscription = await registration.pushManager.getSubscription();
      if (existingSubscription) {
        console.info('🔄 Підписка вже існує:', existingSubscription);
        pushSubscription.value = existingSubscription;
        return;
      }

      const configStore = useConfigStore();
      await configStore.fetchConfigs();
      if (!configStore.config) throw new Error('Config not found');
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(configStore.config?.VAPID_PUBLIC_KEY) as BufferSource,
      });

      pushSubscription.value = subscription;
      console.info('✅ Нова Push Subscription отримано:', subscription);

      await api.post('/api/save-subscription', {
        subscription: subscription,
      })
        .then(() => {
          Notify.create({
            message: 'Ви успішно підписались на сповіщення',
            color: 'secondary',
            position: 'top',
          });
        })
        .catch(async () => {
          const registration = await navigator.serviceWorker.ready;
          const existingSubscription = await registration.pushManager.getSubscription();
          if (existingSubscription) {
            await existingSubscription.unsubscribe();
            pushSubscription.value = null;
            console.info('✅ Підписка успішно видалена.');
          }
        });
    } catch (error) {
      console.error('❌ Помилка підписки на push:', error);
    }
  }

  return { pushSubscription, subscribeToPush };
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = atob(base64);
  return new Uint8Array([...rawData].map((char) => char.charCodeAt(0)));
}

export async function cancelAllSubscriptions(showNotify: boolean = true) {
  navigator.serviceWorker.getRegistration().then((reg) => {
    if (!reg) {
      console.error('Service Worker not registered');
      return;
    }
    reg.pushManager.getSubscription().then((subscription) => {
      if (subscription) {
        subscription
          .unsubscribe()
          .then((successful) => {
            console.info('Push subscription successfully unsubscribed:', successful);
            if (showNotify) {
              Notify.create({
                message: 'Ви успішно скасували підписку на сповіщення',
                color: 'secondary',
                position: 'top',
              });
            }
          })
          .catch((error) => {
            console.error('Error unsubscribing', error);
          });
      } else {
        console.log('No push subscription found.');
      }
    });
  });
}

export function checkPushSubscription(): Promise<PushSubscription | null> {
  return navigator.serviceWorker.getRegistration().then((reg) => {
    if (reg) {
      return reg.pushManager.getSubscription().then((subscription) => {
        console.info('🔍 Push Subscription:', subscription);
        return subscription;
      });
    } else {
      return null;
    }
  });
}
