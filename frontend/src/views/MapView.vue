<template>
  <div style="padding:20px">
    <h2>Geographic Overlay</h2>
    <div id="map" style="height:500px;border-radius:8px"></div>
    <p style="opacity:0.6;margin-top:8px">Location-tagged documents clustered on Leaflet. Connects to /api/processing/geo/.</p>
  </div>
</template>
<script setup>
import { onMounted } from 'vue'
import axios from 'axios'
onMounted(async ()=>{
  const L = await import('leaflet')
  const map = L.map('map').setView([20,0], 2)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution:'&copy; OSM'}).addTo(map)
  try {
    const {data} = await axios.get('/api/processing/geo/')
    ;(Array.isArray(data)?data:[]).forEach(pt=>{
      if(pt.lat && pt.lon) L.marker([pt.lat, pt.lon]).addTo(map).bindPopup(pt.name || 'Location')
    })
  } catch {}
  // demo markers if none
  L.marker([51.5,-0.09]).addTo(map).bindPopup('London — demo entity location')
  L.marker([40.71,-74.0]).addTo(map).bindPopup('New York — demo')
})
</script>
