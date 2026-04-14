import api from './index'

export const sendVerificationCode = (email) =>
  api.post('/api/auth/send-code', { email })

export const register = (data) => api.post('/api/auth/register', data)
export const login = (data) => api.post('/api/auth/login', data)
export const getMe = () => api.get('/api/auth/me')
