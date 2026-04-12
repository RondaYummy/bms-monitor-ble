<template>
  <q-page class="column items-center justify-evenly q-pt-lg q-pr-lg q-pl-lg"
    v-if="!calculatedList && !deyeData && !devicesList?.length">
    <LoaderComponent />
  </q-page>

  <q-page v-else class="column items-center justify-evenly q-pa-lg">
    <template v-if="deyeData">
      <h6>
        Deye
        <q-tooltip> Блок даних з інвертора </q-tooltip>
      </h6>
      <div class="row justify-between full-width">
        <div class="column">
          <SemiCircleGauge :value="deyeData?.total_pv || 0" :image="'/inverter/solar_panel_yellow_200x200.png'"
            :tooltip="`Потужність, яку генерують сонячні панелі ( разом ) | 1 MPPT вхід (PV): ${deyeData?.pv1_power} | 2 MPPT вхід (PV): ${deyeData?.pv2_power}`" />

          <SemiCircleGauge :value="-(deyeData?.battery_power || 0)" :image="'/inverter/battery_yellow_200x200.png'"
            :tooltip="'Потужність заряду/розряду акумулятора'"
            :additional-value="`${deyeData?.battery_voltage?.toFixed(2)}ᵛ`" />
        </div>

        <div class="column">
          <SemiCircleGauge :value="-(deyeData?.grid_power || 0)"
            :image="'/inverter/transmission_tower_yellow_200x200.png'"
            :tooltip="'Потужність, яка надходить з/до мережі'" />

          <SemiCircleGauge :value="deyeData?.load_power || 0" :image="'/inverter/house_yellow_200x200.png'"
            :tooltip="'Cпоживання електроенергії твоїм будинком або підключеними пристроями.'" />
        </div>
      </div>

      <q-btn @click="showMoreDeye = !showMoreDeye" label="↓ Show more ↓" class="q-mb-sm full-width" size="md"
        unelevated />

      <template v-if="showMoreDeye">
        <AddtionalInfo :data="deyeData" />
      </template>
    </template>

    <PowerSolarMinitor />

    <template v-if="topTapoDevices?.length">
      <h6>
        TP-Link Tapo
        <q-tooltip> Блок пристроїв з найбільшим приоритетом TP-Link Tapo. </q-tooltip>
      </h6>

      <div ref="scrollContainer" @wheel.prevent="handleScroll"
        class="row justify-between full-width q-pt-sm q-mb-sm top-tapo-row no-wrap">
        <TopTapoDevice :item="item" v-for="item of topTapoDevices" :key="item?.ip" />
      </div>
    </template>

    <template v-if="devicesList">
      <h6>
        JK-BMS
        <q-tooltip> Блок даних з BMS </q-tooltip>
      </h6>

      <div class="column gap-10 full-width q-mt-sm">
        <div class="indicate indicate-charge" :class="{
          green: deyeData?.total_pv > deyeData?.load_power,
          white: deyeData?.total_pv === deyeData?.load_power,
          red: deyeData?.load_power > deyeData?.total_pv,
        }">
          <q-tooltip> Індикатор зарядки/розрядки відносно споживання </q-tooltip>
        </div>
        <div class="indicate indicate-grid" :class="{
          orange: deyeData?.grid_power > 0,
          white: deyeData?.grid_power <= 0,
        }">
          <q-tooltip> Індикатор використання потужностей з мережі </q-tooltip>
        </div>

        <div class="indicate indicate-info q-gutter-xs">
          <q-icon @click="showSslDialog = true" name="security" size="34px"
            :color="sslData.status === 'danger' ? 'red' : 'white'" />
          <q-icon @click="showPowerSystemDialog = true" name="power_off" size="34px"
            :color="powerSystemData?.devices?.length ? 'red' : 'white'" />
          <q-icon @click="showInfo = true" name="info" size="32px" color="white" />
        </div>

        <q-dialog v-model="showSslDialog" class="ssl-dialog">
          <q-card dark>
            <q-card-section>
              <SslData :data=sslData />
            </q-card-section>

            <q-card-actions align="right">
              <q-btn flat label="GitHub" :disable="!token"
                href="https://github.com/RondaYummy/bms-monitor-ble/blob/main/SSL_CERTIFICATE.md" color="primary" />

              <q-btn flat label="Поновити" :disable="!token" color="black">
                <q-popup-proxy>
                  <q-banner class="q-pa-md">
                    <template v-slot:avatar>
                      <q-icon name="lock" color="black" />
                    </template>
                    <q-btn label="Сертифікат поновлено" color="black" @click="refreshSsl" v-close-popup />
                  </q-banner>
                </q-popup-proxy>
              </q-btn>

              <q-btn flat label="OK" color="primary" v-close-popup />
            </q-card-actions>
          </q-card>
        </q-dialog>

        <q-dialog v-model="showPowerSystemDialog">
          <q-card dark>
            <q-card-section>
              <PowerData :data=powerSystemData />
            </q-card-section>

            <q-card-actions align="right">
              <q-btn flat label="OK" color="primary" v-close-popup />
            </q-card-actions>
          </q-card>
        </q-dialog>

        <q-dialog v-model="showInfo">
          <q-card dark>
            <q-card-section>
              <div class="tooltip-content">
                <strong>🔋 Система моніторингу JK-BMS, інвертора Deye та розумних розеток Tapo</strong>
                <p>
                  Додаток дозволяє моніторити усю енергосистему в реальному часі. Він підключається
                  до:
                </p>
                <ul>
                  <li><strong>JK-BMS</strong> — через Bluetooth (<code>bleak</code>)</li>
                  <li><strong>Deye</strong> — через WiFi-стік (<code>pysolarmanv5</code>)</li>
                  <li><strong>TP-Link Tapo</strong> — через WiFi-стік (<code>PyP110</code>)</li>
                </ul>
                <p>
                  <strong>Зчитуються ключові параметри:</strong><br />
                  Напруга, струм, SOC, SOH, температури, потужність, баланс комірок, генерація з
                  панелей, споживання будинку.
                </p>
                <p>
                  ⚠️ <strong>Критичні події</strong> (наприклад, перегрів, дисбаланс, низький заряд)
                  надсилаються як <strong>Web Push-сповіщення</strong> у PWA-додаток.
                </p>
                <p>
                  🔌 <strong>Динамічне скидання навантаження:</strong> автоматичне балансування потужності для
                  запобігання перевантаженню інвертора шляхом перемикання розумних розеток Tapo та повідомлення про
                  кількість відключених пристроїв.
                </p>
                <p>
                  📱 Фронтенд — <strong>PWA-додаток</strong>, підтримує мобільні
                  пристрої та браузерні повідомлення.
                </p>
                <p>
                  🚀 Працює автономно на <strong>Raspberry Pi 5</strong>, без хмарних залежностей.
                </p>
                <p>
                  <em>Набагато зручніше, ніж офіційні додатки: усі дані — в одному місці, з
                    будь-якого пристрою.</em>
                </p>
              </div>

              <p>
                GitHub:
                <a href="https://github.com/RondaYummy/bms-monitor-ble" target="_blank">bms-monitor-ble</a>
              </p>
            </q-card-section>

            <q-card-actions align="right">
              <q-btn flat label="OK" color="primary" v-close-popup />
            </q-card-actions>
          </q-card>
        </q-dialog>

        <div class="row justify-between">
          <h3 :class="{ 'blink-attention': calculatedList?.battery_voltage < 42 }">
            {{ calculatedList?.battery_voltage?.toFixed(2) || 0.00 }}
            <sup>V</sup>

            <q-tooltip>
              Це загальна напруга батареї, яка вимірюється як сума напруги всіх елементів (комірок),
              з'єднаних послідовно.
            </q-tooltip>
          </h3>

          <h3 :class="{
            unique: calculatedList?.charge_current < 0,
            charge: calculatedList?.charge_current > 0,
          }">
            {{ calculatedList?.charge_current?.toFixed(2) || 0.00 }}
            <sup>A</sup>

            <q-tooltip>
              Струм заряду, якщо число додатнє, йде заряджання а якщо відємне - розряжання.
            </q-tooltip>
          </h3>
        </div>

        <div class="row justify-between">
          <h4 class="text-white">
            {{ calculatedList?.nominal_capacity?.toFixed(2) || 0.00 }}
            <sup>Ah</sup>

            <q-tooltip> Загальна ємність батареї. Виміряється в Ah. </q-tooltip>
          </h4>

          <h4 class="unique">
            {{ calculatedList?.remaining_capacity?.toFixed(2) || 0.00 }}
            <sup>Ah</sup>

            <q-tooltip>
              Це значення вказує на залишкову ємність батареї. Зазвичай воно обчислюється у
              міліампер-годинах (mAh) або ампер-годинах (Ah).
            </q-tooltip>
          </h4>
        </div>

        <div class="row justify-between">
          <span :class="{
            'blink-attention': calculatedList?.voltage_difference >= 0.1,
            coral:
              calculatedList?.voltage_difference >= 0.05 && calculatedList?.voltage_difference < 40,
          }">
            ⚖️ C-Delta: {{ calculatedList?.voltage_difference?.toFixed(3) || 0.000 }}
            <sup>V</sup>

            <q-tooltip>
              Cell Delta — це індикатор здоров'я та збалансованості батарейного модуля. Чим менше
              значення, тим краще. Якщо воно занадто високе, необхідно діагностувати причини та
              забезпечити вирівнювання напруги між комірками.
            </q-tooltip>
          </span>

          <span :class="{ 'blink-attention': calculatedList?.average_voltage < 3.0 }">
            📊 C-avg: {{ calculatedList?.average_voltage?.toFixed(2) || 0.00 }}
            <sup>V</sup>

            <q-tooltip>
              Це середнє значення напруги всіх комірок (ячейок) батареї, які мають ненульову
              напругу.
            </q-tooltip>
          </span>
        </div>

        <div class="row justify-between">
          <span :class="{ unique: calculatedList?.battery_power > 6000 }">
            ⚡ Power: {{ calculatedList?.battery_power?.toFixed(2) || 0.00 }}
            <sup>W</sup>

            <q-tooltip>
              Battery Power — Це потужність, яку батарея видає в даний момент. Обчислюється як
              добуток напруги та струму (W).
            </q-tooltip>
          </span>

          <span :class="{ 'blink-attention': calculatedList?.state_of_charge < 20 }">
            🔄 Balance: {{ calculatedList?.state_of_charge?.toFixed(1) || 0.0 }}
            <sup>%</sup>
          </span>
        </div>

        <div class="row justify-between">
          <span>
            📦 Cap.:
            {{
              (
                (calculatedList?.battery_voltage * calculatedList?.nominal_capacity) /
                1000
              )?.toFixed(2) || 0.00
            }}
            <sup>kWh</sup>

            <q-tooltip> Capacity - Це загальний обсяг ємності батареї в кВт⋅год. </q-tooltip>
          </span>

          <span>
            🪫 Cap. left:
            {{
              (
                (calculatedList?.battery_voltage * calculatedList?.remaining_capacity) /
                1000
              )?.toFixed(2) || 0.00
            }}
            <sup>kWh</sup>

            <q-tooltip> Capacity left - Це обсяг ємності батареї який залишився в кВт⋅год. </q-tooltip>
          </span>
        </div>

        <div class="row justify-between">
          <span>
            🔁 Cycle Cap.:
            {{ Math.round(calculatedList?.total_cycle_capacity) || 0 }}
            <sup>Ah</sup>

            <q-tooltip>
              Total Cycle Capacity - Це загальний обсяг енергії, яку батарея віддала протягом всіх
              циклів свого використання. Зниження цього показника (відносно номінальної ємності)
              може свідчити про деградацію батареї.
            </q-tooltip>
          </span>

          <span>
            🔂 Cycle C: {{ calculatedList?.cycle_count || 0 }}

            <q-tooltip>
              Cycle count - Один цикл визначається як повний процес розряджання батареї (до певного
              рівня) і заряджання до повного заряду.
            </q-tooltip>
          </span>
        </div>

        <div class="row justify-between">
          <span :class="{ 'blink-attention': calculatedList?.state_of_health < 50 }">
            ❤️‍🩹 SOH: {{ calculatedList?.state_of_health || 0 }}
            <sup>%</sup>

            <q-tooltip>
              State of Health (SOH) — це показник загального стану батареї, який використовується
              для оцінки її залишкового ресурсу та ефективності порівняно з початковим (новим)
              станом. Вимірюється у відсотках (%).
            </q-tooltip>
          </span>

          <span v-if="calculatedList?.charge_current < 0" :class="{ 'blink-attention': autonomyTime <= 120 }">
            ⏳ Autonomy:
            {{ formatMinutes(autonomyTime) }}

            <q-tooltip>
              Autonomy - Час автономної роботи при поточних навантаженнях. Також враховується
              ефективність інвертора в коефіцієнті 0.95. Показується в годинах.
            </q-tooltip>
          </span>

          <span v-else>
            ⏱ Time left:
            {{
              calculateChargeTime(
                (calculatedList?.battery_voltage * calculatedList?.nominal_capacity) /
                1000,
                (calculatedList?.battery_voltage * calculatedList?.remaining_capacity) / 1000,
                -(deyeData?.battery_power || 0),
              ) || 0.00
            }}

            <q-tooltip>
              Charging time left - Час, який необхідний до повної зарядки акумуляторів.
            </q-tooltip>
          </span>
        </div>
      </div>
    </template>

    <q-dialog v-model="installAppDialog" position="bottom">
      <q-card style="width: 350px">
        <q-linear-progress :value="1" color="pink" />

        <q-card-section class="column justify-center items-center no-wrap">
          <h6 class="text-center text-dark">📱 Встановіть наш додаток на свій пристрій! 🚀</h6>
          <p class="text-center q-mt-sm text-dark">
            Наш сайт підтримує <b>Progressive Web App (PWA)</b> – це означає, що ви можете
            встановити його як додаток на свій смартфон чи комп’ютер.
          </p>
          <q-btn class="q-mt-sm" @click="installApp" color="black" label="Встановити як додаток" />
          <q-btn class="q-mt-sm" @click="skipInstallApp" color="black" label="Не встановлювати" />
        </q-card-section>
      </q-card>
    </q-dialog>

    <BMSChart :tab="tab" />

    <q-expansion-item v-model="isCellVoltagesOpen" switch-toggle-side expand-separator label="Cell Voltages">
      <template v-slot:header>
        <h6>🔋 Cell Voltages</h6>
      </template>

      <div v-if="isCellVoltagesOpen" class="column items-center q-mt-md">
        <div class="row justify-between">
          <div class="row items-center" v-for="(d, idx) of calculatedList?.cell_voltages" :key="`cv_${idx}`">
            <q-chip dense outline color="primary" text-color="white">{{
              String(idx + 1).padStart(2, '0')
            }}</q-chip>
            <span> - {{ d?.toFixed(2) || 0.00 }} v. </span>
          </div>
        </div>
      </div>
    </q-expansion-item>

    <q-expansion-item v-model="isCellResistancesOpen" switch-toggle-side expand-separator class="fullwidth"
      icon="electrical_services" label="Cell Wire Resistance">
      <template v-slot:header>
        <h6>🧵 Cell Wire Resistance</h6>
      </template>

      <div v-if="isCellResistancesOpen" class="column items-center q-mt-md">
        <div class="row justify-between">
          <div class="row items-center" v-for="(d, idx) of calculatedList?.cell_resistances" :key="`cr_${idx}`">
            <q-chip dense outline color="primary" text-color="white">{{
              String(idx + 1).padStart(2, '0')
            }}</q-chip>
            <span> - {{ d?.toFixed(2) || 0.00 }} v. </span>
          </div>
        </div>
      </div>
    </q-expansion-item>

    <q-tabs v-model="tab" @update:model-value="selectSingleDevice" dense inline-label outside-arrows mobile-arrows
      align="justify" class="q-mt-sm text-white shadow-2 bg-dark full-width" v-if="devicesList">
      <q-tab name="All" style="flex: 1 1 50%" label="All" />

      <q-btn-dropdown auto-close stretch flat style="flex: 1 1 50%" label="Devices">
        <q-list>
          <q-item clickable v-for="device of Object.keys(devicesList)?.sort()?.reverse()" class="text-black"
            :key="device" :name="device" :label="device" @click="tab = device">
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
import PowerData from '../components/power/PowerData.vue'
import {
  calculateAutonomyTime,
  calculateAveragePerIndex,
  calculateChargeTime,
  formatMinutes,
  isInstalled,
  useSessionStorage,
} from '../helpers/utils';
import { ref, watch, onBeforeUnmount, computed, onMounted } from 'vue';
import type { BeforeInstallPromptEvent, CellInfo, DeyeSafeValues } from '../models';
import { useBmsStore } from 'src/stores/bms';
import { useDeyeStore } from 'src/stores/deye';
import SemiCircleGauge from 'src/components/SemiCircleGauge.vue';
import { useTapoStore } from 'src/stores/tapo';
import AddtionalInfo from 'src/components/deye/AddtionalInfo.vue';
import { usePowerStore } from 'src/stores/power';
import SslData from 'src/components/SslData.vue';
import { useConfigStore } from 'src/stores/config';
import TopTapoDevice from 'src/components/tapo/TopTapoDevice.vue';
import PowerSolarMinitor from 'src/components/power/PowerSolarMinitor.vue';
import { Notify } from 'quasar';

