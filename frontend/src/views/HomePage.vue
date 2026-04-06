<template>
  <div class="home-page">
    <div v-if="mapError" class="map-error-banner">
      <strong>地图加载失败</strong> · {{ mapError }}
    </div>

    <!-- Map toolbar: only for logged-in users -->
    <transition name="slide-down">
      <div v-if="userStore.isLoggedIn" class="map-toolbar glass-card" id="map-toolbar">
        <div class="toolbar-copy">
          <div class="toolbar-title-row">
            <div class="toolbar-title">地图打卡</div>
            <span class="toolbar-badge">{{ checkins.length }} 条</span>
          </div>
          <div class="toolbar-subtitle">{{ activeUsers }} 位拾光者正在留下足迹</div>
        </div>

        <div class="toolbar-control-strip">
          <button
            type="button"
            :class="['toolbar-chip', 'toolbar-control', { active: !mapDetailMode }]"
            @click="toggleMapDisplayMode"
          >
            <span class="btn-icon">{{ mapDetailMode ? '📌' : '🖼️' }}</span>
            <span class="toolbar-label">{{ mapDetailMode ? '显示坐标' : '显示详情' }}</span>
          </button>
          <button
            type="button"
            :class="['toolbar-chip', 'toolbar-control', 'toolbar-chip-search', { active: showSearchPanel }]"
            @click="toggleSearchPanel"
          >
            <span class="btn-icon">🔎</span>
            <span class="toolbar-label">搜地点</span>
          </button>
          <button
            type="button"
            :class="['toolbar-chip', 'toolbar-control', { active: hotCitiesOpen }]"
            id="btn-hot-rank"
            @click="toggleHotCities"
          >
            <span class="btn-icon">🔥</span>
            <span class="toolbar-label">城市热榜</span>
          </button>
          <button type="button" class="toolbar-button toolbar-control is-primary" @click="useCurrentLocation">
            <span class="btn-icon">🎯</span>
            <span class="toolbar-label">{{ locating ? '定位中' : '定位打卡' }}</span>
          </button>
        </div>

        <transition name="panel-swap" mode="out-in">
          <div v-if="showSearchPanel" key="search" class="toolbar-panel place-search-panel">
            <div class="place-search-header">
              <div>
                <div class="place-search-title">搜索地点</div>
                <div class="place-search-subtitle">搜景点、餐厅或商圈，快速定位到地图</div>
              </div>
              <button type="button" class="place-search-close" @click="closeSearchPanel">完成</button>
            </div>

            <div class="place-search-bar">
              <label class="place-search-field">
                <span class="toolbar-search-icon">🔎</span>
                <input
                  v-model="searchKeyword"
                  type="text"
                  class="toolbar-search-input"
                  placeholder="搜索景点、餐厅、商圈"
                  @keydown.enter.prevent="searchPlaces"
                />
              </label>
              <button
                type="button"
                class="place-search-submit"
                :disabled="searchLoading || !searchKeyword.trim()"
                @click="searchPlaces"
              >
                {{ searchLoading ? '搜索中' : '搜索' }}
              </button>
            </div>

            <div v-if="searchError" class="place-search-empty">{{ searchError }}</div>
            <div v-else-if="searchLoading && !searchResults.length" class="place-search-empty">正在搜索具体地点...</div>
            <div v-else-if="searchResults.length" class="place-search-list">
              <div
                v-for="place in searchResults"
                :key="place.id"
                class="place-search-item"
                @click="focusSearchResult(place)"
              >
                <div class="place-search-main">
                  <div class="place-search-name">{{ place.name }}</div>
                  <div class="place-search-meta">
                    <span v-if="place.city">{{ place.city }}</span>
                    <span v-if="place.address">{{ place.address }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="hotCitiesOpen" key="hot-cities" class="toolbar-panel toolbar-panel-hot">
            <HotCitiesPanel
              class="hot-cities-inline"
              :closable="true"
              @close="hotCitiesOpen = false"
            />
          </div>
        </transition>
      </div>
    </transition>

    <!-- Guest banner: shown to unauthenticated users -->
    <transition name="slide-down">
      <div v-if="!userStore.isLoggedIn" class="guest-banner glass-card" id="guest-banner">
        <div class="guest-banner-top">
          <div class="guest-banner-left">
            <span class="guest-badge">拾光坐标</span>
            <span class="guest-tagline">探索拾光者的足迹，记录你的旅行故事</span>
          </div>
          <div class="guest-banner-actions">
            <router-link to="/login" class="btn-ghost-sm">登录</router-link>
            <router-link to="/register" class="btn-primary btn-sm">注册</router-link>
          </div>
        </div>
        <div v-if="checkins.length" class="guest-stats-row">
          <span class="guest-stat"><span class="guest-stat-val">{{ checkins.length }}</span> 条公开打卡</span>
          <span class="guest-stat-sep">·</span>
          <span class="guest-stat"><span class="guest-stat-val">{{ activeUsers }}</span> 位拾光者</span>
        </div>
      </div>
    </transition>

    <transition name="slide-up">
      <div v-if="pickMode" class="pick-hint glass-card">
        <span class="pick-title">📍 选点模式已开启</span>
        <span class="pick-copy">点击地图任意位置，带着坐标去填写打卡信息。</span>
      </div>
    </transition>

    <div v-if="!userStore.isLoggedIn" :class="['hot-cities-stack', 'is-guest']">
      <button
        type="button"
        :class="['hot-rank-trigger glass-card', { active: hotCitiesOpen }]"
        id="btn-hot-rank"
        @click="toggleHotCities"
      >
        <span class="trigger-icon">🔥</span>
        <span>{{ hotCitiesOpen ? '收起热榜' : '城市热榜' }}</span>
      </button>

      <transition name="slide-down">
        <HotCitiesPanel
          v-if="hotCitiesOpen"
          class="hot-cities-overlay animate-fade-in-up"
          :closable="true"
          @close="hotCitiesOpen = false"
        />
      </transition>
    </div>

    <div ref="mapContainer" :class="['map-container', { ready: isMapReady }]" id="map-container"></div>

    <!-- North/compass reset button — liquid glass on map -->
    <button
      v-if="isMapReady"
      class="btn-north"
      title="重置地图方向朝北"
      @click="resetMapNorth"
    >北</button>

    <transition name="map-fade">
      <div v-if="showMapLoadingOverlay" class="map-loading-overlay" aria-live="polite">
        <div class="map-loading-gradient"></div>
        <div class="map-loading-card glass-card">
          <div class="map-loading-topline">MAP SQUARE</div>
          <div class="map-loading-title">正在展开地图广场</div>
          <p class="map-loading-copy">{{ mapLoadingCopy }}</p>
          <div class="map-loading-track" aria-hidden="true">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
    </transition>

    <transition name="map-chip">
      <div v-if="showMapSyncStatus" class="map-sync-chip glass-card">
        正在同步最新足迹...
      </div>
    </transition>

    <!-- Checkin preview popup -->
    <transition name="slide-up">
      <div v-if="selectedCheckin" class="checkin-preview glass-card" id="checkin-preview">
        <button class="preview-close" @click="selectedCheckin = null" aria-label="关闭">✕</button>
        <div v-if="selectedCheckin.media_type === 'video' && selectedCheckin.video_url" class="preview-image-wrap">
          <video
            :src="getImageUrl(selectedCheckin.video_url)"
            class="preview-image"
            controls
            preload="metadata"
            style="background:#000"
          ></video>
        </div>
        <div v-else-if="selectedCheckin.preview_image_url" class="preview-image-wrap">
          <img
            :src="getImageUrl(selectedCheckin.preview_image_url)"
            :alt="selectedCheckin.location_name"
            class="preview-image"
          />
        </div>
        <div class="preview-content">
          <div class="preview-header">
            <div class="preview-header-text">
              <div class="preview-name">{{ selectedCheckin.location_name }}</div>
              <div class="preview-meta">
                <router-link :to="`/profile/${selectedCheckin.user_id}`" class="preview-user">
                  {{ selectedCheckin.user_nickname }}
                </router-link>
                <span class="meta-sep">·</span>
                <span>{{ formatCheckinDate(selectedCheckin) }}</span>
                <span v-if="selectedCheckin.media_type === 'video'" class="meta-sep">·</span>
                <span v-if="selectedCheckin.media_type === 'video'">视频</span>
                <template v-else>
                  <span v-if="selectedCheckin.photo_count" class="meta-sep">·</span>
                  <span v-if="selectedCheckin.photo_count">{{ selectedCheckin.photo_count }} 张照片</span>
                </template>
              </div>
            </div>
          </div>
          <p v-if="selectedCheckin.city || selectedCheckin.address" class="preview-address">
            📌 {{ selectedCheckin.city || selectedCheckin.address }}
          </p>
          <p v-if="selectedCheckin.preview_text" class="preview-text">
            {{ selectedCheckin.preview_text }}
          </p>
          <div class="preview-social">
            <span>❤️ {{ selectedCheckin.likes_count || 0 }}</span>
            <span>💬 {{ selectedCheckin.comments_count || 0 }}</span>
          </div>
          <div class="preview-actions">
            <router-link :to="`/checkins/${selectedCheckin.id}`" class="btn-primary btn-sm">
              查看详情
            </router-link>
            <a
              v-if="selectedCheckin.latitude && selectedCheckin.longitude"
              :href="`https://uri.amap.com/navigation?to=${selectedCheckin.longitude},${selectedCheckin.latitude},${encodeURIComponent(selectedCheckin.location_name || '')}&mode=car&src=拾光坐标&callnative=1`"
              target="_blank"
              rel="noopener"
              class="btn-secondary btn-sm"
            >导航到此处</a>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getMapCheckins, searchCheckinPlaces } from '../api/checkins'
