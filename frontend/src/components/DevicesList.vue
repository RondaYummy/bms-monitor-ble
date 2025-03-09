<template>
  <ul>
    <li v-for="device of devicesList"
        :key="`sr_${device?.serial_number}`">
      <div class="column">
        <div class="row justify-between q-mb-10">
          <div class="column">
            <q-badge :class="{
              'connected-device': device?.connected,
              'disconnected-device': !device?.connected,
            }"
                     class="q-pa-xs cursor-pointer text-weight-bold q-mt-sm q-mb-10 text-center cursor-pointer"
                     color="cyan"
                     @click="copy(device.address)">
              {{ device.name }} [{{ device.address?.toUpperCase() }}]
            </q-badge>
            <div class="text-left">{{ device.vendor_id }}</div>
          </div>
          <div class="column">
            <div class="q-mb-10">
              Hardware v.
              <span class="unique">{{ device?.hardware_version }}</span>
            </div>
            <div>
              Software v.
              <span class="unique">{{ device?.software_version }}</span>
            </div>
          </div>
        </div>
        <span class="text-center coral">
          Дата виробництва:
          {{ parseManufacturingDate(device?.manufacturing_date) }}.
        </span>
        <span class="text-center coral">
          Час роботи: {{ formatDuration(device?.device_uptime) }}.
        </span>
      </div>

      <div v-if="disconnectBtn"
           class="row justify-around q-pa-sm">
        <q-btn v-if="device.connected"
               color="black"
               :disable="!token || !!disconnectDeviceState"
               :loading="disconnectDeviceState === device.address"
               dense
               @click="disconnectDevice(device.address, device.name)"
               label="Від’єднатися" />
        <q-btn v-if="!device.connected"
               color="black"
               dense
               :loading="attemptToConnectDevice === device.address"
               @click="connectToDevice(device.address, device.name)"
               :disable="!token || !!attemptToConnectDevice"
               label="Приєднатися" />
      </div>
      <q-separator color="orange"
                   inset />
    </li>
  </ul>
</template>

<script setup lang="ts">
import { copy, formatDuration, parseManufacturingDate, useSessionStorage } from '../helpers/utils';
import { ref, onBeforeUnmount, computed } from 'vue';
import type { DeviceInfo } from '../models';
import { useQuasar } from 'quasar';
import { useBmsStore } from 'src/stores/bms';

const $q = useQuasar();
const bmsStore = useBmsStore();
const token = useSessionStorage("access_token");

const devicesList = computed<DeviceInfo[]>(() => bmsStore.deviceInfo);
const attemptToConnectDevice = ref();
const disconnectDeviceState = ref();
const props = defineProps(['disconnectBtn', 'connected']);

async function connectToDevice(address: string, name: string) {
  try {
    attemptToConnectDevice.value = address;
    const response = await fetch('/api/connect-device', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify({ address, name }),
    });

    const data = await response.json();
    if (data?.error) {
      $q.notify({
        message: data?.error,
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      });
    }
  } catch (error) {
    console.error('Error connecting to device:', error);
    $q.notify({
      message: 'Error connecting to device.',
      color: 'red',
      icon: 'warning',
      position: 'top',
      timeout: 2000,
    });
  } finally {
    setTimeout(() => {
      attemptToConnectDevice.value = '';
    }, 3000);
  }
}

async function disconnectDevice(address: string, name: string) {
  try {
    disconnectDeviceState.value = address;
    await fetch('/api/disconnect-device', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token.value}`,
      },
      body: JSON.stringify({ address, name }),
    });
  } catch (error) {
    console.error('Error disconnect device info:', error);
  } finally {
    setTimeout(() => {
      disconnectDeviceState.value = '';
    }, 3000);
  }
}

bmsStore.fetchDeviceInfo(props.connected);
const intervalId = setInterval(async () => {
  await bmsStore.fetchDeviceInfo(props.connected);
}, 5000);

onBeforeUnmount(() => {
  clearInterval(intervalId);
});
</script>

<style scoped lang="scss">
ul {
  list-style-type: none;
  gap: 15px;
  display: flex;
  flex-direction: column;
  padding: 0;
  width: 100%;
}

.connected-device,
.disconnected-device {
  position: relative;
}

li .connected-device::before {
  content: '';
  width: 8px;
  height: 8px;
  background-color: #0f0;
  border-radius: 50%;
  position: absolute;
  top: -9px;
  left: -9px;
  box-shadow: 0 0 5px rgba(0, 128, 0, 0.5);
  animation: pulse 1.5s infinite;
}

li .disconnected-device::before {
  content: '';
  width: 8px;
  height: 8px;
  background-color: #ff0266;
  border-radius: 50%;
  position: absolute;
  top: -9px;
  left: -9px;
  box-shadow: 0 0 5px #ff026780;
  animation: pulse 1.5s infinite;
}

h2,
p {
  margin: 0;
}
</style>
