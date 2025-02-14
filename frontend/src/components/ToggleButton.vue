<template>
  <div class="toggle-wrapper">
    <span class="name">{{ props?.title }}</span>
    <div class="toggle transparent">
      <input disabled
             :checked="props?.value"
             id="transparent"
             type="checkbox" />
      <label class="toggle-item"
             for="transparent"></label>
    </div>
  </div>
</template>

<script lang="ts" setup>
const props = defineProps({
  title: String,
  value: Boolean,
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

.normal {
  label {
    background: #af4c4c;
    border: .5px solid rgba(117, 117, 117, 0.31);
    box-shadow: inset 0px 0px 4px 0px rgba(0, 0, 0, 0.2), 0 -3px 4px rgba(0, 0, 0, 0.15);

    &:before {
      border: none;
      width: 2.5em;
      height: 2.5em;
      box-shadow: inset 0.5px -1px 1px rgba(0, 0, 0, 0.35);
      background: #fff;
      transform: rotate(-25deg);
    }

    &:after {
      background: transparent;
      height: calc(100% + 8px);
      border-radius: 30px;
      top: -5px;
      width: calc(100% + 8px);
      left: -4px;
      z-index: 0;
      box-shadow: inset 0px 2px 4px -2px rgba(0, 0, 0, 0.2), 0px 1px 2px 0px rgba(151, 151, 151, 0.2);
    }
  }
}

#normal:checked+label {
  background: #4caf50;

  &:before {
    left: 67px;
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
</style>
