<template>
  <div class="column justify-center items-center">
    <h6 class="relative-position inline">
      Статистика роботи
      <div class="indicate indicate-info">
        <q-icon @click="showInfo = true" name="info" size="24px" color="white" />
      </div>
    </h6>

    <div class="row justify-between full-width">
      <div class="column text-center items-center justify-between cell-item">
        <img src="../../../public/images/carbon.png" alt="CO2">
        <span class="text-subtitle1">Зменшення викидів CO2</span>
        <span class="text-h6 text-weight-bold">{{ (props.data.stat_total_pv * 0.000793)?.toFixed(2) }} тонн</span>
      </div>

      <div class="column text-center items-center justify-between cell-item">
        <img src="../../../public/images/pine-tree.png" alt="pine-tree">
        <span class="text-subtitle1">Еквівалентна к-ть посаджених дерев</span>
        <span class="text-h6 text-weight-bold">{{ Math.trunc(props.data.stat_total_pv * 0.997 / 18.3) }} дерев</span>
      </div>

      <div class="column text-center items-center justify-between cell-item">
        <img src="../../../public/images/profit.png" alt="pine-tree">
        <span class="text-subtitle1">Оцінка прибутку</span>
        <span class="text-h6 text-weight-bold">{{ formatterUAH.format(props.data.stat_total_pv * 4.32) }}</span>
      </div>

      <div class="column text-center items-center justify-between cell-item">
        <img src="../../../public/images/solar-cell.png" alt="pine-tree">
        <span class="text-subtitle1">Загальне виробництво</span>
        <span class="text-h6 text-weight-bold">{{ (props.data.stat_total_pv / 1000)?.toFixed(2) }} МВт·год</span>
      </div>
    </div>

    <div>
      <ul>
        <li>
          ✅[ PV ] Виробництво соянчної енергії в день: {{ props.data?.stat_daily_pv }} кВт·год
        </li>

        <li>
          ✅[ PV ] [ Статистика роботи ] Загальне викробництво: {{ props.data?.stat_total_pv }} кВт·год
        </li>

        <li>
          ✅[Battery] Щоденне споживання ( Від мережі ): {{ props.data?.stat_daily_bat_discharge }} кВт·год
        </li>

        <li>
          ✅[ Grid ] Кількість придбаної електроенергії в день: {{ props.data?.stat_daily_grid_in }} кВт·год
        </li>

        <li>
          ✅[ Grid ] Кількість проданої електроенергії в день: {{ props.data?.stat_daily_grid_out }} кВт·год
        </li>

        <li>
          ✅[ Grid ] [ Статистика роботи ] Загальний вивід до мережі: {{ props.data?.stat_total_grid_out }} кВт·год
        </li>

        <li>
          ✅[ PV + Grid ] Загальне споживання: {{ props.data?.stat_total_load }} кВт·год
        </li>
      </ul>

      <h6>Потребують перевірки показники:</h6>

      <ul>
        <li>
          [Battery] Денний заряд: {{ props.data?.daily_bat_charge }} кВт·год
        </li>

        <li>
          [Battery] Загальний заряд: {{ props.data?.total_bat_charge }} кВт·год
        </li>

        <li>
          [Battery] Загальний розряд: {{ props.data?.total_bat_discharge }} кВт·год
        </li>

        <li>
          ✅[ Grid ] Загальна енергія з мережі: {{ props.data?.grid_in }} кВт·год
        </li>

        <li>
          [ Grid ] Денне споживання навантаження: {{ props.data?.daily_load }} кВт·год
        </li>
      </ul>
    </div>
  </div>

  <q-dialog v-model="showInfo">
    <q-card dark>
      <q-card-section>
        <h6 class="text-center text-h6">Пояснення</h6>

        <ul>
          <li>
            Ця частина вмісту обчислюється на основі основної інформації про електростанцію та даних протягом усього її
            життєвого циклу.
          </li>

          <li>
            Якщо очікуваний дохід не має даних, це означає, що ця електростанція ще не налаштувала “дохід за
            кіловат-годину”. Перейдіть до налаштування.
          </li>

          <li>
            Зниження CO2 (тонни) = 0.000793 * Накопичена генерація електричної енергії (kWh), дані з авторитетних
            органів та установ.
          </li>

          <li>
            Еквівалентна кількість посаджених дерев (дерева) = Накопичена генерація електричної енергії (kWh) * 0.997 /
            18.3, тобто скільки дерев потрібно посадити, щоб поглинути CO2-викиди, що виникають при традиційному
            виробництві енергії. Дані з авторитетних органів та установ.
          </li>
        </ul>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn flat label="OK" color="primary" v-close-popup />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { DeyeSafeValues } from 'src/models';


const props = defineProps<{
  data: DeyeSafeValues;
}>();
console.log(props.data);

const showInfo = ref(false);

const formatterUAH = new Intl.NumberFormat('uk-UA', {
  style: 'currency',
  currency: 'UAH',
});
</script>

<style scoped lang="scss">
.indicate-info {
  top: 0;
  right: -30px;
}

ul {
  font-size: 16px;
  list-style-type: decimal;

  li {
    padding: 5px 0px;
  }
}

img {
  max-width: 70px;
}

.cell-item {
  min-height: 135px;
  width: calc(50% - 10px);
  border: 1px solid white;
  margin: 5px;
  padding: 5px;
  border-radius: 15px;
}
</style>
