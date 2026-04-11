<template>
  <div class="app-header-shell">
    <!-- Top header -->
    <header class="app-header">
      <div class="header-inner">
        <div class="header-left">
          <router-link to="/" class="logo" id="logo-link">
            <div class="logo-mark-wrap">
              <div class="logo-mark">
                <LogoIcon :size="26" />
              </div>
              <div class="logo-glow"></div>
            </div>
            <span class="logo-text">拾光坐标</span>
          </router-link>
        </div>

        <div class="header-right">
          <!-- Map display mode toggle (only on map pages) -->
          <button
            v-if="showMapToggle"
            type="button"
            class="map-toggle-btn"
            @click="mapStore.toggleMapDetailMode()"
            :title="mapStore.mapDetailMode ? '切换到显示坐标' : '切换到显示详情'"
          >
            <span class="btn-icon">{{ mapStore.mapDetailMode ? '📌' : '🖼️' }}</span>
            <span class="btn-label">{{ mapStore.mapDetailMode ? '显示坐标' : '显示详情' }}</span>
          </button>

          <!-- Unified search -->
          <div class="search-wrap" ref="searchWrapRef">
            <button class="search-trigger" @click="openSearch" title="搜索">🔍</button>
            <transition name="search-drop">
              <div v-if="searchOpen" class="search-dropdown glass-card">
                <input
                  ref="searchInputRef"
                  v-model="searchQuery"
                  class="search-input"
                  placeholder="输入关键词后可搜用户或搜地点..."
                  @keydown.escape="closeSearch"
                  @keydown.enter.prevent="handleSearchUser"
                />
                <div class="search-actions">
                  <button
                    type="button"
                    class="search-action-btn"
                    :disabled="searchLoading || !searchQuery.trim()"
                    @click="handleSearchUser"
                  >
                    {{ searchLoading && searchMode === 'user' ? '搜索中...' : '搜用户' }}
                  </button>
                  <button
                    type="button"
                    class="search-action-btn search-action-btn-place"
                    :disabled="!searchQuery.trim()"
                    @click="handleSearchPlace"
                  >
                    搜地点
                  </button>
                </div>
                <p v-if="searchMode === 'place' && placeSearchHint" class="search-hint">{{ placeSearchHint }}</p>
                <div v-if="searchResults.length" class="search-results">
                  <router-link
                    v-for="u in searchResults"
                    :key="u.id"
                    :to="`/profile/${u.id}`"
                    class="search-result-item"
                    @click="closeSearch"
                  >
                    <div class="search-avatar">{{ u.nickname?.charAt(0) }}</div>
                    <span class="search-name">{{ u.nickname }}</span>
                  </router-link>
                </div>
                <p
                  v-else-if="searchMode === 'user' && hasSearched && searchQuery.length > 0 && !searchLoading"
                  class="search-empty"
                >
                  未找到用户
                </p>
              </div>
            </transition>
          </div>

          <template v-if="userStore.isLoggedIn">
            <router-link
              :to="`/profile/${userStore.userId}`"
              class="user-avatar-link"
              id="nav-profile"
            >
              <div class="user-avatar">
                <span class="avatar-letter">{{ userStore.user?.nickname?.charAt(0)?.toUpperCase() || '?' }}</span>
                <div class="avatar-ring"></div>
              </div>
              <span class="user-name">{{ userStore.user?.nickname }}</span>
            </router-link>

            <button class="btn-logout" @click="handleLogout" id="btn-logout">退出</button>
          </template>
          <template v-else>
            <router-link to="/login" class="btn-ghost btn-sm" id="btn-login">登录</router-link>
            <router-link to="/register" class="btn-primary btn-sm" id="btn-register">注册</router-link>
          </template>
        </div>
      </div>
    </header>

    <!-- Spring-physics liquid glass bottom dock -->
    <div
      class="bottom-dock"
      ref="dockEl"
      style="touch-action: none;"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
    >
      <!-- Liquid glass capsule -->
      <div class="dock-capsule" ref="capsuleEl"></div>

      <!-- Ripple layer -->
      <div class="dock-ripple-layer" ref="rippleLayerEl"></div>

      <!-- Nav items -->
      <div
        v-for="(item, i) in bottomNavItems"
        :key="item.key"
        :ref="el => setItemRef(el, i)"
        class="dock-item"
        :class="{ active: activeDockKey === item.key }"
      >
        <span class="dock-icon-wrap">
          <span class="dock-icon">{{ item.icon }}</span>
          <span v-if="item.key === 'messages' && unreadCount" class="dock-badge">
            {{ unreadCount > 9 ? '9+' : unreadCount }}
          </span>
        </span>
        <span class="dock-label">{{ item.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { useMapStore } from '../stores/map'
import { searchUsers } from '../api/checkins'
import { getUnreadCount } from '../api/messages'
import LogoIcon from './LogoIcon.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const mapStore = useMapStore()
const unreadCount = ref(0)
let pollTimer = null

// 判断是否显示地图显示模式切换按钮
const showMapToggle = computed(() => {
  return route.name === 'home' || route.name === 'MyFootprint'
})

// ─── Unified search ───────────────────────────────────────────────────────────
const searchOpen = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searchLoading = ref(false)
const searchMode = ref('user')
const hasSearched = ref(false)
const placeSearchHint = ref('')
const searchInputRef = ref(null)
const searchWrapRef = ref(null)

function openSearch() {
  searchOpen.value = true
  nextTick(() => searchInputRef.value?.focus())
}

function closeSearch() {
  searchOpen.value = false
  searchQuery.value = ''
  searchResults.value = []
  searchMode.value = 'user'
  hasSearched.value = false
  placeSearchHint.value = ''
  searchLoading.value = false
}

async function handleSearchUser() {
  const query = searchQuery.value.trim()
  if (!query) return
  searchMode.value = 'user'
  hasSearched.value = true
  placeSearchHint.value = ''
  searchLoading.value = true
  try {
    const res = await searchUsers(query)
    searchResults.value = res.data || []
  } catch {
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

async function handleSearchPlace() {
  const query = searchQuery.value.trim()
  if (!query) return

  searchMode.value = 'place'
  hasSearched.value = false
  searchResults.value = []
  placeSearchHint.value = route.name === 'home'
    ? `正在地图广场搜索“${query}”`
    : `正在跳转地图广场搜索“${query}”`

  mapStore.requestPlaceSearch(query)

  if (route.name !== 'home') {
    await router.push({ name: 'home' })
  }

  closeSearch()
}

function handleClickOutside(e) {
  if (searchWrapRef.value && !searchWrapRef.value.contains(e.target)) closeSearch()
}

function handleLogout() {
  userStore.logout()
  router.push('/')
}

async function fetchUnread() {
  if (!userStore.isLoggedIn) return
  try {
    const res = await getUnreadCount()
    unreadCount.value = res.data.count || 0
  } catch {
    // silently fail
  }
}

const bottomNavItems = computed(() => [
  {
    key: 'messages',
    label: '私信',
    icon: '💬',
    to: userStore.isLoggedIn
      ? { name: 'messages' }
      : { name: 'login', query: { redirect: '/messages' } },
  },
  {
    key: 'home',
    label: '地图广场',
    icon: '🗺️',
    to: { name: 'home' },
  },
  {
    key: 'feed',
    label: '动态',
    icon: '✨',
    to: userStore.isLoggedIn
      ? { name: 'Feed' }
      : { name: 'login', query: { redirect: '/feed' } },
  },
  {
    key: 'footprint',
    label: '足迹',
    icon: '👣',
    to: userStore.isLoggedIn
      ? { name: 'MyFootprint' }
      : { name: 'login', query: { redirect: '/my-footprint' } },
  },
])

function isNavActive(key) {
  if (key === 'home') return route.name === 'home'
  if (key === 'messages') return route.name === 'messages' || route.name === 'chat'
  if (key === 'feed') return route.name === 'Feed'
  if (key === 'footprint') return route.name === 'MyFootprint'
  return false
}

// ─── Drag hover state ─────────────────────────────────────────────────────────
const dragHoverIdx = ref(-1)

const activeDockKey = computed(() => {
  if (dragHoverIdx.value !== -1) {
    return bottomNavItems.value[dragHoverIdx.value]?.key ?? null
  }
  return bottomNavItems.value.find(item => isNavActive(item.key))?.key ?? 'home'
})

function getActiveItemIdx() {
  return bottomNavItems.value.findIndex(item => isNavActive(item.key))
}

// ─── DOM refs ────────────────────────────────────────────────────────────────
const dockEl = ref(null)
const capsuleEl = ref(null)
const rippleLayerEl = ref(null)
const _itemEls = {}

function setItemRef(el, i) {
  _itemEls[i] = el
}

// ─── Spring state ─────────────────────────────────────────────────────────────
let sx = 0, sw = 0
let vx = 0, vw = 0
let tx = 0, tw = 0
let rafId = null

const STIFFNESS = 0.28
const DAMPING = 0.72

function measureItemIdx(idx) {
  const dock = dockEl.value
  const item = _itemEls[idx]
  if (!dock || !item) return null
  const dockRect = dock.getBoundingClientRect()
  const itemRect = item.getBoundingClientRect()
  return {
    x: itemRect.left - dockRect.left,
    w: itemRect.width,
  }
}

function applyCapsule(x, w, stretch = 0) {
  const el = capsuleEl.value
  if (!el) return
  const extra = Math.abs(stretch)
  const ox = stretch < 0 ? -extra : 0
  el.style.transform = `translateX(${x + ox}px)`
  el.style.width = `${w + extra}px`
}

function startSpring() {
  if (rafId) return
  rafId = requestAnimationFrame(springTick)
}

function springTick() {
  vx += (tx - sx) * STIFFNESS
  vx *= DAMPING
  sx += vx

  vw += (tw - sw) * STIFFNESS
  vw *= DAMPING
  sw += vw

  const stretch = _isDragging ? pointerVelX * 0.28 : 0
  applyCapsule(sx, sw, Math.max(-60, Math.min(60, stretch)))

  const settled =
    !_isDragging &&
    Math.abs(vx) < 0.08 && Math.abs(tx - sx) < 0.08 &&
    Math.abs(vw) < 0.08 && Math.abs(tw - sw) < 0.08

  if (!settled) {
    rafId = requestAnimationFrame(springTick)
  } else {
    sx = tx; sw = tw
    applyCapsule(sx, sw, 0)
    rafId = null
  }
}

function springTo(idx, animate = true) {
  const m = measureItemIdx(idx)
  if (!m) return
  tx = m.x
  tw = m.w
  if (!animate) {
    sx = tx; sw = tw
    vx = 0; vw = 0
    applyCapsule(sx, sw, 0)
  }
  startSpring()
}

// ─── Pointer / drag ───────────────────────────────────────────────────────────
let _isDragging = false
let _dragStartX = 0
let _dragStartSX = 0
let _dragStartTime = 0
let pointerVelX = 0
let _lastPX = 0
let _lastPT = 0

function getItemBoundsRelative() {
  const dock = dockEl.value
  if (!dock) return []
  const dr = dock.getBoundingClientRect()
  return Object.keys(_itemEls).map(i => {
    const el = _itemEls[i]
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { i: Number(i), x: r.left - dr.left, w: r.width, cx: r.left + r.width / 2 - dr.left }
  }).filter(Boolean)
}

function rubberBand(x, lo, hi) {
  if (x >= lo && x <= hi) return x
  return x < lo
    ? lo + (x - lo) * 0.2
    : hi + (x - hi) * 0.2
}

function onPointerDown(e) {
  if (e.button !== 0 && e.pointerType === 'mouse') return
  dockEl.value?.setPointerCapture(e.pointerId)
  _isDragging = true
  _dragStartX = e.clientX
  _dragStartSX = sx
  _dragStartTime = Date.now()
  _lastPX = e.clientX
  _lastPT = Date.now()
  pointerVelX = 0
  startSpring()
}

function onPointerMove(e) {
  if (!_isDragging) return
  const now = Date.now()
  const dt = now - _lastPT
  if (dt > 0) {
    const raw = (e.clientX - _lastPX) / dt * 16
    pointerVelX = pointerVelX * 0.65 + raw * 0.35
  }
  _lastPX = e.clientX
  _lastPT = now

  const dx = e.clientX - _dragStartX
  const bounds = getItemBoundsRelative()
  if (!bounds.length) return

  const lo = bounds[0].x
  const hi = bounds[bounds.length - 1].x + bounds[bounds.length - 1].w - sw
  tx = rubberBand(_dragStartSX + dx, lo, hi)

  const cc = tx + sw / 2
  let closest = 0, minD = Infinity
  bounds.forEach(b => {
    const d = Math.abs(b.cx - cc)
    if (d < minD) { minD = d; closest = b.i }
  })
  dragHoverIdx.value = closest
}

function onPointerUp(e) {
  if (!_isDragging) return
  _isDragging = false
  const dx = Math.abs(e.clientX - _dragStartX)
  const dt = Date.now() - _dragStartTime

  vx += pointerVelX * 0.35

  if (dx < 8 && dt < 300) {
    const dock = dockEl.value
    if (dock) {
      const dr = dock.getBoundingClientRect()
      const clickX = e.clientX - dr.left
      const bounds = getItemBoundsRelative()
      const hit = bounds.find(b => clickX >= b.x && clickX <= b.x + b.w)
      if (hit) {
        spawnRipple(e.clientX, e.clientY)
        router.push(bottomNavItems.value[hit.i].to)
      }
    }
  } else {
    const idx = dragHoverIdx.value
    if (idx !== -1) router.push(bottomNavItems.value[idx].to)
  }

  dragHoverIdx.value = -1

  nextTick(() => {
    const ai = getActiveItemIdx()
    if (ai !== -1) springTo(ai, true)
  })
}

function onPointerCancel() {
  _isDragging = false
  pointerVelX = 0
  dragHoverIdx.value = -1
  const ai = getActiveItemIdx()
  if (ai !== -1) springTo(ai, true)
}

// ─── Ripple ───────────────────────────────────────────────────────────────────
function spawnRipple(cx, cy) {
  const dock = dockEl.value
  const layer = rippleLayerEl.value
  if (!dock || !layer) return
  const dr = dock.getBoundingClientRect()
  const r = document.createElement('div')
  r.className = 'dock-ripple'
  r.style.left = `${cx - dr.left}px`
  r.style.top  = `${cy - dr.top}px`
  layer.appendChild(r)
  setTimeout(() => r.remove(), 700)
}

// ─── Route watch → spring ─────────────────────────────────────────────────────
watch(() => route.name, async () => {
  await nextTick()
  const ai = getActiveItemIdx()
  if (ai !== -1) springTo(ai, true)
})

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  await nextTick()
  const ai = getActiveItemIdx()
  if (ai !== -1) springTo(ai, false)
  if (userStore.isLoggedIn) {
    await fetchUnread()
    pollTimer = setInterval(fetchUnread, 30_000)
  }
  document.addEventListener('click', handleClickOutside)
})

watch(() => userStore.isLoggedIn, async (loggedIn) => {
  if (loggedIn) {
    await fetchUnread()
    if (!pollTimer) pollTimer = setInterval(fetchUnread, 30_000)
  } else {
    clearInterval(pollTimer); pollTimer = null
    unreadCount.value = 0
  }
})

onUnmounted(() => {
  clearInterval(pollTimer)
  if (rafId) { cancelAnimationFrame(rafId); rafId = null }
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* ─── Shell ── */
.app-header-shell {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1100;
  background: #ffffff;
  box-shadow: 0 1px 0 rgba(120, 82, 52, 0.08);
}

/* ─── Top header ── */
.app-header {
  position: relative;
  z-index: 1100;
  background: #ffffff;
  box-shadow: none;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 64px;
  max-width: 100%;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text-primary);
}

.logo-mark-wrap {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.logo-glow { display: none; }

.logo-text {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--ink-900);
  -webkit-text-fill-color: unset;
  background: none;
}

/* Header right */
.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Map toggle button */
.map-toggle-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--ink-100);
  background: var(--bg-muted);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 13px;
  transition: all var(--fast);
  white-space: nowrap;
}

.map-toggle-btn:hover {
  background: var(--bg-hover);
  border-color: var(--ink-200);
}

.map-toggle-btn:active {
  transform: scale(0.96);
}

.map-toggle-btn .btn-icon {
  font-size: 15px;
  line-height: 1;
}

.map-toggle-btn .btn-label {
  font-size: 13px;
  color: var(--ink-600);
}

@media (max-width: 768px) {
  .map-toggle-btn .btn-label {
    display: none;
  }
  .map-toggle-btn {
    padding: 6px 10px;
  }
}

/* ─── Search ── */
.search-wrap {
  position: relative;
}

.search-trigger {
  width: 34px;
  height: 34px;
  border: 1px solid var(--ink-100);
  background: var(--bg-muted);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--fast);
}

