<template>
  <div class="gauge-wrapper">
    <apexchart type="radialBar" height="250" :options="chartOptions" :series="[percentage]" />
    <div class="center-content">
      <img :src="image" alt="inverter" class="inverter-image" />
      <div class="value-text2" v-if="additionalValue">
        {{ additionalValue }}
      </div>
      <div class="value-text">
        {{ kilowatts }} kW
      </div>
      <q-tooltip v-if="tooltip">
        {{ tooltip }}
      </q-tooltip>
    </div>
    <div class="labels">
      <span class="left-label">
        0
        <q-tooltip>
          Мінімальне значення
        </q-tooltip>
      </span>
      <span class="right-label">
        7
        <q-tooltip>
          Максимальне значення
        </q-tooltip>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ value: number; image: string; tooltip?: string; additionalValue?: string; max?: number }>()
const max = props.max ?? 7000

const kilowatts = computed(() => (props.value / 1000).toFixed(1))
const percentage = computed(() => (props.value / max * 100))

const getColor = (val: number) => {
  if (val < 85) return '#B6FF00'       // до 85% — зелений
  // if (val < 90) return '#FF00D7'       // до 90% — фіолетовий
  return '#FF0004'                     // вище — червоний
}

const chartOptions = computed(() => ({
  chart: {
    type: 'radialBar',
    offsetY: -20,
    sparkline: { enabled: true }
  },
  plotOptions: {
    radialBar: {
      startAngle: -90,
      endAngle: 90,
      track: {
        background: "#e7e7e7",
        strokeWidth: '97%',
        margin: 5,
        dropShadow: {
          enabled: true,
          top: 2,
          left: 0,
          color: '#444',
          opacity: 1,
          blur: 2
        }
      },
      dataLabels: {
        name: { show: false },
        value: { show: false }
      }
    }
  },
  fill: {
    type: 'solid',
    colors: [getColor(percentage.value)]
  },
  stroke: {
    lineCap: 'butt'
  },
  labels: ['Power']
}))
</script>

<style scoped lang="scss">
.gauge-wrapper {
  position: relative;
  width: 100%;
  max-width: 225px;
  margin: 0 auto;
  margin-bottom: 10px;

  @media screen and (max-width: 500px) {
    max-width: 200px;
  }

  @media screen and (max-width: 448px) {
    max-width: 160px;
  }

  @media screen and (max-width: 368px) {
    max-width: 130px;
    margin-bottom: 20px;
  }
}

.center-content {
  position: absolute;
  top: 65%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.inverter-image {
  width: 50px;
  height: auto;
  margin-bottom: 4px;
  filter: brightness(0) invert(1);
}

.value-text {
  font-size: 16px;
  font-weight: 600;
  color: white;
  margin-top: -7px;
}

.value-text2 {
  font-size: 16px;
  font-weight: 600;
  margin-top: -24px;
}

.labels {
  position: absolute;
  width: 100%;
  top: 79%;
  display: flex;
  justify-content: space-between;
  padding: 0 16%;
  font-size: 12px;
  color: #666;

  @media screen and (max-width: 368px) {
    top: 68%;
    padding: 0 15%;
  }

  .left-label {
    color: #B6FF00;
  }

  .right-label {
    color: #FF0004;
  }
}
</style>