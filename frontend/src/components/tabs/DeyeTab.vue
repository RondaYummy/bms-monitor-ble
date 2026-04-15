<template>
  <div class="deye-page">
    <div class="section-intro">
      <div class="text-h6 section-title">Deye Inverter Devices</div>
      <p class="section-description">
        Тут ви можете керувати своїми пристроями Deye.
      </p>
    </div>

    <div class="add-device-card">
      <q-expansion-item
        :disable="!token"
        v-model="expandAddDeyeDevice"
        icon="add"
        label="Add new device"
        dark
        dense-toggle
        header-class="expansion-header"
      >
        <div class="expansion-content">
          <p class="expansion-description">
            Перш ніж додати ваш інвертор Deye, необхідно дізнатися IP-адресу Wi-Fi стіка та серійний номер
            пристрою. Рекомендуємо призначити статичну IP-адресу, щоб уникнути збоїв у роботі.
          </p>

          <div class="form-grid">
            <q-input
              label-color="white"
              label="Device IP Address"
              :disable="!token"
              v-model="createDeye.ip"
              filled
              class="form-input"
            />
            <q-input
              label-color="white"
              label="Device Serial Number"
              :disable="!token"
              v-model="createDeye.serial_number"
              filled
              class="form-input"
            />
          </div>

          <div class="add-device-actions">
            <q-btn
              :loading="loading"
              @click="createDeyeDevice"
              :disable="!token || !createDeye.ip || !createDeye.serial_number"
              label="Додати інвертор"
              class="primary-btn"
            />
          </div>
        </div>
      </q-expansion-item>
    </div>

    <q-separator class="section-separator" color="white" />

    <div class="device-list">
      <div v-for="item of deyeStore?.deyeData" :key="item?.serial_number" class="device-row">
        <div class="deye-item">
          <div class="device-top">
            <div class="device-top-left">
              <q-icon
                @click.prevent="deleteDevice(item?.ip)"
                class="cursor-pointer remove"
                name="delete"
                size="1.3em"
                color="red"
              />
              <div class="device-main-info">
                <div class="device-id" @click="copy(item?.id)">
                  <span class="meta-label">ID</span>
                  <span class="meta-value">{{ item?.id }}</span>
                </div>
              </div>
            </div>

            <div
              class="status-badge"
              :class="item?.device_on == 0 ? 'status-off' : 'status-on'"
            >
              <span class="status-dot"></span>
              {{ item?.device_on == 0 ? 'Disabled' : 'Enabled' }}
            </div>
          </div>

          <div class="device-meta-grid">
            <div class="meta-card" @click="copy(item?.serial_number)">
              <span class="meta-title">
                SN
                <q-tooltip> Серійний номер пристрою. </q-tooltip>
              </span>
              <span class="meta-text">{{ item?.serial_number }}</span>
            </div>

            <div class="meta-card" @click="copy(item?.ip)">
              <span class="meta-title">IP</span>
              <span class="meta-text">{{ item?.ip }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { copy, useSessionStorage } from 'src/helpers/utils';
import { useDeyeStore } from 'src/stores/deye';
import { Notify } from 'quasar';

const deyeStore = useDeyeStore();

const token = useSessionStorage('access_token');

const expandAddDeyeDevice = ref(false);
const intervalId = ref();
const loading = ref(false);
const createDeye = ref({ ip: '', serial_number: '' });

async function createDeyeDevice() {
  try {
    loading.value = true;
    await deyeStore.createDeyeDevice({
      ip: createDeye.value.ip,
      serial_number: createDeye.value.serial_number,
      slave_id: 1,
    });
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

async function deleteDevice(ip: string) {
  try {
    await deyeStore.deleteDeyeDevice(ip);
    Notify.create({
      message: 'Ви успішно видалили пристрій',
      color: 'secondary',
      position: 'top',
    });
  } catch (error) {
    console.error(error);
    Notify.create({
      message: 'Сталася помилка під час видалення пристрою',
      color: 'red',
      icon: 'warning',
      position: 'top',
      timeout: 2000,
    });
  }
}

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await Promise.allSettled([deyeStore.fetchDeyeDevices()]);
  }, 5000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

deyeStore.fetchDeyeDevices();
</script>

<style scoped lang="scss">
.deye-page {
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

.expansion-description {
  margin: 0 0 16px;
  line-height: 1.55;
  color: rgba(255, 255, 255, 0.78);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.form-input {
  margin: 0;
}

.add-device-actions {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

:deep(.block) {
  color: black;
}

.primary-btn {
  background: #ffffff;
  color: #111;
  border-radius: 12px;
  padding: 0 14px;
  font-weight: 700;
}

.section-separator {
  margin: 22px 0 18px;
  opacity: 0.35;
}

.device-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.device-row {
  width: 100%;
}

.deye-item {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  border-radius: 20px;
  padding: 18px;
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.deye-item:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.14);
  box-shadow:
    0 16px 34px rgba(0, 0, 0, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.device-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.device-top-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.device-main-info {
  min-width: 0;
}

.device-id {
  display: flex;
  flex-direction: column;
  cursor: pointer;
}

.meta-label {
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.52);
  margin-bottom: 4px;
}

.meta-value {
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  word-break: break-word;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.9rem;
  font-weight: 700;
  white-space: nowrap;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-on {
  color: #7ee2a8;
  background: rgba(46, 204, 113, 0.12);
  border: 1px solid rgba(46, 204, 113, 0.24);
}

.status-on .status-dot {
  background: #2ecc71;
  box-shadow: 0 0 10px rgba(46, 204, 113, 0.55);
}

.status-off {
  color: #ff8e8e;
  background: rgba(239, 67, 67, 0.12);
  border: 1px solid rgba(239, 67, 67, 0.24);
}

.status-off .status-dot {
  background: #ef4343;
  box-shadow: 0 0 10px rgba(239, 67, 67, 0.45);
}

.device-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 16px;
}

.meta-card {
  display: flex;
  flex-direction: column;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition:
    background 0.2s ease,
    border-color 0.2s ease;
}

.meta-card:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
}

.meta-title {
  margin-bottom: 6px;
  font-size: 0.76rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.56);
}

.meta-text {
  font-size: 0.96rem;
  font-weight: 600;
  color: #fff;
  word-break: break-word;
}

.remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(239, 67, 67, 0.1);
  border: 1px solid rgba(239, 67, 67, 0.18);
  padding: 8px;
  border-radius: 12px;
  transition:
    transform 0.2s ease,
    background-color 0.2s ease;
}

.remove:hover {
  transform: scale(1.05);
  background-color: rgba(239, 67, 67, 0.16);
}

@media (max-width: 720px) {
  .form-grid,
  .device-meta-grid {
    grid-template-columns: 1fr;
  }

  .device-top {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-badge {
    align-self: flex-start;
  }

  .deye-item {
    padding: 16px;
    border-radius: 16px;
  }
}

:deep(.block) {
  color: black;
}

:deep(.q-spinner) {
  color: black;
}

:deep(.q-field__native) {
  color: white;
}
</style>