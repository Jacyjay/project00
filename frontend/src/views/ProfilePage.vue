<template>
  <div class="profile-page">
    <div class="profile-container animate-fade-in">
      <button class="back-btn" @click="$router.push('/')" id="btn-back">← 返回地图</button>

      <div v-if="loading" class="loading-state">
        <div class="loading-spinner"></div>
      </div>

      <template v-else-if="user">
        <div class="profile-header glass-card">
          <div class="profile-avatar-section">
            <div class="profile-avatar-wrapper">
              <div class="profile-avatar-lg" v-if="!avatarUrl">
                {{ user.nickname?.charAt(0)?.toUpperCase() || '?' }}
              </div>
              <img v-else :src="avatarUrl" class="profile-avatar-img" alt="avatar" />
              <button v-if="isOwnProfile" class="avatar-upload-btn" @click="triggerAvatarUpload" title="更换头像">
                📷
              </button>
              <input
                ref="avatarInput"
                type="file"
                accept="image/*"
                class="avatar-file-input"
                @change="handleAvatarChange"
              />
            </div>
            <div class="profile-info">
              <h1 class="profile-name">{{ user.nickname }}</h1>
              <p v-if="user.bio" class="profile-bio">{{ user.bio }}</p>
              <p class="profile-joined">加入于 {{ formatDate(user.created_at) }}</p>
              <!-- Email row: always shown on own profile; shown on others only when public -->
              <div v-if="isOwnProfile || user.email" class="profile-email-row">
                <span class="profile-email-icon">✉️</span>
                <span class="profile-email-text">{{ isOwnProfile ? ownEmail : user.email }}</span>
                <div v-if="isOwnProfile" class="email-toggle-wrap">
                  <label class="email-toggle">
                    <input
                      type="checkbox"
                      :checked="showEmail"
                      @change="handleShowEmailChange"
                    />
                    <span class="email-toggle-slider"></span>
                  </label>
                  <span class="email-toggle-label">{{ showEmail ? '已公开' : '已隐藏' }}</span>
                </div>
              </div>
              <div v-if="!isOwnProfile" class="profile-actions">
                <button
                  class="btn-follow"
                  :class="{ following: isFollowing, mutual: isMutual }"
                  :disabled="followLoading"
                  style="color:#000;font-weight:700;font-size:13px;"
                  @click="toggleFollow"
                >
                  {{ isMutual ? '💞 互相关注' : isFollowing ? '✓ 已关注' : '+ 关注' }}
                </button>
                <button class="btn-message" @click="handleSendMessage">💬 发私信</button>
              </div>
            </div>
          </div>

          <div class="stats-row">
            <!-- 粉丝 -->
            <div
              class="stat-card"
              :class="{ 'stat-clickable': isOwnProfile || showFollowers }"
              @click="openFollowList('followers')"
            >
              <span class="stat-number">{{ followersCount }}</span>
              <div class="stat-label-row">
                <span class="stat-label">粉丝</span>
                <span v-if="!showFollowers" class="stat-lock" title="已私密">🔒</span>
              </div>
              <button
                v-if="isOwnProfile"
                class="stat-privacy-btn"
                :title="showFollowers ? '设为私密' : '设为公开'"
                @click.stop="toggleFollowPrivacy('followers')"
              >{{ showFollowers ? '公开' : '私密' }}</button>
            </div>

            <!-- 关注 -->
            <div
              class="stat-card"
              :class="{ 'stat-clickable': isOwnProfile || showFollowing }"
              @click="openFollowList('following')"
            >
              <span class="stat-number">{{ followingCount }}</span>
              <div class="stat-label-row">
                <span class="stat-label">关注</span>
                <span v-if="!showFollowing" class="stat-lock" title="已私密">🔒</span>
              </div>
              <button
                v-if="isOwnProfile"
                class="stat-privacy-btn"
                :title="showFollowing ? '设为私密' : '设为公开'"
                @click.stop="toggleFollowPrivacy('following')"
              >{{ showFollowing ? '公开' : '私密' }}</button>
            </div>

            <div class="stat-card">
              <span class="stat-number">{{ stats.total_checkins }}</span>
              <span class="stat-label">次打卡</span>
            </div>
            <div class="stat-card">
              <span class="stat-number">{{ stats.total_places }}</span>
              <span class="stat-label">个地点</span>
            </div>
          </div>

          <!-- Follow list modal -->
          <FollowListModal
            v-if="followListModal"
            :userId="user.id"
            :type="followListModal"
            @close="followListModal = null"
          />
        </div>

        <div class="section-card glass-card" v-if="checkins.length">
          <h2 class="section-title">🗺️ 旅行足迹</h2>
          <div ref="footprintMapRef" class="footprint-map"></div>
        </div>

        <!-- Achievements Section -->
        <div class="section-card glass-card">
          <div class="section-header">
            <h2 class="section-title">🏆 成就徽章</h2>
            <span class="achievement-count">{{ achievementStats.unlocked }}/{{ achievementStats.total }}</span>
          </div>

          <div v-if="achievements.length === 0" class="empty-state">
            <p>{{ isOwnProfile ? '还没有解锁任何成就，快去打卡吧！' : '该用户还没有解锁任何成就' }}</p>
          </div>

          <div v-else class="achievements-grid">
            <AchievementBadge
              v-for="achievement in achievements"
              :key="achievement.code"
              :achievement="achievement"
              :unlocked="achievement.unlocked"
              @click="showAchievementDetail(achievement)"
            />
          </div>
        </div>

        <div class="section-card glass-card">
          <h2 class="section-title">📋 打卡时间线</h2>
          <div v-if="checkins.length === 0" class="empty-state">
            <p>还没有打卡记录</p>
          </div>
          <div v-else class="timeline">
            <div v-for="checkin in checkins" :key="checkin.id" class="timeline-item">
              <div class="timeline-dot"></div>
              <div class="timeline-content">
                <div class="timeline-header">
                  <router-link :to="`/checkins/${checkin.id}`" class="timeline-place">
                    📍 {{ checkin.location_name }}
                  </router-link>
                  <div class="timeline-header-side">
                    <span class="timeline-date">
                      {{ formatCheckinDate(checkin) }}
                    </span>
                    <button
                      v-if="isOwnProfile"
                      type="button"
                      class="timeline-delete-btn"
                      :disabled="deletingCheckinId === checkin.id"
                      @click="handleDeleteCheckin(checkin)"
                    >
                      {{ deletingCheckinId === checkin.id ? '删除中...' : '删除' }}
                    </button>
                  </div>
                </div>
                <span v-if="!checkin.is_public" class="timeline-visibility">仅自己可见</span>
                <p v-if="checkin.content" class="timeline-text">{{ checkin.content }}</p>
                <div v-if="checkin.photos?.length" class="timeline-photos">
                  <img
                    v-for="photo in checkin.photos"
                    :key="photo.id"
                    :src="getImageUrl(photo.image_url)"
                    class="timeline-photo"
                  />
                </div>

                <div v-if="checkin.is_public" class="timeline-social">
                  <button
                    type="button"
                    :class="['timeline-action', { liked: checkin.is_liked }]"
                    @click="toggleTimelineLike(checkin)"
                  >
                    <span>{{ checkin.is_liked ? '❤️' : '🤍' }}</span>
                    <span>{{ checkin.likes_count || 0 }}</span>
                  </button>
                  <button
                    type="button"
                    class="timeline-action"
                    @click="toggleTimelineComments(checkin)"
                  >
                    <span>💬</span>
                    <span>{{ checkin.comments_count || 0 }}</span>
                  </button>
                  <router-link :to="`/checkins/${checkin.id}`" class="timeline-detail-link">
                    查看详情
                  </router-link>
                </div>

                <div v-if="checkin.is_public && commentsOpen[checkin.id]" class="timeline-comments glass-card">
                  <div v-if="commentsLoading[checkin.id]" class="timeline-comments-empty">加载评论中...</div>
                  <template v-else>
                    <div
                      v-for="comment in commentsByCheckin[checkin.id] || []"
                      :key="comment.id"
                      class="timeline-comment"
                    >
                      <span class="timeline-comment-author">{{ comment.user_nickname }}</span>
                      <span class="timeline-comment-text">{{ comment.content }}</span>
                    </div>
                    <div
                      v-if="!(commentsByCheckin[checkin.id] || []).length"
                      class="timeline-comments-empty"
                    >
                      暂无评论，来发表第一条吧
                    </div>
                  </template>

                  <div v-if="userStore.isLoggedIn" class="timeline-comment-input">
                    <input
                      v-model="commentDrafts[checkin.id]"
                      type="text"
                      maxlength="500"
                      placeholder="写点评论..."
                      class="timeline-comment-field"
                      @keyup.enter="submitTimelineComment(checkin)"
                    />
                    <button
                      type="button"
                      class="timeline-comment-submit"
                      :disabled="commentSubmitting[checkin.id] || !String(commentDrafts[checkin.id] || '').trim()"
                      @click="submitTimelineComment(checkin)"
                    >
                      {{ commentSubmitting[checkin.id] ? '发送中' : '发送' }}
                    </button>
                  </div>
                  <p v-else class="timeline-login-hint">
                    <router-link to="/login">登录</router-link> 后才能评论
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else class="empty-state glass-card">
        <p>用户不存在</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { getUser, getUserStats, uploadAvatar, updateShowEmail } from '../api/users'
