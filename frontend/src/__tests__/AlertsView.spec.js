import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
import AlertsView from '../views/AlertsView.vue'

vi.mock('axios')
describe('AlertsView.vue', ()=>{
  beforeEach(()=>{ setActivePinia(createPinia()); vi.mocked(axios.get).mockReset(); vi.mocked(axios.post).mockReset(); localStorage.setItem('access','fake') })
  it('loads watchlists and alerts', async ()=>{
    axios.get.mockImplementation(url=>{
      if(url.includes('/watchlists')) return Promise.resolve({data:[{id:'wl1', name:'Test', rules:[{id:'r1', rule_type:'keyword', value:'election'}]}]})
      if(url.includes('/api/alerts/')) return Promise.resolve({data:[{id:'a1', rule_value:'election', document_title:'Doc', triggered_at:new Date().toISOString(), is_read:false, severity:'medium'}]})
      return Promise.resolve({data:[]})
    })
    const w = mount(AlertsView)
    await new Promise(r=>setTimeout(r,40))
    expect(axios.get).toHaveBeenCalled()
    expect(w.text()).toContain('Watchlists')
  })
  it('creates watchlist and rule', async ()=>{
    axios.get.mockResolvedValue({data:[]})
    axios.post.mockImplementation((url, data)=>{
      if(url.includes('/watchlists') && !url.includes('/rules')) return Promise.resolve({data:{id:'new1', name:data.name}})
      if(url.includes('/rules')) return Promise.resolve({data:{id:'r2'}})
      return Promise.resolve({data:{}})
    })
    const w = mount(AlertsView)
    w.vm.wlName='E2E List'
    w.vm.ruleValue='election'
    w.vm.ruleType='keyword'
    await w.vm.createWatchlist()
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/api/alerts/watchlists/'), expect.objectContaining({name:'E2E List'}))
  })
})
