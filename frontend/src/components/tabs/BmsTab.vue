<template>
  <div class="jk-page">
    <div class="section-intro">
      <div class="text-h6 section-title">JK-BMS Devices</div>
      <p class="section-description">
        Тут ви можете керувати своїми пристроями JK-BMS.
      </p>
    </div>

    <div class="add-device-card">
      <q-expansion-item
        :disable="!token"
        v-model="expandAddDevice"
        icon="add"
        label="Add new device"
        dark
        dense-toggle
        header-class="expansion-header"
      >
        <div class="expansion-content">
          <div class="search-actions">
            <q-btn
              :loading="loadingDevices"
              @click="fetchDevices"
              :disable="!token"
              label="Пошук нових пристроїв"
              class="primary-btn"
            />
          </div>

          <template v-if="devices.length">
            <div class="found-devices-block">
              <h6 class="found-title">Знайдені пристрої</h6>
              <p class="found-description">
                Щоб приєднатися до пристрою, просто натисніть на нього. Доданий вами девайс буде
                підключений приблизно за 10 секунд і ви зможете побачити його на головному екрані.
              </p>

              <q-list class="devices-found-list">
                <q-item
                  v-for="device of devices"
                  :key="device.address"
                  clickable
                  :disable="!!attemptToConnectDevice"
                  :active="attemptToConnectDevice === device.address"
                  @click="token && connectToDevice(device.address, device.name)"
                  v-ripple
                  class="device-found-item"
                  active-class="device-found-item-active"
                >
                  <q-item-section avatar>
                    <div
                      class="device-found-dot"
                      :class="{
                        'is-connecting': attemptToConnectDevice === device.address
                      }"
                    ></div>
                  </q-item-section>

                  <q-item-section>
                    <div class="device-found-content">
                      <div class="device-found-name">
                        {{
                          attemptToConnectDevice === device.address
                            ? `Підключення до ${device?.name}`
                            : device?.name
                        }}
                      </div>
                      <div class="device-found-address">
                        {{ device?.address }}
                      </div>
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </template>

          <template v-if="notFoundDevices">
            <div class="empty-state-card">
              <div class="empty-state-title">Нових пристроїв JK-BMS не знайдено</div>
              <div class="empty-state-text">
                Спробуйте повторити пошук трохи пізніше або переконайтеся, що пристрої доступні для
                сканування.
              </div>
            </div>
          </template>
        </div>
      </q-expansion-item>
    </div>

    <q-separator class="section-separator" color="white" />

    <div class="devices-list-wrap">
      <DevicesList :disconnect-btn="true" />
    </div>
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
const expandAddDevice = ref(false);

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

<style scoped lang="scss">
.jk-page {
  width: 100%;
}

.section-intro {
  margin-bottom: 14px;
}

.section-title {
  font-weight: 700;
  letter-spacing: 0.01em;
}

.section-description {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.96rem;
}

.add-device-card {
  overflow: hidden;
  border-radius: 20px;
  margin-top: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(8px);
}

.expansion-content {
  padding: 6px 16px 18px;
}

:deep(.block) {
  color: black;
}

.search-actions {
  display: flex;
  justify-content: center;
}

.primary-btn {
  background: #ffffff;
  color: #111;
  border-radius: 12px;
  padding: 0 14px;
  font-weight: 700;
}

.found-devices-block {
  margin-top: 18px;
}

.found-title {
  margin: 0 0 8px;
  font-size: 1.02rem;
  font-weight: 700;
  color: #fff;
}

.found-description {
  margin: 0 0 14px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.76);
}

.devices-found-list {
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.device-found-item {
  min-height: 68px;
  padding: 10px 14px;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}

.device-found-item + .device-found-item {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.device-found-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.device-found-item-active {
  background: rgba(255, 255, 255, 0.08);
}

.device-found-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #8b949e;
  box-shadow:
    0 0 0 4px rgba(139, 148, 158, 0.12),
    0 0 10px rgba(139, 148, 158, 0.25);
}

.device-found-dot.is-connecting {
  background: #f5c16c;
  box-shadow:
    0 0 0 4px rgba(245, 193, 108, 0.12),
    0 0 12px rgba(245, 193, 108, 0.45);
}

.device-found-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.device-found-name {
  font-size: 0.98rem;
  font-weight: 700;
  color: #fff;
  word-break: break-word;
}

.device-found-address {
  margin-top: 4px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.56);
  word-break: break-word;
}

.empty-state-card {
  margin-top: 18px;
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.empty-state-title {
  font-size: 0.98rem;
  font-weight: 700;
  color: #fff;
}

.empty-state-text {
  margin-top: 6px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.92rem;
}

.section-separator {
  margin: 22px 0 18px;
  opacity: 0.35;
}

.devices-list-wrap {
  width: 100%;
}

@media (max-width: 720px) {
  .add-device-card {
    border-radius: 16px;
  }

  .expansion-content {
    padding: 6px 12px 14px;
  }

  .device-found-item {
    padding: 10px 12px;
  }
}
</style>