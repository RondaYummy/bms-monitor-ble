<template>
  <div class="toggle-wrapper">
    <span :class="{ disabled: disabled }"
          class="name">{{ title }}</span>
    <div class="toggle transparent">
      <input :disabled="disabled"
             :checked="checked"
             id="transparent"
             type="checkbox" />
      <label class="toggle-item"
             for="transparent"></label>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, watch } from 'vue';

const props = defineProps({
  title: String,
  value: Boolean,
});
const checked = ref(props.value);
const disabled = ref(true);
watch(() => props.value, (newValue) => {
  checked.value = newValue;
});
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
  transition: all .3s ease;
  transform-origin: 20% center;
  cursor: pointer;

  &:before {
    display: block;
    transition: all .2s ease;
    width: 2.3em;
    height: 2.3em;
    top: .25em;
    left: .25em;
    border-radius: 2em;
    border: 2px solid #88cf8f;
    transition: .3s ease;
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

#transparent:checked+label {
  &:before {
    transform: translateX(59px);
  }
}

input:disabled+.toggle-item {
  border: 3px solid #808080 !important;
  color: #808080 !important;
}

.disabled {
  color: #808080 !important;
}

input:disabled+.toggle-item::before {
  background-color: #808080 !important;
  border: 3px solid #808080 !important;
}
</style>
