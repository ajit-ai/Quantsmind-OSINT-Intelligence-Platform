<template>
  <div style="padding:20px">
    <h2>Watchlists & Alerts</h2>
    <div style="display:grid;grid-template-columns:380px 1fr;gap:16px;align-items:start">
      <div style="background:#1e293b;padding:16px;border-radius:12px;position:sticky;top:12px">
        <h3 style="margin-top:0">Create Watchlist</h3>
        <label style="font-size:12px;opacity:0.7">Name</label>
        <input v-model="wlName" placeholder="e.g. Elections 2026" style="width:100%;padding:8px;margin:4px 0 10px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0"/>
        <label style="font-size:12px;opacity:0.7">Rule</label>
        <div style="display:flex;gap:8px">
          <select v-model="ruleType" style="flex:1;padding:8px;border-radius:6px;background:#0f172a;color:#e2e8f0;border:1px solid #334155"><option value="keyword">Keyword</option><option value="entity">Entity</option><option value="topic">Topic</option><option value="sentiment">Sentiment</option></select>
          <input v-model="ruleValue" placeholder="election / London / positive" style="flex:2;padding:8px;border-radius:6px;border:1px solid #334155;background:#0f172a;color:#e2e8f0"/>
        </div>
        <button @click="createWatchlist" :disabled="!wlName || !ruleValue" style="margin-top:10px;width:100%;padding:10px;background:#38bdf8;border:none;border-radius:8px;cursor:pointer;font-weight:600;opacity:0.95">Create + Add Rule</button>
        <hr style="border-color:#334155;margin:16px 0"/>
        <h4 style="margin:0 0 8px">Your Watchlists</h4>
        <div v-for="w in watchlists" :key="w.id" style="border:1px solid #334155;border-radius:8px;padding:10px;margin-bottom:8px;background:#0f172a">
          <div style="display:flex;align-items:center;gap:8px"><strong style="flex:1">{{w.name}}</strong><span style="font-size:11px;background:#1e293b;padding:2px 6px;border-radius:999px">{{w.rules?.length||0}} rules</span><button @click="removeWL(w.id)" style="background:#7f1d1d;border:none;color:#fecaca;padding:2px 6px;border-radius:6px;cursor:pointer">×</button></div>
          <div v-if="w.rules?.length" style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px">
            <span v-for="r in w.rules" :key="r.id" style="font-size:11px;background:#1e293b;border:1px solid #334155;padding:3px 8px;border-radius:999px">{{r.rule_type}}: {{r.value}} <a @click.prevent="removeRule(w.id, r.id)" href="#" style="color:#fca5a5;margin-left:4px">×</a></span>
          </div>
          <div style="margin-top:8px;display:flex;gap:6px">
            <input :id="'add-'+w.id" placeholder="add rule value" style="flex:1;padding:6px;border-radius:6px;border:1px solid #334155;background:#020617;color:#e2e8f0;font-size:12px" @keyup.enter="addRule(w.id, $event.target.value, $event)"/>
            <select :id="'type-'+w.id" style="padding:6px;border-radius:6px;background:#020617;color:#e2e8f0;border:1px solid #334155;font-size:12px"><option value="keyword">keyword</option><option value="entity">entity</option><option value="topic">topic</option></select>
            <button @click="addRule(w.id, document.getElementById('add-'+w.id).value, null, document.getElementById('type-'+w.id).value)" style="padding:6px 10px;background:#0ea5e9;border:none;border-radius:6px;cursor:pointer;font-size:12px">Add</button>
          </div>
        </div>
        <small style="opacity:0.6">Rules fire on enriched docs: keyword ∈ text, entity ∈ NER, topic ∈ topics, sentiment == label. Alerts pushed via <code>ws/alerts/</code>.</small>
      </div>
      <div style="background:#1e293b;padding:16px;border-radius:12px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
          <h3 style="margin:0">Recent Alerts</h3>
          <span :style="{background: wsOk?'#16a34a':'#7f1d1d', padding:'2px 8px', borderRadius:'999px', fontSize:'12px'}">{{wsOk?'● live':'○ offline'}}</span>
          <span style="opacity:0.6;font-size:12px">{{alerts.length}} total · {{unread}} unread</span>
          <button @click="markAllRead" style="margin-left:auto;padding:6px 10px;background:#0f172a;border:1px solid #334155;color:#e2e8f0;border-radius:6px;cursor:pointer">Mark all read</button>
          <button @click="load" style="padding:6px 10px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer">Refresh</button>
        </div>
        <div v-for="a in alerts" :key="a.id" :style="{padding:'10px', borderLeft: a.is_read?'3px solid #334155':'3px solid #38bdf8', background: a.is_read?'#0f172a':'#1e3a5f', borderRadius:'8px', marginBottom:'8px', display:'flex', gap:'10px', alignItems:'center'}">
          <div style="flex:1">
            <div style="display:flex;gap:8px;align-items:center">
              <strong>{{a.rule_value || a.rule || a.id.slice(0,8)}}</strong>
              <span style="font-size:11px;background:#020617;padding:2px 6px;border-radius:999px">{{a.severity || 'medium'}}</span>
              <span v-if="!a.is_read" style="font-size:11px;background:#38bdf8;color:#020617;padding:2px 6px;border-radius:999px">new</span>
            </div>
            <div style="opacity:0.8;font-size:13px;margin-top:2px">{{a.document_title || a.document || ''}}</div>
            <small style="opacity:0.6">{{fmt(a.triggered_at)}}</small>
          </div>
          <button v-if="!a.is_read" @click="markRead(a.id)" style="padding:6px 10px;background:#0f172a;border:1px solid #334155;color:#e2e8f0;border-radius:6px;cursor:pointer">Mark read</button>
        </div>
        <p v-if="!alerts.length" style="opacity:0.6">No alerts yet. Create a watchlist (e.g. keyword <code>election</code>) and trigger a collection at <code>/Sources</code>.</p>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
