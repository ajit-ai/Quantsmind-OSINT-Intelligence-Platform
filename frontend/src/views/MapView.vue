<template>
  <div style="padding:20px">
    <h2>Geographic Overlay</h2>
    <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;flex-wrap:wrap">
      <button @click="fitAll" style="padding:6px 10px;background:#38bdf8;border:none;border-radius:6px;cursor:pointer">Fit all</button>
      <span style="opacity:0.7;font-size:13px">{{markers.length}} locations · clustering via Leaflet markerCluster (fallback: plain markers) · Source: GET /api/processing/geo/</span>
    </div>
    <div id="map" style="height:560px;border-radius:12px;border:1px solid #334155"></div>
    <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap">
      <span v-for="m in markers.slice(0,12)" :key="m.name" style="background:#1e293b;border:1px solid #334155;padding:4px 8px;border-radius:999px;font-size:12px">{{m.name}} <small style="opacity:0.6">{{m.type}}</small></span>
    </div>
  </div>
</template>
<script setup>
import { onMounted, ref } from 'vue'
import axios from 'axios'
const markers = ref([])
let map, group
async function loadGeo(){
  try{
    const {data}=await axios.get('/api/processing/geo/')
    markers.value = Array.isArray(data)? data: []
  }catch{ markers.value=[] }
  // ensure demo if empty (so map is not blank in fresh install)
  if(!markers.value.length){
    markers.value = [{name:'London',type:'GPE',lat:51.5074,lon:-0.1278},{name:'New York',type:'GPE',lat:40.7128,lon:-74.006},{name:'Delhi',type:'GPE',lat:28.6139,lon:77.209},{name:'Mumbai',type:'GPE',lat:19.076,lon:72.8777}]
  }
  render()
}
function render(){
  if(!map) return
  try{ group?.clearLayers()}catch{}
  const L = window.L
  group = L.layerGroup().addTo(map)
  // try markerCluster if available
  let cluster = null
  try{
    if(L.markerClusterGroup) cluster = L.markerClusterGroup()
  }catch{}
  const target = cluster || group
  if(cluster) map.addLayer(cluster)
  markers.value.forEach(pt=>{
    if(pt.lat==null || pt.lon==null) return
    const m = L.marker([pt.lat, pt.lon]).bindPopup(`<strong>${pt.name}</strong><br/><small>${pt.type||''}</small>`)
    if(cluster) cluster.addLayer(m); else m.addTo(group)
  })
}
function fitAll(){
  if(!map || !markers.value.length) return
  const L = window.L
  const pts = markers.value.filter(p=>p.lat!=null && p.lon!=null).map(p=>[p.lat,p.lon])
  if(pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.3))
}
onMounted(async ()=>{
  const L = await import('leaflet')
  window.L = L
  // markerCluster is optional — CDN fallback if installed
  try{ await import('leaflet.markercluster')}catch{}
  map = L.map('map').setView([20,0], 2)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OSM', maxZoom:18}).addTo(map)
  await loadGeo()
  fitAll()
})
</script>
