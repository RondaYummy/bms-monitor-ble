<template>
  <ul>
    <li v-for="device of devicesList"
        :key="`sr_${device?.serial_number}`">
      <div class="column">
        <div class="row justify-between q-mb-10">
          <div class="column">
            <q-badge :class="{ 'connected-device': device?.connected }"
                     class="q-mb-10 text-center"
                     color="cyan">
              {{ device.device_name }}
            </q-badge>
            <div>{{ device.vendor_id }}</div>
          </div>
          <div class="column">
            <div class="q-mb-10">Hardware v.
              <span class="unique">{{ device.hardware_version }}</span>
            </div>
            <div>Software v.
              <span class="unique">{{ device.software_version }}</span>
            </div>
          </div>
        </div>
        <span class="text-center coral">
          Дата виробництва:
          {{ parseManufacturingDate(device.manufacturing_date) }}.
        </span>
        <span class="text-center coral">
          Час роботи: {{ formatDuration(device.device_uptime) }}.
        </span>
      </div>

      <div v-if="disconnectBtn"
           class="row justify-around q-pa-sm">

        <q-btn v-if="device.connected"
               color="black"
               :disable="!isDisabled"
               dense
               @click="disconnectDevice(device.device_address, device.device_name)"
               label="Від’єднатися" />
        <q-btn v-if="!device.connected"
               color="black"
               dense
               @click="connectToDevice(device.device_address, device.device_name)"
               :disable="!isDisabled || attemptToConnectDevice === device.device_address"
               label="Приєднатися" />
      </div>
      <q-separator color="orange"
                   inset />
    </li>
  </ul>
</template>

<script setup lang='ts'>
import { formatDuration, parseManufacturingDate, useSessionStorage } from '../helpers/utils';
import { ref, onBeforeUnmount, computed } from 'vue';
import type { DeviceInfoMap } from '../models';

const token = useSessionStorage("access_token");
const isDisabled = computed(() => !token.value);

const devicesList = ref();
const attemptToConnectDevice = ref();
const props = defineProps(['disconnectBtn', 'connected']);

function checkResponse(response: Response) {
  if (!response.ok) {
    throw new Error('Failed to error alerts');
  }
  if (response.status === 401) {
    sessionStorage.removeItem('access_token');
    throw new Error('Have no access');
  }
}

async function fetchDeviceInfo() {
  try {
    const response = await fetch('/api/device-info');
    checkResponse(response);
    const data: DeviceInfoMap = await response.json();
    console.log('Device Info:', data);
    if (props.connected && data) {
      devicesList.value = Object.values(data).filter((d: any) => d.connected);
    } else {
      devicesList.value = data;
    }
  } catch (error) {
    console.error('Error fetching device info:', error);
  }
}

async function connectToDevice(address: string, name: string) {
  attemptToConnectDevice.value = address;
  const response = await fetch('/api/connect-device', {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token.value}`
    },
    body: JSON.stringify({ address, name }),
  });
  checkResponse(response);
  attemptToConnectDevice.value = '';
}

async function disconnectDevice(address: string, name: string) {
  try {
    const response = await fetch('/api/disconnect-device', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token.value}`
      },
      body: JSON.stringify({ address, name }),
    });
    checkResponse(response);
    const data = await response.json();
    console.log('Device Info:', data);
    devicesList.value = data;
  } catch (error) {
    console.error('Error disconnect device info:', error);
  }
}

fetchDeviceInfo();
const intervalId = setInterval(async () => {
  await fetchDeviceInfo();
}, 3000);
onBeforeUnmount(() => {
  clearInterval(intervalId);
});
</script>

<style scoped lang='scss'>
ul {
  list-style-type: none;
  gap: 15px;
  display: flex;
  flex-direction: column;
  padding: 0;
  width: 100%;
}

.connected-device {
  position: relative;
}

li .connected-device::before {
  content: "";
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

h2,
p {
  margin: 0;
}
</style>
