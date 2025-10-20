<template>
  <div class="body">
    <div class="header">
      <div class="image">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path
            d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z">
          </path>
        </svg>

        <div class="text-h6 text-weight-bold">Статус сертифіката</div>
      </div>
    </div>

    <div class="content">
      <div class="badge">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="m9 12 2 2 4-4"></path>
        </svg>

        {{ certificatStatus(props.data?.status) }}
      </div>

      <div class="box">Сертифікат дійсний ще {{ props.data.certificat?.days_left }} днів.</div>

      <div class="box left">
        <div class="svg circle purpl">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            style="color: rgb(232, 48, 110)">
            <path d="M8 2v4"></path>
            <path d="M16 2v4"></path>
            <rect width="18" height="18" x="3" y="4" rx="2"></rect>
            <path d="M3 10h18"></path>
          </svg>
        </div>

        <div class="column">
          <div class="sub-title">Дата створення</div>
          <div class="title">{{ formatTimestamp(props.data?.certificat?.created_at) }}</div>
        </div>
      </div>

      <div class="box left">
        <div class="svg circle red">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
            style="color: rgb(239, 67, 67)">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
        </div>

        <div class="column">
          <div class="sub-title">Дата закінчення</div>
          <div class="title">{{ formatTimestamp(props.data?.certificat?.expires_at) }}</div>
        </div>
      </div>

      <div class="row justify-between full-width gap">
        <div class="box mini">
          <div class="column">
            <div class="sub-title">Всього днів</div>
            <div class="title">{{ props.data.certificat?.days_valid }}</div>
          </div>
        </div>

        <div class="box mini">
          <div class="column">
            <div class="sub-title">Залишилось днів</div>
            <div class="title">{{ props.data.certificat?.days_left }}</div>
          </div>
        </div>
      </div>

      <div class="mt-6 full-width">
        <div class="row q-mt-sm justify-between text-sm q-mb-sm">
          <span>Прогрес</span>
          <span>{{ Math.round(percentLeft) }}%</span>
        </div>
        <div class="full-width" style="background-color: rgb(43, 48, 59); height: 6px; border-radius: 4px">
          <div class="" style="
              background-image: linear-gradient(135deg, rgb(232, 48, 110), rgb(217, 38, 157));
              height: 6px;
            " :style="{ width: `${percentLeft}%` }"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { formatTimestamp } from 'src/helpers/utils';
import { computed } from 'vue';

const props = defineProps(['data']);

const percentLeft = computed(
  () => (props.data.certificat?.days_left / props.data.certificat?.days_valid) * 100
);

function certificatStatus(status: string) {
  if (status === 'ok') {
    return 'Дійсний';
  } else if (status === 'warning') {
    return 'Закінчується';
  } else if (status === 'danger') {
    return 'Критичний';
  }
  return 'Невідомо';
}
</script>

<style scoped lang="scss">
.body {
  background-color: rgb(25, 29, 36);
  font-family:
    ui-sans-serif, system-ui, sans-serif, 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji';

  .header {
    background-image: linear-gradient(135deg, rgb(232, 48, 110), rgb(217, 38, 157));
    height: 96px;
    display: flex;
    align-items: center;
    justify-content: center;

    .image {
      background-color: rgba(17, 19, 23, 0.1);
      backdrop-filter: blur(4px);
      padding: 0.5rem 0.5rem 0.2rem 0.5rem;
      border-radius: 0.75rem;
      width: fit-content;
      display: flex;
      gap: 10px;
      align-items: center;
    }
  }

  .content {
    color: rgb(248, 250, 252);
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    .badge {
      display: flex;
      align-items: center;
      justify-content: center;
      background-color: rgb(22, 162, 73);
      border-radius: 9999px;
      border-style: solid;
      border-width: 1px;
      border-color: transparent;
      color: rgb(248, 250, 252);
      font-size: 16px;
      font-weight: 600;
      width: fit-content;
      padding: 16px;
      height: 42px;
    }
  }

  .box {
    width: 100%;
    background-color: rgba(33, 36, 44, 0.5);
    border: 1px solid rgb(43, 48, 59);
    border-radius: 12px;
    min-height: 58px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgb(248, 250, 252);
    font-weight: 700;
    margin-top: 16px;
    margin-bottom: 0px;
    padding: 16px;

    .svg {
      margin-right: 16px;
    }

    .sub-title {
      margin-bottom: 4px;
      font-size: 14px;
      line-height: 20px;
      color: rgb(152, 164, 179);
    }

    .title {
      font-weight: 500;
      line-height: 24px;
      color: rgb(248, 250, 252);
    }
  }

  .left {
    justify-content: flex-start;
  }

  .mini {
    max-width: 48%;
    height: 98px;
    text-align: center;

    .title {
      font-weight: 700;
      font-size: 30px;
    }
  }
}

.gap {
  gap: 6px;
}

.circle {
  padding: 8px;
  border-radius: 12px;
}

.purpl {
  background-color: rgba(232, 48, 110, 0.1);
}

.red {
  background-color: rgba(239, 67, 67, 0.1);
}
</style>
