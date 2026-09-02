import { defineStore } from 'pinia'
import axios from 'axios'
export const useAuthStore = defineStore('auth', {
  state: () => ({ token: localStorage.getItem('access') || '', refresh: localStorage.getItem('refresh') || '' }),
  actions: {
    async login(username, password) {
      const { data } = await axios.post('/api/auth/token/', { username, password })
      this.token = data.access; this.refresh = data.refresh
      localStorage.setItem('access', data.access); localStorage.setItem('refresh', data.refresh)
      axios.defaults.headers.common['Authorization'] = 'Bearer ' + data.access
    },
    logout() { this.token=''; this.refresh=''; localStorage.clear(); delete axios.defaults.headers.common['Authorization'] },
    init() { if(this.token) axios.defaults.headers.common['Authorization'] = 'Bearer ' + this.token }
  }
})
