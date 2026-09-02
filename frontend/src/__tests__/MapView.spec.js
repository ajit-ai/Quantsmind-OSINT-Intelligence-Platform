import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import axios from 'axios'
import MapView from '../views/MapView.vue'

vi.mock('axios')
vi.mock('leaflet', () => {
  const L = {
    map: vi.fn(()=>({ setView: vi.fn().mockReturnThis(), fitBounds: vi.fn(), addLayer: vi.fn() })),
    tileLayer: vi.fn(()=>({ addTo: vi.fn() })),
    marker: vi.fn(()=>({ bindPopup: vi.fn().mockReturnThis(), addTo: vi.fn() })),
    latLngBounds: vi.fn(()=>({ pad: vi.fn().mockReturnThis()})),
    layerGroup: vi.fn(()=>({ addTo: vi.fn().mockReturnThis(), clearLayers: vi.fn()})),
    markerClusterGroup: vi.fn(()=>({ addTo: vi.fn(), addLayer: vi.fn()}))
  }
  return { default: L, ...L }
})

describe('MapView.vue', ()=>{
  beforeEach(()=>{ vi.mocked(axios.get).mockReset() })
  it('fetches geo and renders map placeholder', async ()=>{
    axios.get.mockResolvedValue({data:[{name:'London',type:'GPE',lat:51.5,lon:-0.1}]})
    const w = mount(MapView)
    await new Promise(r=>setTimeout(r,30))
    expect(w.text()).toContain('Geographic Overlay')
    expect(w.find('#map').exists()).toBe(true)
  })
})
