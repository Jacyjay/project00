<template>
  <div class="footprint-page">
    <!-- Not logged in -->
    <div v-if="!userStore.isLoggedIn" class="login-wall">
      <div class="login-wall-card glass-card">
        <div class="login-wall-icon">🗺️</div>
        <h2 class="login-wall-title">我的足迹地图</h2>
        <p class="login-wall-copy">登录后查看你走过的每一个坐标</p>
        <router-link to="/login" class="btn-primary">去登录</router-link>
      </div>
    </div>

    <template v-else>
      <!-- Stats card -->
      <div class="stats-card glass-card">
        <div class="stats-header">
          <span class="stats-title">我的足迹</span>
          <router-link
            :to="`/profile/${userStore.userId}`"
            class="stats-profile-link"
          >查看主页 →</router-link>
        </div>
        <div v-if="loading" class="stats-loading">加载中...</div>
        <div v-else class="stats-row">
          <div class="stat-item">
            <span class="stat-val">{{ checkins.length }}</span>
            <span class="stat-label">打卡</span>
          </div>
          <div class="stat-divider"></div>
          <div class="stat-item stat-item--clickable" @click="openCityPanel">
            <span class="stat-val">{{ cityCount }}</span>
            <span class="stat-label">城市 <span class="stat-arrow">›</span></span>
          </div>
        </div>
        <div v-if="!loading && checkins.length === 0" class="stats-empty">
          还没有打卡记录，去地图广场留下第一个足迹吧
        </div>
        <div v-if="!loading && checkins.length > 0" class="action-bar">
          <button class="btn-action" @click="openReport">✨ 足迹报告</button>
          <button
            :class="['btn-action', 'btn-action--journey', { 'btn-action--active': journeyMode }]"
            @click="journeyMode ? closeTripPanel() : openTripPanel()"
          >🗺️ {{ journeyMode ? '退出旅程' : '旅程地图' }}</button>
        </div>
      </div>

      <!-- Footprint report modal -->
      <transition name="modal-fade">
        <div v-if="reportVisible" class="report-overlay" @click.self="reportVisible = false">
          <div class="report-modal glass-card">
            <button class="report-close" @click="reportVisible = false">✕</button>
            <div class="report-header">
              <span class="report-title">我的专属足迹报告</span>
              <span class="report-ai-badge">✦ 由豆包AI生成</span>
            </div>
            <div v-if="reportLoading" class="report-loading">
              <div class="report-spinner"></div>
              <span>正在生成你的专属足迹报告…</span>
            </div>
            <div v-else-if="reportContent" class="report-body">{{ reportContent }}</div>
            <div v-else class="report-empty">
              <p>报告正在生成中，通常需要几秒钟。</p>
              <button class="btn-report-retry" @click="fetchReport">重新获取</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- City / Country detail panels -->
      <transition name="sheet-fade">
        <div v-if="detailPanel" class="detail-overlay" @click.self="detailPanel = null">
          <transition name="sheet-slide">
            <div v-if="detailPanel" class="detail-sheet glass-card">
              <div class="detail-handle"></div>
              <div class="detail-header">
                <span class="detail-title">{{ detailPanel.title }}</span>
                <span class="detail-count-badge">{{ detailPanel.items.length }}</span>
                <button class="detail-close" @click="detailPanel = null">✕</button>
              </div>
              <div class="detail-list">
                <div
                  v-for="(item, idx) in detailPanel.items"
                  :key="item.name"
                  class="detail-item"
                  :style="{ animationDelay: `${idx * 40}ms` }"
                >
                  <div class="detail-item-left">
                    <span class="detail-item-icon">{{ detailPanel.type === 'country' ? '🌏' : '📍' }}</span>
                    <div class="detail-item-info">
                      <span class="detail-item-name">{{ item.name }}</span>
                      <span class="detail-item-sub">{{ item.count }} 次打卡</span>
                    </div>
                  </div>
                  <div class="detail-item-bar-wrap">
                    <div
                      class="detail-item-bar"
                      :style="{ width: `${(item.count / detailPanel.maxCount) * 100}%` }"
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          </transition>
        </div>
      </transition>

      <!-- Trip / Journey panel -->
      <transition name="sheet-fade">
        <div v-if="tripPanelOpen" class="detail-overlay" @click.self="closeTripPanel">
          <transition name="sheet-slide">
            <div v-if="tripPanelOpen" class="detail-sheet glass-card">
              <div class="detail-handle"></div>
              <div class="detail-header">
                <span class="detail-title">我的旅程</span>
                <span class="detail-count-badge">{{ tripCount }}</span>
                <button class="detail-close" @click="closeTripPanel">✕</button>
              </div>
              <div class="detail-list">
                <div
                  v-for="(trip, idx) in groupedTrips"
                  :key="trip.id"
                  :class="['detail-item', 'trip-item', { 'trip-item--selected': selectedTrip?.id === trip.id }]"
                  :style="{ animationDelay: `${idx * 40}ms` }"
                  @click="selectTrip(trip)"
                >
                  <span class="trip-color-dot" :style="{ background: trip.color }"></span>
                  <div class="detail-item-left">
                    <div class="detail-item-info">
                      <span class="detail-item-name">{{ trip.name }}</span>
                      <span class="detail-item-sub">{{ formatTripDate(trip.startDate) }} · {{ trip.count }} 处打卡</span>
                    </div>
                  </div>
                  <span class="trip-arrow">›</span>
                </div>
              </div>

              <!-- 自定义时间段旅程 -->
              <div class="custom-range-section">
                <div class="custom-range-title">自定义时间段</div>
                <el-date-picker
                  v-model="customDateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="开始日期"
                  end-placeholder="结束日期"
                  size="small"
                  style="width: 100%"
                  :shortcuts="dateShortcuts"
                  @change="onCustomRangeChange"
                />
                <div v-if="customDateRange && customRangeCheckins.length > 0" class="custom-range-preview">
                  <span class="custom-range-stat">{{ customRangeCheckins.length }} 处打卡</span>
                  <span class="custom-range-stat">{{ customRangeCities.length }} 座城市</span>
                  <button class="trip-btn-save" @click="openSaveCustomJourney">💾 保存此旅程</button>
                </div>
                <div v-else-if="customDateRange && customRangeCheckins.length === 0" class="custom-range-empty">
                  所选时间段内无打卡记录
                </div>
              </div>

              <!-- 选中旅程后显示操作区 -->
              <transition name="trip-action-slide">
                <div v-if="selectedTrip" class="trip-action-bar">
                  <div class="trip-action-info">
                    <span class="trip-action-dot" :style="{ background: selectedTrip.color }"></span>
                    <span class="trip-action-name">{{ selectedTrip.name }}</span>
                  </div>
                  <div class="trip-action-btns">
                    <button class="trip-btn-save" @click="openSaveJourneyModal(selectedTrip)">
                      💾 保存旅程
                    </button>
                  </div>
                </div>
              </transition>
            </div>
          </transition>
        </div>
      </transition>

      <!-- Save Journey Modal -->
      <transition name="modal-fade">
        <div v-if="saveModalVisible" class="save-modal-overlay" @click.self="saveModalVisible = false">
          <div class="save-modal glass-card">
            <div class="save-modal-header">
              <span class="save-modal-title">保存旅程</span>
              <button class="detail-close" @click="saveModalVisible = false">✕</button>
            </div>
            <div class="save-modal-body">
              <div class="save-modal-meta">
                <span class="save-modal-cities">{{ savingTrip?.name }}</span>
                <span class="save-modal-count">{{ savingTrip?.count }} 处打卡</span>
              </div>
              <div class="save-field">
                <label class="save-field-label">旅程标题</label>
                <input
                  v-model="saveTitle"
                  class="save-field-input"
                  placeholder="给这段旅程起个名字..."
                  maxlength="30"
                  @keydown.enter="confirmSaveJourney"
                />
                <span class="save-field-count">{{ saveTitle.length }}/30</span>
              </div>
              <div class="save-public-row">
                <span class="save-public-label">公开旅程</span>
                <button
                  :class="['save-toggle', { active: saveIsPublic }]"
                  @click="saveIsPublic = !saveIsPublic"
                >
                  <span class="save-toggle-thumb"></span>
                </button>
              </div>
              <p class="save-public-hint">{{ saveIsPublic ? '任何人可通过链接查看' : '仅自己可见' }}</p>
            </div>
            <div class="save-modal-footer">
              <button class="save-cancel-btn" @click="saveModalVisible = false">取消</button>
              <button
                class="save-confirm-btn"
                :disabled="!saveTitle.trim() || isSaving"
                @click="confirmSaveJourney"
              >{{ isSaving ? '保存中…' : '保存旅程' }}</button>
            </div>
          </div>
        </div>
      </transition>

      <button v-if="isMapReady" class="btn-north" @click="resetNorth" title="重置朝北">北</button>

      <transition name="slide-up">
        <div v-if="selectedCheckin" class="preview-card glass-card">
          <button class="preview-close" @click="selectedCheckin = null">✕</button>
          <div class="preview-inner">
            <div v-if="selectedCheckin.preview_image_url || selectedCheckin.photos?.[0]?.image_url" class="preview-photo-wrap">
              <img :src="imageUrl(selectedCheckin.preview_image_url || selectedCheckin.photos?.[0]?.image_url)" class="preview-photo" />
            </div>
            <div class="preview-content">
              <div class="preview-name">{{ selectedCheckin.location_name || normalizeCityName(selectedCheckin.city) || '未知地点' }}</div>
              <div class="preview-meta">{{ normalizeCityName(selectedCheckin.city) }} · {{ formatDate(selectedCheckin.created_at) }}</div>
              <p v-if="selectedCheckin.content" class="preview-text">{{ selectedCheckin.content }}</p>
              <router-link :to="`/checkins/${selectedCheckin.id}`" class="btn-primary btn-sm preview-btn">
                查看详情
              </router-link>
            </div>
          </div>
        </div>
      </transition>

      <div ref="mapContainer" :class="['map-container', { ready: isMapReady }]"></div>

      <transition name="map-fade">
        <div v-if="!isMapReady" class="map-loading-overlay">
          <div class="map-loading-spinner"></div>
          <p class="map-loading-text">正在展开你的足迹地图...</p>
        </div>
      </transition>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useUserStore } from '../stores/user'
