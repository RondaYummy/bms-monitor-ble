<template>
  <q-page class="column items-center justify-evenly">
    <template v-if='devicesList'>
      <div class='row q-gutter-sm'>
        <h3>
          {{ calculatedList?.average_voltage?.toFixed(2) }}
          <sup>V</sup>

          <q-tooltip>
            Це середнє значення напруги всіх комірок (ячейок) батареї, які мають
            ненульову напругу.
          </q-tooltip>
        </h3>
        <h3 class='unique'>
          {{ calculatedList?.remaining_capacity?.toFixed(2) }}
          <sup>Ah</sup>

          <q-tooltip>
            Це значення вказує на залишкову ємність батареї. Зазвичай воно
            обчислюється у міліампер-годинах (mAh) або ампер-годинах (Ah).
          </q-tooltip>
        </h3>

        <h3 class='unique'>
          {{ calculatedList?.nominal_capacity?.toFixed(2) }}
          <sup>Ah</sup>

          <q-tooltip>
            Загальна ємність батареї. Виміряється в Ah.
          </q-tooltip>
        </h3>
      </div>
    </template>

    <q-btn @click="installApp"
           color="white"
           text-color="black"
           label="Install App" />

    <div class="column items-center">
      <h6>Cell Voltages:</h6>
      <div class='row justify-center q-gutter-sm q-pl-md q-pr-md'>
        <div class='row q-gutter-sm items-center'
             v-for='(d, idx) of calculatedList.cell_voltages'
             :key="`cv_${idx}`">
          <q-chip dense
                  color="primary"
                  text-color="white">{{ String(idx + 1).padStart(2, '0') }}</q-chip>
          -
          {{ d?.toFixed(2) }} v.
        </div>
      </div>
    </div>

    <div class="column items-center">
      <h6>Cell Wire Resistance:</h6>
      <div class='row justify-center q-gutter-sm q-pl-md q-pr-md'>
        <div class='row q-gutter-sm items-center'
             v-for='(d, idx) of calculatedList.cell_resistances'
             :key="`cr_${idx}`">
          <q-chip dense
                  color="primary"
                  text-color="white">{{ String(idx + 1).padStart(2, '0') }}</q-chip>
          -
          {{ d?.toFixed(2) }} v.
        </div>
      </div>
    </div>

    <q-tabs v-model="tab"
            @update:model-value="selectSingleDevice"
            dense
            class="q-mt-sm bg-indigo text-white"
            v-if="devicesList">
      <q-tab name="All"
             label="All" />
      <q-tab v-for="device of Object.keys(devicesList)"
             :key="device"
             :name="device"
             :label="device" />
    </q-tabs>
  </q-page>
</template>

<script setup lang="ts">
import { calculateAveragePerIndex } from 'src/helpers/utils';
import type { Device } from 'src/interfaces';
import { ref, watch } from 'vue';

const devicesList = ref<Record<string, Device>>({});
const calculatedList = ref<any>({
  average_voltage: 0,
  remaining_capacity: 0,
  nominal_capacity: 0,
  cell_resistances: [],
  cell_voltages: [],

});
const tab = ref();

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string; }>;
  prompt(): Promise<void>;
}

let deferredPrompt: BeforeInstallPromptEvent;

window.addEventListener('beforeinstallprompt', (event: Event) => {
  // Запобігти автоматичному показу діалогу
  // event.preventDefault();
  deferredPrompt = event as BeforeInstallPromptEvent;
});

watch(devicesList, () => {
  calculateData();
});

function calculateData() {
  const values = Object.values(devicesList.value);

  if (values?.length) {
    const numbers: number[] = [];
    const cell_voltages: number[][] = [];
    const cell_resistances: number[][] = [];

    values.forEach((v) => {
      numbers.push(v.average_voltage || 0);
      calculatedList.value.remaining_capacity += v.remaining_capacity || 0;
      calculatedList.value.nominal_capacity += v.nominal_capacity || 0;
      cell_voltages.push(v.cell_voltages);
      cell_resistances.push(v.cell_resistances);
    });

    calculatedList.value.average_voltage = numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
    calculatedList.value.cell_voltages = calculateAveragePerIndex(cell_voltages);
    calculatedList.value.cell_resistances = calculateAveragePerIndex(cell_resistances);
  }
}

function installApp() {
  deferredPrompt.prompt();
};

function selectSingleDevice(tab: string) {
  if (tab === 'All') {
    calculateData();
  } else {
    calculatedList.value = devicesList.value[tab];

  }
}

async function fetchCellInfo() {
  try {
    const response = await fetch('/api/cell-info');
    if (!response.ok) {
      throw new Error('Failed to fetch cell info');
    }
    const data = await response.json();
    console.log('Cell Info:', data);
    devicesList.value = data;
  } catch (error) {
    console.error('Error fetching cell info:', error);
  }
}
fetchCellInfo();
</script>
