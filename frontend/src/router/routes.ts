import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [{ path: '', component: () => import('pages/IndexPage.vue') }],
    meta: {
      pageTitle: 'BMS Monitor | Cell info',
    },
  },
  {
    path: '/devices',
    component: () => import('layouts/MainLayout.vue'),
    children: [{ path: '', component: () => import('pages/DevicesPage.vue') }],
    meta: {
      pageTitle: 'BMS Monitor | Devices',
    },
  },
  {
    path: '/settings',
    component: () => import('layouts/MainLayout.vue'),
    children: [{ path: '', component: () => import('pages/SettingsPage.vue') }],
    meta: {
      pageTitle: 'BMS Monitor | Settings',
    },
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
    meta: {
      pageTitle: 'BMS Monitor | Error',
    },
  },
];

export default routes;
