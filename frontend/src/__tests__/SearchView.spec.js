import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
import SearchView from '../views/SearchView.vue'

vi.mock('axios')

describe('SearchView.vue', () => {
  beforeEach(()=>{ setActivePinia(createPinia()); vi.mocked(axios.get).mockReset() })

  it('performs search and renders hits with highlights', async () => {
    axios.get.mockImplementation((url)=>{
      if(url.includes('/api/sources/')) return Promise.resolve({data:[]})
      if(url.includes('/api/processing/search')){
        return Promise.resolve({data:{ hits:{hits:[{_id:'1', _source:{title:'Election news', text:'election results in London', source:'bbc', sentiment:{label:'neutral'}, entities:[{text:'London',type:'GPE'}], language:'en', collected_at:new Date().toISOString()}, highlight:{text:['<em>election</em> results']}}], total:{value:1}}, aggregations:{by_source:{buckets:[{key:'bbc',doc_count:1}]}} }})
      }
      return Promise.resolve({data:{results:[]}})
    })
    const w = mount(SearchView)
    await new Promise(r=>setTimeout(r,30))
    // set query and trigger search
    w.vm.q = 'election'
    await w.vm.doSearch()
    await w.vm.$nextTick()
    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/api/processing/search/'), expect.anything())
    expect(w.vm.hits.length).toBe(1)
    expect(w.html()).toContain('Election news')
  })

  it('shows fallback message when no hits', async () => {
    axios.get.mockResolvedValue({data:{hits:{hits:[]}, aggregations:{}}})
    const w = mount(SearchView)
    w.vm.hits=[]
    await w.vm.$nextTick()
    expect(w.text()).toContain('No results')
  })
})
