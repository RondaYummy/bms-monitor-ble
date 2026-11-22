<template>
  <q-expansion-item
    v-model="open"
    switch-toggle-side
    expand-separator
    label="Прогноз батареї"
    caption="Автономність за історією та дисбаланс комірок"
    class="analytics full-width"
  >
    <div v-if="loading && !data" class="q-pa-md text-center"><q-spinner color="white" /></div>

    <div v-else-if="data" class="q-pa-sm column q-gutter-y-sm">
      <div class="row q-col-gutter-sm">
        <div class="col-12 col-sm-4">
          <div class="tile">
            <div class="tile-label">За поточним навантаженням</div>
            <div class="tile-value">{{ fmt(runtime.by_current_load_min) }}</div>
            <div class="tile-hint">Струм зараз: {{ runtime.current_now_a }} A</div>
          </div>
        </div>
        <div class="col-12 col-sm-4">
          <div class="tile" :class="{ ok: runtime.self_sufficient }">
            <div class="tile-label">За звичним профілем (з сонцем)</div>
            <div class="tile-value">
              {{ runtime.self_sufficient ? 'Не розрядиться' : fmt(runtime.by_profile_min) }}
            </div>
            <div class="tile-hint">
              до {{ runtime.reserve_soc }}%: {{ runtime.self_sufficient ? '—' : fmt(runtime.by_profile_to_reserve_min) }}
            </div>
          </div>
        </div>
        <div class="col-12 col-sm-4">
          <div class="tile">
            <div class="tile-label">Відключення (без сонця й мережі)</div>
            <div class="tile-value">{{ fmt(runtime.no_charge_min) }}</div>
            <div class="tile-hint">
              до {{ runtime.reserve_soc }}%: {{ fmt(runtime.no_charge_to_reserve_min) }} ·
              {{ runtime.no_charge_source === 'load' ? 'за споживанням будинку' : 'за середнім розрядом' }}
            </div>
          </div>
        </div>
      </div>

      <div v-if="runtime.max_soc_today !== null && runtime.max_soc_today !== undefined" class="outlook">
        <template v-if="runtime.full_at">🔋 Батарея зарядиться до 100% приблизно о <b>{{ runtime.full_at.slice(11, 16) }}</b></template>
        <template v-else>🔋 Сьогодні заряд дійде максимум до <b>{{ Math.round(runtime.max_soc_today) }}%</b></template>
        <span v-if="runtime.solar_used" class="text-amber-4"> · ☀️ з прогнозом сонця</span>
      </div>

      <div class="text-caption text-grey-4">
        Точність: <b :class="confidenceClass">{{ confidenceLabel }}</b>
        <span v-if="runtime.accuracy?.mae_soc_pct !== undefined && runtime.accuracy?.mae_soc_pct !== null">
          · похибка ±{{ runtime.accuracy.mae_soc_pct }}% SOC на 12 год (перевірено на останніх 3 днях)
        </span>
        <span v-else> · ще мало історії для перевірки ({{ Math.round(runtime.history_hours / 24) }} дн.)</span>
        <q-tooltip max-width="340px">
          Прогноз моделює заряд кожні 5 хвилин: профіль струму батареї за годинами доби (свіжі дні важать
          більше), а на найближчу годину — реальний струм зараз. Кілька варіантів моделі перевіряються на
          ваших даних за останні дні, і використовується найточніший ({{ runtime.model }}).
          «Відключення» — споживання будинку з інвертора без сонця й мережі.
        </q-tooltip>
      </div>

      <div class="profile row no-wrap items-end" aria-label="Середній струм за годинами доби">
        <div
          v-for="(value, hour) in runtime.profile"
          :key="hour"
          class="bar"
          :class="(value ?? 0) >= 0 ? 'bar-charge' : 'bar-discharge'"
          :style="{ height: barHeight(value) }"
        >
          <q-tooltip>{{ hour }}:00 — {{ value ?? 'немає даних' }} A</q-tooltip>
        </div>
      </div>
      <div class="row justify-between text-caption text-grey-6"><span>0:00</span><span>12:00</span><span>23:00</span></div>

      <q-separator color="grey-8" />

      <div class="text-subtitle2 text-white">Дисбаланс комірок</div>
      <div v-if="!data.imbalance.length" class="text-caption text-grey-5">
        Ще немає історії різниці напруг (збирається з цієї версії, потрібно ≥ 3 дні).
      </div>
      <div v-for="item in data.imbalance" :key="item.device_address" class="imbalance">
        <div class="row justify-between items-center">
          <b>{{ item.device_name }}</b>
          <span :class="trendClass(item)">{{ trendLabel(item) }}</span>
        </div>
        <div class="text-caption text-grey-4">
          Зараз: {{ mv(item.current_diff) }} · тренд: {{ item.slope_mv_per_day ?? '—' }} мВ/день
        </div>
        <div v-if="item.trend === 'rising'" class="text-caption">
          До {{ mv(item.error_threshold) }}:
          <b>{{ days(item.days_to_error) }}</b>,
          до {{ mv(item.critical_threshold) }}: <b>{{ days(item.days_to_critical) }}</b>
        </div>
      </div>
    </div>
  </q-expansion-item>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { api } from 'src/axios-instance';
