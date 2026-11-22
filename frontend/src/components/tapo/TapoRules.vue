<template>
  <div class="rules">
    <div class="row items-center justify-between q-mb-sm">
      <div class="text-h6">📅 Розклад</div>
      <q-btn
        v-if="canEdit"
        dense
        color="green-8"
        icon="add"
        label="Правило"
        :disable="!devices.length"
        @click="openEditor()"
      />
    </div>
    <p class="text-caption text-grey-5 text-left">
      Наприклад: «вмикати бойлер з 11:00 до 15:00, якщо SOC &gt; 70% і генерація &gt; 2 кВт».
      Умови перевіряються кожні 20 с з гістерезисом. Розклад вимикає лише ті розетки, які сам увімкнув;
      ручне керування розеткою призупиняє її правила до кінця вікна.
    </p>

    <div v-if="!rules.length" class="text-grey-5 q-pa-sm">Правил ще немає.</div>

    <q-list dark separator class="rounded-borders">
      <q-item v-for="rule in rules" :key="rule.id" class="rule">
        <q-item-section avatar>
          <q-toggle
            :model-value="rule.enabled"
            :disable="!canEdit"
            color="positive"
            @update:model-value="(v: boolean) => toggle(rule, v)"
          />
        </q-item-section>
        <q-item-section class="text-left">
          <q-item-label>
            <b>{{ rule.name || 'Правило' }}</b> · {{ deviceName(rule.ip) }}
          </q-item-label>
          <q-item-label caption class="text-grey-4">
            {{ rule.start_time }}–{{ rule.end_time }} · {{ daysLabel(rule.days) }}
            <span v-if="rule.min_soc !== null"> · SOC ≥ {{ rule.min_soc }}%</span>
            <span v-if="rule.min_pv_w !== null"> · PV ≥ {{ (rule.min_pv_w / 1000).toFixed(1) }} кВт</span>
          </q-item-label>
          <q-item-label caption :class="statusClass(rule)">
            <q-icon v-if="rule.engine_on" name="power" size="xs" /> {{ rule.status?.reason || 'Ще не перевірялось' }}
          </q-item-label>
        </q-item-section>
        <q-item-section v-if="canEdit" side>
          <div class="row no-wrap">
            <q-btn flat round dense icon="edit" color="white" @click="openEditor(rule)" />
            <q-btn flat round dense icon="delete" color="red" @click="remove(rule)" />
          </div>
        </q-item-section>
      </q-item>
    </q-list>

    <q-dialog v-model="editorOpen">
      <div class="column dialog-body q-gutter-y-sm">
        <h6 class="q-my-none">{{ form.id ? 'Редагувати правило' : 'Нове правило' }}</h6>
        <q-input v-model="form.name" dark filled dense label="Назва (необов'язково)" maxlength="64" />
        <q-select
          v-model="form.ip"
          dark
          filled
          dense
          emit-value
          map-options
          :disable="!!form.id"
          :options="devices.map((d) => ({ label: `${d.name || d.ip} (${d.ip})`, value: d.ip }))"
          label="Розетка"
        />
        <div class="row q-col-gutter-sm">
          <q-input v-model="form.start_time" class="col" dark filled dense type="time" label="Початок" />
          <q-input v-model="form.end_time" class="col" dark filled dense type="time" label="Кінець" />
        </div>
        <div class="row justify-between">
          <q-checkbox
            v-for="(label, index) in DAY_LABELS"
            :key="index"
            v-model="form.dayList"
            :val="String(index)"
            :label="label"
            dark
            dense
          />
        </div>
        <q-input
          v-model.number="form.min_soc"
          dark
          filled
          dense
          clearable
          type="number"
          min="0"
          max="100"
          label="Мінімальний SOC, % (порожньо = без умови)"
        />
        <q-input
          v-model.number="form.min_pv_kw"
          dark
          filled
          dense
          clearable
          type="number"
          min="0"
          step="0.1"
          label="Мінімальна генерація, кВт (порожньо = без умови)"
        />
        <q-toggle v-model="form.turn_off_at_end" dark color="positive" label="Вимикати після вікна / коли умови не виконуються" />
        <div class="row justify-between q-mt-sm">
          <q-btn color="positive" size="sm" label="Зберегти" :loading="saving" :disable="!formValid" @click="save" />
          <q-btn color="black" size="sm" label="Скасувати" @click="editorOpen = false" />
        </div>
      </div>
    </q-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Dialog, Notify } from 'quasar';
import { api } from 'src/axios-instance';
import { useAuth } from 'src/helpers/utils';
import { useTapoStore } from 'src/stores/tapo';

