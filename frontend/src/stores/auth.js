import { defineStore } from 'pinia'
import axios from 'axios'
export const useAuthStore = defineStore('auth', {
  state: () => ({ token: localStorage.getItem('access') || '', refresh: localStorage.getItem('refresh') || '', user: JSON.parse(localStorage.getItem('user')||'null') }),
  getters: { isAuthenticated: (s)=> !!s.token, role: (s)=> s.user?.role || '' },
  actions: {
    async login(username, password) {
      const { data } = await axios.post('/api/auth/token/', { username, password })
      this.token = data.access; this.refresh = data.refresh
      localStorage.setItem('access', data.access); localStorage.setItem('refresh', data.refresh)
      axios.defaults.headers.common['Authorization'] = 'Bearer ' + data.access
      // fetch profile if endpoint exists
      try{ const {data: me}=await axios.get('/api/auth/users/me/'); this.user=me; localStorage.setItem('user', JSON.stringify(me)) }catch{ this.user={username} }
    },
    async refreshToken(){
      try{
        const {data}=await axios.post('/api/auth/token/refresh/', {refresh: this.refresh})
        this.token=data.access; this.refresh=data.refresh||this.refresh
        localStorage.setItem('access', this.token); if(data.refresh) localStorage.setItem('refresh', data.refresh)
        axios.defaults.headers.common['Authorization']='Bearer '+this.token
        return true
      }catch{ this.logout(); return false }
    },
    logout(){
      const rt=this.refresh
      if(rt) axios.post('/api/auth/token/blacklist/',{refresh: rt}).catch(()=>{})
      this.token=''; this.refresh=''; this.user=null
      localStorage.removeItem('access'); localStorage.removeItem('refresh'); localStorage.removeItem('user')
      delete axios.defaults.headers.common['Authorization']
    },
    init(){
      if(this.token) axios.defaults.headers.common['Authorization'] = 'Bearer ' + this.token
      // interceptor: auto-refresh on 401
      axios.interceptors.response.use(r=>r, async err=>{
        const orig = err.config
        if(err.response?.status===401 && !orig._retry && this.refresh){
          orig._retry=true
          const ok=await this.refreshToken()
          if(ok){ orig.headers['Authorization']='Bearer '+this.token; return axios(orig) }
        }
        return Promise.reject(err)
      })
    }
  }
})
