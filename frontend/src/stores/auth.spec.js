import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import axios from 'axios'
import { useAuthStore } from './auth.js'

vi.mock('axios')
describe('auth store', ()=>{
  beforeEach(()=>{ setActivePinia(createPinia()); localStorage.clear(); vi.clearAllMocks(); axios.defaults.headers.common={}; axios.interceptors = { response: { use: vi.fn() } } })
  it('login stores tokens and sets header', async ()=>{
    axios.post.mockResolvedValue({data:{access:'acc123', refresh:'ref123'}})
    axios.get.mockResolvedValue({data:{username:'test', role:'analyst'}})
    const store = useAuthStore()
    await store.login('test','pass')
    expect(localStorage.getItem('access')).toBe('acc123')
    expect(store.token).toBe('acc123')
    expect(axios.defaults.headers.common['Authorization']).toContain('Bearer')
  })
  it('refreshToken success', async ()=>{
    const store = useAuthStore()
    store.refresh='ref123'
    axios.post.mockResolvedValue({data:{access:'newacc', refresh:'newref'}})
    const ok = await store.refreshToken()
    expect(ok).toBe(true)
    expect(store.token).toBe('newacc')
  })
  it('logout clears and blacklists', async ()=>{
    const store = useAuthStore()
    store.token='acc'; store.refresh='ref'
    localStorage.setItem('access','acc'); localStorage.setItem('refresh','ref')
    axios.post.mockResolvedValue({data:{}})
    store.logout()
    expect(localStorage.getItem('access')).toBeNull()
    expect(store.token).toBe('')
  })
  it('init restores header', ()=>{
    localStorage.setItem('access','stored')
    const store = useAuthStore()
    store.token='stored'
    store.init()
    expect(axios.defaults.headers.common['Authorization']).toBe('Bearer stored')
  })
})
