import { defineStore } from 'pinia'
import { Notify } from 'quasar'
import { api } from 'src/boot/axios'
import { Device } from 'src/models'
import { readonly, ref } from 'vue'

export const useTapoStore = defineStore('tapo', () => {
  // ==============
  //   STATE
  // ==============
  const devices = ref([])

  // ==============
  //   GETTERS
  // ==============
  function getDevices(): Device[] {
    return devices.value
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateDevices(newDevices: any) {
    devices.value = newDevices
  }

  // ==============
  //   ACTIONS
  // ==============
  async function addDevice(data: { ip: string; email: string; password: string }): Promise<void> {
    try {
      await api.post('/api/tapo/devices/add', data)
      await fetchDevices();
    } catch (error) {
      console.error('Error add device: ', error)
      Notify.create({
        message: 'Error add device.',
        color: 'red',
        icon: 'warning',
        position: 'top',
        timeout: 2000,
      })
    }
  }

  async function fetchDevices() {
    try {
      const response = await api.get('/api/tapo/devices')
      const data = await response.data
      updateDevices(data?.devices)
      return devices.value
    } catch (error) {
      console.error('Error fetching tapo devices: ', error)
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get devices() {
      return readonly(devices)
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
    fetchDevices,
    addDevice,
  }
})
