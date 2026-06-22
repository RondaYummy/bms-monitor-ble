<template>
  <div class="top-tapo device-card">
    <div class="device-main">
      <div class="device-top-row">
        <div class="device-text">
          <div class="power-value">
            {{ item?.power_watt > 0 ? (item?.power_watt / 1000)?.toFixed(2) : '0' }}
            <sup>kW</sup>
          </div>

          <div class="device-name-row">
            <span class="tapo-name">{{ item?.name || 'Unknown' }}</span>

            <div
              class="device-status-badge"
              :class="item?.device_on == 1 ? 'status-on' : 'status-off'"
            >
              <span class="status-dot"></span>
              {{ item?.device_on == 1 ? 'On' : 'Off' }}
            </div>
          </div>
        </div>

        <div class="device-action">
          <q-icon
            v-if="!changeStateTapoDevices.find((d) => d === item?.ip)"
            @click="toggleDevice(item?.device_on, item?.ip)"
            name="power_settings_new"
            class="cursor-pointer action-icon power-icon"
            :class="{ 'is-off': item?.device_on == 0, 'is-on': item?.device_on == 1 }"
            size="2.3em"
          />
          <div v-else class="loader"></div>
        </div>
      </div>
    </div>

    <div class="tapo-timer">
      <div class="timer-header">
        <div class="timer-title" :class="{ 'is-active': timer }">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
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
            <div class="full-width text-white text-center timer-selected-value">
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
  width: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.07);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16);
  transition:
    border-color 0.2s ease,
    transform 0.2s ease;
}

.device-card:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.12);
}

.device-main {
  display: flex;
  flex-direction: column;
}

.device-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.device-text {
  min-width: 0;
  flex: 1 1 auto;
}

.power-value {
  font-size: 1.7rem;
  font-weight: 800;
  line-height: 1;
  color: #8ef0b5;
  letter-spacing: -0.02em;
}

.power-value sup {
  font-size: 0.68rem;
  top: -0.55em;
  position: relative;
  color: rgba(142, 240, 181, 0.8);
}

.device-name-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.tapo-name {
  min-width: 0;
  max-width: 100%;
  display: block;
  font-size: 0.96rem;
  font-weight: 700;
  color: #fff;
  line-height: 1.35;
  word-break: break-word;
}

.device-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 26px;
  padding: 0 8px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  white-space: nowrap;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-on {
  color: #7ee2a8;
  background: rgba(46, 204, 113, 0.1);
  border: 1px solid rgba(46, 204, 113, 0.2);
}

.status-on .status-dot {
  background: #2ecc71;
}

.status-off {
  color: #d0d6dd;
  background: rgba(139, 148, 158, 0.12);
  border: 1px solid rgba(139, 148, 158, 0.2);
}

.status-off .status-dot {
  background: #8b949e;
}

.device-action {
  min-width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-icon {
  border-radius: 12px;
  padding: 4px;
  transition:
    transform 0.2s ease,
    background 0.2s ease;
}

.action-icon:hover {
  transform: scale(1.04);
  background: rgba(255, 255, 255, 0.06);
}

.power-icon.is-on {
  color: #ff5f57;
}

.power-icon.is-off {
  color: rgba(255, 255, 255, 0.82);
}

.tapo-timer {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
}

.timer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  min-height: 34px;
}

.timer-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: rgba(255, 255, 255, 0.72);
  font-weight: 700;
  font-size: 0.88rem;
}

.timer-title.is-active {
  color: #ff77b7;
}

.timer-icon {
  flex-shrink: 0;
}

.timer-select-wrap {
  margin-top: 10px;
}

.timer-selected-value {
  font-size: 0.9rem;
  font-weight: 600;
}

:deep(.timer-select) {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 12px;
  min-height: 42px;
}

:deep(.timer-select .q-field__control) {
  border-radius: 12px;
  min-height: 42px !important;
  background: transparent;
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
    padding: 12px;
    border-radius: 14px;
    box-shadow: none;
    background: rgba(255, 255, 255, 0.035);
  }

  .device-top-row {
    align-items: flex-start;
  }

  .power-value {
    font-size: 1.45rem;
  }

  .tapo-name {
    font-size: 0.9rem;
  }

  .device-status-badge {
    font-size: 0.72rem;
    min-height: 24px;
    padding: 0 7px;
  }

  .action-icon {
    padding: 2px;
  }

  .tapo-timer {
    margin-top: 10px;
    padding-top: 10px;
  }

  .timer-title {
    font-size: 0.82rem;
  }

  :deep(.timer-select) {
    min-height: 40px;
    border-radius: 10px;
  }

  :deep(.timer-select .q-field__control) {
    min-height: 40px !important;
    border-radius: 10px;
  }
}
</style>