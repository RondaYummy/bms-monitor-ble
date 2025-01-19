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

    <q-tabs v-model="tab"
            dense
            class="bg-indigo text-white"
            v-if="devicesList">
      <q-tab v-for="device of Object.keys(devicesList)"
             :key="device"
             :name="device"
             :label="device" />
    </q-tabs>
  </q-page>
</template>

<script setup lang="ts">
import type { Device } from 'src/interfaces';
import { ref, watch } from 'vue';

const devicesList = ref<Record<string, Device>>({});
const calculatedList = ref({
  average_voltage: 0,
  remaining_capacity: 0,
  nominal_capacity: 0,
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
  const values = Object.values(devicesList.value);

  if (values?.length) {
    const numbers: number[] = [];
    values.forEach((v) => {
      numbers.push(v.average_voltage || 0);
      calculatedList.value.remaining_capacity += v.remaining_capacity || 0;
      calculatedList.value.nominal_capacity += v.nominal_capacity || 0;
    });

    calculatedList.value.average_voltage = numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
  }
});

function installApp() {
  deferredPrompt.prompt();
};


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
