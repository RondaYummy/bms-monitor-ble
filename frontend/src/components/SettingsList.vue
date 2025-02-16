<template>
  <q-list padding
          bordered
          class="rounded-borders">
    <q-expansion-item dense
                      dense-toggle
                      expand-separator
                      icon="perm_identity"
                      label="Base Settings">
      <q-card>
        <q-card-section style="background: transparent;">
          Base Settings

          <div class="row justify-between items-center">
            <span>Cell count:</span>

            <q-input outlined
                     v-model="st.cell_count"
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
      <q-card style="background: transparent;">
        <q-card-section>
          Advance Settings
        </q-card-section>
      </q-card>
    </q-expansion-item>

    <q-expansion-item dense
                      dense-toggle
                      expand-separator
                      icon="drafts"
                      label="Con. Wire Res. Settings"
                      header-class="text-purple">
      <q-card style="background: transparent;">
        <q-card-section>
          Con. Wire Res. Settings
        </q-card-section>
      </q-card>
    </q-expansion-item>
  </q-list>
</template>

<script lang="ts" setup>
import type { SettingInfo } from 'src/models';
import { ref, watch } from 'vue';

const defaultSettings: SettingInfo = {
  name: "",
  address: "",
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

watch(() => props.settings, (newValue) => {
  st.value = newValue;
});
</script>
