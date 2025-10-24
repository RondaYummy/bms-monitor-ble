import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { DeyeRealtimeData } from 'src/models';
import { readonly, ref } from 'vue';

const config = {
  timeout: 4000,
};

export const useDeyeStore = defineStore('deye', () => {
  // ==============
  //   STATE
  // ==============
  const deyeData = ref<DeyeRealtimeData[]>([]);

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
      const response = await api.post('/api/deye/device', data, config);
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
