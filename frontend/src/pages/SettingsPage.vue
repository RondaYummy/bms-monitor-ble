<template>
  <div class="q-pa-md">
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
                Тут відображаються всі важливі сповіщення про роботу системи
              </p>

              <div class='row justify-center'>
                <q-chip outline
                        color="primary"
                        text-color="white"
                        icon="priority_high">
                  Info
                </q-chip>
                <q-chip outline
                        color="orange"
                        text-color="white"
                        icon="warning">
                  Warning
                </q-chip>
                <q-chip outline
                        color="deep-orange"
                        text-color="white"
                        icon="error">
                  Error
                </q-chip>
                <q-chip outline
                        color="red"
                        text-color="white"
                        icon="flash_on">
                  Critical
                </q-chip>
              </div>
            </div>

            <div class='column alerts-box'>
              <q-banner v-for="alert of alerts"
                        :key="alert?.id"
                        v-touch-hold.mouse="() => handleHold(alert)"
                        inline-actions
                        :class="{
                          'bg-negative': alert?.level === 'critical',
                          'bg-red': alert?.level === 'error',
                          'bg-orange': alert?.level === 'warning',
                          'bg-bg-primary': alert?.level === 'info',
                        }"
                        class="text-white q-mt-sm q-mb-sm">
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
                    <q-btn color="black"
                           text-color="black"
                           label="Видалити сповіщення" />
                  </div>
                </div>

              </q-banner>
            </div>
          </q-tab-panel>

          <q-tab-panel name="Settings">
            <div class="text-h6">Settings</div>
            Тут будуть ваші налаштування...
          </q-tab-panel>
        </q-tab-panels>
      </div>
    </div>
  </div>
</template>

<script setup lang='ts'>
import { ref } from 'vue';

interface Alert {
  id: number;
  device_address: string;
  device_name: string;
  error_code: string;
  level: 'info' | 'warning' | 'error' | 'critical';
  message: string;
  timestamp: string;
}


const tab = ref('Alerts');
const alerts = ref<Alert[]>();
const holdAlert = ref<Alert>();

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

async function fetchErrorAlerts() {
  try {
    const response = await fetch('/api/error-alerts');
    if (!response.ok) {
      throw new Error('Failed to error alerts');
    }
    const data = await response.json();
    console.log('Error alerts:', data);
    alerts.value = data;
  } catch (error) {
    console.error('Error fetching error alerts:', error);
  }
}

fetchErrorAlerts();
</script>

<style scoped lang='scss'>
.alerts-box {
  gap: 10px;
}
</style>
