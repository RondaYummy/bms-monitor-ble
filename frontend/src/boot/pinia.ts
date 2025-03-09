import { boot } from 'quasar/wrappers';
import { createPinia } from 'pinia';
import type { App } from 'vue';

export default boot(({ app }: { app: App; }) => {
  app.use(createPinia());
});
