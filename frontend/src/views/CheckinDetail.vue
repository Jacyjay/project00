<template>
  <div class="checkin-detail-page">
    <div class="detail-container animate-fade-in">
      <button class="back-btn" @click="$router.push('/')" id="btn-back">
        <span class="back-arrow">←</span>
        <span>返回地图</span>
      </button>

      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <template v-else-if="checkin">
        <!-- Hero header -->
        <div class="checkin-header glass-card animate-fade-in-up" style="animation-delay: 0s; animation-fill-mode: both;">
          <div class="header-main">
            <div class="title-row">
              <h1 class="checkin-name">{{ checkin.location_name }}</h1>
              <span class="badge-pill" :class="checkin.is_public ? 'badge-blue' : 'badge-amber'">
                <span class="badge-dot-status" :class="checkin.is_public ? 'dot-blue' : 'dot-amber'"></span>
                {{ checkin.is_public ? '公开' : '私密' }}
              </span>
            </div>
            <p v-if="displayCity || displayAddress" class="checkin-address">
              📍 {{ displayCity || displayAddress }}
            </p>
            <div class="checkin-meta">
              <router-link :to="`/profile/${checkin.user_id}`" class="meta-user">
                <div class="meta-avatar">{{ checkin.user_nickname?.charAt(0) }}</div>
                <span>{{ checkin.user_nickname }}</span>
              </router-link>
              <span class="meta-sep">·</span>
              <span>{{ formatCheckinDate(checkin) }}</span>
              <span v-if="checkin.content" class="meta-sep">·</span>
              <span v-if="checkin.content">{{ checkin.content.length }} 字</span>
            </div>
          </div>
          <div class="meta-coord-panel">
            <span class="coord-label">坐标</span>
            <strong class="coord-value">{{ formatCoordinates(checkin.latitude, checkin.longitude) }}</strong>
          </div>
        </div>

        <!-- City intro (always expanded, directly below header) -->
        <div v-if="displayCity" class="section-card glass-card animate-fade-in-up" style="animation-delay: 0.08s; animation-fill-mode: both;">
          <h2 class="section-title">
            <span class="section-icon">🏙️</span>
            {{ displayCity }} 城市印象
          </h2>
          <div class="city-intro-body">
            <p v-if="cityIntro" class="city-intro-text">{{ cityIntro }}</p>
            <p v-else class="city-intro-loading">
              {{ cityIntroLoading ? '正在生成城市印象...' : '暂无城市介绍' }}
            </p>
            <span v-if="cityIntro" class="ai-credit">✨ 由豆包AI生成</span>
          </div>
        </div>

        <!-- Content -->
        <div v-if="checkin.content" class="section-card glass-card animate-fade-in-up" style="animation-delay: 0.16s; animation-fill-mode: both;">
          <h2 class="section-title">
            <span class="section-icon">📝</span>
            打卡文案
          </h2>
          <p class="content-text">{{ checkin.content }}</p>
        </div>

        <!-- Video (video checkins) -->
        <div v-if="checkin.media_type === 'video'" class="section-card glass-card animate-fade-in-up" style="animation-delay: 0.24s; animation-fill-mode: both;">
          <h2 class="section-title">
            <span class="section-icon">🎬</span>
            视频
          </h2>
          <div v-if="checkin.video_url" class="video-player-wrap">
            <video
              :src="getImageUrl(checkin.video_url)"
              class="checkin-video"
              controls
              preload="metadata"
            ></video>
          </div>
          <div v-else class="empty-photos">
            <span class="empty-icon">🎬</span>
            <p>视频加载失败</p>
          </div>
        </div>

        <!-- Photos (photo checkins) -->
        <div v-else class="section-card glass-card animate-fade-in-up" style="animation-delay: 0.24s; animation-fill-mode: both;">
          <h2 class="section-title">
            <span class="section-icon">📸</span>
            照片
            <span class="photo-count">{{ checkin.photos.length }}</span>
          </h2>
          <div v-if="checkin.photos.length" class="photo-grid">
            <button
              v-for="(photo, idx) in checkin.photos"
              :key="photo.id"
              type="button"
              class="photo-item"
              :style="{ animationDelay: `${0.26 + idx * 0.06}s` }"
              @click="previewPhoto(photo.image_url)"
            >
              <img :src="getImageUrl(photo.image_url)" :alt="checkin.location_name" loading="lazy" />
              <div class="photo-overlay">
                <span class="photo-zoom-icon">🔍</span>
              </div>
            </button>
          </div>
          <div v-else class="empty-photos">
            <span class="empty-icon">🖼️</span>
            <p>这条打卡还没有上传照片</p>
          </div>
        </div>

        <!-- Owner actions -->
        <div v-if="isOwner" class="section-card glass-card owner-actions animate-fade-in-up" style="animation-delay: 0.28s; animation-fill-mode: both;">
          <button class="action-btn" @click="openEdit">✏️ 编辑文案</button>
          <button class="action-btn" @click="toggleVisibility">
            {{ checkin.is_public ? '🔒 改为私密' : '🌐 改为公开' }}
          </button>
          <button class="action-btn action-btn-danger" @click="handleDelete">🗑️ 删除打卡</button>
        </div>

        <!-- Social interactions -->
        <div class="section-card glass-card animate-fade-in-up" style="animation-delay: 0.32s; animation-fill-mode: both;">
          <div class="social-bar">
            <button :class="['like-btn', { liked: isLiked }]" @click="toggleLike">
              <span class="like-heart">{{ isLiked ? '❤️' : '🤍' }}</span>
              <span>{{ likesCount > 0 ? likesCount : '点赞' }}</span>
            </button>
            <span class="comment-stat">💬 {{ commentsCount }} 条评论</span>
            <button class="share-btn" @click="copyLink">{{ copyDone ? '✅ 已复制' : '🔗 链接' }}</button>
            <button class="share-btn share-btn-poster" @click="showShareCard = true">🖼 海报</button>
          </div>

          <div class="comments-section">
            <div v-if="loadingComments" class="comment-loading">
              <div class="loading-spinner" style="width:20px;height:20px;border-width:2px"></div>
            </div>
            <div v-else>
              <TransitionGroup name="comment-list" tag="div">
                <div v-for="c in comments" :key="c.id" class="comment-row">
                  <div class="comment-avatar">{{ c.user_nickname?.charAt(0) || '?' }}</div>
                  <div class="comment-body">
                    <div class="comment-header">
                      <span class="comment-author">{{ c.user_nickname }}</span>
                      <span class="comment-time">{{ formatCommentTime(c.created_at) }}</span>
                      <button
                        v-if="userStore.userId === c.user_id"
                        class="comment-del-btn"
                        @click="removeComment(c)"
                      >删除</button>
                    </div>
                    <p class="comment-text">{{ c.content }}</p>
                  </div>
                </div>
              </TransitionGroup>
              <p v-if="comments.length === 0" class="no-comments">暂无评论，来发表第一条吧 ✨</p>
            </div>

            <div v-if="userStore.isLoggedIn" class="comment-input-row">
              <input
                v-model="newComment"
                placeholder="写评论..."
                maxlength="500"
                @keyup.enter="submitComment"
                class="comment-input"
              />
              <button @click="submitComment" :disabled="!newComment.trim() || submittingComment" class="comment-send">
                发送
              </button>
            </div>
            <p v-else class="login-hint">
              <router-link to="/login">登录</router-link> 后才能评论
            </p>
          </div>
        </div>
      </template>

      <div v-else class="empty-state glass-card">
        <span style="font-size: 40px; margin-bottom: 8px;">🗺️</span>
        <p>打卡不存在，或你没有权限查看</p>
        <router-link to="/" class="btn-primary">返回地图</router-link>
      </div>
    </div>

    <el-dialog v-model="showPreview" width="80%" :show-close="true" class="photo-dialog">
      <img v-if="previewUrl" :src="previewUrl" class="preview-image" />
    </el-dialog>

    <!-- Edit modal -->
    <transition name="modal-fade">
      <div v-if="editVisible" class="edit-overlay" @click.self="editVisible = false">
        <div class="edit-modal glass-card">
          <div class="edit-modal-header">
            <span class="edit-modal-title">编辑打卡文案</span>
            <button class="edit-modal-close" @click="editVisible = false">✕</button>
          </div>
          <textarea
            v-model="editContent"
            class="edit-textarea"
            placeholder="写下你的旅行故事..."
            maxlength="500"
            rows="6"
          ></textarea>
          <div class="edit-char-count">{{ editContent.length }} / 500</div>
          <div class="edit-modal-actions">
            <button class="btn-secondary" @click="editVisible = false">取消</button>
            <button class="btn-primary" @click="saveEdit" :disabled="savingEdit">
              {{ savingEdit ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Share card modal -->
    <ShareCard
      v-if="showShareCard && checkin"
      :checkin="checkin"
      @close="showShareCard = false"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { getCheckin, likeCheckin, unlikeCheckin, getComments, addComment, deleteComment, updateCheckin, deleteCheckin, getCityIntro } from '../api/checkins'
import { formatCheckinDate, formatCoordinates, getImageUrl } from '../lib/checkins'
import { normalizeAddressName, normalizeCityName } from '../lib/region'
import { useUserStore } from '../stores/user.js'
import { useRouter } from 'vue-router'
import ShareCard from '../components/ShareCard.vue'

const route = useRoute()
const router = useRouter()
const props = defineProps({ id: [String, Number] })

const userStore = useUserStore()
const isOwner = computed(() => checkin.value && userStore.userId === checkin.value.user_id)
const checkin = ref(null)
const loading = ref(true)
const showPreview = ref(false)
const previewUrl = ref('')
const cityIntro = ref(null)
const cityIntroLoading = ref(false)
const displayCity = computed(() => normalizeCityName(checkin.value?.city || ''))
const displayAddress = computed(() => normalizeAddressName(checkin.value?.address || ''))

const isLiked = ref(false)
const likesCount = ref(0)
const commentsCount = ref(0)
const comments = ref([])
const loadingComments = ref(false)
const newComment = ref('')
const submittingComment = ref(false)

// Edit modal
const editVisible = ref(false)
const editContent = ref('')
const savingEdit = ref(false)

function openEdit() {
  editContent.value = checkin.value?.content || ''
  editVisible.value = true
}

async function saveEdit() {
  savingEdit.value = true
  try {
    const res = await updateCheckin(checkin.value.id, { content: editContent.value })
    checkin.value.content = res.data.content
    editVisible.value = false
    ElMessage.success('保存成功')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingEdit.value = false
  }
}

async function toggleVisibility() {
  try {
    const res = await updateCheckin(checkin.value.id, { is_public: !checkin.value.is_public })
    checkin.value.is_public = res.data.is_public
    ElMessage.success(res.data.is_public ? '已改为公开' : '已改为私密')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function handleDelete() {
  if (!confirm('确定删除这条打卡吗？')) return
  try {
    await deleteCheckin(checkin.value.id)
    ElMessage.success('已删除')
    router.push('/')
  } catch {
    ElMessage.error('删除失败')
  }
}

// Share
const copyDone = ref(false)
const showShareCard = ref(false)
function copyLink() {
  navigator.clipboard?.writeText(window.location.href).then(() => {
    copyDone.value = true
    setTimeout(() => { copyDone.value = false }, 2000)
  })
}

// Comment delete
async function removeComment(c) {
  try {
    await deleteComment(checkin.value.id, c.id)
    comments.value = comments.value.filter(x => x.id !== c.id)
    commentsCount.value = Math.max(0, commentsCount.value - 1)
  } catch {
    ElMessage.error('删除失败')
  }
}

// Format comment time
function formatCommentTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })
}

function previewPhoto(imageUrl) {
  previewUrl.value = getImageUrl(imageUrl)
  showPreview.value = true
}

async function loadSocialData(checkinId) {
  try {
    const res = await getComments(checkinId)
    comments.value = res.data.comments || []
    commentsCount.value = res.data.total || 0
  } catch (e) {
    console.error('加载评论失败', e)
  }
}

async function toggleLike() {
  if (!userStore.isLoggedIn) {
    ElMessage.info('请先登录')
    return
  }
  try {
    if (isLiked.value) {
      const res = await unlikeCheckin(checkin.value.id)
      isLiked.value = false
      likesCount.value = res.data.likes_count
    } else {
      const res = await likeCheckin(checkin.value.id)
      isLiked.value = true
      likesCount.value = res.data.likes_count
    }
  } catch (e) {
    console.error(e)
  }
}

async function submitComment() {
  const text = newComment.value.trim()
  if (!text) return
  submittingComment.value = true
  try {
    const res = await addComment(checkin.value.id, text)
    comments.value.push(res.data)
    commentsCount.value += 1
    newComment.value = ''
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '评论失败')
  } finally {
    submittingComment.value = false
  }
}

