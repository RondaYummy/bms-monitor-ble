<template>
  <div class="chart-container">
    <apex-chart type="line"
                :options="chartOptions"
                :series="series"></apex-chart>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import type { AxiosResponse } from 'axios';
import axios from 'axios';

const props = defineProps(['tab']);

interface SeriesData {
  name: string;
  data: any[];
}

const chartOptions = ref({
  chart: {
    id: 'bms-data-chart',
    toolbar: { show: true },
  },
  xaxis: {
    type: 'datetime',
  },
  title: {
    text: 'BMS Data',
    align: 'left',
  },
  yaxis: {
    title: { text: 'Normalized Values (0-100)' },
    labels: {
      formatter: (val: number) => Math.round(val).toString(),
    },
  },
  tooltip: {
    x: { format: 'dd MMM yyyy HH:mm:ss' },
    theme: 'dark',
  },
  colors: ['#FF4560', '#008FFB'], // Червоний і синій кольори
});

const series = ref<SeriesData[]>([]);
const data = ref();
const days = ref(3);
const intervalId = ref();

async function fetchAggregatedData(days: number = 1): Promise<any[]> {
  try {
    const response: AxiosResponse<any[]> = await axios.get(`/api/aggregated-data?days=${days}`);
    if (!response?.data) {
      throw new Error('Failed to fetch aggregated data');
    }
    return response.data;
  } catch (error) {
    console.error('Error fetching aggregated data:', error);
    return [];
  }
}

function calculateMinMax(series: any[]) {
  const values = series.map(item => item.y);
  return { min: Math.min(...values), max: Math.max(...values) };
}

function normalizeData(series: any[], min: number, max: number) {
  return series.map(item => ({
    x: item.x,
    y: ((item.y - min) / (max - min)) * 100, // Масштабування до 0-100
  }));
}

function processAggregatedData(data: any[], tab: string) {
  const filteredData = data.filter((item) => item[6] === tab);

  const currentSeries = filteredData.map((item) => ({
    x: new Date(item[1]).toISOString(),
    y: item[3], // Струм
  }));

  const powerSeries = filteredData.map((item) => ({
    x: new Date(item[1]).toISOString(),
    y: item[4], // Потужність
  }));

  // Розрахунок min/max
  const { min: currentMin, max: currentMax } = calculateMinMax(currentSeries);
  const { min: powerMin, max: powerMax } = calculateMinMax(powerSeries);

  // Нормалізація даних
  const normalizedCurrent = normalizeData(currentSeries, currentMin, currentMax);
  const normalizedPower = normalizeData(powerSeries, powerMin, powerMax);

  return { normalizedCurrent, normalizedPower };
}

async function fetchDataAndProcess(days: number = 1) {
  try {
    data.value = await fetchAggregatedData(days);

    if (!data.value) {
      return;
    }

    const { normalizedCurrent, normalizedPower } = processAggregatedData(data.value, props.tab);
    series.value = [
      {
        name: 'Current (Normalized)',
        data: normalizedCurrent,
      },
      {
        name: 'Battery Power (Normalized)',
        data: normalizedPower,
      },
    ];
  } catch (error) {
    console.error('Error fetching data:', error);
  }
}

onMounted(async () => {
  await fetchDataAndProcess(days.value);
  intervalId.value = setInterval(async () => {
    await fetchDataAndProcess(days.value);
  }, 60000);
});

onBeforeUnmount(async () => {
  clearInterval(intervalId.value);
});

watch(() => props.tab, async (newTab) => {
  try {
    const { normalizedCurrent, normalizedPower } = processAggregatedData(data.value, newTab);

    series.value = [
      {
        name: 'Current (Normalized)',
        data: normalizedCurrent,
      },
      {
        name: 'Battery Power (Normalized)',
        data: normalizedPower,
      },
    ];
  } catch (error) {
    console.error('Error processing data:', error);
  }
});
</script>

<style scoped lang="scss">
.chart-container {
  width: 100%;
}

.apexcharts-tooltip {
  background: #1e1f26;
  color: white;
}
</style>
