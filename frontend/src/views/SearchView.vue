<template>
  <div style="padding:20px">
    <h2>Search & Filtering</h2>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap;align-items:center">
      <input v-model="q" @keyup.enter="doSearch" placeholder="Search query... (title + text, ES multi_match)" style="flex:1;min-width:240px;padding:8px;border-radius:6px;border:1px solid #334155;background:#1e293b;color:#e2e8f0"/>
      <select v-model="source" style="padding:8px;border-radius:6px;background:#1e293b;color:#e2e8f0;border:1px solid #334155"><option value="">All sources</option><option v-for="s in sources" :key="s.slug" :value="s.slug">{{s.slug}}</option></select>
      <select v-model="language" style="padding:8px;border-radius:6px;background:#1e293b;color:#e2e8f0;border:1px solid #334155"><option value="">All languages</option><option value="en">en</option><option value="fr">fr</option><option value="de">de</option></select>
      <select v-model="sentiment" style="padding:8px;border-radius:6px;background:#1e293b;color:#e2e8f0;border:1px solid #334155"><option value="">Any sentiment</option><option value="positive">positive</option><option value="neutral">neutral</option><option value="negative">negative</option></select>
      <button @click="doSearch" :disabled="loading" style="padding:8px 16px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer;opacity:0.9">{{loading?'Searching...':'Search'}}</button>
      <span v-if="meta.db_fallback" style="background:#a16207;padding:4px 8px;border-radius:999px;font-size:12px">DB fallback (ES unavailable)</span>
    </div>
    <div style="display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap">
      <div v-for="agg in aggChips" :key="agg.key" style="background:#0f172a;border:1px solid #334155;padding:6px 10px;border-radius:999px;font-size:12px">
        <strong>{{agg.key}}:</strong> <span v-for="b in agg.buckets.slice(0,4)" :key="b.key" style="margin-left:6px;opacity:0.8">{{b.key}} ({{b.doc_count}})</span>
      </div>
    </div>
    <div v-for="h in hits" :key="h._id || h.id" style="background:#1e293b;padding:12px;border-radius:8px;margin-bottom:8px">
      <div style="display:flex;gap:8px;align-items:center">
        <strong style="flex:1">{{h._source?.title || h.title || '(untitled)'}}</strong>
        <span style="font-size:11px;background:#0f172a;padding:2px 6px;border-radius:999px">{{h._source?.source || h.source_name || ''}}</span>
        <span v-if="h._source?.sentiment?.label" :style="{fontSize:'11px',background: sentBg(h._source.sentiment.label), padding:'2px 6px', borderRadius:'999px'}">{{h._source.sentiment.label}}</span>
        <span style="font-size:11px;opacity:0.6">{{fmt(h._source?.collected_at)}}</span>
      </div>
      <p style="opacity:0.85;margin:6px 0" v-html="highlight(h)"></p>
      <div v-if="(h._source?.entities||[]).length" style="display:flex;gap:6px;flex-wrap:wrap">
        <span v-for="e in (h._source.entities).slice(0,6)" :key="e.text+ e.type" style="font-size:11px;background:#020617;border:1px solid #334155;padding:2px 6px;border-radius:999px">{{e.text}} <small style="opacity:0.6">{{e.type}}</small></span>
      </div>
      <small style="opacity:0.6"><a :href="h._source?.url || h.url" target="_blank" style="color:#7dd3fc">open source</a> · lang: {{h._source?.language || h.language || '—'}}</small>
    </div>
    <p v-if="!loading && !hits.length" style="opacity:0.6">No results. Try a broader query, clear filters, or check <code>/api/processing/search/?q=...</code> and ES health.</p>
    <small style="opacity:0.5">Total: {{total ?? hits.length}} · ES aggregations below table drive facet chips</small>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
const q = ref('')
const source = ref('')
const language = ref('')
const sentiment = ref('')
const hits = ref([])
const total = ref(0)
const aggs = ref({})
const meta = ref({})
const loading = ref(false)
const sources = ref([])
function fmt(s){ try{ return s? new Date(s).toLocaleDateString():'' }catch{ return s||'' } }
function sentBg(l){ return l==='positive'?'#16a34a': l==='negative'?'#dc2626':'#64748b' }
function highlight(h){
  const hl = h.highlight?.text?.[0] || h.highlight?.title?.[0]
  if(hl) return hl.slice(0,400)
  const t = (h._source?.text || h.content_text || '').slice(0,400)
  if(!t) return '<em style="opacity:0.6">no text</em>'
  // naive highlight query tokens
  let out = t
  if(q.value){
    const esc = q.value.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')
    out = out.replace(new RegExp(`(${esc})`,'ig'),'<mark style="background:#fef08a;color:#000;padding:0 2px;border-radius:2px">$1</mark>')
  }
  return out
}
const aggChips = computed(()=>{
  const out=[]
  const a = aggs.value
  if(a.by_source) out.push({key:'source', buckets: (a.by_source.buckets||a.by_source) })
  else if(a['by_source']) out.push({key:'source', buckets: a['by_source'].buckets})
  if(a.by_sentiment) out.push({key:'sentiment', buckets: a.by_sentiment.buckets})
  if(a.by_language) out.push({key:'language', buckets: a.by_language.buckets})
  return out.filter(x=> x.buckets && x.buckets.length)
})
async function loadSources(){ try{ const {data}=await axios.get('/api/sources/'); sources.value=data.results||data||[] }catch{ sources.value=[] } }
async function doSearch(){
  loading.value=true
  try{
    const {data}=await axios.get('/api/processing/search/',{params:{q: q.value||undefined, source: source.value||undefined, language: language.value||undefined, sentiment: sentiment.value||undefined, size:20}})
    hits.value = data.hits?.hits || []
    total.value = data.hits?.total?.value ?? data.hits?.total ?? hits.value.length
    aggs.value = data.aggregations || {}
    meta.value = {db_fallback: !!data.db_fallback, error: data.error}
    if(!hits.value.length && !data.error){
      // also try DB doc search as secondary
      const {data: d2}=await axios.get('/api/documents/',{params:{search: q.value || undefined, source: source.value? undefined: undefined}})
      const rows = d2.results||d2
      if(Array.isArray(rows) && rows.length && hits.value.length===0){
        hits.value = rows.map(d=>({_id:d.id, _source:{title:d.title, text:d.content_text, source: d.source_name || d.source__slug, language:d.language, collected_at:d.collected_at, url:d.url, sentiment:{}, entities:[]}}))
      }
    }
  }catch(e){ console.error(e); hits.value=[] } finally{ loading.value=false }
}
onMounted(()=>{ loadSources(); doSearch() })
</script>
