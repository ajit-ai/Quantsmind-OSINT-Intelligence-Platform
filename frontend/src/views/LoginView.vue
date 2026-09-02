<template>
  <div style="max-width:400px;margin:60px auto;background:#1e293b;padding:24px;border-radius:8px">
    <h2>Login</h2>
    <input v-model="username" placeholder="Username" style="width:100%;padding:8px;margin-bottom:8px;border-radius:6px"/>
    <input v-model="password" type="password" placeholder="Password" style="width:100%;padding:8px;margin-bottom:12px;border-radius:6px"/>
    <button @click="doLogin" style="width:100%;padding:10px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer">Sign in</button>
    <p style="opacity:0.6;margin-top:12px">Use the Django superuser created via createsuperuser.</p>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
const username=ref(''), password=ref('')
const auth=useAuthStore(), router=useRouter()
async function doLogin(){ await auth.login(username.value, password.value); router.push('/') }
</script>