async function loadData() {
  loading.value = true
  const checkinId = props.id || route.params.id

  try {
    const res = await getCheckin(checkinId)
    checkin.value = res.data
    isLiked.value = Boolean(checkin.value.is_liked)
    likesCount.value = checkin.value.likes_count || 0
    commentsCount.value = checkin.value.comments_count || 0

    await loadSocialData(checkin.value.id)

    // Auto-load city intro
    if (displayCity.value) {
      cityIntroLoading.value = true
      try {
        const introRes = await getCityIntro(displayCity.value)
        cityIntro.value = introRes.data.intro || null
      } catch { /* silently ignore */ }
      finally { cityIntroLoading.value = false }
    }
  } catch (error) {
    console.error('Failed to load checkin:', error)
    checkin.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
/* ── City intro ── */
.city-intro-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  color: var(--ink-900);
  font-family: inherit;
  text-align: left;
}

.toggle-arrow {
  margin-left: auto;
  font-size: 16px;
  color: var(--ink-300);
  transition: transform var(--normal) var(--ease-out);
  display: inline-block;
}
.toggle-arrow.open { transform: rotate(180deg); }

.city-intro-body {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--ink-100);
}
.city-intro-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--ink-700);
  margin: 0 0 8px;
}
.city-intro-loading {
  font-size: 13px;
  color: var(--ink-300);
  margin: 0 0 8px;
}
.ai-credit {
  display: inline-block;
  font-size: 11px;
  color: var(--ink-300);
  font-weight: 500;
}

