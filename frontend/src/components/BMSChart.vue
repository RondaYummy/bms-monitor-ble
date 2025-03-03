<template>
  <div class="chart-container q-mt-md">
    <div class="row">
      <div class="chart-actions">
        <q-btn id="one_day"
               label="Day"
               :disable="selectedRange === '1d'"
               :loading="loadingRangeData === '1d'"
               :color="selectedRange === '1d' ? 'bg-positive' : ''"
               size="xs"
               flat
               @click="zoomRange('1d')" />
        <q-btn id="one_week"
               label="Week"
               :disable="selectedRange === '1w'"
               :loading="loadingRangeData === '1w'"
               :color="selectedRange === '1w' ? 'bg-positive' : ''"
               size="xs"
               flat
               @click="zoomRange('1w')" />
        <q-btn id="one_month"
               label="Month"
               :disable="selectedRange === '1m'"
               :loading="loadingRangeData === '1m'"
               :color="selectedRange === '1m' ? 'bg-positive' : ''"
               size="xs"
               flat
               @click="zoomRange('1m')" />
        <q-btn id="one_year"
               label="Year"
               :disable="selectedRange === '1y'"
               :loading="loadingRangeData === '1y'"
               :color="selectedRange === '1y' ? 'bg-positive' : ''"
               size="xs"
               flat
               @click="zoomRange('1y')" />
        <q-btn id="custom"
               label="Custom"
               size="xs"
               :color="selectedRange === 'custom' ? 'bg-positive' : ''"
               :loading="loadingRangeData === 'custom'"
               flat
               @click="rangeDialog = true" />

        <q-dialog v-model="rangeDialog">
          <div class="column q-gutter-sm">
            <div class="date-box">
              <q-date v-model="range"
                      @update:model-value="zoomRange('custom')"
                      range />
              <q-btn label="OK"
                     color="secondary"
                     @click="rangeDialog = false" />
            </div>
          </div>
        </q-dialog>
      </div>
      <div class="chart-actions">
        <q-btn id="power"
               label="Power"
               :disable="selectedTypeChart === 'power'"
               :color="selectedTypeChart === 'power' ? 'bg-positive' : ''"
               size="xs"
               @click="selectTypeChart('power')">
          <q-tooltip :delay="200">
            Battery Power — Це потужність, яку батарея видає в даний момент.
            Обчислюється як добуток напруги та струму (W).
          </q-tooltip>
        </q-btn>
        <q-btn label="Current"
               :disable="selectedTypeChart === 'current'"
               :color="selectedTypeChart === 'current' ? 'bg-positive' : ''"
               size="xs"
               @click="selectTypeChart('current')">
          <q-tooltip :delay="200">
            Струм заряду, якщо число додатнє, йде заряджання а якщо
            відємне
            -
            розряжання.
          </q-tooltip>
        </q-btn>
        <q-btn label="Capacity"
               :disable="selectedTypeChart === 'remainingCapacity'"
               :color="selectedTypeChart === 'remainingCapacity' ? 'bg-positive' : ''"
               size="xs"
               @click="selectTypeChart('remainingCapacity')">
          <q-tooltip :delay="200">
            Це значення вказує на залишкову ємність батареї. Зазвичай воно
            обчислюється у міліампер-годинах (mAh) або ампер-годинах (Ah).
          </q-tooltip>
        </q-btn>
      </div>
    </div>
    <apex-chart ref="chartRef"
                type="line"
                :options="chartOptions"
                :series="series"></apex-chart>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import type ApexCharts from 'apexcharts';

const props = defineProps(['tab']);

interface SeriesData {
  name: string;
  data: any[];
  yaxis?: number;
}
const chartRef = ref<{ chart: ApexCharts; } | null>(null);
const selectedRange = ref('1d');
const loadingRangeData = ref('');
const rangeDialog = ref(false);
const range = ref();
const selectedTypeChart = ref<"power" | "current" | "remainingCapacity">('power');

