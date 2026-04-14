import api from './index'

export const createJourney = (data) => api.post('/api/journeys', data)
export const getMyJourneys = () => api.get('/api/journeys/me')
export const getJourney = (id) => api.get(`/api/journeys/${id}`)
export const deleteJourney = (id) => api.delete(`/api/journeys/${id}`)
