<template>
    <div class="row device-row">
        <q-icon @click="toggleDevice(device?.device_on)" name="power_settings_new" class="cursor-pointer toggle-device"
            :class="{ 'text-white': device?.device_on == 0, 'text-red': device?.device_on == 1 }" size="3em" />
        <div :class="{
            'connected-device': device?.device_on == 1,
            'disconnected-device': device?.device_on == 0,
        }" class="q-pa-xs cursor-pointer text-weight-bold q-mt-sm q-mb-10 text-center cursor-pointer badge">
        </div>

        <h6 @click="copy(device?.device_id)" class="tect-center full-width text-capitalize">
            {{ device?.name }}
            <q-icon @click="deleteDevice(device?.ip)" class="q-pl-md" name="delete" size="2.5em"></q-icon>
        </h6>

        <div class="row justify-between full-width q-mt-md">
            <div class="column">
                <span class="unique">{{ device?.model }}</span>
                <span @click="copy(device?.ip)" class="unique">{{ device?.ip }}</span>
            </div>

            <div class="column">
                <span>{{ new Date(device?.added_at)?.toLocaleDateString() }}</span>
                <span class="unique">
                    {{ device?.hw_ver }}
                    <q-tooltip>
                        Hardware version.
                    </q-tooltip>
                </span>
            </div>
        </div>

        <div class="column full-width">
            <p>Потужність: {{ device?.power_watt }}</p>
            <p>Приорітет: {{ device?.priority }}</p>
            <p>
                {{ device?.fw_ver }}
                <q-tooltip>
                    Software version.
                </q-tooltip>
            </p>
        </div>
    </div>
</template>

<script setup lang="ts">
import { copy, useSessionStorage } from 'src/helpers/utils';
import { TapoDevice } from 'src/models';
import { useTapoStore } from 'src/stores/tapo';
import { computed } from 'vue';

const token = useSessionStorage("access_token");
const tapoStore = useTapoStore()

const props = defineProps<{ device: TapoDevice }>()
const device = computed(() => props.device)

async function deleteDevice(ip: string) {
    if (!token) {
        return;
    }
    await tapoStore.removeDevice(ip);
}

async function toggleDevice(state: number) {
    if (!token) {
        return;
    }
    try {
        if (state == 1) {
            await tapoStore.disableDevice(props.device?.ip);
        } else {
            await tapoStore.enableDevice(props.device?.ip);
        }
    } catch (err) {
        console.error(err);
    }
}
</script>

<style scoped lang="scss">
.device-row {
    width: 100%;
    padding: 10px;
    border: 1px solid white;
    border-radius: 10px;
    position: relative;
}

.toggle-device {
    position: absolute;
    top: 4px;
    right: 4px;
}

.badge:before {
    top: -9px;
    left: 0px;
}
</style>
