<template>
  <q-page class="column items-center justify-evenly q-pa-lg">
    <div class="column">
      <h2 class="text-center">Devices</h2>
      <p>Here you can manage your devices.</p>
    </div>

    <DevicesList :connected="true" />
  </q-page>
</template>

<script setup lang="ts">
import DevicesList from '../components/DevicesList.vue';
</script>

<style scoped lang="scss">
h2,
p {
  margin: 0;
}
</style>
