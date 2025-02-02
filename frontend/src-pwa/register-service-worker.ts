import { register } from 'register-service-worker';
import { Notify } from 'quasar';
import packageJson from '../package.json';

// The ready(), registered(), cached(), updatefound() and updated()
// events passes a ServiceWorkerRegistration instance in their arguments.
// ServiceWorkerRegistration: https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration

// const randomVersion = `${Date.now()}-${Math.random().toString(36).substring(2, 8)}`;
const appVersion = packageJson.version;
console.log('%c[APP-VERSION]: ' + appVersion, 'color: #654ef2; font-weight: bold; font-size: 16px;');

register(process.env.SERVICE_WORKER_FILE, {
  // The registrationOptions object will be passed as the second argument
  // to ServiceWorkerContainer.register()
  // https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerContainer/register#Parameter

  // registrationOptions: { scope: './' },

  ready(/* registration*/) {
    // console.log("Service worker is active.", registration.active);

    // if (registration.active?.state === 'activated') {
    //   console.log('PUSH message activated.');
    //   registration.active.addEventListener("push", (event: any) => {
    //     console.log("Push message received.");
    //     if (!event.data) {
    //       console.error("No data in push event.");
    //       return;
    //     }

    //     const data = event.data.json();
    //     console.log("Push data:", data);

    //     const options = {
    //       body: data.body,
    //       icon: "/icons/android-chrome-192x192.png",
    //       tag: "bms-alert",
    //     };

    //     event.waitUntil(
    //       registration.showNotification(data.title, options).catch((err) => {
    //         console.error("Error displaying notification:", err);
    //       })
    //     );
    //   });
    // }
  },

  registered(/* registration */) {
    // console.log('Service worker has been registered.')
  },

  cached(/* registration */) {
    // console.log('Content has been cached for offline use.');
  },

  updatefound(/* registration */) { },

  updated(/* registration */) {
    // console.log('New content is available; please refresh.');
    // force
    Notify.create({
      type: 'warning',
      progress: true,
      message: 'New content is available. Please click on \'Ok\' to apply changes, or \'Cancel\' and refresh the page yourself later.',
      position: 'bottom',
      multiLine: true,
      actions: [
        { label: 'Cancel', color: 'white', handler: () => { /**/ } },
        {
          label: 'Ok',
          color: 'white',
          handler: () => {
            // localStorage.clear()
            (location as unknown as any)?.reload();
          }
        }
      ],
      timeout: 0
    });
  },

  offline() {
    // console.log('No internet connection found. App is running in offline mode.')
  },

  error(/* err */) {
    // console.error('Error during service worker registration:', err)
  },
});
