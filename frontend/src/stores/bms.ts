import { AxiosResponse } from 'axios';
import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { sortDevices } from 'src/helpers/utils';
import { CellInfo, Device, DeviceInfo, SettingInfo } from 'src/models';
import { ref } from 'vue';

export const useBmsStore = defineStore('bms', () => {
  // ==============
  //   STATE
  // ==============
  const cellInfo = ref<Record<string, CellInfo>>({});
  const deviceInfo = ref<DeviceInfo[]>([]);
  const settings = ref<SettingInfo[]>([]);
  const devices = ref<Device[]>([]);

  // ==============
  //   MUTATIONS
  // ==============
  function updateCellInfo(newInfo: Record<string, CellInfo>): void {
    cellInfo.value = newInfo;
  }

  function updateDeviceInfo(newInfo: DeviceInfo[]): void {
    deviceInfo.value = newInfo;
  }

  function updateSettings(newSettings: SettingInfo[]): void {
    settings.value = newSettings;
  }

  function updateDevices(newDevices: Device[]) {
    devices.value = newDevices;
  }

  // ==============
  //   ACTIONS
  // ==============
  async function fetchSettings(): Promise<void> {
    try {
      const response = await api.get('/api/device-settings');
      const data: SettingInfo[] = response.data;
      settings.value = data;
    } catch (error) {
      console.error('Error fetching device settings:', error);
    }
  }

  async function fetchCellInfo(): Promise<void> {
    try {
      const response = await api.get('/api/cell-info');
      const data = response.data;
      cellInfo.value = data;
    } catch (error) {
      console.error('Error fetching cell info:', error);
    }
  }

  async function fetchDeviceInfo(connected: boolean): Promise<void> {
    try {
      const response = await api.get('/api/device-info');
      const data: DeviceInfo[] = await response.data;
      if (connected) {
        deviceInfo.value = sortDevices(data.filter((d: any) => d.connected));
      } else {
        deviceInfo.value = sortDevices(data);
      }
    } catch (error) {
      console.error('Error fetching device info:', error);
    }
  }

  async function connectToDevice(address: string, name: string): Promise<AxiosResponse<any, any>> {
    return await api.post('/api/connect-device', { address, name });
  }

  async function disconnectDevice(address: string, name: string) {
    try {
      await api.post('/api/disconnect-device', { address, name });
    } catch (error: any) {
      throw new Error('Error disconnect device info:', error);
    }
  }

  async function fetchDevices(): Promise<Device[] | undefined> {
    try {
      const response = await api.get('/api/devices');
      const data = await response.data;
      updateDevices(data?.devices);
      return devices.value;
    } catch (error) {
      console.error(error);
    }
  }

  return {
    // ==============
    //   GETTERS
    // ==============
    devices,
    cellInfo,
    deviceInfo,
    settings,

    // ==============
    //   MUTATIONS
    // ==============
    updateCellInfo,
    updateDeviceInfo,
    updateSettings,
    updateDevices,

    // ==============
    //   ACTIONS
    // ==============
    fetchSettings,
    fetchCellInfo,
    fetchDeviceInfo,
    fetchDevices,
    connectToDevice,
    disconnectDevice,
  };
});
