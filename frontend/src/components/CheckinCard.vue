<template>
  <router-link :to="{ name: 'checkin-detail', params: { id: checkin.id } }" class="checkin-card-link">
  <div class="checkin-card">
    <!-- Photo -->
    <div class="card-photo-wrap" v-if="checkin.first_photo">
      <img :src="photoUrl(checkin.first_photo)" class="card-photo" loading="lazy" />
      <div class="card-photo-gradient"></div>
      <div class="card-photo-meta" v-if="checkin.location_name">
        <span class="location-chip">📍 {{ checkin.location_name }}</span>
      </div>
    </div>

    <!-- Card body -->
    <div class="card-body">
      <!-- User info -->
      <div class="card-header">
        <div class="user-info">
          <div class="avatar" :style="avatarStyle">
            <span class="avatar-letter">{{ checkin.user_nickname?.charAt(0)?.toUpperCase() || '?' }}</span>
          </div>
          <div class="user-meta">
            <div class="username">{{ checkin.user_nickname }}</div>
            <div class="meta">{{ displayCity }} · {{ formatDate(checkin.created_at) }}</div>
          </div>
        </div>
      </div>

      <!-- Location tag (no-photo fallback) -->
      <div class="location-tag-inline" v-if="checkin.location_name && !checkin.first_photo">
        <span class="location-dot"></span>{{ checkin.location_name }}
      </div>

      <!-- Content -->
      <p class="card-content" v-if="checkin.content">{{ checkin.content }}</p>

      <!-- Actions -->
      <div class="card-actions" @click.prevent>
        <button :class="['action-btn', { liked: isLiked }]" @click.prevent="toggleLike">
          <span class="action-icon">{{ isLiked ? '❤️' : '🤍' }}</span>
          <span class="action-count">{{ likesCount }}</span>
        </button>
        <button class="action-btn" @click.prevent="toggleComments">
          <span class="action-icon">💬</span>
          <span class="action-count">{{ commentsCount }}</span>
        </button>
      </div>

      <!-- Comments section -->
      <div class="comments-section" v-if="showComments" @click.prevent>
        <div v-if="loadingComments" class="comment-loading">加载中...</div>
        <div v-else>
          <div v-for="c in comments" :key="c.id" class="comment-item">
            <span class="comment-author">{{ c.user_nickname }}：</span>
            <span class="comment-text">{{ c.content }}</span>
          </div>
          <div v-if="comments.length === 0" class="no-comments">暂无评论，来发表第一条吧</div>
        </div>

        <div class="comment-input" v-if="userStore.isLoggedIn">
          <input
            v-model="newComment"
            placeholder="说点什么..."
            maxlength="500"
            @keyup.enter="submitComment"
            class="comment-field"
            @click.stop
          />
          <button class="submit-btn" @click.prevent="submitComment" :disabled="!newComment.trim()">发送</button>
        </div>
        <div v-else class="login-hint">
          <router-link to="/login">登录后</router-link>才能评论
        </div>
      </div>
    </div>
  </div>
  </router-link>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../stores/user.js'
import { likeCheckin, unlikeCheckin, getComments, addComment } from '../api/checkins.js'
import { getImageUrl } from '../lib/checkins'
import { normalizeCityName } from '../lib/region'

const props = defineProps({
  checkin: { type: Object, required: true }
})

const userStore = useUserStore()
const isLiked = ref(props.checkin.is_liked || false)
const likesCount = ref(props.checkin.likes_count || 0)
const commentsCount = ref(props.checkin.comments_count || 0)
const showComments = ref(false)
const comments = ref([])
const loadingComments = ref(false)
const newComment = ref('')

const avatarStyle = computed(() => {
  const hue = (props.checkin.user_nickname?.charCodeAt(0) || 0) * 37 % 360
  return {
    background: `linear-gradient(135deg, hsl(${hue}, 65%, 52%), hsl(${(hue + 40) % 360}, 70%, 42%))`
  }
})

const displayCity = computed(() => normalizeCityName(props.checkin.city || ''))

