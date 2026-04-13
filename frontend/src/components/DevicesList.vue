<template>
  <ul class="devices-list">
    <li
      v-for="device of devicesList"
      :key="`sr_${device?.serial_number}`"
      class="device-row"
    >
      <div class="device-card">
        <div class="device-header">
          <div class="device-title-wrap">
            <div
              :class="{
                'connected-device': device?.connected,
                'disconnected-device': !device?.connected,
              }"
              class="device-status-dot"
            ></div>

            <div class="device-title-block">
              <div @click="copy(device.address)" class="device-title">
                {{ device.name }}
              </div>
              <div class="device-subtitle">
                <span class="device-address">[{{ device.address?.toUpperCase() }}]</span>
              </div>
            </div>
          </div>

          <div class="device-vendor">
            <span class="meta-label">Vendor ID</span>
            <span class="meta-value">{{ device.vendor_id }}</span>
          </div>
        </div>

        <div class="device-content">
          <div class="device-meta-grid">
            <div class="meta-card">
              <span class="meta-label">Hardware v.</span>
              <span class="meta-value unique">{{ device?.hardware_version }}</span>
            </div>

            <div class="meta-card">
              <span class="meta-label">Software v.</span>
              <span class="meta-value unique">{{ device?.software_version }}</span>
            </div>

            <div class="meta-card">
              <span class="meta-label">Дата виробництва</span>
              <span class="meta-value">
                {{ parseManufacturingDate(device?.manufacturing_date) }}
              </span>
            </div>

            <div class="meta-card">
              <span class="meta-label">Час роботи</span>
              <span class="meta-value accent-value">
                {{ formatDuration(device?.device_uptime) }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="disconnectBtn" class="device-actions">
          <q-btn
            v-if="device.connected"
            :disable="!token || !!disconnectDeviceState"
            :loading="disconnectDeviceState === device.address"
            @click="disconnectDevice(device.address, device.name)"
            label="Від’єднатися"
            class="secondary-dark-btn"
            no-caps
          />
          <q-btn
            v-if="!device.connected"
            :loading="attemptToConnectDevice === device.address"
            @click="connectToDevice(device.address, device.name)"
            :disable="!token || !!attemptToConnectDevice"
            label="Приєднатися"
            class="primary-btn"
            no-caps
          />
        </div>
      </div>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { copy, formatDuration, parseManufacturingDate, useSessionStorage } from '../helpers/utils';
import { ref, onBeforeUnmount, computed } from 'vue';
import type { DeviceInfo } from '../models';
import { useBmsStore } from 'src/stores/bms';

const bmsStore = useBmsStore();
const token = useSessionStorage('access_token');

const devicesList = computed<DeviceInfo[]>(bmsStore.getDeviceInfo);
const attemptToConnectDevice = ref<string>('');
const disconnectDeviceState = ref<string>('');
const props = defineProps(['disconnectBtn', 'connected']);

async function connectToDevice(address: string, name: string) {
  attemptToConnectDevice.value = address;
  await bmsStore.connectToDevice(address, name);
  setTimeout(() => {
    attemptToConnectDevice.value = '';
  }, 3000);
}

async function disconnectDevice(address: string, name: string) {
  disconnectDeviceState.value = address;
  await bmsStore.disconnectDevice(address, name);
  setTimeout(() => {
    disconnectDeviceState.value = '';
  }, 3000);
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
.devices-list {
  list-style-type: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0;
  margin: 0;
  width: 100%;
}

.device-row {
  width: 100%;
}

.device-card {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(8px);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 16px 34px rgba(0, 0, 0, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.14);
}

.device-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.device-title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
}

.device-status-dot {
  width: 14px;
  height: 14px;
  min-width: 14px;
  border-radius: 50%;
  margin-top: 7px;
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.03);
}

.connected-device {
  background: #2ecc71;
  box-shadow:
    0 0 0 4px rgba(46, 204, 113, 0.12),
    0 0 14px rgba(46, 204, 113, 0.45);
}

.disconnected-device {
  background: #8b949e;
  box-shadow:
    0 0 0 4px rgba(139, 148, 158, 0.12),
    0 0 12px rgba(139, 148, 158, 0.25);
}

.device-title-block {
  min-width: 0;
}

.device-title {
  margin: 0;
  font-size: 1.12rem;
  font-weight: 700;
  line-height: 1.2;
  cursor: pointer;
  color: #fff;
  word-break: break-word;
}

.device-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.92rem;
}

.device-address {
  font-weight: 600;
  letter-spacing: 0.02em;
}

.device-vendor {
  min-width: 160px;
  text-align: right;
}

.device-content {
  margin-top: 10px;
}

.device-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
  gap: 12px;
}

.meta-card {
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.meta-label {
  display: block;
  margin-bottom: 6px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.58);
}

.meta-value {
  display: block;
  font-size: 0.98rem;
  font-weight: 600;
  color: #fff;
  word-break: break-word;
}

.accent-value {
  color: #f5c16c;
}

.device-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.primary-btn {
  background: #ffffff;
  color: #111;
  border-radius: 12px;
  padding: 0 14px;
  font-weight: 700;
  min-height: 42px;
  box-shadow: 0 8px 20px rgba(255, 255, 255, 0.08);
}

.secondary-dark-btn {
  background: rgba(255, 255, 255, 0.06);
  color: #fff;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 0 14px;
  font-weight: 700;
  min-height: 42px;
}

h2,
p {
  margin: 0;
}

@media (max-width: 720px) {
  .device-card {
    padding: 16px;
    border-radius: 16px;
  }

  .device-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .device-vendor {
    min-width: unset;
    text-align: left;
  }

  .device-meta-grid {
    grid-template-columns: 1fr;
  }

  .device-actions {
    justify-content: stretch;
    flex-direction: column;
  }
}
</style>