<template>
  <div class="journey-page">

    <!-- Custom header -->
    <div class="journey-header glass-card">
      <button class="journey-back" @click="goBack">
        <span class="journey-back-icon">←</span>
      </button>
      <div class="journey-header-center">
        <span class="journey-header-title">{{ journey?.title || '旅程详情' }}</span>
        <span v-if="journey" class="journey-header-sub">{{ journey.user?.nickname }}</span>
      </div>
      <button class="journey-share-btn" @click="generateShareImage" :disabled="isGenerating">
        <span v-if="isGenerating" class="share-spinner"></span>
        <span v-else>分享</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="journey-loading">
      <div class="journey-loading-spinner"></div>
      <p>正在加载旅程…</p>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="journey-error">
      <div class="journey-error-icon">🗺️</div>
      <p class="journey-error-msg">{{ error }}</p>
      <button class="btn-primary" @click="goBack">返回</button>
    </div>

    <template v-else-if="journey">
      <!-- Map section -->
      <div class="journey-map-wrap">
        <div ref="mapContainer" class="journey-map" :class="{ ready: isMapReady }"></div>
        <div v-if="!isMapReady" class="journey-map-placeholder">
          <div class="journey-loading-spinner"></div>
        </div>

        <!-- Floating stats pill on map -->
        <div class="journey-map-pill glass-card">
          <span class="pill-stat">
            <span class="pill-val">{{ journey.checkin_count }}</span>
            <span class="pill-label">处打卡</span>
          </span>
          <span class="pill-sep">·</span>
          <span class="pill-stat">
            <span class="pill-val">{{ journey.cities.length }}</span>
            <span class="pill-label">座城市</span>
          </span>
          <span class="pill-sep">·</span>
          <span class="pill-stat">
            <span class="pill-val">{{ tripDays }}</span>
            <span class="pill-label">天</span>
          </span>
        </div>
      </div>

      <!-- Journey info card -->
      <div class="journey-info-card">
        <h1 class="journey-title">{{ journey.title }}</h1>
        <div class="journey-cities-row">
          <span v-for="(city, i) in journey.cities.slice(0, 6)" :key="city" class="journey-city-chip">
            {{ city }}
            <span v-if="i < Math.min(journey.cities.length, 6) - 1" class="city-arrow">→</span>
          </span>
          <span v-if="journey.cities.length > 6" class="journey-city-more">+{{ journey.cities.length - 6 }}城</span>
        </div>
        <div class="journey-date-row">
          <span class="journey-date-icon">📅</span>
          <span class="journey-date-text">{{ formatDateRange(journey.start_date, journey.end_date) }}</span>
        </div>
      </div>

      <!-- Checkin list -->
      <div class="journey-checkins">
        <div class="journey-checkins-title">打卡记录</div>
        <div
          v-for="(checkin, idx) in journey.checkins"
          :key="checkin.id"
          :class="['journey-checkin-card', { 'journey-checkin-card--active': activeCheckinIdx === idx }]"
          @click="focusCheckin(checkin, idx)"
        >
          <!-- Number badge -->
          <div class="checkin-badge" :style="{ background: badgeColor(idx) }">{{ idx + 1 }}</div>

          <!-- Photo -->
          <div class="checkin-photo-wrap">
            <img
              v-if="checkin.preview_image_url"
              :src="resolveUrl(checkin.preview_image_url)"
              class="checkin-photo"
              loading="lazy"
            />
            <div v-else class="checkin-photo-placeholder" :style="{ background: placeholderGradient(idx) }">
              <span class="checkin-photo-placeholder-icon">📍</span>
            </div>
          </div>

          <!-- Info -->
          <div class="checkin-info">
            <div class="checkin-name">{{ checkin.location_name }}</div>
            <div class="checkin-meta">
              <span v-if="checkin.city" class="checkin-city">{{ checkin.city }}</span>
              <span class="checkin-date">{{ formatCheckinDate(checkin.visit_date || checkin.created_at) }}</span>
            </div>
            <p v-if="checkin.content" class="checkin-excerpt">{{ checkin.content }}</p>
          </div>

          <!-- Connector line (not on last) -->
          <div v-if="idx < journey.checkins.length - 1" class="checkin-connector"></div>
        </div>
      </div>

      <!-- Bottom padding for FAB -->
      <div style="height: 80px"></div>
    </template>

    <!-- Share image preview modal -->
    <transition name="modal-fade">
      <div v-if="sharePreviewVisible" class="share-preview-overlay" @click.self="sharePreviewVisible = false">
        <div class="share-preview-modal glass-card">
          <div class="share-preview-header">
            <span class="share-preview-title">旅程分享图</span>
            <button class="detail-close" @click="sharePreviewVisible = false">✕</button>
          </div>
          <div class="share-preview-image-wrap">
            <img :src="shareImageDataUrl" class="share-preview-image" />
          </div>
          <div class="share-preview-actions">
            <button class="share-copy-btn" @click="copyJourneyLink">🔗 复制链接</button>
            <button class="share-download-btn" @click="saveToAlbum">📥 保存到相册</button>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getJourney } from '../api/journeys'
import { ensureAmapScreenshotPlugin, loadAmap } from '../lib/amap'
import { resolveApiUrl } from '../lib/config'
import { normalizeCityName } from '../lib/region'

const route = useRoute()
const router = useRouter()

// ── State ──────────────────────────────────────────────────────────────────────
const journey = ref(null)
const loading = ref(true)
const error = ref('')
const isMapReady = ref(false)
const activeCheckinIdx = ref(-1)
const isGenerating = ref(false)
const sharePreviewVisible = ref(false)
const shareImageDataUrl = ref('')
const staticMapUrl = ref('')
const staticMapImageUrl = ref('')
const staticMapViewport = ref(null)

const mapContainer = ref(null)

let map = null
let AMap = null
let markers = []
let routeLine = null

// ── Computed ───────────────────────────────────────────────────────────────────
const tripDays = computed(() => {
  if (!journey.value?.start_date || !journey.value?.end_date) return 1
  const diff = new Date(journey.value.end_date) - new Date(journey.value.start_date)
  return Math.max(1, Math.round(diff / 86400000) + 1)
})

// ── Helpers ────────────────────────────────────────────────────────────────────
const BADGE_COLORS = ['#E85D04', '#1a6fd4', '#16a34a', '#9333ea', '#0891b2', '#d97706', '#be185d', '#374151']
const PLACEHOLDER_GRADIENTS = [
  'linear-gradient(135deg, #f97316, #fb923c)',
  'linear-gradient(135deg, #3b82f6, #60a5fa)',
  'linear-gradient(135deg, #10b981, #34d399)',
  'linear-gradient(135deg, #8b5cf6, #a78bfa)',
  'linear-gradient(135deg, #06b6d4, #22d3ee)',
  'linear-gradient(135deg, #f59e0b, #fbbf24)',
  'linear-gradient(135deg, #ec4899, #f472b6)',
]

function badgeColor(idx) {
  return BADGE_COLORS[idx % BADGE_COLORS.length]
}

function placeholderGradient(idx) {
  return PLACEHOLDER_GRADIENTS[idx % PLACEHOLDER_GRADIENTS.length]
}

function truncateText(text, maxLength = 22) {
  const normalized = String(text || '').trim()
  if (!normalized) return ''
  return normalized.length > maxLength ? `${normalized.slice(0, maxLength - 1)}…` : normalized
}

function resolveUrl(url) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return resolveApiUrl(url)
}