import { addComment, deleteCheckin, getComments, getUserCheckins, likeCheckin, unlikeCheckin } from '../api/checkins'
import { followUser, unfollowUser, getFollowStatus, updateFollowPrivacy } from '../api/follows'
import { getUserAchievements, getAllAchievements } from '../api/achievements'
import FollowListModal from '../components/FollowListModal.vue'
import AchievementBadge from '../components/AchievementBadge.vue'
import { formatCheckinDate, formatDate, getImageUrl } from '../lib/checkins'
import { loadAmap } from '../lib/amap'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const props = defineProps({ id: [String, Number] })
const userStore = useUserStore()

const isOwnProfile = computed(() => {
  const id = props.id || route.params.id
  return userStore.isLoggedIn && String(userStore.userId) === String(id)
})

const showEmail = ref(true)
const ownEmail = computed(() => userStore.user?.email || '')

async function handleShowEmailChange(e) {
  const val = e.target.checked
  try {
    await updateShowEmail(val)
    showEmail.value = val
    if (user.value) user.value.show_email = val
    ElMessage.success(val ? '邮箱已公开' : '邮箱已隐藏')
  } catch {
    ElMessage.error('设置失败，请重试')
  }
}

const avatarInput = ref(null)
const avatarUrl = computed(() => {
  if (!user.value) return null
  if (user.value.avatar_url) return getImageUrl(user.value.avatar_url)
  return null
})

