<template>
    <div class="row device-row">
        <h6 @click="copy(device?.device_id)" class="tect-center full-width text-capitalize">{{ device?.name }}</h6>
        <div class="row justify-between full-width">
            <div class="column">
                <span class="unique">{{ device?.model }}</span>
                <span @click="copy(device?.ip)" class="unique">{{ device?.ip }}</span>
            </div>

            <q-icon @click="toggleDevice(device?.device_on)" name="power_settings_new" class="cursor-pointer"
                :class="{ 'text-white': device?.device_on == 0, 'text-red': device?.device_on == 1 }" size="3em" />

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

        <div class="column">
            <span>{{ device?.email }}</span>
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
import { copy, useSessionStorage } from 'src/helpers/utils'
import { TapoDevice } from 'src/models'
import { useTapoStore } from 'src/stores/tapo'
import { computed, ref } from 'vue'

const token = useSessionStorage("access_token");
const tapoStore = useTapoStore()

const props = defineProps<{ device: TapoDevice }>()
const device = computed(() => props.device)
const disableButton = ref(false)

async function toggleDevice(state: number) {
    try {
        if (disableButton.value || !token) return
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
}
</style>
