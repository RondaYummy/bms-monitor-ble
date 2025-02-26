<template>
  <q-page class="column items-center q-pa-lg">
    <p class='unique text-center full-width'
       v-if='!token'>
      Щоб мати можливість змінювати налаштування, будь ласка, авторизуйтеся.
    </p>
    <p class='charge text-center full-width'
       v-if='token'>
      Ви успішно авторизовані та можете змінювати налаштування.
    </p>

    <div class='row justify-center no-wrap q-gutter-sm q-mb-md'
         v-if='!token'>
      <q-input v-model="password"
               dense
               outlined
               label="Введіть пароль"
               label-color="white"
               color="white"
               :type="isPwd ? 'password' : 'text'">
        <template v-slot:append>
          <q-icon :name="isPwd ? 'visibility_off' : 'visibility'"
                  class="cursor-pointer text-white"
                  @click="isPwd = !isPwd" />
        </template>
      </q-input>
      <q-btn @click="login(password)"
             color="black"
             label="Підтвердити" />
    </div>

    <div>
      <q-tabs v-model="tab"
              align="justify"
              narrow-indicator
              class="q-mb-lg">
        <q-tab class="text-purple"
               name="Alerts"
               label="Alerts" />
        <q-tab class="text-orange"
               name="Settings"
               label="Settings" />
        <q-tab class="text-blue"
               name="Devices"
               label="Devices" />
      </q-tabs>

      <div class="q-gutter-y-sm">
        <q-tab-panels v-model="tab"
                      animated
                      transition-prev="scale"
                      transition-next="scale"
                      class="text-white text-center transparent">
          <q-tab-panel name="Alerts">
            <div class="text-h6">Alerts</div>

            <div class='column items-center justify-center'>
              <p>
                Тут ви можете переглянути всі важливі сповіщення про роботу
                системи.
              </p>

              <div class='row justify-center'>
                <q-chip @click="filterAlertsByLevel()"
                        outline
                        clickable
                        color="white"
                        icon="apps">
                  All
                </q-chip>
                <q-chip @click="filterAlertsByLevel('info')"
                        outline
                        clickable
                        color="primary"
                        icon="priority_high">
                  Info
                </q-chip>
                <q-chip @click="filterAlertsByLevel('warning')"
                        outline
                        clickable
                        color="orange"
                        icon="warning">
                  Warning
                </q-chip>
                <q-chip @click="filterAlertsByLevel('error')"
                        outline
                        clickable
                        color="deep-orange"
                        icon="error">
                  Error
                </q-chip>
                <q-chip @click="filterAlertsByLevel('critical')"
                        outline
                        clickable
                        color="red"
                        icon="flash_on">
                  Critical
                </q-chip>
              </div>
            </div>

            <div class='column alerts-box'>
              <q-banner v-for="alert of alerts"
                        :key="alert?.id"
                        v-touch-swipe.mouse.right.left="() => token && deleteErrorAlert(alert?.id)"
                        inline-actions
                        :class="{
                          'bg-negative': alert?.level === 'critical',
                          'bg-red': alert?.level === 'error',
                          'bg-orange': alert?.level === 'warning',
                          'bg-bg-primary': alert?.level === 'info',
                        }"
                        class="text-white q-mt-sm q-mb-sm cursor-pointer">
                <div class="column">
                  <div class='row justify-between'>
                    <q-chip outline
                            color="white"
                            text-color="white"
                            :icon="getAlertIcon(alert?.level)">
                      {{ alert?.device_name }}
                    </q-chip>

                    <div class="row items-center">
                      <q-badge outline
                               color="white"
                               :label="alert?.error_code" />
                    </div>

                    <span class='row items-center'>
                      {{ formatTimestamp(alert?.timestamp) }}
                    </span>
                  </div>

                  <p v-if="alert?.id"
                     class='q-mt-md text-left'>
                    {{ alert?.message }}
                  </p>
                </div>

              </q-banner>

              <p v-if="!alerts?.length"
                 class="level q-mt-md">
                {{ selectedLevel ? `"${selectedLevel}" повідомлення не
                знайдено.` : `Повідомлень не знайдено.` }}
              </p>
            </div>
          </q-tab-panel>

          <q-tab-panel name="Settings">
            <p class='text-caption'>
              Цей пароль, для доступу до налаштувань вашого додатку.
            </p>

            <q-btn class="q-mt-md"
                   @click="changePasswordModal = true"
                   color="black"
                   :disable="!token"
                   label="Змінити пароль" />
            <ChangePasswordModal @update:show="(value) => changePasswordModal = value"
                                 :show="changePasswordModal" />

            <q-separator class="q-mt-md"
                         color="orange"
                         inset />

            <div class='column'>
              <p class='text-caption'>
                PUSH сповіщення - це спливаюче повідомлення на екрані смартфона.
              </p>

              <q-btn class="q-mt-md"
                     @click="subscribePush"
                     color="black"
                     :disable="!token || !!pushSubscription"
                     label="Підписатись на PUSH" />
              <q-btn class="q-mt-md"
                     @click="cancelSubs"
                     color="black"
                     :disable="!token || !pushSubscription"
                     label="Скасувати підписки" />
            </div>

            <q-separator class="q-mt-md"
                         color="orange"
                         inset />

            <div class="column q-mt-md q-mb-md"
                 v-if="config">
              <q-btn class="q-mt-md"
                     @click="alertsModal = true"
                     color="black"
                     :disable="!token"
                     label="Налаштування Alerts" />
              <AlertsSettingsModal :config="config"
                                   :show="alertsModal"
                                   @update:show="alertsModal = !alertsModal" />

              <q-separator class="q-mt-md"
                           color="orange"
                           inset />

              <p class='text-caption'>
                Щоб переглянути налаштування вашого JK-BMS, оберіть пристрій.
              </p>
              <q-btn-dropdown v-if="settings?.length"
                              class="q-mt-md"
                              auto-close
                              stretch
                              flat
                              style='flex: 1 1 50%;'
                              label="Оберіть пристрій">

                <q-list v-if="settings?.length">
                  <q-item clickable
                          v-for="setting of settings"
                          class="text-black"
                          :key="setting?.address"
                          :name="setting?.name"
                          :label="setting?.name"
                          @click="currentSetting = setting">
                    <q-item-section>{{ setting?.name }}</q-item-section>
                  </q-item>
                </q-list>
              </q-btn-dropdown>

              <template v-if="currentSetting">
                <ToggleButton :value="currentSetting?.charge_switch"
                              title="Charge" />
                <ToggleButton :value="currentSetting?.discharge_switch"
                              title="Discharge" />
                <ToggleButton :value="currentSetting?.balancer_switch"
                              title="Balance" />
                <!-- <ToggleButton :value="currentSetting?."
                            title="Emergency" /> -->
                <ToggleButton :value="currentSetting?.heating_enabled"
                              title="Heating" />
                <ToggleButton :value="currentSetting?.disable_temperature_sensors"
                              title="Disable Temp. Sensor" />
                <ToggleButton :value="currentSetting?.display_always_on"
                              title="Display Always On" />
                <ToggleButton :value="currentSetting?.special_charger"
                              title="Special Charger On" />
                <ToggleButton :value="currentSetting?.smart_sleep"
                              title="Smart Sleep On" />
                <ToggleButton :value="currentSetting?.timed_stored_data"
                              title="Timed Stored Data" />
                <ToggleButton :value="currentSetting?.charging_float_mode"
                              title="Charging Float Mode" />
                <ToggleButton :value="currentSetting?.gps_heartbeat"
                              title="GPS Heartbeat" />
                <ToggleButton :value="currentSetting?.disable_pcl_module"
                              title="Disable PCL Module" />
                <ToggleButton :value="currentSetting?.charge_utpr"
                              title="Charge UTPR" />

                <SettingsList :settings="currentSetting" />
              </template>

              <q-separator class="q-mt-md"
                           color="orange"
                           inset />
            </div>
          </q-tab-panel>

          <q-tab-panel name="Devices">
            <div class="text-h6">Devices</div>
            <p>Тут ви можете керувати своїми пристроями.</p>

            <q-btn :loading="loadingDevices"
                   @click="fetchDevices"
                   :disable="!token"
                   color="black"
                   label="Пошук нових пристроїв" />


            <template v-if='devices.length'>
              <h6 class="q-mt-md">Знайдені пристрої:</h6>
              <p>
                Щоб приєднатися до пристрою, просто натисніть на нього.
                Доданий
                вами девайс, буде підключений приблизно за 10 секунд і ви
                зможете побачити його на головному екрані.
              </p>
              <q-list bordered
                      separator>
                <q-item v-for="device of devices"
                        :key="device.address"
                        clickable
                        :disable="!!attemptToConnectDevice"
                        :active="attemptToConnectDevice === device.address"
                        @click="token && connectToDevice(device.address, device.name)"
                        v-ripple>
                  <q-item-section>{{ attemptToConnectDevice === device.address ? `Підключення до ${device?.name}` : device?.name }}</q-item-section>
                </q-item>
              </q-list>
            </template>
            <template v-if="notFoundDevices">
              <h6 class="q-mt-md">
                Нових пристроїв JK-BMS не знайдено.
              </h6>
            </template>

            <q-separator class="q-mt-md"
                         color="white" />

            <div>
              <div class="text-h6 q-mt-md">Ваші пристрої:</div>
              <DevicesList :disconnect-btn="true"
                           :token="token" />
            </div>
          </q-tab-panel>
        </q-tab-panels>
      </div>
    </div>
  </q-page>