interface Rule {
  id: number;
  ip: string;
  name: string | null;
  enabled: boolean;
  start_time: string;
  end_time: string;
  days: string;
  min_soc: number | null;
  min_pv_w: number | null;
  turn_off_at_end: boolean;
  engine_on: boolean;
  paused: boolean;
  status: { window_active: boolean; conditions_ok: boolean; reason: string } | null;
}

const DAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд'];

const { isAdmin: canEdit } = useAuth();
const tapoStore = useTapoStore();
const devices = computed(() => tapoStore.devices);
const rules = ref<Rule[]>([]);
const editorOpen = ref(false);
const saving = ref(false);
const emptyForm = () => ({
  id: 0,
  name: '',
  ip: '',
  start_time: '11:00',
  end_time: '15:00',
  dayList: ['0', '1', '2', '3', '4', '5', '6'],
  min_soc: 70 as number | null,
  min_pv_kw: 2 as number | null,
  turn_off_at_end: true,
});
const form = ref(emptyForm());
let timer: ReturnType<typeof setInterval> | undefined;

const formValid = computed(
  () =>
    !!form.value.ip &&
    /^\d{2}:\d{2}$/.test(form.value.start_time) &&
    /^\d{2}:\d{2}$/.test(form.value.end_time) &&
    form.value.start_time !== form.value.end_time &&
    form.value.dayList.length > 0
);

function deviceName(ip: string) {
  return devices.value.find((d) => d.ip === ip)?.name || ip;
}
function daysLabel(days: string) {
  if (days.length === 7) return 'щодня';
  return days
    .split('')
    .map((d) => DAY_LABELS[Number(d)])
    .join(', ');
}
function statusClass(rule: Rule) {
  if (rule.engine_on) return 'text-green';
  if (rule.paused) return 'text-orange';
  if (rule.status?.window_active && !rule.status?.conditions_ok) return 'text-yellow';
  return 'text-grey-5';
}

async function load() {
  try {
    rules.value = (await api.get('/api/tapo/rules')).data;
  } catch (error) {
    console.error('Error loading Tapo rules:', error);
  }
}

function openEditor(rule?: Rule) {
  form.value = rule
    ? {
        id: rule.id,
        name: rule.name || '',
        ip: rule.ip,
        start_time: rule.start_time,
        end_time: rule.end_time,
        dayList: rule.days.split(''),
        min_soc: rule.min_soc,
        min_pv_kw: rule.min_pv_w === null ? null : rule.min_pv_w / 1000,
        turn_off_at_end: rule.turn_off_at_end,
      }
    : { ...emptyForm(), ip: devices.value[0]?.ip || '' };
  editorOpen.value = true;
}

function numberOrNull(value: unknown): number | null {
  return value === '' || value === null || value === undefined || Number.isNaN(Number(value)) ? null : Number(value);
}

async function save() {
  saving.value = true;
  const kw = numberOrNull(form.value.min_pv_kw);
  const payload = {
    name: form.value.name || null,
    start_time: form.value.start_time,
    end_time: form.value.end_time,
    days: [...form.value.dayList].sort().join(''),
    min_soc: numberOrNull(form.value.min_soc),
    min_pv_w: kw === null ? null : Math.round(kw * 1000),
    turn_off_at_end: form.value.turn_off_at_end,
  };
  try {
    if (form.value.id) {
      await api.patch(`/api/tapo/rules/${form.value.id}`, payload);
    } else {
      await api.post('/api/tapo/rules', { ...payload, ip: form.value.ip, enabled: true });
    }
    editorOpen.value = false;
    await load();
    Notify.create({ message: 'Правило збережено', color: 'positive', position: 'top' });
  } catch (error: any) {
    const detail = error?.response?.data?.detail;
    Notify.create({
      message: typeof detail === 'string' ? detail : 'Не вдалося зберегти правило',
      color: 'red',
      position: 'top',
    });
  } finally {
    saving.value = false;
  }
}

async function toggle(rule: Rule, enabled: boolean) {
  try {
    await api.patch(`/api/tapo/rules/${rule.id}`, { enabled });
    await load();
  } catch (error) {
    console.error(error);
  }
}

function remove(rule: Rule) {
  Dialog.create({
    title: 'Видалити правило?',
    message: `${rule.name || 'Правило'} для ${deviceName(rule.ip)}`,
    cancel: true,
    dark: true,
  }).onOk(async () => {
    await api.delete(`/api/tapo/rules/${rule.id}`);
    await load();
  });
}

onMounted(() => {
  void load();
  if (!devices.value.length) void tapoStore.fetchDevices();
  timer = setInterval(() => !document.hidden && load(), 20000);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<style scoped lang="scss">
.rules {
  color: white;
}
.rule {
  background: rgba(255, 255, 255, 0.04);
}
.dialog-body {
  padding: 20px;
  background: #1e1f26;
  color: white;
  min-width: 300px;
  max-width: 420px;
}
</style>