import { formatCheckinDate, getImageUrl } from '../lib/checkins'
import { convertGpsToAmap, loadAmap } from '../lib/amap'
import { useUserStore } from '../stores/user'
import HotCitiesPanel from '../components/HotCitiesPanel.vue'

const mapContainer = ref(null)
const checkins = ref([])
const selectedCheckin = ref(null)
const pickMode = ref(false)
const locating = ref(false)
const mapDetailMode = ref(true) // true=显示详情(照片), false=显示坐标(小点)
const mapError = ref('')
const hotCitiesOpen = ref(false)
const isMapReady = ref(false)
const isCheckinsLoading = ref(true)
const searchKeyword = ref('')
const searchLoading = ref(false)
const searchError = ref('')
const searchResults = ref([])
const searchPanelOpen = ref(false)

let map = null
let AMapInstance = null
let markers = []
let placeSearch = null
let searchMarker = null
let searchRequestId = 0

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeUsers = computed(() =>
  new Set(checkins.value.map((c) => c.user_id)).size
)
const showMapLoadingOverlay = computed(() => !mapError.value && !isMapReady.value)
const showMapSyncStatus = computed(() => !mapError.value && isMapReady.value && isCheckinsLoading.value)
const showSearchPanel = computed(() =>
  searchPanelOpen.value || searchLoading.value || searchResults.value.length > 0 || Boolean(searchError.value)
)
const mapLoadingCopy = computed(() =>
  userStore.isLoggedIn
    ? '地图引擎正在预热，公开打卡和实时足迹会一起载入。'
    : '正在连接旅行者公开地图，第一次进入会稍慢，之后会更顺。'
)