import { useMapStore } from '../stores/map'
import { getUserCheckins, getFootprintReport, refreshFootprintReport } from '../api/checkins'
import { createJourney } from '../api/journeys'
import { ElMessage } from 'element-plus'
import { useRouter as useVueRouter } from 'vue-router'
import { getCurrentAmapLocation, loadAmap, reverseGeocodeWithAmap, searchNearbyTravelPlaces } from '../lib/amap'
import { getImageUrl } from '../lib/checkins'
import { normalizeCityName } from '../lib/region'

const userStore = useUserStore()
const mapStore = useMapStore()
const mapContainer = ref(null)
const checkins = ref([])
const loading = ref(true)
const isMapReady = ref(false)
const selectedCheckin = ref(null)
const userLocationLoading = ref(false)
const userLocation = ref(null)

// Footprint report
const reportVisible = ref(false)
const reportLoading = ref(false)
const reportContent = ref(null)

async function fetchReport() {
  reportLoading.value = true
  reportContent.value = null
  try {
    const res = await getFootprintReport()
    reportContent.value = res.data.content || null
    if (!reportContent.value) {
      // Not ready yet — trigger generation then poll every 3s up to 10 times
      await refreshFootprintReport()
      let attempts = 0
      const poll = async () => {
        attempts++
        try {
          const r = await getFootprintReport()
          if (r.data.content) {
            reportContent.value = r.data.content
            reportLoading.value = false
            return
          }
        } catch { /* ignore */ }
        if (attempts < 10) setTimeout(poll, 3000)
        else reportLoading.value = false
      }
      setTimeout(poll, 3000)
      return
    }
  } catch {
    reportContent.value = null
  }
  reportLoading.value = false
}