function formatCheckinDate(str) {
  if (!str) return ''
  const d = new Date(str)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function formatDateRange(start, end) {
  if (!start) return ''
  const s = new Date(start)
  const e = end ? new Date(end) : s
  const sy = s.getFullYear(), sm = s.getMonth() + 1, sd = s.getDate()
  const ey = e.getFullYear(), em = e.getMonth() + 1, ed = e.getDate()
  if (sy === ey && sm === em && sd === ed) return `${sy}年${sm}月${sd}日`
  if (sy === ey) return `${sy}年${sm}月${sd}日 – ${em}月${ed}日`
  return `${sy}年${sm}月${sd}日 – ${ey}年${em}月${ed}日`
}

function estimateStaticMapZoom(points) {
  if (!points.length) return 10
  const longitudes = points.map(point => Number(point.longitude))
  const latitudes = points.map(point => Number(point.latitude))
  const lngSpan = Math.max(...longitudes) - Math.min(...longitudes)
  const latSpan = Math.max(...latitudes) - Math.min(...latitudes)
  const span = Math.max(lngSpan, latSpan)

  if (span > 40) return 4
  if (span > 20) return 5
  if (span > 10) return 6
  if (span > 5) return 7
  if (span > 2) return 8
  if (span > 1) return 9
  if (span > 0.5) return 10
  if (span > 0.2) return 11
  if (span > 0.1) return 12
  if (span > 0.05) return 13
  if (span > 0.02) return 14
  if (span > 0.01) return 15
  return 16
}

function buildStaticMapViewport(points) {
  if (!points?.length) return null
  const longitudes = points.map(point => Number(point.longitude))
  const latitudes = points.map(point => Number(point.latitude))
  return {
    centerLongitude: (Math.min(...longitudes) + Math.max(...longitudes)) / 2,
    centerLatitude: (Math.min(...latitudes) + Math.max(...latitudes)) / 2,
    zoom: estimateStaticMapZoom(points),
  }
}

function projectPointToStaticMap(point, viewport, width, height) {
  const tileSize = 256
  const scale = 2 ** Number(viewport.zoom || 10)
  const lngToX = (lng) => ((lng + 180) / 360) * tileSize * scale
  const latToY = (lat) => {
    const sin = Math.sin((Number(lat) * Math.PI) / 180)
    const clamped = Math.min(Math.max(sin, -0.9999), 0.9999)
    return (0.5 - Math.log((1 + clamped) / (1 - clamped)) / (4 * Math.PI)) * tileSize * scale
  }

  const centerX = lngToX(viewport.centerLongitude)
  const centerY = latToY(viewport.centerLatitude)
  const pointX = lngToX(point.longitude)
  const pointY = latToY(point.latitude)

  return {
    x: width / 2 + (pointX - centerX),
    y: height / 2 + (pointY - centerY),
  }
}

// ── Static map URL ─────────────────────────────────────────────────────────────
function buildStaticMapUrl(checkins, w = 1080, h = 600) {
  if (!checkins?.length) return ''
  const pts = checkins.filter(c => c.latitude && c.longitude)
  if (!pts.length) return ''
  const viewport = buildStaticMapViewport(pts)
  staticMapViewport.value = viewport

  // Include numbered markers for each check-in
  const markerColors = ['0xE85D04', '0x1A6FD4', '0x16A34A', '0x9333EA', '0x0891B2', '0xD97706', '0xBE185D', '0x374151']
  const markersParam = pts.slice(0, 8).map((c, i) =>
    `large,${markerColors[i % markerColors.length]},${i + 1}:${c.longitude},${c.latitude}`
  ).join('|')

  // Include the route path
  const pathCoords = pts.map(c => `${c.longitude},${c.latitude}`).join(';')
  const pathsParam = `6,0xE85D04,0.85:${pathCoords}`

  const params = new URLSearchParams({
    location: `${viewport.centerLongitude},${viewport.centerLatitude}`,
    zoom: String(viewport.zoom),
    size: `${w}*${h}`,
    markers: markersParam,
    paths: pathsParam,
    _ts: String(Date.now()),
  })

  return `/api/proxy/amap-static?${params.toString()}`
}

async function loadStaticMapImage(url) {
  const response = await fetch(url, { cache: 'no-store' })
  const contentType = response.headers.get('content-type') || ''

  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || `静态地图请求失败 (${response.status})`)
  }

  if (!contentType.toLowerCase().includes('image')) {
    const detail = await response.text().catch(() => '')
    throw new Error(detail || '静态地图返回的不是图片')
  }

  const blob = await response.blob()
  if (!blob.size) {
    throw new Error('静态地图返回了空内容')
  }

  staticMapImageUrl.value = await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('静态地图读取失败'))
    reader.readAsDataURL(blob)
  })
}

function getRectRelativeToContainer(element, containerRect) {
  const rect = element.getBoundingClientRect()
  return {
    x: rect.left - containerRect.left,
    y: rect.top - containerRect.top,
    width: rect.width,
    height: rect.height,
  }
}

async function captureLiveMapSnapshot() {
  const container = mapContainer.value
  if (!container) {
    throw new Error('地图容器不存在')
  }

  const containerRect = container.getBoundingClientRect()
  if (!containerRect.width || !containerRect.height) {
    throw new Error('地图容器尺寸异常')
  }

  const snapshotCanvas = document.createElement('canvas')
  snapshotCanvas.width = Math.round(containerRect.width * 2)
  snapshotCanvas.height = Math.round(containerRect.height * 2)
  const snapshotCtx = snapshotCanvas.getContext('2d')
  snapshotCtx.scale(2, 2)
  snapshotCtx.fillStyle = '#f3ebdf'
  snapshotCtx.fillRect(0, 0, containerRect.width, containerRect.height)

  const drawables = Array.from(container.querySelectorAll('canvas, img'))
  let renderedLayers = 0

  for (const element of drawables) {
    const relativeRect = getRectRelativeToContainer(element, containerRect)
    if (relativeRect.width <= 0 || relativeRect.height <= 0) {
      continue
    }

    const style = window.getComputedStyle(element)
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity || 1) === 0) {
      continue
    }

    try {
      snapshotCtx.drawImage(
        element,
        relativeRect.x,
        relativeRect.y,
        relativeRect.width,
        relativeRect.height,
      )
      renderedLayers += 1
    } catch (error) {
      console.warn('旅程地图图层抓取失败', error)
    }
  }

  if (!renderedLayers) {
    throw new Error('未捕获到地图图层')
  }

  return snapshotCanvas.toDataURL('image/png')
}

async function captureMapWithAmapScreenshotPlugin() {
  if (!map) {
    throw new Error('地图实例不存在')
  }

  const AMapWithPlugin = await ensureAmapScreenshotPlugin()
  if (!AMapWithPlugin?.Screenshot) {
    throw new Error('高德截图插件不可用')
  }

  return await new Promise((resolve, reject) => {
    try {
      const screenshot = new AMapWithPlugin.Screenshot(map)
      screenshot.getScreen((err, canvas) => {
        if (err || !canvas) {
          reject(err || new Error('高德截图结果为空'))
          return
        }
        try {
          const dataUrl = canvas.toDataURL('image/png')
          if (!dataUrl || dataUrl === 'data:,') {
            reject(new Error('高德截图为空白'))
            return
          }
          resolve(dataUrl)
        } catch (error) {
          reject(error)
        }
      })
    } catch (error) {
      reject(error)
    }
  })
}

