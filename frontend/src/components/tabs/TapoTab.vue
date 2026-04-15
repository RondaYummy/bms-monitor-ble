<template>
  <div class="tapo-page">
    <div class="section-intro">
      <div class="text-h6 section-title">TP-Link Tapo Devices</div>
      <p class="section-description">
        Тут ви можете керувати своїми пристроями Tapo.
      </p>
    </div>

    <div class="add-device-card">
      <q-expansion-item
        :disable="!token"
        v-model="expandAddTapoDevice"
        icon="add"
        label="Add new device"
        dark
        dense-toggle
        class="styled-expansion"
      >
        <div class="expansion-content">
          <p class="expansion-description">
            Перш ніж додати новий пристрій TP-Link Tapo, переконайтесь, що він уже доданий в офіційний
            застосунок Tapo. Після цього введіть у поля нижче ваші облікові дані (email та пароль) — це
            необхідно для авторизації та доступу до ваших пристроїв.
          </p>

          <div class="form-grid">
            <q-input
              label-color="white"
              label="Email from Tapo App"
              :disable="!token"
              v-model="newTapoDevice.email"
              filled
              class="form-input"
            />
            <q-input
              label-color="white"
              label="Password from Tapo App"
              :disable="!token"
              v-model="newTapoDevice.password"
              filled
              class="form-input"
            />
          </div>

          <div class="search-actions">
            <q-btn
              :loading="loadingTapoDevices"
              @click="searchTapoDevices"
              :disable="!token || !newTapoDevice.email || !newTapoDevice.password"
              label="Шукати пристрої Tapo"
              class="primary-btn search-btn"
              no-caps
            />
          </div>

          <template v-if="!tapoStore.foundDevices?.length">
            <div class="empty-state-card">
              <div class="empty-state-title">Нових пристроїв TP-Link Tapo не знайдено</div>
              <div class="empty-state-text">
                Перевірте облікові дані Tapo та спробуйте виконати пошук ще раз.
              </div>
            </div>
          </template>

          <template v-if="tapoStore.foundDevices?.length">
            <div class="found-devices-block">
              <h6 class="found-title">Знайдено нові пристрої TP-Link Tapo</h6>

              <q-list class="devices-found-list">
                <q-item
                  v-for="device of tapoStore.foundDevices"
                  :key="device?.ip"
                  clickable
                  :disable="openModalAddTapo"
                  @click="token && openModalAddTapoDevice(device)"
                  v-ripple
                  class="device-found-item"
                >
                  <q-item-section avatar>
                    <div class="device-found-dot"></div>
                  </q-item-section>

                  <q-item-section>
                    <div class="device-found-content">
                      <div class="device-found-name">{{ device?.name }}</div>
                      <div class="device-found-meta">{{ device?.ip }} · {{ device?.model }}</div>
                    </div>
                  </q-item-section>
                </q-item>
              </q-list>
            </div>
          </template>

          <q-dialog v-model="openModalAddTapo" persistent>
            <q-card dark class="edit-dialog">
              <q-card-section class="dialog-header">
                <div class="dialog-title-row">
                  <div class="dialog-title-wrap">
                    <div class="text-h6">{{ modalAddTapoDeviceData?.nmae }}</div>
                  </div>
                </div>
              </q-card-section>

              <q-card-section class="q-pt-none dialog-body">
                <div class="form-row">
                  <q-input
                    label-color="white"
                    label="Device IP Address"
                    :disable="!token"
                    v-model="newTapoDevice.ip"
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
                    label="Priority"
                    :disable="!token"
                    v-model="newTapoDevice.priority"
                    filled
                    class="form-input"
                  />
                  <q-icon class="help-icon" name="help" size="2em">
                    <q-tooltip>
                      Приорітет пристрою, чим вищий приорітет, тим важливіший пристрій. Наприклад
                      автоматична система буде включати прилади з вищим приорітеом в першу чергу.
                    </q-tooltip>
                  </q-icon>
                </div>

                <div class="form-row">
                  <q-input
                    label-color="white"
                    label="Device power ( W )"
                    :disable="!token"
                    v-model="newTapoDevice.power_watt"
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
                  :loading="loadingDevices"
                  @click="addTapoDevice"
                  :disable="!token || !newTapoDevice.ip || !newTapoDevice.email || !newTapoDevice.password"
                  label="Додати новий пристрій"
                  class="primary-btn"
                  no-caps
                />
              </q-card-actions>
            </q-card>
          </q-dialog>
        </div>
      </q-expansion-item>
    </div>

    <q-separator class="section-separator" color="white" />

    <div class="devices-list-wrap">
      <TapoDevicesList />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import TapoDevicesList from '../tapo/TapoDevicesList.vue';
