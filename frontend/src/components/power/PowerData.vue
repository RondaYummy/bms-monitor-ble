<template>
  <div class="text-h6 q-gutter-sm row items-center">
    <svg :class="{ 'blink-attention': props?.data?.devices?.length }" xmlns="http://www.w3.org/2000/svg" width="24"
      height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
      stroke-linejoin="round" class="lucide lucide-activity text-primary m-md">
      <path
        d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2">
      </path>
    </svg>
    <span class="m-md text-white" :class="{ 'blink-attention': props?.data?.devices?.length }">Система
      Моніторингу</span>
  </div>

  <div class="stats-grid-container">

    <div class="stat-item">
      <div class="column items-center q-gutter-sm">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="icon-base text-primary">
          <path
            d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z">
          </path>
        </svg>
        <p class="text-label">Максимальна потужність</p>
        <p class="blink-attention">{{ props?.data?.threshold / 1000 }} kW</p>
      </div>
    </div>

    <div class="stat-item">
      <div class="column items-center q-gutter-sm">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="icon-base text-secondary">
          <line x1="10" x2="14" y1="2" y2="2"></line>
          <line x1="12" x2="15" y1="14" y2="11"></line>
          <circle cx="12" cy="14" r="8"></circle>
        </svg>
        <p class="text-label">Інтервал перемикання</p>
        <p class="blink-attention">{{ props?.data?.MIN_TOGGLE_INTERVAL_S }} сек</p>
      </div>
    </div>

    <div class="stat-item">
      <div class="column items-center q-gutter-sm">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="icon-base text-accent">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        <p class="text-label">Інтервал оновлення</p>
        <p class="blink-attention">{{ props?.data?.POLL_INTERVAL_S }} сек</p>
      </div>
    </div>
  </div>

  <div class="stats-header-container">
    <div style="flex: 1 1 49%">
      <p class="text-sm text-black q-mb-none text-center">Вимкнено пристроїв</p>
      <p class="blink-attention q-mb-none text-center">{{ props?.data?.devices?.length || 0 }}</p>
    </div>
    <div style="flex: 1 1 49%">
      <p class="text-sm text-black q-mb-none text-center">Вимкнена потужність</p>
      <p class="blink-attention q-mb-none text-center">{{ Math.floor(totalPower || 0) }} kW</p>
    </div>
  </div>

  <div>
    <h3 class="text-lg-semibold">Вимкнені пристрої:</h3>
    <p v-if="!props?.data?.devices?.length" class="text-center text-green">
      Система працює у штатному режимі: навантаження нормалізовано, примусового вимкнення споживачів не відбувалося.
    </p>

    <div class="devices-grid-container">
      <div class="device-card" v-for="device in props?.data?.devices" :key="device?.ip">
        <div class="flex items-start justify-between q-mb-sm">
          <div class="flex-gap-2">
            <div class="icon-box-destructive cursor-pointer" @click="powerStore.removeDeviceFromSystem(device?.ip)">
              <q-icon name="delete" size="sm" color="negative" />
            </div>
            <div>
              <p class="font-semibold text-dark q-mb-none">{{ device?.ip }}</p>
              <div class="status-badge-destructive">
                Вимкнено
              </div>
            </div>
          </div>
          <div class="text-right">
            <div class="flex-gap-1-sm">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="22" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                class="lucide lucide-zap">
                <path
                  d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z">
                </path>
              </svg>
              <span class="font-medium">{{ Math.floor(device?.power_w) }}W</span>
            </div>
          </div>
        </div>

        <div class="space-y-2 text-sm-muted">

          <div class="flex-gap-2">
            <q-icon name="schedule" size="xs" />
            <span>Вимкнено: {{ formatOffSince(device?.off_since) }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span>Тривалість: {{ formatDuration(device?.duration_s) }}</span>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { usePowerStore } from 'src/stores/power';
import { computed } from 'vue';

const powerStore = usePowerStore();

const props = defineProps(['data']);
const totalPower = computed<number>(() => {
  const devices = props.data?.devices;
  if (!Array.isArray(devices)) {
    return 0;
  }
  return devices.reduce((sum, device) => {
    const power = Number(device.power_w) || 0;
    return sum + power;
  }, 0);
});

function formatOffSince(unixTimestamp: number) {
  if (!unixTimestamp) return 'N/A';
  const date = new Date(unixTimestamp * 1000);

  const options: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };

  return new Intl.DateTimeFormat('uk-UA', options).format(date);
}

