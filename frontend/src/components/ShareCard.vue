<template>
  <transition name="modal-fade">
    <div class="share-overlay" @click.self="$emit('close')">
      <div class="share-modal">
        <div class="share-modal-top">
          <div class="share-modal-header">
            <div class="share-modal-heading">
              <span class="share-modal-title">生成分享海报</span>
              <span class="share-modal-subtitle">选择本次打卡照片，生成更完整的纪念卡片</span>
            </div>
            <button class="share-modal-close" @click="$emit('close')">✕</button>
          </div>

          <div v-if="photoOptions.length > 1" class="picker-panel">
            <div class="picker-label-row">
              <span class="picker-label">选择海报主图</span>
              <span class="picker-count">{{ selectedPhotoIndex + 1 }} / {{ photoOptions.length }}</span>
            </div>
            <div class="picker-list">
              <button
                v-for="(photo, index) in photoOptions"
                :key="photo.key"
                type="button"
                :class="['picker-thumb', { active: index === selectedPhotoIndex }]"
                @click="selectPhoto(index)"
              >
                <img :src="photo.url" :alt="`打卡照片 ${index + 1}`" crossorigin="anonymous" />
                <span class="picker-thumb-index">{{ index + 1 }}</span>
              </button>
            </div>
          </div>

          <div class="style-panel">
            <div class="style-label-row">
              <span class="picker-label">海报风格</span>
            </div>
            <div class="style-list">
              <button
                type="button"
                :class="['style-chip', { active: posterStyle === 'minimal' }]"
                @click="posterStyle = 'minimal'"
              >
                极简白卡风
              </button>
              <button
                type="button"
                :class="['style-chip', { active: posterStyle === 'magazine' }]"
                @click="posterStyle = 'magazine'"
              >
                旅行杂志风
              </button>
              <button
                type="button"
                :class="['style-chip', { active: posterStyle === 'photo-title' }]"
                @click="posterStyle = 'photo-title'"
              >
                照片压字风
              </button>
              <button
                type="button"
                :class="['style-chip', { active: posterStyle === 'photo-editorial' }]"
                @click="posterStyle = 'photo-editorial'"
              >
                封面压字风
              </button>
            </div>
          </div>
        </div>

        <div class="share-modal-body">
          <div class="share-card-wrap">
            <div ref="cardEl" :class="['share-card', `share-card-${posterStyle}`]">
              <div class="share-card-photo-shell">
                <div class="share-card-photo-frame">
                  <img
                    v-if="selectedPhotoUrl"
                    :key="selectedPhotoUrl"
                    :src="selectedPhotoUrl"
                    class="card-hero-photo"
                    crossorigin="anonymous"
                    @error="handlePhotoError"
                  />
                <div v-else class="card-photo-placeholder">
                  <span class="placeholder-icon">📸</span>
                  <span class="placeholder-copy">这条打卡没有可用照片</span>
                </div>
                <div
                  v-if="posterStyle === 'photo-title' || posterStyle === 'photo-editorial'"
                  :class="['card-photo-text-overlay', `card-photo-text-${posterStyle}`]"
                >
                  <div class="photo-overlay-kicker">{{ displayCity || 'Travel Note' }}</div>
                  <div class="photo-overlay-title">{{ checkin.location_name || '旅行坐标' }}</div>
                  <div v-if="captionText" class="photo-overlay-caption">{{ captionText }}</div>
                </div>
                <div class="card-photo-sheen"></div>
                <div class="card-photo-badge">拾光海报</div>
              </div>
            </div>

              <div class="card-watermark-band">
                <div class="card-watermark-left">
                  <div class="card-user-chip">
                    <div class="card-avatar">{{ userInitial }}</div>
                    <div class="card-user-meta">
                      <span class="card-user-label">{{ posterStyle === 'photo-title' || posterStyle === 'photo-editorial' ? 'Traveler' : 'Share By' }}</span>
                      <span class="card-username">{{ checkin.user_nickname || '旅行者' }}</span>
                    </div>
                  </div>
                </div>
                <div class="card-watermark-divider"></div>
                <div class="card-watermark-right">
                  <span class="card-brand-kicker">{{ posterStyle === 'photo-title' || posterStyle === 'photo-editorial' ? checkinDate : 'Travel Notes' }}</span>
                  <div class="card-brand-chip">
                    <span class="card-brand-mark"></span>
                    <span class="card-brand-name">拾光坐标</span>
                  </div>
                </div>
              </div>

              <div v-if="posterStyle !== 'photo-title' && posterStyle !== 'photo-editorial'" class="card-copy-block">
                <div class="card-copy-kicker">{{ posterKicker }}</div>
                <div class="card-location-row">
                  <div class="card-location-main">{{ checkin.location_name || '旅行坐标' }}</div>
                  <div class="card-date-chip">{{ checkinDate }}</div>
                </div>
                <div class="card-meta-line">
                  <span v-if="displayCity">📍 {{ displayCity }}</span>
                  <span v-if="displayCity && subtitleText" class="meta-dot">·</span>
                  <span v-if="subtitleText">{{ subtitleText }}</span>
                </div>
                <p v-if="captionText" class="card-caption">{{ captionText }}</p>
                <p v-else class="card-caption card-caption-empty">在地图上留下这一刻，把路过的风景认真收藏。</p>
              </div>
            </div>
          </div>

          <p v-if="saveHint" class="save-hint">{{ saveHint }}</p>

          <div class="share-actions">
            <button class="share-save-btn" :disabled="generating" @click="saveCard">
              {{ generating ? '生成中...' : saveLabel }}
            </button>
            <button class="share-cancel-btn" @click="$emit('close')">取消</button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed, ref } from 'vue'
