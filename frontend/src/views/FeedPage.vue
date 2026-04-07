<template>
  <div class="feed-page">
    <div class="feed-container">
      <div class="feed-header">
        <h1 class="feed-title">动态</h1>
        <p class="feed-subtitle">关注的人的最新打卡</p>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="feed-loading">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <!-- Empty: not logged in -->
      <div v-else-if="!userStore.isLoggedIn" class="feed-empty glass-card">
        <span class="feed-empty-icon">👣</span>
        <p class="feed-empty-title">登录后查看动态</p>
        <p class="feed-empty-desc">关注感兴趣的拾光者，这里将显示他们的最新打卡</p>
        <router-link to="/login" class="btn-primary">去登录</router-link>
      </div>

      <!-- Empty: no following -->
      <div v-else-if="!loading && checkins.length === 0" class="feed-empty glass-card">
        <span class="feed-empty-icon">🔭</span>
        <p class="feed-empty-title">还没有动态</p>
        <p class="feed-empty-desc">去关注一些拾光者，这里就会出现他们的打卡故事</p>
        <router-link to="/" class="btn-primary">探索地图广场</router-link>
      </div>

      <!-- Feed list -->
      <div v-else class="feed-list">
        <div
          v-for="item in checkins"
          :key="item.id"
          class="feed-card glass-card animate-fade-in-up"
        >
          <!-- User info -->
          <div class="feed-card-header">
            <router-link :to="`/profile/${item.user_id}`" class="feed-user">
              <div class="feed-avatar">{{ item.user_nickname?.charAt(0) }}</div>
              <div class="feed-user-info">
                <span class="feed-username">{{ item.user_nickname }}</span>
                <span class="feed-time">{{ formatTime(item.created_at) }}</span>
              </div>
            </router-link>
            <div class="feed-location-tag">
              <span v-if="item.city" class="feed-city">📍 {{ normalizeCityName(item.city) }}</span>
            </div>
          </div>

          <!-- Photo -->
          <router-link v-if="item.preview_image_url" :to="`/checkins/${item.id}`" class="feed-photo-link">
            <div class="feed-photo-wrap">
              <img
                :src="getImageUrl(item.preview_image_url)"
                :alt="item.location_name"
                class="feed-photo"
                loading="lazy"
              />
              <div v-if="item.photo_count > 1" class="feed-photo-count">+{{ item.photo_count - 1 }}</div>
              <div v-if="item.media_type === 'video'" class="feed-video-badge">🎬</div>
            </div>
          </router-link>

          <!-- Content -->
          <div class="feed-card-body">
            <router-link :to="`/checkins/${item.id}`" class="feed-place-name">
              {{ item.location_name }}
            </router-link>
            <p v-if="item.content" class="feed-content">{{ truncate(item.content) }}</p>
          </div>

          <!-- Social bar -->
          <div class="feed-social">
            <button
              :class="['feed-like-btn', { liked: item.is_liked }]"
              @click="toggleLike(item)"
            >
              <span>{{ item.is_liked ? '❤️' : '🤍' }}</span>
              <span>{{ item.likes_count || 0 }}</span>
            </button>
            <router-link :to="`/checkins/${item.id}`" class="feed-comment-btn">
              <span>💬</span>
              <span>{{ item.comments_count || 0 }}</span>
            </router-link>
          </div>
        </div>

        <!-- Load more -->
        <div v-if="hasMore" class="feed-more">
          <button class="feed-more-btn" :disabled="loadingMore" @click="loadMore">
            {{ loadingMore ? '加载中...' : '加载更多' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getFeed } from '../api/follows'
import { likeCheckin, unlikeCheckin } from '../api/checkins'
import { getImageUrl } from '../lib/checkins'
import { normalizeCityName } from '../lib/region'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

const checkins = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const offset = ref(0)
const LIMIT = 20

function truncate(text) {
  if (!text) return ''
  return text.length > 100 ? text.slice(0, 99) + '…' : text
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}天前`
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

async function fetchFeed(reset = false) {
  if (!userStore.isLoggedIn) { loading.value = false; return }
  try {
    const res = await getFeed(LIMIT, reset ? 0 : offset.value)
    const data = res.data
    if (reset) {
      checkins.value = data.checkins
    } else {
      checkins.value.push(...data.checkins)
    }
    offset.value = (reset ? 0 : offset.value) + data.checkins.length
    hasMore.value = data.has_more
  } catch (e) {
    console.error('Feed load failed', e)
    ElMessage.error('加载动态失败')
  }
}

async function loadMore() {
  loadingMore.value = true
  try {
    await fetchFeed(false)
  } finally {
    loadingMore.value = false
  }
}

async function toggleLike(item) {
  if (!userStore.isLoggedIn) { ElMessage.info('请先登录'); return }
  try {
    if (item.is_liked) {
      const res = await unlikeCheckin(item.id)
      item.is_liked = false
      item.likes_count = res.data.likes_count
    } else {
      const res = await likeCheckin(item.id)
      item.is_liked = true
      item.likes_count = res.data.likes_count
    }
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(async () => {
  loading.value = true
  await fetchFeed(true)
  loading.value = false
})
</script>

<style scoped>
.feed-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px 16px;
  background: var(--bg-base);
}

.feed-container {
  max-width: 600px;
  margin: 0 auto;
}

.feed-header {
  margin-bottom: 20px;
}

.feed-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--ink-900);
  margin: 0 0 4px;
}

.feed-subtitle {
  font-size: 13px;
  color: var(--ink-300);
  margin: 0;
}

/* Loading */
.feed-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--ink-300);
  font-size: 14px;
}

/* Empty */
.feed-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 48px 24px;
  text-align: center;
}

.feed-empty-icon { font-size: 48px; }

.feed-empty-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--ink-700);
  margin: 0;
}

.feed-empty-desc {
  font-size: 13px;
  color: var(--ink-300);
  margin: 0;
  max-width: 260px;
  line-height: 1.5;
}

/* Feed list */
.feed-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feed-card {
  border-radius: 16px;
  overflow: hidden;
  padding: 0;
}

/* Card header */
.feed-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 10px;
}

.feed-user {
  display: flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
  color: inherit;
}

.feed-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.feed-user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.feed-username {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink-800);
}

.feed-time {
  font-size: 11px;
  color: var(--ink-300);
}

.feed-city {
  font-size: 11.5px;
  color: var(--ink-400);
}

/* Photo */
.feed-photo-link { display: block; }

.feed-photo-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 4 / 3;
  background: var(--bg-muted);
  overflow: hidden;
}

.feed-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.3s ease;
}
.feed-photo-link:hover .feed-photo { transform: scale(1.02); }

.feed-photo-count {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.55);
  color: white;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 7px;
  border-radius: 20px;
}

.feed-video-badge {
  position: absolute;
  bottom: 10px;
  right: 10px;
  font-size: 20px;
  filter: drop-shadow(0 1px 3px rgba(0,0,0,0.5));
}

/* Card body */
.feed-card-body {
  padding: 10px 14px 4px;
}

.feed-place-name {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
  text-decoration: none;
  margin-bottom: 4px;
}
.feed-place-name:hover { color: var(--brand); }

.feed-content {
  font-size: 13px;
  color: var(--ink-500);
  line-height: 1.55;
  margin: 0;
}

/* Social bar */
.feed-social {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px 12px;
}

.feed-like-btn, .feed-comment-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--ink-100);
  background: var(--bg-muted);
  font-size: 13px;
  color: var(--ink-500);
  cursor: pointer;
  font-family: inherit;
  text-decoration: none;
  transition: background var(--fast), color var(--fast);
}
.feed-like-btn:hover { background: var(--bg-hover); }
.feed-like-btn.liked { color: #e05; border-color: #fcc; background: #fff0f3; }

/* Load more */
.feed-more {
  display: flex;
  justify-content: center;
  padding: 8px 0 20px;
}

.feed-more-btn {
  padding: 10px 28px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--ink-100);
  background: var(--bg-surface);
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--fast);
}
.feed-more-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.feed-more-btn:not(:disabled):hover { background: var(--bg-muted); }

/* Loading spinner reuse */
.loading-spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
