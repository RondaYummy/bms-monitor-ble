<template>
  <q-dialog v-model="localShow">
    <div class="column dialog-body">
      <h6>Змінити пароль</h6>

      <q-input :disable="!token"
               v-model="oldPassword"
               label="Введіть пароль"
               filled />
      <q-input :disable="!token"
               label="Повторіть пароль"
               v-model="oldAgainPassword"
               filled />

      <q-separator class="q-mt-md"
                   color="white" />

      <q-input :disable="!token"
               label="Ввудіть новий пароль"
               v-model="newPassword"
               filled />

      <div class='row justify-between q-mt-sm'>
        <q-btn @click="updatePassword"
               color="positive"
               size="xs"
               :disable="!token"
               label="Зберегти" />

        <q-btn @click="close"
               size="xs"
               color="black"
               :disable="!token"
               label="Скасувати" />
      </div>
    </div>
  </q-dialog>
</template>

<script setup lang="ts">
import { useSessionStorage } from 'src/helpers/utils';
import { defineProps, defineEmits, ref, watch } from 'vue';
import { useQuasar } from 'quasar';

const $q = useQuasar();
const token = useSessionStorage("access_token");

interface Props {
  show: boolean;
}

const props = defineProps<Props>();
const oldPassword = ref('');
const newPassword = ref('');
const oldAgainPassword = ref('');

const emits = defineEmits<{
  (e: 'update:show', value: boolean): void;
}>();
const localShow = ref(props.show);

watch(() => props.show, (newVal) => {
  localShow.value = newVal;
});

watch(localShow, (newVal) => {
  emits('update:show', newVal);
});

function close() {
  localShow.value = false;
  oldPassword.value = '';
  newPassword.value = '';
  oldAgainPassword.value = '';
}

async function updatePassword() {
  try {
    const response = await fetch('/api/change-password', {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token.value}`
      },
      body: JSON.stringify({ old_password: oldPassword.value, new_password: newPassword.value }),
    });
    const json = await response.json();
    $q.notify({
      message: json?.message,
      color: 'info',
      icon: 'info',
      position: 'top',
      timeout: 2000,
    });
    close();
  } catch (error) {
    console.error('Error updating configs:', error);
  }
}
</script>

<style scoped lang='scss'>
.dialog-body {
  padding: 20px;
  gap: 10px;
  background: #1e1f26;
}
</style>
