<template>
  <q-page class="stats-page column items-center q-pa-md">
    <div v-if="!hasInverter && !loading" class="empty q-pa-md text-center">
      Статистика береться з інвертора Deye. Додайте інвертор у
      <router-link to="/settings" class="link">Налаштування → Deye</router-link>.
    </div>
    <div v-else-if="loading" class="q-pa-lg"><q-spinner color="white" size="2em" /></div>
    <AddtionalInfo v-else :data="totals" class="full-width" />
  </q-page>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import AddtionalInfo from 'src/components/deye/AddtionalInfo.vue';
import { useDeyeTotals } from 'src/composables/useDeyeTotals';
import { useDeyeStore } from 'src/stores/deye';
import { useLiveStore } from 'src/stores/live';

const deyeStore = useDeyeStore();
const liveStore = useLiveStore();
const totals = useDeyeTotals();
const loading = ref(true);
const hasInverter = computed(() => (deyeStore.getDeyeData() || []).length > 0);
let timer: ReturnType<typeof setInterval> | undefined;

async function refresh() {
  // The live stream keeps the store fresh; poll only as a fallback.
  if (document.hidden || liveStore.isConnected()) return;
  await deyeStore.fetchDeyeDevices();
}

onMounted(async () => {
  liveStore.start();
  await deyeStore.fetchDeyeDevices();
  loading.value = false;
  timer = setInterval(refresh, 5000);
});

onBeforeUnmount(() => {
  liveStore.stop();
  clearInterval(timer);
});
</script>

<style scoped lang="scss">
.stats-page {
  color: white;
  max-width: 720px;
  margin: 0 auto;
  /* keep the last tiles above the tab bar */
  padding-bottom: 80px;
}
.empty {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 8px;
}
.link {
  color: #03dac6;
}
</style>
