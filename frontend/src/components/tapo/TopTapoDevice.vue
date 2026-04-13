<template>
  <div class="top-tapo device-card">
    <div class="device-main">
      <div class="power-block">
        <span class="power-value">
          {{ item?.power_watt > 0 ? (item?.power_watt / 1000)?.toFixed(2) : '0' }}
          <sup>kW</sup>
        </span>
      </div>

      <div class="device-info">
        <span class="tapo-name">{{ item?.name || 'Unknown' }}</span>

        <div
          class="device-status-badge"
          :class="item?.device_on == 1 ? 'status-on' : 'status-off'"
        >
          <span class="status-dot"></span>
          {{ item?.device_on == 1 ? 'Enabled' : 'Disabled' }}
        </div>
      </div>

      <div class="device-action">
        <q-icon
          v-if="!changeStateTapoDevices.find((d) => d === item?.ip)"
          @click="toggleDevice(item?.device_on, item?.ip)"
          name="power_settings_new"
          class="cursor-pointer action-icon power-icon"
          :class="{ 'is-off': item?.device_on == 0, 'is-on': item?.device_on == 1 }"
          size="2.8em"
        />
        <div v-else class="loader"></div>
      </div>
    </div>

    <div class="tapo-timer">
      <div class="timer-header">
        <div class="timer-title" :class="{ 'is-active': timer }">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            class="timer-icon"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>

          <span>Timer</span>
        </div>

        <q-toggle
          :disable="!token"
          color="pink"
          v-model="timer"
          @update:model-value="toggleTimer"
        />
      </div>

      <div class="timer-select-wrap">
        <q-select
          :disable="timer || !token"
          popup-content-class="dark-select-popup"
          class="timer-select"
          outlined
          dense
          options-dense
          v-model="time"
          :options="timeOptions"
        >
          <template v-slot:selected v-if="item.timer && item.timerTimeLeft">
            <div class="full-width text-white text-center">
              {{ formatMinutes(item.timerTimeLeft) }}
              <q-tooltip :delay="200">
                Вимкнемо через <br />{{ timeLeft }}
              </q-tooltip>
            </div>
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
import { computed, ref, watch } from 'vue';

const tapoStore = useTapoStore();

const props = defineProps<{ item: TapoDevice }>();
const token = useSessionStorage('access_token');

const timeOptions = Array.from({ length: 32 }, (_, i) => {
  const totalMinutes = (i + 1) * 15;
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

const timeLeft = computed(() => {
  const time = props.item.timerTimeLeft || 0;
  if (time < 1) {
    return '< 1m';
  }
  if (time < 60) {
    return `${time}m`;
  }
  return formatMinutes(time);
});

async function toggleTimer(value: boolean) {
  if (value) {
    await tapoStore.enableTimer(props.item.ip, time.value?.value || 0);
  } else {
    await tapoStore.disableTimer(props.item.ip);
  }
}

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

watch(
  () => props.item.timer,
  (newVal) => {
    timer.value = newVal;
  }
);
</script>

<style scoped lang="scss">
.top-tapo {
  flex: 1 1 320px;
  min-width: 320px;
  display: flex;
}

.device-card {
  position: relative;
  overflow: hidden;
  width: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 20px;
  padding: 18px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.02));
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 10px 30px rgba(0, 0, 0, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(8px);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.device-card:hover {
  transform: translateY(-2px);
  box-shadow:
    0 16px 34px rgba(0, 0, 0, 0.24),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.14);
}

.device-main {
  display: grid;
  grid-template-columns: minmax(72px, auto) 1fr auto;
  align-items: center;
  gap: 14px;
  min-height: 96px;
}

.power-block {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.power-value {
  display: inline-block;
  font-size: 2rem;
  font-weight: 800;
  line-height: 1;
  color: #8ef0b5;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.power-value sup {
  font-size: 0.7rem;
  top: -0.65em;
  position: relative;
  color: rgba(142, 240, 181, 0.85);
}

.device-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
}

.tapo-name {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-clamp: 2;
  min-height: 2.8em;
  max-width: 100%;
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  line-height: 1.4;
  word-break: break-word;
}

.device-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 32px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 0.84rem;
  font-weight: 700;
  white-space: nowrap;
  max-width: 100%;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-on {
  color: #7ee2a8;
  background: rgba(46, 204, 113, 0.12);
  border: 1px solid rgba(46, 204, 113, 0.24);
}

.status-on .status-dot {
  background: #2ecc71;
  box-shadow: 0 0 10px rgba(46, 204, 113, 0.55);
}

.status-off {
  color: #d0d6dd;
  background: rgba(139, 148, 158, 0.14);
  border: 1px solid rgba(139, 148, 158, 0.24);
}

.status-off .status-dot {
  background: #8b949e;
  box-shadow: 0 0 10px rgba(139, 148, 158, 0.35);
}

.device-action {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
}

.action-icon {
  border-radius: 14px;
  padding: 6px;
  transition:
    transform 0.2s ease,
    background 0.2s ease,
    color 0.2s ease;
}

.action-icon:hover {
  transform: scale(1.06);
  background: rgba(255, 255, 255, 0.08);
}

.power-icon.is-on {
  color: #ff5f57;
}

.power-icon.is-off {
  color: rgba(255, 255, 255, 0.82);
}

.tapo-timer {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.timer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 42px;
}

.timer-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.78);
  font-weight: 700;
}

.timer-title.is-active {
  color: #ff77b7;
}

.timer-icon {
  flex-shrink: 0;
}

.timer-select-wrap {
  margin-top: 12px;
}

:deep(.timer-select) {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  min-height: 48px;
}

:deep(.timer-select .q-field__control) {
  border-radius: 14px;
  min-height: 48px !important;
  background: rgba(255, 255, 255, 0.02);
}

:deep(.timer-select .q-field__native),
:deep(.timer-select .q-field__input),
:deep(.timer-select .q-field__marginal),
:deep(.timer-select .q-select__dropdown-icon) {
  color: white;
}

:deep(.timer-select.q-field--outlined .q-field__control:before),
:deep(.timer-select.q-field--outlined .q-field__control:after) {
  border: none;
}

@media (max-width: 900px) {
  .top-tapo {
    flex: 1 1 100%;
    min-width: 100%;
  }
}

@media (max-width: 640px) {
  .device-card {
    padding: 16px;
    border-radius: 16px;
  }

  .device-main {
    grid-template-columns: 1fr;
    justify-items: center;
    text-align: center;
    min-height: unset;
  }

  .power-block,
  .device-action {
    justify-content: center;
  }

  .power-value {
    font-size: 1.8rem;
  }

  .device-info {
    width: 100%;
  }

  .timer-header {
    align-items: center;
  }
}
</style>