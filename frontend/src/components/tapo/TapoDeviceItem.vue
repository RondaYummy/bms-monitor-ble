<template>
  <div class="row device-row">
    <q-icon
    v-if="!loadding"
      @click="toggleDevice(device?.device_on)"
      name="power_settings_new"
      class="cursor-pointer toggle-device"
      :class="{ 'text-white': device?.device_on == 0, 'text-red': device?.device_on == 1 }"
      size="3em"
    />
    <div v-else class="loader toggle-device"></div>
    <div
      :class="{
        'connected-device': device?.device_on == 1,
        'disconnected-device': device?.device_on == 0,
      }"
      class="q-pa-xs cursor-pointer text-weight-bold q-mt-sm q-mb-10 text-center cursor-pointer badge"
    ></div>

    <h6 @click="copy(device?.device_id)" class="tect-center full-width text-capitalize">
      <span class="q-mr-sm">{{ device?.name }}</span>
    </h6>

    <div class="row justify-between full-width q-mt-md">
      <div class="column">
        <span class="text-left">
          <span class="unique q-mr-sm">
            {{ device?.model }}
          </span>
          <q-icon
            @click.prevent="openEditModal(device)"
            class="cursor-pointer"
            name="edit"
            size="1.5em"
          ></q-icon>
        </span>

        <span @click="copy(device?.ip)" class="unique">{{ device?.ip }}</span>
      </div>

      <div class="column">
        <span>{{ new Date(device?.added_at)?.toLocaleDateString() }}</span>
        <div class="row">
          <span class="q-mr-sm">
            [ {{ device?.priority }} ]
            <q-tooltip>
              Приорітет пристрою, для автоматичного увімкнення чи вимкнення. Більше число, більший
              приорітет.
            </q-tooltip>
          </span>

          <span class="unique">
            {{ Math.floor(device?.power_watt || 0) }} Вт
            <q-tooltip> Потужність підключеного приладу через цю розетку у ватах. </q-tooltip>
          </span>
        </div>
      </div>
    </div>
  </div>

  <q-dialog v-model="openModalEdit" persistent>
    <q-card dark style="min-width: 350px">
      <q-card-section>
        <div class="text-h6">
          <q-icon
            @click.prevent="deleteDevice(device?.ip)"
            class="cursor-pointer q-mr-sm"
            name="delete"
            size="1.5em"
          ></q-icon>
          {{ editedDeviceData?.name }}
        </div>
        <div class="row justify-center full-width">
          <span @click="copy(device?.hw_ver)" class="unique q-mr-sm">
            [ {{ device?.hw_ver }} ]
            <q-tooltip> Hardware version. </q-tooltip>
          </span>
          <span @click="copy(device?.fw_ver)">
            {{ device?.fw_ver }}
            <q-tooltip> Software version. </q-tooltip>
          </span>
        </div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <div class="row justify-between items-center">
          <q-input
            label-color="white"
            dark
            label="Device IP Address"
            :disable="!token"
            v-model="editedDeviceData.ip"
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
            dark
            label="Priority"
            :disable="!token"
            v-model="editedDeviceData.priority"
            filled
            class="q-mb-sm"
            style="flex: 1 1 auto"
          />
          <q-icon class="q-pl-md" name="help" size="2.5em">
            <q-tooltip>
              Приорітет пристрою, чим вищий приорітет, тим важливіший пристрій. Наприклад
              автоматична система буде включати прилади з вищим приорітеом в першу чергу. система
              буде включати прилади з вищим приорітеом в першу чергу.
            </q-tooltip>
          </q-icon>
        </div>

        <div class="row justify-between items-center">
          <q-input
            label-color="white"
            dark
            label="Email to Tapo application"
            :disable="!token"
            v-model="editedDeviceData.email"
            filled
            class="q-mb-sm"
            style="flex: 1 1 auto"
          />
          <q-icon class="q-pl-md" name="help" size="2.5em">
            <q-tooltip> Необхідно для підключення до вашого девайсу. </q-tooltip>
          </q-icon>
        </div>

        <div class="row justify-between items-center">
          <q-input
            label-color="white"
            dark
            label="Password to Tapo application"
            :disable="!token"
            v-model="editedDeviceData.password"
            filled
            class="q-mb-sm"
            style="flex: 1 1 auto"
          />
          <q-icon class="q-pl-md" name="help" size="2.5em">
            <q-tooltip> Необхідно для підключення до вашого девайсу. </q-tooltip>
          </q-icon>
        </div>

        <div class="row justify-between items-center">
          <q-input
            label-color="white"
            dark
            label="Device power ( W )"
            :disable="!token"
            v-model="editedDeviceData.power_watt"
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
          :loading="loadingEditDevice"
          @click="editTapoDevice"
          :disable="!token"
          color="black"
          label="Update"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>

  <q-separator color="orange" inset />
</template>

<script setup lang="ts">
import { copy, useSessionStorage } from 'src/helpers/utils';
import { TapoDevice } from 'src/models';
import { UpdateTapoDeviceDto, useTapoStore } from 'src/stores/tapo';
import { computed, ref } from 'vue';

const token = useSessionStorage('access_token');
const tapoStore = useTapoStore();

const props = defineProps<{ device: TapoDevice }>();
const device = computed(() => props.device);
const openModalEdit = ref(false);
const loadingEditDevice = ref(false);
const editedTapoIp = ref('');
const loadding = ref(false);
const editedDeviceData = ref<TapoDevice & { password?: string }>({
  added_at: '',
  device_id: '',
  device_on: 0,
  email: '',
  fw_ver: '',
  password: '',
  hw_ver: '',
  id: 0,
  ip: '',
  model: '',
  name: '',
  power_watt: 0,
  priority: 0,
});

async function deleteDevice(ip: string) {
  if (!token.value) return;
  await tapoStore.removeDevice(ip);
}

async function openEditModal(device: TapoDevice) {
  editedTapoIp.value = device.ip;
  editedDeviceData.value = device;
  openModalEdit.value = true;
}

async function editTapoDevice() {
  loadingEditDevice.value = true;
  try {
    const updateData: UpdateTapoDeviceDto = {
      email: editedDeviceData.value.email,
      power_watt: editedDeviceData.value.power_watt,
      priority: editedDeviceData.value.priority,
    };
    if (editedDeviceData.value.password) {
      updateData.password = editedDeviceData.value.password;
    }

    await tapoStore.updateTapoDeviceConfig(editedTapoIp.value, updateData);
  } catch (error) {
    console.error(error);
  } finally {
    loadingEditDevice.value = false;
  }
}

async function toggleDevice(state: number) {
  if (!token.value) return;
  loadding.value = true;
  try {
    if (state == 1) {
      await tapoStore.disableDevice(props.device?.ip);
    } else {
      await tapoStore.enableDevice(props.device?.ip);
    }
  } catch (err) {
    console.error(err);
  } finally {
    loadding.value = false;
  }
}
</script>

<style scoped lang="scss">
.device-row {
  width: 100%;
  padding: 15px;
  position: relative;
}

.toggle-device {
  position: absolute;
  top: 10px;
  right: 10px;
}

.badge:before {
  top: -9px;
  left: 2px;
}
</style>
