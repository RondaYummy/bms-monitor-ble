<template>
  <q-layout view="lHr Lpr fFf">
    <q-page-container>
      <router-view />
    </q-page-container>

    <q-footer elevated
              class="footer">
      <nav class="mobile-nav">
        <router-link to="/devices"
                     class="bloc-icon">
          <span>Devices</span>
        </router-link>
        <router-link to="/"
                     id="summary"
                     class="bloc-icon">
          <span>Summary</span>
        </router-link>
        <router-link to="/settings"
                     class="bloc-icon">
          <span>Settings</span>
        </router-link>
      </nav>
    </q-footer>
  </q-layout>
</template>