const chartOptions = ref({
  chart: {
    id: 'bms-data-chart',
    type: 'area',
    background: '#1e1f26',
    zoom: {
      enabled: true,
    },
    animations: {
      enabled: true,
      easing: 'linear',
      dynamicAnimation: {
        speed: 1000,
      },
    },
    dropShadow: {
      enabled: true,
      opacity: 0.3,
      blur: 5,
      left: -7,
      top: 7,
    },
  },
  stroke: {
    curve: 'smooth',
    width: 3,
  },
  grid: {
    borderColor: '#222226',
    padding: {
      left: 0,
      right: 0,
    },
  },
  markers: {
    colors: ['#FFFFFF'],
  },
  dataLabels: {
    enabled: false,
  },
  legend: {
    show: false,
  },
  xaxis: {
    type: 'datetime',
    axisBorder: {
      show: true,
      color: '#222226',
    },
    axisTicks: {
      show: true,
      color: '#555',
      height: 6,
    },
    tickAmount: 6,
    labels: {
      style: {
        colors: '#aaa',
      },
      formatter: function (value: string | number) {
        const date = new Date(value);
        return date.toLocaleTimeString('uk-UA', {
          hour: '2-digit',
          minute: '2-digit'
        });
      }
    },
  },
  title: {
    text: 'BMS',
    align: 'left',
  },
  yaxis: [
    {
      show: false,
      labels: {
        formatter: (val: number) => Math.round(val).toString(),
      },
    },
    {
      show: false,
      opposite: true, // Right Y-axis
      labels: {
        formatter: (val: number) => Math.round(val).toString(),
      },
    },
  ],
  tooltip: {
    shared: true,
    intersect: false,
    theme: 'dark',
    y: [
      {
        formatter: (val: number) => `${val?.toFixed(2)} W`,
      },
      {
        formatter: (val: number) => `${val?.toFixed(2)} A`,
      },
    ],
    x: {
      formatter: (value: string) => {
        const date = new Date(value);
        return `${date.toLocaleDateString('uk-UA', {
          day: '2-digit',
          month: 'short',
          year: '2-digit'
        })} ${date.toLocaleTimeString('uk-UA', {
          hour: '2-digit',
          minute: '2-digit',
        })}`;
      },
    },
  },
  colors: ['#0480de'],
});

const series = ref<SeriesData[]>([]);
const data = ref();
const days = ref(1);
const intervalId = ref();

async function zoomRange(ranges: '1d' | '1w' | '1m' | '1y' | 'custom') {
  if (!chartRef.value) return;
  selectedRange.value = ranges;
  loadingRangeData.value = ranges;
  selectedTypeChart.value = 'power';

  if (ranges === '1d') {
    days.value = 1;
  } else if (ranges === '1w') {
    days.value = 7;
  } else if (ranges === '1m') {
    days.value = 30;
  } else if (ranges === '1y') {
    days.value = 365;
  } else if (ranges === 'custom') {
    days.value = 0;
  }

  if (ranges !== 'custom') {
    range.value = '';
  }
  await fetchDataAndProcess(days.value, range.value);

  const chart = chartRef.value?.chart;
  const now = new Date().getTime();

  let from, to;
  switch (range.value) {
    case '1d': // 1 day
      from = now - 24 * 60 * 60 * 1000;
      to = now;
      break;
    case '1w': // 1 week
      from = now - 7 * 24 * 60 * 60 * 1000;
      to = now;
      break;
    case '1m': // 1 month
      from = now - 30 * 24 * 60 * 60 * 1000;
      to = now;
      break;
    case '1y': // 1 year
      from = now - 365 * 24 * 60 * 60 * 1000;
      to = now;
      break;
    // case 'custom':
    //   from = new Date(range.value.from).getTime();
    //   to = new Date(range.value.to).getTime() + 23 * 60 * 60 * 1000 + 59 * 60 * 1000 + 59 * 1000;
    //   break;
    default:
      // Якщо дані вже завантажено, беремо перший і останній час з першої серії
      if (series.value[0]?.data.length) {
        from = new Date(series.value[0].data[0].x).getTime();
        const lastIndex = series.value[0].data.length - 1;
        to = new Date(series.value[0].data[lastIndex].x).getTime();
      } else {
        from = now - 30 * 24 * 60 * 60 * 1000;
        to = now;
      }
      break;
  }

  loadingRangeData.value = '';
  chart.zoomX(from, to);
}

async function fetchAggregatedData(
  days: number = 1,
  range?: {
    from: string;
    to: string;
  },
): Promise<any[]> {
  try {
    let url = `/api/aggregated-data?days=${days}`;
    if (range && range.from && range.to) {
      url += `&from=${encodeURIComponent(range.from)}&to=${encodeURIComponent(range.to)}`;
    }
    const response: any = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to fetch aggregated data');
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching aggregated data:', error);
    return [];
  }
}