function handleMapComplete() {
  isMapReady.value = true
  if (map) {
    requestAnimationFrame(() => {
      map.resize()
    })
  }
}

async function initMap() {
  if (map || !mapContainer.value) return

  AMapInstance = await loadAmap()
  map = new AMapInstance.Map(mapContainer.value, {
    viewMode: '2D',
    zoom: 5,
    center: [105.0, 35.0],
    mapStyle: 'amap://styles/light',
    resizeEnable: true,
    features: ['bg', 'road', 'building', 'point'],
  })

  map.addControl(new AMapInstance.Scale())
  map.addControl(new AMapInstance.ToolBar({ position: 'RB' }))
  placeSearch = new AMapInstance.PlaceSearch({
    pageSize: 8,
    pageIndex: 1,
    city: '全国',
    citylimit: false,
    extensions: 'base',
  })
  map.on('complete', handleMapComplete)
  map.on('click', handleMapClick)
}

function resetMapNorth() {
  if (map) map.setRotation(0)
}

function clearMarkers() {
  if (!map || !markers.length) return
  map.remove(markers)
  markers = []
}

function renderMarkers(fitView = true) {
  if (!map || !AMapInstance) return
  clearMarkers()

  markers = checkins.value.map((checkin) => {
    const photoUrl = mapDetailMode.value && checkin.preview_image_url
      ? getImageUrl(checkin.preview_image_url)
      : null

    const markerContent = photoUrl
      ? `<div class="map-photo-pin"><img src="${photoUrl}" class="pin-photo" loading="lazy" /><span class="pin-dot-small"></span></div>`
      : `<div class="map-coord-dot"></div>`

    const offset = photoUrl
      ? new AMapInstance.Pixel(-22, -22)
      : new AMapInstance.Pixel(-5, -5)

    const marker = new AMapInstance.Marker({
      position: [checkin.longitude, checkin.latitude],
      offset,
      content: markerContent,
    })

    marker.on('click', () => {
      closeSearchPanel()
      selectedCheckin.value = checkin
      pickMode.value = false
      map.setCenter([checkin.longitude, checkin.latitude])
    })

    return marker
  })

  if (markers.length) {
    map.add(markers)
    if (fitView) {
      map.setFitView(markers, false, [80, 80, 160, 80])
    }
  }
}

function clearSearchMarker() {
  if (!map || !searchMarker) return
  map.remove(searchMarker)
  searchMarker = null
}

function getPoiCoordinate(location) {
  if (!location) return null
  const longitude = typeof location.lng === 'number' ? location.lng : location.getLng?.()
  const latitude = typeof location.lat === 'number' ? location.lat : location.getLat?.()
  if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null
  return { longitude, latitude }
}

function normalizeSearchResult(poi, index) {
  const coordinate = getPoiCoordinate(poi.location)
  if (!coordinate) return null

  const city = String(poi.cityname || poi.pname || poi.adname || '').trim()
  const addressParts = [poi.pname, poi.cityname, poi.adname, poi.address]
    .map((item) => String(item || '').trim())
    .filter(Boolean)
  const address = [...new Set(addressParts)].join(' ')

  return {
    id: poi.id || `${poi.name || 'poi'}-${index}-${coordinate.longitude}-${coordinate.latitude}`,
    name: String(poi.name || '未命名地点').trim(),
    city,
    address,
    latitude: coordinate.latitude,
    longitude: coordinate.longitude,
  }
}

