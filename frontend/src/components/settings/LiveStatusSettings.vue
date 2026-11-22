<template>
  <div class="live-status column q-gutter-y-xs">
    <div class="preview">
      <div class="preview-app"><q-icon name="notifications" size="14px" /> BMS Monitor · зараз</div>
      <div class="preview-title">{{ preview?.title || '🔋 —% · ☀️ — кВт · 🏠 — кВт' }}</div>
      <div class="preview-body">{{ preview?.body || 'Стан системи з’явиться після першого оновлення' }}</div>
    </div>

    <q-toggle
      :model-value="prefs.enabled"
      dark
      color="positive"
      label="Живий стан у сповіщенні"
      :disable="busy || !supported"
      @update:model-value="toggleStatus"
    />
    <div v-if="prefs.enabled" class="row items-center q-gutter-sm">
      <span class="text-caption">Оновлювати кожні</span>
      <q-select
        :model-value="prefs.interval_min"
        dense
        dark
        filled
        emit-value
        map-options
        style="min-width: 110px"
        :options="INTERVALS"
        :disable="busy || platform === 'ios'"
        @update:model-value="(v: number) => save({ interval_min: v })"
      />
    </div>
    <p class="text-caption text-grey-5 q-mb-none">
      <template v-if="platform === 'ios'">
        На iPhone кожне оновлення приходить окремим банером, тому стан надсилається лише при важливих змінах
        (зникла чи з'явилась мережа, SOC змінився на 10%) і не частіше разу на годину.
      </template>
      <template v-else>
        Сповіщення тихо замінює попереднє; при відключенні мережі — одразу. Можна змахнути: з'явиться з наступним
        оновленням.
      </template>
      <span v-if="!supported"> Потрібна підписка на PUSH на цьому пристрої.</span>
    </p>

    <q-toggle
      v-if="badgeSupported"
      v-model="badge"
      dark
      color="positive"
      label="SOC на іконці застосунку"
      @update:model-value="onBadgeToggle"
    />
    <p v-if="badgeSupported" class="text-caption text-grey-5 q-mb-none">
      Число на іконці (iPhone, Windows, macOS). На Android Chrome показує лише крапку.
    </p>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { checkPushSubscription } from 'src/composables/usePush';
import { isBadgeEnabled, isBadgeSupported, setBadgeEnabled, showSocBadge, socFromCellInfo } from 'src/composables/useAppBadge';
import { useBmsStore } from 'src/stores/bms';

const INTERVALS = [5, 10, 15, 30, 60].map((m) => ({ label: m === 60 ? '1 год' : `${m} хв`, value: m }));

const props = defineProps<{ subscribed: boolean }>();
const bmsStore = useBmsStore();

const platform = /iPad|iPhone|iPod/.test(navigator.userAgent) ? 'ios' : /Android/i.test(navigator.userAgent) ? 'android' : 'desktop';
const prefs = ref({ enabled: false, interval_min: 10 });
const preview = ref<{ title: string; body: string }>();
const busy = ref(false);
const supported = ref(false);
const badgeSupported = isBadgeSupported();
const badge = ref(isBadgeEnabled());
let endpoint = '';

async function save(fields: Record<string, unknown>) {
  if (!endpoint) return;
  busy.value = true;
  try {
    const { data } = await api.post('/api/push/status', { endpoint, platform, ...fields });
    prefs.value = { enabled: data.enabled, interval_min: data.interval_min };
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    Notify.create({ message: typeof detail === 'string' ? detail : 'Не вдалося зберегти', color: 'red', position: 'top' });
  } finally {
    busy.value = false;
  }
}

async function toggleStatus(enabled: boolean) {
  await save({ enabled });
  if (enabled) Notify.create({ message: 'Перше сповіщення зі станом прийде протягом хвилини', color: 'positive', position: 'top' });
}

async function onBadgeToggle(enabled: boolean) {
  await setBadgeEnabled(enabled);
  if (enabled) await showSocBadge(socFromCellInfo(bmsStore.getCellInfo() as any));
}

onMounted(async () => {
  try {
    preview.value = (await api.get('/api/push/status/preview')).data;
  } catch {
    /* no data yet */
  }
  const subscription = props.subscribed ? await checkPushSubscription() : null;
  endpoint = subscription?.endpoint || '';
  supported.value = !!endpoint;
  if (endpoint) await save({});
});
</script>

<style scoped lang="scss">
.live-status {
  width: 100%;
  max-width: 420px;
  margin: 0 auto;
  text-align: left;
}
.preview {
  background: rgba(255, 255, 255, 0.92);
  color: #111;
  border-radius: 14px;
  padding: 8px 12px;
  margin-bottom: 4px;
}
.preview-app {
  font-size: 11px;
  color: #555;
}
.preview-title {
  font-weight: 700;
  font-size: 14px;
}
.preview-body {
  font-size: 13px;
  color: #333;
}
</style>