.intro-expand-enter-active { transition: opacity var(--normal) var(--ease-out), transform var(--normal) var(--ease-out); }
.intro-expand-leave-active { transition: opacity var(--fast) var(--ease-out); }
.intro-expand-enter-from   { opacity: 0; transform: translateY(-6px); }
.intro-expand-leave-to     { opacity: 0; }

.checkin-detail-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: var(--bg-base);
}

.detail-container {
  max-width: 860px;
  margin: 0 auto;
}

/* ── Back button ── */
.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-full);
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 8px 18px;
  margin-bottom: 20px;
  transition: background var(--fast) var(--ease-out), color var(--fast) var(--ease-out), transform var(--fast) var(--ease-out);
  font-family: inherit;
  box-shadow: var(--shadow-card);
}

.back-btn:hover {
  background: var(--bg-muted);
  color: var(--brand);
  transform: translateX(-2px);
}

.back-arrow {
  font-size: 14px;
  transition: transform var(--fast) var(--ease-out);
}

.back-btn:hover .back-arrow {
  transform: translateX(-3px);
}

/* ── Cards ── */
.checkin-header,
.section-card,
.empty-state {
  position: relative;
  padding: 28px;
  margin-bottom: 20px;
}

/* ── Header ── */
.checkin-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.checkin-name {
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: var(--ink-900);
}

