import { createRouter, createWebHistory } from 'vue-router'
import Home from '@/views/Home.vue'
import MainLayout from '@/components/Layout/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/Login.vue')
    },
    {
      path: '/app',
      component: MainLayout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '/dashboard',
          name: 'dashboard',
          component: () => import('@/views/Dashboard.vue')
        },
        {
          path: '/team',
          name: 'team',
          component: () => import('@/views/TeamManagement.vue')
        },
        {
          path: '/market',
          name: 'market',
          component: () => import('@/views/TransferMarket.vue')
        },
        {
          path: '/matches',
          name: 'matches',
          component: () => import('@/views/Matches.vue')
        },
        {
          path: '/youth',
          name: 'youth',
          component: () => import('@/views/YouthAcademy.vue')
        }
      ]
    }
  ]
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem('token')
  
  if (to.meta.requiresAuth && !isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})

export default router 