async function loadImageElement(src) {
  if (!src) {
    throw new Error('图片地址为空')
  }

  return await new Promise((resolve, reject) => {
    const image = new Image()
    if (!src.startsWith('data:')) {
      image.crossOrigin = 'anonymous'
    }
    image.onload = async () => {
      try {
        if (typeof image.decode === 'function') {
          await image.decode()
        }
      } catch {
        // ignore decode failures; onload is sufficient fallback
      }
      resolve(image)
    }
    image.onerror = () => reject(new Error('图片加载失败'))
    image.src = src
  })
}

function isImageMostlyBlank(image) {
  try {
    const sampleCanvas = document.createElement('canvas')
    const sampleWidth = 48
    const sampleHeight = 48
    sampleCanvas.width = sampleWidth
    sampleCanvas.height = sampleHeight
    const sampleCtx = sampleCanvas.getContext('2d', { willReadFrequently: true })
    sampleCtx.drawImage(image, 0, 0, sampleWidth, sampleHeight)

    const { data } = sampleCtx.getImageData(0, 0, sampleWidth, sampleHeight)
    let brightPixels = 0
    let alphaPixels = 0
    let varianceSum = 0
    let lastLuma = null

    for (let index = 0; index < data.length; index += 4) {
      const r = data[index]
      const g = data[index + 1]
      const b = data[index + 2]
      const a = data[index + 3]
      if (a < 10) continue
      alphaPixels += 1
      const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
      if (luma > 245) brightPixels += 1
      if (lastLuma !== null) {
        varianceSum += Math.abs(luma - lastLuma)
      }
      lastLuma = luma
    }

    if (!alphaPixels) return true
    const brightRatio = brightPixels / alphaPixels
    const averageVariance = varianceSum / Math.max(alphaPixels - 1, 1)
    return brightRatio > 0.92 && averageVariance < 5
  } catch {
    return false
  }
}

function buildPosterLayout(journeyData) {
  const photoCheckins = (journeyData?.checkins || []).filter(item => item.preview_image_url)
  const photoCount = Math.min(photoCheckins.length, 6)
  const photoRows = Math.ceil(photoCount / 2)
  const hasPhotos = photoCount > 0

  const HEADER_H = 140
  const MAP_H = 600
  const TITLE_H = 230
  const ROUTE_H = 90
  const PHOTOS_H = hasPhotos ? (64 + photoRows * 310 + Math.max(0, photoRows - 1) * 16) : 0
  const FOOTER_H = 120

  return {
    width: 1080,
    paddingX: 64,
    headerH: HEADER_H,
    mapH: MAP_H,
    titleH: TITLE_H,
    routeH: ROUTE_H,
    photosH: PHOTOS_H,
    footerH: FOOTER_H,
    height: HEADER_H + MAP_H + TITLE_H + ROUTE_H + PHOTOS_H + FOOTER_H,
    // legacy compat
    mapY: HEADER_H,
    mapHeight: MAP_H,
  }
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  const safeRadius = Math.min(radius, width / 2, height / 2)
  ctx.beginPath()
  ctx.moveTo(x + safeRadius, y)
  ctx.arcTo(x + width, y, x + width, y + height, safeRadius)
  ctx.arcTo(x + width, y + height, x, y + height, safeRadius)
  ctx.arcTo(x, y + height, x, y, safeRadius)
  ctx.arcTo(x, y, x + width, y, safeRadius)
  ctx.closePath()
}

function fillRoundedRect(ctx, x, y, width, height, radius, fillStyle) {
  ctx.save()
  ctx.fillStyle = fillStyle
  drawRoundedRect(ctx, x, y, width, height, radius)
  ctx.fill()
  ctx.restore()
}

function drawRoundedImage(ctx, image, x, y, width, height, radius, fit = 'cover') {
  ctx.save()
  drawRoundedRect(ctx, x, y, width, height, radius)
  ctx.clip()

  const sourceWidth = Number(image?.naturalWidth || image?.videoWidth || image?.width || 0)
  const sourceHeight = Number(image?.naturalHeight || image?.videoHeight || image?.height || 0)

  if (!sourceWidth || !sourceHeight) {
    ctx.restore()
    return
  }

  if (fit === 'contain') {
    const scale = Math.min(width / sourceWidth, height / sourceHeight)
    const drawWidth = sourceWidth * scale
    const drawHeight = sourceHeight * scale
    const dx = x + (width - drawWidth) / 2
    const dy = y + (height - drawHeight) / 2
    ctx.drawImage(image, dx, dy, drawWidth, drawHeight)
    ctx.restore()
    return
  }

  const targetRatio = width / height
  const sourceRatio = sourceWidth / sourceHeight

  let sx = 0
  let sy = 0
  let sw = sourceWidth
  let sh = sourceHeight

  if (sourceRatio > targetRatio) {
    sw = sourceHeight * targetRatio
    sx = (sourceWidth - sw) / 2
  } else if (sourceRatio < targetRatio) {
    sh = sourceWidth / targetRatio
    sy = (sourceHeight - sh) / 2
  }

  ctx.drawImage(image, sx, sy, sw, sh, x, y, width, height)
  ctx.restore()
}

function formatCoordinateLabel(value, axis = 'lng') {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return ''
  const suffix = axis === 'lat'
    ? (numeric >= 0 ? 'N' : 'S')
    : (numeric >= 0 ? 'E' : 'W')
  return `${Math.abs(numeric).toFixed(2)}°${suffix}`
}

function drawMapDecorLine(ctx, points, color, lineWidth, alpha = 1, dashed = []) {
  if (!points.length) return
  ctx.save()
  ctx.beginPath()
  points.forEach(([px, py], index) => {
    if (index === 0) ctx.moveTo(px, py)
    else ctx.lineTo(px, py)
  })
  ctx.strokeStyle = color
  ctx.globalAlpha = alpha
  ctx.lineWidth = lineWidth
  ctx.lineJoin = 'round'
  ctx.lineCap = 'round'
  if (dashed.length) {
    ctx.setLineDash(dashed)
  }
  ctx.stroke()
  ctx.restore()
}