const wlName=ref(''), ruleValue=ref(''), ruleType=ref('keyword')
const watchlists=ref([]), alerts=ref([]), wsOk=ref(false)
let ws=null
const unread = computed(()=> alerts.value.filter(a=>!a.is_read).length)
function fmt(s){ try{ return s? new Date(s).toLocaleString(): ''}catch{ return s||'' } }
async function load(){
  try{ const {data}=await axios.get('/api/alerts/watchlists/'); watchlists.value=data.results||data||[] }catch{ watchlists.value=[] }
  try{ const {data}=await axios.get('/api/alerts/'); alerts.value=(data.results||data||[]).slice(0,100) }catch{ alerts.value=[] }
}
async function createWatchlist(){
  if(!wlName.value || !ruleValue.value) return
  const {data: wl}=await axios.post('/api/alerts/watchlists/', {name: wlName.value})
  await axios.post(`/api/alerts/watchlists/${wl.id}/rules/`, {watchlist: wl.id, rule_type: ruleType.value, value: ruleValue.value})
  wlName.value=''; ruleValue.value=''
  await load()
}
async function addRule(wlId, value, evt, typeOverride){
  const v = (value||'').trim()
  if(!v) return
  const t = typeOverride || (document.getElementById('type-'+wlId)?.value) || 'keyword'
  await axios.post(`/api/alerts/watchlists/${wlId}/rules/`, {watchlist: wlId, rule_type: t, value: v})
  if(evt && evt.target) evt.target.value=''
  await load()
}
async function removeWL(id){ if(!confirm('Delete watchlist?')) return; await axios.delete(`/api/alerts/watchlists/${id}/`); await load() }
async function removeRule(wlId, ruleId){ await axios.delete(`/api/alerts/watchlists/${wlId}/rules/${ruleId}/`); await load() }
async function markRead(id){ await axios.post(`/api/alerts/${id}/read/`); await load() }
async function markAllRead(){ await axios.post('/api/alerts/read-all/'); await load() }
function connectWS(){
  try{
    const proto = location.protocol==='https:'?'wss:':'ws:'
    const token = localStorage.getItem('access') || ''
    const url = `${proto}//${location.host}/ws/alerts/${token?`?token=${encodeURIComponent(token)}`:''}`
    ws = new WebSocket(url)
    ws.onopen = ()=> wsOk.value=true
    ws.onclose = ()=> { wsOk.value=false; setTimeout(connectWS, 5000) }
    ws.onerror = ()=> wsOk.value=false
    ws.onmessage = (e)=>{ try{ const d=JSON.parse(e.data); if(d.type!=='connected' && d.type!=='pong') alerts.value.unshift(d); }catch{} }
  }catch{ wsOk.value=false }
}
onMounted(()=>{ load(); connectWS() })
onUnmounted(()=>{ try{ ws?.close()}catch{} })
</script>
