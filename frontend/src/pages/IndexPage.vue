<template>
  <q-page class="column items-center justify-evenly q-pt-lg q-pr-lg q-pl-lg"
          v-if="!calculatedList">
    <LoaderComponent />
  </q-page>
  <q-page v-else
          class="column items-center justify-evenly q-pa-lg">
    <template v-if='devicesList'>
      <div class='column gap-10 full-width q-mt-sm'>
        <div class='indicate indicate-charge'
             :class="{ green: calculatedList?.charging_status === 1, orange: calculatedList?.charging_status !== 1 }">
        </div>
        <div class='indicate indicate-discharge'
             :class="{ red: calculatedList?.discharging_status === 1, orange: calculatedList?.discharging_status !== 1 }">
        </div>
        <div class='row justify-between'>
          <h3>
            {{ calculatedList?.battery_voltage?.toFixed(2) }}
            <sup>V</sup>

            <q-tooltip>
              Це загальна напруга батареї, яка вимірюється як сума напруги всіх
              елементів (комірок), з'єднаних послідовно.
            </q-tooltip>
          </h3>
          <h3
              :class="{ unique: calculatedList?.charge_current < 0, charge: calculatedList?.charge_current > 0 }">
            {{ calculatedList?.charge_current?.toFixed(2) }}
            <sup>A</sup>

            <q-tooltip>
              Струм заряду, якщо число додатнє, йде заряджання а якщо
              відємне
              -
              розряжання.
            </q-tooltip>
          </h3>
        </div>

        <div class='row justify-between'>
          <h4 class='text-white'>
            {{ calculatedList?.nominal_capacity?.toFixed(2) }}
            <sup>Ah</sup>

            <q-tooltip>
              Загальна ємність батареї. Виміряється в Ah.
            </q-tooltip>
          </h4>

          <h4 class='unique'>
            {{ calculatedList?.remaining_capacity?.toFixed(2) }}
            <sup>Ah</sup>

            <q-tooltip>
              Це значення вказує на залишкову ємність батареї. Зазвичай воно
              обчислюється у міліампер-годинах (mAh) або ампер-годинах (Ah).
            </q-tooltip>
          </h4>
        </div>

        <div class='row justify-between'>
          <span
                :class="{ unique: calculatedList?.voltage_difference >= 40, coral: calculatedList?.voltage_difference >= 20 && calculatedList?.voltage_difference < 40 }">
            Cell delta: {{ calculatedList?.voltage_difference?.toFixed(3) }}
            <sup>V</sup>

            <q-tooltip>
              Cell Delta — це індикатор здоров'я та збалансованості
              батарейного
              модуля. Чим менше значення, тим краще. Якщо воно занадто
              високе,
              необхідно діагностувати причини та забезпечити вирівнювання
              напруги між комірками.
            </q-tooltip>
          </span>
          <span>
            Cell average: {{ calculatedList?.average_voltage?.toFixed(2) }}
            <sup>V</sup>

            <q-tooltip>
              Це середнє значення напруги всіх комірок (ячейок) батареї, які
              мають
              ненульову напругу.
            </q-tooltip>
          </span>
        </div>

        <div class='row justify-between'>
          <span :class="{ unique: calculatedList?.battery_power > 6000 }">
            Power: {{ calculatedList?.battery_power?.toFixed(2) }}
            <sup>W</sup>

            <q-tooltip>
              Battery Power — Це потужність, яку батарея видає в даний момент.
              Обчислюється як добуток напруги та струму (W).
            </q-tooltip>
          </span>

          <span>Balance:
            {{ calculatedList?.state_of_charge?.toFixed(1) }}%</span>
        </div>

        <div class='row justify-between'>
          <span>
            Capacity:
            {{ ((calculatedList?.battery_voltage * calculatedList?.nominal_capacity) / 1000)?.toFixed(2) }}
            <sup>kW</sup>

            <q-tooltip>
              Capacity - Це загальний обсяг ємності батареї в кВт.
            </q-tooltip>
          </span>

          <span>
            Capacity left:
            {{ ((calculatedList?.battery_voltage * calculatedList?.remaining_capacity) / 1000)?.toFixed(2) }}
            <sup>kW</sup>

            <q-tooltip>
              Capacity left - Це обсяг ємності батареї який залишився в кВт.
            </q-tooltip>
          </span>
        </div>

        <div class='row justify-between'>
          <span>
            Total C. C.:
            {{ calculatedList?.total_cycle_capacity?.toFixed(2) }}
            <sup>Ah</sup>

            <q-tooltip>
              CTotal Cycle Capacity - Це загальний обсяг енергії, яку батарея
              віддала протягом всіх циклів свого використання. Зниження цього
              показника (відносно номінальної ємності) може свідчити про
              деградацію батареї.
            </q-tooltip>
          </span>

          <span>
            Cycle count: {{ calculatedList?.cycle_count }}

            <q-tooltip>
              Cycle count - Один цикл визначається як повний процес розряджання
              батареї (до
              певного рівня) і заряджання до повного заряду.
            </q-tooltip>
          </span>
        </div>

        <div class='row justify-between'>
          <span :class="{ unique: calculatedList?.state_of_health < 30 }">
            SOH: {{ calculatedList?.state_of_health }}%

            <q-tooltip>
              State of Health (SOH) — це показник загального стану батареї,
              який
              використовується для оцінки її залишкового ресурсу та
              ефективності
              порівняно з початковим (новим) станом. Вимірюється у відсотках
              (%).
            </q-tooltip>
          </span>

          <span>
            Autonomy:
            {{ calculateAutonomyTime(calculatedList?.remaining_capacity, calculatedList?.charge_current, 0.95) }}

            <q-tooltip>
              Autonomy - Час автономної роботи при поточних навантаженнях. Також
              враховується ефективність інвертора в коефіцієнті 0.95.
              Показується в годинах.
            </q-tooltip>
          </span>
        </div>
      </div>
    </template>

    <q-dialog v-model="installAppDialog"
              position="bottom">
      <q-card style="width: 350px">
        <q-linear-progress :value="1"
                           color="pink" />

        <q-card-section class="column justify-center items-center no-wrap">
          <h6 class='text-center text-dark'>📱 Встановіть наш додаток на свій
            пристрій! 🚀
          </h6>
          <p class='text-center q-mt-sm text-dark'>
            Наш сайт підтримує <b>Progressive Web App (PWA)</b> – це означає, що
            ви
            можете встановити його як додаток на свій смартфон чи комп’ютер.
          </p>
          <q-btn class="q-mt-sm"
                 @click="installApp"
                 color="black"
                 label="Встановити як додаток" />
        </q-card-section>
      </q-card>
    </q-dialog>

    <BMSChart :tab="tab" />

    <q-expansion-item switch-toggle-side
                      expand-separator
                      label="Cell Voltages">
      <template v-slot:header>
        <h6>Cell Voltages</h6>
      </template>

      <div class="column items-center q-mt-md">
        <div class='row justify-between'>
          <div class='row items-center'
               v-for='(d, idx) of calculatedList?.cell_voltages'
               :key="`cv_${idx}`">
            <q-chip dense
                    outline
                    color="primary"
                    text-color="white">{{ String(idx + 1).padStart(2, '0') }}</q-chip>
            <span>
              - {{ d?.toFixed(2) }} v.
            </span>
          </div>
        </div>
      </div>
    </q-expansion-item>

    <q-expansion-item switch-toggle-side
                      expand-separator
                      class="fullwidth"
                      icon="electrical_services"
                      label="Cell Wire Resistance">
      <template v-slot:header>
        <h6>Cell Wire Resistance</h6>
      </template>

      <div class="column items-center q-mt-md">
        <div class='row justify-between'>
          <div class='row items-center'
               v-for='(d, idx) of calculatedList?.cell_resistances'
               :key="`cr_${idx}`">
            <q-chip dense
                    outline
                    color="primary"
                    text-color="white">{{ String(idx + 1).padStart(2, '0') }}</q-chip>
            <span>
              - {{ d?.toFixed(2) }} v.
            </span>
          </div>
        </div>
      </div>
    </q-expansion-item>


    <q-tabs v-model="tab"
            @update:model-value="selectSingleDevice"
            dense
            inline-label
            outside-arrows
            mobile-arrows
            align="justify"
            class="q-mt-sm text-white shadow-2 bg-dark full-width"
            v-if="devicesList">
      <q-tab name="All"
             style='flex: 1 1 50%;'
             label="All" />

      <q-btn-dropdown auto-close
                      stretch
                      flat
                      style='flex: 1 1 50%;'
                      label="Devices">
        <q-list>
          <q-item clickable
                  v-for="device of Object.keys(devicesList)?.sort()?.reverse()"
                  class="text-black"
                  :key="device"
                  :name="device"
                  :label="device"
                  @click="tab = device">
            <q-item-section>{{ device }}</q-item-section>
          </q-item>
        </q-list>
      </q-btn-dropdown>
    </q-tabs>
  </q-page>
