<template>
  <q-page class="energy-page q-pa-md">
    <div class="row items-center justify-between q-mb-sm no-print">
      <div class="text-h6">💰 Економія енергії</div>
      <div class="row q-gutter-xs">
        <q-btn dense flat icon="tune" color="white" @click="tariffsOpen = true"><q-tooltip>Тарифи</q-tooltip></q-btn>
        <q-btn dense flat icon="download" color="white" :loading="downloading" @click="downloadCsv">
          <q-tooltip>CSV</q-tooltip>
        </q-btn>
        <q-btn dense flat icon="print" color="white" @click="printReport"><q-tooltip>Звіт / PDF</q-tooltip></q-btn>
      </div>
    </div>

    <div class="row q-col-gutter-sm items-end q-mb-md no-print">
      <q-select v-model="period" class="col-12 col-sm-4" dark filled dense emit-value map-options
        :options="periodOptions" label="Період" />
      <template v-if="period === 'custom'">
        <q-input v-model="customFrom" class="col-6 col-sm-3" dark filled dense type="date" label="Від" />
        <q-input v-model="customTo" class="col-6 col-sm-3" dark filled dense type="date" label="До" />
        <div class="col-12 col-sm-2"><q-btn class="full-width" color="positive" label="Показати" @click="load" /></div>
      </template>
    </div>

    <h5 class="print-only">Звіт про енергію та економію: {{ report?.from }} — {{ report?.to }}</h5>

    <div v-if="loading && !report" class="text-center q-pa-lg"><q-spinner color="white" size="2em" /></div>

    <template v-else-if="report">
      <div v-if="!report.days.length" class="empty q-pa-md">
        Даних за цей період ще немає. Облік кВт·год ведеться з моменту оновлення системи (кожні 3 с з інвертора Deye).
      </div>

      <template v-else>
        <div class="row q-col-gutter-sm q-mb-md">
          <div v-for="tile in tiles" :key="tile.label" class="col-6 col-sm-3">
            <div class="tile" :class="tile.cls">
              <div class="tile-label">{{ tile.label }}</div>
              <div class="tile-value">{{ tile.value }}</div>
              <div v-if="tile.hint" class="tile-hint">{{ tile.hint }}</div>
            </div>
          </div>
        </div>

        <apex-chart type="bar" height="280" :options="chartOptions" :series="chartSeries" class="q-mb-md" />

        <q-markup-table dark dense flat class="days-table">
          <thead>
            <tr>
              <th class="text-left">Дата</th>
              <th>PV</th>
              <th>Спож.</th>
              <th>Мережа</th>
              <th>Продано</th>
              <th>Витрати</th>
              <th>Економія</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="day in report.days" :key="day.date">
              <td class="text-left">{{ day.date.slice(5) }}</td>
              <td>{{ kwh(day.pv) }}</td>
              <td>{{ kwh(day.load) }}</td>
              <td>{{ kwh(day.grid_in) }}<span v-if="tariffs.two_zone" class="text-grey-5"> ({{ kwh(day.grid_in_night) }} н)</span></td>
              <td>{{ kwh(day.grid_out) }}</td>
              <td>{{ money(day.cost) }}</td>
              <td class="text-green">{{ money(day.savings) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="total">
              <td class="text-left">Разом</td>
              <td>{{ kwh(report.totals.pv) }}</td>
              <td>{{ kwh(report.totals.load) }}</td>
              <td>{{ kwh(report.totals.grid_in) }}</td>
              <td>{{ kwh(report.totals.grid_out) }}</td>
              <td>{{ money(report.totals.cost) }}</td>
              <td class="text-green">{{ money(report.totals.savings) }}</td>
            </tr>
          </tfoot>
        </q-markup-table>

        <p class="text-caption text-grey-5 q-mt-sm">
          Тариф: {{ tariffs.day_price }} {{ tariffs.currency }}/кВт·год
          <span v-if="tariffs.two_zone">, ніч ({{ tariffs.night_start }}–{{ tariffs.night_end }}): {{ tariffs.night_price }}</span>
          <span v-if="tariffs.export_price">, продаж: {{ tariffs.export_price }}</span>.
          «Без системи» — вартість того самого споживання, якби вся енергія купувалась із мережі.
        </p>
      </template>
    </template>

    <q-dialog v-model="tariffsOpen">
      <div class="column dialog-body q-gutter-y-sm">
        <h6 class="q-my-none">Тарифи</h6>
        <div class="row q-col-gutter-sm">
          <q-input v-model.number="form.day_price" class="col-8" dark filled dense type="number" step="0.01"
            label="Ціна, за кВт·год (день)" :disable="!canEdit" />
          <q-input v-model="form.currency" class="col-4" dark filled dense label="Валюта" :disable="!canEdit" />
        </div>
        <q-toggle v-model="form.two_zone" dark color="positive" label="Двозонний лічильник (дешевша ніч)" :disable="!canEdit" />
        <div v-if="form.two_zone" class="row q-col-gutter-sm">
          <q-input v-model.number="form.night_price" class="col-4" dark filled dense type="number" step="0.01"
            label="Ціна вночі" :disable="!canEdit" />
          <q-select v-model="form.night_start" class="col-4" dark filled dense :options="HOURS" label="Ніч з" :disable="!canEdit" />
          <q-select v-model="form.night_end" class="col-4" dark filled dense :options="HOURS" label="до" :disable="!canEdit" />
        </div>
        <q-input v-model.number="form.export_price" dark filled dense type="number" step="0.01"
          label="«Зелений» тариф / ціна продажу за кВт·год" :disable="!canEdit" />
        <p class="text-caption text-grey-5 q-mb-none">Тарифи застосовуються до всієї історії при перерахунку.</p>
        <div class="row justify-between">
          <q-btn color="positive" size="sm" label="Зберегти" :disable="!canEdit" :loading="saving" @click="saveTariffs" />
          <q-btn color="black" size="sm" label="Закрити" @click="tariffsOpen = false" />
        </div>
      </div>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { useAuth } from 'src/helpers/utils';

interface Tariffs {
  currency: string;
  day_price: number;
  two_zone: boolean;
  night_price: number;
  night_start: string;
  night_end: string;
  export_price: number;
}
interface DayRow {
  date: string;
  pv: number;
  load: number;
  grid_in: number;
  grid_in_day: number;
  grid_in_night: number;
  grid_out: number;
  bat_charge: number;
  bat_discharge: number;
  cost: number;
  cost_without_system: number;
  export_income: number;
  savings: number;
  self_sufficiency: number | null;
}
interface Report {
  from: string;
  to: string;
  tariffs: Tariffs;
  totals: Omit<DayRow, 'date'>;
  days: DayRow[];
}

const HOURS = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, '0')}:00`);
const { isAdmin: canEdit } = useAuth();

const report = ref<Report>();
const loading = ref(false);
const downloading = ref(false);
const saving = ref(false);
const tariffsOpen = ref(false);
const months = ref<{ month: string; savings: number }[]>([]);
const period = ref<string>(new Date().toISOString().slice(0, 7));
const customFrom = ref('');
const customTo = ref('');
const form = ref<Tariffs>({
  currency: 'грн', day_price: 4.32, two_zone: false, night_price: 2.16,
  night_start: '23:00', night_end: '07:00', export_price: 0,
});
const tariffs = computed(() => report.value?.tariffs || form.value);

const periodOptions = computed(() => {
  const current = new Date().toISOString().slice(0, 7);
  const list = new Set([current, ...months.value.map((m) => m.month)]);
  return [
    ...[...list].sort().reverse().map((m) => ({ label: monthLabel(m), value: m })),
    { label: 'Останні 30 днів', value: 'last30' },
    { label: 'Довільний період', value: 'custom' },
  ];
});

function monthLabel(month: string) {
  const [y, m] = month.split('-').map(Number);
  return new Date(y!, m! - 1, 1).toLocaleDateString('uk-UA', { month: 'long', year: 'numeric' });
}
function isoDate(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function range(): { from: string; to: string } {
  if (period.value === 'custom') return { from: customFrom.value, to: customTo.value };
  if (period.value === 'last30') {
    const to = new Date();
    return { from: isoDate(new Date(to.getTime() - 29 * 86400000)), to: isoDate(to) };
  }
  const [y, m] = period.value.split('-').map(Number);
  return { from: isoDate(new Date(y!, m! - 1, 1)), to: isoDate(new Date(y!, m!, 0)) };
}

const kwh = (v: number) => (v ?? 0).toFixed(1);
const money = (v: number) => `${(v ?? 0).toFixed(2)}`;

const tiles = computed(() => {
  const t = report.value!.totals;
  const cur = tariffs.value.currency;
  return [
    { label: 'Зекономлено', value: `${money(t.savings)} ${cur}`, cls: 'good', hint: `без системи: ${money(t.cost_without_system)}` },
    { label: 'Сплачено за мережу', value: `${money(t.cost)} ${cur}`, hint: `${kwh(t.grid_in)} кВт·год` },
    { label: 'Продано в мережу', value: `${money(t.export_income)} ${cur}`, hint: `${kwh(t.grid_out)} кВт·год` },
    { label: 'Автономність', value: t.self_sufficiency === null ? '—' : `${Math.round(t.self_sufficiency * 100)}%`,
      hint: `генерація ${kwh(t.pv)} / спож. ${kwh(t.load)} кВт·год` },
  ];
});

const chartSeries = computed(() => [
  { name: 'Генерація', data: report.value?.days.map((d) => +d.pv.toFixed(2)) || [] },
  { name: 'Споживання', data: report.value?.days.map((d) => +d.load.toFixed(2)) || [] },
  { name: 'З мережі', data: report.value?.days.map((d) => +d.grid_in.toFixed(2)) || [] },
  { name: 'В мережу', data: report.value?.days.map((d) => +d.grid_out.toFixed(2)) || [] },
]);
const chartOptions = computed(() => ({
  chart: { background: 'transparent', toolbar: { show: false }, foreColor: '#cfd8dc' },
  theme: { mode: 'dark' },
  colors: ['#ffca28', '#42a5f5', '#ef5350', '#66bb6a'],
  plotOptions: { bar: { columnWidth: '70%' } },
  dataLabels: { enabled: false },
  xaxis: { categories: report.value?.days.map((d) => d.date.slice(5)) || [] },
  yaxis: { title: { text: 'кВт·год' }, labels: { formatter: (v: number) => v.toFixed(0) } },
  tooltip: { y: { formatter: (v: number) => `${v.toFixed(2)} кВт·год` } },
  legend: { position: 'top' },
  grid: { borderColor: '#37474f' },
}));

function notifyError(error: any, fallback: string) {
  const detail = error?.response?.data?.detail;
  Notify.create({ message: typeof detail === 'string' ? detail : fallback, color: 'red', position: 'top' });
}

async function load() {
  const { from, to } = range();
  if (!from || !to) return;
  loading.value = true;
  try {
    report.value = (await api.get('/api/energy/summary', { params: { from, to }, timeout: 15000 })).data;
    form.value = { ...report.value!.tariffs };
  } catch (error) {
    notifyError(error, 'Не вдалося завантажити звіт');
  } finally {
    loading.value = false;
  }
}

async function downloadCsv() {
  const { from, to } = range();
  downloading.value = true;
  try {
    const response = await api.get('/api/energy/export.csv', { params: { from, to }, responseType: 'blob', timeout: 30000 });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = url;
    link.download = `energy-${from}_${to}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  } catch (error) {
    notifyError(error, 'Не вдалося завантажити CSV');
  } finally {
    downloading.value = false;
  }
}

