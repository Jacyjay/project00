<template>
  <div ref="scrollContainer" class="city-detail-page">
    <div class="page-container">
      <div class="page-header animate-fade-in-down">
        <button class="back-btn" @click="$router.back()">← 返回</button>
        <h1 class="city-title">📍 {{ city }}</h1>
        <p class="city-subtitle">{{ total }} 条公开打卡</p>
      </div>

      <!-- AI city intro -->
      <transition name="intro-fade">
        <div v-if="cityIntro" class="city-intro-card animate-fade-in">
          <p class="city-intro-text">{{ cityIntro }}</p>
          <span class="ai-credit">✨ 由豆包AI生成</span>
        </div>
      </transition>

      <!-- Sort controls -->
      <div class="sort-bar animate-fade-in">
        <span class="sort-label">排序：</span>
        <button
          v-for="s in sortOptions"
          :key="s.value"
          :class="['sort-btn', { active: sort === s.value }]"
          @click="changeSort(s.value)"
        >{{ s.label }}</button>
      </div>

      <!-- Checkin list -->
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="checkins.length === 0" class="empty">
        <p>这座城市还没有公开打卡</p>
        <router-link to="/checkins/new" class="cta-btn">成为第一个打卡的人</router-link>
      </div>
      <div v-else class="checkins-list">
        <CheckinCard
          v-for="(c, idx) in checkins"
          :key="c.id"
          :checkin="c"
          :style="{ animationDelay: `${idx * 0.05}s`, animationFillMode: 'both' }"
          class="animate-fade-in-up"
        />

        <!-- Pagination -->
        <div class="pagination" v-if="total > pageSize">
          <button :disabled="page === 1" @click="changePage(page-1)" class="page-btn">上一页</button>
          <span class="page-info">{{ page }} / {{ totalPages }}</span>
          <button :disabled="page >= totalPages" @click="changePage(page+1)" class="page-btn">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import CheckinCard from '../components/CheckinCard.vue'
import { getCityCheckins, getCityIntro } from '../api/checkins.js'
import { normalizeCityName } from '../lib/region'

const route = useRoute()
const city = computed(() => normalizeCityName(String(route.params.city || '')))

const scrollContainer = ref(null)
const checkins = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const sort = ref('latest')
const loading = ref(true)
const cityIntro = ref(null)

const totalPages = computed(() => Math.ceil(total.value / pageSize))

const sortOptions = [
  { value: 'latest', label: '最新' },
  { value: 'likes', label: '最多点赞' },
  { value: 'comments', label: '最多评论' }
]

async function fetchCheckins() {
  loading.value = true
  try {
    const res = await getCityCheckins(city.value, { sort: sort.value, page: page.value, page_size: pageSize })
    checkins.value = res.data.checkins || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('获取城市打卡失败', e)
  } finally {
    loading.value = false
  }
}

function scrollToTop() {
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = 0
    return
  }
  window.scrollTo(0, 0)
}

function changeSort(newSort) {
  sort.value = newSort
  page.value = 1
  scrollToTop()
  fetchCheckins()
}

function changePage(newPage) {
  page.value = newPage
  scrollToTop()
  fetchCheckins()
}

async function fetchCityIntro() {
  cityIntro.value = null
  if (!city.value) return
  try {
    const res = await getCityIntro(city.value)
    cityIntro.value = res.data.intro || null
  } catch {
    // intro is optional, silently ignore errors
  }
}

onMounted(() => {
  fetchCheckins()
  fetchCityIntro()
})

watch(() => route.params.city, () => {
  page.value = 1
  scrollToTop()
  fetchCheckins()
  fetchCityIntro()
})
</script>

<style scoped>
.city-detail-page {
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  background: #f8f8f8;
  padding: 20px 16px calc(120px + env(safe-area-inset-bottom));
}

.page-container {
  max-width: 680px;
  margin: 0 auto;
}
.page-header { margin-bottom: 20px; }
.back-btn {
  background: none; border: none; cursor: pointer;
  color: #666; font-size: 14px; padding: 0; margin-bottom: 8px;
}
.back-btn:hover { color: var(--brand); }
.city-title { font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 0 0 4px; }
.city-subtitle { font-size: 13px; color: #999; margin: 0; }

.city-intro-card {
  margin-bottom: 16px;
  padding: 14px 16px;
  background: white;
  border-radius: 12px;
  border-left: 3px solid var(--brand);
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.city-intro-text {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  margin: 0 0 8px;
}
.ai-credit {
  font-size: 11px;
  color: #bbb;
}
.intro-fade-enter-active { transition: opacity 0.4s ease, transform 0.3s ease; }
.intro-fade-leave-active { transition: opacity 0.2s ease; }
.intro-fade-enter-from   { opacity: 0; transform: translateY(-6px); }
.intro-fade-leave-to     { opacity: 0; }
.sort-bar {
  display: flex; align-items: center; gap: 8px;
  margin-bottom: 16px; padding: 12px 16px;
  background: white; border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.sort-label { font-size: 13px; color: #666; }
.sort-btn {
  padding: 5px 12px;
  border: 1px solid #e0e0e0; border-radius: 16px;
  background: white; cursor: pointer;
  font-size: 12px; color: #666;
  transition: all 0.2s;
}
.sort-btn.active { background: var(--brand); border-color: var(--brand); color: white; }
.loading { text-align: center; padding: 60px; color: #999; }
.empty { text-align: center; padding: 60px; }
.empty p { color: #999; margin-bottom: 16px; }
.cta-btn {
  display: inline-block; padding: 10px 24px;
  background: #ff6b35; color: white;
  border-radius: 20px; text-decoration: none;
  font-size: 14px;
}
.pagination {
  display: flex; align-items: center; justify-content: center;
  gap: 16px; margin-top: 20px; padding: 16px;
}
.page-btn {
  padding: 8px 16px;
  border: 1px solid #e0e0e0; border-radius: 6px;
  background: white; cursor: pointer; font-size: 13px;
}
.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.page-info { font-size: 13px; color: #666; }

@media (max-width: 768px) {
  .city-detail-page {
    padding: 16px 12px calc(128px + env(safe-area-inset-bottom));
  }

  .page-header {
    margin-bottom: 16px;
  }

  .city-title {
    font-size: 22px;
  }

  .sort-bar {
    flex-wrap: wrap;
    gap: 8px 6px;
    padding: 10px 12px;
    border-radius: 16px;
  }

  .loading,
  .empty {
    padding: 48px 16px;
  }
}
</style>