.badge-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.badge-blue {
  background: var(--brand-light);
  color: var(--brand);
}

.badge-amber {
  background: rgba(232, 161, 0, 0.10);
  color: var(--warning);
}

.badge-dot-status {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.dot-blue { background: var(--brand); }
.dot-amber { background: var(--warning); }

.checkin-address {
  margin-top: 10px;
  color: var(--ink-500);
  font-size: 14px;
}

.checkin-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  color: var(--ink-300);
  font-size: 13px;
}

.meta-sep { opacity: 0.5; }

.meta-user {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--brand);
  text-decoration: none;
  font-weight: 600;
  transition: opacity var(--fast) var(--ease-out);
}

.meta-user:hover { opacity: 0.8; }

.meta-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--brand-gradient);
  color: white;
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── Coordinate panel ── */
.meta-coord-panel {
  min-width: 170px;
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.12);
  flex-shrink: 0;
}

.coord-label {
  display: block;
  color: var(--ink-300);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.coord-value {
  font-size: 13px;
  font-family: var(--font-mono);
  color: var(--ink-900);
}

/* ── Section title ── */
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 18px;
  color: var(--ink-900);
  letter-spacing: -0.02em;
}

.section-icon {
  font-size: 16px;
}

/* ── Mini map ── */
.mini-map {
  height: 240px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* ── Content text ── */
.content-text {
  color: var(--ink-500);
  font-size: 15px;
  line-height: 1.85;
  white-space: pre-wrap;
}

/* ── Photo count ── */
.photo-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-light);
  color: var(--brand);
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: var(--radius-full);
}