</template>

<script setup lang='ts'>
import { ref, onMounted } from 'vue';
import { checkResponse, useSessionStorage } from '../helpers/utils';
import type { Alert, Device, Config } from '../models';
import DevicesList from '../components/DevicesList.vue';
import ToggleButton from '../components/ToggleButton.vue';
import SettingsList from '../components/SettingsList.vue';
import ChangePasswordModal from 'src/components/modals/ChangePasswordModal.vue';
import { cancelAllSubscriptions, checkPushSubscription, usePush } from 'src/composables/usePush';
import AlertsSettingsModal from 'src/components/modals/AlertsSettingsModal.vue';

const tab = ref('Alerts');
const password = ref('');
const isPwd = ref(true);
const loadingDevices = ref(false);
const devices = ref<Device[]>([]);
const attemptToConnectDevice = ref();
const notFoundDevices = ref(false);
const alertsModal = ref(false);

const pushSubscription = ref<PushSubscription | null>(null);
const changePasswordModal = ref(false);
const selectedLevel = ref();
const alerts = ref<Alert[]>();
const alertsMain = ref<Alert[]>();
const token = useSessionStorage("access_token");
const config = ref<Config>();
const settings = ref();
const currentSetting = ref();

function filterAlertsByLevel(level?: string): void {
  console.log('Selected level: ', level);
  if (!level) {
    alerts.value = alertsMain.value;
    return;
  }
  selectedLevel.value = level;
  alerts.value = alertsMain.value?.filter((a) => a.level === level);
}

