import AMapLoader from '@amap/amap-jsapi-loader'

import { AMAP_KEY, AMAP_SECURITY_JS_CODE } from './config'
import { normalizeAddressName, normalizeCityName } from './region'

let amapPromise
let amapScreenshotPromise
const INVALID_CITY_NAMES = new Set(['市辖区', '县', '城区'])
const AMAP_GEOCODE_TIMEOUT_MS = 5000
const AMAP_CONVERT_TIMEOUT_MS = 5000
const AMAP_NEARBY_TIMEOUT_MS = 6000
const TRAVEL_NEARBY_KEYWORDS = ['风景名胜', '公园', '博物馆', '步行街', '商圈', '咖啡馆']
const AMAP_SCREENSHOT_PLUGIN_URL = 'https://cdn.jsdelivr.net/npm/@amap/screenshot/dist/index.js'

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
      plugins: ['AMap.Scale', 'AMap.ToolBar', 'AMap.Geocoder', 'AMap.PlaceSearch', 'AMap.HeatMap'],
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

export async function ensureAmapScreenshotPlugin() {
  const AMap = await loadAmap()
  if (typeof window === 'undefined') {
    return AMap
  }
  if (AMap?.Screenshot) {
    return AMap
  }
  if (!amapScreenshotPromise) {
    amapScreenshotPromise = new Promise((resolve, reject) => {
      const existingScript = document.querySelector(`script[data-amap-screenshot-plugin="1"]`)
      if (existingScript) {
        existingScript.addEventListener('load', () => resolve(window.AMap || AMap), { once: true })
        existingScript.addEventListener('error', () => reject(new Error('高德截图插件加载失败')), { once: true })
        return
      }

      const script = document.createElement('script')
      script.src = AMAP_SCREENSHOT_PLUGIN_URL
      script.async = true
      script.defer = true
      script.dataset.amapScreenshotPlugin = '1'
      script.onload = () => {
        if ((window.AMap || AMap)?.Screenshot) {
          resolve(window.AMap || AMap)
          return
        }
        reject(new Error('高德截图插件未正确注册'))
      }
      script.onerror = () => reject(new Error('高德截图插件加载失败'))
      document.head.appendChild(script)
    }).catch((error) => {
      amapScreenshotPromise = null
      throw error
    })
  }

  return amapScreenshotPromise
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
      const city = normalizeCityName(extractCityFromRegeocode(regeocode))
      const address = normalizeAddressName(normalizeAmapText(regeocode.formattedAddress))
      const currentPoi = Array.isArray(regeocode.pois) && regeocode.pois.length ? regeocode.pois[0] : null

      resolve({
        city,
        address,
        current_poi_name: normalizeAmapText(currentPoi?.name),
        current_poi_type: normalizeAmapText(currentPoi?.type),
      })
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

export async function getCurrentAmapLocation(options = {}) {
  if (typeof window === 'undefined' || !navigator.geolocation) {
    throw new Error('当前浏览器不支持定位')
  }

  const {
    timeout = 8000,
    maximumAge = 0,
    enableHighAccuracy = false,
    retryWithHighAccuracy = true,
  } = options

  const resolveBrowserLocation = (requestOptions) =>
    new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, requestOptions)
    })

  let position

  try {
    position = await resolveBrowserLocation({
      enableHighAccuracy,
      timeout,
      maximumAge,
    })
  } catch (error) {
    const shouldRetry =
      retryWithHighAccuracy &&
      !enableHighAccuracy &&
      (error?.code === 2 || error?.code === 3)

    if (!shouldRetry) {
      throw error
    }

    position = await resolveBrowserLocation({
      enableHighAccuracy: true,
      timeout: Math.max(timeout, 15000),
      maximumAge: 0,
    })
  }

  const rawLocation = {
    longitude: position.coords.longitude,
    latitude: position.coords.latitude,
    accuracy: Number.isFinite(position.coords.accuracy) ? position.coords.accuracy : 0,
  }

  try {
    const converted = await convertGpsToAmap(rawLocation.longitude, rawLocation.latitude)
    return {
      ...converted,
      accuracy: rawLocation.accuracy,
      source: 'gps-converted',
    }
  } catch {
    return {
      ...rawLocation,
      source: 'gps-raw',
    }
  }
}

function extractPoiCoordinate(location) {
  if (!location) return null
  const longitude = typeof location.lng === 'number' ? location.lng : location.getLng?.()
  const latitude = typeof location.lat === 'number' ? location.lat : location.getLat?.()
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null
  return { longitude, latitude }
}

function normalizeNearbyPoi(poi, fallbackType = '') {
  const coordinate = extractPoiCoordinate(poi?.location)
  if (!coordinate) return null

  const city = normalizeCityName(
    normalizeAmapText(poi.cityname || poi.pname || poi.adname || '')
  )
  const addressParts = [poi.pname, poi.cityname, poi.adname, poi.address]
    .map((item) => normalizeAmapText(item))
    .filter(Boolean)
  const address = normalizeAddressName([...new Set(addressParts)].join(' '))

  return {
    name: normalizeAmapText(poi.name) || '未命名地点',
    city,
    address,
    latitude: coordinate.latitude,
    longitude: coordinate.longitude,
    distance_text: normalizeAmapText(poi.distance),
    type: normalizeAmapText(poi.type) || fallbackType,
  }
}

export async function searchNearbyTravelPlaces(latitude, longitude, options = {}) {
  const AMap = await loadAmap()
  const radius = Math.max(500, Number(options.radius || 3500))
  const maxResults = Math.max(3, Number(options.maxResults || 10))
  const keywords = Array.isArray(options.keywords) && options.keywords.length
    ? options.keywords
    : TRAVEL_NEARBY_KEYWORDS

  const placeSearch = new AMap.PlaceSearch({
    pageSize: 8,
    pageIndex: 1,
    city: '全国',
    citylimit: false,
    extensions: 'base',
  })

  const results = []
  const seen = new Set()

  for (const keyword of keywords) {
    // eslint-disable-next-line no-await-in-loop
    const pois = await new Promise((resolve) => {
      const timeoutId = window.setTimeout(() => resolve([]), AMAP_NEARBY_TIMEOUT_MS)
      placeSearch.searchNearBy(keyword, [longitude, latitude], radius, (status, result) => {
        window.clearTimeout(timeoutId)
        if (status !== 'complete') {
          resolve([])
          return
        }
        resolve(result?.poiList?.pois || [])
      })
    })

    for (const poi of pois) {
      const item = normalizeNearbyPoi(poi, keyword)
      if (!item) continue
      const key = `${item.name}-${item.latitude.toFixed(4)}-${item.longitude.toFixed(4)}`
      if (seen.has(key)) continue
      seen.add(key)
      results.push(item)
      if (results.length >= maxResults) {
        return results
      }
    }
  }

  return results
}