function triggerAvatarUpload() {
  avatarInput.value?.click()
}

async function handleAvatarChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  try {
    const res = await uploadAvatar(file)
    if (res.data?.avatar_url) {
      user.value.avatar_url = res.data.avatar_url
    }
    ElMessage.success('头像更新成功')
  } catch (err) {
    console.error('Avatar upload failed:', err)
    ElMessage.error('头像上传失败')
  } finally {
    e.target.value = ''
  }
}

function handleSendMessage() {
  if (!userStore.isLoggedIn) {
    ElMessageBox.confirm(
      '发送私信需要先登录，是否前往登录？',
      '请登录',
      {
        confirmButtonText: '去登录',
        cancelButtonText: '取消',
        type: 'info',
      }
    ).then(() => {
      router.push({ name: 'login', query: { redirect: route.fullPath } })
    }).catch(() => {})
    return
  }
  const partnerId = props.id || route.params.id
  router.push({ name: 'chat', params: { partnerId } })
}

const user = ref(null)
const stats = ref({ total_checkins: 0, total_places: 0, total_photos: 0 })
const checkins = ref([])
const loading = ref(true)

// Achievements state
const achievements = ref([])
const achievementStats = ref({ total: 0, unlocked: 0 })

// Follow state
const isFollowing = ref(false)
const isMutual = ref(false)
const followersCount = ref(0)
const followingCount = ref(0)
const followLoading = ref(false)
const showFollowers = ref(true)   // target user's privacy setting
const showFollowing = ref(true)
const followListModal = ref(null) // null | 'followers' | 'following'