function focusSearchResult(place) {
  if (!map || !AMapInstance) return
  selectedCheckin.value = null
  pickMode.value = false

  const position = [place.longitude, place.latitude]
  map.setZoomAndCenter(Math.max(map.getZoom(), 15), position)

  clearSearchMarker()
  searchMarker = new AMapInstance.Marker({
    position,
    offset: new AMapInstance.Pixel(-18, -42),
    content: '<div class="search-pin"><span class="search-pin-core"></span></div>',
  })
  map.add(searchMarker)
}

function clearSearchState() {
  searchLoading.value = false
  searchError.value = ''
  searchResults.value = []
  clearSearchMarker()
}

function closeSearchPanel() {
  searchRequestId += 1
  searchPanelOpen.value = false
  clearSearchState()
}

async function searchPlaces() {
  if (!placeSearch || !map) {
    ElMessage.warning('地图还没准备好')
    return
  }

  const keyword = searchKeyword.value.trim()
  if (!keyword) {
    ElMessage.warning('先输入想搜索的地点')
    return
  }

  const requestId = ++searchRequestId
  searchLoading.value = true
  searchPanelOpen.value = true
  searchError.value = ''
  searchResults.value = []
  selectedCheckin.value = null
  pickMode.value = false
  hotCitiesOpen.value = false

  try {
    const pois = await new Promise((resolve, reject) => {
      placeSearch.search(keyword, (status, result) => {
        if (status !== 'complete') {
          reject(new Error('地点搜索失败'))
          return
        }
        resolve(result?.poiList?.pois || [])
      })
    })

    const normalized = pois
      .map((item, index) => normalizeSearchResult(item, index))
      .filter(Boolean)

    let finalResults = normalized

    if (!finalResults.length) {
      const fallback = await searchCheckinPlaces(keyword, 8)
      if (requestId !== searchRequestId) return
      finalResults = Array.isArray(fallback.data) ? fallback.data : []
    }

    if (requestId !== searchRequestId) return
    searchResults.value = finalResults

    if (!finalResults.length) {
      searchError.value = '没有找到对应地点，换个关键词试试'
      clearSearchMarker()
      return
    }

    focusSearchResult(finalResults[0])
  } catch (error) {
    try {
      const fallback = await searchCheckinPlaces(keyword, 8)
      if (requestId !== searchRequestId) return
      const finalResults = Array.isArray(fallback.data) ? fallback.data : []
      if (requestId !== searchRequestId) return
      searchResults.value = finalResults

      if (!finalResults.length) {
        searchError.value = '没有找到对应地点，换个关键词试试'
        clearSearchMarker()
        return
      }

      focusSearchResult(finalResults[0])
    } catch (fallbackError) {
      console.error('Place search failed:', error, fallbackError)
      searchError.value = '地点搜索失败，请稍后重试'
      clearSearchMarker()
    }
  } finally {
    searchLoading.value = false
  }
}

async function loadPublicCheckins() {
  isCheckinsLoading.value = true
  try {
    const res = await getMapCheckins()
    checkins.value = res.data
  } catch (error) {
    console.error('Failed to load public checkins:', error)
  } finally {
    isCheckinsLoading.value = false
  }
}

async function initMapAndLoad() {
  if (!mapContainer.value) return
  isMapReady.value = false
  mapError.value = ''
  const checkinsPromise = loadPublicCheckins()
  await nextTick()
  try {
    await initMap()
    await checkinsPromise
    if (map) {
      requestAnimationFrame(() => {
        renderMarkers()
      })
    }
  } catch (error) {
    console.error(error)
    mapError.value = error.message || '地图初始化失败'
  }
}

async function consumePickQuery() {
  if (!userStore.isLoggedIn || route.query.pick !== '1') return
  pickMode.value = true
  selectedCheckin.value = null
  ElMessage.info('点击地图选择打卡位置')
  await router.replace({ name: 'home' })
}

function startPickMode() {
  if (!map) {
    ElMessage.warning('地图还没准备好')
    return
  }
  closeSearchPanel()
  pickMode.value = true
  selectedCheckin.value = null
  ElMessage.info('点击地图任意位置开始打卡')
}

function toggleMapDisplayMode() {
  mapDetailMode.value = !mapDetailMode.value
  renderMarkers(false) // 切换模式时保持当前缩放级别和中心点
}

function toggleHotCities() {
  if (!hotCitiesOpen.value) {
    closeSearchPanel()
  }
  hotCitiesOpen.value = !hotCitiesOpen.value
}

