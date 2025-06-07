import { boot } from 'quasar/wrappers';
import { api } from 'src/axios-instance';

export default boot(({ app }) => {
  app.config.globalProperties.$api = api;
});

export { api };