/* ── Photo grid ── */
.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.photo-item {
  border: none;
  padding: 0;
  border-radius: var(--radius-md);
  overflow: hidden;
  aspect-ratio: 1;
  cursor: pointer;
  background: var(--bg-muted);
  position: relative;
  animation: fadeInUp 0.45s cubic-bezier(0.22, 1, 0.36, 1) both;
  transition: transform var(--normal) var(--ease-out), box-shadow var(--normal) var(--ease-out);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}

.photo-item:hover {
  transform: translateY(-3px) scale(1.02);
  box-shadow: var(--shadow-float);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s ease;
}

.photo-item:hover img {
  transform: scale(1.06);
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(28, 16, 7, 0.0);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--normal) var(--ease-out);
}

.photo-item:hover .photo-overlay {
  background: rgba(28, 16, 7, 0.12);
}

.photo-zoom-icon {
  opacity: 0;
  transform: scale(0.7);
  transition: all 0.25s ease;
  font-size: 20px;
}

.photo-item:hover .photo-zoom-icon {
  opacity: 1;
  transform: scale(1);
}

/* ── Video player ── */
.video-player-wrap {
  width: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: #000;
}

.checkin-video {
  width: 100%;
  max-height: 480px;
  display: block;
  border-radius: var(--radius-md);
}

/* ── Empty photos ── */
.empty-photos {
  text-align: center;
  padding: 28px 0;
  color: var(--ink-300);
}

.empty-icon { font-size: 32px; display: block; margin-bottom: 8px; }

/* ── Preview ── */
.preview-image {
  width: 100%;
  max-height: 78vh;
  object-fit: contain;
}

/* ── Map pin ── */
:deep(.detail-pin) {
  width: 32px;
  height: 32px;
  border-radius: 50% 50% 50% 4px;
  transform: rotate(-45deg);
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 20px rgba(232, 93, 4, 0.30);
}

:deep(.detail-pin-dot) {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: white;
  transform: rotate(45deg);
}

/* ── Owner actions ── */
.owner-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 16px 20px;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--ink-100);
  background: var(--bg-surface);
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background var(--fast) var(--ease-out), color var(--fast) var(--ease-out), border-color var(--fast) var(--ease-out);
}

.action-btn:hover {
  background: var(--bg-muted);
  color: var(--ink-900);
  border-color: var(--border-strong);
}

.action-btn-danger:hover {
  color: var(--error);
  border-color: rgba(217, 79, 61, 0.25);
  background: rgba(217, 79, 61, 0.05);
}

/* ── Share button ── */
.share-btn {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--ink-100);
  background: transparent;
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  transition: background var(--fast) var(--ease-out), color var(--fast) var(--ease-out);
}

.share-btn:hover {
  background: var(--bg-muted);
  color: var(--ink-900);
}

.share-btn-poster {
  margin-left: 0;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.12));
  border-color: rgba(102, 126, 234, 0.3);
  color: #7c6fe0;
}
.share-btn-poster:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.22), rgba(118, 75, 162, 0.22));
  color: #6c5ce7;
}