.search-trigger:hover { background: var(--bg-hover); }

.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 260px;
  padding: 10px;
  border-radius: var(--radius-md);
  z-index: 1500;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.search-actions {
  display: flex;
  gap: 8px;
}

.search-action-btn {
  flex: 1;
  height: 34px;
  border: 1px solid var(--ink-100);
  background: var(--bg-muted);
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 13px;
  color: var(--ink-700);
  transition: all var(--fast);
}

.search-action-btn:hover:not(:disabled) {
  background: var(--bg-hover);
  border-color: var(--ink-200);
}

.search-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.search-action-btn-place {
  color: var(--brand-strong);
}

.search-hint {
  margin: 0;
  font-size: 12px;
  color: var(--ink-400);
  line-height: 1.5;
}

.search-input {
  width: 100%;
  padding: 8px 12px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  outline: none;
  background: var(--bg-muted);
  color: var(--ink-900);
  box-sizing: border-box;
  transition: border-color var(--fast);
}

.search-input:focus {
  border-color: var(--brand);
  background: var(--bg-surface);
}

.search-results {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: var(--radius-sm);
  text-decoration: none;
  color: var(--ink-900);
  transition: background var(--fast);
}

.search-result-item:hover { background: var(--bg-muted); }

.search-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--brand-gradient);
  color: white;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.search-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-700);
}

