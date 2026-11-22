<template>
  <p class="text-caption q-mb-sm">
    Цей пароль, для доступу до налаштувань вашого додатку.
  </p>

  <q-btn
    @click="changePasswordModal = true"
    color="black"
    :disable="!isLoggedIn"
    label="Змінити пароль"
  />
  <ChangePasswordModal
    @update:show="(value) => (changePasswordModal = value)"
    :show="changePasswordModal"
  />

  <q-expansion-item
    v-if="isLoggedIn"
    dense
    label="Двофакторна автентифікація (2FA)"
    icon="verified_user"
    class="q-mt-sm"
  >
    <TwoFactorSetup class="q-pa-sm" />
  </q-expansion-item>

  <q-separator class="q-mt-sm" color="orange" inset />

  <p class="text-caption q-mb-sm">
    PUSH сповіщення - це спливаюче повідомлення на екрані смартфона.
  </p>

  <q-btn
    class="q-mb-sm"
    @click="subscribePush"
    color="black"
    :disable="!isLoggedIn || !!pushSubscription"
    label="Підписатись на PUSH"
  />
  <q-btn
    class="q-mb-sm"
    @click="cancelSubs"
    color="black"
    :disable="!isLoggedIn || !pushSubscription"
    label="Скасувати підписки"
  />

  <q-separator class="q-mb-sm" color="orange" inset />

  <p class="text-caption q-mb-sm">
    Налаштування ваших сповіщень
  </p>
  <div class="row justify-center q-gutter-sm q-mb-sm">
    <q-btn @click="alertsModal = true" color="black" :disable="!isAdmin" label="Частота Alerts" />
    <q-btn @click="thresholdsModal = true" color="black" :disable="!isLoggedIn" label="Пороги Alerts" />
  </div>
  <AlertsSettingsModal
    v-if="config"
    :config="config"
    :show="alertsModal"
    @update:show="(value) => (alertsModal = value)"
  />
  <AlertThresholdsModal
    :show="thresholdsModal"
    :detected-cell-count="detectedCellCount"
    @update:show="(value) => (thresholdsModal = value)"
  />

  <template v-if="isAdmin">
    <q-separator class="q-mb-sm" color="orange" inset />
    <q-expansion-item dense label="Користувачі та доступ" icon="group">
      <UsersManager class="q-pa-sm" />
    </q-expansion-item>
    <div class="row justify-center q-gutter-sm q-my-sm">
      <q-btn color="black" icon="storage" label="Дані та бекапи" @click="dataModal = true" />
      <q-btn color="black" icon="wb_sunny" label="Прогноз сонця" @click="solarModal = true" />
    </div>
    <DataMaintenanceModal :show="dataModal" @update:show="(value) => (dataModal = value)" />
    <SolarSettingsModal :show="solarModal" @update:show="(value) => (solarModal = value)" />
  </template>

  <q-separator class="q-mb-sm" color="orange" inset />

  <p class="text-caption q-mb-sm">
    Щоб переглянути налаштування вашого JK-BMS, оберіть пристрій.
  </p>

  <q-btn-dropdown
    :disable="!settings?.length"
    class="q-mb-sm"
    auto-close
    stretch
    flat
    style="flex: 1 1 50%"
    :label="currentSetting?.name || 'Оберіть пристрій'"
  >
    <q-list v-if="settings?.length">
      <q-item
        clickable
        v-for="setting of sortDevices([...settings])"
        class="text-black"
        :key="setting?.address"
        :name="setting?.name"
        :label="setting?.name"
        @click="currentAddress = setting.address"
      >
        <q-item-section>{{ setting?.name }}</q-item-section>
      </q-item>
    </q-list>
  </q-btn-dropdown>

  <template v-if="currentSetting">
    <p v-if="isAdmin" class="text-caption text-orange q-mb-xs">
      Перемикачі Charge / Discharge / Balance керують MOSFET-ключами BMS напряму.
    </p>
    <ToggleButton
      v-for="sw in BMS_SWITCHES"
      :key="sw.key"
      :value="Boolean((currentSetting as any)?.[sw.field])"
      :title="sw.title"
      :interactive="isAdmin"
      :loading="switching === sw.key"
      @toggle="(value: boolean) => requestSwitch(sw, value)"
    />
    <ToggleButton :value="currentSetting?.heating_enabled" title="Heating" />
    <ToggleButton
      :value="currentSetting?.disable_temperature_sensors"
      title="Disable Temp. Sensor"
    />
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
import { sortDevices, useAuth } from '../../helpers/utils';
import ToggleButton from 'src/components/ToggleButton.vue';
import SettingsList from 'src/components/SettingsList.vue';
import AlertsSettingsModal from 'src/components/modals/AlertsSettingsModal.vue';
import ChangePasswordModal from 'src/components/modals/ChangePasswordModal.vue';
import AlertThresholdsModal from 'src/components/modals/AlertThresholdsModal.vue';
import DataMaintenanceModal from 'src/components/modals/DataMaintenanceModal.vue';
import SolarSettingsModal from 'src/components/modals/SolarSettingsModal.vue';
import TwoFactorSetup from 'src/components/settings/TwoFactorSetup.vue';
import UsersManager from 'src/components/settings/UsersManager.vue';
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Dialog, Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { Config, SettingInfo } from 'src/models';
import { useBmsStore } from 'src/stores/bms';
import { useConfigStore } from 'src/stores/config';
import { cancelAllSubscriptions, checkPushSubscription, usePush } from 'src/composables/usePush';

