<template>
  <q-page class="column items-center justify-evenly">
    <div class="column">
      <h2>Devices</h2>
      <p>Here you can manage your devices.</p>
    </div>

    <ul>
      <li v-for="device of devicesList"
          :key="device?.serial_number">
        <div class="column">
          <div class="row justify-between q-mb-10">
            <div class="column">
              <q-badge id="dev-name"
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
          <div class="text-center coral">
            Uptime: {{ formatDuration(device.device_uptime) }}.
          </div>
        </div>
      </li>
    </ul>
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
ul {
  list-style-type: none;
  gap: 15px;
  display: flex;
  flex-direction: column;
  padding: 0;
}

#dev-name {
  position: relative;
}

li #dev-name::before {
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