.search-empty {
  font-size: 12px;
  color: var(--ink-300);
  text-align: center;
  padding: 8px 0;
  margin: 0;
}

.search-drop-enter-active, .search-drop-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.search-drop-enter-from, .search-drop-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.btn-sm {
  padding: 8px 18px;
  font-size: 13px;
  border-radius: var(--radius-full);
  font-weight: 600;
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 18px;
  background: transparent;
  color: var(--ink-500);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-full);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--fast);
  font-family: inherit;
}

.btn-ghost:hover {
  background: var(--bg-muted);
  color: var(--ink-900);
}

/* User avatar */
.user-avatar-link {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--ink-900);
  padding: 3px 10px 3px 3px;
  border-radius: var(--radius-full);
  border: 1px solid transparent;
  transition: background var(--fast), border-color var(--fast);
}

.user-avatar-link:hover {
  background: var(--bg-muted);
  border-color: var(--ink-100);
}

.user-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.20);
}

.avatar-letter {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink-900);
}

.avatar-ring { display: none; }

.user-name {
  font-size: 13px;
  font-weight: 600;
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--ink-700);
}

/* ─── Logout button ── */
.btn-logout {
  padding: 7px 16px;
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  border: 1px solid var(--ink-100);
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--fast), color var(--fast);
}

