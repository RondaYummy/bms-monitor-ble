<template>
  <q-page class="column items-center q-pa-lg">
    <p class="unique text-center full-width" v-if="!token">
      Щоб мати можливість змінювати налаштування, будь ласка, авторизуйтеся.
    </p>
    <p class="charge text-center full-width" v-if="token">
      Ви успішно авторизовані та можете змінювати налаштування.
    </p>

    <div class="row justify-center no-wrap q-gutter-sm q-mb-md" v-if="!token">
      <q-input
        v-model="password"
        dense
        outlined
        label="Введіть пароль"
        label-color="white"
        color="white"
        :type="isPwd ? 'password' : 'text'"
      >
        <template v-slot:append>
          <q-icon
            :name="isPwd ? 'visibility_off' : 'visibility'"
            class="cursor-pointer text-white"
            @click="isPwd = !isPwd"
          />
        </template>
      </q-input>
      <q-btn @click="login(password)" color="black" label="Підтвердити" />
    </div>

    <div class="full-width">
      <q-tabs v-model="tab" align="justify" narrow-indicator class="q-mb-lg">
        <q-tab class="text-purple" name="Alerts" label="Alerts" />
        <q-tab class="text-orange" name="Settings" label="Settings" />
      </q-tabs>
      <q-tabs v-model="tab" align="justify" narrow-indicator class="q-mb-lg">
        <q-tab class="text-blue" name="bms" label="JK-BMS" />
        <q-tab class="text-blue" name="tapo" label="Tapo" />
        <q-tab class="text-blue" name="deye" label="Deye" />
      </q-tabs>

      <div class="q-gutter-y-sm">
        <q-tab-panels
          swipeable
          infinite
          v-model="tab"
          animated
          transition-prev="scale"
          transition-next="scale"
          class="text-white text-center transparent"
        >
          <q-tab-panel name="Alerts">
            <AlertsTab />
          </q-tab-panel>

          <q-tab-panel name="Settings">
            <SettingsTab />
          </q-tab-panel>

          <q-tab-panel name="bms">
            <BmsTab />
          </q-tab-panel>

          <q-tab-panel name="tapo">
            <TapoTab />
          </q-tab-panel>

          <q-tab-panel name="deye">
            <DeyeTab />
          </q-tab-panel>
        </q-tab-panels>
      </div>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useSessionStorage } from '../helpers/utils';
import DeyeTab from 'src/components/tabs/DeyeTab.vue';
import { useConfigStore } from 'src/stores/config';
import BmsTab from 'src/components//tabs/BmsTab.vue';
import TapoTab from 'src/components/tabs/TapoTab.vue';
import SettingsTab from 'src/components/tabs/SettingsTab.vue';
import AlertsTab from 'src/components/tabs/AlertsTab.vue';

const configStore = useConfigStore();

const token = useSessionStorage('access_token');

const tab = ref<string>('Alerts');
const password = ref<string>('');
const isPwd = ref<boolean>(true);
const intervalId = ref<NodeJS.Timeout>();

const login = async (pwd: string) => {
  const response = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password: pwd }),
  });

  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  token.value = data?.access_token;
  password.value = '';
  console.info('---Successful---');
  return true;
};

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await Promise.allSettled([configStore.fetchConfigs()]);
  }, 8000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

configStore.fetchConfigs();
</script>

<style scoped lang="scss">
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