function toggleSearchPanel() {
  if (showSearchPanel.value) {
    closeSearchPanel()
    return
  }
  hotCitiesOpen.value = false
  searchPanelOpen.value = true
  selectedCheckin.value = null
  pickMode.value = false
}

async function pushToCheckinForm(latitude, longitude, source, details = {}) {
  router.push({
    name: 'checkin-new',
    query: {
      lat: latitude.toFixed(6),
      lng: longitude.toFixed(6),
      source,
      city: details.city || '',
      address: details.address || '',
      location_name: details.location_name || '',
    },
  })
}

async function handleMapClick(event) {
  if (!pickMode.value) return
  if (!userStore.isLoggedIn) {
    ElMessage.info('请登录后再发起打卡')
    router.push({ name: 'login' })
    return
  }
  pickMode.value = false
  await pushToCheckinForm(event.lnglat.lat, event.lnglat.lng, 'map')
}

async function startSearchCheckin(place) {
  await pushToCheckinForm(place.latitude, place.longitude, 'search', {
    city: place.city,
    address: place.address,
    location_name: place.name,
  })
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    ElMessage.error('当前浏览器不支持定位，请改用地图选点')
    startPickMode()
    return
  }

  // ── iOS KEY FIX ──────────────────────────────────────────────────────────
  // iOS Safari/Chrome only allow getCurrentPosition inside a synchronous user-
  // gesture handler. Call it FIRST before any state mutations, then update UI.
  // We use enableHighAccuracy:false (WiFi/cell) which works indoors; if it
  // fails we retry once with GPS.
  // ─────────────────────────────────────────────────────────────────────────
  let retried = false

  function onSuccess({ coords }) {
    locating.value = false
    convertGpsToAmap(coords.longitude, coords.latitude)
      .then(({ latitude, longitude }) =>
        pushToCheckinForm(latitude, longitude, 'geolocation')
      )
      .catch(() =>
        pushToCheckinForm(coords.latitude, coords.longitude, 'geolocation')
      )
  }

  function onError(error) {
    // Low-accuracy POSITION_UNAVAILABLE or TIMEOUT → retry once with GPS
    if (!retried && (error.code === 2 || error.code === 3)) {
      retried = true
      navigator.geolocation.getCurrentPosition(onSuccess, onError, {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 0,
      })
      return
    }

    locating.value = false
    if (error.code === 1 /* PERMISSION_DENIED */) {
      ElMessage.error(
        'iOS：设置 → 隐私与安全性 → 定位服务 → Safari（或Chrome）→ 选择「允许」，然后重试'
      )
    } else if (error.code === 2 /* POSITION_UNAVAILABLE */) {
      ElMessage.warning('当前位置信号弱，无法获取定位，请改用地图选点')
    } else {
      ElMessage.warning('定位超时，请改用地图选点或检查网络后重试')
    }
    startPickMode()
  }

  // Start geolocation BEFORE any async / state updates (user-gesture context)
  navigator.geolocation.getCurrentPosition(onSuccess, onError, {
    enableHighAccuracy: false,
    timeout: 10000,
    maximumAge: 0,
  })

  // Update UI after starting the request
  closeSearchPanel()
  locating.value = true
  pickMode.value = false
}

function destroyMap() {
  clearMarkers()
  clearSearchMarker()
  if (map) {
    map.off('click', handleMapClick)
    map.off('complete', handleMapComplete)
    map.destroy()
    map = null
  }
  AMapInstance = null
  placeSearch = null
  isMapReady.value = false
  selectedCheckin.value = null
}

onMounted(async () => {
  await initMapAndLoad()
  await consumePickQuery()
})

watch(
  () => route.query.pick,
  async () => { await consumePickQuery() }
)

onBeforeUnmount(() => { destroyMap() })
</script>

<style scoped>
.home-page {
  height: 100%;
  width: 100%;
  position: relative;
  overflow: hidden;
  background: var(--bg-base);
}