.btn-logout:hover {
  background: var(--bg-hover);
  color: var(--ink-900);
}

.btn-logout:active { transform: scale(0.96); }

/* ─── Bottom dock ── */
.bottom-dock {
  position: fixed;
  left: 50%;
  bottom: calc(18px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 1200;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 16px;
  background: rgba(253, 246, 240, 0.82);
  backdrop-filter: blur(20px) saturate(160%);
  -webkit-backdrop-filter: blur(20px) saturate(160%);
  border-radius: var(--radius-full);
  border: 1px solid rgba(232, 161, 0, 0.12);
  box-shadow: 0 4px 24px rgba(28, 16, 7, 0.12), 0 1px 0 rgba(255,255,255,0.6) inset;
  overflow: hidden;
}

.bottom-dock::after { display: none; }

/* ─── Spring capsule ── */
.dock-capsule {
  position: absolute;
  top: 5px;
  bottom: 5px;
  left: 0;
  height: auto;
  width: 96px;
  border-radius: var(--radius-full);
  pointer-events: none;
  z-index: 0;
  will-change: transform, width;
  transform: translateX(0);
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.18);
  box-shadow: none;
}

/* ─── Ripple layer ── */
.dock-ripple-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 3;
  border-radius: var(--radius-full);
  overflow: hidden;
}