function drawPosterMapFallback(ctx, x, y, width, height, points, journeyData, viewport) {
  // === Beautiful illustrated paper-map style background ===
  ctx.save()
  // Clip to the map area (full rect, no border-radius needed here since it's full-width)
  ctx.rect(x, y, width, height)
  ctx.clip()

  // Sky-blue to sea-green gradient base
  const bg = ctx.createLinearGradient(x, y, x + width, y + height)
  bg.addColorStop(0, '#d8eef5')
  bg.addColorStop(0.35, '#cde8e0')
  bg.addColorStop(0.7, '#c5e2d8')
  bg.addColorStop(1, '#bad9cf')
  ctx.fillStyle = bg
  ctx.fillRect(x, y, width, height)

  // Fine grid texture (classic map grid)
  ctx.strokeStyle = 'rgba(80, 140, 120, 0.07)'
  ctx.lineWidth = 0.8
  const gridStep = 50
  for (let gx = x; gx <= x + width; gx += gridStep) {
    ctx.beginPath(); ctx.moveTo(gx, y); ctx.lineTo(gx, y + height); ctx.stroke()
  }
  for (let gy = y; gy <= y + height; gy += gridStep) {
    ctx.beginPath(); ctx.moveTo(x, gy); ctx.lineTo(x + width, gy); ctx.stroke()
  }

  // Land masses — organic shapes with soft watercolor-like fill
  const lands = [
    { cx: 0.12, cy: 0.25, rx: 0.22, ry: 0.20, rot: -0.3, c: 'rgba(168, 210, 168, 0.72)' },
    { cx: 0.55, cy: 0.18, rx: 0.28, ry: 0.18, rot: 0.18, c: 'rgba(160, 205, 175, 0.65)' },
    { cx: 0.40, cy: 0.72, rx: 0.30, ry: 0.22, rot: 0.08, c: 'rgba(175, 215, 178, 0.68)' },
    { cx: 0.88, cy: 0.58, rx: 0.18, ry: 0.28, rot: -0.12, c: 'rgba(162, 208, 172, 0.60)' },
    { cx: 0.08, cy: 0.78, rx: 0.14, ry: 0.16, rot: 0.35, c: 'rgba(170, 212, 178, 0.58)' },
    { cx: 0.78, cy: 0.88, rx: 0.20, ry: 0.14, rot: -0.20, c: 'rgba(158, 204, 168, 0.55)' },
  ]
  lands.forEach(l => {
    ctx.save()
    ctx.translate(x + l.cx * width, y + l.cy * height)
    ctx.rotate(l.rot)
    ctx.fillStyle = l.c
    ctx.beginPath()
    ctx.ellipse(0, 0, l.rx * width, l.ry * height, 0, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  })

  // River / water body paths
  const drawQuadPath = (pts, strokeColor, lineWidth, dashArr = []) => {
    ctx.save()
    ctx.strokeStyle = strokeColor
    ctx.lineWidth = lineWidth
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    if (dashArr.length) ctx.setLineDash(dashArr)
    ctx.beginPath()
    ctx.moveTo(pts[0][0], pts[0][1])
    for (let i = 1; i < pts.length - 1; i++) {
      const mx = (pts[i][0] + pts[i + 1][0]) / 2
      const my = (pts[i][1] + pts[i + 1][1]) / 2
      ctx.quadraticCurveTo(pts[i][0], pts[i][1], mx, my)
    }
    ctx.lineTo(pts[pts.length - 1][0], pts[pts.length - 1][1])
    ctx.stroke()
    ctx.restore()
  }

  // Main river (wide, light blue)
  drawQuadPath([
    [x, y + height * 0.55], [x + width * 0.18, y + height * 0.48],
    [x + width * 0.36, y + height * 0.53], [x + width * 0.54, y + height * 0.44],
    [x + width * 0.74, y + height * 0.38], [x + width, y + height * 0.32],
  ], 'rgba(110, 175, 200, 0.52)', 20)
  drawQuadPath([
    [x, y + height * 0.55], [x + width * 0.18, y + height * 0.48],
    [x + width * 0.36, y + height * 0.53], [x + width * 0.54, y + height * 0.44],
    [x + width * 0.74, y + height * 0.38], [x + width, y + height * 0.32],
  ], 'rgba(160, 210, 225, 0.38)', 8)

  // Tributary
  drawQuadPath([
    [x + width * 0.30, y], [x + width * 0.28, y + height * 0.22],
    [x + width * 0.34, y + height * 0.40],
  ], 'rgba(110, 175, 200, 0.40)', 10)

  // Secondary roads (curved white lines)
  const roadSets = [
    [[x + width * 0.05, y + height * 0.14], [x + width * 0.22, y + height * 0.26], [x + width * 0.40, y + height * 0.30], [x + width * 0.58, y + height * 0.24], [x + width * 0.78, y + height * 0.18]],
    [[x + width * 0.12, y + height * 0.65], [x + width * 0.28, y + height * 0.58], [x + width * 0.46, y + height * 0.62], [x + width * 0.64, y + height * 0.72], [x + width * 0.82, y + height * 0.78]],
    [[x + width * 0.68, y], [x + width * 0.64, y + height * 0.28], [x + width * 0.66, y + height * 0.52], [x + width * 0.70, y + height * 0.80]],
  ]
  roadSets.forEach(rpts => {
    drawQuadPath(rpts, 'rgba(255, 255, 255, 0.55)', 4)
    drawQuadPath(rpts, 'rgba(130, 170, 145, 0.28)', 2, [12, 10])
  })

  // === Route line (the actual journey) ===
  if (points.length > 1) {
    // Glow effect
    ctx.save()
    ctx.shadowColor = 'rgba(232, 93, 4, 0.50)'
    ctx.shadowBlur = 24
    ctx.strokeStyle = 'rgba(232, 93, 4, 0.88)'
    ctx.lineWidth = 8
    ctx.lineJoin = 'round'
    ctx.lineCap = 'round'
    ctx.beginPath()
    points.forEach((pt, i) => {
      if (i === 0) ctx.moveTo(x + pt.x, y + pt.y)
      else ctx.lineTo(x + pt.x, y + pt.y)
    })
    ctx.stroke()
    ctx.restore()
    // Dash overlay
    ctx.save()
    ctx.strokeStyle = 'rgba(255, 200, 150, 0.60)'
    ctx.lineWidth = 2.5
    ctx.setLineDash([10, 14])
    ctx.beginPath()
    points.forEach((pt, i) => {
      if (i === 0) ctx.moveTo(x + pt.x, y + pt.y)
      else ctx.lineTo(x + pt.x, y + pt.y)
    })
    ctx.stroke()
    ctx.restore()
  }

  // === Numbered location pins ===
  const uniqueCities = [...new Set((journeyData?.checkins || []).map(item => normalizeCityName(item.city)).filter(Boolean))]
  points.slice(0, 9).forEach((pt, i) => {
    const px = x + pt.x
    const py = y + pt.y
    // Drop shadow
    ctx.save()
    ctx.shadowColor = 'rgba(0,0,0,0.28)'
    ctx.shadowBlur = 14
    ctx.shadowOffsetY = 4
    ctx.fillStyle = BADGE_COLORS[i % BADGE_COLORS.length]
    ctx.beginPath()
    ctx.arc(px, py, 22, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
    // White ring
    ctx.strokeStyle = 'rgba(255,255,255,0.95)'
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.arc(px, py, 22, 0, Math.PI * 2)
    ctx.stroke()
    // Number
    ctx.fillStyle = '#ffffff'
    ctx.font = '800 18px "PingFang SC", "Microsoft YaHei", sans-serif'
    const lbl = String(i + 1)
    const lw = ctx.measureText(lbl).width
    ctx.fillText(lbl, px - lw / 2, py - 10)
  })

  // === Compass rose ===
  const cX = x + width - 80
  const cY = y + 68
  const cR = 38
  ctx.save()
  ctx.shadowColor = 'rgba(0,0,0,0.18)'
  ctx.shadowBlur = 12
  ctx.fillStyle = 'rgba(255,255,255,0.90)'
  ctx.beginPath()
  ctx.arc(cX, cY, cR, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()
  ctx.strokeStyle = 'rgba(80, 130, 110, 0.22)'
  ctx.lineWidth = 1.5
  ctx.beginPath()
  ctx.arc(cX, cY, cR, 0, Math.PI * 2)
  ctx.stroke()
  // Inner ring
  ctx.strokeStyle = 'rgba(80, 130, 110, 0.12)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.arc(cX, cY, cR * 0.55, 0, Math.PI * 2)
  ctx.stroke()
  // N arrow (red)
  ctx.save()
  ctx.fillStyle = '#E85D04'
  ctx.beginPath()
  ctx.moveTo(cX, cY - cR + 10)
  ctx.lineTo(cX + 8, cY - 2)
  ctx.lineTo(cX - 8, cY - 2)
  ctx.closePath()
  ctx.fill()
  // S arrow (grey)
  ctx.fillStyle = '#c8d8d0'
  ctx.beginPath()
  ctx.moveTo(cX, cY + cR - 10)
  ctx.lineTo(cX + 8, cY + 2)
  ctx.lineTo(cX - 8, cY + 2)
  ctx.closePath()
  ctx.fill()
  ctx.restore()
  // Cardinal labels
  ctx.font = '700 14px "DM Sans", "PingFang SC", sans-serif'
  ctx.fillStyle = '#E85D04'
  ctx.fillText('N', cX - 5, cY - cR + 5)
  ctx.fillStyle = '#6a9080'
  ctx.font = '600 12px "DM Sans", sans-serif'
  ctx.fillText('S', cX - 4, cY + cR - 4)
  ctx.fillText('E', cX + cR - 9, cY + 5)
  ctx.fillText('W', cX - cR + 4, cY + 5)

  // === "示意图" label ===
  ctx.fillStyle = 'rgba(50, 90, 70, 0.50)'
  ctx.font = '500 18px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('坐标示意图', x + 22, y + height - 30)

  ctx.restore()
}

function drawTextBlock(ctx, text, x, y, maxWidth, lineHeight, maxLines, color = '#5b5b5b') {
  const content = String(text || '').trim()
  if (!content) return y

  ctx.fillStyle = color
  const chars = [...content]
  let line = ''
  let lineCount = 0

  for (const char of chars) {
    const testLine = line + char
    const tooWide = ctx.measureText(testLine).width > maxWidth
    if (tooWide && line) {
      ctx.fillText(line, x, y)
      y += lineHeight
      lineCount += 1
      line = char
      if (lineCount >= maxLines - 1) {
        break
      }
    } else {
      line = testLine
    }
  }

  if (lineCount < maxLines && line) {
    let finalLine = line
    if (lineCount === maxLines - 1 && ctx.measureText(finalLine).width > maxWidth) {
      while (finalLine && ctx.measureText(`${finalLine}…`).width > maxWidth) {
        finalLine = finalLine.slice(0, -1)
      }
      finalLine = `${finalLine}…`
    }
    ctx.fillText(finalLine, x, y)
    y += lineHeight
  }

  return y
}

async function renderJourneyPoster() {
  const journeyData = journey.value
  if (!journeyData) throw new Error('旅程数据不存在')

  const W = 1080
  const PAD = 60

  const photoCheckins = (journeyData.checkins || []).filter(c => c.preview_image_url).slice(0, 6)
  const hasPhotos = photoCheckins.length > 0
  const PH_COLS  = photoCheckins.length <= 2 ? 2 : 3
  const photoRows = Math.ceil(photoCheckins.length / PH_COLS)
  const PH_INNER = PH_COLS === 2 ? 360 : 248
  const PH_LABEL = 58
  const PH_GAP   = 12

  const HEADER_H = 96
  const MAP_H    = 580
  const STATS_H  = 168
  const PHOTO_SECTION_H = hasPhotos
    ? (58 + photoRows * (PH_INNER + PH_LABEL) + Math.max(0, photoRows - 1) * PH_GAP + 36)
    : 0
  const FOOTER_H = 82
  const H = HEADER_H + MAP_H + STATS_H + PHOTO_SECTION_H + FOOTER_H

  // Hi-res canvas
  const DPR = 2
  const canvas = document.createElement('canvas')
  canvas.width  = W * DPR
  canvas.height = H * DPR
  const ctx = canvas.getContext('2d')
  ctx.scale(DPR, DPR)
  ctx.textBaseline = 'top'
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'

  const DARK   = '#0d0a07'
  const AMBER  = '#c8880e'
  const ORANGE = '#E85D04'
  const CREAM  = '#f5ede0'
  const PHOTO_BG = '#f2ebe0'
  const MUTED_ON_DARK = 'rgba(245,232,208,0.52)'

  // ── BACKGROUND ─────────────────────────────────────────────────────────────
  // Dark base for all sections; photo area gets warm light bg
  ctx.fillStyle = DARK
  ctx.fillRect(0, 0, W, H)
  if (hasPhotos) {
    ctx.fillStyle = PHOTO_BG
    ctx.fillRect(0, HEADER_H + MAP_H + STATS_H, W, PHOTO_SECTION_H)
  }

  // Left accent stripe on dark bands
  const darkBands = [
    [0, HEADER_H, ORANGE],
    [HEADER_H + MAP_H, STATS_H, AMBER],
    [HEADER_H + MAP_H + STATS_H + PHOTO_SECTION_H, FOOTER_H, ORANGE],
  ]
  darkBands.forEach(([y, h, color]) => {
    ctx.fillStyle = color
    ctx.fillRect(0, y, 5, h)
  })

  // ── HEADER ─────────────────────────────────────────────────────────────────
  // Brand name
  ctx.fillStyle = CREAM
  ctx.font = '800 44px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('拾光坐标', PAD, 18)

  // Sub-label
  ctx.fillStyle = AMBER
  ctx.font = '500 17px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('JOURNEY  ·  TRAVEL RECORD', PAD, 68)

  // User info (right-aligned): avatar circle + @name
  const userName = journeyData.user?.nickname || journeyData.user?.username || '旅行者'
  const userLabel = '@' + userName
  ctx.font = '600 22px "PingFang SC", "Microsoft YaHei", sans-serif'
  const ulW = ctx.measureText(userLabel).width
  const AVR = 20
  const avCX = W - PAD - ulW - AVR * 2 - 14
  const avCY = HEADER_H / 2

  ctx.save()
  ctx.fillStyle = ORANGE
  ctx.beginPath(); ctx.arc(avCX + AVR, avCY, AVR, 0, Math.PI * 2); ctx.fill()
  ctx.fillStyle = '#ffffff'
  ctx.font = '700 18px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.textBaseline = 'middle'
  const initChar = (userName.charAt(0) || '旅').toUpperCase()
  const initW = ctx.measureText(initChar).width
  ctx.fillText(initChar, avCX + AVR - initW / 2, avCY)
  ctx.restore()

  ctx.fillStyle = CREAM
  ctx.font = '600 22px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText(userLabel, W - PAD - ulW, HEADER_H / 2 - 13)

  // ── MAP ─────────────────────────────────────────────────────────────────────
  const mapY = HEADER_H
  const geoPts = (journeyData.checkins || []).filter(c =>
    Number.isFinite(Number(c.longitude)) && Number.isFinite(Number(c.latitude))
  )
  const vp = staticMapViewport.value || (geoPts.length ? buildStaticMapViewport(geoPts) : null)
  const routePts = vp ? geoPts.map(c => projectPointToStaticMap(c, vp, W, MAP_H)) : []

  let mapRendered = false
  if (staticMapImageUrl.value) {
    try {
      const mapImg = await loadImageElement(staticMapImageUrl.value)
      if (!isImageMostlyBlank(mapImg)) {
        ctx.drawImage(mapImg, 0, mapY, W, MAP_H)
        mapRendered = true
      }
    } catch (e) { console.warn('海报地图图片绘制失败', e) }
  }
  if (!mapRendered) {
    drawPosterMapFallback(ctx, 0, mapY, W, MAP_H, routePts, journeyData, vp)
  }

  // Route line overlay (real map)
  if (mapRendered && routePts.length > 1) {
    ctx.save()
    ctx.rect(0, mapY, W, MAP_H); ctx.clip()
    ctx.shadowColor = 'rgba(232,93,4,0.52)'; ctx.shadowBlur = 24
    ctx.strokeStyle = 'rgba(232,93,4,0.92)'; ctx.lineWidth = 7
    ctx.lineJoin = 'round'; ctx.lineCap = 'round'
    ctx.beginPath()
    routePts.forEach((pt, i) => {
      if (i === 0) ctx.moveTo(pt.x, mapY + pt.y)
      else ctx.lineTo(pt.x, mapY + pt.y)
    })
    ctx.stroke()
    ctx.restore()
  }

  // Numbered pins (real map)
  if (mapRendered) {
    routePts.slice(0, 9).forEach((pt, i) => {
      const px = pt.x; const py = mapY + pt.y
      ctx.save()
      ctx.shadowColor = 'rgba(0,0,0,0.32)'; ctx.shadowBlur = 16; ctx.shadowOffsetY = 5
      ctx.fillStyle = BADGE_COLORS[i % BADGE_COLORS.length]
      ctx.beginPath(); ctx.arc(px, py, 20, 0, Math.PI * 2); ctx.fill()
      ctx.restore()
      ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 2.5
      ctx.beginPath(); ctx.arc(px, py, 20, 0, Math.PI * 2); ctx.stroke()
      ctx.save()
      ctx.fillStyle = '#ffffff'
      ctx.font = '800 16px "PingFang SC", "Microsoft YaHei", sans-serif'
      ctx.textBaseline = 'middle'
      const nb = String(i + 1); const nbW = ctx.measureText(nb).width
      ctx.fillText(nb, px - nbW / 2, py)
      ctx.restore()
    })
  }

  // Map bottom dark gradient
  const mapGrad = ctx.createLinearGradient(0, mapY + MAP_H * 0.28, 0, mapY + MAP_H)
  mapGrad.addColorStop(0,   'rgba(5,2,1,0)')
  mapGrad.addColorStop(0.48,'rgba(5,2,1,0.52)')
  mapGrad.addColorStop(1,   'rgba(5,2,1,0.90)')
  ctx.fillStyle = mapGrad
  ctx.fillRect(0, mapY, W, MAP_H)

  // Journey title — large, white, bottom of map
  ctx.fillStyle = '#ffffff'
  ctx.font = '800 78px "PingFang SC", "Microsoft YaHei", sans-serif'
  drawTextBlock(ctx, journeyData.title || '我的旅程', PAD, mapY + MAP_H - 176, W - PAD * 2 - 40, 84, 2, '#ffffff')

  // Date in amber below title
  ctx.fillStyle = AMBER
  ctx.font = '500 24px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText(formatDateRange(journeyData.start_date, journeyData.end_date), PAD, mapY + MAP_H - 54)

  // ── STATS BAND ─────────────────────────────────────────────────────────────
  let curY = mapY + MAP_H

  const stats = [
    { val: String(journeyData.checkin_count), label: '处打卡', primary: true },
    { val: String(journeyData.cities.length), label: '座城市', primary: false },
    { val: String(tripDays.value),            label: '天旅程', primary: false },
  ]
  const statW = Math.floor((W - PAD * 2) / 3)

  stats.forEach((s, i) => {
    const sx = PAD + i * statW
    // Vertical divider between columns
    if (i > 0) {
      ctx.strokeStyle = 'rgba(255,255,255,0.07)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(sx, curY + 16); ctx.lineTo(sx, curY + 110)
      ctx.stroke()
    }
    // Large number
    ctx.fillStyle = s.primary ? ORANGE : AMBER
    ctx.font = '800 60px "PingFang SC", "Microsoft YaHei", sans-serif'
    const vW = ctx.measureText(s.val).width
    ctx.fillText(s.val, sx + statW / 2 - vW / 2, curY + 14)
    // Label
    ctx.fillStyle = MUTED_ON_DARK
    ctx.font = '500 19px "PingFang SC", "Microsoft YaHei", sans-serif'
    const lW = ctx.measureText(s.label).width
    ctx.fillText(s.label, sx + statW / 2 - lW / 2, curY + 86)
  })

  // Thin separator before cities
  ctx.strokeStyle = 'rgba(200,136,14,0.20)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(PAD, curY + 118); ctx.lineTo(W - PAD, curY + 118)
  ctx.stroke()

  // Cities route chain
  const citiesSlice = (journeyData.cities || []).slice(0, 7)
  const cityStr = citiesSlice.join('  →  ')
    + (journeyData.cities.length > 7 ? `  +${journeyData.cities.length - 7}` : '')
  if (cityStr.trim()) {
    ctx.fillStyle = 'rgba(245,232,208,0.70)'
    ctx.font = '500 22px "PingFang SC", "Microsoft YaHei", sans-serif'
    drawTextBlock(ctx, cityStr, PAD, curY + 130, W - PAD * 2, 28, 1, 'rgba(245,232,208,0.70)')
  }

  curY += STATS_H

  // ── PHOTOS ─────────────────────────────────────────────────────────────────
  if (hasPhotos) {
    // Section heading
    ctx.fillStyle = '#2a1810'
    ctx.font = '700 26px "PingFang SC", "Microsoft YaHei", sans-serif'
    ctx.fillText('沿途风景', PAD, curY + 16)
    // Accent underline
    ctx.fillStyle = ORANGE
    ctx.fillRect(PAD, curY + 50, 36, 3)
    ctx.fillStyle = 'rgba(232,93,4,0.18)'
    ctx.fillRect(PAD + 36, curY + 50, 100, 3)
    curY += 58

    const phW = Math.floor((W - PAD * 2 - PH_GAP * (PH_COLS - 1)) / PH_COLS)

    for (let pi = 0; pi < photoCheckins.length; pi++) {
      const item = photoCheckins[pi]
      const col = pi % PH_COLS
      const row = Math.floor(pi / PH_COLS)
      const px = PAD + col * (phW + PH_GAP)
      const py = curY + row * (PH_INNER + PH_LABEL + PH_GAP)

      // White card with shadow
      ctx.save()
      ctx.shadowColor = 'rgba(20,10,4,0.14)'
      ctx.shadowBlur = 22; ctx.shadowOffsetY = 8
      fillRoundedRect(ctx, px, py, phW, PH_INNER + PH_LABEL, 18, '#ffffff')
      ctx.restore()

      // Photo image (top of card, rounded only on top)
      try {
        const pImg = await loadImageElement(resolveUrl(item.preview_image_url))
        drawRoundedImage(ctx, pImg, px, py, phW, PH_INNER, 18)
        // Flat fill to remove bottom radius on photo (card bottom has its own radius)
        ctx.fillStyle = '#ffffff'
        ctx.fillRect(px, py + PH_INNER - 18, phW, 18)
      } catch {
        const pg = ctx.createLinearGradient(px, py, px + phW, py + PH_INNER)
        pg.addColorStop(0, '#ede0ce'); pg.addColorStop(1, '#e0d0be')
        fillRoundedRect(ctx, px, py, phW, PH_INNER, 18, pg)
      }

      // Location name
      ctx.fillStyle = '#1e110a'
      ctx.font = `600 ${PH_COLS === 2 ? 20 : 17}px "PingFang SC", "Microsoft YaHei", sans-serif`
      ctx.fillText(truncateText(item.location_name, PH_COLS === 2 ? 12 : 9), px + 12, py + PH_INNER + 9)

      // City in muted warm tone
      if (item.city) {
        ctx.fillStyle = '#9a7055'
        ctx.font = `400 ${PH_COLS === 2 ? 16 : 14}px "PingFang SC", "Microsoft YaHei", sans-serif`
        ctx.fillText(item.city, px + 12, py + PH_INNER + 33)
      }

      // Number badge (top-right corner)
      const BR = 14
      ctx.save()
      ctx.shadowColor = 'rgba(0,0,0,0.18)'; ctx.shadowBlur = 8; ctx.shadowOffsetY = 3
      fillRoundedRect(ctx, px + phW - BR * 2 - 10, py + 10, BR * 2, BR * 2, BR, BADGE_COLORS[pi % BADGE_COLORS.length])
      ctx.restore()
      ctx.save()
      ctx.fillStyle = '#ffffff'
      ctx.font = '700 14px "PingFang SC", "Microsoft YaHei", sans-serif'
      ctx.textBaseline = 'middle'
      const nb = String(pi + 1); const nbW = ctx.measureText(nb).width
      ctx.fillText(nb, px + phW - 10 - BR - nbW / 2, py + 10 + BR)
      ctx.restore()
    }

    curY += photoRows * (PH_INNER + PH_LABEL + PH_GAP) - PH_GAP + 36
  }

  // ── FOOTER ─────────────────────────────────────────────────────────────────
  ctx.fillStyle = DARK
  ctx.fillRect(0, curY, W, FOOTER_H)

  // Brand name in amber
  ctx.fillStyle = AMBER
  ctx.font = '700 28px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('拾光坐标', PAD, curY + 20)

  // Tagline
  ctx.fillStyle = 'rgba(245,228,200,0.42)'
  ctx.font = '400 18px "PingFang SC", "Microsoft YaHei", sans-serif'
  ctx.fillText('记录每一次出发，把坐标变成回忆。', PAD, curY + 52)

  // URL (right)
  ctx.fillStyle = 'rgba(245,228,200,0.26)'
  ctx.font = '400 15px "PingFang SC", "Microsoft YaHei", sans-serif'
  const urlText = 'jy-m.com'
  const urlTW = ctx.measureText(urlText).width
  ctx.fillText(urlText, W - PAD - urlTW, curY + 36)

  return canvas
}

// ── Map ────────────────────────────────────────────────────────────────────────
async function initMap() {
  if (!mapContainer.value || !journey.value?.checkins?.length) return
  try {
    AMap = await loadAmap()

    // Ensure container has layout dimensions before initializing
    await new Promise(resolve => requestAnimationFrame(resolve))

    map = new AMap.Map(mapContainer.value, {
      viewMode: '2D',
      zoom: 5,
      center: [105.0, 35.0],
      mapStyle: 'amap://styles/light',
      resizeEnable: true,
      features: ['bg', 'road', 'building', 'point'],
      WebGLParams: {
        preserveDrawingBuffer: true,
      },
    })

    // Timeout fallback: reveal map even if 'complete' event is slow / tiles blocked
    const readyTimer = setTimeout(() => {
      if (!isMapReady.value) {
        isMapReady.value = true
        renderRoute()
        map?.resize()
      }
    }, 8000)

    map.on('complete', () => {
      clearTimeout(readyTimer)
      isMapReady.value = true
      renderRoute()
      // Resize after the CSS opacity transition (0.5s) finishes so AMap fills the container properly
      setTimeout(() => map?.resize(), 600)
    })
  } catch (e) {
    console.error('地图初始化失败', e)
    isMapReady.value = true
  }
}

function renderRoute() {
  if (!map || !AMap || !journey.value?.checkins?.length) return
  const pts = journey.value.checkins.filter(c => c.latitude && c.longitude)
  if (!pts.length) return

  // Draw polyline
  if (pts.length > 1) {
    routeLine = new AMap.Polyline({
      path: pts.map(c => [c.longitude, c.latitude]),
      strokeColor: '#E85D04',
      strokeWeight: 4,
      strokeOpacity: 0.85,
      strokeStyle: 'solid',
      lineJoin: 'round',
      lineCap: 'round',
      showDir: true,
    })
    map.add(routeLine)
  }

  // Draw numbered markers
  markers = pts.map((c, idx) => {
    const color = BADGE_COLORS[idx % BADGE_COLORS.length]
    const content = `<div class="jmap-marker" style="background:${color}">${idx + 1}</div>`
    const marker = new AMap.Marker({
      position: [c.longitude, c.latitude],
      content,
      offset: new AMap.Pixel(-14, -14),
      zIndex: 100 + idx,
    })
    marker.on('click', () => focusCheckin(c, idx))
    return marker
  })
  map.add(markers)

  // Fit all points
  const bounds = new AMap.Bounds(
    [Math.min(...pts.map(c => c.longitude)), Math.min(...pts.map(c => c.latitude))],
    [Math.max(...pts.map(c => c.longitude)), Math.max(...pts.map(c => c.latitude))],
  )
  map.setBounds(bounds, false, [60, 60, 60, 60])
}

function focusCheckin(checkin, idx) {
  activeCheckinIdx.value = idx
  if (map && checkin.latitude && checkin.longitude) {
    map.setCenter([checkin.longitude, checkin.latitude])
    map.setZoom(13)
  }
  // Scroll card into view
  nextTick(() => {
    const cards = document.querySelectorAll('.journey-checkin-card')
    cards[idx]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  })
}

// ── Share image ────────────────────────────────────────────────────────────────
async function generateShareImage() {
  if (!journey.value || isGenerating.value) return
  isGenerating.value = true
  try {
    staticMapImageUrl.value = ''
    try {
      staticMapImageUrl.value = await captureMapWithAmapScreenshotPlugin()
    } catch (pluginError) {
      console.warn('高德截图插件失败，尝试静态地图', pluginError)
      staticMapUrl.value = buildStaticMapUrl(journey.value.checkins)
      if (!staticMapUrl.value) {
        throw new Error('旅程缺少有效坐标，无法生成地图')
      }
      try {
        await loadStaticMapImage(staticMapUrl.value)
      } catch (mapError) {
        console.warn('静态地图加载失败，尝试抓取页面地图', mapError)
        try {
          staticMapImageUrl.value = await captureLiveMapSnapshot()
        } catch (captureError) {
          console.warn('页面地图抓取失败，改用程序绘制底图', captureError)
        }
      }
    }
    const canvas = await renderJourneyPoster()
    shareImageDataUrl.value = canvas.toDataURL('image/png')
    sharePreviewVisible.value = true
  } catch (e) {
    console.error('生成分享图失败', e)
    ElMessage.error(e?.message || '生成分享图失败，请重试')
  } finally {
    isGenerating.value = false
  }
}

async function saveToAlbum() {
  if (!shareImageDataUrl.value) return
  const fileName = `${journey.value?.title || '我的旅程'}.png`
  try {
    // Convert dataURL to Blob
    const res = await fetch(shareImageDataUrl.value)
    const blob = await res.blob()
    const file = new File([blob], fileName, { type: 'image/png' })
    if (navigator.share && navigator.canShare?.({ files: [file] })) {
      await navigator.share({ files: [file], title: journey.value?.title || '我的旅程' })
    } else {
      // Fallback: download
      const link = document.createElement('a')
      link.download = fileName
      link.href = shareImageDataUrl.value
      link.click()
    }
  } catch (e) {
    if (e?.name !== 'AbortError') {
      // Fallback: download
      const link = document.createElement('a')
      link.download = fileName
      link.href = shareImageDataUrl.value
      link.click()
    }
  }
}

async function copyJourneyLink() {
  const url = window.location.href
  try {
    await navigator.clipboard.writeText(url)
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.info(`旅程链接：${url}`)
  }
}

function goBack() {
  if (window.history.length > 1) router.back()
  else router.push('/my-footprint')
}

// ── Lifecycle ──────────────────────────────────────────────────────────────────
onMounted(async () => {
  const id = route.params.id
  try {
    const res = await getJourney(id)
    journey.value = res.data
  } catch (e) {
    error.value = e.response?.status === 404 ? '旅程不存在' : e.response?.status === 403 ? '此旅程未公开' : '加载失败，请重试'
  } finally {
    loading.value = false
  }
  if (journey.value) {
    await nextTick()
    await initMap()
  }
})

onBeforeUnmount(() => {
  if (map) { map.destroy(); map = null }
})
</script>

<style scoped>
/* ── Page layout ── */
.journey-page {
  min-height: 100%;
  background: var(--bg-base);
  display: flex;
  flex-direction: column;
}

/* ── Header ── */
.journey-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 0;
  border-bottom: 1px solid var(--ink-100);
  background: var(--bg-surface) !important;
}

.journey-back {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: var(--bg-hover);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--ink-700);
  flex-shrink: 0;
  transition: background var(--fast);
}
.journey-back:hover { background: var(--ink-100); }

.journey-header-center {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.journey-header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.journey-header-sub {
  font-size: 11px;
  color: var(--ink-400);
  font-weight: 500;
}

.journey-share-btn {
  flex-shrink: 0;
  padding: 7px 18px;
  border-radius: var(--radius-full);
  border: none;
  background: var(--brand-gradient);
  color: var(--ink-900);
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(232, 93, 4, 0.25);
  transition: filter var(--fast);
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 60px;
  justify-content: center;
}
.journey-share-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.journey-share-btn:not(:disabled):hover { filter: brightness(0.93); }

.share-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(0,0,0,0.2);
  border-top-color: var(--ink-900);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Loading / Error states ── */
.journey-loading, .journey-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 60px 24px;
  color: var(--ink-500);
}

.journey-loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.journey-error-icon { font-size: 48px; }
.journey-error-msg { font-size: 15px; font-weight: 500; color: var(--ink-500); }

/* ── Map section ── */
.journey-map-wrap {
  position: relative;
  width: 100%;
  height: 46vh;
  min-height: 260px;
  max-height: 400px;
  background: #cde8e0;  /* matches map fallback bg so there's no flash */
  overflow: hidden;
}

.journey-map {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.journey-map.ready { opacity: 1; }

.journey-map-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #cde8e0;
  z-index: 2;
  transition: opacity 0.3s ease;
}

.journey-map-pill {
  position: absolute;
  bottom: 14px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 18px;
  border-radius: var(--radius-full);
  background: rgba(255,255,255,0.92) !important;
  backdrop-filter: blur(12px);
  white-space: nowrap;
  box-shadow: 0 4px 20px rgba(0,0,0,0.12);
}

.pill-stat {
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.pill-val {
  font-size: 16px;
  font-weight: 700;
  color: var(--brand);
  font-family: var(--font-display);
}

.pill-label {
  font-size: 11px;
  color: var(--ink-500);
  font-weight: 500;
}

.pill-sep {
  color: var(--ink-200);
  font-size: 14px;
}

/* ── Journey info card ── */
.journey-info-card {
  padding: 18px 18px 14px;
  border-bottom: 1px solid var(--ink-100);
  background: var(--bg-surface);
}

.journey-title {
  font-size: 22px;
  font-weight: 800;
  color: var(--ink-900);
  font-family: var(--font-display);
  letter-spacing: -0.03em;
  margin: 0 0 10px;
  line-height: 1.25;
}

.journey-cities-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-bottom: 10px;
}

.journey-city-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-700);
}

