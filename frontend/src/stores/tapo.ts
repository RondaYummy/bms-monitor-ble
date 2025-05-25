import { defineStore } from 'pinia'
import { Notify } from 'quasar'
import { api } from 'src/boot/axios'
import { TapoDevice } from 'src/models'
import { readonly, ref } from 'vue'

export const useTapoStore = defineStore('tapo', () => {
  // ==============
  //   STATE
  // ==============
  const devices = ref<TapoDevice[]>([]);
  const foundDevices = ref();

  // ==============
  //   GETTERS
  // ==============
  function getDevices(): TapoDevice[] {
    return devices.value;
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateDevices(newDevices: TapoDevice[]) {
    devices.value = newDevices;
  }

  // ==============
  //   ACTIONS
  // ==============
  async function addDevice(data: {
    ip: string
    email: string
    password: string
    power_watt: number
    priority: number
  }): Promise<{ status: string; device: TapoDevice } | undefined> {
    try {
      const res = await api.post('/api/tapo/devices/add', data)
      await fetchDevices()
      if (res.data?.status === 'added') {
        const index = foundDevices.value.findIndex((d: TapoDevice) => d.ip === data.ip)
        if (index !== -1) {
          foundDevices.value.splice(index, 1)
        }
        Notify.create({
          message: 'Tapo device aded success.',
          color: 'green',
          position: 'top',
          timeout: 2000,
        })
      }
      return res.data;
    } catch (error) {
      console.error('Error add device: ', error)
      Notify.create({
        message: 'Error add device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      });
    }
  }

  async function fetchDevices(): Promise<TapoDevice[] | undefined> {
    try {
      const response = await api.get('/api/tapo/devices')
      const data: { devices: TapoDevice[] } = await response.data
      updateDevices(data?.devices)
      return devices.value
    } catch (error) {
      console.error('Error fetching tapo devices: ', error)
    }
  }

  async function enableDevice(ip: string): Promise<void> {
    try {
      await api.post(`/api/tapo/devices/${ip}/on`)
      await fetchDevices()
    } catch (error) {
      console.error('Error enable tapo device: ', error)
      Notify.create({
        message: 'Error enable device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      })
    }
  }

  async function disableDevice(ip: string): Promise<void> {
    try {
      await api.post(`/api/tapo/devices/${ip}/off`)
      await fetchDevices()
    } catch (error) {
      console.error('Error disable tapo device: ', error)
      Notify.create({
        message: 'Error disable device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      })
    }
  }

  async function removeDevice(ip: string): Promise<void> {
    try {
      const res = await api.delete(`/api/tapo/device/${ip}`)
      await fetchDevices()
      Notify.create({
        message: res.data?.message,
        color: 'green',
        position: 'top',
        timeout: 2000,
      })
    } catch (error) {
      console.error('Error disable tapo device: ', error)
      Notify.create({
        message: 'Error disable device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      })
    }
  }

  async function searchTapoDevices(data: { email: string; password: string }) {
    try {
      const res = await api.post(`/api/tapo/devices/search`, data);
      foundDevices.value = res.data?.devices;
      return foundDevices.value;
    } catch (error) {
      console.error('Error search tapo devices: ', error)
      Notify.create({
        message: 'Error search tapo devices.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      })
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get devices() {
      return readonly(devices)
    },
    get foundDevices() {
      return readonly(foundDevices)
    },
    // ==============
    //   GETTERS
    // ==============
    getDevices,

    // ==============
    //   MUTATIONS
    // ==============
    updateDevices,

    // ==============
    //   ACTIONS
    // ==============
    searchTapoDevices,
    fetchDevices,
    addDevice,
    enableDevice,
    disableDevice,
    removeDevice,
  }
})
