import { defineStore } from 'pinia'
import { api } from 'src/boot/axios'
import { DeyeRealtimeData } from 'src/models'
import { readonly, ref } from 'vue'

export const useDeyeStore = defineStore('deye', () => {
  // ==============
  //   STATE
  // ==============
  const deyeData = ref<DeyeRealtimeData>({
    timestamp: '',
    pv1_power: 0,
    pv2_power: 0,
    total_pv: 0,
    load_power: 0,
    grid_power: 0,
    battery_power: 0,
    battery_voltage: 0,
    battery_soc: 0,
    net_balance: 0,
  })

  // ==============
  //   GETTERS
  // ==============
  function getDeyeData(): DeyeRealtimeData {
    return deyeData.value
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateDeyeData(newDeyeData: DeyeRealtimeData) {
    deyeData.value = newDeyeData
  }

  // ==============
  //   ACTIONS
  // ==============
  async function fetchDeyeData(): Promise<DeyeRealtimeData | undefined> {
    try {
      const response = await api.get('/api/deye-info')
      const data = await response.data
      updateDeyeData(data)
      return deyeData.value
    } catch (error) {
      console.error('Error Deye data: ', error)
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get deyeData() {
      return readonly(deyeData)
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
    fetchDeyeData,
  }
})
