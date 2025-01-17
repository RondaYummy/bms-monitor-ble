<template>
  <q-page class="column items-center justify-evenly">
    <div>Loading...</div>
    <template v-if='devicesList'>
      <h3>
        {{ (Object.values(devicesList)[0] as any)?.average_voltage?.toFixed(2) }}
        <sup>V</sup>
      </h3>
      <h3 class='unique'>
        {{ (Object.values(devicesList)[0] as any)?.remaining_capacity?.toFixed(2) }}
        <sup>Ah</sup>
      </h3>
    </template>

    <q-btn @click="installApp"
           color="white"
           text-color="black"
           label="Install App" />

    <q-tabs v-model="tab"
            dense
            class="bg-indigo text-white"
            v-if="devicesList">
      <q-tab v-for="device of Object.keys(devicesList)"
             :key="device"
             :name="device"
             :label="device" />
    </q-tabs>
  </q-page>
</template>

<script setup lang="ts">
import type { Device } from 'src/interfaces';
import { ref } from 'vue';

const devicesList = ref<Record<string, Device>>({});
const tab = ref();

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string; }>;
  prompt(): Promise<void>;
}

let deferredPrompt: BeforeInstallPromptEvent;

window.addEventListener('beforeinstallprompt', (event: Event) => {
  // Запобігти автоматичному показу діалогу
  // event.preventDefault();
  deferredPrompt = event as BeforeInstallPromptEvent;
});

function installApp() {
  deferredPrompt.prompt();
};


async function fetchCellInfo() {
  try {
    const response = await fetch('/api/cell-info');
    if (!response.ok) {
      throw new Error('Failed to fetch cell info');
    }
    const data = await response.json();
    console.log('Cell Info:', data);
    devicesList.value = data;
  } catch (error) {
    console.error('Error fetching cell info:', error);
  }
}
fetchCellInfo();
</script>
