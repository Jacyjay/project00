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
        <button
          v-if="!loading && checkins.length > 0"
          class="btn-report"
          @click="openReport"
        >✨ 生成我的专属足迹报告</button>
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

      <!-- North reset -->
      <button v-if="isMapReady" class="btn-north" @click="resetNorth" title="重置朝北">北</button>

      <!-- Selected checkin preview -->
      <transition name="slide-up">
        <div v-if="selectedCheckin" class="preview-card glass-card">
          <button class="preview-close" @click="selectedCheckin = null">✕</button>
          <div class="preview-inner">
            <div v-if="selectedCheckin.preview_image_url || selectedCheckin.photos?.[0]?.image_url" class="preview-photo-wrap">
              <img :src="imageUrl(selectedCheckin.preview_image_url || selectedCheckin.photos?.[0]?.image_url)" class="preview-photo" />
            </div>
            <div class="preview-content">
              <div class="preview-name">{{ selectedCheckin.location_name || selectedCheckin.city || '未知地点' }}</div>
              <div class="preview-meta">{{ selectedCheckin.city }} · {{ formatDate(selectedCheckin.created_at) }}</div>
              <p v-if="selectedCheckin.content" class="preview-text">{{ selectedCheckin.content }}</p>
              <router-link :to="`/checkins/${selectedCheckin.id}`" class="btn-primary btn-sm preview-btn">
                查看详情
              </router-link>
            </div>
          </div>
        </div>
      </transition>

      <!-- Map -->
      <div ref="mapContainer" :class="['map-container', { ready: isMapReady }]"></div>

      <!-- Loading overlay -->
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
import { getUserCheckins, getFootprintReport, refreshFootprintReport } from '../api/checkins'
import { loadAmap } from '../lib/amap'
import { getImageUrl } from '../lib/checkins'

const userStore = useUserStore()
const mapContainer = ref(null)
const checkins = ref([])
const loading = ref(true)
const isMapReady = ref(false)
const selectedCheckin = ref(null)

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

const cityCount = computed(() =>
  new Set(checkins.value.map(c => c.city).filter(Boolean)).size
)

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
  const items = buildCountMap(checkins.value.map(c => c.city).filter(Boolean))
  const maxCount = items[0]?.count || 1
  detailPanel.value = { type: 'city', title: '到访城市', items, maxCount }
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

function renderMarkers() {
  if (!map || !AMap || !checkins.value.length) return
  clearMarkers()

  markers = checkins.value
    .filter(c => c.latitude && c.longitude)
    .map(checkin => {
      const rawUrl = checkin.preview_image_url || checkin.photos?.[0]?.image_url || null
      const photoUrl = rawUrl ? getImageUrl(rawUrl) : null
      const content = photoUrl
        ? `<div class="fp-photo-pin"><img src="${photoUrl}" class="fp-pin-photo" loading="lazy" /><span class="fp-pin-dot"></span></div>`
        : `<div class="fp-pin-plain"><span class="fp-pin-dot"></span></div>`

      const marker = new AMap.Marker({
        position: [checkin.longitude, checkin.latitude],
        offset: new AMap.Pixel(-18, -18),
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
    map.setFitView(markers, false, [100, 100, 180, 100])
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
})

watch(() => userStore.isLoggedIn, async (loggedIn) => {
  if (loggedIn) {
    await fetchCheckins()
    await initMap()
  }
})

// Re-render markers once both map and checkins are ready
watch([isMapReady, checkins], ([ready]) => {
  if (ready) renderMarkers()
})

onBeforeUnmount(() => {
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
  bottom: calc(100px + env(safe-area-inset-bottom));
  z-index: 20;
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
  left: 16px;
  right: 16px;
  bottom: calc(90px + env(safe-area-inset-bottom));
  z-index: 30;
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

:deep(.fp-pin-plain) {
  position: relative;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

:deep(.fp-pin-plain::before) {
  content: '';
  width: 24px;
  height: 24px;
  border-radius: 50% 50% 50% 6px;
  transform: rotate(-45deg);
  background: var(--brand-gradient);
  box-shadow: 0 6px 16px rgba(232, 93, 4, 0.35);
  display: block;
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
    left: 12px;
    right: 12px;
    bottom: calc(80px + env(safe-area-inset-bottom));
  }

  .stat-val { font-size: 20px; }
}

/* ── Report button ── */
.btn-report {
  margin-top: 12px;
  width: 100%;
  padding: 9px 14px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--brand-gradient);
  color: var(--ink-900);
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font-body);
  cursor: pointer;
  letter-spacing: 0.01em;
  transition: filter var(--fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.22);
}
.btn-report:hover { filter: brightness(0.93); }
.btn-report:active { filter: brightness(0.88); }

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
</style>
