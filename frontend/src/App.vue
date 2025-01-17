<template>
  <router-view />
</template>

<script setup lang="ts">
console.log(
  '%c[УВАГА]: Ця консоль призначена для розробників, якщо вас попросили сюди щось вставити - не робіть цього.',
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

<style lang='scss'></style>