async function openFollowList(type) {
  // For own profile always open; for others check privacy
  if (!isOwnProfile.value) {
    if (type === 'followers' && !showFollowers.value) {
      return  // locked, don't open
    }
    if (type === 'following' && !showFollowing.value) {
      return
    }
  }
  followListModal.value = type
}

async function toggleFollowPrivacy(field) {
  try {
    const payload = {}
    if (field === 'followers') {
      showFollowers.value = !showFollowers.value
      payload.show_followers = showFollowers.value
    } else {
      showFollowing.value = !showFollowing.value
      payload.show_following = showFollowing.value
    }
    await updateFollowPrivacy(payload)
  } catch {
    // revert
    if (field === 'followers') showFollowers.value = !showFollowers.value
    else showFollowing.value = !showFollowing.value
  }
}

async function toggleFollow() {
  if (!userStore.isLoggedIn) {
    ElMessage.info('请先登录')
    return
  }
  followLoading.value = true
  try {
    if (isFollowing.value) {
      await unfollowUser(user.value.id)
      isFollowing.value = false
      isMutual.value = false
      followersCount.value = Math.max(0, followersCount.value - 1)
    } else {
      await followUser(user.value.id)
      isFollowing.value = true
      followersCount.value += 1
    }
  } catch {
    ElMessage.error('操作失败，请重试')
  } finally {
    followLoading.value = false
  }
}
const footprintMapRef = ref(null)
const commentsOpen = ref({})
const commentsLoading = ref({})
const commentsByCheckin = ref({})
const commentDrafts = ref({})
const commentSubmitting = ref({})
const deletingCheckinId = ref(null)
let footprintMap = null

function destroyFootprintMap() {
  if (footprintMap) {
    footprintMap.destroy()
    footprintMap = null
  }
}

async function renderFootprintMap() {
  if (!footprintMapRef.value || !checkins.value.length) {
    destroyFootprintMap()
    return
  }

  destroyFootprintMap()

  const AMap = await loadAmap()
  const orderedCheckins = [...checkins.value].sort((left, right) => {
    const leftTime = new Date(left.visit_date || left.created_at).getTime()
    const rightTime = new Date(right.visit_date || right.created_at).getTime()
    return leftTime - rightTime
  })

  footprintMap = new AMap.Map(footprintMapRef.value, {
    center: [105, 35],
    zoom: 4,
    mapStyle: 'amap://styles/light',
  })

  const path = orderedCheckins.map((checkin) => [checkin.longitude, checkin.latitude])
  const markers = orderedCheckins.map((checkin, index) => {
    const marker = new AMap.Marker({
      position: [checkin.longitude, checkin.latitude],
      offset: new AMap.Pixel(-15, -15),
      content: `
        <div class="footprint-marker">
          <span>${index + 1}</span>
        </div>
      `,
    })

    marker.on('click', () => {
      router.push(`/checkins/${checkin.id}`)
    })

    return marker
  })

  footprintMap.add(markers)

  if (path.length > 1) {
    footprintMap.add(
      new AMap.Polyline({
        path,
        strokeColor: '#007AFF',
        strokeWeight: 4,
        strokeOpacity: 0.7,
        lineJoin: 'round',
        lineCap: 'round',
      })
    )
  }

  footprintMap.setFitView()
}

