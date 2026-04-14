import api from './index'

// 获取所有成就定义及当前用户的解锁状态
export const getAllAchievements = () => api.get('/api/achievements')

// 获取指定用户的成就
export const getUserAchievements = (userId) => api.get(`/api/achievements/users/${userId}`)

// 更新成就可见性
export const updateAchievementVisibility = (achievementCode, isVisible) =>
  api.put(`/api/achievements/me/${achievementCode}/visibility`, { is_visible: isVisible })

// 获取成就统计
export const getAchievementStats = () => api.get('/api/achievements/stats')
