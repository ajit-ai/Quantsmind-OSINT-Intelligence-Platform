<template>
  <div style="padding:20px">
    <h2>Search & Filtering</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px">
      <input v-model="q" placeholder="Search query..." style="flex:1;padding:8px;border-radius:6px;border:1px solid #334155;background:#1e293b;color:#e2e8f0"/>
      <select v-model="source" style="padding:8px;border-radius:6px"><option value="">All sources</option><option value="reuters_rss">Reuters</option><option value="bbc_rss">BBC</option></select>
      <button @click="doSearch" style="padding:8px 16px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer">Search</button>
    </div>
    <div v-for="h in hits" :key="h._id" style="background:#1e293b;padding:12px;border-radius:8px;margin-bottom:8px">
      <strong>{{h._source?.title || h.title || 'Untitled'}}</strong>
      <p style="opacity:0.8">{{(h._source?.text || h.content_text || '').slice(0,300)}}</p>
      <small>{{h._source?.source}} | {{h._source?.collected_at}}</small>
    </div>
    <p v-if="!hits.length" style="opacity:0.6">No results. Try a broader query or check Elasticsearch connectivity.</p>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import axios from 'axios'
const q = ref('')
const source = ref('')
const hits = ref([])
async function doSearch(){
  try {
    const {data} = await axios.get('/api/processing/search/', {params:{q: q.value, source: source.value || undefined}})
    hits.value = data.hits?.hits || data.results || []
    if(!hits.value.length && data.results) hits.value = data.results
    // fallback to document search
    if(!hits.value.length){
      const {data: d2} = await axios.get('/api/documents/', {params:{search: q.value}})
      hits.value = (d2.results || d2).map(d=>({_id:d.id, _source:{title:d.title, text:d.content_text, source:d.source_name, collected_at:d.collected_at}}))
    }
  } catch(e){ console.error(e) }
}
</script>
