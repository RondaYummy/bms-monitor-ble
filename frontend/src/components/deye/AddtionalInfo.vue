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
        <span class="text-h6 text-weight-bold">{{ (props.data.stat_total_pv / 1000)?.toFixed() }} кВт·год</span>
      </div>
    </div>

    <div>

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
