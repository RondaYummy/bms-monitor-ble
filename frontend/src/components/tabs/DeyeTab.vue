<template>
    <div class="text-h6 q-mb-sm full-width">Deye inverter Devices</div>
    <q-expansion-item :disable="!token" v-model="expandAddDeyeDevice" icon="add" label="Add new device" dark
        dense-toggle>
        <q-input label-color="white" label="Device IP Address" :disable="!token" v-model="createDeye.ip" filled
            class="q-mb-sm q-mt-sm" />
        <q-input label-color="white" label="Device Serial Number" :disable="!token" v-model="createDeye.serial_number"
            filled class="q-mb-sm q-mt-sm" />
        <q-btn :loading="loading" @click="createDeyeDevice"
            :disable="!token || !createDeye.ip || !createDeye.serial_number" color="black"
            label="Додати новий Deye пристрій" />
    </q-expansion-item>

    {{ deyeStore?.deyeData }}
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useSessionStorage } from 'src/helpers/utils';
import { useDeyeStore } from 'src/stores/deye';

const deyeStore = useDeyeStore();

const token = useSessionStorage("access_token");

const expandAddDeyeDevice = ref(false);
const loading = ref(false);
const createDeye = ref({ ip: '', serial_number: '' })

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

deyeStore.fetchDeyeDevices();
</script>