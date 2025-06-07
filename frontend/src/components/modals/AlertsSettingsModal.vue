<template>
  <q-dialog v-model="localShow">
    <div class="column dialog-body">
      <div class="column">
        <p>
          Періодичність сповіщеннь ( Alerts ):

          <q-tooltip>
            Це значення задається в цілих годинах. Якщо встановлено 12 годин, то ви не
            отримуватимете важливих сповіщень про стан батареї частіше ніж раз на 12 годин. Це
            зроблено, щоб уникнути надмірної кількості повідомлень у вашій скриньці.
          </q-tooltip>
        </p>
        <q-input
          :disable="!token"
          v-model.number="config.n_hours"
          label-color="white"
          type="number"
          filled
        />
      </div>

      <div class="row justify-between q-mt-sm">
        <q-btn
          @click="configStore.updateConfigs"
          color="black"
          size="xs"
          :disable="!token"
          label="Зберегти"
        />

        <q-btn @click="close" size="xs" color="black" :disable="!token" label="Скасувати" />
      </div>
    </div>
  </q-dialog>
</template>

<script setup lang="ts">
import { useSessionStorage } from 'src/helpers/utils';
import type { Config } from 'src/models';
import { useConfigStore } from 'src/stores/config';
import { ref, watch } from 'vue';

const token = useSessionStorage('access_token');
const configStore = useConfigStore();

interface Props {
  show: boolean;
  config: Config;
}

const props = defineProps<Props>();
const oldPassword = ref('');
const newPassword = ref('');
const oldAgainPassword = ref('');

const emits = defineEmits<{
  (e: 'update:show', value: boolean): void;
}>();
const localShow = ref(props.show);
const config = ref<Config>(props.config);

watch(
  () => props.show,
  (newVal) => {
    localShow.value = newVal;
  }
);

watch(localShow, (newVal) => {
  emits('update:show', newVal);
});

function close() {
  localShow.value = false;
  oldPassword.value = '';
  newPassword.value = '';
  oldAgainPassword.value = '';
}
</script>

<style scoped lang="scss">
.dialog-body {
  padding: 20px;
  gap: 10px;
  background: #1e1f26;
}
</style>
