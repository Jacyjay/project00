import { resolveApiUrl } from './config'

export function getImageUrl(url) {
  return resolveApiUrl(url)
}

export function formatDate(value) {
  if (!value) return ''
  return new Date(value).toLocaleDateString('zh-CN')
}

export function formatCheckinDate(checkin) {
  if (!checkin) return ''
  return checkin.visit_date || formatDate(checkin.created_at)
}

export function truncateText(text, maxLength = 96) {
  if (!text) return ''
  const normalized = text.trim()
  if (normalized.length <= maxLength) return normalized
  return `${normalized.slice(0, maxLength - 1)}…`
}

export function formatCoordinates(latitude, longitude) {
  const lat = Number(latitude)
  const lng = Number(longitude)
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return ''
  return `${lat.toFixed(5)}, ${lng.toFixed(5)}`
}
