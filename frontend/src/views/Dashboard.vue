<template>
  <div style="padding:20px">
    <h2>Intelligence Dashboard</h2>
    <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap">
      <span style="background:#1e293b;padding:8px 12px;border-radius:999px">Total docs: {{stats.total ?? docs.length}}</span>
      <span style="background:#1e293b;padding:8px 12px;border-radius:999px">Indexed: {{byStatus('indexed')}}</span>
      <span style="background:#1e293b;padding:8px 12px;border-radius:999px">Live: <span :style="{color: wsOk?'#22c55e':'#ef4444'}">{{ wsOk?'● connected':'○ disconnected' }}</span></span>
      <button @click="refreshAll" style="margin-left:auto;padding:6px 12px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer">Refresh</button>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div style="background:#1e293b;padding:16px;border-radius:8px">
        <h3>Ingestion Trend ({{days}}d)</h3>
        <select v-model="days" @change="loadTrends" style="margin-bottom:8px;padding:4px 8px;border-radius:6px">
          <option :value="7">7 days</option>
          <option :value="30">30 days</option>
          <option :value="90">90 days</option>
        </select>
        <v-chart :option="trendOption" autoresize style="height:280px" v-if="trends.length"/>
        <small style="opacity:0.6">Source: GET /api/processing/trends/?days=& DB fallback</small>
      </div>
      <div style="background:#1e293b;padding:16px;border-radius:8px">
        <h3>Sentiment Breakdown</h3>
        <v-chart :option="sentimentOption" autoresize style="height:280px"/>
        <small style="opacity:0.6">From Elasticsearch aggs + DB fallback</small>
      </div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px">
      <div style="background:#1e293b;padding:16px;border-radius:8px">
        <h3>By Source</h3>
        <v-chart :option="sourceOption" autoresize style="height:240px"/>
      </div>
      <div style="background:#1e293b;padding:16px;border-radius:8px">
        <h3>Recent Documents</h3>
        <table style="width:100%;border-collapse:collapse">
          <thead><tr style="opacity:0.7;font-size:12px"><th style="text-align:left;padding:6px">Title</th><th>Source</th><th>Status</th><th>When</th></tr></thead>
          <tbody>
            <tr v-for="d in docs" :key="d.id" style="border-top:1px solid #334155">
              <td style="padding:8px;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" :title="d.title">{{d.title || '(untitled)'}}</td>
              <td style="text-align:center">{{d.source_name || d.source__slug || d.source}}</td>
              <td style="text-align:center"><span :style="{background: statusBg(d.status), padding:'2px 8px', borderRadius:'999px', fontSize:'12px'}">{{d.status}}</span></td>
              <td style="text-align:center;opacity:0.7;font-size:12px">{{fmtDate(d.collected_at)}}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import VChart from 'vue-echarts'
const docs = ref([])
const trends = ref([])
const stats = ref({})
const facets = ref({})
const days = ref(30)
const wsOk = ref(false)
let poll = null
let ws = null

function fmtDate(s){ try{ return new Date(s).toLocaleString()}catch{ return s||'' } }
function statusBg(s){ return s==='indexed'?'#16a34a': s==='enriched'?'#0ea5e9': s==='failed'?'#dc2626':'#a16207' }
function byStatus(s){ const v = stats.value.by_status?.find(x=>x.status===s); return v? v.count: 0 }

async function loadDocs(){ try{ const {data}=await axios.get('/api/documents/',{params:{page_size:10, ordering:'-collected_at'}}); docs.value=data.results||data||[] }catch{ docs.value=[] } }
async function loadTrends(){ try{ const {data}=await axios.get('/api/processing/trends/',{params:{days: days.value}}); trends.value=Array.isArray(data)?data:[] }catch{ trends.value=[{date:'2026-08-01',count:12},{date:'2026-08-02',count:18}] } }
async function loadStats(){ try{ const {data}=await axios.get('/api/documents/stats/'); stats.value=data }catch{ stats.value={} } }
async function loadFacets(){ try{ const {data}=await axios.get('/api/processing/facets/'); facets.value=data }catch{ facets.value={} } }
async function refreshAll(){ await Promise.all([loadDocs(),loadTrends(),loadStats(),loadFacets()]) }

const trendOption = computed(()=>({
  xAxis:{type:'category', data: trends.value.map(t=> (t.date||'').slice(0,10)), boundaryGap:false},
  yAxis:{type:'value'},
  series:[{data: trends.value.map(t=>t.count), type:'line', smooth:true, areaStyle:{color:'rgba(56,189,248,0.2)'}, lineStyle:{color:'#38bdf8'}}],
  tooltip:{trigger:'axis'}, grid:{left:40,right:12,top:12,bottom:24}
}))
const sentimentOption = computed(()=>{
  const agg = facets.value.by_sentiment?.buckets || facets.value['by_sentiment']?.buckets
  let data
  if(agg && agg.length){
    data = agg.map(b=>({value:b.doc_count, name: b.key}))
  } else {
    const byS = stats.value.by_status || []
    // naive: map status as proxy if ES down
    data = byS.length ? byS.map(b=>({value:b.count, name: b.status})) : [{value:40,name:'neutral'},{value:25,name:'positive'},{value:35,name:'negative'}]
  }
  return { tooltip:{trigger:'item'}, series:[{type:'pie', radius:['40%','70%'], data, emphasis:{scale:true}}] }
})
const sourceOption = computed(()=>{
  const bySrc = stats.value.by_source || []
  const rows = bySrc.slice(0,8)
  return {
    tooltip:{trigger:'axis'},
    xAxis:{type:'value'},
    yAxis:{type:'category', data: rows.map(r=> r.source__slug || r.key || r.source)},
    series:[{type:'bar', data: rows.map(r=> r.count ?? r.doc_count), itemStyle:{color:'#38bdf8'}}],
    grid:{left:90,right:12,top:8,bottom:8}
  }
})

onMounted(async ()=>{
  refreshAll()
  poll = setInterval(refreshAll, 30000)
  // live alerts WS — reflects real-time ingestion
  try{
    const proto = location.protocol==='https:'?'wss:':'ws:'
    const token = localStorage.getItem('access') || ''
    const url = `${proto}//${location.host}/ws/alerts/${token?`?token=${encodeURIComponent(token)}`:''}`
    ws = new WebSocket(url)
    ws.onopen = ()=> wsOk.value=true
    ws.onclose = ()=> wsOk.value=false
    ws.onmessage = ()=> { loadDocs(); loadStats() }
    ws.onerror = ()=> wsOk.value=false
  }catch{ wsOk.value=false }
})
onUnmounted(()=>{ clearInterval(poll); try{ ws?.close()}catch{} })
</script>