const bmsStore = useBmsStore();
const deyeStore = useDeyeStore();
const tapoStore = useTapoStore();
const powerStore = usePowerStore();
const configStore = useConfigStore();
const token = useSessionStorage('access_token');

configStore.fetchSsl();

const skipInstall = localStorage.getItem('skip-install');

const sslData = computed(configStore.getSsl);
const devicesList = computed<Record<string, CellInfo>>(bmsStore.getCellInfo);
const topTapoDevices = computed(() => tapoStore.topDevices);
const powerSystemData = computed(powerStore.getPowerData);
const deyeData = computed<DeyeSafeValues>(() => {
  const data = deyeStore.getDeyeData();
  const initial: DeyeSafeValues = {
    pv1_power: 0,
    pv2_power: 0,
    total_pv: 0,
    load_power: 0,
    grid_power: 0,
    battery_power: 0,
    battery_voltage: 0,
    battery_soc: 0,
    net_balance: 0,
    stat_daily_pv: 0,
    stat_total_pv: 0,
    stat_daily_bat_discharge: 0,
    stat_daily_grid_in: 0,
    stat_daily_grid_out: 0,
    stat_total_grid_out: 0,
    stat_total_load: 0,
    daily_bat_charge: 0,
    daily_load: 0,
    grid_in: 0,
    total_bat_charge: 0,
    total_bat_discharge: 0,
  };

  if (!Array.isArray(data)) return initial;
  return data.reduce((acc, curr) => {
    acc.battery_voltage += Number(curr.battery_voltage) || 0;
    acc.pv1_power += Number(curr.pv1_power) || 0;
    acc.pv2_power += Number(curr.pv2_power) || 0;
    acc.total_pv += Number(curr.total_pv) || 0;
    acc.load_power += Number(curr.load_power) || 0;
    acc.grid_power += Number(curr.grid_power) || 0;
    acc.battery_power += Number(curr.battery_power) || 0;
    acc.battery_soc += Number(curr.battery_soc) || 0;
    acc.net_balance += Number(curr.net_balance) || 0;
    acc.stat_daily_pv += Number(curr.stat_daily_pv) || 0;
    acc.stat_total_pv += Number(curr.stat_total_pv) || 0;
    acc.stat_daily_bat_discharge += Number(curr.stat_daily_bat_discharge) || 0;
    acc.stat_daily_grid_in += Number(curr.stat_daily_grid_in) || 0;
    acc.stat_daily_grid_out += Number(curr.stat_daily_grid_out) || 0;
    acc.stat_total_grid_out += Number(curr.stat_total_grid_out) || 0;
    acc.stat_total_load += Number(curr.stat_total_load) || 0;
    return acc;
  }, initial);
});

