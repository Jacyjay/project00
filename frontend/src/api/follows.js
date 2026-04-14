import api from './index'

export const followUser = (userId) => api.post(`/api/users/${userId}/follow`)
export const unfollowUser = (userId) => api.delete(`/api/users/${userId}/follow`)
export const getFollowStatus = (userId) => api.get(`/api/users/${userId}/follow-status`)
export const getFeed = (limit = 20, offset = 0) => api.get('/api/feed', { params: { limit, offset } })
export const getMutualFollowers = () => api.get('/api/follows/mutual')
export const getFollowers = (userId) => api.get(`/api/users/${userId}/followers`)
export const getFollowing = (userId) => api.get(`/api/users/${userId}/following`)
export const updateFollowPrivacy = (data) => api.put('/api/users/me/follow-privacy', data)
