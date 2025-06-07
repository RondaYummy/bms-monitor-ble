<template>
  <div class="text-h6 q-mb-sm full-width">TP-LINK Tapo Devices</div>

  <q-expansion-item
    :disable="!token"
    v-model="expandAddTapoDevice"
    icon="add"
    label="Add new device"
    dark
    dense-toggle
  >
    <p>
      Перш ніж додати новий пристрій TP-Link Tapo, переконайтесь, що він уже доданий в офіційний
      застосунок Tapo. Після цього введіть у поля нижче ваші облікові дані (email та пароль) — це
      необхідно для авторизації та доступу до ваших пристроїв.
    </p>

    <q-input
      label-color="white"
      label="Email from Tapo App"
      :disable="!token"
      v-model="newTapoDevice.email"
      filled
      class="q-mb-sm q-mt-sm"
      style="flex: 1 1 auto"
    />
    <q-input
      label-color="white"
      label="Password from Tapo App"
      :disable="!token"
      v-model="newTapoDevice.password"
      filled
      class="q-mb-sm q-mt-sm"
      style="flex: 1 1 auto"
    />

    <q-btn
      :loading="loadingTapoDevices"
      @click="searchTapoDevices"
      :disable="!token || !newTapoDevice.email || !newTapoDevice.password"
      color="black"
      label="Шукати пристрої Tapo"
    />

    <q-separator v-if="!tapoStore.foundDevices?.length" class="q-mt-md q-mb-md" color="white" />

    <template v-if="!tapoStore.foundDevices?.length">
      <h6 class="q-mt-md">Нових пристроїв TP-Link Tapo не знайдено.</h6>
    </template>

    <h6 v-if="tapoStore.foundDevices?.length" class="q-mt-md">
      Знайдено нові пристрої TP-Link Tapo:
    </h6>
    <q-list v-if="tapoStore.foundDevices?.length" bordered separator>
      <q-item
        v-for="device of tapoStore.foundDevices"
        :key="device?.ip"
        clickable
        :disable="openModalAddTapo"
        @click="token && openModalAddTapoDevice(device)"
        v-ripple
        class="justify-between items-center"
      >
        <div class="text-h6">
          {{ device?.name }}
        </div>
        {{ device?.ip }} | {{ device?.model }}
      </q-item>
    </q-list>

    <q-dialog v-model="openModalAddTapo" persistent>
      <q-card dark style="min-width: 350px">
        <q-card-section>
          <div class="text-h6">{{ modalAddTapoDeviceData?.nmae }}</div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <div class="row justify-between items-center">
            <q-input
              label-color="white"
              label="Device IP Address"
              :disable="!token"
              v-model="newTapoDevice.ip"
              filled
              class="q-mb-sm q-mt-sm"
              style="flex: 1 1 auto"
            />
            <q-icon class="q-pl-md" name="help" size="2.5em">
              <q-tooltip>
                Щоб забезпечити стабільну роботу системи, потрібно **призначити статичні IP-адреси**
                для інвертора та розеток Tapo через налаштування роутера. Це запобігає випадковій
                зміні IP після перезавантаження та гарантує постійне з'єднання.
              </q-tooltip>
            </q-icon>
          </div>

          <div class="row justify-between items-center">
            <q-input
              label-color="white"
              label="Priority"
              :disable="!token"
              v-model="newTapoDevice.priority"
              filled
              class="q-mb-sm"
              style="flex: 1 1 auto"
            />
            <q-icon class="q-pl-md" name="help" size="2.5em">
              <q-tooltip>
                Приорітет пристрою, чим вищий приорітет, тим важливіший пристрій. Наприклад
                автоматична система буде включати прилади з вищим приорітеом в першу чергу.
              </q-tooltip>
            </q-icon>
          </div>

          <div class="row justify-between items-center">
            <q-input
              label-color="white"
              label="Device power ( W )"
              :disable="!token"
              v-model="newTapoDevice.power_watt"
              filled
              class="q-mb-sm"
              style="flex: 1 1 auto"
            />
            <q-icon class="q-pl-md" name="help" size="2.5em">
              <q-tooltip>
                Потужність прилада, який вмикається цією розеткою Tapo. Наприклад бойлер, який
                використовує 2 кВт - вказуєте 2000 ват.
              </q-tooltip>
            </q-icon>
          </div>
        </q-card-section>

        <q-card-actions align="right" class="text-primary">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn
            v-close-popup
            :loading="loadingDevices"
            @click="addTapoDevice"
            :disable="
              !token || !newTapoDevice.ip || !newTapoDevice.email || !newTapoDevice.password
            "
            color="black"
            label="Додати новий пристрій"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-expansion-item>

  <q-separator class="q-mt-md q-mb-md" color="white" />

  <TapoDevicesList />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import TapoDevicesList from '../tapo/TapoDevicesList.vue';
import { useTapoStore } from 'src/stores/tapo';
import { useSessionStorage } from 'src/helpers/utils';

const tapoStore = useTapoStore();

const token = useSessionStorage('access_token');

const loadingDevices = ref<boolean>(false);
const expandAddTapoDevice = ref(false);
const loadingTapoDevices = ref<boolean>(false);
const openModalAddTapo = ref<boolean>(false);
const modalAddTapoDeviceData = ref();
const intervalId = ref();
const newTapoDevice = ref({ ip: '', email: '', password: '', power_watt: 0, priority: 1 });

async function openModalAddTapoDevice(device: any) {
  modalAddTapoDeviceData.value = device;
  openModalAddTapo.value = true;
  newTapoDevice.value.ip = device?.ip;
}

async function searchTapoDevices() {
  loadingTapoDevices.value = true;
  try {
    await tapoStore.searchTapoDevices({
      email: newTapoDevice.value.email,
      password: newTapoDevice.value.password,
    });
  } catch (error) {
    console.error(error);
  } finally {
    loadingTapoDevices.value = false;
  }
}

async function addTapoDevice() {
  await tapoStore.addDevice({
    ip: newTapoDevice.value.ip,
    email: newTapoDevice.value.email,
    password: newTapoDevice.value.password,
    power_watt: newTapoDevice.value?.power_watt,
    priority: newTapoDevice.value?.priority,
  });
  newTapoDevice.value.ip = '';
}

onMounted(async () => {
  intervalId.value = setInterval(async () => {
    await tapoStore.fetchDevices();
  }, 5000);
});

onBeforeUnmount(() => {
  clearInterval(intervalId.value);
});

tapoStore.fetchDevices();
</script>