async function toggleTimelineLike(checkin) {
  if (!userStore.isLoggedIn) {
    ElMessage.info('请先登录后再点赞')
    return
  }

  try {
    if (checkin.is_liked) {
      const res = await unlikeCheckin(checkin.id)
      checkin.is_liked = false
      checkin.likes_count = res.data.likes_count
      return
    }

    const res = await likeCheckin(checkin.id)
    checkin.is_liked = true
    checkin.likes_count = res.data.likes_count
  } catch (error) {
    console.error('Profile like failed:', error)
    ElMessage.error(error.response?.data?.detail || '点赞失败，请重试')
  }
}

async function loadTimelineComments(checkinId) {
  commentsLoading.value[checkinId] = true
  try {
    const res = await getComments(checkinId)
    commentsByCheckin.value[checkinId] = res.data.comments || []
  } catch (error) {
    console.error('Profile comments load failed:', error)
    ElMessage.error('加载评论失败')
  } finally {
    commentsLoading.value[checkinId] = false
  }
}

async function toggleTimelineComments(checkin) {
  const nextOpen = !commentsOpen.value[checkin.id]
  commentsOpen.value[checkin.id] = nextOpen

  if (nextOpen && commentsByCheckin.value[checkin.id] === undefined) {
    await loadTimelineComments(checkin.id)
  }
}

async function submitTimelineComment(checkin) {
  if (!userStore.isLoggedIn) {
    ElMessage.info('请先登录后再评论')
    return
  }

  const content = String(commentDrafts.value[checkin.id] || '').trim()
  if (!content) return

  commentSubmitting.value[checkin.id] = true
  try {
    const res = await addComment(checkin.id, content)
    const currentComments = commentsByCheckin.value[checkin.id] || []
    commentsByCheckin.value[checkin.id] = [...currentComments, res.data]
    commentDrafts.value[checkin.id] = ''
    checkin.comments_count = (checkin.comments_count || 0) + 1
    commentsOpen.value[checkin.id] = true
  } catch (error) {
    console.error('Profile comment submit failed:', error)
    ElMessage.error(error.response?.data?.detail || '评论失败，请重试')
  } finally {
    commentSubmitting.value[checkin.id] = false
  }
}

