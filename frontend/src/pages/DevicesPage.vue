<template>
  <q-page class="row items-center justify-evenly">
    <h2>Devices</h2>
    <p>Here you can manage your devices.</p>

    <ul v-for="device of devicesList"
        :key="device?.serial_number">
      <li>
        <div class="column">
          <div class="row justify-between q-mb-10">
            <div class="column">
              <q-badge id="dev-name"
                       class="q-mb-10"
                       color="cyan">
                #{{ device.device_name }}
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
          <div class="text-center coral">
            Uptime: {{ formatDuration(device.device_uptime) }}.
          </div>
        </div>
      </li>
    </ul>
    <q-badge color="blue">
      #4D96F2
    </q-badge>
  </q-page>
</template>

<script setup lang='ts'>
import { formatDuration } from 'src/helpers/utils';
import { ref } from 'vue';

const devicesList = ref();

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
fetchDeviceInfo();
</script>

<style scoped lang='scss'>
@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }

  50% {
    transform: scale(1.2);
    opacity: 0.7;
  }

  100% {
    transform: scale(1);
    opacity: 1;
  }
}

li #dev-name::before {
  content: "";
  width: 8px;
  height: 8px;
  background-color: green;
  border-radius: 50%;
  position: absolute;
  top: -7px;
  left: -7px;
  box-shadow: 0 0 5px rgba(0, 128, 0, 0.5);
  animation: pulse 1.5s infinite;
}
</style>
