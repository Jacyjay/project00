<template>
  <div class="hot-cities-panel">
    <div class="panel-header">
      <div class="panel-heading">
        <span class="panel-icon">🔥</span>
        <span class="panel-title">热门城市</span>
      </div>
      <button v-if="closable" type="button" class="panel-close" @click="emit('close')">收起</button>
    </div>

    <div class="tabs">
      <div class="tabs-track">
        <div class="tabs-indicator" :style="tabIndicatorStyle"></div>
        <button
          v-for="(tab, i) in tabs"
          :key="tab.key"
          :ref="el => setTabRef(el, i)"
          :class="['tab-btn', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >{{ tab.label }}</button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="loading-spinner" style="width:20px;height:20px;border-width:2px"></div>
      <span>加载中...</span>
    </div>

    <div v-else-if="currentList.length === 0" class="empty-state">
      {{ activeTab === 'today' ? '今日暂无打卡数据' : '暂无数据' }}
    </div>

    <template v-else>
    <TransitionGroup name="city-list" tag="ul" class="city-list">
      <li
        v-for="(item, index) in currentList"
        :key="item.city"
        class="city-item"
        :style="{ '--idx': index }"
        @click="goToCity(item.city)"
      >
        <span :class="['rank', index < 3 ? `rank-${index+1}` : '']">
          <template v-if="index < 3">
            {{ ['🥇','🥈','🥉'][index] }}
          </template>
          <template v-else>{{ index + 1 }}</template>
        </span>
        <span class="city-name">{{ item.city }}</span>
        <div class="city-bar-wrap">
          <div class="city-bar" :style="{ width: barWidth(item.count) }"></div>
        </div>
        <span class="city-count">{{ item.count }}</span>
      </li>
    </TransitionGroup>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getHotCities } from '../api/checkins.js'

defineProps({
  closable: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close'])
const router = useRouter()
const loading = ref(true)
const todayCities = ref([])
const historicalCities = ref([])
const activeTab = ref('today')

const tabs = [
  { key: 'today', label: '今日热门' },
  { key: 'historical', label: '历史热门' }
]

const currentList = computed(() =>
  activeTab.value === 'today' ? todayCities.value : historicalCities.value
)

const maxCount = computed(() => {
  const list = currentList.value
  if (!list.length) return 1
  return Math.max(...list.map(i => i.count), 1)
})

function barWidth(count) {
  return `${Math.max(8, (count / maxCount.value) * 100)}%`
}

// Tab indicator
const _tabEls = {}
function setTabRef(el, i) { _tabEls[i] = el }

const tabIndicatorStyle = ref({})

function updateIndicator() {
  const idx = tabs.findIndex(t => t.key === activeTab.value)
  const el = _tabEls[idx]
  if (!el) return
  tabIndicatorStyle.value = {
    transform: `translateX(${el.offsetLeft}px)`,
    width: `${el.offsetWidth}px`,
  }
}

watch(activeTab, async () => {
  await nextTick()
  updateIndicator()
})

onMounted(async () => {
  try {
    const res = await getHotCities()
    todayCities.value = res.data.today || []
    historicalCities.value = res.data.historical || []
    if (todayCities.value.length === 0) activeTab.value = 'historical'
  } catch (e) {
    console.error('获取热门城市失败', e)
  } finally {
    loading.value = false
  }
  await nextTick()
  updateIndicator()
})

function goToCity(city) {
  router.push({ name: 'CityDetail', params: { city } })
}
</script>

<style scoped>
.hot-cities-panel {
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-card);
  min-width: 0;
  width: 100%;
  max-width: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}

.panel-heading {
  display: flex;
  align-items: center;
  gap: 6px;
}

.panel-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.02em;
}

.panel-close {
  border: none;
  background: var(--brand-light);
  color: var(--brand);
  border-radius: var(--radius-full);
  padding: 5px 12px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.panel-close:hover {
  filter: brightness(0.95);
}

/* ── Tabs with sliding indicator ── */
.tabs {
  margin-bottom: 12px;
}

.tabs-track {
  position: relative;
  display: flex;
  gap: 6px;
  background: var(--bg-muted);
  border-radius: var(--radius-sm);
  padding: 3px;
}

.tabs-indicator {
  position: absolute;
  top: 3px;
  bottom: 3px;
  left: 0;
  width: 0;
  border-radius: 8px;
  background: var(--brand-gradient);
  box-shadow: 0 4px 12px rgba(232, 93, 4, 0.20);
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1), width 0.3s cubic-bezier(0.22, 1, 0.36, 1);
  pointer-events: none;
  z-index: 0;
}

.tab-btn {
  flex: 1;
  min-height: 34px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  font-size: 12px;
  color: var(--ink-500);
  font-weight: 600;
  transition: color 0.2s ease;
  position: relative;
  z-index: 1;
  font-family: inherit;
}

.tab-btn.active {
  color: #ffffff;
}

/* ── City intro block ── */
.city-intro-block {
  margin-bottom: 12px;
  padding: 10px 12px;
  background: rgba(232, 93, 4, 0.04);
  border-left: 3px solid rgba(232, 93, 4, 0.30);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.city-intro-text {
  margin: 0 0 6px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--ink-700);
}

.ai-badge {
  display: inline-block;
  font-size: 10px;
  color: var(--ink-300);
  font-weight: 500;
}

.intro-fade-enter-active { transition: opacity 0.4s ease, transform 0.4s ease; }
.intro-fade-leave-active { transition: opacity 0.2s ease; }
.intro-fade-enter-from   { opacity: 0; transform: translateY(-4px); }
.intro-fade-leave-to     { opacity: 0; }

/* ── City list ── */
.city-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.city-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 8px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: background 0.15s ease, transform 0.15s ease;
  animation: fadeInUp 0.3s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(var(--idx) * 0.04s);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.city-item:hover {
  background: var(--bg-muted);
  transform: translateX(2px);
}

.rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--ink-300);
  flex-shrink: 0;
}

.rank-1, .rank-2, .rank-3 { font-size: 16px; }

.city-name {
  flex-shrink: 0;
  min-width: 48px;
  font-size: 13px;
  color: var(--ink-900);
  font-weight: 600;
}

.city-bar-wrap {
  flex: 1;
  height: 4px;
  background: var(--ink-100);
  border-radius: 4px;
  overflow: hidden;
  min-width: 40px;
}

.city-bar {
  height: 100%;
  border-radius: 4px;
  background: var(--brand-gradient);
  transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.city-count {
  font-size: 11px;
  font-weight: 700;
  color: var(--ink-300);
  min-width: 20px;
  text-align: right;
}

/* ── States ── */
.loading-state, .empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  color: var(--ink-300);
  font-size: 13px;
  padding: 20px 0;
}

/* ── Transitions ── */
.city-list-enter-active { transition: all 0.3s ease; }
.city-list-leave-active { transition: all 0.2s ease; }
.city-list-enter-from { opacity: 0; transform: translateY(8px); }
.city-list-leave-to { opacity: 0; transform: translateX(-10px); }
.city-list-move { transition: transform 0.3s ease; }

/* ── Responsive ── */
@media (max-width: 768px) {
  .hot-cities-panel {
    border-radius: var(--radius-md);
    padding: 12px;
  }

  .panel-header { margin-bottom: 10px; }
  .city-item { padding: 8px 6px; }
}
</style>