.city-arrow {
  color: var(--brand);
  font-size: 11px;
}

.journey-city-more {
  font-size: 12px;
  color: var(--ink-400);
  background: var(--bg-muted);
  padding: 2px 8px;
  border-radius: var(--radius-full);
}

.journey-date-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.journey-date-icon { font-size: 13px; }

.journey-date-text {
  font-size: 13px;
  color: var(--ink-400);
  font-weight: 500;
}

/* ── Checkin list ── */
.journey-checkins {
  padding: 0 16px;
  background: var(--bg-base);
}

.journey-checkins-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 18px 0 12px;
}

.journey-checkin-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 14px 14px 0;
  position: relative;
  cursor: pointer;
  border-radius: 16px;
  transition: background var(--fast);
}

.journey-checkin-card:hover,
.journey-checkin-card--active {
  background: var(--bg-muted);
  padding-left: 14px;
  margin: 0 -14px;
  width: calc(100% + 28px);
}

/* Number badge */
.checkin-badge {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: white;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  margin-top: 4px;
  z-index: 2;
  position: relative;
}

/* Photo */
.checkin-photo-wrap {
  flex-shrink: 0;
  width: 72px;
  height: 72px;
  border-radius: 12px;
  overflow: hidden;
}

.checkin-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.checkin-photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

