import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import DashboardView from './views/DashboardView.vue'
import SignInView from './views/SignInView.vue'
import SignUpView from './views/SignUpView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/dashboard', name: 'dashboard', component: DashboardView },
    { path: '/signin', name: 'signin', component: SignInView },
    { path: '/signup', name: 'signup', component: SignUpView },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
