const rawApiBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim()
const normalizedApiBaseUrl = rawApiBaseUrl.replace(/\/$/, '')

function isLocalHostname(hostname) {
  return (
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '0.0.0.0' ||
    /^10(?:\.\d{1,3}){3}$/.test(hostname) ||
    /^192\.168(?:\.\d{1,3}){2}$/.test(hostname) ||
    /^172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}$/.test(hostname)
  )
}

function resolveApiBaseUrl() {
  if (!normalizedApiBaseUrl || typeof window === 'undefined') return normalizedApiBaseUrl

  try {
    const currentHost = window.location.hostname
    const apiUrl = new URL(normalizedApiBaseUrl)

    if (isLocalHostname(currentHost) && isLocalHostname(apiUrl.hostname)) {
      return ''
    }

    if (!isLocalHostname(currentHost) && isLocalHostname(apiUrl.hostname)) {
      return ''
    }
  } catch {
    return normalizedApiBaseUrl
  }

  return normalizedApiBaseUrl
}

export const API_BASE_URL = resolveApiBaseUrl()
export const AMAP_KEY = (import.meta.env.VITE_AMAP_KEY || '').trim()
export const AMAP_SECURITY_JS_CODE = (import.meta.env.VITE_AMAP_SECURITY_JS_CODE || '').trim()

export function resolveApiUrl(path = '') {
  if (!path) return ''
  if (/^https?:\/\//.test(path)) return path

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return API_BASE_URL ? `${API_BASE_URL}${normalizedPath}` : normalizedPath
}
