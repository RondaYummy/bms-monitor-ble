<template>
  <div class="chart-container q-mt-md">
    <div class="row">
      <div class="chart-actions">
        <q-btn id="one_day"
               label="Day"
               :disable="selectedRange === '1d'"
               :loading="loadingRangeData === '1d'"
               :color="selectedRange === '1d' ? 'bg-positive' : ''"
               size="sm"
               flat
               @click="zoomRange('1d')" />
        <q-btn id="one_week"
               label="Week"
               :disable="selectedRange === '1w'"
               :loading="loadingRangeData === '1w'"
               :color="selectedRange === '1w' ? 'bg-positive' : ''"
               size="sm"
               flat
               @click="zoomRange('1w')" />
        <q-btn id="one_month"
               label="Month"
               :disable="selectedRange === '1m'"
               :loading="loadingRangeData === '1m'"
               :color="selectedRange === '1m' ? 'bg-positive' : ''"
               size="sm"
               flat
               @click="zoomRange('1m')" />
        <q-btn id="one_year"
               label="Year"
               :disable="selectedRange === '1y'"
               :loading="loadingRangeData === '1y'"
               :color="selectedRange === '1y' ? 'bg-positive' : ''"
               size="sm"
               flat
               @click="zoomRange('1y')" />
        <q-btn id="custom"
               label="Custom"
               size="sm"
               :color="selectedRange === 'custom' ? 'bg-positive' : ''"
               :loading="loadingRangeData === 'custom'"
               flat
               @click="rangeDialog = true" />

        <q-dialog v-model="rangeDialog">
          <q-date v-model="range"
                  @update:model-value="zoomRange('custom')"
                  range />
        </q-dialog>
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
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        if (diff > 2 * 24 * 60 * 60 * 1000) {
          return date.toLocaleDateString('uk-UA', {
            day: '2-digit',
            month: 'short',
            year: '2-digit'
          });
        } else {
          return date.toLocaleTimeString('uk-UA', {
            hour: '2-digit',
            minute: '2-digit'
          });
        }
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
        return `${date.toLocaleDateString('en-GB', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        })} ${date.toLocaleTimeString('en-GB', {
          hour: '2-digit',
          minute: '2-digit',
        })}`;
      },
    },
  },
  // colors: ['#FF4560', '#008FFB', '#F2C037'],
});

const series = ref<SeriesData[]>([]);
const data = ref();
const days = ref(1);
const intervalId = ref();

async function zoomRange(ranges: '1d' | '1w' | '1m' | '1y' | 'custom') {
  if (!chartRef.value) return;
  selectedRange.value = ranges;
  loadingRangeData.value = ranges;

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
  console.log(range.value, 'range.value');
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
    const groupedData: Record<string, { currentSum: number; count: number; powerSum: number; }> = {};

    data.forEach((item: any) => {
      const date = new Date(item[1]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      const minuteKey = localDate.toISOString().slice(0, 16);

      if (!groupedData[minuteKey]) {
        groupedData[minuteKey] = { currentSum: 0, powerSum: 0, count: 0 };
      }
      groupedData[minuteKey].currentSum += item[2];
      groupedData[minuteKey].powerSum += item[3];
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

    return { currentSeries, powerSeries };
  } else {
    // Filter data by `tab`
    const filteredData = data.filter((item) => item[5] === tab);
    const currentSeries = filteredData.map((item) => {
      const date = new Date(item[1]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      return {
        x: localDate.toISOString().slice(0, 16),
        y: item[2],
      };
    });

    const powerSeries = filteredData.map((item) => {
      const date = new Date(item[1]);
      const offset = date.getTimezoneOffset();
      const localDate = new Date(date.getTime() - offset * 60 * 1000);
      return {
        x: localDate.toISOString().slice(0, 16),
        y: item[3],
      };
    });

    return { currentSeries, powerSeries };
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
    console.log('Aggregated Data: ', data.value);

    if (!data.value) {
      return;
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { currentSeries, powerSeries } = processAggregatedData(data.value, props.tab);
    series.value = [
      {
        name: 'Battery Power',
        data: powerSeries,
      },
      // {
      //   name: 'Current',
      //   data: currentSeries,
      // },
    ];
  } catch (error) {
    console.error('Error fetching data:', error);
  }
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
  async (newTab) => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { currentSeries, powerSeries } = processAggregatedData(data.value, newTab);

      series.value = [
        {
          name: 'Battery Power',
          data: powerSeries,
        },
        // {
        //   name: 'Current',
        //   data: currentSeries,
        // },
      ];
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
.apexcharts-menu,
:deep(.q-date__header),
:deep(.q-date__view) {
  background: #1e1f26;
  color: white;
}
</style>
