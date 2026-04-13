<template>
  <div class="device-row device-item">
    <div class="device-card">
      <div class="device-actions">
        <q-icon
          v-if="!loadding"
          @click="toggleDevice(device?.device_on)"
          name="power_settings_new"
          class="cursor-pointer action-icon power-icon"
          :class="{ 'is-off': device?.device_on == 0, 'is-on': device?.device_on == 1 }"
          size="2.2em"
        />
        <div v-else class="loader power-icon"></div>

        <q-icon
          v-if="!loadding"
          name="bolt"
          class="cursor-pointer action-icon auto-icon"
          :class="{
            'is-disabled': device?.auto_power_off_enabled == 0,
            'is-enabled': device?.auto_power_off_enabled == 1
          }"
          size="2em"
          @click="tapoStore?.toggleAutoPower(device)"
        >
          <q-tooltip>
            Автоматичне вимкнення при низькій генерації
          </q-tooltip>
        </q-icon>
      </div>

      <div class="device-header">
        <div class="device-title-wrap">
          <div
            :class="{
              'connected-device': device?.device_on == 1,
              'disconnected-device': device?.device_on == 0
            }"
            class="device-status-dot"
          ></div>

          <div class="device-title-block">
            <h6 @click="copy(device?.device_id)" class="device-title">
              {{ device?.name }}
            </h6>
            <div class="device-subtitle">
              <span class="device-model">{{ device?.model }}</span>
              <q-icon
                @click.prevent="openEditModal(device)"
                class="cursor-pointer edit-icon"
                name="edit"
                size="1.2em"
              />
            </div>
          </div>
        </div>
      </div>

      <div class="device-content">
        <div class="device-meta-grid">
          <div class="meta-card">
            <span class="meta-label">IP адреса</span>
            <span @click="copy(device?.ip)" class="meta-value unique clickable">{{ device?.ip }}</span>
          </div>

          <div class="meta-card">
            <span class="meta-label">Додано</span>
            <span class="meta-value">{{ new Date(device?.added_at)?.toLocaleDateString() }}</span>
          </div>

          <div class="meta-card">
            <span class="meta-label">
              Пріоритет
              <q-tooltip>
                Пріорітет пристрою, для автоматичного увімкнення чи вимкнення. Більше число, більший
                приорітет.
              </q-tooltip>
            </span>
            <span class="meta-value">[ {{ device?.priority }} ]</span>
          </div>

          <div class="meta-card">
            <span class="meta-label">
              Потужність
              <q-tooltip> Потужність підключеного приладу через цю розетку у ватах. </q-tooltip>
            </span>
            <span class="meta-value accent-value">{{ Math.floor(device?.power_watt || 0) }} Вт</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <q-dialog v-model="openModalEdit" persistent>
    <q-card dark class="edit-dialog">
      <q-card-section class="dialog-header">
        <div class="dialog-title-row">
          <div class="dialog-title-wrap">
            <q-icon
              @click.prevent="deleteDevice(device?.ip)"
              class="cursor-pointer delete-icon"
              name="delete"
              size="1.4em"
            />
            <div class="text-h6">{{ editedDeviceData?.name }}</div>
          </div>
        </div>

        <div class="dialog-meta">
          <span @click="copy(device?.hw_ver)" class="unique q-mr-sm info-chip">
            {{ device?.hw_ver }}
            <q-tooltip> Hardware version. </q-tooltip>
          </span>
          <span @click="copy(device?.fw_ver)" class="info-chip">
            {{ device?.fw_ver }}
            <q-tooltip> Software version. </q-tooltip>
          </span>
        </div>
      </q-card-section>

      <q-card-section class="q-pt-none dialog-body">
        <div class="form-row">
          <q-input
            label-color="white"
            dark
            label="Device IP Address"
            :disable="!token"
            v-model="editedDeviceData.ip"
            filled
            class="form-input"
          />
          <q-icon class="help-icon" name="help" size="2em">
            <q-tooltip>
              Щоб забезпечити стабільну роботу системи, потрібно призначити статичні IP-адреси
              для інвертора та розеток Tapo через налаштування роутера. Це запобігає випадковій
              зміні IP після перезавантаження та гарантує постійне з'єднання.
            </q-tooltip>
          </q-icon>
        </div>

        <div class="form-row">
          <q-input
            label-color="white"
            dark
            label="Priority"
            :disable="!token"
            v-model="editedDeviceData.priority"
            filled
            class="form-input"
          />
          <q-icon class="help-icon" name="help" size="2em">
            <q-tooltip>
              Пріорітет пристрою, чим вищий приорітет, тим важливіший пристрій. Наприклад
              автоматична система буде включати прилади з вищим приорітеом в першу чергу.
            </q-tooltip>
          </q-icon>
        </div>

        <div class="form-row">
          <q-input
            label-color="white"
            dark
            label="Email to Tapo application"
            :disable="!token"
            v-model="editedDeviceData.email"
            filled
            class="form-input"
          />
          <q-icon class="help-icon" name="help" size="2em">
            <q-tooltip> Необхідно для підключення до вашого девайсу. </q-tooltip>
          </q-icon>
        </div>

        <div class="form-row">
          <q-input
            label-color="white"
            dark
            label="Password to Tapo application"
            :disable="!token"
            v-model="editedDeviceData.password"
            filled
            class="form-input"
          />
          <q-icon class="help-icon" name="help" size="2em">
            <q-tooltip> Необхідно для підключення до вашого девайсу. </q-tooltip>
          </q-icon>
        </div>

        <div class="form-row">
          <q-input
            label-color="white"
            dark
            label="Device power ( W )"
            :disable="!token"
            v-model="editedDeviceData.power_watt"
            filled
            class="form-input"
          />
          <q-icon class="help-icon" name="help" size="2em">
            <q-tooltip>
              Потужність прилада, який вмикається цією розеткою Tapo. Наприклад бойлер, який
              використовує 2 кВт - вказуєте 2000 ват.
            </q-tooltip>
          </q-icon>
        </div>
      </q-card-section>

      <q-card-actions align="right" class="dialog-actions">
        <q-btn flat label="Cancel" v-close-popup class="secondary-btn" />
        <q-btn
          v-close-popup
          :loading="loadingEditDevice"
          @click="editTapoDevice"
          :disable="!token"
          label="Update"
          class="primary-btn"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { copy, useSessionStorage } from 'src/helpers/utils';