const intervalId = ref();
const isFetching = ref(false);
const scrollContainer = ref<HTMLElement | null>(null);
const installAppDialog = ref<boolean>(false);
const calculatedList = ref<any>();
const showInfo = ref(false);
const showPowerSystemDialog = ref(false);
const showSslDialog = ref(false);
const tab = ref<string>('All');
const isCellVoltagesOpen = ref(false);
const isCellResistancesOpen = ref(false);
const showMoreDeye = ref(false);

const autonomyTime = computed(() => calculateAutonomyTime(
  calculatedList.value?.remaining_capacity,
  calculatedList.value?.charge_current,
  0.95
) || 0.00);

let deferredPrompt: BeforeInstallPromptEvent;

window.addEventListener('beforeinstallprompt', (event: Event) => {
  // event.preventDefault(); // Prevent the dialog from showing automatically
  deferredPrompt = event as BeforeInstallPromptEvent;
});

watch(devicesList, () => {
  selectSingleDevice(tab.value);
});

const yieldToBrowser = () => new Promise(resolve => setTimeout(resolve, 0));

async function refreshSsl() {
  try {
    await configStore.refreshSsl();
    Notify.create({
      message: 'Термін дії SSL сертифікату скинуто',
      color: 'secondary',
      position: 'top',
    });
  } catch (error) {
    console.error(error);
    Notify.create({
      message: 'Сталася помилка під час скидання терміну дії SSL сертифікату',
      color: 'red',
      icon: 'warning',
      position: 'top',
      timeout: 2000,
    });
  }
}

