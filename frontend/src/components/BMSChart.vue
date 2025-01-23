<template>
  <div class="chart-container">
    <apex-chart type="line"
                :options="chartOptions"
                :series="series"></apex-chart>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import type { AxiosResponse } from 'axios';
import axios from 'axios';

interface SeriesData {
  name: string;
  data: any[];
}

// Ініціалізація даних графіка
const chartOptions = ref({
  chart: {
    id: 'bms-data-chart',
    toolbar: { show: true },
  },
  xaxis: {
    type: 'datetime',
    categories: [], // Дата або інші категорії
  },
  title: {
    text: 'BMS Data',
    align: 'left',
  },
  yaxis: {
    title: { text: 'Value' },
    labels: {
      formatter: (val: number) => Math.round(val).toString(),
    },
    min: undefined,
  },
  tooltip: {
    x: { format: 'dd MMM yyyy HH:mm:ss' }, // Формат тултіпа
  },
  colors: ['#FF4560', '#008FFB'], // Кольори серій
});

// Серії для графіка
const series = ref<SeriesData[]>([]);

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

onMounted(async () => {
  try {
    const data = await fetchAggregatedData();
    console.log('Aggregated Data: ', data);

    if (!data) {
      return;
    }

    const voltageSeries = data.map((item: any) => ({
      x: new Date(item[1]).toISOString(), // Дата в ISO форматі
      y: item[2]?.toFixed(2), // Значення напруги
    }));
    const currentSeries = data.map((item: any) => ({
      x: new Date(item[1]).toISOString(), // Дата в ISO форматі
      y: item[3]?.toFixed(2), // Значення струму
    }));
    // const categories = data.map((item: any) => item[1]); // Дата
    // const voltageSeries = data.map((item: any) => item[2]); // Напруга
    // const currentSeries = data.map((item: any) => item[3]); // Струм
    // console.log(categories, 'categories');

    // // Оновлюємо графік
    // chartOptions.value.xaxis.categories = categories;
    series.value = [
      {
        name: 'Voltage',
        data: voltageSeries,
      },
      {
        name: 'Current',
        data: currentSeries,
      },
    ];
  } catch (error) {
    console.error('Error fetching data:', error);
  }
});
</script>

<style scoped>
.chart-container {
  width: 100%;
  min-height: 300px;
}
</style>
