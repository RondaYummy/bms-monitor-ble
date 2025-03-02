<template>
  <q-list bordered
          class="rounded-borders">
    <q-expansion-item dense
                      dense-toggle
                      expand-separator
                      icon="perm_identity"
                      label="Base Settings">
      <q-card style="background: transparent">
        <q-card-section class="column"
                        style="background: transparent">
          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>{{ getUnit('cell_count') }}</span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_count"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('nominal_battery_capacity') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.nominal_battery_capacity"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('balance_trigger_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.balance_trigger_voltage"
                     dense />
          </div>
        </q-card-section>
      </q-card>
    </q-expansion-item>

    <q-expansion-item dense
                      dense-toggle
                      expand-separator
                      icon="signal_wifi_off"
                      header-class="text-orange"
                      label="Advance Settings">
      <q-card style="background: transparent">
        <q-card-section class="column">
          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('start_balance_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.start_balance_voltage"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('max_balance_current') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.max_balance_current"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('cell_ovp') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_ovp"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('cell_request_charge_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_request_charge_voltage"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('soc_100_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.soc_100_voltage"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('cell_ovpr') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_ovpr"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('cell_uvpr') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_uvpr"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('cell_uvp') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_uvp"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('power_off_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.power_off_voltage"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('cell_request_float_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.cell_request_float_voltage"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('smart_sleep_voltage') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.smart_sleep_voltage"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('max_charge_current') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.max_charge_current"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('charge_ocp_delay') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.charge_ocp_delay"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('charge_ocp_recovery') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.charge_ocp_recovery"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('max_discharge_current') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.max_discharge_current"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('discharge_ocp_delay') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.discharge_ocp_delay"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('discharge_ocp_recovery') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.discharge_ocp_recovery"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('charge_otp') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.charge_otp"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('charge_otp_recovery') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.charge_otp_recovery"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('discharge_otp') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.discharge_otp"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('discharge_otp_recovery') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.discharge_otp_recovery"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('charge_utp') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.charge_utp"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('mos_otp') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.mos_otp"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('mos_otp_recovery') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.mos_otp_recovery"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('short_circuit_protection_delay') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.short_circuit_protection_delay"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('short_circuit_protection_recovery') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.short_circuit_protection_recovery"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('device_address') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.device_address"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('port_switch') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.port_switch"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('precharge_time') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.precharge_time"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('data_field_enable_control') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.data_field_enable_control"
                     dense />
          </div>

          <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('controls_bitmask') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.controls_bitmask"
                     dense />
          </div>
        </q-card-section>
      </q-card>
    </q-expansion-item>

    <q-expansion-item dense
                      dense-toggle
                      expand-separator
                      icon="drafts"
                      label="Con. Wire Res. Settings"
                      header-class="text-purple">
      <q-card style="background: transparent">
        <q-card-section>
          Con. Wire Res. Settings
          <!-- <div class="row q-gutter-x-md justify-between items-center custom">
            <span>
              {{ getUnit('connection_wire_resistances') }}
            </span>

            <q-input :readonly="readonlyInputs"
                     outlined
                     v-model="st.connection_wire_resistances"
                     dense />
          </div> -->
        </q-card-section>
      </q-card>
    </q-expansion-item>
  </q-list>
</template>

<script lang="ts" setup>
import { getUnit } from 'src/helpers/utils';
import type { SettingInfo } from 'src/models';
import { ref, watch } from 'vue';

const defaultSettings: SettingInfo = {
  name: '',
  address: '',
  cell_count: 0,
  nominal_battery_capacity: 0,
  balance_trigger_voltage: 0,
  start_balance_voltage: 0,
  max_balance_current: 0,
  cell_ovp: 0,
  cell_request_charge_voltage: 0,
  soc_100_voltage: 0,
  cell_ovpr: 0,
  cell_uvpr: 0,
  soc_0_voltage: 0,
  cell_uvp: 0,
  power_off_voltage: 0,
  cell_request_float_voltage: 0,
  smart_sleep_voltage: 0,
  smart_sleep: false,
  max_charge_current: 0,
  charge_ocp_delay: 0,
  charge_ocp_recovery: 0,
  max_discharge_current: 0,
  discharge_ocp_delay: 0,
  discharge_ocp_recovery: 0,
  charge_otp: 0,
  charge_otp_recovery: 0,
  discharge_otp: 0,
  discharge_otp_recovery: 0,
  charge_utp_recovery: 0,
  charge_utp: 0,
  mos_otp: 0,
  mos_otp_recovery: 0,
  short_circuit_protection_delay: 0,
  short_circuit_protection_recovery: 0,
  device_address: 0,
  connection_wire_resistances: [],
  charge_switch: false,
  discharge_switch: false,
  balancer_switch: false,
  heating_enabled: null,
  disable_temperature_sensors: null,
  display_always_on: null,
  special_charger: null,
  timed_stored_data: null,
  charging_float_mode: null,
  gps_heartbeat: null,
  disable_pcl_module: null,
  port_switch: null,
  precharge_time: 0,
  data_field_enable_control: 0,
  controls_bitmask: 0,
};

const props = defineProps<{ settings: SettingInfo; }>();
const st = ref<SettingInfo>(defaultSettings);
const readonlyInputs = ref(true);

watch(
  () => props.settings,
  (newValue) => {
    st.value = newValue;
  },
  { deep: true, immediate: true },
);
</script>

<style scoped lang="scss">
.q-input {
  max-width: 55px;
}

.q-input:focus-within {
  border: 2px solid green !important;
  box-shadow: 0 0 8px hsla(120, 100%, 25%, 0.6);
  border-radius: 4px;
}

.custom:focus-within span {
  color: green;
}

.custom {
  margin: 5px 0px;
  flex-wrap: nowrap;
}
</style>
