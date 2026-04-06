import api from './index'

export const publishCheckin = (formData) =>
  api.post('/api/checkins', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })

export const getMapCheckins = (limit = 200) =>
  api.get('/api/checkins/map', { params: { limit } })
export const reverseGeocodeCheckin = (latitude, longitude) =>
  api.get('/api/checkins/reverse-geocode', { params: { latitude, longitude } })
export const searchCheckinPlaces = (q, limit = 8) =>
  api.get('/api/checkins/search-places', { params: { q, limit }, timeout: 20000 })

export const getCheckin = (id) => api.get(`/api/checkins/${id}`)
export const deleteCheckin = (id) => api.delete(`/api/checkins/${id}`)
export const updateCheckin = (id, data) => api.patch(`/api/checkins/${id}`, data)
export const deleteComment = (checkinId, commentId) =>
  api.delete(`/api/checkins/${checkinId}/comments/${commentId}`)
export const searchUsers = (q, limit = 10) =>
  api.get('/api/users/search', { params: { q, limit } })

export const getPlaceCheckins = (placeId, limit = 50, offset = 0) =>
  api.get(`/api/checkins/place/${placeId}`, { params: { limit, offset } })

export const getUserCheckins = (userId, limit = 50, offset = 0) =>
  api.get(`/api/checkins/user/${userId}`, { params: { limit, offset } })

export const getPlacePhotos = (placeId, limit = 50) =>
  api.get(`/api/checkins/place/${placeId}/photos`, { params: { limit } })

// Likes
export const likeCheckin = (checkinId) => api.post(`/api/checkins/${checkinId}/like`)
export const unlikeCheckin = (checkinId) => api.delete(`/api/checkins/${checkinId}/like`)

// Comments
export const getComments = (checkinId) => api.get(`/api/checkins/${checkinId}/comments`)
export const addComment = (checkinId, content) => api.post(`/api/checkins/${checkinId}/comments`, { content })

// Cities
export const getHotCities = () => api.get('/api/cities/hot')
export const getCityCheckins = (city, params = {}) => api.get(`/api/cities/${encodeURIComponent(city)}/checkins`, { params })

// AI Caption
export const generateCaption = (data) =>
  api.post('/api/ai/generate-caption', data, {
    timeout: 90000,
  })

// City intro (AI-generated, cached server-side)
export const getCityIntro = (city) =>
  api.get(`/api/cities/${encodeURIComponent(city)}/intro`)

// Footprint report (AI-generated, pre-cached server-side)
export const getFootprintReport = () => api.get('/api/footprint-report')
export const refreshFootprintReport = () => api.post('/api/footprint-report/refresh')