function openReport() {
  reportVisible.value = true
  reportContent.value = null
  fetchReport()
}

let map = null
let AMap = null
let markers = []
let tripPolylines = []
let currentLocationMarker = null
let currentLocationCircle = null
let nearbyMarkers = []

const TRIP_COLORS = ['#E85D04', '#1a6fd4', '#16a34a', '#9333ea', '#0891b2', '#d97706', '#be185d', '#374151']
const TRIP_GAP_DAYS = 7

const journeyMode = ref(false)
const tripPanelOpen = ref(false)
const selectedTrip = ref(null)

// Save journey modal
const saveModalVisible = ref(false)
const savingTrip = ref(null)
const saveTitle = ref('')
const saveIsPublic = ref(true)
const isSaving = ref(false)
const vueRouter = useVueRouter()

// Custom date range
const customDateRange = ref(null)

const customRangeCheckins = computed(() => {
  if (!customDateRange.value || !customDateRange.value[0] || !customDateRange.value[1]) return []
  const start = new Date(customDateRange.value[0])
  start.setHours(0, 0, 0, 0)
  const end = new Date(customDateRange.value[1])
  end.setHours(23, 59, 59, 999)
  return checkins.value.filter(c => {
    const d = new Date(c.visit_date || c.created_at)
    return d >= start && d <= end && c.latitude && c.longitude
  }).sort((a, b) => new Date(a.visit_date || a.created_at) - new Date(b.visit_date || b.created_at))
})

const customRangeCities = computed(() =>
  [...new Set(customRangeCheckins.value.map(c => normalizeCityName(c.city)).filter(Boolean))]
)

const dateShortcuts = [
  { text: '最近一周', value: () => { const e = new Date(); const s = new Date(); s.setDate(s.getDate() - 6); return [s, e] } },
  { text: '最近一月', value: () => { const e = new Date(); const s = new Date(); s.setMonth(s.getMonth() - 1); return [s, e] } },
  { text: '最近三月', value: () => { const e = new Date(); const s = new Date(); s.setMonth(s.getMonth() - 3); return [s, e] } },
]

let customPolyline = null

function clearCustomPolyline() {
  if (map && customPolyline) {
    map.remove(customPolyline)
    customPolyline = null
  }
}

function onCustomRangeChange() {
  clearCustomPolyline()
  if (!map || !AMap || customRangeCheckins.value.length < 2) return
  const pts = customRangeCheckins.value
  customPolyline = new AMap.Polyline({
    path: pts.map(c => [c.longitude, c.latitude]),
    strokeColor: '#E85D04',
    strokeWeight: 5,
    strokeOpacity: 0.9,
    strokeStyle: 'solid',
    lineJoin: 'round',
    lineCap: 'round',
    showDir: true,
  })
  map.add(customPolyline)
  const lnglats = pts.map(c => new AMap.LngLat(c.longitude, c.latitude))
  const bounds = new AMap.Bounds(lnglats[0], lnglats[lnglats.length - 1])
  lnglats.forEach(ll => bounds.extend(ll))
  map.setBounds(bounds, false, [80, 80, 200, 80])
}

function openSaveCustomJourney() {
  if (!customRangeCheckins.value.length) return
  const cities = customRangeCities.value
  const start = customDateRange.value[0]
  const end = customDateRange.value[1]
  const s = new Date(start)
  const e = new Date(end)
  const defaultTitle = cities.length
    ? cities.slice(0, 3).join(' → ')
    : `${s.getFullYear()}/${s.getMonth()+1}/${s.getDate()} - ${e.getMonth()+1}/${e.getDate()}`
  savingTrip.value = {
    checkins: customRangeCheckins.value,
    count: customRangeCheckins.value.length,
    name: defaultTitle,
    isCustom: true,
  }
  saveTitle.value = defaultTitle
  saveIsPublic.value = true
  saveModalVisible.value = true
}

const cityCount = computed(() =>
  new Set(checkins.value.map(c => normalizeCityName(c.city)).filter(Boolean)).size
)