function formatDuration(totalSeconds: number) {
  if (typeof totalSeconds !== 'number' || totalSeconds < 0) {
    return '0 с';
  }

  const seconds = Math.floor(totalSeconds % 60);
  const minutes = Math.floor((totalSeconds / 60) % 60);
  const hours = Math.floor((totalSeconds / (60 * 60)) % 24);
  const days = Math.floor(totalSeconds / (60 * 60 * 24));

  const parts = [];

  if (days > 0) {
    parts.push(`${days} д`);
  }
  if (hours > 0) {
    const time = [
      String(hours).padStart(2, '0'),
      String(minutes).padStart(2, '0'),
      String(seconds).padStart(2, '0')
    ].join(':');

    if (days > 0) {
      parts.push(time);
    } else {
      if (hours > 0) parts.push(`${hours} год`);
      if (minutes > 0 && hours === 0) parts.push(`${minutes} хв`);
      if (minutes === 0 && hours === 0) parts.push(`${seconds} с`);
    }
  } else if (minutes > 0) {
    parts.push(`${minutes} хв`);
    parts.push(`${seconds} с`);
  } else {
    parts.push(`${seconds} с`);
  }

  if (parts.length > 1 && days > 0) {
    return `${days} д ${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  } else if (parts.length > 1) {
    return parts.slice(0, 2).join(' ');
  }

  return parts[0] || '0 с';
}
</script>

<style scoped lang="scss">
@import '../../css/quasar.variables.scss';

$primary-10: to-rgba($primary, 0.1);
$primary-5: to-rgba($primary, 0.05);
$accent-10: to-rgba($accent, 0.1);
$accent-5: to-rgba($accent, 0.05);
$secondary-10: to-rgba($secondary, 0.1);
$border-primary-20: to-rgba($primary, 0.2);

span {
  color: black;
}

.stats-grid-container {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 1.5rem;
  background: linear-gradient(to bottom right, $primary-5, $accent-5);
  border-radius: 0.5rem;
  border: 1px solid $border-primary-20;
  margin-top: 20px;
  color: white;
}

.stat-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.text-label {
  font-size: 0.75rem;
  color: white;
  font-weight: 500;
  line-height: 1.2;
  margin-bottom: 0;
}

@function to-rgba($color, $opacity) {
  @return rgba($color, $opacity);
}

$color-card: #ffffff;
$color-muted: #f1f5f9;
$color-shadow-primary: #000000;

$muted-50: to-rgba($color-muted, 0.5);
$muted-30: to-rgba($color-muted, 0.3);

.stats-header-container {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  padding: 1rem;
  background-color: white;
  border-radius: 0.5rem;
}

.devices-grid-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;

  @media (min-width: $breakpoint-md) {
    grid-template-columns: repeat(2, 1fr);
  }
}

.device-card {
  border-radius: 0.5rem;
  border: 1px solid rgba($dark, 0.1);
  background-color: $color-card;
  color: $dark;
  box-shadow: 0 1px 2px 0 rgba($color-shadow-primary, 0.05);
  padding: 1rem;

  transition: all 300ms ease-in-out;

  &:hover {
    box-shadow: 0 10px 15px -3px rgba($color-shadow-primary, 0.1), 0 4px 6px -2px rgba($color-shadow-primary, 0.05);
  }

  border-left: 4px solid rgba(240, 66, 66, 0.8);
  background-image: linear-gradient(to bottom right, $color-card, $muted-30);
}

.status-badge-destructive {
  display: inline-flex;
  align-items: center;
  border-radius: 9999px;
  padding: 0.125rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 600;
  background-color: rgba(240, 66, 66, 0.8);
  color: $white;
  margin-top: 0.25rem;
  border: none;
  transition: background-color 300ms;
}

.text-sm-muted {
  font-size: 0.875rem;
  color: $grey-7;
}

.text-lg-semibold {
  font-size: 1.125rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: white;
}

.flex-gap-2 {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.flex-gap-1-sm {
  @extend .flex-gap-2;
  gap: 0.25rem;
  font-size: 0.875rem;
  color: $grey-7;
}

.space-y-2 {
  &>*+* {
    margin-top: 0.5rem;
  }
}

.blink-attention {
  font-weight: 700;
  font-size: 18px;
}

.icon-box-destructive {
  background-color: rgba(240, 66, 66, 0.1);
  border-radius: 50%;
  padding: 5px;
}

.font-medium {
  color: rgb(98, 112, 132);
  font-weight: 500;
}

.font-semibold {
  font-weight: 600;
}
</style>