function formatTimestamp(timestamp?: any): string {
  if (!timestamp) {
    return 'Invalid timestamp';
  }

  const cleanTimestamp = timestamp.split('.')[0];
  const date = new Date(cleanTimestamp.replace(' ', 'T'));

  if (isNaN(date.getTime())) {
    return 'Invalid date';
  }

  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0'); // Months from 0 to 11
  const year = String(date.getFullYear()).slice(2); // Last two digits of the year
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${month}.${day}.${year} ${hours}.${minutes}`;
}

function getAlertIcon(level: string | undefined): string {
  if (level === 'info') return 'priority_high';
  if (level === 'warning') return 'warning';
  if (level === 'error') return 'error';
  if (level === 'critical') return 'flash_on';
  return '';
}

async function fetchErrorAlerts() {
  try {
    const response = await fetch('/api/error-alerts');
    if (response.status === 404) {
      alerts.value = [];
      alertsMain.value = [];
      return;
    }
    checkResponse(response);
    const data = await response.json();
    alerts.value = data;
    alertsMain.value = data;
  } catch (error) {
    console.error('Error fetching error alerts:', error);
  }
}

async function fetchConfigs() {
  try {
    const response = await fetch('/api/configs');
    checkResponse(response);
    const data = await response.json();
    config.value = data;
  } catch (error) {
    console.error('Error fetching configs:', error);
  }
}

async function fetchSettings() {
  try {
    const response = await fetch('/api/device-settings');
    checkResponse(response);
    const data = await response.json();
    settings.value = data;
  } catch (error) {
    console.error('Error fetching configs:', error);
  }
}

async function cancelSubs() {
  await cancelAllSubscriptions(true);
  setTimeout(async () => {
    pushSubscription.value = await checkPushSubscription();
  }, 1000);
}

async function subscribePush() {
  const { subscribeToPush } = usePush();
  await subscribeToPush();
  setTimeout(async () => {
    pushSubscription.value = await checkPushSubscription();
  }, 1000);
}

async function deleteErrorAlert(id: number) {
  try {
    token.value = sessionStorage.getItem("access_token");
    const response = await fetch('/api/error-alerts', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token.value}`
      },
      body: JSON.stringify({ id: id }),
    });
    checkResponse(response);
    fetchErrorAlerts();
  } catch (error) {
    console.error('Error remove error alerts:', error);
  }
}

const login = async (pwd: string) => {
  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password: pwd }),
  });
  checkResponse(response);

  const data = await response.json();
  sessionStorage.setItem("access_token", data.access_token);
  token.value = data?.access_token;
  password.value = '';
  console.log("Login successful");
  return true;
};

async function fetchDevices() {
  try {
    loadingDevices.value = true;
    notFoundDevices.value = false;
    const response = await fetch('/api/devices');
    if (!response?.ok) {
      notFoundDevices.value = true;
    }
    checkResponse(response);
    const data = await response.json();
    devices.value = data?.devices;
    console.log('Discovered devices: ', data);
  } catch (error) {
    console.error(error);
  } finally {
    loadingDevices.value = false;
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
  devices.value = devices.value?.filter((d) => d.address !== address);
  attemptToConnectDevice.value = '';
}

onMounted(async () => {
  pushSubscription.value = await checkPushSubscription();

  setTimeout(async () => {
    pushSubscription.value = await checkPushSubscription();
  }, 2000);
});

fetchErrorAlerts();
fetchConfigs();
fetchSettings();
</script>

<style scoped lang='scss'>
.alerts-box {
  gap: 10px;
}

.level {
  text-transform: capitalize;
  font-weight: 600;
}

:deep(.q-field__native) {
  color: white !important;
}
</style>