const groupedTrips = computed(() => {
  const sorted = [...checkins.value]
    .filter(c => c.latitude && c.longitude)
    .sort((a, b) => new Date(a.visit_date || a.created_at) - new Date(b.visit_date || b.created_at))

  if (!sorted.length) return []

  const groups = []
  let current = [sorted[0]]
  for (let i = 1; i < sorted.length; i++) {
    const gap = (new Date(sorted[i].visit_date || sorted[i].created_at) - new Date(sorted[i - 1].visit_date || sorted[i - 1].created_at)) / 86400000
    if (gap > TRIP_GAP_DAYS) {
      groups.push(current)
      current = [sorted[i]]
    } else {
      current.push(sorted[i])
    }
  }
  groups.push(current)

  return groups.map((checkinList, idx) => {
    const cities = [...new Set(checkinList.map(c => normalizeCityName(c.city)).filter(Boolean))]
    const dates = checkinList.map(c => new Date(c.visit_date || c.created_at))
    return {
      id: idx,
      name: cities.length ? cities.slice(0, 3).join(' → ') : `旅程 ${idx + 1}`,
      checkins: checkinList,
      startDate: new Date(Math.min(...dates)),
      endDate: new Date(Math.max(...dates)),
      count: checkinList.length,
      hasRoute: checkinList.length >= 2,
      color: TRIP_COLORS[idx % TRIP_COLORS.length],
    }
  })
})

const tripCount = computed(() => groupedTrips.value.length)

// Detail panel (city or country breakdown)
const detailPanel = ref(null)

function buildCountMap(items) {
  const map = {}
  for (const v of items) {
    if (v) map[v] = (map[v] || 0) + 1
  }
  return Object.entries(map)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
}

function openCityPanel() {
  const items = buildCountMap(checkins.value.map(c => normalizeCityName(c.city)).filter(Boolean))
  const maxCount = items[0]?.count || 1
  detailPanel.value = { type: 'city', title: '到访城市', items, maxCount }
}