import { useTapoStore } from 'src/stores/tapo';
import { useSessionStorage } from 'src/helpers/utils';

const tapoStore = useTapoStore();

const token = useSessionStorage('access_token');

const loadingDevices = ref<boolean>(false);
const expandAddTapoDevice = ref(false);
const loadingTapoDevices = ref<boolean>(false);
const openModalAddTapo = ref<boolean>(false);
const modalAddTapoDeviceData = ref();
const intervalId = ref();
const newTapoDevice = ref({ ip: '', email: '', password: '', power_watt: 0, priority: 1 });

async function openModalAddTapoDevice(device: any) {
  modalAddTapoDeviceData.value = device;
  openModalAddTapo.value = true;
  newTapoDevice.value.ip = device?.ip;
}

async function searchTapoDevices() {
  loadingTapoDevices.value = true;
  try {
    await tapoStore.searchTapoDevices({
      email: newTapoDevice.value.email,
      password: newTapoDevice.value.password,
    });
  } catch (error) {
    console.error(error);
  } finally {
    loadingTapoDevices.value = false;
  }
}

async function addTapoDevice() {
  await tapoStore.addDevice({
    ip: newTapoDevice.value.ip,
    email: newTapoDevice.value.email,
    password: newTapoDevice.value.password,
    power_watt: newTapoDevice.value?.power_watt,
    priority: newTapoDevice.value?.priority,
  });
  newTapoDevice.value.ip = '';
}

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await tapoStore.fetchDevices();
  }, 5000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

tapoStore.fetchDevices();
</script>

<style scoped lang="scss">
.tapo-page {
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

.styled-expansion :deep(.q-item) {
  min-height: 72px;
  padding: 16px 18px;
  border-radius: 18px;
}

.styled-expansion :deep(.q-item__section--avatar) {
  min-width: 40px;
}

.styled-expansion :deep(.q-item__label) {
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  letter-spacing: 0.01em;
}

.styled-expansion :deep(.q-icon) {
  color: rgba(255, 255, 255, 0.9);
}

.styled-expansion :deep(.q-expansion-item__toggle-icon) {
  transition: transform 0.25s ease;
}

.styled-expansion :deep(.q-expansion-item__content) {
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.styled-expansion :deep(.q-focus-helper) {
  display: none;
}

.expansion-content {
  padding: 14px 18px 18px;
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
  flex: 1 1 auto;
}

.search-actions {
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
  min-height: 42px;
  box-shadow: 0 8px 20px rgba(255, 255, 255, 0.08);
}

.search-btn {
  border: 1px solid rgba(255, 255, 255, 0.12);
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

.found-devices-block {
  margin-top: 18px;
}

.found-title {
  margin: 0 0 12px;
  font-size: 1.02rem;
  font-weight: 700;
  color: #fff;
}

.devices-found-list {
  border-radius: 16px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.device-found-item {
  min-height: 70px;
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

.device-found-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #2ecc71;
  box-shadow:
    0 0 0 4px rgba(46, 204, 113, 0.12),
    0 0 12px rgba(46, 204, 113, 0.35);
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

.device-found-meta {
  margin-top: 4px;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.56);
  word-break: break-word;
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

.dialog-body {
  padding-top: 18px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.help-icon {
  color: rgba(255, 255, 255, 0.65);
}

.dialog-actions {
  padding: 16px 20px 20px;
  gap: 10px;
}

.secondary-btn {
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.82);
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

  .styled-expansion :deep(.q-item) {
    min-height: 64px;
    padding: 14px 14px;
  }

  .expansion-content {
    padding: 12px 14px 14px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .device-found-item {
    padding: 10px 12px;
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