<template>
  <q-dialog v-model="localShow">
    <div class="column dialog-body q-gutter-y-sm">
      <h6 class="q-my-none">Дані та бекапи</h6>

      <template v-if="status">
        <div class="text-caption text-grey-4">
          База: {{ mb(status.stats.db_size_bytes) }} · детальних записів: {{ status.stats.raw_rows }} ·
          погодинних: {{ status.stats.hourly_rows }} · алертів: {{ status.stats.alerts }}
          <span v-if="status.stats.oldest"> · з {{ status.stats.oldest.slice(0, 10) }}</span>
        </div>

        <div class="text-subtitle2">Зберігання</div>
        <div class="row q-col-gutter-sm">
          <q-input v-model.number="settings.raw_retention_days" class="col-6" dark filled dense type="number"
            min="7" label="Детальні дані, днів">
            <q-tooltip>Старіші дані автоматично усереднюються до погодинних (раз на добу).</q-tooltip>
          </q-input>
          <q-input v-model.number="settings.alerts_retention_days" class="col-6" dark filled dense type="number"
            min="7" label="Історія алертів, днів" />
        </div>

        <div class="text-subtitle2">Бекапи (щодоби)</div>
        <div class="row q-col-gutter-sm items-center">
          <q-toggle v-model="settings.backup_enabled" class="col-6" dark color="positive" label="Автобекап" />
          <q-input v-model.number="settings.backup_keep" class="col-6" dark filled dense type="number" min="1"
            max="60" label="Зберігати копій" />
        </div>
        <div class="row justify-between">
          <q-btn color="positive" size="sm" label="Зберегти налаштування" :loading="busy === 'settings'" @click="saveSettings" />
          <q-btn color="black" size="sm" label="Ущільнити зараз" :loading="busy === 'rollup'" @click="rollup" />
        </div>

        <q-separator color="grey-8" />
        <div class="row justify-between items-center">
          <span>Копії ({{ status.backups.length }})</span>
          <q-btn color="black" size="sm" icon="backup" label="Створити бекап" :loading="busy === 'backup'" @click="backupNow" />
        </div>
        <div v-if="status.last_backup_error" class="text-red text-caption">Помилка останнього бекапу: {{ status.last_backup_error }}</div>
        <q-list dark dense separator>
          <q-item v-for="backup in status.backups" :key="backup.name">
            <q-item-section class="text-left">
              <q-item-label>{{ backup.created_at.replace('T', ' ') }}</q-item-label>
              <q-item-label caption class="text-grey-5">{{ mb(backup.size_bytes) }}</q-item-label>
            </q-item-section>
            <q-item-section side>
              <div class="row no-wrap">
                <q-btn flat round dense icon="download" color="white" @click="download(backup.name)" />
                <q-btn flat round dense icon="delete" color="red" @click="remove(backup.name)" />
              </div>
            </q-item-section>
          </q-item>
        </q-list>
        <p class="text-caption text-grey-5 q-mb-none">
          Бекап містить паролі (хеші), зашифровані дані Tapo та 2FA. Ключ шифрування
          <code>data/secret.key</code> до бекапу не входить — зберігайте його окремо, інакше після
          відновлення на іншому сервері паролі Tapo доведеться ввести заново.
        </p>
      </template>

      <q-btn color="black" size="sm" label="Закрити" @click="localShow = false" />
    </div>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Dialog, Notify } from 'quasar';
import { api } from 'src/axios-instance';

interface Backup {
  name: string;
  size_bytes: number;
  created_at: string;
}
interface Status {
  settings: Settings;
  stats: { raw_rows: number; hourly_rows: number; oldest: string | null; alerts: number; db_size_bytes: number };
  backups: Backup[];
  last_backup_error: string | null;
}
interface Settings {
  raw_retention_days: number;
  alerts_retention_days: number;
  backup_enabled: boolean;
  backup_keep: number;
}

const props = defineProps<{ show: boolean }>();
const emits = defineEmits<{ (e: 'update:show', value: boolean): void }>();
const localShow = ref(props.show);
const status = ref<Status>();
const settings = ref<Settings>({ raw_retention_days: 90, alerts_retention_days: 365, backup_enabled: true, backup_keep: 7 });
const busy = ref<string>('');

watch(() => props.show, (v) => (localShow.value = v));
watch(localShow, async (v) => {
  emits('update:show', v);
  if (v) await load();
});

const mb = (bytes: number) => `${(bytes / 1024 / 1024).toFixed(1)} МБ`;

function notifyError(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  Notify.create({ message: typeof detail === 'string' ? detail : fallback, color: 'red', position: 'top' });
}

async function load() {
  try {
    status.value = (await api.get('/api/maintenance', { timeout: 15000 })).data;
    settings.value = { ...status.value!.settings };
  } catch (error) {
    notifyError(error, 'Не вдалося завантажити стан');
  }
}

async function run(kind: string, action: () => Promise<unknown>, ok: string) {
  busy.value = kind;
  try {
    await action();
    Notify.create({ message: ok, color: 'positive', position: 'top' });
    await load();
  } catch (error) {
    notifyError(error, 'Помилка');
  } finally {
    busy.value = '';
  }
}

const saveSettings = () => run('settings', () => api.post('/api/maintenance/settings', settings.value), 'Збережено');
const rollup = () => run('rollup', () => api.post('/api/maintenance/rollup', {}, { timeout: 120000 }), 'Старі дані ущільнено');
const backupNow = () => run('backup', () => api.post('/api/maintenance/backups', {}, { timeout: 120000 }), 'Бекап створено');

async function download(name: string) {
  try {
    // Through axios (Authorization header) — a plain link would not be authenticated.
    const response = await api.get(`/api/maintenance/backups/${encodeURIComponent(name)}`, {
      responseType: 'blob',
      timeout: 120000,
    });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (error) {
    notifyError(error, 'Не вдалося завантажити бекап');
  }
}

function remove(name: string) {
  Dialog.create({ title: 'Видалити бекап?', message: name, cancel: true, dark: true }).onOk(() =>
    run('delete', () => api.delete(`/api/maintenance/backups/${encodeURIComponent(name)}`), 'Видалено')
  );
}
</script>

<style scoped lang="scss">
.dialog-body {
  padding: 20px;
  background: #1e1f26;
  color: white;
  max-width: 520px;
  width: 100%;
}
</style>
