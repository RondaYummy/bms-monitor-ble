<template>
  <q-layout view="lHr Lpr fFf">
    <q-page-container>
      <router-view />
    </q-page-container>

    <q-footer class="footer">
      <!-- Native-app style tab bar: icon + short label, the active tab is highlighted -->
      <nav class="tab-bar" aria-label="Головне меню">
        <router-link
          v-for="tab in TABS"
          :key="tab.to"
          :to="tab.to"
          class="tab"
          :class="{ active: isActive(tab.to) }"
          :aria-current="isActive(tab.to) ? 'page' : undefined"
        >
          <q-icon :name="tab.icon" size="26px" />
          <span class="tab-label">{{ tab.label }}</span>
        </router-link>
      </nav>
    </q-footer>
  </q-layout>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router';

const TABS = [
  { to: '/devices', label: 'Пристрої', icon: 'battery_charging_full' },
  { to: '/stats', label: 'Статистика', icon: 'insights' },
  { to: '/', label: 'Огляд', icon: 'home' },
  { to: '/energy', label: 'Економія', icon: 'savings' },
  { to: '/settings', label: 'Налаштування', icon: 'settings' },
] as const;

const route = useRoute();
const isActive = (to: string) => (to === '/' ? route.path === '/' : route.path.startsWith(to));
</script>

<style scoped lang="scss">
.footer {
  background: #16171d;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  /* iPhone home indicator */
  padding-bottom: env(safe-area-inset-bottom);
}

.tab-bar {
  display: flex;
  height: 60px;
}

.tab {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #9aa4b2;
  text-decoration: none;
  transition: color 0.2s ease;
  -webkit-tap-highlight-color: transparent;

  &.active {
    color: #03dac6;
  }

  &:active .q-icon {
    transform: scale(0.9);
  }
}

.tab-label {
  font-size: 10px;
  letter-spacing: -0.1px;
  line-height: 1.1;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
