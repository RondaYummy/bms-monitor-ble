<template>
  <div class="column items-center q-pa-md rounded-borders top-tapo">
    <span class="text-light-green-12">
      {{ item?.power_watt > 0 ? (item?.power_watt / 1000)?.toFixed(2) : '0' }}
      <sup>kW</sup>
    </span>

    <span class="text-center tapo-name">{{ item?.name }}</span>
    <q-icon v-if="!changeStateTapoDevices.find((d) => d === item?.ip)" @click="toggleDevice(item?.device_on, item?.ip)"
      name="power_settings_new" class="cursor-pointer"
      :class="{ 'text-white': item?.device_on == 0, 'text-red': item?.device_on == 1 }" size="3em" />
    <div v-else class="loader"></div>

    <div class="tapo-timer">
      <div class="row justify-center items-center">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="q-mr-xs text-white" :class="{ 'text-pink': timer }">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>

        <span :class="{ 'text-pink': timer }">Timer</span>

        <q-toggle color="pink" v-model="timer" @update:model-value="toggleTimer" />

        <q-select :disable="timer" popup-content-class="dark-select-popup" class="full-width q-mt-sm"
          outlined dense options-dense v-model="time" :options="timeOptions">
          <template v-slot:selected v-if="item.timer && item.timerTimeLeft">
            <div class="full-width text-white text-center">Вимкнемо через <br/>{{ formatMinutes(item.timerTimeLeft) }}</div>
          </template>
        </q-select>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatMinutes, useSessionStorage } from 'src/helpers/utils';
import { TapoDevice } from 'src/models';
import { useTapoStore } from 'src/stores/tapo';
import { ref } from 'vue';

const tapoStore = useTapoStore();

const props = defineProps<{ item: TapoDevice }>();

const token = useSessionStorage('access_token');

const timeOptions = Array.from({ length: 32 }, (_, i) => {
  const totalMinutes = (i + 1) * 10; // Interval 10 min
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  const labelParts = [];
  if (hours > 0) labelParts.push(`${hours}h`);
  if (minutes > 0) labelParts.push(`${minutes}m`);

  return {
    label: labelParts.join(' '),
    value: totalMinutes,
  };
});

const changeStateTapoDevices = ref<Array<string>>([]);
const timer = ref(props.item.timer);
const time = ref(timeOptions[0]);

async function toggleTimer(value: boolean) {
  if (value) {
    await tapoStore.enableTimer(props.item.ip, time.value?.value || 0);
  } else {
    await tapoStore.disableTimer(props.item.ip);
  }
};

async function toggleDevice(state: number, deviceIp: string) {
  if (!token.value) return;
  changeStateTapoDevices.value.push(deviceIp);
  try {
    if (state == 1) {
      await tapoStore.disableDevice(deviceIp);
    } else {
      await tapoStore.enableDevice(deviceIp);
    }
  } catch (err) {
    console.error(err);
  } finally {
    changeStateTapoDevices.value = changeStateTapoDevices.value.filter(
      (ip: string) => ip !== deviceIp
    );
  }
}
</script>

<style scoped lang="scss">
.top-tapo {
  border: 1px solid rgb(43, 48, 59);
  flex: 1 1 48%;
  min-width: 48%;
}

.tapo-timer {
  border-top: 1px solid rgb(43, 48, 59);
  padding-top: 8px;
  margin-top: 8px;
}

:deep(.q-select) {
  background-color: rgb(17, 19, 23);
  border: 1px solid rgb(43, 48, 59);
  border-radius: 8px;
  min-height: 48px;
}

:deep(.q-field__control) {
  border-radius: 8px;
  min-height: 48px;
}

:deep(.q-select__dropdown-icon) {
  color: white;
}

.tapo-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  display: block;
}
</style>
