<template>
  <div class="text-h6">BMS Devices</div>
  <p>Тут ви можете керувати своїми пристроями JK-BMS.</p>

  <q-btn
    :loading="loadingDevices"
    @click="fetchDevices"
    :disable="!token"
    color="black"
    label="Пошук нових пристроїв"
  />

  <template v-if="devices.length">
    <h6 class="q-mt-md">Знайдені пристрої:</h6>
    <p>
      Щоб приєднатися до пристрою, просто натисніть на нього. Доданий вами девайс, буде підключений
      приблизно за 10 секунд і ви зможете побачити його на головному екрані.
    </p>
    <q-list bordered separator>
      <q-item
        v-for="device of devices"
        :key="device.address"
        clickable
        :disable="!!attemptToConnectDevice"
        :active="attemptToConnectDevice === device.address"
        @click="token && connectToDevice(device.address, device.name)"
        v-ripple
      >
        <q-item-section>{{
          attemptToConnectDevice === device.address
            ? `Підключення до ${device?.name}`
            : device?.name
        }}</q-item-section>
      </q-item>
    </q-list>
  </template>
  <template v-if="notFoundDevices">
    <h6 class="q-mt-md">Нових пристроїв JK-BMS не знайдено.</h6>
  </template>

  <q-separator class="q-mt-md" color="white" />

  <div>
    <div class="text-h6 q-mt-md">Ваші пристрої:</div>
    <DevicesList :disconnect-btn="true" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { useSessionStorage } from '../../helpers/utils';
import DevicesList from '../DevicesList.vue';
import type { Device } from '../../models';
import { useBmsStore } from 'src/stores/bms';

const bmsStore = useBmsStore();

const token = useSessionStorage('access_token');
const devices = computed<Device[]>(bmsStore.getDevices);
const notFoundDevices = ref<boolean>(false);
const loadingDevices = ref<boolean>(false);
const attemptToConnectDevice = ref<string>('');
const intervalId = ref();

async function fetchDevices() {
  try {
    loadingDevices.value = true;
    notFoundDevices.value = false;
    const response = await bmsStore.fetchDevices();
    if (!response) {
      notFoundDevices.value = true;
    }
  } catch (error) {
    console.error(error);
  } finally {
    loadingDevices.value = false;
  }
}

async function connectToDevice(address: string, name: string) {
  attemptToConnectDevice.value = address;
  await bmsStore.connectToDevice(address, name);
  bmsStore.updateDevices(devices.value.filter((d) => d.address !== address));
  attemptToConnectDevice.value = '';
}

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await Promise.allSettled([bmsStore.fetchSettings()]);
  }, 5000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

Promise.allSettled([bmsStore.fetchSettings()]);
</script>
