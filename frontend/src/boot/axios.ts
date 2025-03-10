import { boot } from 'quasar/wrappers';
import axios from 'axios';
import { eventBus } from 'src/eventBus';

const api = axios.create({
  baseURL: '',
});

api.interceptors.request.use(
  config => {
    const token = sessionStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

api.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    const { response } = error;
    if (response) {
      if (response.status === 401) {
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('access_token_timestamp');
        eventBus.emit("session:remove", "access_token");
        return Promise.reject(new Error('Unauthorized: Access token has been removed.'));
      }
    }
    return Promise.reject(error);
  }
);

export default boot(({ app }) => {
  app.config.globalProperties.$axios = axios;
  app.config.globalProperties.$api = api;
});

export { axios, api };