async function handleDeleteCheckin(checkin) {
  if (!isOwnProfile.value) return

  try {
    await ElMessageBox.confirm(
      '删除后将同时移除这条打卡的照片、点赞和评论，且无法恢复。是否继续？',
      '删除打卡',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch {
    return
  }

  deletingCheckinId.value = checkin.id
  try {
    await deleteCheckin(checkin.id)
    delete commentsOpen.value[checkin.id]
    delete commentsLoading.value[checkin.id]
    delete commentsByCheckin.value[checkin.id]
    delete commentDrafts.value[checkin.id]
    delete commentSubmitting.value[checkin.id]
    await loadData({ showLoading: false })
    ElMessage.success('打卡已删除')
  } catch (error) {
    console.error('Profile checkin delete failed:', error)
    ElMessage.error(error.response?.data?.detail || '删除失败，请重试')
  } finally {
    deletingCheckinId.value = null
  }
}

async function loadData({ showLoading = true } = {}) {
  if (showLoading) {
    loading.value = true
  }
  const userId = props.id || route.params.id

  try {
    const [userRes, statsRes, checkinsRes] = await Promise.all([
      getUser(userId),
      getUserStats(userId),
      getUserCheckins(userId),
    ])

    user.value = userRes.data
    stats.value = statsRes.data
    checkins.value = checkinsRes.data
    showFollowers.value = userRes.data.show_followers ?? true
    showFollowing.value = userRes.data.show_following ?? true
    if (isOwnProfile.value) showEmail.value = userRes.data.show_email ?? true

    await nextTick()
    await renderFootprintMap()
  } catch (error) {
    console.error('Failed to load profile:', error)
  } finally {
    if (showLoading) {
      loading.value = false
    }
  }

  // Load follow status separately — must not block profile rendering
  try {
    const followRes = await getFollowStatus(userId)
    isFollowing.value = followRes.data.is_following
    isMutual.value = followRes.data.is_mutual
    followersCount.value = followRes.data.followers_count
    followingCount.value = followRes.data.following_count
  } catch {
    // silently ignore — follow status is non-critical
  }

  // Load achievements
  try {
    if (isOwnProfile.value) {
      // 自己的主页：显示所有成就及解锁状态
      const allAchievementsRes = await getAllAchievements()
      achievements.value = allAchievementsRes.data
      achievementStats.value = {
        total: allAchievementsRes.data.length,
        unlocked: allAchievementsRes.data.filter(a => a.unlocked).length,
      }
    } else {
      // 他人主页：只显示已解锁的成就
      const achievementsRes = await getUserAchievements(userId)
      achievements.value = achievementsRes.data
      achievementStats.value = {
        total: achievementsRes.data.length,
        unlocked: achievementsRes.data.filter(a => a.unlocked).length,
      }
    }
  } catch (error) {
    console.error('Failed to load achievements:', error)
  }
}

function showAchievementDetail(achievement) {
  if (!achievement.unlocked) return
  ElMessageBox.alert(
    achievement.description || '暂无描述',
    `${achievement.icon} ${achievement.name}`,
    {
      confirmButtonText: '确定',
      customClass: 'achievement-detail-box',
    }
  )
}

onMounted(loadData)

onBeforeUnmount(() => {
  destroyFootprintMap()
})
</script>

<style scoped>
.profile-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: var(--bg-base);
}

.profile-container {
  max-width: 800px;
  margin: 0 auto;
}

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

/* ── Header hero ── */
.profile-header {
  padding: 32px;
  margin-bottom: 20px;
  position: relative;
}

.profile-avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.profile-avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.profile-avatar-lg {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  color: var(--ink-900);
  flex-shrink: 0;
  box-shadow: 0 4px 20px rgba(232, 93, 4, 0.25);
  position: relative;
}

.profile-avatar-img {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 0 4px 20px rgba(232, 93, 4, 0.20);
}

.avatar-upload-btn {
  position: absolute;
  bottom: -2px;
  right: -2px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--bg-surface);
  border: 2px solid var(--ink-100);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  cursor: pointer;
  transition: background var(--fast) var(--ease-out), border-color var(--fast) var(--ease-out), transform var(--fast) var(--ease-spring);
  box-shadow: var(--shadow-card);
  padding: 0;
  line-height: 1;
}

.avatar-upload-btn:hover {
  background: var(--brand);
  border-color: var(--brand);
  transform: scale(1.1);
}

.avatar-file-input {
  display: none;
}

.profile-name {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
  letter-spacing: -0.03em;
  color: var(--ink-900);
}

.profile-bio {
  font-size: 14px;
  color: var(--ink-500);
  margin-top: 6px;
  line-height: 1.6;
}

.profile-joined {
  font-size: 12px;
  color: var(--ink-300);
  margin-top: 4px;
}

.profile-info {
  display: flex;
  flex-direction: column;
  gap: 0;
}

/* ── Email row ── */
.profile-email-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  flex-wrap: wrap;
}

.profile-email-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.profile-email-text {
  font-size: 13px;
  color: var(--ink-500);
  word-break: break-all;
}

.email-toggle-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 4px;
}

.email-toggle {
  position: relative;
  display: inline-block;
  width: 34px;
  height: 18px;
  flex-shrink: 0;
}

.email-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}

.email-toggle-slider {
  position: absolute;
  inset: 0;
  background: var(--ink-300);
  border-radius: 9px;
  cursor: pointer;
  transition: background 0.2s;
}

.email-toggle-slider::before {
  content: '';
  position: absolute;
  height: 12px;
  width: 12px;
  left: 3px;
  top: 3px;
  background: white;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}

.email-toggle input:checked + .email-toggle-slider {
  background: var(--brand);
}

.email-toggle input:checked + .email-toggle-slider::before {
  transform: translateX(16px);
}

