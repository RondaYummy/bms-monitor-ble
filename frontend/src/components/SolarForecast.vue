<template>
  <q-expansion-item
    v-model="open"
    switch-toggle-side
    expand-separator
    label="Прогноз сонця"
    :caption="caption"
    class="solar full-width"
  >
    <div class="q-pa-sm column q-gutter-y-sm">
      <div v-if="loading && !data" class="text-center q-pa-md"><q-spinner color="white" /></div>

      <div v-else-if="data && !data.configured" class="hint">
        Прогноз генерації на 3 дні з Open-Meteo (безкоштовно) робить прогноз батареї точнішим.
        <span v-if="canEdit">Налаштуйте координати й орієнтацію панелей у
          <router-link to="/settings" class="link">Налаштування → Settings → Прогноз сонця</router-link>.</span>
        <span v-else>Попросіть адміністратора налаштувати його.</span>
      </div>

      <template v-else-if="data">
        <div class="row q-col-gutter-sm">
          <div v-for="(day, i) in data.days" :key="day.date" class="col-4">
            <div class="tile" :class="{ today: i === 0 }">
              <div class="tile-label">{{ dayLabel(day.date, i) }}</div>
              <div class="tile-value">{{ day.pv_kwh }} <small>кВт·год</small></div>
              <div class="tile-hint">
                {{ cloudIcon(day.cloud_avg) }} {{ day.cloud_avg ?? '—' }}% хмар
                <span v-if="day.actual_kwh !== null && i === 0"> · вже {{ day.actual_kwh }}</span>
              </div>
            </div>
          </div>
        </div>

        <apex-chart v-if="data.hours.length" type="bar" height="180" :options="chartOptions" :series="series" />

        <div class="text-caption text-grey-4">
          <template v-if="data.calibration?.method === 'learned'">
            Модель навчена на {{ data.calibration.points }} год вашої генерації
            (~{{ data.calibration.kw_per_1000_wm2 }} кВт при 1000 Вт/м²).
          </template>
          <template v-else-if="data.calibration?.method === 'peak_power'">
            Поки за вказаною потужністю панелей — точність зросте після кількох сонячних днів історії.
          </template>
          <span v-if="data.last_error" class="text-orange"> Open-Meteo: {{ data.last_error }}</span>
        </div>
      </template>
    </div>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from 'src/axios-instance';
import { useAuth } from 'src/helpers/utils';

interface SolarDay {
  date: string;
  pv_kwh: number;
  cloud_avg: number | null;
  actual_kwh: number | null;
}
interface SolarHour {
  hour: string;
  pv_kwh: number;
  cloud: number | null;
}
interface SolarSummary {
  configured: boolean;
  calibration: { method: string | null; points: number; kw_per_1000_wm2: number | null } | null;
  days: SolarDay[];
  hours: SolarHour[];
  last_error: string | null;
}

const { isAdmin: canEdit } = useAuth();
const open = ref(false);
const loading = ref(false);
const data = ref<SolarSummary>();
let timer: ReturnType<typeof setInterval> | undefined;

const caption = computed(() => {
  const days = data.value?.days || [];
  if (!data.value?.configured) return 'Open-Meteo: генерація на 3 дні';
  if (!days.length) return 'Завантаження прогнозу…';
  return `Сьогодні ~${days[0]!.pv_kwh} кВт·год${days[1] ? `, завтра ~${days[1].pv_kwh}` : ''}`;
});

function dayLabel(date: string, index: number) {
  if (index === 0) return 'Сьогодні';
  if (index === 1) return 'Завтра';
  return new Date(date).toLocaleDateString('uk-UA', { weekday: 'long' });
}
function cloudIcon(cloud: number | null) {
  if (cloud === null) return '';
  if (cloud < 25) return '☀️';
  if (cloud < 60) return '⛅';
  if (cloud < 85) return '🌥️';
  return '☁️';
}

const series = computed(() => [{ name: 'Генерація', data: data.value?.hours.map((h) => h.pv_kwh) || [] }]);
const chartOptions = computed(() => ({
  chart: { background: 'transparent', toolbar: { show: false }, foreColor: '#cfd8dc', animations: { enabled: false } },
  theme: { mode: 'dark' },
  colors: ['#ffca28'],
  plotOptions: { bar: { columnWidth: '85%', borderRadius: 2 } },
  dataLabels: { enabled: false },
  xaxis: {
    categories: data.value?.hours.map((h) => `${h.hour.slice(8, 10)}.${h.hour.slice(5, 7)} ${h.hour.slice(11)}:00`) || [],
    tickAmount: 8,
    labels: { rotate: 0, hideOverlappingLabels: true, formatter: (v: string) => (v ? v.slice(-5) : v) },
  },
  yaxis: { title: { text: 'кВт·год' }, labels: { formatter: (v: number) => v.toFixed(1) } },
  tooltip: {
    y: { formatter: (v: number, opts: any) => `${v.toFixed(2)} кВт·год · хмарність ${data.value?.hours[opts?.dataPointIndex]?.cloud ?? '—'}%` },
  },
  grid: { borderColor: '#37474f' },
}));

async function load() {
  if (document.hidden) return;
  loading.value = true;
  try {
    data.value = (await api.get('/api/solar/forecast', { timeout: 15000 })).data;
  } catch (error) {
    console.error('Solar forecast:', error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void load();
  timer = setInterval(load, 15 * 60 * 1000);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<style scoped lang="scss">
.solar {
  color: white;
}
.tile {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 6px 8px;
  height: 100%;
  &.today {
    background: rgba(255, 202, 40, 0.14);
  }
}
.tile-label {
  font-size: 0.72em;
  color: #bdbdbd;
  text-transform: capitalize;
}
.tile-value {
  font-size: 1.15em;
  font-weight: 700;
  small {
    font-size: 0.6em;
    font-weight: 400;
  }
}
.tile-hint {
  font-size: 0.7em;
  color: #9e9e9e;
}
.hint {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 10px;
}
.link {
  color: #03dac6;
}
</style>