/* Info */
.checkin-info {
  flex: 1;
  min-width: 0;
  padding-top: 2px;
}

.checkin-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.checkin-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 5px;
}

.checkin-city {
  font-size: 11px;
  color: var(--brand);
  font-weight: 600;
  background: var(--brand-light);
  padding: 1px 7px;
  border-radius: var(--radius-full);
}

.checkin-date {
  font-size: 11px;
  color: var(--ink-400);
  font-weight: 500;
}

.checkin-excerpt {
  font-size: 12px;
  color: var(--ink-500);
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Timeline connector */
.checkin-connector {
  position: absolute;
  left: 27px;
  top: 46px;
  bottom: -14px;
  width: 2px;
  background: linear-gradient(to bottom, var(--ink-100) 0%, transparent 100%);
  z-index: 1;
}

/* ── Map marker style (injected) ── */
:deep(.jmap-marker) {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  color: white;
  font-size: 12px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.25);
  border: 2px solid white;
  cursor: pointer;
  transition: transform 0.15s ease;
}

:deep(.jmap-marker:hover) { transform: scale(1.2); }

/* ── Share preview modal ── */
.share-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(10, 6, 2, 0.65);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0 0 env(safe-area-inset-bottom);
}

.share-preview-modal {
  width: 100%;
  max-width: 520px;
  max-height: 88vh;
  border-radius: 24px 24px 0 0;
  padding: 16px 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--bg-surface);
  box-shadow: 0 -12px 40px rgba(0,0,0,0.2);
  overflow: hidden;
}

.share-preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.share-preview-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
}

.share-preview-image-wrap {
  flex: 1;
  overflow-y: auto;
  border-radius: 14px;
  background: var(--bg-muted);
}

.share-preview-image {
  width: 100%;
  display: block;
  border-radius: 14px;
}

.share-preview-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.share-copy-btn, .share-download-btn {
  padding: 12px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: filter var(--fast);
}

.share-copy-btn {
  background: var(--bg-hover);
  border: 1.5px solid var(--ink-100);
  color: var(--ink-700);
}

.share-download-btn {
  background: var(--brand-gradient);
  border: none;
  color: var(--ink-900);
  box-shadow: 0 2px 10px rgba(232, 93, 4, 0.25);
}

.share-download-btn:hover { filter: brightness(0.93); }

/* ── Transitions ── */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.22s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }
</style>
