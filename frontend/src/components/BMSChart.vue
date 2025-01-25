<template>
  <div class="chart-container">
    <apex-chart type="area"
                :options="chartOptions"
                :series="series"></apex-chart>
    <apex-chart type="bar"
                :options="chartOptions2"
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
  yaxis?: number;
}
const series = ref<SeriesData[]>([]);

const chartOptions = ref({
  chart: {
    id: "chart2",
    type: "area",
    height: 230,
    foreColor: "#ccc",
    toolbar: {
      autoSelected: "pan",
      show: false
    }
  },
  colors: ["#00BAEC"],
  stroke: {
    width: 3
  },
  grid: {
    borderColor: "#555",
    clipMarkers: false,
    yaxis: {
      lines: {
        show: false
      }
    }
  },
  dataLabels: {
    enabled: false
  },
  series: {
    data: series.value,
  },
  fill: {
    gradient: {
      enabled: true,
      opacityFrom: 0.55,
      opacityTo: 0
    }
  },
  markers: {
    size: 5,
    colors: ["#000524"],
    strokeColor: "#00BAEC",
    strokeWidth: 3
  },
  tooltip: {
    theme: "dark"
  },
  xaxis: {
    type: "datetime"
  },
  yaxis: {
    tickAmount: 4
  }
});

const chartOptions2 = ref({
  chart: {
    id: "chart1",
    height: 130,
    type: "bar",
    foreColor: "#ccc",
    brush: {
      target: "apexchartschart2",
      enabled: true
    },
    series: {
      data: series.value,
    },
    selection: {
      enabled: true,
      fill: {
        color: "#fff",
        opacity: 0.4
      },
      xaxis: {
        // type: 'datetime',
        // axisBorder: {
        //   show: false
        // },
        // axisTicks: {
        //   show: false
        // },
        // labels: {
        //   style: {
        //     colors: "#aaa"
        //   }
        // }
        min: 0,
        max: 8000,
      },
    }
  },
  colors: ["#FF0080"],
  stroke: {
    width: 2
  },
  grid: {
    borderColor: "#444"
  },
  markers: {
    size: 0
  },
  xaxis: {
    type: "datetime",
    tooltip: {
      enabled: false
    }
  },
  yaxis: {
    tickAmount: 2
  }
});

const data = ref();
const days = ref(1);
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
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { currentSeries, powerSeries } = processAggregatedData(data.value, props.tab);
    series.value = [
      // {
      //   name: 'Current',
      //   data: currentSeries,
      // },
      {
        name: 'Battery Power',
        data: powerSeries,
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
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { currentSeries, powerSeries } = processAggregatedData(data.value, newTab);

    series.value = [
      // {
      //   name: 'Current',
      //   data: currentSeries,
      // },
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

.apexcharts-tooltip {
  background: #1e1f26;
  color: white;
}
</style>
