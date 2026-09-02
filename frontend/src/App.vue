<template>
  <div>
    <nav style="display:flex;gap:16px;padding:12px 20px;background:#020617;align-items:center">
      <strong>Quantsmind OSINT</strong>
      <router-link to="/">Dashboard</router-link>
      <router-link to="/search">Search</router-link>
      <router-link to="/map">Map</router-link>
      <router-link to="/alerts">Alerts</router-link>
      <router-link to="/sources">Sources</router-link>
      <span style="margin-left:auto" v-if="auth.token">Logged in | <a @click="auth.logout()" href="#">Logout</a></span>
      <router-link v-else to="/login">Login</router-link>
    </nav>
    <router-view />
  </div>
</template>
<script setup>
import { useAuthStore } from './stores/auth.js'
const auth = useAuthStore()
</script>
