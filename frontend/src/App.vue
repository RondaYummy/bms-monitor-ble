<template>
  <router-view />
</template>

<script setup lang="ts">
import { usePush } from "./composables/usePush";

const { subscribeToPush } = usePush();
const requestedSubscription = localStorage.getItem('sub-req');
if (!requestedSubscription) {
  subscribeToPush();
  localStorage.setItem('sub-req', 'requested');
}

// const tokenTimestamp = Number(sessionStorage.getItem(`access_token_timestamp`));
// const currentTime = new Date().getTime();
// const elapsedTime = (currentTime - tokenTimestamp) / 1000;
// if (elapsedTime >= 3600) {
//   console.info('Time expired!');
//   sessionStorage.removeItem(`access_token`);
//   sessionStorage.removeItem(`access_token_timestamp`);
// }

console.warn(
  '%c[УВАГА]: Ця консоль призначена для розробників, якщо вас попросили сюди щось вставити - не робіть цього.',
  'color: red; font-weight: bold;'
);
console.warn(
  '%c[УВАГА]: This console is intended for developers, if you are asked to insert something here, do not do it.',
  'color: red; font-weight: bold;'
);
console.group('Ukraine');
console.info(
  '%c                    ',
  'background: #0057B8; font-size: 18px;'
);
console.info(
  '%c                    ',
  'background: #FFD700;  font-size: 18px;'
);
console.groupEnd();

if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {

  const handler = (e: any) => {
    if (e && e.scale !== 1) {
      e.preventDefault();
    }
  };

  window.addEventListener('touchmove', handler as EventListenerOrEventListenerObject, { passive: false });
  window.document.addEventListener('touchmove', handler as EventListenerOrEventListenerObject, {
    passive: false
  });
}
</script>
