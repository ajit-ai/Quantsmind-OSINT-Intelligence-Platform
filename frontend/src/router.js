import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from './views/Dashboard.vue'
import SearchView from './views/SearchView.vue'
import MapView from './views/MapView.vue'
import AlertsView from './views/AlertsView.vue'
import SourcesView from './views/SourcesView.vue'
import LoginView from './views/LoginView.vue'
export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/search', component: SearchView },
    { path: '/map', component: MapView },
    { path: '/alerts', component: AlertsView },
    { path: '/sources', component: SourcesView },
    { path: '/login', component: LoginView },
  ]
})
