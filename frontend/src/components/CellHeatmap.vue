<template>
  <q-expansion-item
    v-model="open"
    switch-toggle-side
    expand-separator
    label="Історія комірок"
    caption="Відхилення кожної комірки від середнього за тижні"
    class="heatmap full-width"
  >
    <div class="q-pa-sm column q-gutter-y-sm">
      <div class="row q-col-gutter-sm">
        <q-select v-model="device" class="col-7" dark filled dense emit-value map-options :options="deviceOptions"
          label="Батарея" />
        <q-select v-model="days" class="col-5" dark filled dense emit-value map-options :options="DAY_OPTIONS"
          label="Період" />
      </div>

      <div v-if="loading" class="text-center q-pa-md"><q-spinner color="white" /></div>
      <div v-else-if="!devices.length" class="text-caption text-grey-5">
        Історія збирається з цієї версії: середня напруга кожної комірки записується кожні 5 хвилин.
      </div>
      <div v-else-if="error" class="text-caption text-orange">{{ error }}</div>

      <template v-else-if="data">
        <div v-if="data.suspects.length" class="verdict bad">
          ⚠️ Підозрілі комірки: <b>{{ data.suspects.map((c) => `#${c}`).join(', ') }}</b> —
          {{ data.method === 'soc'
            ? 'просідають при низькому заряді та «вистрибують» при повному, ознака меншої ємності.'
            : 'найбільше відхилення від середнього.' }}
        </div>
        <div v-else class="verdict good">✅ Комірки поводяться рівномірно.</div>

        <apex-chart type="heatmap" :height="Math.max(220, data.cells * 22 + 60)" :options="chartOptions" :series="series" />

        <q-markup-table dark dense flat class="stats">
          <thead>
            <tr>
              <th class="text-left">Комірка</th>
              <th>Сер., мВ</th>
              <th>SOC ≤ 30%</th>
              <th>SOC ≥ 90%</th>
              <th>Оцінка</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sortedStats" :key="s.cell" :class="{ suspect: data.suspects.includes(s.cell) }">
              <td class="text-left">#{{ s.cell }}</td>
              <td>{{ fmt(s.mean_dev_mv) }}</td>
              <td>{{ fmt(s.low_soc_dev_mv) }}</td>
              <td>{{ fmt(s.high_soc_dev_mv) }}</td>
              <td>{{ fmt(s.weak_score_mv) }}</td>
            </tr>
          </tbody>
        </q-markup-table>
        <p class="text-caption text-grey-5 q-mb-none">
          Оцінка = відхилення при повному заряді − відхилення при низькому. Чим більша (≥ 15 мВ), тим ймовірніше
          комірка має меншу ємність за інші. Колір: синій — нижче середнього, червоний — вище.
        </p>
      </template>
    </div>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { api } from 'src/axios-instance';

interface CellStat {
  cell: number;
  mean_dev_mv: number | null;
  max_abs_dev_mv: number;
  low_soc_dev_mv: number | null;
  high_soc_dev_mv: number | null;
  weak_score_mv: number | null;
}
interface History {
  cells: number;
  bucket_hours: number;
  buckets: string[];
  deviation_mv: (number | null)[][];
  cell_stats: CellStat[];
  suspects: number[];
  method: 'soc' | 'spread';
}

const DAY_OPTIONS = [
  { label: '7 днів', value: 7 },
  { label: '14 днів', value: 14 },
  { label: '30 днів', value: 30 },
  { label: '90 днів', value: 90 },
];

const open = ref(false);
const loading = ref(false);
const error = ref('');
const devices = ref<{ device_address: string; device_name: string }[]>([]);
const device = ref<string>();
const days = ref(14);
const data = ref<History>();

const deviceOptions = computed(() => devices.value.map((d) => ({ label: d.device_name || d.device_address, value: d.device_address })));
const sortedStats = computed(() =>
  [...(data.value?.cell_stats || [])].sort((a, b) => (b.weak_score_mv ?? b.max_abs_dev_mv) - (a.weak_score_mv ?? a.max_abs_dev_mv))
);

const series = computed(() => {
  if (!data.value) return [];
  const labels = data.value.buckets.map((b) => b.replace('T', ' ').slice(5, 16));
  // ApexCharts draws the first series at the bottom: reverse so cell #1 is on top.
  return data.value.deviation_mv
    .map((row, index) => ({ name: `#${index + 1}`, data: row.map((y, i) => ({ x: labels[i], y })) }))
    .reverse();
});

const chartOptions = computed(() => ({
  chart: { background: 'transparent', toolbar: { show: false }, foreColor: '#cfd8dc', animations: { enabled: false } },
  theme: { mode: 'dark' },
  dataLabels: { enabled: false },
  stroke: { width: 0 },
  xaxis: { type: 'category', tickAmount: 6, labels: { rotate: 0, hideOverlappingLabels: true } },
  tooltip: { y: { formatter: (v: number | null) => (v === null ? 'немає даних' : `${v > 0 ? '+' : ''}${v} мВ`) } },
  plotOptions: {
    heatmap: {
      enableShades: false,
      colorScale: {
        ranges: [
          { from: -10000, to: -30, color: '#0d47a1', name: '< −30 мВ' },
          { from: -30, to: -10, color: '#42a5f5', name: '−30…−10' },
          { from: -10, to: 10, color: '#37474f', name: '±10 мВ' },
          { from: 10, to: 30, color: '#ef9a9a', name: '10…30' },
          { from: 30, to: 10000, color: '#c62828', name: '> 30 мВ' },
        ],
      },
    },
  },
  legend: { position: 'bottom' },
}));

const fmt = (v: number | null) => (v === null || v === undefined ? '—' : `${v > 0 ? '+' : ''}${v}`);

async function loadDevices() {
  try {
    devices.value = (await api.get('/api/cells/devices')).data;
    if (!device.value && devices.value.length) device.value = devices.value[0]!.device_address;
  } catch (e) {
    console.error(e);
  }
}

async function loadHistory() {
  if (!device.value) return;
  loading.value = true;
  error.value = '';
  try {
    data.value = (await api.get('/api/cells/history', { params: { device: device.value, days: days.value }, timeout: 20000 })).data;
  } catch (e: any) {
    data.value = undefined;
    error.value = e?.response?.status === 404 ? 'За цей період історії ще немає.' : 'Не вдалося завантажити історію.';
  } finally {
    loading.value = false;
  }
}

watch(open, async (isOpen) => {
  if (isOpen && !devices.value.length) {
    loading.value = true;
    await loadDevices();
    loading.value = false;
  }
  if (isOpen) await loadHistory();
});
watch([device, days], () => open.value && loadHistory());
</script>

<style scoped lang="scss">
.heatmap {
  color: white;
}
.verdict {
  border-radius: 6px;
  padding: 6px 10px;
  &.bad {
    background: rgba(255, 152, 0, 0.18);
  }
  &.good {
    background: rgba(76, 175, 80, 0.15);
  }
}
.stats {
  background: transparent;
  th,
  td {
    text-align: right;
  }
  .suspect td {
    color: #ffb74d;
    font-weight: 700;
  }
}
</style>
