<template>
    <div class="row device-row">
        <h6 class="tect-center full-width text-capitalize">{{ device?.name }}</h6>

        <div class="column">
            <div class="q-mb-10">
                Hardware v.
                <span class="unique">{{ device?.hw_ver }}</span>
            </div>
            <div>
                Software v.
                <span class="unique">{{ device?.fw_ver }}</span>
            </div>
        </div>

        <div class="column">
            <span>Model: {{ device?.model }}</span>
            <span>IP: {{ device?.ip }}</span>
            <span>Email: {{ device?.email }}</span>
            <span>{{ parseManufacturingDate(device?.added_at) }}</span>
        </div>
        <div class="column">
            {{ device?.device_on == 1 }}
            {{ device?.device_on == 0 }}
            <q-icon @click="toggleDevice(device?.device_on)" name="power_settings_new"
                class="cursor-pointer"
                :class="{ 'text-white': device?.device_on == 0, 'text-red': device?.device_on == 1 }" size="2em" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { parseManufacturingDate } from 'src/helpers/utils'
import { TapoDevice } from 'src/models'
import { useTapoStore } from 'src/stores/tapo'
import { computed, ref } from 'vue'

const tapoStore = useTapoStore()

const props = defineProps<{ device: TapoDevice }>()
const device = computed(() => props.device)
const disableButton = ref(false)

async function toggleDevice(state: number) {
    try {
        if (disableButton.value) return
        disableButton.value = true
        if (state == 1) {
            await tapoStore.disableDevice(props.device?.ip)
        } else {
            await tapoStore.enableDevice(props.device?.ip)
        }
    } catch (err) {
        console.error(err)
    } finally {
        disableButton.value = false
    }
}
</script>

<style scoped lang="scss">
.device-row {
    width: 100%;
    height: 100px;
    border: 1px solid white;
    border-radius: 5px;
}
</style>
