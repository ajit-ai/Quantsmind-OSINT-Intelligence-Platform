<template>
  <div style="padding:20px">
    <div style="display:flex;align-items:center;gap:12px">
      <h2 style="flex:1">Sources & Collection Policies</h2>
      <button @click="triggerAll" style="padding:8px 14px;background:#0ea5e9;border:none;border-radius:8px;cursor:pointer">Trigger all active</button>
    </div>
    <div style="background:#1e293b;padding:12px;border-radius:12px;margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <span style="opacity:0.7;font-size:13px">Queue: <code>Ingestion queue</code> (Redis primary, RabbitMQ/Kafka via .env) · Policies live-editable per source</span>
      <span style="margin-left:auto;opacity:0.6;font-size:12px">{{sources.length}} sources</span>
    </div>
    <table style="width:100%;border-collapse:collapse;background:#1e293b;border-radius:12px;overflow:hidden">
      <thead><tr style="background:#020617;text-align:left;font-size:12px;opacity:0.8"><th style="padding:10px">Name</th><th>Type</th><th>URL</th><th>Interval</th><th>Policy (rps / robots / allowed)</th><th>Active</th><th>Action</th></tr></thead>
      <tbody>
        <tr v-for="s in sources" :key="s.id" style="border-top:1px solid #334155">
          <td style="padding:10px"><strong>{{s.name}}</strong><br/><small style="opacity:0.6">{{s.slug}}</small></td>
          <td><span style="background:#0f172a;padding:2px 6px;border-radius:999px;font-size:11px">{{s.source_type}}</span></td>
          <td style="max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"><a :href="s.url" target="_blank" style="color:#7dd3fc">{{s.url}}</a></td>
          <td style="text-align:center">{{s.collection_interval_minutes ?? 15}}m</td>
          <td style="font-size:11px;line-height:1.4">
            <span v-if="s.policies?.[0]">rps: {{s.policies[0].rate_limit_rps}} · robots: {{s.policies[0].respects_robots?'yes':'no'}}<br/>allow: {{(s.policies[0].allowed_domains||[]).join(', ') || '—'}}</span>
            <span v-else style="opacity:0.6">—</span>
          </td>
          <td style="text-align:center"><span :style="{background: s.is_active?'#16a34a':'#7f1d1d', padding:'2px 6px', borderRadius:'999px', fontSize:'11px'}">{{s.is_active?'on':'off'}}</span></td>
          <td><button @click="trigger(s.id)" :disabled="pending[s.id]" style="padding:6px 10px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer;opacity:0.95">{{pending[s.id]?'Queuing...':'Collect now'}}</button></td>
        </tr>
      </tbody>
    </table>
    <small style="opacity:0.6">Collect respects <code>CollectionPolicy</code> (robots.txt cache TTL 1h, throttling, allowlist, block auth/paywall). Trigger enqueues <code>poll_source</code> Celery task (acks_late + retry + DLQ).</small>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
const sources=ref([])
const pending=ref({})
async function load(){ const {data}=await axios.get('/api/sources/'); sources.value=data.results||data||[] }
async function trigger(id){ pending.value[id]=true; try{ await axios.post(`/api/sources/${id}/trigger/`)}catch(e){ alert(e.response?.data?.detail || e.message)} finally{ pending.value[id]=false } }
async function triggerAll(){ try{ await axios.post('/api/sources/trigger-all/'); alert('All active sources queued')}catch(e){ alert(e.response?.data?.detail || e.message)} }
onMounted(load)
</script>