.map-container {
  height: 100%;
  width: 100%;
  background:
    radial-gradient(circle at 16% 18%, rgba(232, 93, 4, 0.08), transparent 30%),
    radial-gradient(circle at 84% 16%, rgba(244, 162, 97, 0.10), transparent 26%),
    linear-gradient(145deg, #fdf6f0 0%, #f5ede6 48%, #fdf0e8 100%);
  transition: filter 0.45s ease, opacity 0.45s ease, background 0.45s ease;
}

/* ─── North/compass reset button — liquid glass (map dark-surface variant) ── */
.btn-north {
  position: fixed;
  top: 76px; /* below the header (~60px) + 16px gap */
  right: 16px;
  z-index: 900;

  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  color: var(--ink-700);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  transition:
    background var(--fast) var(--ease-out),
    transform var(--fast) var(--ease-spring),
    box-shadow var(--fast) var(--ease-out);
}

.btn-north:hover {
  background: var(--bg-muted);
  color: var(--brand);
}
.btn-north:active {
  transform: scale(0.94);
}

.map-container.ready {
  background: var(--bg-muted);
}

.map-loading-overlay {
  position: absolute;
  inset: 0;
  z-index: 920;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  pointer-events: none;
}

.map-loading-gradient {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 20%, rgba(232, 93, 4, 0.08), transparent 32%),
    radial-gradient(circle at 80% 18%, rgba(244, 162, 97, 0.10), transparent 28%),
    linear-gradient(160deg, #fdf6f0 0%, #f5ede6 100%);
  animation: mapAmbientShift 9s ease-in-out infinite;
}

.map-loading-card {
  position: relative;
  z-index: 1;
  width: min(420px, calc(100% - 32px));
  padding: 24px 24px 22px;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: mapCardRise 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

.map-loading-topline {
  font-size: 11px;
  line-height: 1;
  font-weight: 700;
  letter-spacing: 0.24em;
  color: var(--brand);
}

.map-loading-title {
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1.05;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--ink-900);
}

.map-loading-copy {
  max-width: 28ch;
  font-size: 14px;
  line-height: 1.6;
  color: var(--ink-500);
}

.map-loading-track {
  margin-top: 4px;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.map-loading-track span {
  height: 6px;
  border-radius: 999px;
  background: linear-gradient(
    90deg,
    rgba(232, 93, 4, 0.12) 0%,
    rgba(244, 162, 97, 0.40) 50%,
    rgba(232, 93, 4, 0.12) 100%
  );
  background-size: 220% 100%;
  animation: shimmer 1.3s linear infinite;
}

.map-loading-track span:nth-child(2) {
  animation-delay: 0.12s;
}

.map-loading-track span:nth-child(3) {
  animation-delay: 0.24s;
}

.map-sync-chip {
  position: absolute;
  top: 78px;
  left: 50%;
  z-index: 1001;
  transform: translateX(-50%);
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-500);
  white-space: nowrap;
}

/* Guest banner */
.guest-banner {
  position: absolute;
  top: 16px;
  left: 16px;
  right: 16px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 20px;
}

.guest-banner-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.guest-banner-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.guest-stats-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--ink-500);
  padding-top: 2px;
  border-top: 1px solid var(--ink-100);
}

.guest-stat {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.guest-stat-val {
  font-weight: 700;
  color: var(--ink-900);
  font-size: 13px;
}

.guest-stat-sep {
  color: var(--ink-100);
}

.guest-badge {
  flex-shrink: 0;
  display: inline-flex;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--brand-gradient);
  color: white;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.guest-tagline {
  font-size: 13px;
  color: var(--ink-500);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guest-banner-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.btn-ghost-sm {
  display: inline-flex;
  align-items: center;
  padding: 6px 14px;
  background: transparent;
  color: var(--ink-500);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  transition: background var(--fast) var(--ease-out), color var(--fast) var(--ease-out);
  font-family: inherit;
}

.btn-ghost-sm:hover {
  background: var(--bg-muted);
  color: var(--ink-900);
  border-color: var(--border-strong);
}

/* Logged-in toolbar */
.map-toolbar {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  width: min(356px, calc(100% - 28px));
  padding: 16px;
  background: var(--bg-muted);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
}

.toolbar-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
  align-items: center;
  text-align: center;
}

.toolbar-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.toolbar-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.02em;
}

.toolbar-subtitle {
  color: var(--ink-300);
  font-size: 12px;
}

.toolbar-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: var(--radius-full);
  background: var(--brand-light);
  color: var(--brand);
  font-size: 11px;
  font-weight: 700;
}

.toolbar-control-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.toolbar-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 52px;
  padding: 8px 6px;
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  color: var(--ink-700);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--fast), color var(--fast), border-color var(--fast);
  font-family: inherit;
}

.toolbar-chip:hover {
  background: var(--brand-light);
  color: var(--brand);
  border-color: rgba(232, 93, 4, 0.2);
}

.toolbar-chip.active {
  background: var(--brand-light);
  color: var(--brand);
  border-color: rgba(232, 93, 4, 0.25);
}

.toolbar-chip-search {
  color: var(--brand);
  background: var(--brand-light);
  border-color: rgba(232, 93, 4, 0.2);
}

.toolbar-search-icon {
  font-size: 14px;
  color: var(--ink-300);
}

.toolbar-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 52px;
  padding: 8px 6px;
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  color: var(--ink-700);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background var(--fast), color var(--fast);
  font-family: inherit;
}

.toolbar-button:hover {
  background: var(--bg-hover);
  color: var(--ink-900);
}

.toolbar-button.is-primary {
  border: 1.5px solid rgba(232, 93, 4, 0.30);
  color: var(--ink-900);
  background: var(--bg-muted);
}

.toolbar-button.is-primary:hover {
  background: var(--brand-light);
  border-color: rgba(232, 93, 4, 0.45);
  color: var(--ink-900);
}

