<template>
    <div class="text-h6">Alerts</div>

    <div class='column items-center justify-center'>
        <p>
            Тут ви можете переглянути всі важливі сповіщення про роботу системи.
            Щоб видалити сповіщення, натисніть і утримуйте його.
        </p>

        <div class='row justify-center'>
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

    <div class='column alerts-box'>
        <q-banner v-for="alert of alertsMain" :key="alert?.id"
            v-touch-hold.mouse="() => token && alertsStore.deleteErrorAlert(alert?.id)" inline-actions :class="{
                'bg-negative': alert?.level === 'critical',
                'bg-red': alert?.level === 'error',
                'bg-orange': alert?.level === 'warning',
                'bg-bg-primary': alert?.level === 'info',
            }" class="text-white q-mt-sm q-mb-sm cursor-pointer rounded-borders">
            <div class="column">
                <div class='row justify-between'>
                    <q-chip outline color="white" text-color="white" :icon="getAlertIcon(alert?.level)">
                        {{ alert?.device_name }}
                    </q-chip>

                    <div class="row items-center">
                        <q-badge outline color="white" :label="alert?.error_code" />
                    </div>

                    <span class='row items-center'>
                        {{ formatTimestamp(alert?.timestamp) }}
                    </span>
                </div>

                <p v-if="alert?.id" class='q-mt-md text-left'>
                    {{ alert?.message }}
                </p>
            </div>

        </q-banner>

        <p v-if="!alerts?.length" class="level q-mt-md">
            {{ selectedLevel ? `"${selectedLevel}" повідомлення не
            знайдено.` : `Повідомлень не знайдено.` }}
        </p>
    </div>
</template>

<script setup lang="ts">
import { formatTimestamp, getAlertIcon, useSessionStorage } from 'src/helpers/utils';
import type { Alert } from '../../models';
import { useAlertsStore } from 'src/stores/alerts';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const alertsStore = useAlertsStore();

const token = useSessionStorage("access_token");

const selectedLevel = ref<string>();
const intervalId = ref();
const alertsMain = ref<Alert[]>();
const alerts = computed<Alert[]>(alertsStore.getAlerts);

watch(alerts, () => {
    alertsMain.value = alerts.value;
})

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