<template>
  <div class="toggle-wrapper">
    <span :class="{ disabled: !interactive }" class="name">
      {{ title }}
      <q-spinner v-if="loading" size="0.8em" class="q-ml-xs" />
    </span>
    <div class="toggle transparent">
      <!-- unique id per instance: all toggles used to share id="transparent" -->
      <input
        :id="uid"
        :disabled="!interactive || loading"
        :checked="checked"
        type="checkbox"
        @change="onChange"
      />
      <label class="toggle-item" :for="uid"></label>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, useId, watch } from 'vue';

const props = defineProps({
  title: String,
  value: Boolean,
  interactive: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
});
const emit = defineEmits<{ (e: 'toggle', value: boolean): void }>();

const uid = `toggle-${useId()}`;
const checked = ref(props.value);

watch(
  () => props.value,
  (newValue) => {
    checked.value = newValue;
  }
);

function onChange(event: Event) {
  const requested = (event.target as HTMLInputElement).checked;
  // The parent confirms and applies the change; until the BMS reports it, show the real state.
  (event.target as HTMLInputElement).checked = props.value;
  checked.value = props.value;
  emit('toggle', requested);
}
</script>

<style scoped lang="scss">
* {
  box-sizing: border-box;

  &:before,
  &:after {
    content: '';
    position: absolute;
  }
}

input {
  height: 15px;
  left: 0;
  opacity: 0 !important;
  position: absolute;
  top: 0;
  width: 40px;
}

.name {
  font-size: 1.5em;
  font-weight: 700;
  color: white;
  text-align: left;
}

.toggle-wrapper {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.toggle {
  position: relative;
  display: inline-block;
}

label.toggle-item {
  width: 6.7em;
  height: 2.5em;
  display: inline-block;
  border-radius: 50px;
  margin: 5px;
  position: relative;
  transition: all 0.3s ease;
  transform-origin: 20% center;
  cursor: pointer;

  &:before {
    display: block;
    transition: all 0.2s ease;
    width: 2.3em;
    height: 2.3em;
    top: 0.25em;
    left: 0.25em;
    border-radius: 2em;
    border: 2px solid #88cf8f;
    transition: 0.3s ease;
  }
}

.transparent {
  label {
    background: transparent;
    border: 3px solid #fff;

    &:before {
      border: 3px solid #fff;
      width: 1.7em;
      height: 1.7em;
      top: 0.2em;
      left: 0.2em;
      background: #fff;
    }
  }
}

input:checked + label {
  &:before {
    transform: translateX(59px);
  }
}

input:disabled + .toggle-item {
  border: 3px solid #808080 !important;
  color: #808080 !important;
}

.disabled {
  color: #808080 !important;
}

input:disabled + .toggle-item::before {
  background-color: #808080 !important;
  border: 3px solid #808080 !important;
}
</style>