function photoUrl(url) {
  return getImageUrl(url)
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

async function toggleLike() {
  if (!userStore.isLoggedIn) {
    ElMessage({ message: '请先登录后再点赞', type: 'warning', duration: 2000 })
    return
  }
  try {
    if (isLiked.value) {
      await unlikeCheckin(props.checkin.id)
      isLiked.value = false
      likesCount.value = Math.max(0, likesCount.value - 1)
    } else {
      await likeCheckin(props.checkin.id)
      isLiked.value = true
      likesCount.value += 1
    }
  } catch (e) {
    console.error('点赞操作失败', e)
  }
}

async function toggleComments() {
  showComments.value = !showComments.value
  if (showComments.value && comments.value.length === 0) {
    loadingComments.value = true
    try {
      const res = await getComments(props.checkin.id)
      comments.value = res.data.comments || []
    } catch (e) {
      console.error('获取评论失败', e)
    } finally {
      loadingComments.value = false
    }
  }
}

async function submitComment() {
  const text = newComment.value.trim()
  if (!text) return
  try {
    const res = await addComment(props.checkin.id, text)
    comments.value.push(res.data)
    commentsCount.value += 1
    newComment.value = ''
  } catch (e) {
    console.error('评论失败', e)
    ElMessage({ message: '评论失败，请重试', type: 'error', duration: 2000 })
  }
}
</script>

<style scoped>
.checkin-card-link {
  display: block;
  text-decoration: none;
  color: inherit;
}

.checkin-card {
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  margin-bottom: 12px;
  overflow: hidden;
  box-shadow: var(--shadow-card);
  transition: transform 0.2s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.2s ease;
}

.checkin-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-float);
}

/* ── Photo ── */
.card-photo-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: 20px 20px 0 0;
}

.card-photo {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.4s ease;
}

.checkin-card:hover .card-photo {
  transform: scale(1.03);
}

.card-photo-gradient {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    to bottom,
    transparent 40%,
    rgba(15, 23, 42, 0.55) 100%
  );
  pointer-events: none;
}

.card-photo-meta {
  position: absolute;
  bottom: 10px;
  left: 12px;
  right: 12px;
}

.location-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 0.5px solid rgba(255, 255, 255, 0.35);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* ── Card body ── */
.card-body {
  padding: 14px 16px 12px;
}

.card-header {
  margin-bottom: 10px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(28, 16, 7, 0.15);
}

.avatar-letter {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
}

.user-meta { flex: 1; min-width: 0; }

.username {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
  font-family: var(--font-display);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.meta {
  font-size: 11px;
  color: var(--ink-300);
  margin-top: 1px;
}

/* ── Location tag (no-photo) ── */
.location-tag-inline {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 600;
  color: var(--brand);
  margin-bottom: 8px;
}

.location-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand-gradient);
  flex-shrink: 0;
}

/* ── Content ── */
.card-content {
  font-size: 13.5px;
  color: var(--ink-700);
  line-height: 1.7;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ── Actions ── */
.card-actions {
  display: flex;
  gap: 4px;
  padding-top: 10px;
  border-top: 1px solid var(--ink-100);
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 13px;
  color: var(--ink-500);
  font-weight: 600;
  font-family: inherit;
  transition: background 0.15s ease, color 0.15s ease;
}

.action-btn:hover {
  background: var(--brand-light);
  color: var(--brand);
}

.action-btn.liked .action-count {
  color: #EF4444;
}

.action-icon { font-size: 15px; line-height: 1; }
.action-count { font-size: 12px; font-weight: 700; }

/* ── Comments ── */
.comments-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--ink-100);
}

.comment-loading {
  font-size: 12px;
  color: var(--ink-300);
  padding: 4px 0;
}

.comment-item {
  padding: 5px 0;
  font-size: 12.5px;
  line-height: 1.6;
  border-bottom: 1px solid var(--ink-100);
}

.comment-author {
  font-weight: 700;
  color: var(--ink-900);
}

.comment-text { color: var(--ink-700); }

.no-comments {
  font-size: 12px;
  color: var(--ink-300);
  padding: 4px 0;
  font-style: italic;
}

.comment-input {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.comment-field {
  flex: 1;
  padding: 8px 12px;
  background: var(--bg-muted);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-sm);
  font-size: 13px;
  outline: none;
  font-family: inherit;
  color: var(--ink-900);
  transition: border-color 0.15s ease, background 0.15s ease;
}

.comment-field:focus {
  border-color: var(--brand);
  background: var(--bg-surface);
}

.comment-field::placeholder { color: var(--ink-300); }

.submit-btn {
  padding: 8px 16px;
  background: var(--brand-gradient);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  transition: opacity 0.15s ease, transform 0.15s ease;
  white-space: nowrap;
}

.submit-btn:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.login-hint {
  font-size: 12px;
  color: var(--ink-300);
  margin-top: 8px;
}

.login-hint a {
  color: var(--brand);
  font-weight: 600;
  text-decoration: none;
}
</style>
