import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { Config } from 'src/models';
import { ref } from 'vue';

export const useConfigStore = defineStore('config', () => {
  // ==============
  //   STATE
  // ==============
  const config = ref<Config>({
    n_hours: 12,
    password: '',
    VAPID_PUBLIC_KEY: '',
    vapid_public: '',
  });

  // ==============
  //   GETTERS
  // ==============
  function getConfig(): Config {
    return config.value;
  }

  // ==============
  //   MUTATIONS
  // ==============
  function updateConfig(newInfo: Config) {
    config.value = newInfo;
  }

  // ==============
  //   ACTIONS
  // ==============
  async function fetchConfigs() {
    try {
      const response = await api.get('/api/configs');
      const data: Config = response.data;
      config.value = data;
    } catch (error) {
      console.error('Error fetching configs:', error);
    }
  }

  async function updateConfigs() {
    try {
      const response = await api.post('/api/configs', { ...config.value });
      config.value = response.data;
    } catch (error) {
      console.error('Error updating configs:', error);
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    config,

    // ==============
    //   GETTERS
    // ==============
    getConfig,

    // ==============
    //   MUTATIONS
    // ==============
    updateConfig,

    // ==============
    //   ACTIONS
    // ==============
    fetchConfigs,
    updateConfigs,
  };
});
