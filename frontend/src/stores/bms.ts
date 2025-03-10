import { defineStore } from 'pinia';
import { Notify } from 'quasar';
import { api } from 'src/boot/axios';
import { sortDevices } from 'src/helpers/utils';
import { CellInfo, Device, DeviceInfo, SettingInfo } from 'src/models';
import { readonly, ref } from 'vue';

export const useBmsStore = defineStore('bms', () => {
  // ==============
  //   STATE
  // ==============
  const cellInfo = ref<Record<string, CellInfo>>({});
  const deviceInfo = ref<DeviceInfo[]>([]);
  const settingInfo = ref<SettingInfo[]>([]);
  const devices = ref<Device[]>([]);

  // ==============
  //   GETTERS
  // ==============
  function getDevices(): Device[] {
    return devices.value;
  }

  function getCellInfo(): Record<string, CellInfo> {
    return cellInfo.value;
  }

  function getDeviceInfo(): DeviceInfo[] {
    return deviceInfo.value;
  }

  function getSettingInfo(): SettingInfo[] {
    return settingInfo.value;
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateCellInfo(newInfo: Record<string, CellInfo>): void {
    cellInfo.value = newInfo;
  };

  function updateDeviceInfo(newInfo: DeviceInfo[]): void {
    deviceInfo.value = newInfo;
  }

  function updateSettings(newSettings: SettingInfo[]): void {
    settingInfo.value = newSettings;
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
      settingInfo.value = data;
    } catch (error) {
      console.error('Error fetching device settings: ', error);
    }
  }

  async function fetchCellInfo(): Promise<void> {
    try {
      const response = await api.get('/api/cell-info');
      const data = response.data;
      cellInfo.value = data;
    } catch (error) {
      console.error('Error fetching cell info: ', error);
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
      console.error('Error fetching device info: ', error);
    }
  }

  async function connectToDevice(address: string, name: string): Promise<void> {
    try {
      const res = await api.post('/api/connect-device', { address, name });
      if (res?.data?.error) {
        Notify.create({
          message: res?.data?.error,
          color: 'red',
          icon: 'warning',
          position: 'top',
          timeout: 2000,
        });
      }
    } catch (error) {
      console.error('Error connecting to device: ', error);
      Notify.create({
        message: 'Error connecting to device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      });
    }
  }

  async function disconnectDevice(address: string, name: string): Promise<void> {
    try {
      await api.post('/api/disconnect-device', { address, name });
    } catch (error: any) {
      console.error('Error disconnect device info: ', error);
      Notify.create({
        message: 'Error disconnecting device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      });
    }
  }

  async function fetchDevices(): Promise<Device[] | undefined> {
    try {
      const response = await api.get('/api/devices');
      const data = await response.data;
      updateDevices(data?.devices);
      return devices.value;
    } catch (error) {
      console.error('Error fetching devices: ', error);
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get devices() {
      return readonly(devices);
    },
    get cellInfo() {
      return readonly(cellInfo);
    },
    get deviceInfo() {
      return readonly(deviceInfo);
    },
    get settingInfo() {
      return readonly(settingInfo);
    },

    // ==============
    //   GETTERS
    // ==============
    getDevices,
    getCellInfo,
    getDeviceInfo,
    getSettingInfo,

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
