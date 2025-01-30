<template>
  <ul>
    <li v-for="device of devicesList"
        :key="device?.serial_number">
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
          Uptime: {{ formatDuration(device.device_uptime) }}.
        </span>
      </div>

      <div v-if="disconnectBtn"
           class="row justify-around q-pa-sm">
        <q-btn color="black"
               :disable="!props.token"
               dense
               @click="disconnectDevice(device.address)"
               label="Disconnect" />
        <q-btn color="black"
               dense
               @click="reconnectDevice(device.address)"
               :disable="!props.token"
               label="Reconnect" />
      </div>
      <q-separator color="orange"
                   inset />
    </li>
  </ul>
</template>

<script setup lang='ts'>
import { formatDuration } from '../helpers/utils';
import { ref, onBeforeUnmount } from 'vue';

const devicesList = ref();
const props = defineProps(['disconnectBtn', 'token']);

async function fetchDeviceInfo() {
  try {
    const response = await fetch('/api/device-info');
    if (!response.ok) {
      throw new Error('Failed to fetch device info');
    }
    const data = await response.json();
    console.log('Device Info:', data);
    devicesList.value = data;
  } catch (error) {
    console.error('Error fetching device info:', error);
  }
}

async function disconnectDevice(address: string) {
  try {
    const response = await fetch('/api/disconnect-device', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${props.token}`
      },
      body: JSON.stringify({ address }),
    });
    if (!response.ok) {
      throw new Error('Failed to disconnect device info');
    }
    const data = await response.json();
    console.log('Device Info:', data);
    devicesList.value = data;
  } catch (error) {
    console.error('Error disconnect device info:', error);
  }
}

async function reconnectDevice(address: string) {
  try {
    const response = await fetch('/api/reconnect-device', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${props.token}`
      },
      body: JSON.stringify({ address }),
    });
    if (!response.ok) {
      throw new Error('Failed to reconnect device info');
    }
    const data = await response.json();
    console.log('Device Info:', data);
    devicesList.value = data;
  } catch (error) {
    console.error('Error reconnect device info:', error);
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
