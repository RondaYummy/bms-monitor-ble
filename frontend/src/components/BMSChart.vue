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
  yaxis: number;
}

const chartOptions = ref({
  chart: {
    id: 'bms-data-chart',
    toolbar: { show: true },
  },
  legend: {
    show: false,
  },
  xaxis: {
    type: 'datetime',
  },
  title: {
    text: 'BMS Data',
    align: 'left',
  },
  yaxis: [
    {
      // title: { text: 'Battery Power' }, // Ліва вісь Y
      labels: {
        formatter: (val: number) => Math.round(val).toString(),
      },
    },
    {
      opposite: true, // Права вісь Y
      // title: { text: 'Current' },
      labels: {
        formatter: (val: number) => Math.round(val).toString(),
      },
    },
  ],
  tooltip: {
    x: { format: 'dd MMM yyyy HH:mm:ss' },
    theme: 'dark',
  },
  colors: ['#FF4560', '#008FFB', '#F2C037'],
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

function processAggregatedData(data: any[], tab: string) {
  if (tab === 'All') {
    const groupedData: Record<string, { currentSum: number; count: number; powerSum: number; }> = {};

    data.forEach((item: any) => {
      const minuteKey = new Date(item[1]).toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
      if (!groupedData[minuteKey]) {
        groupedData[minuteKey] = { currentSum: 0, powerSum: 0, count: 0 };
      }
      groupedData[minuteKey].currentSum += item[3]; // Струм
      groupedData[minuteKey].powerSum += item[4]; // Сила
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
    // Фільтруємо дані за `tab`
    const filteredData = data.filter((item) => item[6] === tab);

    const currentSeries = filteredData.map((item) => ({
      x: new Date(item[1]).toISOString(),
      y: item[3],
    }));

    const powerSeries = filteredData.map((item) => ({
      x: new Date(item[1]).toISOString(),
      y: item[4],
    }));

    return { currentSeries, powerSeries };
  }
}

async function fetchDataAndProcess(days: number = 1) {
  try {
    data.value = await fetchAggregatedData(days);
    console.log('Aggregated Data: ', data.value);

    if (!data.value) {
      return;
    }

    const { currentSeries, powerSeries } = processAggregatedData(data.value, props.tab);
    series.value = [
      {
        name: 'Current',
        data: currentSeries,
        yaxis: 0, // Використовує праву вісь Y
      },
      {
        name: 'Battery Power',
        data: powerSeries,
        yaxis: 0, // Використовує ліву вісь Y
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
    const { currentSeries, powerSeries } = processAggregatedData(data.value, newTab);

    series.value = [
      {
        name: 'Current',
        data: currentSeries,
        yaxis: 0, // Використовує праву вісь Y
      },
      {
        name: 'Battery Power',
        data: powerSeries,
        yaxis: 0, // Використовує ліву вісь Y
      },
    ];
  } catch (error) {
    console.error('Error processing data:', error);
  }
});
</script>

<style scoped lang='scss'>
.chart-container {
  width: 100%;
}

.apexcharts-tooltip {
  background: #1e1f26;
  color: white;
}
</style>