:deep(.dock-ripple) {
  position: absolute;
  transform: translate(-50%, -50%) scale(0);
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(232, 93, 4, 0.12);
  animation: rippleOut 0.55s ease-out forwards;
  pointer-events: none;
}

@keyframes rippleOut {
  to { transform: translate(-50%, -50%) scale(4); opacity: 0; }
}

/* ─── Nav items ── */
.dock-item {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 28px;
  border-radius: var(--radius-full);
  cursor: pointer;
  user-select: none;
  -webkit-user-select: none;
  color: var(--ink-300);
  transition: color var(--normal) var(--ease-out);
  white-space: nowrap;
  min-width: 52px;
  justify-content: center;
}

.dock-item.active { color: var(--brand); }

.dock-icon-wrap {
  position: relative;
  display: inline-flex;
  flex-shrink: 0;
}

.dock-icon {
  font-size: 20px;
  line-height: 1;
  transition: transform var(--normal) var(--ease-spring);
}

.dock-item.active .dock-icon { transform: scale(1.08); }

.dock-label {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1;
}

/* ─── Unread badge ── */
.dock-badge {
  position: absolute;
  top: -7px;
  right: -10px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: var(--radius-full);
  background: var(--error);
  color: white;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--bg-surface);
  line-height: 1;
}

/* ─── Mobile ── */
@media (max-width: 768px) {
  .header-inner {
    padding: 0 14px;
    height: 56px;
  }
  .user-name { display: none; }

  .bottom-dock {
    bottom: calc(14px + env(safe-area-inset-bottom));
    padding: 5px 8px;
  }

  .dock-item {
    padding: 8px 20px;
    min-width: 0;
  }

  .dock-label { font-size: 10px; }
}
</style>
