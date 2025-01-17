<template>
  <router-view />
</template>

<script setup lang="ts">
if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
