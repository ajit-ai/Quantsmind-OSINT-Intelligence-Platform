<template>
  <div style="padding:20px">
    <h2>Sources & Collection Policies</h2>
    <table style="width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden">
      <tr style="background:#020617"><th style="padding:10px;text-align:left">Name</th><th>Type</th><th>URL</th><th>Active</th><th>Action</th></tr>
      <tr v-for="s in sources" :key="s.id" style="border-top:1px solid #334155"><td style="padding:10px">{{s.name}}</td><td>{{s.source_type}}</td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis">{{s.url}}</td><td>{{s.is_active? 'Yes':'No'}}</td><td><button @click="trigger(s.id)" style="padding:4px 10px;background:#38bdf8;border:none;border-radius:4px;cursor:pointer">Collect now</button></td></tr>
    </table>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
const sources=ref([])
onMounted(async()=>{ const {data}=await axios.get('/api/sources/'); sources.value=data.results||data })
async function trigger(id){ await axios.post(`/api/sources/${id}/trigger/`); alert('Collection queued') }
</script>