function printReport() {
  // The print stylesheet hides navigation/buttons; "Save as PDF" in the print dialog produces the PDF report.
  window.print();
}

async function saveTariffs() {
  saving.value = true;
  try {
    await api.put('/api/energy/tariffs', form.value);
    tariffsOpen.value = false;
    Notify.create({ message: 'Тарифи збережено', color: 'positive', position: 'top' });
    await load();
  } catch (error) {
    notifyError(error, 'Не вдалося зберегти тарифи');
  } finally {
    saving.value = false;
  }
}

watch(period, (value) => {
  if (value !== 'custom') void load();
});

onMounted(async () => {
  try {
    months.value = (await api.get('/api/energy/months')).data;
  } catch (error) {
    console.error(error);
  }
  await load();
});
</script>

<style scoped lang="scss">
.energy-page {
  color: white;
  max-width: 960px;
  margin: 0 auto;
}
.tile {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 8px 10px;
  height: 100%;
  &.good {
    background: rgba(76, 175, 80, 0.18);
  }
}
.tile-label {
  font-size: 0.75em;
  color: #bdbdbd;
}
.tile-value {
  font-size: 1.3em;
  font-weight: 700;
}
.tile-hint {
  font-size: 0.72em;
  color: #9e9e9e;
}
.days-table {
  background: transparent;
  overflow-x: auto;
  th,
  td {
    text-align: right;
    white-space: nowrap;
  }
  .total td {
    font-weight: 700;
    border-top: 1px solid #546e7a;
  }
}
.empty {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}
.dialog-body {
  padding: 20px;
  background: #1e1f26;
  color: white;
  max-width: 420px;
  width: 100%;
}
.print-only {
  display: none;
}

@media print {
  .no-print {
    display: none !important;
  }
  .print-only {
    display: block;
    color: black;
  }
  .energy-page,
  .days-table,
  .tile {
    color: black !important;
    background: white !important;
  }
}
</style>

<style lang="scss">
@media print {
  /* hide the app chrome (footer navigation) when printing the report */
  .q-footer,
  .q-header {
    display: none !important;
  }
  body,
  .q-page-container {
    background: white !important;
    padding: 0 !important;
  }
}
</style>
