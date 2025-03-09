import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { sortDevices } from 'src/helpers/utils';
import { CellInfo, DeviceInfo, SettingInfo } from 'src/models';
import { ref } from 'vue';

export const useBmsStore = defineStore('bms', () => {
  const cellInfo = ref<Record<string, CellInfo>>({});
  const deviceInfo = ref<DeviceInfo[]>([]);
  const settings = ref<SettingInfo[]>([]);
  const devices = ref();

  function updateCellInfo(newInfo: Record<string, CellInfo>) {
    cellInfo.value = newInfo;
  }

  function updateDeviceInfo(newInfo: DeviceInfo[]) {
    deviceInfo.value = newInfo;
  }

  function updateSettings(newSettings: SettingInfo[]) {
    settings.value = newSettings;
  }

  async function fetchSettings() {
    try {
      const response = await api.get('/api/device-settings');
      const data: SettingInfo[] = response.data;
      settings.value = data;
    } catch (error) {
      console.error('Error fetching device settings:', error);
    }
  }

  async function fetchCellInfo() {
    try {
      const response = await api.get('/api/cell-info');
      const data = response.data;
      cellInfo.value = data;
    } catch (error) {
      console.error('Error fetching cell info:', error);
    }
  }

  async function fetchDeviceInfo(connected: boolean) {
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

  return { devices, cellInfo, deviceInfo, settings, updateCellInfo, updateDeviceInfo, updateSettings, fetchSettings, fetchCellInfo, fetchDeviceInfo };
});
