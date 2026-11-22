<template>
  <div class="column q-gutter-y-sm users">
    <q-toggle
      :model-value="publicRead"
      color="positive"
      dark
      label="Публічний перегляд без входу"
      @update:model-value="setPublicRead"
    >
      <q-tooltip max-width="320px">
        Увімкнено: дашборд бачить будь-хто з посиланням (як раніше). Вимкнено: дані доступні лише
        користувачам, що увійшли (ролі «перегляд» або «адмін»).
      </q-tooltip>
    </q-toggle>

    <q-list dark separator bordered class="rounded-borders">
      <q-item v-for="user in users" :key="user.id">
        <q-item-section class="text-left">
          <q-item-label>
            <b>{{ user.username }}</b>
            <q-badge class="q-ml-sm" :color="user.role === 'admin' ? 'deep-orange' : 'blue-grey'">
              {{ user.role === 'admin' ? 'адмін' : 'перегляд' }}
            </q-badge>
            <q-badge v-if="user.totp_enabled" class="q-ml-xs" color="green">2FA</q-badge>
          </q-item-label>
          <q-item-label caption class="text-grey-5">{{ user.created_at }}</q-item-label>
        </q-item-section>
        <q-item-section side>
          <q-btn flat round dense icon="more_vert" color="white">
            <q-menu dark auto-close>
              <q-list dense style="min-width: 200px">
                <q-item clickable @click="setRole(user, user.role === 'admin' ? 'viewer' : 'admin')">
                  <q-item-section>Зробити {{ user.role === 'admin' ? 'переглядачем' : 'адміном' }}</q-item-section>
                </q-item>
                <q-item clickable @click="resetPassword(user)">
                  <q-item-section>Скинути пароль</q-item-section>
                </q-item>
                <q-item v-if="user.totp_enabled" clickable @click="disable2fa(user)">
                  <q-item-section>Вимкнути 2FA</q-item-section>
                </q-item>
                <q-item clickable class="text-red" @click="removeUser(user)">
                  <q-item-section>Видалити</q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </q-btn>
        </q-item-section>
      </q-item>
    </q-list>

    <div class="row q-col-gutter-xs items-start">
      <q-input v-model="newUser.username" class="col-12 col-sm-4" dark filled dense label="Логін" autocomplete="off" />
      <q-input v-model="newUser.password" class="col-12 col-sm-4" dark filled dense type="password"
        label="Пароль (≥ 8)" autocomplete="new-password" />
      <q-select v-model="newUser.role" class="col-12 col-sm-4" dark filled dense emit-value map-options
        :options="[{ label: 'Перегляд', value: 'viewer' }, { label: 'Адмін', value: 'admin' }]" label="Роль" />
    </div>
    <q-btn color="positive" label="Додати користувача" :loading="busy"
      :disable="newUser.username.length < 3 || newUser.password.length < 8" @click="createUser" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Dialog, Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { useConfigStore } from 'src/stores/config';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'viewer';
  totp_enabled: boolean;
  created_at: string;
}

const configStore = useConfigStore();
const users = ref<User[]>([]);
const busy = ref(false);
const newUser = ref({ username: '', password: '', role: 'viewer' });
const publicRead = computed(() => (configStore.getConfig() as any)?.public_read !== false);

function notifyError(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail[0]?.msg : fallback;
  Notify.create({ message: message || fallback, color: 'red', position: 'top' });
}

async function load() {
  try {
    users.value = (await api.get('/api/users')).data;
  } catch (error) {
    console.error(error);
  }
}

async function setPublicRead(value: boolean) {
  try {
    await api.post('/api/configs', { public_read: value });
    await configStore.fetchConfigs();
  } catch (error) {
    notifyError(error, 'Не вдалося змінити доступ');
  }
}

async function createUser() {
  busy.value = true;
  try {
    await api.post('/api/users', newUser.value);
    newUser.value = { username: '', password: '', role: 'viewer' };
    await load();
  } catch (error) {
    notifyError(error, 'Не вдалося створити користувача');
  } finally {
    busy.value = false;
  }
}

async function patch(user: User, body: Record<string, unknown>, ok: string) {
  try {
    await api.patch(`/api/users/${user.id}`, body);
    Notify.create({ message: ok, color: 'positive', position: 'top' });
    await load();
  } catch (error) {
    notifyError(error, 'Не вдалося оновити користувача');
  }
}

function setRole(user: User, role: string) {
  void patch(user, { role }, 'Роль змінено, сесії користувача завершено');
}

function resetPassword(user: User) {
  Dialog.create({
    title: `Новий пароль для ${user.username}`,
    prompt: { model: '', type: 'password', isValid: (v: string) => v.length >= 8 },
    cancel: true,
    dark: true,
  }).onOk((password: string) => patch(user, { password }, 'Пароль змінено'));
}

function disable2fa(user: User) {
  Dialog.create({ title: `Вимкнути 2FA для ${user.username}?`, cancel: true, dark: true }).onOk(() =>
    patch(user, { disable_2fa: true }, '2FA вимкнено')
  );
}

function removeUser(user: User) {
  Dialog.create({ title: `Видалити ${user.username}?`, cancel: true, dark: true }).onOk(async () => {
    try {
      await api.delete(`/api/users/${user.id}`);
      await load();
    } catch (error) {
      notifyError(error, 'Не вдалося видалити');
    }
  });
}

onMounted(load);
</script>

<style scoped lang="scss">
.users {
  color: white;
  width: 100%;
}
</style>
