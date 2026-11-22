<template>
  <q-dialog v-model="localShow">
    <div class="column dialog-body q-gutter-y-sm">
      <h6 class="q-my-none">Пороги сповіщень</h6>
      <p class="text-caption q-mb-none">
        Оберіть хімію батареї та кількість комірок, щоб підставити типові значення, або налаштуйте вручну.
        Значення одразу використовуються в текстах алертів.
      </p>

      <template v-if="form">
        <div class="row q-col-gutter-sm items-end">
          <q-select v-model="preset" class="col-6" dark filled dense label="Хімія" :options="['LiFePO4', 'Li-ion', 'LTO']" />
          <q-input v-model.number="cellCount" class="col-3" dark filled dense type="number" min="1" max="32" label="Комірок" />
          <div class="col-3">
            <q-btn class="full-width" color="black" label="Застосувати" :disable="!canEdit" @click="applyPreset" />
          </div>
        </div>
        <div class="text-caption text-grey-5">Поточний набір: {{ form.chemistry }} · {{ form.cell_count }}S</div>

        <div v-for="group in GROUPS" :key="group.title" class="group">
          <div class="text-subtitle2">{{ group.title }}</div>
          <div class="row q-col-gutter-xs">
            <q-input
              v-for="field in group.fields"
              :key="field.key"
              v-model.number="(form as any)[field.key]"
              class="col-6"
              dark
              filled
              dense
              type="number"
              :step="field.step || 1"
              :label="field.label"
              :disable="!canEdit"
            >
              <template #append>
                <q-checkbox
                  v-if="field.code"
                  :model-value="!form.disabled_codes.includes(field.code)"
                  dense
                  size="xs"
                  :disable="!canEdit"
                  @update:model-value="(on: boolean) => toggleCode(field.code!, on)"
                >
                  <q-tooltip>Алерт {{ field.code }} {{ form.disabled_codes.includes(field.code) ? 'вимкнено' : 'увімкнено' }}</q-tooltip>
                </q-checkbox>
              </template>
            </q-input>
          </div>
        </div>
      </template>

      <div class="row justify-between q-mt-sm">
        <q-btn color="positive" size="sm" label="Зберегти" :loading="saving" :disable="!canEdit || !form" @click="save" />
        <q-btn color="black" size="sm" label="Закрити" @click="localShow = false" />
      </div>
    </div>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { useAuth } from 'src/helpers/utils';

type Thresholds = Record<string, any> & { chemistry: string; cell_count: number; disabled_codes: number[] };

interface Field {
  key: string;
  label: string;
  step?: number;
  code?: number;
}

const GROUPS: { title: string; fields: Field[] }[] = [
  { title: 'Рівень заряду (SOC), %', fields: [
    { key: 'soc_critical', label: 'Критичний', code: 1001 },
    { key: 'soc_error', label: 'Низький', code: 1002 },
    { key: 'soc_warning_no_charge', label: 'Без заряджання', code: 1003 },
  ] },
  { title: 'Розбаланс комірок, V', fields: [
    { key: 'cell_diff_error', label: 'Помилка', step: 0.005, code: 1005 },
    { key: 'cell_diff_critical', label: 'Критично', step: 0.005, code: 1004 },
  ] },
  { title: 'Середня напруга комірки, V', fields: [
    { key: 'avg_cell_low_critical', label: 'Мін. критично', step: 0.01, code: 1006 },
    { key: 'avg_cell_low_error', label: 'Мін. помилка', step: 0.01, code: 1007 },
    { key: 'avg_cell_high_error', label: 'Макс. помилка', step: 0.01, code: 1009 },
    { key: 'avg_cell_high_critical', label: 'Макс. критично', step: 0.01, code: 1008 },
  ] },
  { title: 'Напруга батареї, V', fields: [
    { key: 'pack_low_critical', label: 'Мін. критично', step: 0.1, code: 1022 },
    { key: 'pack_low_error', label: 'Мін. помилка', step: 0.1, code: 1023 },
    { key: 'pack_high_error', label: 'Макс. помилка', step: 0.1, code: 1021 },
    { key: 'pack_high_critical', label: 'Макс. критично', step: 0.1, code: 1020 },
  ] },
  { title: 'Температура, °C', fields: [
    { key: 'temp_error', label: 'Помилка', code: 1011 },
    { key: 'temp_critical', label: 'Критично', code: 1010 },
  ] },
  { title: 'Струм, A', fields: [
    { key: 'charge_current_error', label: 'Заряд: помилка', code: 1013 },
    { key: 'charge_current_critical', label: 'Заряд: критично', code: 1012 },
    { key: 'discharge_current_error', label: 'Розряд: помилка', code: 1015 },
    { key: 'discharge_current_critical', label: 'Розряд: критично', code: 1014 },
  ] },
  { title: 'Стан і ресурс', fields: [
    { key: 'soh_error', label: 'SOH помилка, %', code: 1016 },
    { key: 'soh_critical', label: 'SOH критично, %', code: 1017 },
    { key: 'resistance_error', label: 'Опір: помилка, Ом', step: 0.05, code: 1019 },
    { key: 'resistance_critical', label: 'Опір: критично, Ом', step: 0.05, code: 1018 },
    { key: 'cycles_warning', label: 'Цикли: увага', step: 100, code: 1027 },
    { key: 'cycles_high', label: 'Цикли: багато', step: 100, code: 1026 },
    { key: 'emergency_error_min', label: 'Аварія: помилка, хв', code: 1025 },
    { key: 'emergency_critical_min', label: 'Аварія: критично, хв', code: 1024 },
  ] },
];

const props = defineProps<{ show: boolean; detectedCellCount?: number | undefined }>();
const emits = defineEmits<{ (e: 'update:show', value: boolean): void }>();
const { isAdmin: canEdit } = useAuth();

const localShow = ref(props.show);
const form = ref<Thresholds>();
const preset = ref('LiFePO4');
const cellCount = ref(16);
const saving = ref(false);

watch(() => props.show, (v) => (localShow.value = v));
watch(localShow, async (v) => {
  emits('update:show', v);
  if (v) await load();
});

async function load() {
  try {
    form.value = (await api.get('/api/alert-thresholds')).data;
    preset.value = form.value!.chemistry === 'custom' ? 'LiFePO4' : form.value!.chemistry;
    cellCount.value = props.detectedCellCount || form.value!.cell_count || 16;
  } catch (error) {
    console.error(error);
  }
}

async function applyPreset() {
  const presets = (await api.get('/api/alert-thresholds/presets', { params: { cell_count: cellCount.value } })).data;
  form.value = { ...presets[preset.value], disabled_codes: form.value?.disabled_codes || [] };
}

function toggleCode(code: number, on: boolean) {
  if (!form.value) return;
  const codes = new Set(form.value.disabled_codes);
  if (on) codes.delete(code);
  else codes.add(code);
  form.value.disabled_codes = [...codes].sort();
}

async function save() {
  saving.value = true;
  try {
    form.value = (await api.put('/api/alert-thresholds', form.value)).data;
    Notify.create({ message: 'Пороги збережено', color: 'positive', position: 'top' });
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    const message = Array.isArray(detail) ? detail.map((d: any) => d.msg).join('; ') : detail;
    Notify.create({ message: message || 'Не вдалося зберегти', color: 'red', position: 'top', timeout: 6000 });
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped lang="scss">
.dialog-body {
  padding: 20px;
  background: #1e1f26;
  color: white;
  max-width: 560px;
  width: 100%;
}
.group {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 6px;
}
</style>
