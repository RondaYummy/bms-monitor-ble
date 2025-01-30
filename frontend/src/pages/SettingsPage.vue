<template>
  <div class="q-pa-md">
    <div class='row justify-center q-gutter-sm q-mb-md'
         v-if='!token'>
      <p class='text-center full-width'>
        Щоб мати можливість змінювати налаштування, будь ласка, авторизуйтеся.
      </p>
      <q-input filled
               v-model="password"
               outlined
               label="Введіть пароль"
               label-color="white"
               dense />
      <q-btn @click="login(password)"
             color="black"
             label="Авторизуватись" />
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
                        v-touch-hold.mouse="() => token && handleHold(alert)"
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

                  <p v-if="alert?.id !== holdAlert?.id"
                     class='q-mt-md text-left'>{{ alert?.message }}</p>
                  <div v-else>
                    <q-btn @click="deleteErrorAlert"
                           color="black"
                           label="Видалити сповіщення" />
                  </div>
                </div>

              </q-banner>

              <p v-if="!alerts?.length"
                 class="level q-mt-md">
                Жодних {{ selectedLevel ? `"${selectedLevel}"` : '' }}
                повідомлень не знайдено.
              </p>
            </div>
          </q-tab-panel>

          <q-tab-panel name="Settings">
            <div class="text-h6">Settings</div>
            Тут будуть ваші налаштування...
          </q-tab-panel>

          <q-tab-panel name="Devices">
            <div class="text-h6">Devices</div>
            <p>Тут ви можете керувати вашими пристроями...</p>

            <q-btn :loading="loadingDevices"
                   @click="token && fetchDevices"
                   :disable="!token"
                   color="black"
                   label="Пошук пристроїв" />


            <template v-if='devices.length'>
              <h6 class="q-mt-md">Знайдені пристрої:</h6>
              <p>Щоб приєднатись до девайсу, просто нажміть на нього. Доданий
                вами девайс, буде підключений приблизно за 10 секунд і ви
                зможете побачити його на головному екрані.</p>
              <q-list bordered
                      separator>
                <q-item v-for="device of devices"
                        :key="device.address"
                        clickable
                        @click="token && connectToDevice(device.address)"
                        v-ripple>
                  <q-item-section>{{ device?.name }}</q-item-section>
                </q-item>
              </q-list>
            </template>

            <template>
              <div class="text-h6">Ваші підключені пристрої:</div>

              <DevicesList :disconnect-btn="true" />
            </template>
          </q-tab-panel>
        </q-tab-panels>
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue';
import { useSessionStorage } from '../helpers/utils';
import type { Alert, Device } from '../models';
import DevicesList from '../components/DevicesList.vue';

const tab = ref('Alerts');
const password = ref('');
const loadingDevices = ref(false);
const devices = ref<Device[]>([]);
const selectedLevel = ref();
const alerts = ref<Alert[]>();
const alertsMain = ref<Alert[]>();
const holdAlert = ref<Alert>();
const token = useSessionStorage("access_token");

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
  const month = String(date.getMonth() + 1).padStart(2, '0'); // Місяці від 0 до 11
  const year = String(date.getFullYear()).slice(2); // Останні дві цифри року
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

function handleHold(alert: Alert): void {
  holdAlert.value = alert;
}

function checkResponse(response: Response) {
  if (!response.ok) {
    throw new Error('Failed to error alerts');
  }
  if (response.status === 301) {
    sessionStorage.removeItem('access_token');
    throw new Error('Have no access');
  }
}

async function fetchErrorAlerts() {
  try {
    const response = await fetch('/api/error-alerts');
    checkResponse(response);
    const data = await response.json();
    console.log('Error alerts:', data);
    alerts.value = data;
    alertsMain.value = data;
  } catch (error) {
    console.error('Error fetching error alerts:', error);
  }
}

async function deleteErrorAlert() {
  try {
    token.value = sessionStorage.getItem("access_token");
    const response = await fetch('/api/error-alerts', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token.value}`
      },
      body: JSON.stringify({ id: holdAlert.value?.id }),
    });
    checkResponse(response);
    fetchErrorAlerts();
  } catch (error) {
    console.error('Error remove error alerts:', error);
  }
}

const login = async (password: string) => {
  const response = await fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  checkResponse(response);

  const data = await response.json();
  sessionStorage.setItem("access_token", data.access_token);
  token.value = data?.access_token;
  console.log("Login successful");
  return true;
};

async function fetchDevices() {
  try {
    loadingDevices.value = true;
    const response = await fetch('/api/devices');
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

async function connectToDevice(address: string) {
  const response = await fetch('/api/connect-device', {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token.value}`
    },
    body: JSON.stringify({ address }),
  });
  checkResponse(response);
  await fetchDevices();
}

fetchErrorAlerts();
</script>

<style scoped lang='scss'>
.alerts-box {
  gap: 10px;
}

.level {
  text-transform: capitalize;
  font-weight: 600;
}
</style>
