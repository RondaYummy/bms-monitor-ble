import { computed } from 'vue';
import type { DeyeSafeValues } from 'src/models';
import { useDeyeStore } from 'src/stores/deye';

/** Sum of all Deye inverters (dashboard gauges and the Statistics page). */
export function useDeyeTotals() {
  const deyeStore = useDeyeStore();
  return computed<DeyeSafeValues>(() => {
    const data = deyeStore.getDeyeData();
    const initial: DeyeSafeValues = {
      pv1_power: 0,
      pv2_power: 0,
      total_pv: 0,
      load_power: 0,
      grid_power: 0,
      battery_power: 0,
      battery_voltage: 0,
      battery_soc: 0,
      net_balance: 0,
      stat_daily_pv: 0,
      stat_total_pv: 0,
      stat_daily_bat_discharge: 0,
      stat_daily_grid_in: 0,
      stat_daily_grid_out: 0,
      stat_total_grid_out: 0,
      stat_total_load: 0,
      daily_bat_charge: 0,
      daily_load: 0,
      grid_in: 0,
      total_bat_charge: 0,
      total_bat_discharge: 0,
    };
  
    if (!Array.isArray(data)) return initial;
    return data.reduce((acc, curr) => {
      acc.battery_voltage += Number(curr.battery_voltage) || 0;
      acc.pv1_power += Number(curr.pv1_power) || 0;
      acc.pv2_power += Number(curr.pv2_power) || 0;
      acc.total_pv += Number(curr.total_pv) || 0;
      acc.load_power += Number(curr.load_power) || 0;
      acc.grid_power += Number(curr.grid_power) || 0;
      acc.battery_power += Number(curr.battery_power) || 0;
      acc.battery_soc += Number(curr.battery_soc) || 0;
      acc.net_balance += Number(curr.net_balance) || 0;
      acc.stat_daily_pv += Number(curr.stat_daily_pv) || 0;
      acc.stat_total_pv += Number(curr.stat_total_pv) || 0;
      acc.stat_daily_bat_discharge += Number(curr.stat_daily_bat_discharge) || 0;
      acc.stat_daily_grid_in += Number(curr.stat_daily_grid_in) || 0;
      acc.stat_daily_grid_out += Number(curr.stat_daily_grid_out) || 0;
      acc.stat_total_grid_out += Number(curr.stat_total_grid_out) || 0;
      acc.stat_total_load += Number(curr.stat_total_load) || 0;
      return acc;
    }, initial);
  });;
}