function processAggregatedData(data: any[], tab: string) {
  if (tab === 'All') {
    const groupedData: Record<string, { currentSum: number; count: number; powerSum: number; remainingCapacitySum: number; }> = {};

    data.forEach((item: any) => {
      const date = new Date(item[0]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      const minuteKey = localDate.toISOString().slice(0, 16);

      if (!groupedData[minuteKey]) {
        groupedData[minuteKey] = { currentSum: 0, powerSum: 0, count: 0, remainingCapacitySum: 0 };
      }
      groupedData[minuteKey].currentSum += item[1];
      groupedData[minuteKey].powerSum += item[2];
      groupedData[minuteKey].remainingCapacitySum += item[5];
      groupedData[minuteKey].count += 1;
    });

    const currentSeries = Object.entries(groupedData).map(([minute, values]) => ({
      x: minute,
      y: values.currentSum,
    }));

    const powerSeries = Object.entries(groupedData).map(([minute, values]) => ({
      x: minute,
      y: values.powerSum,
    }));

    const remainingCapacitySeries = Object.entries(groupedData).map(([minute, values]) => ({
      x: minute,
      y: values.remainingCapacitySum,
    }));

    return { currentSeries, powerSeries, remainingCapacitySeries };
  } else {
    // Filter data by `tab`
    const filteredData = data.filter((item) => item[4] === tab);
    const currentSeries = filteredData.map((item) => {
      const date = new Date(item[0]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      return {
        x: localDate.toISOString().slice(0, 16),
        y: item[1],
      };
    });

    const powerSeries = filteredData.map((item) => {
      const date = new Date(item[0]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      return {
        x: localDate.toISOString().slice(0, 16),
        y: item[2],
      };
    });

    const remainingCapacitySeries = filteredData.map((item) => {
      const date = new Date(item[0]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      return {
        x: localDate.toISOString().slice(0, 16),
        y: item[5],
      };
    });

    return { currentSeries, powerSeries, remainingCapacitySeries };
  }
}

async function fetchDataAndProcess(
  days: number = 1,
  range?: {
    from: string;
    to: string;
  },
) {
  try {
    data.value = await fetchAggregatedData(days, range);

    if (!data.value) {
      return;
    }

    selectTypeChart(selectedTypeChart.value);
    chartRef.value?.chart.updateOptions(chartOptions.value);
  } catch (error) {
    console.error('Error fetching data:', error);
  }
}

function selectTypeChart(type: 'power' | 'current' | 'remainingCapacity') {
  selectedTypeChart.value = type;
  const { currentSeries, powerSeries, remainingCapacitySeries } = processAggregatedData(data.value, props.tab);
  if (type === 'power') {
    chartOptions.value.tooltip.y = [{
      formatter: (val: number) => `${val?.toFixed(2)} W`,
    }];
    series.value = [
      {
        name: 'Battery Power',
        data: powerSeries,
      },
    ];
  }
  if (type === 'current') {
    chartOptions.value.tooltip.y = [{
      formatter: (val: number) => `${val?.toFixed(2)} A`,
    }];
    series.value = [
      {
        name: 'Current',
        data: currentSeries,
      },
    ];
  }
  if (type === 'remainingCapacity') {
    chartOptions.value.tooltip.y = [{
      formatter: (val: number) => `${val?.toFixed(2)} Ah`,
    }];
    series.value = [
      {
        name: 'Capacity',
        data: remainingCapacitySeries,
      },
    ];
  }
  chartRef.value?.chart.updateOptions(chartOptions.value);
}

onMounted(async () => {
  loadingRangeData.value = '1d';
  await fetchDataAndProcess(days.value, range.value);
  loadingRangeData.value = '';
  intervalId.value = setInterval(async () => {
    await fetchDataAndProcess(days.value, range.value);
  }, 30000);
});

onBeforeUnmount(async () => {
  clearInterval(intervalId.value);
});

watch(
  () => props.tab,
  async () => {
    try {
      selectTypeChart(selectedTypeChart.value);
    } catch (error) {
      console.error('Error processing data:', error);
    }
  },
);
</script>

<style scoped lang="scss">
.chart-container {
  width: 100%;
}

.apexcharts-tooltip,
:deep(.apexcharts-menu),
:deep(.q-date__header),
:deep(.q-date__view),
:deep(.q-date) {
  background: #1e1f26;
  color: white;
  box-shadow: none;
}

.date-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #1e1f26;
  color: white;
  padding: 10px;
}
</style>
