<template>
  <div class="text-h6">Alerts</div>

  <div class="column items-center justify-center">
    <p>
      Тут ви можете переглянути всі важливі сповіщення про роботу системи. Щоб видалити сповіщення,
      натисніть і утримуйте його.
    </p>

    <div class="row justify-center">
      <q-chip @click="filterAlertsByLevel()" outline clickable color="white" icon="apps">
        All
      </q-chip>
      <q-chip @click="filterAlertsByLevel('info')" outline clickable color="primary" icon="priority_high">
        Info
      </q-chip>
      <q-chip @click="filterAlertsByLevel('warning')" outline clickable color="orange" icon="warning">
        Warning
      </q-chip>
      <q-chip @click="filterAlertsByLevel('error')" outline clickable color="deep-orange" icon="error">
        Error
      </q-chip>
      <q-chip @click="filterAlertsByLevel('critical')" outline clickable color="red" icon="flash_on">
        Critical
      </q-chip>
    </div>
  </div>

  <button v-if="alerts?.length" @click="alertsStore.deleteAllAlerts" class="clear-all-btn cursor-pointer">
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
      class="lucide lucide-x w-4 h-4 transition-transform group-hover:rotate-90">
      <path d="M18 6 6 18"></path>
      <path d="m6 6 12 12"></path>
    </svg>
    <span>Очистити всі</span>
  </button>

  <div class="column">
    <q-banner v-for="alert of alertsMain" :key="alert?.id"
      v-touch-hold.mouse="() => token && alertsStore.deleteErrorAlert(alert?.id)" inline-actions :class="{
        'bg-negative': alert?.level === 'critical',
        'bg-red': alert?.level === 'error',
        'bg-orange': alert?.level === 'warning',
        'bg-bg-primary': alert?.level === 'info',
      }" class="text-white q-mt-sm q-mb-sm cursor-pointer rounded-borders">
      <div class="column">
        <div class="row justify-between">
          <q-chip outline color="white" text-color="white" :icon="getAlertIcon(alert?.level)">
            {{ alert?.device_name }}
          </q-chip>

          <div class="row items-center">
            <q-badge outline color="white" :label="alert?.error_code" />
          </div>

          <span class="row items-center">
            {{ formatTimestamp(alert?.timestamp) }}
          </span>
        </div>

        <p v-if="alert?.id" class="q-mt-md text-left">
          {{ alert?.message }}
        </p>
      </div>
    </q-banner>

    <div v-if="!alertsMain?.length" class="text-center">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-muted">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"></path>
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"></path>
      </svg>
      <p class="text-muted text-muted-title">
        Немає сповіщень ({{ selectedLevel }})
      </p>
      <p class="text-muted">Всі системи працюють нормально</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatTimestamp, getAlertIcon, useSessionStorage } from 'src/helpers/utils';
import type { Alert } from '../../models';
import { useAlertsStore } from 'src/stores/alerts';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const alertsStore = useAlertsStore();

const token = useSessionStorage('access_token');

const selectedLevel = ref<string>();
const intervalId = ref();
const alertsMain = ref<Alert[]>();
const alerts = computed<Alert[]>(alertsStore.getAlerts);

watch(alerts, () => {
  alertsMain.value = alerts.value;
});

function filterAlertsByLevel(level?: string): void {
  if (!alerts.value) {
    return;
  }
  if (!level) {
    alertsMain.value = alerts.value;
    return;
  }
  selectedLevel.value = level;
  alertsMain.value = alerts.value?.filter((a) => a.level === level);
}

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await Promise.allSettled([alertsStore.fetchErrorAlerts()]);
  }, 8000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

alertsStore.fetchErrorAlerts();
</script>

<style scoped lang="scss">
.text-muted {
  color: rgb(152, 164, 179);
}

.text-muted-title {
  font-size: 18px;
  color: rgb(152, 164, 179);
  font-weight: 500;
}

svg {
  width: 4rem;
  height: 4rem;
}

.clear-all-btn {
  color: rgb(239, 67, 67);
  border: 1px solid rgba(239, 67, 67, 0.3);
  border-radius: 12px;
  padding: 8px 16px;
  font-weight: 900;
  background-color: rgba(239, 67, 67, 0.1);
  margin: 0 0 0 auto;

  span {
    color: rgb(239, 67, 67);
  }
}
</style>
