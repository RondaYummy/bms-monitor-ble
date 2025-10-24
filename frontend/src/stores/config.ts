import { defineStore } from 'pinia';
import { api } from 'src/boot/axios';
import { Config } from 'src/models';
import { ref, readonly } from 'vue';

export type SslStatus = 'ok' | 'warning' | 'danger' | 'error' | 'none';

export interface SslCertificateDetails {
  created_at: string;
  expires_at: string;
  days_valid: number;
  days_left: number;
}

export interface SslResponse {
  status: SslStatus;
  message: string;
  certificat: SslCertificateDetails | null;
}

const configs = {
  timeout: 4000,
};

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

  const ssl = ref<SslResponse>({
    certificat: { days_left: 0, days_valid: 0, expires_at: '', created_at: '' },
    message: '',
    status: 'ok',
  });

  // ==============
  //   GETTERS
  // ==============
  function getConfig(): Config {
    return config.value;
  }

  function getSsl(): SslResponse {
    return ssl.value;
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
  async function fetchSsl() {
    try {
      const response = await api.get('/api/ssl', configs);
      const data: SslResponse = response.data;
      ssl.value = data;
    } catch (error) {
      console.error('Error fetching ssl:', error);
    }
  }

  async function fetchConfigs() {
    try {
      const response = await api.get('/api/configs', configs);
      const data: Config = response.data;
      config.value = data;
    } catch (error) {
      console.error('Error fetching configs:', error);
    }
  }

  async function updateConfigs() {
    try {
      const response = await api.post('/api/configs', { ...config.value }, configs);
      config.value = response.data;
    } catch (error) {
      console.error('Error updating configs:', error);
    }
  }

  return {
    // ==============
    //   STATE
    // ==============
    get config() {
      return readonly(config);
    },
    get ssl() {
      return readonly(ssl);
    },

    // ==============
    //   GETTERS
    // ==============
    getConfig,
    getSsl,

    // ==============
    //   MUTATIONS
    // ==============
    updateConfig,

    // ==============
    //   ACTIONS
    // ==============
    fetchConfigs,
    fetchSsl,
    updateConfigs,
  };
});
