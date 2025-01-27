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

              <div class='row'>
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
            <pre>
            {{ alerts }}
            </pre>
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

const tab = ref('Alerts');
const alerts = ref();

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

<style scoped lang='scss'></style>
