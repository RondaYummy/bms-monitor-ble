<template>
  <q-layout view="lHr Lpr fFf">
    <q-page-container>
      <router-view />
    </q-page-container>

    <q-footer elevated
              class="footer">
      <nav class="mobile-nav">
        <router-link to="/devices"
                     class="bloc-icon"> Devices </router-link>
        <router-link to="/"
                     id="summary"
                     class="bloc-icon"> Summary </router-link>
        <router-link to="/settings"
                     class="bloc-icon"> Settings </router-link>
      </nav>
    </q-footer>
  </q-layout>
</template>

<script setup lang="ts">

</script>

<style scoped lang='scss'></style>