import html2canvas from 'html2canvas'
import { getImageUrl } from '../lib/checkins'
import { normalizeAddressName, normalizeCityName } from '../lib/region'

const props = defineProps({
  checkin: { type: Object, required: true },
})

defineEmits(['close'])

const cardEl = ref(null)
const generating = ref(false)
const saveHint = ref('')
const selectedPhotoIndex = ref(0)
const brokenPhotoKeys = ref(new Set())
const posterStyle = ref('minimal')

const canShareFiles = typeof navigator !== 'undefined'
  && !!navigator.canShare
  && navigator.canShare({ files: [new File([], 'test.png', { type: 'image/png' })] })

const saveLabel = canShareFiles ? '📲 保存到相册' : '⬇ 保存图片'

const photoOptions = computed(() => {
  const items = []

  if (Array.isArray(props.checkin.photos) && props.checkin.photos.length) {
    props.checkin.photos.forEach((photo, index) => {
      if (!photo?.image_url) return
      items.push({
        key: String(photo.id || `photo-${index}`),
        url: getImageUrl(photo.image_url),
      })
    })
  }

  if (!items.length && props.checkin.preview_image_url) {
    items.push({
      key: 'preview-image',
      url: getImageUrl(props.checkin.preview_image_url),
    })
  }

  return items.filter((item) => !brokenPhotoKeys.value.has(item.key))
})

const selectedPhoto = computed(() => photoOptions.value[selectedPhotoIndex.value] || null)
const selectedPhotoUrl = computed(() => selectedPhoto.value?.url || '')

