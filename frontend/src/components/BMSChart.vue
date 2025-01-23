<template>
  <div class="chart-container">
    <apex-chart type="line"
                :options="chartOptions"
                :series="series"></apex-chart>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import type { AxiosResponse } from 'axios';
import axios from 'axios';

const props = defineProps(['tab']);

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
    // title: { text: 'Value' },
    labels: {
      formatter: (val: number) => Math.round(val).toString(),
    },
    min: undefined,
  },
  tooltip: {
    x: { format: 'dd MMM yyyy HH:mm:ss' }, // Формат тултіпа
  },
  colors: ['#FF4560', '#008FFB', '#F2C037'], // Кольори серій
});

// Серії для графіка
const series = ref<SeriesData[]>([]);
const data = ref();

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
    const uniqueDevices: Record<string, any> = {};

    data.forEach((item) => {
      const deviceName = item[6];
      if (!uniqueDevices[deviceName]) {
        uniqueDevices[deviceName] = item; // Зберігаємо перший запис для пристрою
      }
    });

    // Перетворюємо унікальні записи в масив
    const uniqueData = Object.values(uniqueDevices);

    // Групуємо дані за хвилинами
    const groupedData: Record<string, { voltageSum: number; currentSum: number; count: number; powerSum: number; }> = {};

    uniqueData.forEach((item: any) => {
      const minuteKey = new Date(item[1]).toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
      if (!groupedData[minuteKey]) {
        groupedData[minuteKey] = { voltageSum: 0, currentSum: 0, powerSum: 0, count: 0 };
      }
      groupedData[minuteKey].voltageSum += item[2]; // Напруга
      groupedData[minuteKey].currentSum += item[3]; // Струм
      groupedData[minuteKey].powerSum += item[4]; // Сила
      groupedData[minuteKey].count += 1;
    });

    // Формуємо серії для графіка
    const voltageSeries = Object.entries(groupedData).map(([minute, values]) => ({
      x: minute,
      y: values.voltageSum / values.count,
    }));
    console.log(voltageSeries, 'voltageSeries');

    const currentSeries = Object.entries(groupedData).map(([minute, values]) => ({
      x: minute,
      y: values.currentSum,
    }));
    console.log(currentSeries, 'currentSeries');

    const powerSeries = Object.entries(groupedData).map(([minute, values]) => ({
      x: minute,
      y: values.powerSum,
    }));
    console.log(powerSeries, 'powerSeries');

    return { voltageSeries, currentSeries, powerSeries };
  } else {
    // Фільтруємо дані за `tab`
    const filteredData = data.filter((item) => item[6] === tab);

    const voltageSeries = filteredData.map((item) => ({
      x: new Date(item[1]).toISOString(),
      y: item[2],
    }));

    const currentSeries = filteredData.map((item) => ({
      x: new Date(item[1]).toISOString(),
      y: item[3],
    }));

    const powerSeries = filteredData.map((item) => ({
      x: new Date(item[1]).toISOString(),
      y: item[4],
    }));

    return { voltageSeries, currentSeries, powerSeries };
  }
}

onMounted(async () => {
  try {
    data.value = await fetchAggregatedData(1);
    console.log('Aggregated Data: ', data.value);

    if (!data.value) {
      return;
    }

    const { voltageSeries, currentSeries, powerSeries } = processAggregatedData(data.value, props.tab);
    series.value = [
      {
        name: 'Voltage',
        data: voltageSeries,
      },
      {
        name: 'Current',
        data: currentSeries,
      },
      {
        name: 'Battery Power',
        data: powerSeries,
      },
    ];
  } catch (error) {
    console.error('Error fetching data:', error);
  }
});

watch(() => props.tab, async (newTab) => {
  try {
    const { voltageSeries, currentSeries, powerSeries } = processAggregatedData(data.value, newTab);

    series.value = [
      {
        name: 'Voltage',
        data: voltageSeries,
      },
      {
        name: 'Current',
        data: currentSeries,
      },
      {
        name: 'Battery Power',
        data: powerSeries,
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
</style>
