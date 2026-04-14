import api from './index'

export const getConversations = () => api.get('/api/messages/conversations')
export const getMessages = (partnerId, limit = 50, offset = 0) =>
  api.get(`/api/messages/${partnerId}`, { params: { limit, offset } })
export const sendMessage = (partnerId, content) =>
  api.post(`/api/messages/${partnerId}`, { content })
export const getUnreadCount = () => api.get('/api/messages/unread-count')
