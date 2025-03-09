import { defineStore } from 'pinia';
import { axios } from 'src/boot/axios';
import { Alert } from 'src/models';
import { ref } from 'vue';

export const useAlertsStore = defineStore('alerts', () => {
  const alerts = ref<Alert[]>([]);

  function updateAlerts(newInfo: Alert[]) {
    alerts.value = newInfo;
  }

  async function fetchErrorAlerts() {
    try {
      const response = await axios.get('/api/error-alerts', {
        validateStatus: (status) => status < 500
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
      await axios.post('/api/error-alerts', { id }, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${sessionStorage.getItem("access_token")}`
        }
      });
      fetchErrorAlerts();
    } catch (error) {
      console.error('Error remove error alerts:', error);
    }
  }

  return { alerts, updateAlerts, fetchErrorAlerts, deleteErrorAlert };
});
