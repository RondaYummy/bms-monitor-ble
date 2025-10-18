import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { DeyeRealtimeData } from 'src/models';
import { readonly, ref } from 'vue';

export interface DisabledDeviceInfo {
  ip: string;
  off_since: number;
  power_w: number;
  duration_s: number;
  last_action: number;
}

export interface PowerManagerStatus {
  devices: DisabledDeviceInfo[];
  threshold: number;
  MIN_TOGGLE_INTERVAL_S: number;
  POLL_INTERVAL_S: number;
}

export const usePowerStore = defineStore('power', () => {
  // ==============
  //   STATE
  // ==============
  const data = ref<PowerManagerStatus>();

  // ==============
  //   GETTERS
  // ==============
  function getPowerData() {
    return data.value;
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updatePowerData(newDeyeData: PowerManagerStatus) {
    data.value = newDeyeData;
  }

  // ==============
  //   ACTIONS
  // ==============
  async function fetchPowerData(): Promise<DeyeRealtimeData[] | undefined> {
    try {
      const response = await api.get('/api/power/system');
      const data = await response.data;
      updatePowerData(data);
      return data.value;
    } catch (error) {
      console.error('Error getting power system data: ', error);
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get powerData() {
      return readonly(data);
    },

    // ==============
    //   GETTERS
    // ==============
    getPowerData,

    // ==============
    //   MUTATIONS
    // ==============
    updatePowerData,

    // ==============
    //   ACTIONS
    // ==============
    fetchPowerData,
  };
});
