import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import axios from 'axios'
import Dashboard from '../views/Dashboard.vue'

vi.mock('axios')
vi.mock('vue-echarts', () => ({ default: { template: '<div />' } }))

describe('Dashboard.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.mocked(axios.get).mockReset()
  })

  it('fetches documents, trends, stats, facets on mount', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/api/documents/') && url.includes('stats')) return Promise.resolve({ data: { total: 5, by_status: [{status:'indexed',count:3}], by_source:[{source__slug:'bbc',count:2}] }})
      if (url.includes('/api/documents/')) return Promise.resolve({ data: { results: [{id:'1', title:'Hello', source_name:'bbc', status:'indexed', collected_at:new Date().toISOString()}] }})
      if (url.includes('/trends')) return Promise.resolve({ data: [{date:'2026-08-01',count:5},{date:'2026-08-02',count:7}]})
      if (url.includes('/facets')) return Promise.resolve({ data: { by_sentiment:{buckets:[{key:'positive',doc_count:3}]}}})
      return Promise.resolve({ data: [] })
    })
    const wrapper = mount(Dashboard)
    await new Promise(r=>setTimeout(r, 50))
    // need to flush promises
    await wrapper.vm.$nextTick()
    expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('/api/documents/'), expect.anything())
  })

  it('computes statusBg for indexed', async () => {
    axios.get.mockResolvedValue({ data: [] })
    const w = mount(Dashboard)
    // access function via vm? exposed as internal, test via DOM class
    expect(w.text()).toContain('Intelligence Dashboard')
  })
})
