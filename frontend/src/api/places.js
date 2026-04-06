import api from './index'

export const getPlaces = (q) => api.get('/api/places', { params: q ? { q } : {} })
export const getPlace = (id) => api.get(`/api/places/${id}`)
export const createPlace = (data) => api.post('/api/places', data)
