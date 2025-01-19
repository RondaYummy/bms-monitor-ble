<template>
  <q-page class="column items-center justify-evenly">
    <template v-if='devicesList'>
      <div class='row q-gutter-sm'>
        <h3>
          {{ calculatedList?.average_voltage?.toFixed(2) }}
          <sup>V</sup>
        </h3>
        <h3 class='unique'>
          {{ calculatedList?.remaining_capacity?.toFixed(2) }}
          <sup>Ah</sup>
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
    values.forEach((v) => {
      calculatedList.value.average_voltage += v.average_voltage || 0;
      calculatedList.value.remaining_capacity += v.remaining_capacity || 0;
    });
  }
  console.log(calculatedList.value);

  // const g = {
  //   "Andrii 1": {
  //     "voltage_difference": 0.006000000000000227,
  //     "average_voltage": 3.961166666666667,
  //     "cell_voltages": [
  //       3.956,
  //       3.9610000000000003,
  //       3.962,
  //       3.962,
  //       3.962,
  //       3.962,
  //       3.962,
  //       3.962,
  //       3.9610000000000003,
  //       3.962,
  //       3.962,
  //       3.96
  //     ],
  //     "power_tube_temperature": 0,
  //     "battery_voltage": 0,
  //     "battery_power": 0,
  //     "charge_current": 0,
  //     "temperature_sensor_1": 0,
  //     "temperature_sensor_2": 0,
  //     "state_of_charge": 0,
  //     "remaining_capacity": 8912.896,
  //     "nominal_capacity": 0,
  //     "cycle_count": 47537,
  //     "state_of_health": 199;
  //   }
  // };
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