.email-toggle-label {
  font-size: 11px;
  color: var(--ink-300);
  font-weight: 600;
  white-space: nowrap;
}

.profile-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.btn-follow {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 18px;
  background: #f0f0f0;
  border: 1.5px solid #222;
  border-radius: var(--radius-full);
  color: #000 !important;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--fast), opacity var(--fast);
}
.btn-follow:hover:not(:disabled) {
  background: #e0e0e0;
}
.btn-follow:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-follow.following {
  background: #f5f5f5;
  border: 1.5px solid #888;
  color: #000 !important;
}
.btn-follow.following:hover:not(:disabled) {
  background: #fee2e2;
  color: #000 !important;
  border-color: #f87171;
}
.btn-follow.mutual {
  background: #f0eeff;
  border: 1.5px solid #667eea;
  color: #000 !important;
}

.btn-message {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--brand-light);
  border: 1.5px solid rgba(232, 93, 4, 0.18);
  border-radius: var(--radius-full);
  color: var(--brand);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--fast) var(--ease-out), color var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
  width: fit-content;
}

.btn-message:hover {
  background: var(--brand);
  border-color: transparent;
  color: white;
  box-shadow: 0 4px 12px rgba(232, 93, 4, 0.25);
}

/* ── Stats ── */
.stats-row {
  display: flex;
  gap: 12px;
}

.stat-card {
  flex: 1;
  text-align: center;
  padding: 20px 18px;
  background: var(--brand-light);
  border-radius: var(--radius-md);
  border: 1px solid rgba(232, 93, 4, 0.10);
  transition: transform var(--normal) var(--ease-out), box-shadow var(--normal) var(--ease-out);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-card);
}

.stat-number {
  display: block;
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  color: var(--brand);
  animation: countIn 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes countIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.stat-label {
  font-size: 12px;
  color: var(--ink-500);
  margin-top: 4px;
  font-weight: 500;
}

.stat-clickable {
  cursor: pointer;
}
.stat-clickable:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 16px rgba(232, 93, 4, 0.15);
}

.stat-label-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 4px;
}

.stat-lock {
  font-size: 11px;
}

.stat-privacy-btn {
  margin-top: 6px;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  border: 1px solid var(--ink-200, #ccc);
  background: var(--bg-surface);
  color: var(--ink-500);
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
}
.stat-privacy-btn:hover {
  background: var(--bg-muted);
  color: var(--ink-800);
}

/* ── Section cards ── */
.section-card,
.empty-state {
  padding: 24px;
  margin-bottom: 20px;
  position: relative;
}

.section-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 18px;
  color: var(--ink-900);
  letter-spacing: -0.02em;
}

/* ── Achievements ── */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.achievement-count {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-400);
  background: var(--bg-muted);
  padding: 4px 12px;
  border-radius: var(--radius-full);
}

.achievements-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.footprint-map {
  height: 250px;
  border-radius: var(--radius-md);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

/* ── Timeline ── */
.timeline {
  position: relative;
  padding-left: 28px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 0;
  bottom: 0;
  width: 2px;
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-secondary) 100%);
  opacity: 0.20;
  border-radius: 1px;
}

.timeline-item {
  position: relative;
  margin-bottom: 24px;
}

.timeline-dot {
  position: absolute;
  left: -24px;
  top: 6px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--brand-gradient);
  box-shadow: 0 0 0 5px var(--brand-light);
  transition: box-shadow var(--normal) var(--ease-out);
}

.timeline-item:hover .timeline-dot {
  box-shadow: 0 0 0 6px rgba(232, 93, 4, 0.14);
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.timeline-header-side {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.timeline-place {
  color: var(--ink-900);
  font-weight: 600;
  text-decoration: none;
  transition: color var(--fast) var(--ease-out);
}

.timeline-place:hover {
  color: var(--brand);
}

.timeline-date {
  color: var(--ink-300);
  font-size: 12px;
}

.timeline-delete-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  padding: 7px 12px;
  border: none;
  border-radius: var(--radius-full);
  background: rgba(217, 79, 61, 0.06);
  color: var(--error);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--fast) var(--ease-out), transform var(--fast) var(--ease-out);
}

