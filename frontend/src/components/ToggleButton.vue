<template>
  <div class="toggle-wrapper">
    <span class="name">{{ title }}</span>
    <div class="toggle transparent">
      <input disabled
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
  width: 7em;
  background: #2e394d;
  height: 3em;
  display: inline-block;
  border-radius: 50px;
  margin: 40px;
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
    height: 3.35em;

    &:before {
      border: 3px solid #fff;
      width: 2em;
      height: 2em;
      top: 0.45em;
      left: 0.21em;
      background: #fff;
    }
  }
}

#transparent:checked+label {
  &:before {
    transform: translateX(59px);
  }
}

input[type="checkbox"]:not(:checked) {
  border: 3px solid #808080;
  color: #808080;
}

input:disabled+.toggle-item {
  border: 3px solid #808080 !important;
  color: #808080 !important;
}

input:disabled+.toggle-item::before {
  background-color: #808080 !important;
  border: 3px solid #808080 !important;
}
</style>