import { TapoDevice } from 'src/models';
import { UpdateTapoDeviceDto, useTapoStore } from 'src/stores/tapo';
import { computed, ref } from 'vue';

const token = useSessionStorage('access_token');
const tapoStore = useTapoStore();

const props = defineProps<{ device: TapoDevice }>();
const device = computed(() => props.device);
const openModalEdit = ref(false);
const loadingEditDevice = ref(false);
const editedTapoIp = ref('');
const loadding = ref(false);
const editedDeviceData = ref<TapoDevice & { password?: string }>({
  added_at: '',
  device_id: '',
  device_on: 0,
  email: '',
  fw_ver: '',
  password: '',
  hw_ver: '',
  id: 0,
  ip: '',
  model: '',
  name: '',
  power_watt: 0,
  priority: 0,
});

async function deleteDevice(ip: string) {
  if (!token.value) return;
  await tapoStore.removeDevice(ip);
}

async function openEditModal(device: TapoDevice) {
  editedTapoIp.value = device.ip;
  editedDeviceData.value = device;
  openModalEdit.value = true;
}

async function editTapoDevice() {
  loadingEditDevice.value = true;
  try {
    const updateData: UpdateTapoDeviceDto = {
      email: editedDeviceData.value.email,
      power_watt: editedDeviceData.value.power_watt,
      priority: editedDeviceData.value.priority,
    };
    if (editedDeviceData.value.password) {
      updateData.password = editedDeviceData.value.password;
    }

    await tapoStore.updateTapoDeviceConfig(editedTapoIp.value, updateData);
  } catch (error) {
    console.error(error);
  } finally {
    loadingEditDevice.value = false;
  }
}

async function toggleDevice(state: number) {
  if (!token.value) return;
  loadding.value = true;
  try {
    if (state == 1) {
      await tapoStore.disableDevice(props.device?.ip);
    } else {
      await tapoStore.enableDevice(props.device?.ip);
    }
  } catch (err) {
    console.error(err);
  } finally {
    loadding.value = false;
  }
}
</script>

<style scoped lang="scss">
.device-row {
  width: 100%;
  margin: 12px 0;
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

.device-actions {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.action-icon {
  border-radius: 12px;
  padding: 6px;
  transition:
    transform 0.2s ease,
    background 0.2s ease,
    color 0.2s ease;
}

.action-icon:hover {
  transform: scale(1.06);
  background: rgba(255, 255, 255, 0.08);
}

.power-icon.is-on {
  color: #ff5f57;
}

.power-icon.is-off {
  color: rgba(255, 255, 255, 0.8);
}

.auto-icon.is-enabled {
  color: #2ecc71;
}

.auto-icon.is-disabled {
  color: rgba(255, 255, 255, 0.75);
}

.device-header {
  padding-right: 110px;
  margin-bottom: 18px;
}

.device-title-wrap {
  display: flex;
  align-items: flex-start;
  gap: 14px;
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
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.2;
  cursor: pointer;
  word-break: break-word;
}

.device-subtitle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.95rem;
}

.device-model {
  font-weight: 500;
}

.edit-icon {
  opacity: 0.8;
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.edit-icon:hover {
  opacity: 1;
  transform: scale(1.05);
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

.clickable {
  cursor: pointer;
}

.edit-dialog {
  min-width: 420px;
  max-width: 560px;
  width: 100%;
  border-radius: 22px;
  overflow: hidden;
  background: #15171c;
}

.dialog-header {
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.dialog-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.dialog-title-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.delete-icon {
  color: #ff6b6b;
  transition: transform 0.2s ease;
}

.delete-icon:hover {
  transform: scale(1.06);
}

.dialog-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.info-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  color: rgba(255, 255, 255, 0.84);
  font-size: 0.85rem;
}

.dialog-body {
  padding-top: 18px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.form-input {
  flex: 1 1 auto;
}

.help-icon {
  color: rgba(255, 255, 255, 0.65);
}

.dialog-actions {
  padding: 16px 20px 20px;
  gap: 10px;
}

.primary-btn {
  background: #ffffff;
  color: #111;
  border-radius: 12px;
  padding: 0 14px;
  font-weight: 700;
}

.secondary-btn {
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.82);
}

.badge:before {
  display: none;
}

@media (max-width: 600px) {
  .device-card {
    padding: 16px;
    border-radius: 16px;
  }

  .device-header {
    padding-right: 88px;
  }

  .device-actions {
    top: 12px;
    right: 12px;
    gap: 6px;
  }

  .device-meta-grid {
    grid-template-columns: 1fr;
  }

  .edit-dialog {
    min-width: unset;
    width: calc(100vw - 24px);
  }

  .form-row {
    align-items: flex-start;
  }
}
</style>