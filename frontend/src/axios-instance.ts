import axios from 'axios';
import { eventBus } from 'src/eventBus';

function isHtmlResponse(headers: any, data: any) {
  const ct = (headers && (headers['content-type'] || headers['Content-Type'])) || '';
  if (typeof data === 'string' && /<!doctype html|<html/i.test(data)) return true;
  if (typeof ct === 'string' && ct.includes('text/html')) return true;
  return false;
}

export const api = axios.create({
  baseURL: '',
  timeout: 20000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => {
    if (isHtmlResponse(response.headers, response.data)) {
      return Promise.reject({ isHtml: true, message: 'HTML response received', response });
    }
    return response;
  },
  (error) => {
    const { response } = error;

    if ((response && response?.status === 401) || response?.status === 403) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('access_token_timestamp');
      eventBus.emit('session:remove', 'access_token');
      return Promise.reject(new Error('Unauthorized: Access token has been removed.'));
    }
    return Promise.reject(error);
  }
);
