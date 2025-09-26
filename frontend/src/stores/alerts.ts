import { defineStore } from 'pinia';
import { Notify } from 'quasar';
import { api } from 'src/boot/axios';
import { Alert } from 'src/models';
import { readonly, ref } from 'vue';

export const useAlertsStore = defineStore('alerts', () => {
  // ==============
  //   STATE
  // ==============
  const alerts = ref<Alert[]>([]);

  // ==============
  //   GETTERS
  // ==============
  function getAlerts(): Alert[] {
    return alerts.value;
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateAlerts(newInfo: Alert[]) {
    alerts.value = newInfo;
  }

  // ==============
  //   ACTIONS
  // ==============
  async function fetchErrorAlerts() {
    try {
      const response = await api.get('/api/error-alerts', {
        validateStatus: (status) => status < 500,
      });

      if (response.status === 404) {
        alerts.value = [];
        return;
      }

      alerts.value = response.data;
    } catch (error) {
      console.error('Error fetching error alerts:', error);
    }
  }

  async function deleteErrorAlert(id: number) {
    try {
      const res = await api.post('/api/error-alerts', { id });
      if (res.data?.message) {
        Notify.create({
          message: res.data?.message,
          color: 'secondary',
        });
      }
      fetchErrorAlerts();
    } catch (error) {
      console.error('Error remove error alerts:', error);
    }
  }

  async function deleteAllAlerts() {
    try {
      const res = await api.delete('/api/error-alerts/all');
      if (res.data?.message) {
        Notify.create({
          position: 'top',
          message: res.data?.message,
          color: 'secondary',
        });
      }
      fetchErrorAlerts();
    } catch (error) {
      console.error('Error remove error alerts:', error);
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get alerts() {
      return readonly(alerts);
    },

    // ==============
    //   GETTERS
    // ==============
    getAlerts,

    // ==============
    //   MUTATIONS
    // ==============
    updateAlerts,

    // ==============
    //   ACTIONS
    // ==============
    fetchErrorAlerts,
    deleteErrorAlert,
    deleteAllAlerts,
  };
});
