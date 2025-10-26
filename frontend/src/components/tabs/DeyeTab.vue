<template>
  <div class="text-h6 q-mb-sm full-width">Deye Inverter Devices</div>
  <p>Тут ви можете керувати своїми пристроями Deye.</p>

  <div class="red-item">
    <q-expansion-item :disable="!token" v-model="expandAddDeyeDevice" icon="add" label="Add new device" dark
      dense-toggle>
      <p>
        Перш ніж додати ваш інвертор Deye, необхідно дізнатися IP-адресу Wi-Fi стіка та серійний номер
        пристрою. Рекомендуємо призначити статичну IP-адресу, щоб уникнути збоїв у роботі.
      </p>

      <q-input label-color="white" label="Device IP Address" :disable="!token" v-model="createDeye.ip" filled
        class="q-mb-sm q-mt-sm" />
      <q-input label-color="white" label="Device Serial Number" :disable="!token" v-model="createDeye.serial_number"
        filled class="q-mb-sm q-mt-sm" />
      <q-btn :loading="loading" @click="createDeyeDevice"
        :disable="!token || !createDeye.ip || !createDeye.serial_number" color="black" label="Додати інвертор" />
    </q-expansion-item>
  </div>

  <q-separator class="q-mt-md q-mb-md" color="white" />

  <div v-for="item of deyeStore?.deyeData" :key="item?.serial_number">
    <div class="deye-item column q-mt-sm q-mb-sm rounded-borders q-pa-lg">
      <div class="row">
        <q-icon @click.prevent="deleteDevice(item?.ip)" class="cursor-pointer q-mr-sm remove" name="delete" size="1.5em"
          color="red"></q-icon>

        <div class="row justify-between" style="flex: 1 1 auto;">
          <span @click="copy(item?.id)">
            <span class="muted">ID:</span> {{ item?.id }}
          </span>

          <span :class="item?.device_on == 0 ? 'text-red' : 'text-green'">
            {{ item?.device_on == 0 ? 'Disabled' : 'Enabled' }}
          </span>
        </div>
      </div>


      <div class="row justify-between q-mt-sm">
        <span @click="copy(item?.serial_number)" class="text-caption">
          <span class="muted">SN:</span>
          {{ item?.serial_number }}
          <q-tooltip> Серійний номер пристрою. </q-tooltip>
        </span>

        <span @click="copy(item?.ip)" class="text-caption">
          <span class="muted">IP:</span> {{ item?.ip }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { copy, useSessionStorage } from 'src/helpers/utils';
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
      position: 'top',
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
  border: 1px solid rgba(43, 48, 59, 0.5);
  background: linear-gradient(135deg, rgb(25, 29, 36), rgb(33, 36, 44));
  border-radius: 10px;
}

.remove {
  background-color: rgba(239, 67, 67, 0.1);
  padding: 8px;
  border-radius: 10px;
}
</style>
