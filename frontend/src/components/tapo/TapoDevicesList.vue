<template>
  <h6 class="q-mt-md" v-if="tapoDevices?.length">Ваші пристрої TP-Link Tapo:</h6>

  <div class="column q-mt-md q-mb-md" v-if="tapoDevices?.length">
    <q-separator color="orange" inset />
    <TapoDeviceItem :device="device" v-for="device of tapoDevices" :key="device.id" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import TapoDeviceItem from './TapoDeviceItem.vue';
import { useTapoStore } from 'src/stores/tapo';
import { TapoDevice } from 'src/models';

const tapoStore = useTapoStore();

const tapoDevices = computed<TapoDevice[]>(tapoStore.getDevices);
const intervalId = ref();

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await tapoStore.fetchDevices();
  }, 8000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

tapoStore.fetchDevices();
</script>
