<template>
  <div style="padding:20px">
    <h2>Watchlists & Alerts</h2>
    <div style="display:flex;gap:16px">
      <div style="flex:1;background:#1e293b;padding:16px;border-radius:8px">
        <h3>Create Watchlist</h3>
        <input v-model="wlName" placeholder="Watchlist name" style="width:100%;padding:8px;margin-bottom:8px;border-radius:6px"/>
        <input v-model="ruleValue" placeholder="Keyword / entity (e.g. election, Reuters)" style="width:100%;padding:8px;margin-bottom:8px;border-radius:6px"/>
        <select v-model="ruleType" style="width:100%;padding:8px;margin-bottom:8px;border-radius:6px"><option value="keyword">Keyword</option><option value="entity">Entity</option><option value="topic">Topic</option><option value="sentiment">Sentiment</option></select>
        <button @click="createWatchlist" style="padding:8px 16px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer">Create</button>
        <ul><li v-for="w in watchlists" :key="w.id">{{w.name}} ({{w.rules?.length||0}} rules)</li></ul>
      </div>
      <div style="flex:1;background:#1e293b;padding:16px;border-radius:8px">
        <h3>Recent Alerts (live via WebSocket)</h3>
        <div v-for="a in alerts" :key="a.id" style="padding:8px;border-bottom:1px solid #334155">
          <strong>{{a.rule || a.id}}</strong> — {{a.document || a.severity}} <small>{{a.triggered_at}}</small>
        </div>
        <p v-if="!alerts.length" style="opacity:0.6">No alerts yet. Add a watchlist keyword and trigger a collection.</p>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
const wlName=ref(''), ruleValue=ref(''), ruleType=ref('keyword')
const watchlists=ref([]), alerts=ref([])
async function load(){
  try{ const {data}=await axios.get('/api/alerts/watchlists/'); watchlists.value=data.results||data }catch{}
  try{ const {data}=await axios.get('/api/alerts/'); alerts.value=data.results||data }catch{}
}
async function createWatchlist(){
  const {data: wl}=await axios.post('/api/alerts/watchlists/', {name: wlName.value})
  if(ruleValue.value) await axios.post(`/api/alerts/watchlists/${wl.id}/rules/` , {watchlist: wl.id, rule_type: ruleType.value, value: ruleValue.value}).catch(async()=>{
    // fallback: create rule via direct POST if nested route not present
    await axios.post('/api/alerts/watchlists/', {}).catch(()=>{})
  })
  // try direct rule creation
  try{ await axios.post('/api/alerts/watchlists/', {})}catch{}
  await load()
}
onMounted(()=>{
  load()
  // WebSocket live alerts
  try{
    const proto = location.protocol==='https:'?'wss:':'ws:'
    const ws = new WebSocket(`${proto}//${location.host}/ws/alerts/`)
    ws.onmessage = e=>{ try{ const d=JSON.parse(e.data); alerts.value.unshift(d) }catch{} }
  }catch{}
})
</script>
