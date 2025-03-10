import { boot } from 'quasar/wrappers';
import VueApexCharts from 'vue3-apexcharts';

export default boot(({ app }) => {
  app.use(VueApexCharts);
  app.component('apex-chart', VueApexCharts);
});
