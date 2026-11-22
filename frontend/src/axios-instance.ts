import axios from 'axios';
import { Notify } from 'quasar';
import { eventBus } from 'src/eventBus';

function isHtmlResponse(headers: any, data: any) {
  const ct = (headers && (headers['content-type'] || headers['Content-Type'])) || '';
  if (typeof data === 'string' && /<!doctype html|<html/i.test(data)) return true;
  if (typeof ct === 'string' && ct.includes('text/html')) return true;
  return false;
}

// Leave VITE_API_URL empty in production: nginx proxies /api on the same origin (same certificate).
// All request paths already start with /api, so a value ending in /api would produce /api/api/...
export const apiUrl = String(import.meta.env.VITE_API_URL || '')
  .trim()
  .replace(/\/+$/, '')
  .replace(/\/api$/, '');

export const api = axios.create({
  baseURL: apiUrl,
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

    // 401 = session missing/expired -> log out. Login itself returns 401 for a wrong password,
    // so the original error is kept (the login form shows it).
    if (response?.status === 401) {
      const hadSession = !!localStorage.getItem('access_token');
      ['access_token', 'access_role', 'access_username', 'token_created_at', 'access_token_timestamp'].forEach(
        (key) => {
          localStorage.removeItem(key);
          eventBus.emit('session:remove', key);
        }
      );
      if (hadSession && !String(error.config?.url || '').endsWith('/api/login')) {
        Notify.create({ message: 'Сесія завершилась. Увійдіть знову.', color: 'orange', position: 'top' });
      }
      return Promise.reject(error);
    }
    // 403 = logged in, but the role is not allowed (viewer). Keep the session.
    if (response?.status === 403) {
      Notify.create({
        message: 'Недостатньо прав: ця дія доступна лише адміністратору.',
        color: 'red',
        icon: 'lock',
        position: 'top',
      });
    }
    return Promise.reject(error);
  }
);
