<template>
  <div class="text-h6 q-mb-sm full-width">Deye inverter Devices</div>
  <q-expansion-item :disable="!token" v-model="expandAddDeyeDevice" icon="add" label="Add new device" dark dense-toggle>
    <p>
      Перш ніж додати ваш інвертор Deye, необхідно дізнатися IP-адресу Wi-Fi стіка та серійний номер
      пристрою. Рекомендуємо призначити статичну IP-адресу, щоб уникнути збоїв у роботі.
    </p>

    <q-input label-color="white" label="Device IP Address" :disable="!token" v-model="createDeye.ip" filled
      class="q-mb-sm q-mt-sm" />
    <q-input label-color="white" label="Device Serial Number" :disable="!token" v-model="createDeye.serial_number"
      filled class="q-mb-sm q-mt-sm" />
    <q-btn :loading="loading" @click="createDeyeDevice" :disable="!token || !createDeye.ip || !createDeye.serial_number"
      color="black" label="Додати новий Deye пристрій" />
  </q-expansion-item>

  <div v-for="item of deyeStore?.deyeData" :key="item?.serial_number">
    <div class="deye-item column q-mt-sm q-mb-sm rounded-borders q-pa-md">
      <div class="row justify-between">
        <span>
          <q-icon @click.prevent="deleteDevice(item?.ip)" class="cursor-pointer q-mr-sm" name="delete"
            size="1.5em"></q-icon>
          ID: {{ item?.id }}
        </span>
        <span>IP: {{ item?.ip }}</span>
      </div>
      <div class="row justify-between">
        <span>SN:
          {{ item?.serial_number }}
          <q-tooltip>
            Серійний номер пристрою.
          </q-tooltip>
        </span>
        <span :class="item?.device_on == 0 ? 'text-red' : 'text-green'">
          {{ item?.device_on == 0 ? 'Disabled' : 'Enabled' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useSessionStorage } from 'src/helpers/utils';
import { useDeyeStore } from 'src/stores/deye';
import { Notify } from 'quasar';

const deyeStore = useDeyeStore();

const token = useSessionStorage('access_token');

const expandAddDeyeDevice = ref(false);
const intervalId = ref();
const loading = ref(false);
const createDeye = ref({ ip: '', serial_number: '' });

async function createDeyeDevice() {
  try {
    loading.value = true;
    await deyeStore.createDeyeDevice({
      ip: createDeye.value.ip,
      serial_number: createDeye.value.serial_number,
      slave_id: 1,
    });
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
}

async function deleteDevice(ip: string) {
  try {
    await deyeStore.deleteDeyeDevice(ip);
    Notify.create({
      message: 'Ви успішно видалили пристрій',
      color: 'secondary',
    });
  } catch (error) {
    console.error(error);
    Notify.create({
      message: 'Сталася помилка під час видалення пристрою',
      color: 'red',
      icon: 'warning',
      position: 'top',
      timeout: 2000,
    });
  }
}

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await Promise.allSettled([deyeStore.fetchDeyeDevices()]);
  }, 5000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

deyeStore.fetchDeyeDevices();
</script>

<style scoped lang="scss">
.deye-item {
  border: 1px solid white;
}
</style>
