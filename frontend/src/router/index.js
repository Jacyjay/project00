import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomePage.vue'),
    meta: { immersiveDock: true },
  },
  {
    path: '/checkins/new',
    name: 'checkin-new',
    component: () => import('../views/CheckinForm.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/checkins/:id',
    name: 'checkin-detail',
    component: () => import('../views/CheckinDetail.vue'),
    props: true,
  },
  {
    path: '/checkin',
    redirect: { name: 'checkin-new' },
  },
  {
    path: '/profile/:id',
    name: 'profile',
    component: () => import('../views/ProfilePage.vue'),
    props: true,
  },
  {
    path: '/messages',
    name: 'messages',
    component: () => import('../views/MessagesPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/messages/:partnerId',
    name: 'chat',
    component: () => import('../views/MessagesPage.vue'),
    meta: { requiresAuth: true },
    props: true,
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/LoginPage.vue'),
    meta: { hideChrome: true },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('../views/RegisterPage.vue'),
    meta: { hideChrome: true },
  },
  {
    path: '/cities/:city',
    name: 'CityDetail',
    component: () => import('../views/CityDetailPage.vue'),
  },
  {
    path: '/download',
    name: 'Download',
    component: () => import('../views/DownloadPage.vue'),
  },
  {
    path: '/my-footprint',
    name: 'MyFootprint',
    component: () => import('../views/MyFootprintPage.vue'),
    meta: { immersiveDock: true },
  },
  {
    path: '/feed',
    name: 'Feed',
    component: () => import('../views/FeedPage.vue'),
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      next({ name: 'login', query: { redirect: to.fullPath } })
      return
    }
  }
  next()
})

export default router
