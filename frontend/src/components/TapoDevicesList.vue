<template>
    <div class="row device-row">
        <h6 class="tect-center">{{ device?.name }}</h6>

        <div class="column">
            <span>Model: {{ device?.model }}</span>
            <span>FW v.: {{ device?.fw_ver }}</span>
            <span>HW v.: {{ device?.hw_ver }}</span>
            <span>HW v.: {{ device?.device_on }}</span>
            <span>ip: {{ device?.ip }}</span>
            <span>name: {{ device?.name }}</span>
            <span>email: {{ device?.email }}</span>
            <span>added_at: {{ device?.added_at }}</span>
        </div>
        1
        <div class="column">
            <q-icon @click="device?.device_on ? disableDevice : enableDevice" name="power_settings_new"
                class="text-white cursor-pointer" size="2em" />
        </div>
    </div>
</template>

<script setup lang="ts">
import { TapoDevice } from 'src/models'
import { useTapoStore } from 'src/stores/tapo'
import { computed, ref } from 'vue'

const tapoStore = useTapoStore()

const props = defineProps<{ device: TapoDevice }>()
const device = computed(() => props.device)
const disableButton = ref(false)

async function disableDevice() {
    try {
        disableButton.value = true
        await tapoStore.disableDevice(props.device?.ip)
    } catch (error) {
        console.error(error)
    } finally {
        disableButton.value = false
    }
}

async function enableDevice() {
    try {
        disableButton.value = true
        await tapoStore.disableDevice(props.device?.ip)
    } catch (error) {
        console.error(error)
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
