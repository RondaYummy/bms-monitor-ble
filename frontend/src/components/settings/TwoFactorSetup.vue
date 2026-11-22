<template>
  <div class="column items-center q-gutter-y-sm">
    <p class="text-caption q-mb-none">
      Двофакторна автентифікація (2FA): при вході, окрім пароля, потрібен 6-значний код із застосунку
      (Google Authenticator, Aegis, 1Password тощо).
    </p>

    <template v-if="me">
      <div>
        Статус:
        <b :class="me.totp_enabled ? 'text-green' : 'text-orange'">
          {{ me.totp_enabled ? 'увімкнено' : 'вимкнено' }}
        </b>
      </div>

      <q-btn v-if="!me.totp_enabled && !setup" color="black" label="Увімкнути 2FA" :loading="busy" @click="startSetup" />
      <q-btn v-if="me.totp_enabled" color="black" label="Вимкнути 2FA" @click="disableOpen = true" />

      <div v-if="setup" class="setup column items-center q-gutter-y-sm">
        <p class="q-mb-none">1. Відскануйте QR-код застосунком-автентифікатором:</p>
        <img v-if="qr" :src="qr" alt="QR-код для 2FA" width="200" height="200" class="qr" />
        <p class="text-caption q-mb-none">
          або введіть ключ вручну: <code class="secret" @click="copy(setup.secret)">{{ setup.secret }}</code>
        </p>
        <p class="q-mb-none">2. Введіть код із застосунку:</p>
        <q-input v-model="code" dark filled dense maxlength="6" inputmode="numeric" autocomplete="one-time-code"
          input-class="text-center" style="width: 140px" />
        <div class="row q-gutter-sm">
          <q-btn color="positive" label="Підтвердити" :disable="code.length !== 6" :loading="busy" @click="enable" />
          <q-btn color="black" label="Скасувати" @click="setup = null" />
        </div>
      </div>
    </template>

    <q-dialog v-model="disableOpen">
      <div class="column dialog-body q-gutter-y-sm">
        <h6 class="q-my-none">Вимкнути 2FA</h6>
        <q-input v-model="disablePassword" dark filled dense type="password" label="Пароль" autocomplete="current-password" />
        <q-input v-model="disableCode" dark filled dense maxlength="6" inputmode="numeric" label="Код 2FA" />
        <div class="row justify-between">
          <q-btn color="red" size="sm" label="Вимкнути" :loading="busy" @click="disable" />
          <q-btn color="black" size="sm" label="Скасувати" @click="disableOpen = false" />
        </div>
      </div>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Notify } from 'quasar';
import QRCode from 'qrcode';
import { api } from 'src/axios-instance';
import { copy } from 'src/helpers/utils';

interface Me {
  username: string;
  role: string;
  totp_enabled: boolean;
}

const me = ref<Me>();
const setup = ref<{ secret: string; otpauth_uri: string } | null>(null);
const qr = ref('');
const code = ref('');
const busy = ref(false);
const disableOpen = ref(false);
const disablePassword = ref('');
const disableCode = ref('');

function notifyError(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  Notify.create({ message: typeof detail === 'string' ? detail : fallback, color: 'red', position: 'top' });
}

async function loadMe() {
  try {
    me.value = (await api.get('/api/auth/me')).data;
  } catch (error) {
    console.error(error);
  }
}

async function startSetup() {
  busy.value = true;
  try {
    setup.value = (await api.post('/api/auth/2fa/setup')).data;
    // The QR code is rendered locally — the secret never leaves the browser/server pair.
    qr.value = await QRCode.toDataURL(setup.value!.otpauth_uri, { width: 200, margin: 1 });
  } catch (error) {
    notifyError(error, 'Не вдалося розпочати налаштування 2FA');
  } finally {
    busy.value = false;
  }
}

async function enable() {
  busy.value = true;
  try {
    await api.post('/api/auth/2fa/enable', { code: code.value });
    setup.value = null;
    code.value = '';
    Notify.create({ message: '2FA увімкнено. Інші сесії завершено.', color: 'positive', position: 'top' });
    await loadMe();
  } catch (error) {
    notifyError(error, 'Невірний код');
  } finally {
    busy.value = false;
  }
}

async function disable() {
  busy.value = true;
  try {
    await api.post('/api/auth/2fa/disable', { password: disablePassword.value, code: disableCode.value });
    disableOpen.value = false;
    disablePassword.value = '';
    disableCode.value = '';
    Notify.create({ message: '2FA вимкнено', color: 'orange', position: 'top' });
    await loadMe();
  } catch (error) {
    notifyError(error, 'Не вдалося вимкнути 2FA');
  } finally {
    busy.value = false;
  }
}

onMounted(loadMe);
</script>

<style scoped lang="scss">
.qr {
  background: white;
  border-radius: 8px;
  padding: 4px;
}
.secret {
  word-break: break-all;
  cursor: pointer;
  color: #ffd54f;
}
.dialog-body {
  padding: 20px;
  background: #1e1f26;
  color: white;
  min-width: 280px;
}
</style>