async function calculateData() {
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

  if (!values?.length) return;

  let sumBatteryVoltage = 0;
  let sumAverageVoltage = 0;
  let sumStateOfCharge = 0;
  let sumStateOfHealth = 0;
  let sumVoltageDifference = 0;

  let hasCharging = false;
  let hasDischarging = false;

  const allCellVoltages = [];
  const allCellResistances = [];

  const valuesLength = values.length;

  for (let i = 0; i < valuesLength; i++) {
    const v = values[i];
    if (!v) {
      continue;
    }

    calculatedList.value.remaining_capacity += v.remaining_capacity || 0;
    calculatedList.value.nominal_capacity += v.nominal_capacity || 0;
    calculatedList.value.charge_current += v.charge_current || 0;
    calculatedList.value.battery_power += v.battery_power || 0;
    calculatedList.value.total_cycle_capacity += v.total_cycle_capacity || 0;
    calculatedList.value.cycle_count += v.cycle_count || 0;

    sumBatteryVoltage += v.battery_voltage || 0;
    sumAverageVoltage += v.average_voltage || 0;
    sumStateOfCharge += v.state_of_charge || 0;
    sumStateOfHealth += v.state_of_health || 0;
    sumVoltageDifference += v.voltage_difference || 0;

    if (!hasCharging && v.charging_status === 1) hasCharging = true;
    if (!hasDischarging && v.discharging_status === 1) hasDischarging = true;

    if (v.cell_voltages) allCellVoltages.push(v.cell_voltages);
    if (v.cell_resistances) allCellResistances.push(v.cell_resistances);
  }

  calculatedList.value.battery_voltage = sumBatteryVoltage / valuesLength;
  calculatedList.value.average_voltage = sumAverageVoltage / valuesLength;
  calculatedList.value.state_of_charge = sumStateOfCharge / valuesLength;
  calculatedList.value.state_of_health = sumStateOfHealth / valuesLength;
  calculatedList.value.voltage_difference = sumVoltageDifference / valuesLength;

  calculatedList.value.charging_status = hasCharging ? 1 : 0;
  calculatedList.value.discharging_status = hasDischarging ? 1 : 0;

  if (allCellVoltages.length > 0) {
    await yieldToBrowser();
    calculatedList.value.cell_voltages = calculateAveragePerIndex(allCellVoltages);
    calculatedList.value.cell_resistances = calculateAveragePerIndex(allCellResistances);
  }
}

function handleScroll(e: WheelEvent) {
  if (!scrollContainer.value) return;
  scrollContainer.value.scrollLeft += e.deltaY;
};

function installApp() {
  deferredPrompt.prompt();
}

function skipInstallApp() {
  localStorage.setItem('skip-install', 'true');
  installAppDialog.value = false;
}

function selectSingleDevice(tab: string) {
  if (tab === 'All') {
    calculateData();
  } else {
    calculatedList.value = devicesList.value[tab];
  }
}

if (!isInstalled() && skipInstall !== 'true') {
  installAppDialog.value = true;
}

const intervalFunction = async () => {
  if (isFetching.value) return;
  isFetching.value = true;
  try {
    await Promise.allSettled([
      bmsStore.fetchCellInfo(),
      deyeStore.fetchDeyeDevices(),
      tapoStore.getTopDevices(),
      powerStore.fetchPowerData(),
    ]);
  } finally {
    isFetching.value = false;
  }
};

onMounted(() => {
  intervalFunction();
  intervalId.value = setInterval(intervalFunction, 2000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});
</script>

<style scoped lang="scss">
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

.ssl-dialog .q-card__section.q-card__section--vert {
  padding: 0 !important;
}

.top-tapo-row {
  gap: 10px;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
}
</style>
