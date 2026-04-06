import AMapLoader from '@amap/amap-jsapi-loader'

import { AMAP_KEY, AMAP_SECURITY_JS_CODE } from './config'

let amapPromise
const INVALID_CITY_NAMES = new Set(['市辖区', '县', '城区'])
const AMAP_GEOCODE_TIMEOUT_MS = 5000
const AMAP_CONVERT_TIMEOUT_MS = 5000

export async function loadAmap() {
  if (!AMAP_KEY || !AMAP_SECURITY_JS_CODE) {
    throw new Error('缺少高德地图配置，请先设置 VITE_AMAP_KEY 和 VITE_AMAP_SECURITY_JS_CODE')
  }

  window._AMapSecurityConfig = {
    securityJsCode: AMAP_SECURITY_JS_CODE,
  }

  if (!amapPromise) {
    amapPromise = AMapLoader.load({
      key: AMAP_KEY,
      version: '2.0',
      plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Geocoder', 'AMap.PlaceSearch'],
    })
  }

  return amapPromise
}

export function preloadAmap() {
  if (!AMAP_KEY || !AMAP_SECURITY_JS_CODE) {
    return Promise.resolve(null)
  }

  return loadAmap().catch((error) => {
    console.warn('高德地图预加载失败', error)
    return null
  })
}

function normalizeAmapText(value) {
  if (Array.isArray(value)) {
    value = value[0] || ''
  }
  if (typeof value !== 'string') {
    return ''
  }
  return value.trim()
}

function normalizeCityCandidate(value) {
  const text = normalizeAmapText(value)
  if (!text || INVALID_CITY_NAMES.has(text)) {
    return ''
  }
  return text
}

function isMunicipalityLikeRegion(value) {
  return /(?:市|特别行政区)$/.test(value)
}

function extractCityFromFormattedAddress(address) {
  const normalizedAddress = normalizeAmapText(address).replace(/^中国/, '')
  if (!normalizedAddress) return ''

  const provincePrefix = normalizedAddress.match(/^.+?(?:省|自治区|特别行政区|市)/)?.[0] || ''
  const remaining = provincePrefix ? normalizedAddress.slice(provincePrefix.length) : normalizedAddress
  const cityMatch = remaining.match(/^.+?(?:市|州|地区|盟)/)
  return cityMatch ? cityMatch[0].trim() : ''
}

function extractCityFromRegeocode(regeocode) {
  const addressComponent = regeocode?.addressComponent || {}
  const province = normalizeAmapText(addressComponent.province)
  const district = normalizeAmapText(addressComponent.district)
  const township = normalizeAmapText(addressComponent.township)
  const country = normalizeAmapText(addressComponent.country)
  const formattedAddress = normalizeAmapText(regeocode?.formattedAddress)

  const explicitCity =
    normalizeCityCandidate(addressComponent.city) ||
    extractCityFromFormattedAddress(formattedAddress)

  if (explicitCity) {
    return explicitCity
  }

  if (isMunicipalityLikeRegion(province)) {
    return province
  }

  return province || district || township || country
}

export async function reverseGeocodeWithAmap(latitude, longitude) {
  const AMap = await loadAmap()

  return new Promise((resolve, reject) => {
    const geocoder = new AMap.Geocoder({ extensions: 'all', radius: 500, batch: false })
    const timeoutId = window.setTimeout(() => {
      reject(new Error('高德地理编码超时'))
    }, AMAP_GEOCODE_TIMEOUT_MS)

    geocoder.getAddress([longitude, latitude], (status, result) => {
      window.clearTimeout(timeoutId)
      if (status !== 'complete' || !result?.regeocode) {
        reject(new Error('高德地理编码失败'))
        return
      }

      const regeocode = result.regeocode
      const city = extractCityFromRegeocode(regeocode)
      const address = normalizeAmapText(regeocode.formattedAddress)

      resolve({ city, address })
    })
  })
}

export async function convertGpsToAmap(longitude, latitude) {
  const AMap = await loadAmap()

  return new Promise((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      reject(new Error('坐标转换超时'))
    }, AMAP_CONVERT_TIMEOUT_MS)

    AMap.convertFrom([longitude, latitude], 'gps', (status, result) => {
      window.clearTimeout(timeoutId)
      if (status !== 'complete' || !result?.locations?.length) {
        reject(new Error('坐标转换失败'))
        return
      }

      const location = result.locations[0]
      resolve({ longitude: location.lng, latitude: location.lat })
    })
  })
}
