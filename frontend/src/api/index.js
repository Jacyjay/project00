import axios from 'axios'

import { API_BASE_URL } from '../lib/config'

const api = axios.create({
  baseURL: API_BASE_URL || '',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach auth token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor: clear stale token on 401 (but don't force redirect on public pages)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const token = localStorage.getItem('token')
      if (token) {
        // Only clear token and redirect if we previously had a token (stale session)
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        const path = typeof window !== 'undefined' ? window.location.pathname : '/'
        const guestAllowed = ['/', '/login', '/register']
        const isGuestAllowed = guestAllowed.some((p) => path === p || path.startsWith('/checkins/') || path.startsWith('/profile/'))
        if (!isGuestAllowed && typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api
