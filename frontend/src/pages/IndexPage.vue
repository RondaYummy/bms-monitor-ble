<template>
  <q-page class="row items-center justify-evenly">
    <div>Loading...</div>
    <button @click="installApp">Install App</button>
    <q-btn color="white"
           text-color="black"
           label="Install App" />
  </q-page>
</template>

<script setup lang="ts">
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
</script>