/* ── Social bar ── */
.social-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ink-100);
}

.like-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  cursor: pointer;
  font-size: 14px;
  font-family: inherit;
  font-weight: 500;
  color: var(--ink-500);
  transition: border-color var(--fast) var(--ease-out), color var(--fast) var(--ease-out), background var(--fast) var(--ease-out);
}

.like-btn:hover {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-light);
}

.like-btn.liked {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-light);
}

.like-heart {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.like-btn:active .like-heart {
  transform: scale(1.3);
}

.comment-stat {
  color: var(--ink-300);
  font-size: 14px;
}

/* ── Comment header ── */
.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.comment-time {
  font-size: 11px;
  color: var(--ink-300);
}

.comment-del-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 11px;
  color: var(--ink-300);
  cursor: pointer;
  padding: 0 2px;
  font-family: inherit;
  transition: color var(--fast) var(--ease-out);
}

.comment-del-btn:hover { color: #EF4444; }

/* ── Edit modal ── */
.edit-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(28, 16, 7, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.edit-modal {
  width: 100%;
  max-width: 480px;
  padding: 24px;
  border-radius: var(--radius-lg);
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.edit-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.edit-modal-title {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
}

.edit-modal-close {
  width: 28px;
  height: 28px;
  border: none;
  background: var(--bg-muted);
  border-radius: 50%;
  cursor: pointer;
  font-size: 13px;
  color: var(--ink-500);
  display: flex;
  align-items: center;
  justify-content: center;
}

.edit-textarea {
  width: 100%;
  padding: 12px 14px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-md);
  font-size: 14px;
  font-family: inherit;
  line-height: 1.7;
  resize: vertical;
  outline: none;
  color: var(--ink-900);
  background: var(--bg-muted);
  transition: border-color var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
  box-sizing: border-box;
}

.edit-textarea:focus {
  border-color: var(--brand);
  background: var(--bg-surface);
  box-shadow: 0 0 0 3px var(--brand-light);
}

.edit-char-count {
  font-size: 12px;
  color: var(--ink-300);
  text-align: right;
  margin-top: -8px;
}

.edit-modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

/* ── Comments ── */
.comment-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}

.comment-avatar {
  width: 32px;
  height: 32px;
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

.comment-author {
  font-size: 13px;
  font-weight: 700;
  color: var(--ink-900);
  margin-bottom: 2px;
  display: block;
}

.comment-text {
  font-size: 14px;
  color: var(--ink-500);
  margin: 0;
  line-height: 1.6;
}

.no-comments {
  color: var(--ink-100);
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

.comment-input-row {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.comment-input {
  flex: 1;
  padding: 10px 16px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-sm);
  font-size: 14px;
  outline: none;
  font-family: inherit;
  background: var(--bg-muted);
  color: var(--ink-900);
  transition: border-color var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out), background var(--fast) var(--ease-out);
}

.comment-input:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-light);
  background: var(--bg-surface);
}

.comment-send {
  padding: 10px 18px;
  background: var(--brand-gradient);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  transition: filter var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.25);
}

.comment-send:hover { filter: brightness(0.93); box-shadow: 0 4px 14px rgba(232, 93, 4, 0.30); }
.comment-send:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

.login-hint { font-size: 13px; color: var(--ink-300); margin-top: 12px; }
.login-hint a { color: var(--brand); font-weight: 600; }

/* ── Comment transition ── */
.comment-list-enter-active { transition: all 0.3s ease; }
.comment-list-leave-active { transition: all 0.2s ease; }
.comment-list-enter-from { opacity: 0; transform: translateY(10px); }
.comment-list-leave-to { opacity: 0; transform: translateX(-10px); }

/* ── Responsive ── */
@media (max-width: 768px) {
  .checkin-detail-page { padding: 16px; }

  .checkin-header,
  .section-card,
  .empty-state { padding: 22px; }

  .checkin-header { flex-direction: column; }

  .checkin-name { font-size: 24px; }

  .photo-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