</template>

<script setup lang="ts">
import LoaderComponent from '../components/LoaderComponent.vue';
import BMSChart from '../components/BMSChart.vue';
import { calculateAutonomyTime, calculateAverage, calculateAveragePerIndex, isInstalled } from '../helpers/utils';
import { ref, watch, onBeforeUnmount, computed } from 'vue';
import type { BeforeInstallPromptEvent, CellInfo } from '../models';
import { useBmsStore } from 'src/stores/bms';

const bmsStore = useBmsStore();

const devicesList = computed<Record<string, CellInfo>>(() => bmsStore.cellInfo);
const installAppDialog = ref(false);
const calculatedList = ref<any>();
const tab = ref('All');

let deferredPrompt: BeforeInstallPromptEvent;

window.addEventListener('beforeinstallprompt', (event: Event) => {
  // Prevent the dialog from showing automatically
  // event.preventDefault();
  deferredPrompt = event as BeforeInstallPromptEvent;
});

watch(devicesList, () => {
  selectSingleDevice(tab.value);
});

function calculateData() {
  const values = Object.values(devicesList.value);
  calculatedList.value = {
    average_voltage: 0,
    remaining_capacity: 0,
    nominal_capacity: 0,
    cell_resistances: [],
    cell_voltages: [],
    charging_status: 0,
    charge_current: 0,
    discharging_status: 0,
    voltage_difference: 0,
    state_of_charge: 0,
    state_of_health: 0,
    battery_voltage: 0,
    battery_power: 0,
    total_cycle_capacity: 0,
    cycle_count: 0,
  };

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

    calculatedList.value.discharging_status = values.some(obj => obj.discharging_status === 1) ? 1 : 0;
    calculatedList.value.charging_status = values.some(obj => obj.charging_status === 1) ? 1 : 0;
    calculatedList.value.charge_current = values.reduce((sum, obj) => sum + (obj.charge_current || 0), 0);
    calculatedList.value.battery_power = values.reduce((sum, obj) => sum + (obj.battery_power || 0), 0);
    calculatedList.value.total_cycle_capacity = values.reduce((sum, obj) => sum + (obj.total_cycle_capacity || 0), 0);
    calculatedList.value.cycle_count = values.reduce((sum, obj) => sum + (obj.cycle_count || 0), 0);
    calculatedList.value.average_voltage = calculateAverage(values, 'average_voltage');
    calculatedList.value.battery_voltage = calculateAverage(values, 'battery_voltage');
    calculatedList.value.state_of_charge = calculateAverage(values, 'state_of_charge');
    calculatedList.value.state_of_health = calculateAverage(values, 'state_of_health');
    calculatedList.value.voltage_difference = calculateAverage(values, 'voltage_difference');
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

if (!isInstalled()) {
  installAppDialog.value = true;
}
const intervalId = setInterval(async () => {
  await bmsStore.fetchCellInfo();
}, 3000);

onBeforeUnmount(() => {
  clearInterval(intervalId);
});

bmsStore.fetchCellInfo();
</script>

<style scoped lang='scss'>
:deep(.q-expansion-item) {
  width: 100%;
}

:deep(.q-menu) {
  color: black;
  font-weight: 600;
}

:deep(.q-tabs) {
  box-shadow: none;
  background: #1e1f26 !important;
}
</style>