const BMS_SWITCHES = [
  { key: 'charge', field: 'charge_switch', title: 'Charge', label: 'заряд' },
  { key: 'discharge', field: 'discharge_switch', title: 'Discharge', label: 'розряд' },
  { key: 'balance', field: 'balancer_switch', title: 'Balance', label: 'балансування' },
] as const;
type BmsSwitch = (typeof BMS_SWITCHES)[number];

const bmsStore = useBmsStore();
const configStore = useConfigStore();

const { isLoggedIn, isAdmin } = useAuth();

const changePasswordModal = ref(false);
const alertsModal = ref<boolean>(false);
const thresholdsModal = ref(false);
const dataModal = ref(false);
const solarModal = ref(false);
const switching = ref<string>('');
const intervalId = ref();
const config = computed<Config>(configStore.getConfig);
const settings = computed<SettingInfo[]>(bmsStore.getSettingInfo);
const currentAddress = ref<string>();
// Always derived from the store, so the toggles show what the BMS reports after a change.
const currentSetting = computed<SettingInfo | undefined>(() =>
  settings.value?.find((s) => s.address === currentAddress.value)
);
const detectedCellCount = computed(() => Number(settings.value?.[0]?.cell_count) || undefined);
const pushSubscription = ref<PushSubscription | null>(null);

function requestSwitch(sw: BmsSwitch, enabled: boolean) {
  const device = currentSetting.value;
  if (!device || !isAdmin.value) return;
  const dangerous = sw.key === 'discharge' && !enabled;
  Dialog.create({
    title: `${enabled ? 'Увімкнути' : 'Вимкнути'} ${sw.label}?`,
    message: dangerous
      ? `⚠️ Вимкнення розряду на «${device.name}» миттєво відключить живлення від цієї батареї ` +
        '(інвертор/будинок може залишитися без живлення). Продовжити?'
      : `Пристрій «${device.name}»: ${sw.label} буде ${enabled ? 'увімкнено' : 'вимкнено'}.`,
    cancel: { label: 'Скасувати', flat: true, color: 'white' },
    ok: { label: dangerous ? 'Так, вимкнути розряд' : 'Підтвердити', color: dangerous ? 'red' : 'positive' },
    dark: true,
    persistent: dangerous,
  }).onOk(() => applySwitch(device.address, sw, enabled));
}

async function applySwitch(address: string, sw: BmsSwitch, enabled: boolean) {
  switching.value = sw.key;
  try {
    const { data } = await api.post(
      `/api/device-settings/${encodeURIComponent(address)}/switch`,
      { switch: sw.key, enabled },
      { timeout: 20000 }
    );
    await bmsStore.fetchSettings();
    let message = 'Команду надіслано, але BMS ще не надіслав нові налаштування';
    if (data.applied) message = `BMS підтвердив: ${sw.label} ${enabled ? 'увімкнено' : 'вимкнено'}`;
    else if (data.confirmed) message = 'BMS не прийняв зміну (стан не змінився)';
    Notify.create({ message, color: data.applied ? 'positive' : 'orange', position: 'top' });
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    Notify.create({
      message: typeof detail === 'string' ? detail : 'Не вдалося змінити налаштування BMS',
      color: 'red',
      position: 'top',
    });
  } finally {
    switching.value = '';
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

onMounted(async () => {
  void bmsStore.fetchSettings();
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
