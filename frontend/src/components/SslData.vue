<template>
  <pre>
    {{ props?.data }}
  </pre>
</template>

<script setup lang="ts">
const props = defineProps(['data']);
</script>
