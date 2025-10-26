<template>
  <div class="box">
    <div class="p-6">
      <div class="row items-center justify-between gap-4">
        <div class="flex-1 space-y-1">
          <div class="flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"
              viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
              stroke-linejoin="round" class="lucide lucide-zap w-5 h-5 text-success">
              <path
                d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z">
              </path>
            </svg>
            <h3 class="font-semibold text-foreground">Авто-балансування</h3>
          </div>
          <p class="text-sm text-muted-foreground">Автоматично вимикає прилади, якщо споживання перевищує генерацію</p>
        </div>

        <button v-if="!enabled" class="btn" @click="enabled = true;">
          ВИМКНЕНО
        </button>

        <button v-if="enabled" class="btn btn-enabled" @click="enabled = false">
          <div class="w-2 h-2 rounded-full bg-success animate-pulse"></div>
          АКТИВНО
        </button>
      </div>

      <div v-if="enabled" class="mt-4 pt-4 border-t row items-center gap-2 text-sm text-success">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="lucide lucide-shield w-4 h-4">
          <path
            d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z">
          </path>
        </svg>
        <span>Система моніторить баланс енергії</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const enabled = ref(false);
</script>

<style scoped lang="scss">
.box {
  color: rgb(248, 250, 252);
  border: 1px solid rgba(43, 48, 59, 0.5);
  background-color: rgba(25, 29, 36, 0.5);
  box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.05);
  backdrop-filter: blur(4px);
  border-radius: 12px;
  margin-bottom: 10px;
}

.p-6 {
  padding: 1.5rem;
}

.text-foreground {
  color: rgb(248, 250, 252);
}

.font-semibold {
  font-weight: 600;
}

h3 {
  font-size: 16px;
  font-weight: 600;
}

.text-sm {
  font-size: 0.875rem;
  line-height: 1.25rem;
}

.gap-4 {
  gap: 1rem;
}

.text-muted-foreground {
  color: rgb(152, 164, 179);
}

.flex-1 {
  flex: 1 1 0%;
}

.gap-2 {
  gap: 0.5rem;
}

.w-5 {
  width: 1.25rem;
}

.h-5 {
  height: 1.25rem;
}

.w-4 {
  width: 1rem;
}

.h-4 {
  height: 1rem;
}

.w-2 {
  width: 0.5rem;
}

.h-2 {
  height: 0.5rem;
}

.rounded-full {
  border-radius: 9999px;
}

.btn {
  color: rgb(152, 164, 179);
  background-color: rgba(0, 0, 0, 0);
  border: 1px solid rgb(43, 48, 59);
  animation-duration: 0.3s;
  transition-duration: 0.3s;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  padding: 8px 16px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}

.btn-enabled {
  color: rgb(22, 162, 73);
  box-shadow: rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(232, 48, 110, 0.3) 0px 0px 40px 0px;
}

.text-success {
  color: rgb(22, 162, 73);

  span {
    color: rgb(22, 162, 73);
  }
}

.pt-4 {
  padding-top: 1rem;
}

.mt-4 {
  margin-top: 1rem;
}

.bg-success {
  color: rgb(22, 162, 73);
  background-color: rgb(22, 162, 73);
}

.border-t {
  border-top: 1px solid rgba(43, 48, 59, 0.5);
}
</style>
