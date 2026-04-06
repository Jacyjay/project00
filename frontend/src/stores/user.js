import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getMe } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const token = ref(localStorage.getItem('token') || '')

  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const userId = computed(() => user.value?.id)

  function setAuth(tokenValue, userData) {
    token.value = tokenValue
    user.value = userData
    localStorage.setItem('token', tokenValue)
    localStorage.setItem('user', JSON.stringify(userData))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  async function fetchUser() {
    try {
      const res = await getMe()
      user.value = res.data
      localStorage.setItem('user', JSON.stringify(res.data))
    } catch {
      logout()
    }
  }

  return { user, token, isLoggedIn, userId, setAuth, logout, fetchUser }
})