.toolbar-control {
  width: 100%;
  flex-direction: column;
  text-align: center;
  line-height: 1.1;
}

.btn-icon { font-size: 14px; line-height: 1; }

.toolbar-label {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-sm {
  padding: 7px 16px;
  font-size: 13px;
  border-radius: var(--radius-full);
}

/* Stat items */
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 72px;
}

.stat-value {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
  color: var(--brand);
  letter-spacing: -0.02em;
}

.stat-label {
  font-size: 11px;
  color: var(--ink-300);
  margin-top: 1px;
}

.stat-divider {
  width: 1px;
  background: var(--ink-100);
  align-self: stretch;
}

/* Pick hint */
.pick-hint {
  position: absolute;
  left: 16px;
  bottom: 108px;
  z-index: 1000;
  max-width: 400px;
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pick-title {
  font-weight: 700;
  font-size: 14px;
}

.pick-copy {
  color: var(--ink-500);
  font-size: 13px;
}

/* Map error */
.map-error-banner {
  position: absolute;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1001;
  padding: 10px 18px;
  background: rgba(255, 45, 85, 0.1);
  border: 1px solid rgba(255, 45, 85, 0.2);
  border-radius: var(--radius-full);
  font-size: 13px;
  color: var(--pink);
  white-space: nowrap;
}

/* Checkin preview */
.checkin-preview {
  position: absolute;
  left: 16px;
  bottom: 108px;
  z-index: 1001;
  width: 340px;
  overflow: hidden;
}

.preview-image-wrap {
  position: relative;
  height: 160px;
  overflow: hidden;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.checkin-preview:hover .preview-image {
  transform: scale(1.03);
}

.preview-close {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  cursor: pointer;
  z-index: 2;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--fast) var(--ease-out);
}

.preview-close:hover {
  background: rgba(0, 0, 0, 0.72);
}

.preview-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.preview-header-text {
  flex: 1;
  min-width: 0;
}

.preview-name {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--ink-900);
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  color: var(--ink-300);
  font-size: 12px;
  margin-top: 6px;
}

.meta-sep { color: var(--ink-100); }

.preview-user {
  color: var(--brand);
  text-decoration: none;
  font-weight: 500;
}

.preview-user:hover { text-decoration: underline; }

.preview-address {
  color: var(--ink-500);
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.preview-text {
  color: var(--ink-500);
  font-size: 13px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.preview-actions {
  display: flex;
  gap: 8px;
  margin-top: 2px;
}

/* Hot cities overlay */
.hot-cities-stack {
  position: absolute;
  left: 16px;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.hot-cities-stack.is-guest {
  top: 148px;
}

.hot-rank-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  padding: 10px 14px;
  border: none;
  color: var(--ink-900);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  transition: transform var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out), background var(--fast) var(--ease-out);
}

.hot-rank-trigger:hover {
  transform: translateY(-1px);
}

.hot-rank-trigger.active {
  background: var(--bg-surface);
  box-shadow: var(--shadow-float);
}

.trigger-icon {
  font-size: 14px;
}

.hot-cities-overlay {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  width: min(280px, calc(100vw - 24px));
  max-height: 400px;
  overflow-y: auto;
}

.toolbar-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-card);
}

.toolbar-panel-hot {
  padding: 10px;
}

.place-search-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.place-search-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.place-search-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
}

.place-search-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ink-500);
}

.place-search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}

.place-search-field {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  height: 40px;
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  border: 1px solid var(--ink-100);
}

.toolbar-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--ink-900);
  font-size: 13px;
  font-family: inherit;
}

.toolbar-search-input::placeholder {
  color: var(--ink-300);
}

.place-search-submit {
  min-width: 68px;
  height: 40px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--brand-gradient);
  color: white;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.25);
}

.place-search-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.place-search-close {
  border: none;
  background: var(--bg-muted);
  color: var(--brand);
  border-radius: var(--radius-full);
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.place-search-empty {
  padding: 12px 2px 4px;
  color: var(--ink-500);
  font-size: 13px;
}

.place-search-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 288px;
  overflow-y: auto;
}

.place-search-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  border: 1px solid var(--ink-100);
  cursor: pointer;
  transition: transform var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out), border-color var(--fast) var(--ease-out);
}

.place-search-item:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-card);
  border-color: rgba(232, 93, 4, 0.2);
}

.place-search-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.place-search-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
}

.place-search-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: var(--ink-500);
}


.hot-cities-inline {
  width: 100%;
}

/* Preview social counts */
.preview-social {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--ink-500);
  margin-top: -4px;
}

/* Map pin markers */
/* 坐标模式：纯小圆点（蓝色，在浅色地图上清晰可见） */
:deep(.map-coord-dot) {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #1a6fd4;
  border: 2px solid white;
  box-shadow: 0 1px 4px rgba(26, 111, 212, 0.55);
  cursor: pointer;
  transition: transform 0.15s ease;
}