const checkinDate = computed(() => {
  const raw = props.checkin.visit_date || props.checkin.created_at
  if (!raw) return '今日打卡'
  return new Date(raw).toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

function normalizePosterRegion(value) {
  const normalized = normalizeAddressName(value)
  return normalized || ''
}

const displayCity = computed(() => normalizePosterRegion(normalizeCityName(props.checkin.city || '')))
const displayAddress = computed(() => normalizePosterRegion(props.checkin.address || ''))

const subtitleText = computed(() => {
  if (displayAddress.value && displayAddress.value !== displayCity.value) {
    return displayAddress.value
  }
  if (props.checkin.media_type === 'video') {
    return '视频打卡'
  }
  const count = photoOptions.value.length
  return count ? `${count} 张照片` : ''
})

const captionText = computed(() => {
  const text = String(props.checkin.content || '').trim()
  if (!text) return ''
  return text.length > 88 ? `${text.slice(0, 87)}…` : text
})

const posterKicker = computed(() => {
  if (posterStyle.value === 'minimal') return 'Shiguang Coordinate'
  if (posterStyle.value === 'magazine') return 'Travel Issue'
  if (posterStyle.value === 'photo-title') return 'Photo Typography'
  return 'Editorial Cover'
})

const userInitial = computed(() => (props.checkin.user_nickname || '拾').trim().charAt(0).toUpperCase())

function selectPhoto(index) {
  selectedPhotoIndex.value = index
  saveHint.value = ''
}

function handlePhotoError() {
  const key = selectedPhoto.value?.key
  if (!key) return

  const next = new Set(brokenPhotoKeys.value)
  next.add(key)
  brokenPhotoKeys.value = next

  if (selectedPhotoIndex.value >= photoOptions.value.length) {
    selectedPhotoIndex.value = Math.max(0, photoOptions.value.length - 1)
  }
}

async function saveCard() {
  if (!cardEl.value || generating.value) return

  generating.value = true
  saveHint.value = ''

  try {
    const canvas = await html2canvas(cardEl.value, {
      useCORS: true,
      allowTaint: false,
      scale: 3,
      backgroundColor: '#f7f1e8',
      logging: false,
    })

    const filename = `拾光坐标_${props.checkin.location_name || '打卡'}.png`

    if (canShareFiles) {
      const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'))
      const file = new File([blob], filename, { type: 'image/png' })
      try {
        await navigator.share({
          files: [file],
          title: props.checkin.location_name || '拾光坐标',
        })
        return
      } catch (error) {
        if (error.name === 'AbortError') return
      }
    }

    const link = document.createElement('a')
    link.download = filename
    link.href = canvas.toDataURL('image/png')
    link.click()
    saveHint.value = '图片已保存，可在下载文件夹中找到'
  } catch (error) {
    console.error('生成海报失败', error)
    saveHint.value = '生成失败，请重试'
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.share-overlay {
  position: fixed;
  top: 64px;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding:
    max(32px, env(safe-area-inset-top, 0px) + 20px)
    18px
    max(24px, env(safe-area-inset-bottom, 0px) + 16px);
  background: rgba(245, 238, 228, 0.92);
  backdrop-filter: blur(8px);
  -webkit-overflow-scrolling: touch;
}

.share-modal {
  width: 100%;
  max-width: 392px;
  max-height: min(860px, calc(100vh - 24px - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px)));
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  padding: 0;
  border-radius: 28px;
  background: #f7f0e6;
  box-shadow: 0 20px 48px rgba(91, 63, 38, 0.14);
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
}

.share-modal-top {
  margin: 0;
  padding: 20px 18px 10px;
  background: transparent;
  border-bottom: none;
  box-shadow: none;
  flex-shrink: 0;
}

.share-modal-body {
  overflow: visible;
  padding: 0 18px calc(168px + env(safe-area-inset-bottom, 0px));
  background: #f7f0e6;
  -webkit-overflow-scrolling: touch;
}

.share-modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.share-modal-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.share-modal-title {
  color: #2f221b;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.share-modal-subtitle {
  color: rgba(74, 52, 39, 0.68);
  font-size: 12px;
  line-height: 1.5;
}

.share-modal-close {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 999px;
  background: rgba(114, 79, 54, 0.08);
  color: rgba(58, 39, 28, 0.76);
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.share-modal-close:hover {
  background: rgba(114, 79, 54, 0.14);
  color: #2f221b;
  transform: rotate(90deg);
}

.picker-panel {
  margin-bottom: 10px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: none;
}

.picker-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.picker-label {
  color: rgba(61, 42, 30, 0.88);
  font-size: 12px;
  font-weight: 600;
}

.picker-count {
  padding: 4px 10px;
  border-radius: 999px;
  background: #a66a3d;
  color: #fff8f1;
  font-size: 11px;
  font-weight: 700;
}

.picker-list {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.picker-thumb {
  position: relative;
  width: 56px;
  height: 72px;
  padding: 0;
  border-radius: 14px;
  overflow: hidden;
  background: #e8d8c5;
  cursor: pointer;
  flex: 0 0 auto;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.picker-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.picker-thumb.active {
  box-shadow: 0 0 0 2px rgba(200, 137, 84, 0.32);
  transform: translateY(-2px);
}

.picker-thumb-index {
  position: absolute;
  right: 6px;
  bottom: 6px;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(10, 8, 7, 0.68);
  color: #fff8f1;
  font-size: 11px;
  font-weight: 700;
}

.style-panel {
  padding-top: 0;
  margin-bottom: 4px;
}

.style-label-row {
  margin-bottom: 8px;
}

.style-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.style-chip {
  height: 34px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: #efe4d4;
  color: #5b3d2a;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.style-chip.active {
  background: #b87949;
  color: #fff8f1;
}

.style-chip:hover {
  transform: translateY(-1px);
}

.share-card-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}

.share-card {
  width: 320px;
  padding: 12px;
  border-radius: 28px;
  background: #fffaf4;
  box-shadow: 0 18px 42px rgba(91, 63, 38, 0.12);
  color: #33261d;
  font-family: Georgia, 'Times New Roman', 'PingFang SC', 'Hiragino Sans GB', serif;
}

.share-card-minimal {
  background: #fffaf4;
}

.share-card-magazine {
  background: linear-gradient(180deg, #fffaf4 0%, #f2e4d1 100%);
}

.share-card-photo-title {
  background: #fffaf4;
}

.share-card-photo-editorial {
  background: #f7efe4;
}

.share-card-photo-shell {
  padding: 8px;
  border-radius: 20px;
  background: #f1e4d4;
}

.share-card-photo-frame {
  position: relative;
  aspect-ratio: 4 / 4.25;
  overflow: hidden;
  border-radius: 16px;
  background: linear-gradient(145deg, #eadbc8, #d8c2aa);
}

.card-hero-photo {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.card-photo-text-overlay {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  padding: 18px 16px 14px;
  color: #fffaf4;
  background: linear-gradient(180deg, rgba(20, 14, 10, 0) 0%, rgba(20, 14, 10, 0.18) 28%, rgba(20, 14, 10, 0.72) 100%);
}

.card-photo-text-photo-title .photo-overlay-kicker,
.card-photo-text-photo-editorial .photo-overlay-kicker {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  opacity: 0.78;
  margin-bottom: 6px;
}

.card-photo-text-photo-title {
  padding-top: 52px;
}

.card-photo-text-photo-title .photo-overlay-title {
  font-size: 26px;
  line-height: 1.06;
  font-weight: 700;
  max-width: 75%;
  text-wrap: balance;
}

.card-photo-text-photo-title .photo-overlay-caption {
  margin-top: 8px;
  font-size: 11px;
  line-height: 1.5;
  opacity: 0.85;
  max-width: 72%;
}

.card-photo-text-photo-editorial {
  top: 0;
  bottom: 0;
  padding: 44px 16px 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background:
    linear-gradient(180deg, rgba(22, 16, 11, 0.34) 0%, rgba(22, 16, 11, 0.08) 24%, rgba(22, 16, 11, 0.62) 100%);
}

.card-photo-text-photo-editorial .photo-overlay-title {
  font-size: 34px;
  line-height: 0.96;
  font-weight: 700;
  max-width: 68%;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  text-wrap: balance;
}

.card-photo-text-photo-editorial .photo-overlay-caption {
  align-self: flex-end;
  max-width: 52%;
  font-size: 11px;
  line-height: 1.55;
  text-align: right;
  opacity: 0.88;
}

.card-photo-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: rgba(62, 42, 28, 0.72);
  text-align: center;
  padding: 24px;
}

.placeholder-icon {
  font-size: 46px;
}

.placeholder-copy {
  font-size: 14px;
  line-height: 1.6;
}

.card-photo-sheen {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(140deg, rgba(255, 255, 255, 0.28), transparent 24%, transparent 76%, rgba(60, 33, 16, 0.16)),
    linear-gradient(180deg, transparent 62%, rgba(48, 29, 19, 0.1));
  pointer-events: none;
}

.card-photo-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(255, 250, 245, 0.86);
  color: #73492d;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  backdrop-filter: blur(8px);
}

.share-card-magazine .card-photo-badge {
  background: #b87949;
  color: #fff8f1;
}

.share-card-photo-title .card-photo-badge,
.share-card-photo-editorial .card-photo-badge {
  background: rgba(255, 250, 245, 0.18);
  color: #fffaf4;
  border: 1px solid rgba(255, 250, 245, 0.22);
}

.share-card-photo-editorial .card-photo-badge {
  top: 18px;
}

.card-watermark-band {
  margin: 10px 2px 0;
  padding: 10px 12px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: #f8efe4;
}

.share-card-magazine .card-watermark-band {
  background: rgba(255, 248, 241, 0.78);
}

.card-watermark-left,
.card-watermark-right {
  min-width: 0;
  flex: 1;
}

.card-watermark-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 3px;
}

.card-watermark-divider {
  width: 1px;
  align-self: stretch;
  background: linear-gradient(180deg, transparent, rgba(109, 74, 47, 0.22), transparent);
}

.card-user-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.card-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at 30% 30%, rgba(255, 243, 232, 0.28), transparent 38%),
    linear-gradient(135deg, #8d5e3b, #d98c52);
  color: #fffdf9;
  font-size: 13px;
  font-weight: 700;
  text-shadow: 0 1px 2px rgba(63, 35, 14, 0.28);
  flex-shrink: 0;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.22),
    0 8px 18px rgba(104, 63, 31, 0.16);
}

.card-user-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.card-user-label {
  color: rgba(90, 62, 41, 0.54);
  font-size: 8px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.card-username {
  color: #4d3425;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-brand-kicker {
  color: rgba(104, 72, 49, 0.54);
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.card-brand-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #4e3324;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  flex-shrink: 0;
}

.card-brand-mark {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  position: relative;
  display: inline-block;
  flex-shrink: 0;
  background:
    radial-gradient(circle at center, rgba(222, 143, 73, 0.9) 0 28%, transparent 32%),
    radial-gradient(circle at center, transparent 0 52%, rgba(222, 143, 73, 0.6) 56% 62%, transparent 66%);
}

.card-brand-mark::after {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  border: 1px solid rgba(222, 143, 73, 0.35);
}

.card-copy-block {
  margin-top: 12px;
  padding: 14px 14px 13px;
  border-radius: 20px;
  background: #f3e5d5;
}

.share-card-magazine .card-copy-block {
  background: #b87949;
}

.share-card-photo-title .card-copy-block,
.share-card-photo-editorial .card-copy-block {
  background: #f1e3d2;
}

.card-copy-kicker {
  margin-bottom: 8px;
  color: rgba(120, 82, 52, 0.76);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.share-card-magazine .card-copy-kicker {
  color: rgba(255, 241, 230, 0.72);
}

.card-location-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 6px;
}

.card-location-main {
  color: #5c3926;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.22;
  letter-spacing: 0.01em;
}

.share-card-magazine .card-location-main {
  color: #fff8f1;
}

.share-card-photo-title .card-location-main,
.share-card-photo-editorial .card-location-main {
  color: #5c3926;
}

.card-date-chip {
  padding: 6px 8px;
  border-radius: 999px;
  background: #fffaf4;
  color: #8d5a39;
  font-size: 9px;
  font-weight: 700;
  line-height: 1.2;
  text-align: right;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.share-card-magazine .card-date-chip {
  background: rgba(255, 246, 238, 0.16);
  color: #fff4e9;
}

.share-card-photo-title .card-date-chip,
.share-card-photo-editorial .card-date-chip {
  background: #fff8f1;
  color: #8d5a39;
}

.card-meta-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  color: rgba(111, 73, 49, 0.84);
  font-size: 11px;
  line-height: 1.5;
}

.share-card-magazine .card-meta-line {
  color: rgba(255, 240, 230, 0.8);
}

.share-card-photo-title .card-meta-line,
.share-card-photo-editorial .card-meta-line {
  color: rgba(111, 73, 49, 0.84);
}

.meta-dot {
  opacity: 0.4;
}

.card-caption {
  margin: 0;
  color: #5c3926;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.share-card-magazine .card-caption {
  color: #fff7f0;
}

.share-card-photo-title .card-caption,
.share-card-photo-editorial .card-caption {
  color: #5c3926;
}

.card-caption-empty {
  color: rgba(111, 73, 49, 0.6);
}

.share-card-magazine .card-caption-empty {
  color: rgba(255, 239, 227, 0.72);
}

.save-hint {
  margin: 0 0 12px;
  color: rgba(255, 240, 230, 0.72);
  font-size: 11px;
  text-align: center;
}

.share-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  padding-top: 2px;
  justify-content: center;
}

.share-save-btn,
.share-cancel-btn {
  height: 46px;
  border: none;
  border-radius: 14px;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.2s ease, background 0.2s ease;
}

.share-save-btn {
  flex: 0 1 220px;
  background: linear-gradient(135deg, #e0874d, #c96b2d);
  color: #fffaf5;
  box-shadow: 0 14px 28px rgba(192, 102, 42, 0.28);
}

.share-save-btn:disabled {
  opacity: 0.56;
  cursor: not-allowed;
  box-shadow: none;
}

.share-save-btn:not(:disabled):hover,
.share-cancel-btn:hover {
  transform: translateY(-1px);
}

.share-cancel-btn {
  flex: 0 0 92px;
  padding: 0 16px;
  background: rgba(255, 249, 244, 0.14);
  color: #8a6244;
  border: 1px solid rgba(170, 127, 93, 0.16);
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.2s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

@media (max-width: 420px) {
  .share-overlay {
    padding:
      max(20px, env(safe-area-inset-top, 0px) + 12px)
      10px
      max(14px, env(safe-area-inset-bottom, 0px) + 10px);
  }

  .share-modal {
    border-radius: 24px;
    max-height: calc(100vh - 12px - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px));
  }

  .share-modal-top {
    margin-bottom: 0;
    padding: 18px 16px 10px;
  }

  .share-modal-body {
    padding: 0 16px calc(180px + env(safe-area-inset-bottom, 0px));
  }

  .share-card {
    width: min(100%, 320px);
  }

  .card-location-main {
    font-size: 20px;
  }

  .card-photo-text-photo-title .photo-overlay-title {
    font-size: 22px;
  }

  .card-photo-text-photo-title {
    padding-top: 44px;
  }

  .card-photo-text-photo-editorial .photo-overlay-title {
    font-size: 28px;
    max-width: 78%;
  }

  .card-watermark-band {
    padding: 12px 14px;
    gap: 10px;
  }

  .card-brand-chip {
    font-size: 12px;
  }

  .share-actions {
    padding-bottom: 8px;
  }

  .share-save-btn {
    flex-basis: 200px;
  }

}
</style>
