import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import axios from 'axios'
import SourcesView from '../views/SourcesView.vue'

vi.mock('axios')
describe('SourcesView.vue', ()=>{
  beforeEach(()=>{ vi.mocked(axios.get).mockReset(); vi.mocked(axios.post).mockReset() })
  it('renders sources table and triggers collection', async ()=>{
    axios.get.mockResolvedValue({data:[{id:'1', name:'BBC', slug:'bbc', source_type:'rss', url:'http://example.com/rss', collection_interval_minutes:15, policies:[{rate_limit_rps:1, respects_robots:true, allowed_domains:[]}], is_active:true}]})
    const w = mount(SourcesView)
    await new Promise(r=>setTimeout(r,30))
    expect(w.text()).toContain('Sources & Collection')
    // trigger
    axios.post.mockResolvedValue({data:{status:'queued'}})
    await w.vm.trigger('1')
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/trigger/'))
  })
  it('trigger-all', async ()=>{
    axios.get.mockResolvedValue({data:[]})
    axios.post.mockResolvedValue({data:{status:'queued_all'}})
    const w = mount(SourcesView)
    await w.vm.triggerAll()
    expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('trigger-all'))
  })
})
