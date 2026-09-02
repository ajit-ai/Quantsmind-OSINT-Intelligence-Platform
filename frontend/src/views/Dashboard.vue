<template>
  <div style="padding:20px">
    <h2>Intelligence Dashboard</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
      <div style="background:#1e293b;padding:16px;border-radius:8px">
        <h3>Ingestion Trend (30d)</h3>
        <v-chart :option="trendOption" autoresize style="height:280px" v-if="trendOption"/>
      </div>
      <div style="background:#1e293b;padding:16px;border-radius:8px">
        <h3>Sentiment Breakdown</h3>
        <v-chart :option="sentimentOption" autoresize style="height:280px"/>
      </div>
    </div>
    <div style="background:#1e293b;padding:16px;border-radius:8px;margin-top:16px">
      <h3>Recent Documents</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr v-for="d in docs" :key="d.id" style="border-bottom:1px solid #334155"><td style="padding:8px">{{d.title}}</td><td>{{d.source_name}}</td><td>{{d.collected_at}}</td><td><span :style="{color: sentimentColor(d)}">{{d.status}}</span></td></tr>
      </table>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import VChart from 'vue-echarts'
import * as echarts from 'echarts'
const docs = ref([])
const trends = ref([])
onMounted(async ()=>{
  try {
    const {data} = await axios.get('/api/documents/?page_size=10')
    docs.value = data.results || data
  } catch {}
  try {
    const {data} = await axios.get('/api/processing/trends/')
    trends.value = data
  } catch { trends.value = [{date:'2026-08-01',count:12},{date:'2026-08-02',count:18}] }
})
const trendOption = computed(()=>({
  xAxis:{type:'category', data: trends.value.map(t=>t.date)},
  yAxis:{type:'value'},
  series:[{data: trends.value.map(t=>t.count), type:'line', smooth:true, areaStyle:{}}],
  tooltip:{trigger:'axis'}
}))
const sentimentOption = { tooltip:{trigger:'item'}, series:[{type:'pie', data:[{value:40,name:'Neutral'},{value:25,name:'Positive'},{value:35,name:'Negative'}]}] }
const sentimentColor = (d)=> d.status==='indexed' ? '#22c55e' : '#eab308'
</script>
