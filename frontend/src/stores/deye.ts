import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { DeyeRealtimeData } from 'src/models';
import { readonly, ref } from 'vue';

const config = {
  timeout: 6000,
};

const data: DeyeRealtimeData[] = [
  {
    id: 1,
    ip: "192.168.1.10",
    serial_number: "DEYE123456789",
    slave_id: 1,
    timestamp: "2026-04-13T10:00:00Z",
    pv1_power: 1200,
    pv2_power: 1300,
    total_pv: 2500,
    load_power: 1800,
    grid_power: 200,
    battery_power: -300,
    battery_voltage: 48.5,
    battery_soc: 75,
    net_balance: 400,
    device_on: 1,
    stat_daily_pv: 15.2,
    stat_total_pv: 12450.7,
    stat_daily_bat_discharge: 5.1,
    stat_daily_grid_in: 3.4,
    stat_daily_grid_out: 2.8,
    stat_total_grid_out: 8420.3,
    stat_total_load: 15890.6,
  },
  {
    id: 2,
    ip: "192.168.1.11",
    serial_number: "DEYE987654321",
    slave_id: 1,
    timestamp: "2026-04-13T10:05:00Z",
    pv1_power: 900,
    pv2_power: 1100,
    total_pv: 2000,
    load_power: 1500,
    grid_power: -100,
    battery_power: 200,
    battery_voltage: 47.8,
    battery_soc: 60,
    net_balance: 300,
    device_on: 1,
    stat_daily_pv: 12.7,
    stat_total_pv: 9870.4,
    stat_daily_bat_discharge: 4.3,
    stat_daily_grid_in: 2.1,
    stat_daily_grid_out: 3.6,
    stat_total_grid_out: 7650.2,
    stat_total_load: 13450.9,
  }
];

export const useDeyeStore = defineStore('deye', () => {
  // ==============
  //   STATE
  // ==============
  const deyeData = ref<DeyeRealtimeData[]>(data);

  // ==============
  //   GETTERS
  // ==============
  function getDeyeData(): DeyeRealtimeData[] {
    return deyeData.value;
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateDeyeData(newDeyeData: DeyeRealtimeData[]) {
    deyeData.value = newDeyeData;
  }

  // ==============
  //   ACTIONS
  // ==============
  async function fetchDeyeDevices(): Promise<DeyeRealtimeData[] | undefined> {
    try {
      const response = await api.get('/api/deye/devices', config);
      const data = await response.data;
      updateDeyeData(data);
      return deyeData.value;
    } catch (error) {
      console.error('Error Deye data: ', error);
    }
  }

  async function createDeyeDevice(data: {
    ip: string;
    serial_number: string;
    slave_id?: number;
  }): Promise<DeyeRealtimeData[] | undefined> {
    try {
      const response = await api.post('/api/deye/device', data);
      const devices = await response.data;
      updateDeyeData(devices);
      return deyeData.value;
    } catch (error) {
      console.error('Error create Deye: ', error);
    }
  }

  async function deleteDeyeDevice(ip: string): Promise<void> {
    try {
      await api.delete(`/api/deye/device?ip=${ip}`, config);
      await fetchDeyeDevices();
    } catch (error) {
      console.error('Error delete Deye: ', error);
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get deyeData() {
      return readonly(deyeData);
    },

    // ==============
    //   GETTERS
    // ==============
    getDeyeData,

    // ==============
    //   MUTATIONS
    // ==============
    updateDeyeData,

    // ==============
    //   ACTIONS
    // ==============
    fetchDeyeDevices,
    createDeyeDevice,
    deleteDeyeDevice,
  };
});