:deep(.map-coord-dot:hover) {
  transform: scale(1.4);
}

:deep(.map-photo-pin) {
  position: relative;
  width: 44px;
  height: 44px;
  cursor: pointer;
}

:deep(.pin-photo) {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  display: block;
}

:deep(.pin-dot-small) {
  position: absolute;
  bottom: -4px;
  left: 50%;
  transform: translateX(-50%);
  width: 8px;
  height: 8px;
  background: var(--brand);
  border-radius: 50%;
  border: 2px solid white;
}

:deep(.search-pin) {
  position: relative;
  width: 36px;
  height: 44px;
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

:deep(.search-pin::before) {
  content: '';
  width: 30px;
  height: 30px;
  border-radius: 50% 50% 50% 6px;
  transform: rotate(-45deg);
  background: var(--brand-gradient);
  box-shadow: 0 10px 22px rgba(232, 93, 4, 0.34);
  display: block;
}

:deep(.search-pin-core) {
  position: absolute;
  top: 8px;
  left: 50%;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: white;
  transform: translateX(-50%);
}

/* Transitions */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: opacity 0.42s cubic-bezier(0.22, 1, 0.36, 1), transform 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: opacity 0.38s cubic-bezier(0.22, 1, 0.36, 1), transform 0.38s cubic-bezier(0.22, 1, 0.36, 1);
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.panel-swap-enter-active,
.panel-swap-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.panel-swap-enter-from,
.panel-swap-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.map-fade-enter-active,
.map-fade-leave-active {
  transition: opacity 0.45s cubic-bezier(0.22, 1, 0.36, 1);
}

.map-fade-enter-from,
.map-fade-leave-to {
  opacity: 0;
}

.map-chip-enter-active,
.map-chip-leave-active {
  transition: opacity 0.28s ease, transform 0.28s ease;
}

.map-chip-enter-from,
.map-chip-leave-to {
  opacity: 0;
  transform: translate(-50%, -8px);
}

@keyframes mapCardRise {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes mapAmbientShift {
  0%,
  100% {
    transform: scale(1) translate3d(0, 0, 0);
  }
  50% {
    transform: scale(1.04) translate3d(0, -8px, 0);
  }
}

@media (max-width: 768px) {
  .guest-banner {
    gap: 8px;
  }

  .guest-banner-top {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }

  .guest-banner-left {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .guest-banner-actions {
    justify-content: flex-end;
  }

  .map-toolbar {
    top: 12px;
    left: 12px;
    width: calc(100% - 24px);
    padding: 12px;
    gap: 8px;
    border-radius: var(--radius-lg);
  }

  .map-loading-card {
    width: calc(100% - 24px);
    padding: 20px 18px 18px;
  }

  .map-loading-title {
    font-size: 24px;
  }

  .map-sync-chip {
    top: 72px;
    max-width: calc(100% - 24px);
  }

  .toolbar-control-strip {
    gap: 6px;
  }

  .toolbar-subtitle {
    font-size: 11px;
  }

  .toolbar-copy {
    gap: 2px;
  }

  .toolbar-title {
    font-size: 14px;
  }

  .toolbar-chip,
  .toolbar-button {
    min-height: 46px;
    padding: 7px 4px;
    border-radius: var(--radius-sm);
    font-size: 11px;
  }

  .btn-icon {
    font-size: 13px;
  }

  .toolbar-label {
    letter-spacing: -0.01em;
  }

  .toolbar-panel {
    padding: 12px;
    border-radius: var(--radius-md);
  }

  .place-search-header {
    gap: 10px;
  }

  .place-search-title {
    font-size: 15px;
  }

  .place-search-subtitle {
    margin-top: 2px;
    font-size: 11px;
  }

  .place-search-bar {
    align-items: stretch;
  }

  .place-search-field,
  .place-search-submit {
    height: 38px;
  }

  .place-search-list {
    max-height: 250px;
  }

  .place-search-item {
    align-items: flex-start;
    padding: 11px 12px;
  }

  .place-search-meta {
    flex-direction: column;
    gap: 2px;
  }

  .checkin-preview {
    left: 16px;
    right: 16px;
    width: auto;
    bottom: 104px;
  }

  .checkin-preview .preview-image-wrap {
    height: 110px;
  }

  .checkin-preview .preview-content {
    padding: 11px 14px;
    gap: 6px;
  }

  .checkin-preview .preview-name {
    font-size: 15px;
  }

  .checkin-preview .preview-actions {
    margin-top: 0;
  }

  .pick-hint {
    left: 16px;
    right: 16px;
    max-width: none;
    bottom: 104px;
  }

  .hot-cities-stack.is-guest {
    top: 200px;
  }

  .hot-rank-trigger {
    padding: 10px 12px;
  }
}
</style>
