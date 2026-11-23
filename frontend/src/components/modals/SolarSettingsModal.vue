<template>
  <q-dialog v-model="localShow">
    <div class="column dialog-body q-gutter-y-sm">
      <h6 class="q-my-none">☀️ Прогноз сонця (Open-Meteo)</h6>
      <p class="text-caption text-grey-4 q-mb-none">
        Безкоштовний прогноз погоди для вашої станції. Модель сама навчиться, скільки ваші панелі виробляють при
        певному сонці, порівнюючи прогноз із реальною генерацією Deye. Координати округлюються до ~1 км.
      </p>

      <q-toggle v-model="form.enabled" dark color="positive" label="Увімкнути прогноз сонця" :disable="!canEdit" />

      <div class="row q-col-gutter-sm">
        <q-input v-model.number="form.latitude" class="col-6" dark filled dense type="number" step="0.0001"
          label="Широта" :disable="!canEdit" />
        <q-input v-model.number="form.longitude" class="col-6" dark filled dense type="number" step="0.0001"
          label="Довгота" :disable="!canEdit" />
      </div>
      <q-btn flat dense size="sm" color="light-blue-4" icon="my_location" label="Моє місцезнаходження"
        :disable="!canEdit" :loading="locating" @click="locate" />

      <div class="row q-col-gutter-sm">
        <q-input v-model.number="form.tilt" class="col-6" dark filled dense type="number" min="0" max="90"
          label="Нахил панелей, °" :disable="!canEdit">
          <q-tooltip>0° — лежать горизонтально, 90° — вертикально. Типово 25–35°.</q-tooltip>
        </q-input>
        <q-select v-model="form.azimuth" class="col-6" dark filled dense emit-value map-options
          :options="AZIMUTHS" label="Орієнтація" :disable="!canEdit" />
      </div>

      <q-input v-model.number="form.peak_kw" dark filled dense type="number" step="0.1" clearable
        label="Потужність панелей, кВт (необов'язково)" :disable="!canEdit">
        <q-tooltip>Потрібна лише перші дні, поки не накопичиться історія генерації для автокалібрування.</q-tooltip>
      </q-input>

      <div v-if="status" class="text-caption text-grey-4">
        <div v-if="status.calibration?.method === 'learned'">
          ✅ Навчено на {{ status.calibration.points }} год: ~{{ status.calibration.kw_per_1000_wm2 }} кВт при 1000 Вт/м².
        </div>
        <div v-else-if="status.calibration?.method === 'peak_power'">
          ℹ️ Поки за потужністю панелей ({{ status.calibration.points }} год історії, потрібно ≥ 12 сонячних годин).
        </div>
        <div v-if="status.updated_at">Дані оновлено: {{ status.updated_at.replace('T', ' ') }}</div>
        <div v-if="status.last_error" class="text-orange">
          Не вдається оновити з Open-Meteo: {{ status.last_error }}. Повтор автоматично за кілька хвилин.
        </div>
      </div>

      <div class="row justify-between q-mt-sm">
        <q-btn color="positive" size="sm" label="Зберегти" :loading="saving" :disable="!canEdit || !valid" @click="save" />
        <q-btn color="black" size="sm" label="Закрити" @click="localShow = false" />
      </div>
    </div>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { useAuth } from 'src/helpers/utils';

interface SolarSettings {
  enabled: boolean;
  latitude: number | null;
  longitude: number | null;
  tilt: number;
  azimuth: number;
  peak_kw: number | null;
}

// Open-Meteo convention: 0 = south, -90 = east, 90 = west
const AZIMUTHS = [
  { label: 'Південь', value: 0 },
  { label: 'Південний схід', value: -45 },
  { label: 'Південний захід', value: 45 },
  { label: 'Схід', value: -90 },
  { label: 'Захід', value: 90 },
  { label: 'Північ', value: 180 },
];

const props = defineProps<{ show: boolean }>();
const emits = defineEmits<{ (e: 'update:show', value: boolean): void }>();
const { isAdmin: canEdit } = useAuth();

const localShow = ref(props.show);
const saving = ref(false);
const locating = ref(false);
const status = ref<any>();
const form = ref<SolarSettings>({ enabled: true, latitude: null, longitude: null, tilt: 30, azimuth: 0, peak_kw: null });
const valid = computed(
  () => Number.isFinite(form.value.latitude) && Number.isFinite(form.value.longitude) && form.value.latitude !== null
);

watch(() => props.show, (v) => (localShow.value = v));
watch(localShow, async (v) => {
  emits('update:show', v);
  if (v) await load();
});

async function load() {
  try {
    status.value = (await api.get('/api/solar/forecast', { timeout: 15000 })).data;
    form.value = { ...form.value, ...status.value.settings, enabled: status.value.settings.enabled || !status.value.settings.latitude };
  } catch (error) {
    console.error(error);
  }
}

function locate() {
  if (!navigator.geolocation) return;
  locating.value = true;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.value.latitude = +pos.coords.latitude.toFixed(4);
      form.value.longitude = +pos.coords.longitude.toFixed(4);
      locating.value = false;
    },
    () => {
      locating.value = false;
      Notify.create({ message: 'Не вдалося визначити місцезнаходження', color: 'orange', position: 'top' });
    },
    { timeout: 10000 }
  );
}

async function save() {
  saving.value = true;
  try {
    await api.put('/api/solar/settings', form.value, { timeout: 30000 });
    Notify.create({ message: 'Прогноз сонця налаштовано', color: 'positive', position: 'top' });
    await load();
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    Notify.create({ message: typeof detail === 'string' ? detail : 'Не вдалося зберегти', color: 'red', position: 'top' });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped lang="scss">
.dialog-body {
  padding: 20px;
  background: #1e1f26;
  color: white;
  max-width: 440px;
  width: 100%;
}
</style>