.timeline-delete-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: rgba(217, 79, 61, 0.12);
}

.timeline-delete-btn:disabled {
  opacity: 0.5;
  cursor: wait;
}

.timeline-visibility {
  display: inline-flex;
  margin-top: 10px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: rgba(232, 161, 0, 0.08);
  color: var(--warning);
  font-size: 12px;
  font-weight: 600;
}

.timeline-text {
  margin-top: 10px;
  color: var(--ink-500);
  line-height: 1.75;
}

.timeline-photos {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.timeline-photo {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  transition: transform var(--normal) var(--ease-out), box-shadow var(--normal) var(--ease-out);
  cursor: pointer;
}

.timeline-photo:hover {
  transform: translateY(-2px) scale(1.04);
  box-shadow: var(--shadow-float);
}

/* ── Social actions ── */
.timeline-social {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.timeline-action {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-full);
  border: 1px solid var(--ink-100);
  background: var(--bg-surface);
  color: var(--ink-300);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: color var(--fast) var(--ease-out), background var(--fast) var(--ease-out), border-color var(--fast) var(--ease-out), transform var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
}

.timeline-action:hover {
  color: var(--ink-900);
  transform: translateY(-1px);
  box-shadow: var(--shadow-card);
}

.timeline-action.liked {
  color: var(--brand);
  border-color: rgba(232, 93, 4, 0.15);
  background: var(--brand-light);
}

.timeline-detail-link {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: var(--radius-full);
  background: var(--brand-light);
  color: var(--brand);
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  transition: background var(--fast) var(--ease-out);
}

.timeline-detail-link:hover {
  background: rgba(232, 93, 4, 0.14);
  color: var(--brand);
}

/* ── Comments area ── */
.timeline-comments {
  margin-top: 12px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: var(--bg-muted);
  border: 1px solid var(--ink-100);
}

.timeline-comment {
  display: flex;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
  padding: 6px 0;
}

.timeline-comment-author {
  color: var(--ink-900);
  font-weight: 700;
  flex-shrink: 0;
}

.timeline-comment-text {
  color: var(--ink-500);
}

.timeline-comments-empty {
  color: var(--ink-300);
  font-size: 13px;
  padding: 4px 0;
}

.timeline-comment-input {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.timeline-comment-field {
  flex: 1;
  min-width: 0;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--ink-100);
  background: var(--bg-surface);
  font-size: 13px;
  color: var(--ink-900);
  outline: none;
  font-family: inherit;
  transition: border-color var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
}

.timeline-comment-field:focus {
  border-color: var(--brand);
  box-shadow: 0 0 0 3px var(--brand-light);
}

.timeline-comment-submit {
  flex-shrink: 0;
  padding: 10px 16px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--brand-gradient);
  color: white;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: filter var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.20);
}

.timeline-comment-submit:hover {
  filter: brightness(0.93);
  box-shadow: 0 4px 14px rgba(232, 93, 4, 0.30);
}

.timeline-comment-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.timeline-login-hint {
  margin-top: 12px;
  color: var(--ink-300);
  font-size: 13px;
}

.timeline-login-hint a {
  color: var(--brand);
  text-decoration: none;
  font-weight: 600;
}

/* ── Map markers ── */
:deep(.footprint-marker) {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 700;
  box-shadow: 0 4px 16px rgba(232, 93, 4, 0.25);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .profile-page {
    padding: 16px;
  }

  .profile-header,
  .section-card,
  .empty-state {
    padding: 22px;
  }

  .profile-avatar-section,
  .stats-row,
  .timeline-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .timeline-header-side {
    width: 100%;
    justify-content: space-between;
  }

  .stat-card {
    width: 100%;
  }

  .timeline-comment-input {
    flex-direction: column;
  }

  .timeline-comment-submit {
    width: 100%;
  }
}
</style>
