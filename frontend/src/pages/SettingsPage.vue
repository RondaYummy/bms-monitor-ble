<template>
  <div class="auth-header">

    <template v-if="token">
      <p class="text-success text-center q-mb-sm">
        Ви увійшли як <b>{{ username || 'admin' }}</b>
        ({{ isAdmin ? 'адміністратор' : 'лише перегляд' }}).
      </p>
      <p class="text-muted">
        {{ displayTimeRemaining() }}
      </p>

      <button class="q-mb-sm logout-button" type="button" @click="logout">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="lucide lucide-log-out h-4 w-4">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
          <polyline points="16 17 21 12 16 7"></polyline>
          <line x1="21" x2="9" y1="12" y2="12"></line>
        </svg>
        LOGOUT
      </button>
    </template>

    <template v-if="!token">
      <p class="text-negat text-center full-width q-mb-sm">
        Щоб мати можливість змінювати налаштування, будь ласка, авторизуйтеся.
      </p>

      <form class="column items-center q-gutter-sm q-mb-md" @submit.prevent="login(password)">
        <template v-if="!otpStep">
          <q-input v-model="loginUsername" dense outlined label="Користувач" label-color="white" color="white"
            autocomplete="username" input-class="text-white" />
          <q-input v-model="password" dense outlined label="Введіть пароль" label-color="white" color="white"
            autocomplete="current-password" input-class="text-white" :type="isPwd ? 'password' : 'text'">
            <template v-slot:append>
              <q-icon :name="isPwd ? 'visibility_off' : 'visibility'" class="cursor-pointer text-white"
                @click="isPwd = !isPwd" />
            </template>
          </q-input>
        </template>
        <template v-else>
          <p class="text-white q-mb-none">Введіть 6-значний код із застосунку-автентифікатора</p>
          <q-input v-model="otp" dense outlined label="Код 2FA" label-color="white" color="white" autofocus
            inputmode="numeric" autocomplete="one-time-code" maxlength="6" input-class="text-white text-center" />
          <q-btn flat dense size="sm" color="grey-5" label="Назад" @click="resetLoginForm" />
        </template>

        <button class="q-mb-sm login-button" type="submit" :disabled="loggingIn">
          ПІДТВЕРДИТИ
        </button>
      </form>
    </template>
  </div>


  <q-page class="column items-center q-pa-lg">

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
        <q-tab-panels swipeable infinite v-model="tab" animated transition-prev="scale" transition-next="scale"
          class="text-white text-center transparent">
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
import { Notify } from 'quasar';
import { clearSession, useAuth } from '../helpers/utils';
import DeyeTab from 'src/components/tabs/DeyeTab.vue';
import { useConfigStore } from 'src/stores/config';
import BmsTab from 'src/components//tabs/BmsTab.vue';
import TapoTab from 'src/components/tabs/TapoTab.vue';
import SettingsTab from 'src/components/tabs/SettingsTab.vue';
import AlertsTab from 'src/components/tabs/AlertsTab.vue';
import { api } from '../axios-instance';
const configStore = useConfigStore();

const { token, role, username, isAdmin } = useAuth();
const loginUsername = ref<string>('admin');
const otp = ref<string>('');
const otpStep = ref(false);
const loggingIn = ref(false);

function resetLoginForm() {
  otpStep.value = false;
  otp.value = '';
  password.value = '';
}

const tab = ref<string>('Alerts');
const password = ref<string>('');
const isPwd = ref<boolean>(true);
const intervalId = ref<NodeJS.Timeout>();

const login = async (pwd: string) => {
  if (loggingIn.value) return false;
  loggingIn.value = true;
  let response;
  try {
    response = await api.post('/api/login', {
      username: loginUsername.value.trim() || 'admin',
      password: pwd,
      ...(otpStep.value ? { otp: otp.value.trim() } : {}),
    });
  } catch (error: any) {
    const status = error?.response?.status;
    const detail = error?.response?.data?.detail;
    Notify.create({
      message: status === 429
        ? 'Забагато невдалих спроб. Спробуйте пізніше.'
        : detail === 'Invalid 2FA code' ? 'Невірний код 2FA' : 'Невірний логін або пароль',
      color: 'red',
      icon: 'warning',
      position: 'top',
      timeout: 2500,
    });
    otp.value = '';
    return false;
  } finally {
    loggingIn.value = false;
  }

  const data = response.data;
  if (data?.otp_required) {
    // Password is correct, the account has 2FA: ask for the code and repeat the request.
    otpStep.value = true;
    return false;
  }
  localStorage.setItem('token_created_at', String(Date.now() + (24 * 60 * 60 * 30 * 1000)));
  token.value = data.access_token;
  role.value = data.role || 'admin';
  username.value = data.username || loginUsername.value;
  resetLoginForm();
  return true;
};

const logout = async () => {
  try {
    await api.post('/api/logout');
  } catch (error) {
    console.warn('Logout request failed (session may already be expired):', error);
  } finally {
    // Always drop the local session, even if the server call failed.
    clearSession();
    token.value = null;
    role.value = null;
    username.value = null;
    resetLoginForm();
  }
  return true;
};

function displayTimeRemaining() {
  const expiresAt = localStorage.getItem('token_created_at');
  if (!expiresAt) return "Немає даних про сесію.";

  const remainingMilliseconds = parseInt(expiresAt) - Date.now();
  if (remainingMilliseconds <= 0) {
    logout();
    return "Сесія закінчилася. Будь ласка, увійдіть знову.";
  }

  const remainingDays = Math.ceil(remainingMilliseconds / (1000 * 60 * 60 * 24));
  return `До виходу з системи залишилось ${remainingDays} ${remainingDays === 1 ? 'день' : 'днів'}.`;
}

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
:deep(.q-field) {
  color: rgb(248, 250, 252) !important;
}

:deep(.q-field) {
  color: rgb(248, 250, 252) !important;
  border: 1px solid rgb(248, 250, 252);
  border-radius: 10px;
  margin-top: 0;
}

.auth-header {
  background-color: rgba(25, 29, 36, 0.5);
  border-bottom: 1px solid rgb(43, 48, 59);
  backdrop-filter: blur(4px);
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  .text-success {
    color: rgb(22, 162, 73);
  }

  .text-muted {
    color: rgb(152, 164, 179);
  }

  .text-negat {
    color: rgb(239, 67, 67);
  }

  .logout-button {
    color: rgb(239, 67, 67);
    background-color: rgb(17, 19, 23);
    border: 1px solid rgba(239, 67, 67, 0.5);
    border-radius: 10px;
    padding: 10px 32px;
    font-size: 14px;
    font-weight: 500;
    display: flex;
    gap: 5px;
    align-items: center;
    justify-content: center;
    cursor: pointer;
  }

  .login-button {
    background-color: rgb(232, 48, 110);
    padding: 10px 32px;
    font-size: 14px;
    font-weight: 700;
    border-radius: 10px;
    border: none;
    cursor: pointer;
    color: rgb(248, 250, 252);
  }
}
</style>
