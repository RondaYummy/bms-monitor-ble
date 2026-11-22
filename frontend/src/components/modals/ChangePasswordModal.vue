<template>
  <q-dialog v-model="localShow">
    <div class="column dialog-body">
      <h6>Змінити пароль</h6>

      <q-input
        :disable="!token"
        v-model="oldPassword"
        type="password"
        autocomplete="current-password"
        label="Введіть поточний пароль"
        label-color="white"
        filled
      />

      <q-separator class="q-mt-md" color="white" />

      <q-input
        :disable="!token"
        label="Введіть новий пароль (мінімум 8 символів)"
        label-color="white"
        v-model="newPassword"
        type="password"
        autocomplete="new-password"
        :rules="[(v: string) => !v || v.length >= MIN_PASSWORD_LENGTH || 'Мінімум 8 символів']"
        filled
      />

      <div class="row justify-between q-mt-sm">
        <q-btn
          @click="updatePassword"
          color="positive"
          size="xs"
          :disable="!token || !oldPassword || newPassword.length < MIN_PASSWORD_LENGTH"
          :loading="saving"
          label="Зберегти"
        />

        <q-btn @click="close" size="xs" color="black" :disable="!token" label="Скасувати" />
      </div>
    </div>
  </q-dialog>
</template>

<script setup lang="ts">
import { useSessionStorage } from 'src/helpers/utils';
import { ref, watch } from 'vue';
import { useQuasar } from 'quasar';
import { api } from '../../axios-instance';

const $q = useQuasar();
const token = useSessionStorage('access_token');

interface Props {
  show: boolean;
}

const props = defineProps<Props>();
const MIN_PASSWORD_LENGTH = 8;
const oldPassword = ref('');
const newPassword = ref('');
const saving = ref(false);

const emits = defineEmits<{
  (e: 'update:show', value: boolean): void;
}>();
const localShow = ref(props.show);

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
}

async function updatePassword() {
  saving.value = true;
  try {
    const response = await api.post('/api/change-password', {
      old_password: oldPassword.value,
      new_password: newPassword.value,
    });
    const json = response.data;
    $q.notify({
      message: json?.message,
      color: 'info',
      icon: 'info',
      position: 'top',
      timeout: 2000,
    });
    close();
  } catch (error: any) {
    console.error('Error changing password:', error);
    const detail = error?.response?.data?.detail;
    $q.notify({
      message: typeof detail === 'string' ? detail : 'Не вдалося змінити пароль',
      color: 'red',
      icon: 'warning',
      position: 'top',
      timeout: 3000,
    });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped lang="scss">
.dialog-body {
  padding: 20px;
  gap: 10px;
  background: #1e1f26;
}
</style>
