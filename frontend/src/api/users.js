import api from './index'

export const getUser = (id) => api.get(`/api/users/${id}`)
export const getUserStats = (id) => api.get(`/api/users/${id}/stats`)
export const searchUsers = (q, limit = 10) => api.get('/api/users/search', { params: { q, limit } })

export const uploadAvatar = (file) => {
  const formData = new FormData()
  formData.append('avatar', file)
  return api.put('/api/users/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000,
  })
}

export const updateShowEmail = (showEmail) =>
  api.put('/api/users/me/show-email', { show_email: showEmail })
