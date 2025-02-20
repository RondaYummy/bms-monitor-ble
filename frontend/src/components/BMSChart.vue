<template>
  <div class="chart-container">
    <div class="chart-header">
      <h3>BMS Data</h3>
      <div class="chart-actions">
        <q-btn id="one_day"
               label="1Д"
               flat
               @click="zoomRange('1d')" />
        <q-btn id="one_week"
               label="1Т"
               flat
               @click="zoomRange('1w')" />
        <q-btn id="one_month"
               label="1М"
               flat
               @click="zoomRange('1m')" />
        <q-btn id="one_year"
               label="1Р"
               flat
               @click="zoomRange('1y')" />
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

const chartOptions = ref({
  chart: {
    id: 'bms-data-chart',
    type: "area",
    background: "#1e1f26",
    zoom: {
      enabled: false
    },
    animations: {
      enabled: true,
      easing: "linear",
      dynamicAnimation: {
        speed: 1000
      }
    },
    dropShadow: {
      enabled: true,
      opacity: 0.3,
      blur: 5,
      left: -7,
      top: 7
    },
  },
  stroke: {
    curve: "smooth",
    width: 3,
  },
  grid: {
    borderColor: "#222226",
    padding: {
      left: 0,
      right: 0,
    },
  },
  markers: {
    colors: ["#FFFFFF"]
  },
  dataLabels: {
    enabled: false
  },
  legend: {
    show: false,
  },
  xaxis: {
    type: 'datetime',
    axisBorder: {
      show: true,
      color: "#222226"
    },
    axisTicks: {
      show: true,
      color: "#555",
      height: 6,
    },
    tickAmount: 6,
    labels: {
      style: {
        colors: "#aaa"
      },
      formatter: function (value: string | number) {
        const date = new Date(value);
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - offset * 60 * 1000);
        return `${localDate.toISOString().slice(11, 16)}`;
      }
    }
  },
  title: {
    text: 'BMS Data',
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
    y: [{
      formatter: (val: number) => `${val?.toFixed(2)} W`,
    }, {
      formatter: (val: number) => `${val?.toFixed(2)} A`,
    }],
    x: {
      formatter: (value: string) => {
        const date = new Date(value);
        return `${date.toLocaleDateString('en-GB', {
          day: '2-digit',
          month: 'short',
          year: 'numeric'
        })} ${date.toLocaleTimeString('en-GB', {
          hour: '2-digit',
          minute: '2-digit'
        })}`;
      }
    },
  },
  // colors: ['#FF4560', '#008FFB', '#F2C037'],
});

const series = ref<SeriesData[]>([]);
const data = ref();
const days = ref(1);
const intervalId = ref();

function zoomRange(range: '1d' | '1w' | '1m' | '1y' | 'all') {
  if (!chartRef.value) return;

  const chart = chartRef.value?.chart;
  const now = new Date().getTime();

  let from, to;
  switch (range) {
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
    case 'all': // Усі дані – встановити діапазон за даними графіка
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

  chart.zoomX(from, to);
}

async function fetchAggregatedData(days: number = 1): Promise<any[]> {
  try {
    const response: any = await fetch(`/api/aggregated-data?days=${days}`);
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
    console.log('WATCH');
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
});
</script>

<style scoped lang='scss'>
.chart-container {
  width: 100%;
}

.apexcharts-tooltip,
.apexcharts-menu {
  background: #1e1f26;
  color: white;
}
</style>
