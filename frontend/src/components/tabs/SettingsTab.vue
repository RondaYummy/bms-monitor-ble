<template>
    <p class='text-caption'>Цей пароль, для доступу до налаштувань вашого додатку.</p>

    <q-btn class="q-mt-sm" @click="changePasswordModal = true" color="black" :disable="!token" label="Змінити пароль" />
    <ChangePasswordModal @update:show="(value) => changePasswordModal = value" :show="changePasswordModal" />

    <q-separator class="q-mt-md" color="orange" inset />

    <p class='text-caption'>PUSH сповіщення - це спливаюче повідомлення на екрані смартфона.</p>

    <q-btn class="q-mt-sm" @click="subscribePush" color="black" :disable="!token || !!pushSubscription"
        label="Підписатись на PUSH" />
    <q-btn class="q-mt-sm" @click="cancelSubs" color="black" :disable="!token || !pushSubscription"
        label="Скасувати підписки" />

    <q-separator class="q-mt-md" color="orange" inset />

    <p class='text-caption'>Налаштування ваших сповіщень</p>
    <q-btn class="q-mt-sm" @click="alertsModal = true" color="black" :disable="!token" label="Налаштування Alerts" />
    <AlertsSettingsModal v-if="config" :config="config" :show="alertsModal"
        @update:show="(value) => alertsModal = value" />

    <q-separator class="q-mt-md" color="orange" inset />

    <p class='text-caption'>
        Щоб переглянути налаштування вашого JK-BMS, оберіть пристрій.
    </p>

    <q-btn-dropdown :disable="!settings?.length" class="q-mt-sm" auto-close stretch flat style='flex: 1 1 50%;'
        label="Оберіть пристрій">

        <q-list v-if="settings?.length">
            <q-item clickable v-for="setting of sortDevices(settings)" class="text-black" :key="setting?.address"
                :name="setting?.name" :label="setting?.name" @click="currentSetting = setting">
                <q-item-section>{{ setting?.name }}</q-item-section>
            </q-item>
        </q-list>
    </q-btn-dropdown>

    <template v-if="currentSetting">
        <ToggleButton :value="currentSetting?.charge_switch" title="Charge" />
        <ToggleButton :value="currentSetting?.discharge_switch" title="Discharge" />
        <ToggleButton :value="currentSetting?.balancer_switch" title="Balance" />
        <!-- <ToggleButton :value="currentSetting?."
                title="Emergency" /> -->
        <ToggleButton :value="currentSetting?.heating_enabled" title="Heating" />
        <ToggleButton :value="currentSetting?.disable_temperature_sensors" title="Disable Temp. Sensor" />
        <ToggleButton :value="currentSetting?.display_always_on" title="Display Always On" />
        <ToggleButton :value="currentSetting?.special_charger" title="Special Charger On" />
        <ToggleButton :value="currentSetting?.smart_sleep" title="Smart Sleep On" />
        <ToggleButton :value="currentSetting?.timed_stored_data" title="Timed Stored Data" />
        <ToggleButton :value="currentSetting?.charging_float_mode" title="Charging Float Mode" />
        <ToggleButton :value="currentSetting?.gps_heartbeat" title="GPS Heartbeat" />
        <ToggleButton :value="currentSetting?.disable_pcl_module" title="Disable PCL Module" />

        <SettingsList :settings="currentSetting" />
    </template>

    <q-separator class="q-mt-md" color="orange" inset />
</template>

<script setup lang="ts">
import { sortDevices, useSessionStorage } from '../../helpers/utils';
import ToggleButton from 'src/components/ToggleButton.vue';
import SettingsList from 'src/components/SettingsList.vue';
import AlertsSettingsModal from 'src/components/modals/AlertsSettingsModal.vue';
import ChangePasswordModal from 'src/components/modals/ChangePasswordModal.vue';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Config, SettingInfo } from 'src/models';
import { useBmsStore } from 'src/stores/bms';
import { useConfigStore } from 'src/stores/config';
import { cancelAllSubscriptions, checkPushSubscription, usePush } from 'src/composables/usePush';

const bmsStore = useBmsStore();
const configStore = useConfigStore();

const token = useSessionStorage("access_token");

const changePasswordModal = ref(false);
const alertsModal = ref<boolean>(false);
const intervalId = ref();
const config = computed<Config>(configStore.getConfig);
const settings = computed<SettingInfo[]>(bmsStore.getSettingInfo);
const currentSetting = ref<SettingInfo>();
const pushSubscription = ref<PushSubscription | null>(null);

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

onMounted(async () => {
    pushSubscription.value = await checkPushSubscription();
    setTimeout(async () => {
        pushSubscription.value = await checkPushSubscription();
    }, 2000);

    intervalId.value = setInterval(async () => {
        await Promise.allSettled([configStore.fetchConfigs()]);
    }, 5000);
});

onBeforeUnmount(() => {
    clearInterval(intervalId.value);
});

configStore.fetchConfigs();
</script>