import { formatMinutes } from 'src/helpers/utils';

interface Imbalance {
  device_address: string;
  device_name: string;
  current_diff: number | null;
  trend: 'rising' | 'falling' | 'stable' | 'unknown';
  slope_mv_per_day: number | null;
  days_to_error: number | null;
  days_to_critical: number | null;
  error_threshold: number;
  critical_threshold: number;
}

interface Analytics {
  runtime: {
    by_current_load_min: number | null;
    by_profile_min: number | null;
    by_profile_to_reserve_min: number | null;
    no_charge_min: number | null;
    no_charge_to_reserve_min: number | null;
    no_charge_source: 'load' | 'bms' | null;
    avg_discharge_a: number | null;
    model: string;
    solar_used: boolean;
    max_soc_today: number | null;
    full_at: string | null;
    accuracy: { mae_soc_pct: number | null; points: number } | null;
    current_now_a: number;
    reserve_soc: number;
    history_hours: number;
    confidence: 'low' | 'medium' | 'high';
    profile: (number | null)[];
    self_sufficient: boolean;
  };
  imbalance: Imbalance[];
}

const open = ref(false);
const loading = ref(false);
const data = ref<Analytics>();
let timer: ReturnType<typeof setInterval> | undefined;

const runtime = computed(() => data.value!.runtime);
const confidenceLabel = computed(
  () => ({ low: 'низька', medium: 'середня', high: 'висока' })[runtime.value.confidence]
);
const confidenceClass = computed(
  () => ({ low: 'text-orange', medium: 'text-yellow', high: 'text-green' })[runtime.value.confidence]
);
const maxAbs = computed(() =>
  Math.max(1, ...runtime.value.profile.map((v) => Math.abs(v ?? 0)))
);

function fmt(minutes: number | null | undefined) {
  if (minutes === null || minutes === undefined) return '—';
  return formatMinutes(minutes);
}
function barHeight(value: number | null) {
  return `${Math.max(4, (Math.abs(value ?? 0) / maxAbs.value) * 48)}px`;
}
function mv(value: number | null) {
  return value === null || value === undefined ? '—' : `${Math.round(value * 1000)} мВ`;
}
function days(value: number | null) {
  if (value === null) return '—';
  return value <= 0 ? 'вже перевищено' : `~${value} дн.`;
}
function trendLabel(item: Imbalance) {
  return { rising: '↗ зростає', falling: '↘ зменшується', stable: '→ стабільний', unknown: 'мало даних' }[item.trend];
}
function trendClass(item: Imbalance) {
  if (item.trend !== 'rising') return 'text-green';
  return (item.days_to_error ?? 99) < 14 ? 'text-red' : 'text-orange';
}

async function load() {
  if (document.hidden) return;
  loading.value = true;
  try {
    data.value = (await api.get('/api/analytics/battery', { timeout: 15000 })).data;
  } catch (error) {
    console.error('Error loading battery analytics:', error);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void load();
  timer = setInterval(load, 5 * 60 * 1000);
});
onBeforeUnmount(() => clearInterval(timer));
</script>

<style scoped lang="scss">
.analytics {
  color: white;
}
.tile {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 8px 10px;
  height: 100%;
  &.ok {
    background: rgba(76, 175, 80, 0.15);
  }
}
.tile-label {
  font-size: 0.75em;
  color: #bdbdbd;
}
.tile-value {
  font-size: 1.35em;
  font-weight: 700;
}
.tile-hint {
  font-size: 0.75em;
  color: #9e9e9e;
}
.profile {
  height: 52px;
  gap: 2px;
}
.bar {
  flex: 1;
  border-radius: 2px 2px 0 0;
}
.bar-charge {
  background: #4caf50;
}
.bar-discharge {
  background: #ff9800;
}
.outlook {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 6px 10px;
}
.imbalance {
  background: rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 6px 8px;
}
</style>