function formatTripDate(date) {
  if (!date) return ''
  const d = new Date(date)
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()}`
}

function clearTripPolylines() {
  if (map && tripPolylines.length) {
    map.remove(tripPolylines)
    tripPolylines = []
  }
}

function renderTripLines() {
  if (!map || !AMap) return
  clearTripPolylines()
  groupedTrips.value.forEach(trip => {
    if (!trip.hasRoute) return
    const path = trip.checkins.map(c => [c.longitude, c.latitude])
    const isSelected = selectedTrip.value?.id === trip.id
    const opacity = selectedTrip.value ? (isSelected ? 0.92 : 0.18) : 0.65
    const weight = isSelected ? 5 : 3
    const polyline = new AMap.Polyline({
      path,
      strokeColor: trip.color,
      strokeWeight: weight,
      strokeOpacity: opacity,
      strokeStyle: 'solid',
      lineJoin: 'round',
      lineCap: 'round',
      showDir: isSelected,
    })
    tripPolylines.push(polyline)
  })
  if (tripPolylines.length) map.add(tripPolylines)
}

function openTripPanel() {
  if (!groupedTrips.value.length) return
  journeyMode.value = true
  tripPanelOpen.value = true
  if (isMapReady.value) renderTripLines()
}

function closeTripPanel() {
  tripPanelOpen.value = false
  selectedTrip.value = null
  journeyMode.value = false
  customDateRange.value = null
  clearTripPolylines()
  clearCustomPolyline()
}

function selectTrip(trip) {
  if (selectedTrip.value?.id === trip.id) {
    selectedTrip.value = null
    renderTripLines()
    return
  }
  selectedTrip.value = trip
  renderTripLines()
  if (!map || !AMap || !trip.checkins.length) return
  if (trip.checkins.length === 1) {
    map.setCenter([trip.checkins[0].longitude, trip.checkins[0].latitude])
    map.setZoom(12)
  } else {
    const lnglats = trip.checkins.map(c => new AMap.LngLat(c.longitude, c.latitude))
    const bounds = new AMap.Bounds(lnglats[0], lnglats[lnglats.length - 1])
    lnglats.forEach(ll => bounds.extend(ll))
    map.setBounds(bounds, false, [120, 120, 300, 120])
  }
}

function openSaveJourneyModal(trip) {
  savingTrip.value = trip
  saveTitle.value = trip.name
  saveIsPublic.value = true
  saveModalVisible.value = true
}

async function confirmSaveJourney() {
  if (!savingTrip.value || !saveTitle.value.trim() || isSaving.value) return
  isSaving.value = true
  try {
    const checkinIds = savingTrip.value.checkins.map(c => c.id)
    const res = await createJourney({
      title: saveTitle.value.trim(),
      checkin_ids: checkinIds,
      is_public: saveIsPublic.value,
    })
    saveModalVisible.value = false
    closeTripPanel()
    ElMessage.success('旅程已保存，正在跳转…')
    setTimeout(() => vueRouter.push(`/journeys/${res.data.id}`), 600)
  } catch (e) {
    ElMessage.error('保存失败，请重试')
  } finally {
    isSaving.value = false
  }
}

function imageUrl(url) {
  return getImageUrl(url)
}

function formatDate(str) {
  if (!str) return ''
  const d = new Date(str)
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

async function fetchCheckins() {
  if (!userStore.isLoggedIn || !userStore.userId) return
  loading.value = true
  try {
    const res = await getUserCheckins(userStore.userId, 200, 0)
    checkins.value = res.data.checkins || res.data || []
  } catch (e) {
    console.error('获取足迹失败', e)
  } finally {
    loading.value = false
  }
}

function clearMarkers() {
  if (map && markers.length) {
    map.remove(markers)
    markers = []
  }
}

function clearNearbyMarkers() {
  if (!map || !nearbyMarkers.length) return
  map.remove(nearbyMarkers)
  nearbyMarkers = []
}

function clearCurrentLocationDecorations() {
  if (!map) return
  if (currentLocationMarker) {
    map.remove(currentLocationMarker)
    currentLocationMarker = null
  }
  if (currentLocationCircle) {
    map.remove(currentLocationCircle)
    currentLocationCircle = null
  }
  clearNearbyMarkers()
}

function renderCurrentLocationDecorations(location) {
  if (!map || !AMap || !location) return

  clearCurrentLocationDecorations()

  const position = [location.longitude, location.latitude]

  currentLocationCircle = new AMap.Circle({
    center: position,
    radius: Math.min(Math.max(location.accuracy || 120, 80), 300),
    fillColor: 'rgba(26, 111, 212, 0.12)',
    fillOpacity: 1,
    strokeColor: 'rgba(26, 111, 212, 0.35)',
    strokeOpacity: 1,
    strokeWeight: 1,
    zIndex: 9,
  })

  currentLocationMarker = new AMap.Marker({
    position,
    offset: new AMap.Pixel(-11, -11),
    content: '<div class="current-location-pin"><span class="current-location-core"></span></div>',
    zIndex: 120,
  })

  map.add([currentLocationCircle, currentLocationMarker])

  nearbyMarkers = (location.nearby || []).slice(0, 4).map((place) => new AMap.Marker({
    position: [place.longitude, place.latitude],
    offset: new AMap.Pixel(-12, -12),
    content: `<div class="nearby-poi-pin"><span class="nearby-poi-dot"></span><span class="nearby-poi-text">${place.name}</span></div>`,
    zIndex: 110,
  }))

  if (nearbyMarkers.length) {
    map.add(nearbyMarkers)
  }
}

async function locateCurrentScene({ focus = true, silent = false } = {}) {
  if (!map || !AMap) return false

  userLocationLoading.value = true

  try {
    const coords = await getCurrentAmapLocation({
      timeout: 9000,
      maximumAge: 0,
      enableHighAccuracy: false,
      retryWithHighAccuracy: true,
    })

    const [geoResult, nearbyResult] = await Promise.allSettled([
      reverseGeocodeWithAmap(coords.latitude, coords.longitude),
      searchNearbyTravelPlaces(coords.latitude, coords.longitude, {
        radius: 1200,
        maxResults: 6,
        keywords: ['商圈', '步行街', '公园', '咖啡馆'],
      }),
    ])

    const location = {
      latitude: coords.latitude,
      longitude: coords.longitude,
      accuracy: coords.accuracy || 0,
      city: '',
      address: '',
      current_poi_name: '',
      nearby: [],
    }

    if (geoResult.status === 'fulfilled') {
      Object.assign(location, geoResult.value)
    }
    if (nearbyResult.status === 'fulfilled') {
      location.nearby = nearbyResult.value
    }

    userLocation.value = location
    renderCurrentLocationDecorations(location)

    if (focus) {
      map.setZoomAndCenter(Math.max(map.getZoom(), 16), [location.longitude, location.latitude])
    }

    return true
  } catch (error) {
    userLocation.value = null
    if (!silent) {
      ElMessage.warning('暂时无法获取当前位置，已保留足迹地图浏览')
    }
    return false
  } finally {
    userLocationLoading.value = false
  }
}

function renderMarkers() {
  if (!map || !AMap || !checkins.value.length) return
  clearMarkers()

  markers = checkins.value
    .filter(c => c.latitude && c.longitude)
    .map(checkin => {
      const rawUrl = checkin.preview_image_url || checkin.photos?.[0]?.image_url || null
      const photoUrl = mapStore.mapDetailMode && rawUrl ? getImageUrl(rawUrl) : null
      const content = photoUrl
        ? `<div class="fp-photo-pin"><img src="${photoUrl}" class="fp-pin-photo" loading="lazy" /><span class="fp-pin-dot"></span></div>`
        : `<div class="fp-coord-dot"></div>`
      const offset = photoUrl
        ? new AMap.Pixel(-18, -18)
        : new AMap.Pixel(-5, -5)

      const marker = new AMap.Marker({
        position: [checkin.longitude, checkin.latitude],
        offset,
        content,
      })

      marker.on('click', () => {
        selectedCheckin.value = checkin
        map.setCenter([checkin.longitude, checkin.latitude])
      })

      return marker
    })

  if (markers.length) {
    map.add(markers)
    if (!userLocation.value) {
      map.setFitView(markers, false, [100, 100, 180, 100])
    }
  }
}

async function initMap() {
  if (!mapContainer.value || map) return
  try {
    AMap = await loadAmap()
    map = new AMap.Map(mapContainer.value, {
      viewMode: '2D',
      zoom: 5,
      center: [105.0, 35.0],
      mapStyle: 'amap://styles/light',
      resizeEnable: true,
      features: ['bg', 'road', 'building', 'point'],
    })
    map.addControl(new AMap.Scale())
    map.on('complete', () => {
      isMapReady.value = true
      map.resize()
      renderMarkers()
    })
    map.on('click', () => {
      selectedCheckin.value = null
    })
  } catch (e) {
    console.error('地图初始化失败', e)
  }
}

function resetNorth() {
  if (map) map.setRotation(0)
}

onMounted(async () => {
  if (!userStore.isLoggedIn) return
  await fetchCheckins()
  await initMap()
  await locateCurrentScene({ focus: true, silent: true })
})

watch(() => userStore.isLoggedIn, async (loggedIn) => {
  if (loggedIn) {
    await fetchCheckins()
    await initMap()
    await locateCurrentScene({ focus: true, silent: true })
  }
})

// Re-render markers once both map and checkins are ready
watch([isMapReady, checkins], ([ready]) => {
  if (ready) {
    renderMarkers()
    if (journeyMode.value) renderTripLines()
  }
})

// Re-render markers when display mode changes
watch(() => mapStore.mapDetailMode, () => {
  renderMarkers()
})

onBeforeUnmount(() => {
  clearTripPolylines()
  clearCustomPolyline()
  clearCurrentLocationDecorations()
  if (map) {
    map.destroy()
    map = null
  }
})
</script>

<style scoped>
.footprint-page {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--bg-base);
  overflow: hidden;
}

/* ── Map ── */
.map-container {
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 0.6s ease;
}

.map-container.ready { opacity: 1; }

/* ── Loading overlay ── */
.map-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: var(--bg-base);
  z-index: 10;
}

.map-loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.map-loading-text {
  font-size: 13px;
  color: var(--ink-500);
  font-weight: 500;
}

.map-fade-leave-active { transition: opacity 0.4s ease; }
.map-fade-leave-to { opacity: 0; }

/* ── Stats card ── */
.stats-card {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 20;
  width: min(356px, calc(100% - 28px));
  padding: 14px 16px;
  border-radius: 18px;
  background: var(--bg-muted) !important;
}

.stats-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.stats-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
  letter-spacing: -0.02em;
}

.stats-profile-link {
  font-size: 12px;
  font-weight: 600;
  color: var(--brand);
  text-decoration: none;
}

.stats-profile-link:hover { opacity: 0.75; }

.stats-loading {
  font-size: 13px;
  color: var(--ink-300);
}

.stats-row {
  display: flex;
  align-items: center;
  gap: 0;
}

.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--brand);
  font-family: var(--font-display);
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: var(--ink-500);
  font-weight: 600;
}

.stat-divider {
  width: 1px;
  height: 32px;
  background: var(--ink-100);
}

.stat-item--clickable {
  cursor: pointer;
  border-radius: 10px;
  transition: background var(--fast) var(--ease-out), transform var(--fast) var(--ease-spring);
  padding: 6px 10px;
  margin: -6px -10px;
}

.stat-item--clickable:hover {
  background: var(--brand-light);
  transform: translateY(-1px);
}

.stat-item--clickable:active {
  transform: scale(0.96);
}

.stat-arrow {
  font-size: 10px;
  opacity: 0.45;
  margin-left: 1px;
}

.stats-empty {
  font-size: 12px;
  color: var(--ink-300);
  margin-top: 4px;
  line-height: 1.6;
}

/* ── North button ── */
.btn-north {
  position: absolute;
  right: 16px;
  top: 74px;
  z-index: 40;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-700);
  cursor: pointer;
  font-family: inherit;
  transition: transform var(--fast) var(--ease-spring), background var(--fast) var(--ease-out);
}

.btn-north:hover { transform: scale(1.08); background: var(--bg-muted); }

/* ── Preview card ── */
.preview-card {
  position: absolute;
  left: 14px;
  right: 14px;
  top: 180px;
  z-index: 40;
  padding: 14px;
  border-radius: 18px;
}

.preview-close {
  position: absolute;
  top: 10px;
  right: 12px;
  background: var(--bg-muted);
  border: none;
  border-radius: 50%;
  width: 26px;
  height: 26px;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-500);
  transition: background var(--fast) var(--ease-out);
}

.preview-close:hover { background: var(--bg-hover); }

.preview-inner {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.preview-photo-wrap {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}

.preview-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-content { flex: 1; min-width: 0; padding-right: 20px; }

.preview-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-meta {
  font-size: 11px;
  color: var(--ink-300);
  margin: 2px 0 6px;
}

.preview-text {
  font-size: 12px;
  color: var(--ink-500);
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.preview-btn {
  font-size: 12px;
  padding: 6px 14px;
  text-decoration: none;
  display: inline-block;
}

/* Slide transition */
.slide-up-enter-active { transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1); }
.slide-up-leave-active { transition: all 0.2s ease; }
.slide-up-enter-from { opacity: 0; transform: translateY(16px); }
.slide-up-leave-to { opacity: 0; transform: translateY(8px); }

/* ── Login wall ── */
.login-wall {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-base);
  z-index: 10;
}

.login-wall-card {
  text-align: center;
  padding: 40px 32px;
  border-radius: var(--radius-lg);
  max-width: 320px;
  width: calc(100% - 48px);
}

.login-wall-icon { font-size: 48px; margin-bottom: 16px; }

.login-wall-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--ink-900);
  margin: 0 0 8px;
  font-family: var(--font-display);
}

.login-wall-copy {
  font-size: 14px;
  color: var(--ink-500);
  margin: 0 0 24px;
  line-height: 1.6;
}

:deep(.current-location-pin) {
  position: relative;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
}

:deep(.current-location-pin::before) {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: rgba(26, 111, 212, 0.18);
  animation: currentLocationPulse 1.8s ease-out infinite;
}

:deep(.current-location-core) {
  position: relative;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #1a6fd4;
  border: 2px solid white;
  box-shadow: 0 4px 16px rgba(26, 111, 212, 0.35);
}

:deep(.nearby-poi-pin) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(255, 255, 255, 0.8);
  box-shadow: 0 10px 30px rgba(34, 20, 8, 0.14);
  color: var(--ink-700);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

:deep(.nearby-poi-dot) {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--brand);
}

:deep(.nearby-poi-text) {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
}

@keyframes currentLocationPulse {
  0% {
    transform: scale(0.65);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.9);
    opacity: 0;
  }
}

/* ── Map pin markers (injected as HTML) ── */
:deep(.fp-photo-pin) {
  position: relative;
  width: 40px;
  height: 40px;
}

:deep(.fp-pin-photo) {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  object-fit: cover;
  border: 2.5px solid white;
  box-shadow: 0 3px 10px rgba(232, 93, 4, 0.28);
  display: block;
}

:deep(.fp-pin-dot) {
  position: absolute;
  bottom: -3px;
  left: 50%;
  transform: translateX(-50%);
  width: 7px;
  height: 7px;
  background: var(--brand);
  border-radius: 50%;
  border: 2px solid white;
}

:deep(.fp-coord-dot) {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #1a6fd4;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(26, 111, 212, 0.55);
  cursor: pointer;
  transition: transform 0.15s ease;
}

:deep(.fp-coord-dot:hover) {
  transform: scale(1.4);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .stats-card {
    top: 8px;
    left: 12px;
    width: min(356px, calc(100% - 24px));
    padding: 12px 14px;
    border-radius: 16px;
  }

  .preview-card {
    left: 10px;
    right: 10px;
    top: 164px;
  }

  .stat-val { font-size: 20px; }
}

/* ── Report button ── */
/* ── Action bar (足迹报告 + 旅程地图) ── */
.action-bar {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.btn-action {
  padding: 9px 8px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--brand-gradient);
  color: var(--ink-900);
  font-size: 12px;
  font-weight: 700;
  font-family: var(--font-body);
  cursor: pointer;
  letter-spacing: 0.01em;
  transition: filter var(--fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.18);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-action:hover { filter: brightness(0.93); }
.btn-action:active { filter: brightness(0.86); }

.btn-action--journey {
  background: var(--bg-hover);
  border: 1.5px solid var(--ink-100);
  color: var(--ink-700);
  box-shadow: none;
}

.btn-action--journey:hover {
  filter: none;
  background: var(--brand-light);
  border-color: rgba(232, 93, 4, 0.3);
  color: var(--brand);
}

.btn-action--active.btn-action--journey {
  background: var(--brand-light);
  border-color: rgba(232, 93, 4, 0.35);
  color: var(--brand);
}

/* ── Report modal ── */
.report-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(28, 16, 7, 0.45);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 0 12px calc(24px + env(safe-area-inset-bottom));
}

.report-modal {
  width: 100%;
  max-width: 480px;
  max-height: 72vh;
  overflow-y: auto;
  border-radius: var(--radius-lg);
  padding: 20px 18px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
}

.report-close {
  position: absolute;
  top: 14px;
  right: 16px;
  width: 28px;
  height: 28px;
  border: none;
  background: var(--bg-muted);
  border-radius: 50%;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-500);
}

.report-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-right: 36px;
}

.report-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
  letter-spacing: -0.02em;
}

.report-ai-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--brand);
  background: var(--brand-light);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  white-space: nowrap;
}

.report-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ink-500);
  font-size: 13px;
  padding: 12px 0;
}

.report-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--ink-100);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

.report-body {
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-700);
  white-space: pre-wrap;
}

.report-empty {
  text-align: center;
  color: var(--ink-500);
  font-size: 13px;
  padding: 10px 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.btn-report-retry {
  padding: 7px 20px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--brand);
  background: transparent;
  color: var(--brand);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.modal-fade-enter-active,
.modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; }

/* ── Detail bottom-sheet ── */
.detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(20, 12, 4, 0.38);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

.detail-sheet {
  width: 100%;
  max-width: 520px;
  max-height: 72vh;
  border-radius: 22px 22px 0 0;
  padding: 12px 0 calc(24px + env(safe-area-inset-bottom));
  display: flex;
  flex-direction: column;
  background: var(--bg-surface);
  box-shadow: 0 -8px 40px rgba(0, 0, 0, 0.18);
}

.detail-handle {
  width: 36px;
  height: 4px;
  background: var(--ink-200);
  border-radius: 2px;
  margin: 0 auto 14px;
  flex-shrink: 0;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px 14px;
  border-bottom: 1px solid var(--ink-100);
  flex-shrink: 0;
}

.detail-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
  letter-spacing: -0.02em;
  flex: 1;
}

.detail-count-badge {
  font-size: 12px;
  font-weight: 700;
  color: var(--brand);
  background: var(--brand-light);
  padding: 2px 10px;
  border-radius: var(--radius-full);
}

.detail-close {
  width: 28px;
  height: 28px;
  border: none;
  background: var(--bg-muted);
  border-radius: 50%;
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-500);
  transition: background var(--fast) var(--ease-out);
}

.detail-close:hover { background: var(--bg-hover); }

.detail-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 20px 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: var(--bg-muted);
  animation: itemSlideIn 0.32s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes itemSlideIn {
  from { opacity: 0; transform: translateY(12px); }
  to   { opacity: 1; transform: translateY(0); }
}

.detail-item-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.detail-item-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.detail-item-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.detail-item-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-item-sub {
  font-size: 11px;
  color: var(--ink-400);
  font-weight: 500;
}

.detail-item-bar-wrap {
  width: 72px;
  height: 6px;
  background: var(--ink-100);
  border-radius: 3px;
  overflow: hidden;
  flex-shrink: 0;
}

.detail-item-bar {
  height: 100%;
  background: var(--brand-gradient);
  border-radius: 3px;
  transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

/* Sheet transitions */
.sheet-fade-enter-active { transition: opacity 0.22s ease; }
.sheet-fade-leave-active { transition: opacity 0.18s ease; }
.sheet-fade-enter-from,
.sheet-fade-leave-to { opacity: 0; }

.sheet-slide-enter-active { transition: transform 0.36s cubic-bezier(0.22, 1, 0.36, 1); }
.sheet-slide-leave-active { transition: transform 0.24s cubic-bezier(0.4, 0, 1, 1); }
.sheet-slide-enter-from,
.sheet-slide-leave-to { transform: translateY(100%); }

/* ── Journey / Trip panel ── */
.stat-item--active .stat-val {
  color: var(--brand);
}

.stat-item--active .stat-label {
  color: var(--brand);
  opacity: 0.8;
}

.trip-item {
  cursor: pointer;
  transition: background var(--fast) var(--ease-out), transform var(--fast) var(--ease-spring);
  align-items: center;
  gap: 12px;
}

.trip-item:hover {
  background: var(--bg-hover);
  transform: translateX(3px);
}

.trip-item--selected {
  background: var(--brand-light) !important;
  border: 1px solid rgba(232, 93, 4, 0.2);
}

.trip-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8);
}

.trip-arrow {
  font-size: 18px;
  color: var(--ink-300);
  flex-shrink: 0;
  transition: color var(--fast), transform var(--fast);
}

.trip-item--selected .trip-arrow {
  color: var(--brand);
  transform: translateX(2px);
}

/* ── Trip action bar (appears after selecting a trip) ── */
.trip-action-bar {
  padding: 12px 16px 4px;
  border-top: 1px solid var(--ink-100);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}

.trip-action-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.trip-action-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.trip-action-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-600);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.trip-action-btns {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.trip-btn-save {
  padding: 8px 16px;
  border-radius: var(--radius-full);
  border: none;
  background: var(--brand-gradient);
  color: var(--ink-900);
  font-size: 12px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(232, 93, 4, 0.25);
  transition: filter var(--fast), transform var(--fast);
  white-space: nowrap;
}

.trip-btn-save:hover {
  filter: brightness(0.93);
  transform: translateY(-1px);
}

.trip-action-slide-enter-active {
  transition: all 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}
.trip-action-slide-leave-active {
  transition: all 0.18s ease;
}
.trip-action-slide-enter-from,
.trip-action-slide-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

/* ── Custom date range section ── */
.custom-range-section {
  padding: 12px 16px 8px;
  border-top: 1px solid var(--ink-100);
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}

.custom-range-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-400);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.custom-range-preview {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.custom-range-stat {
  font-size: 12px;
  font-weight: 600;
  color: var(--brand);
  background: var(--brand-light);
  padding: 3px 10px;
  border-radius: var(--radius-full);
}

.custom-range-empty {
  font-size: 12px;
  color: var(--ink-400);
  font-weight: 500;
}

/* ── Save Journey Modal ── */
.save-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2100;
  background: rgba(20, 12, 4, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.save-modal {
  width: 100%;
  max-width: 400px;
  border-radius: 22px;
  padding: 22px 20px 18px;
  background: var(--bg-surface);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
}

.save-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.save-modal-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
  letter-spacing: -0.02em;
}

.save-modal-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.save-modal-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--bg-muted);
  border-radius: var(--radius-sm);
}

.save-modal-cities {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-700);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.save-modal-count {
  font-size: 11px;
  color: var(--brand);
  background: var(--brand-light);
  padding: 2px 8px;
  border-radius: var(--radius-full);
  white-space: nowrap;
  font-weight: 600;
}

.save-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.save-field-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-500);
}

.save-field-input {
  width: 100%;
  padding: 10px 44px 10px 12px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  font-size: 14px;
  color: var(--ink-900);
  font-family: inherit;
  outline: none;
  transition: border-color var(--fast);
  box-sizing: border-box;
}

.save-field-input:focus {
  border-color: var(--brand);
  background: var(--bg-surface);
}

.save-field-count {
  position: absolute;
  right: 12px;
  bottom: 10px;
  font-size: 11px;
  color: var(--ink-300);
}

.save-public-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.save-public-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-700);
}

.save-toggle {
  width: 44px;
  height: 26px;
  border-radius: 13px;
  border: none;
  background: var(--ink-200);
  cursor: pointer;
  position: relative;
  transition: background 0.25s ease;
  padding: 0;
}

.save-toggle.active {
  background: var(--brand);
}

.save-toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
  transition: left 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.save-toggle.active .save-toggle-thumb {
  left: 21px;
}

.save-public-hint {
  font-size: 11px;
  color: var(--ink-400);
  margin: -6px 0 0;
}

.save-modal-footer {
  display: flex;
  gap: 10px;
  margin-top: 18px;
}

.save-cancel-btn {
  flex: 1;
  padding: 11px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--ink-100);
  background: transparent;
  color: var(--ink-500);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
}

.save-confirm-btn {
  flex: 2;
  padding: 11px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--brand-gradient);
  color: var(--ink-900);
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(232, 93, 4, 0.28);
  transition: filter var(--fast);
}

.save-confirm-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.save-confirm-btn:not(:disabled):hover {
  filter: brightness(0.93);
}
</style>
