<template>
  <div class="checkin-page">
    <div class="checkin-container animate-fade-in">
      <button class="back-btn" @click="$router.push('/')" id="btn-back">← 返回地图</button>

      <div v-if="!hasCoordinates" class="empty-state glass-card">
        <h1 class="page-title">先选一个位置</h1>
        <p class="page-subtitle">这版打卡必须从地图选点或当前位置定位进入。</p>
        <router-link :to="{ name: 'home', query: { pick: '1' } }" class="btn-primary">
          返回地图选点
        </router-link>
      </div>

      <div v-else class="checkin-card glass-card">
        <h1 class="page-title">✚ 发布打卡</h1>
        <p class="page-subtitle">位置已经固定，接下来填写地点名称、照片和你的旅途感受。</p>

        <div class="location-panel">
          <div class="location-copy">
            <span class="location-badge">{{ sourceLabel }}</span>
            <strong>{{ locationHeadline }}</strong>
            <span v-if="form.address.trim()" class="location-detail">{{ form.address.trim() }}</span>
          </div>
          <div class="location-side">
            <span class="location-tip">已根据你选择的位置自动识别城市与地址。</span>
            <div class="geo-status-row">
              <span :class="['geo-status-pill', locationStatusClass]">{{ locationStatusText }}</span>
              <button
                type="button"
                class="geo-refresh-btn"
                :disabled="resolvingLocation || !hasCoordinates"
                @click="resolveLocationDetails(true)"
              >
                {{ resolvingLocation ? '识别中...' : '重新识别' }}
              </button>
            </div>
          </div>
        </div>

        <el-form :model="form" label-position="top" class="checkin-form">
          <el-form-item label="地点名称">
            <el-input
              v-model="form.location_name"
              placeholder="填写地点名称，如西湖、外滩、天安门"
              maxlength="80"
              clearable
            />
          </el-form-item>

          <el-form-item label="城市">
            <div class="location-readonly">{{ form.city || '识别中...' }}</div>
          </el-form-item>

          <el-form-item label="详细地址">
            <div class="location-readonly">{{ form.address || '识别中...' }}</div>
          </el-form-item>

          <!-- 媒体类型选择 -->
          <el-form-item label="媒体类型">
            <div class="media-type-toggle">
              <button
                type="button"
                :class="['media-type-btn', { active: mediaType === 'photo' }]"
                @click="switchMediaType('photo')"
              >
                <span>📷</span>
                <span>照片</span>
              </button>
              <button
                type="button"
                :class="['media-type-btn', { active: mediaType === 'video' }]"
                @click="switchMediaType('video')"
              >
                <span>🎬</span>
                <span>视频</span>
              </button>
            </div>
          </el-form-item>

          <!-- 照片上传（照片模式） -->
          <el-form-item v-if="mediaType === 'photo'" label="照片（最多9张）">
            <div class="photo-upload-grid">
              <div
                v-for="(file, idx) in fileList"
                :key="idx"
                class="photo-thumb"
              >
                <img
                  v-if="!file.previewError"
                  :src="file.url"
                  :alt="file.name"
                  class="thumb-img"
                  @error="markPreviewError(idx)"
                />
                <div v-else class="thumb-fallback">
                  <span class="thumb-fallback-icon">🖼️</span>
                  <span class="thumb-fallback-text">{{ file.fallbackText || '无法预览' }}</span>
                </div>
                <button type="button" class="thumb-remove" @click="removePhoto(idx)">×</button>
              </div>
              <label v-if="fileList.length < 9" :class="['photo-add-btn', { disabled: processingPhotos }]">
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  style="display:none"
                  :disabled="processingPhotos"
                  @change="handlePhotoInput"
                />
                <span style="font-size:22px">📷</span>
                <span style="font-size:12px;color:#999">{{ processingPhotos ? '处理中...' : '添加照片' }}</span>
              </label>
            </div>
          </el-form-item>

          <!-- 视频上传（视频模式） -->
          <el-form-item v-if="mediaType === 'video'" label="视频（仅限一条）">
            <div class="video-upload-area">
              <div v-if="videoFile" class="video-preview-wrap">
                <video
                  :src="videoPreviewUrl"
                  class="video-preview"
                  controls
                  preload="metadata"
                ></video>
                <div v-if="videoThumbnailUrl" class="video-thumb-hint">
                  <img :src="videoThumbnailUrl" class="video-thumb-img" alt="封面预览" />
                  <span class="video-thumb-label">地图封面（自动提取第一帧）</span>
                </div>
                <button type="button" class="video-remove-btn" @click="removeVideo">移除视频</button>
              </div>
              <label v-else :class="['video-add-btn', { disabled: processingVideo }]">
                <input
                  type="file"
                  accept="video/*"
                  style="display:none"
                  :disabled="processingVideo"
                  @change="handleVideoInput"
                />
                <span style="font-size:32px">🎬</span>
                <span style="font-size:13px;font-weight:600;color:var(--ink-700)">
                  {{ processingVideo ? '处理中...' : '点击上传视频' }}
                </span>
                <span style="font-size:12px;color:var(--ink-300)">支持 MP4、MOV 等格式，最大 200MB</span>
              </label>
            </div>
          </el-form-item>

          <el-form-item label="短评">
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="4"
              placeholder="写下你的感受..."
              id="input-content"
              maxlength="500"
              show-word-limit
            />
          </el-form-item>

          <!-- AI 文案生成 -->
          <div class="ai-panel">
            <div class="ai-header">
              <span class="ai-icon">✨</span>
              <span class="ai-title">智能生成文案</span>
              <button type="button" class="ai-toggle" @click="showAiPanel = !showAiPanel">
                {{ showAiPanel ? '收起' : '展开' }}
              </button>
            </div>

            <div v-if="showAiPanel" class="ai-body">
              <div class="ai-options">
                <div class="option-group">
                  <label>文案类型</label>
                  <div class="option-btns">
                    <button
                      v-for="t in ['旅行文案','生活记录']" :key="t"
                      type="button"
                      :class="['opt-btn', { active: aiType === t }]"
                      @click="aiType = t"
                    >{{ t }}</button>
                  </div>
                </div>
                <div class="option-group">
                  <label>风格</label>
                  <div class="option-btns">
                    <button
                      v-for="s in ['清新风','文艺风','日记风','轻社交风']" :key="s"
                      type="button"
                      :class="['opt-btn', { active: aiStyle === s }]"
                      @click="aiStyle = s"
                    >{{ s }}</button>
                  </div>
                </div>
              </div>

              <div class="ai-actions">
                <button type="button" class="ai-generate-btn" @click="requestAiCaption('generate')" :disabled="aiLoading">
                  {{ aiLoading && aiPendingMode === 'generate' ? (aiCaptions.length ? 'AI 润色中...' : '生成中...') : '✨ 生成新文案' }}
                </button>
                <button
                  type="button"
                  class="ai-polish-btn"
                  @click="requestAiCaption('polish')"
                  :disabled="aiLoading || !hasDraftContent"
                >
                  {{ aiLoading && aiPendingMode === 'polish' ? '润色中...' : '润色当前文案' }}
                </button>
              </div>

              <div v-if="aiStatus" :class="['ai-status', `is-${aiStatusLevel}`]">{{ aiStatus }}</div>
              <div v-if="aiError" class="ai-error">{{ aiError }}</div>

              <div v-if="aiCaptions.length > 0" class="ai-results">
                <p class="ai-results-hint">点击文案一键填入：</p>
                <div
                  v-for="(caption, idx) in aiCaptions" :key="idx"
                  class="ai-caption-item"
                  @click="applyCaption(caption)"
                >{{ caption }}</div>
              </div>

              <div class="ai-credit-row">✨ 由豆包AI生成</div>
            </div>
          </div>

          <el-form-item label="公开展示">
            <div class="public-control">
              <el-switch v-model="form.is_public" id="switch-public" />
              <span class="public-hint">
                {{ form.is_public ? '所有用户（包括未登录）均可在地图上看到' : '仅你自己可见' }}
              </span>
            </div>
          </el-form-item>

          <el-form-item>
            <button
              type="button"
              class="btn-primary submit-btn"
              @click="handleSubmit"
              :disabled="submitting || processingPhotos || processingVideo || !effectiveLocationName"
              id="btn-submit"
            >
              {{ submitting ? (mediaType === 'video' ? '压缩上传中，请稍候...' : '发布中...') : '🚀 发布打卡' }}
            </button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { publishCheckin, generateCaption, reverseGeocodeCheckin } from '../api/checkins'
import { normalizeImageUpload } from '../api/uploads'
import { reverseGeocodeWithAmap } from '../lib/amap'
import { createInstantCaptions } from '../lib/instantCaption'
import { normalizeAddressName, normalizeCityName } from '../lib/region'
import {
  canPreviewFileInBrowser,
  compressImageFile,
  formatImagePreparationError,
  isHeicLikeFile,
  normalizeImageFileForBrowser,
} from '../lib/images'

const route = useRoute()
const router = useRouter()

const form = ref({
  location_name: '',
  city: '',
  address: '',
  latitude: null,
  longitude: null,
  content: '',
  is_public: true,
})

const fileList = ref([])
const submitting = ref(false)
const processingPhotos = ref(false)
const mediaType = ref('photo') // 'photo' | 'video'
const videoFile = ref(null)
const videoPreviewUrl = ref('')
const videoThumbnailUrl = ref('')
const videoThumbnailBlob = ref(null)
const processingVideo = ref(false)

const showAiPanel = ref(false)
const aiLoading = ref(false)
const aiCaptions = ref([])
const aiStyle = ref('清新风')
const aiType = ref('旅行文案')
const aiError = ref('')
const aiStatus = ref('')
const aiStatusLevel = ref('idle')
const aiPendingMode = ref('generate')
const resolvingLocation = ref(false)
const locationResolveError = ref('')
const lastResolvedLocationKey = ref('')

let locationResolveRequestId = 0

const hasCoordinates = computed(() =>
  Number.isFinite(form.value.latitude) && Number.isFinite(form.value.longitude)
)
const hasDraftContent = computed(() => form.value.content.trim().length > 0)
const effectiveLocationName = computed(() =>
  form.value.location_name.trim() || form.value.address.trim() || form.value.city.trim()
)

const sourceLabel = computed(() => {
  if (route.query.source === 'geolocation') return '当前位置定位'
  if (route.query.source === 'search') return '地点搜索'
  return '地图选点'
})

const locationHeadline = computed(() => {
  if (resolvingLocation.value) return '正在识别城市...'
  if (form.value.city.trim()) return form.value.city.trim()
  if (form.value.address.trim()) return form.value.address.trim()
  if (locationResolveError.value) return '暂未识别到城市'
  return '等待位置识别'
})

const locationStatusText = computed(() => {
  if (!hasCoordinates.value) return '等待坐标'
  if (resolvingLocation.value) return '正在识别城市与地址...'
  if (locationResolveError.value) return locationResolveError.value
  if (form.value.city.trim()) return `已自动识别 ${form.value.city.trim()}`
  if (form.value.address.trim()) return '已自动识别详细地址'
  return '将根据坐标自动识别城市'
})

const locationStatusClass = computed(() => {
  if (resolvingLocation.value) return 'is-loading'
  if (locationResolveError.value) return 'is-error'
  if (form.value.city.trim() || form.value.address.trim()) return 'is-ready'
  return 'is-idle'
})

function parseCoordinate(value) {
  const parsed = Number.parseFloat(String(value))
  return Number.isFinite(parsed) ? Number(parsed.toFixed(6)) : null
}

function buildCoordinateKey(latitude, longitude) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return ''
  return `${latitude.toFixed(6)},${longitude.toFixed(6)}`
}

function syncRouteLocation() {
  const nextLatitude = parseCoordinate(route.query.lat)
  const nextLongitude = parseCoordinate(route.query.lng)
  const currentKey = buildCoordinateKey(form.value.latitude, form.value.longitude)
  const nextKey = buildCoordinateKey(nextLatitude, nextLongitude)
  const coordinatesChanged = currentKey !== nextKey

  form.value.latitude = nextLatitude
  form.value.longitude = nextLongitude

  const routeCity = typeof route.query.city === 'string' ? normalizeCityName(route.query.city.trim()) : ''
  const routeAddress = typeof route.query.address === 'string' ? normalizeAddressName(route.query.address.trim()) : ''
  const routeLocationName = typeof route.query.location_name === 'string' ? route.query.location_name.trim() : ''
  const fallbackLocationName = routeLocationName || routeAddress || routeCity

  if (coordinatesChanged) {
    form.value.location_name = fallbackLocationName
    form.value.city = routeCity
    form.value.address = routeAddress
    locationResolveError.value = ''
    lastResolvedLocationKey.value = ''
    return
  }

  if (fallbackLocationName && !form.value.location_name.trim()) {
    form.value.location_name = fallbackLocationName
  }

  if (routeCity && !form.value.city) {
    form.value.city = routeCity
  }

  if (routeAddress && !form.value.address) {
    form.value.address = routeAddress
  }
}

async function resolveLocationDetails(force = false) {
  if (!hasCoordinates.value) return

  const coordinateKey = buildCoordinateKey(form.value.latitude, form.value.longitude)
  if (!coordinateKey) return

  if (!force && lastResolvedLocationKey.value === coordinateKey) return

  const initialCity = form.value.city.trim()
  const initialAddress = form.value.address.trim()
  const requestId = ++locationResolveRequestId

  resolvingLocation.value = true
  locationResolveError.value = ''

  try {
    let res = await reverseGeocodeWithAmap(form.value.latitude, form.value.longitude)
    const missingLocation = !String(res?.city || '').trim() && !String(res?.address || '').trim()
    if (missingLocation) {
      const fallback = await reverseGeocodeCheckin(form.value.latitude, form.value.longitude)
      res = fallback.data || fallback
    }
    if (requestId !== locationResolveRequestId) return

    const detectedCity = typeof res?.city === 'string' ? res.city.trim() : ''
    const detectedAddress = typeof res?.address === 'string' ? res.address.trim() : ''
    const detectedLocationName = detectedAddress || detectedCity

    if (detectedCity && (!form.value.city.trim() || form.value.city.trim() === initialCity || force)) {
      form.value.city = detectedCity
    }

    if (detectedAddress && (!form.value.address.trim() || form.value.address.trim() === initialAddress || force)) {
      form.value.address = detectedAddress
    }

    if (detectedLocationName && (!form.value.location_name.trim() || force)) {
      form.value.location_name = detectedLocationName
    }

    lastResolvedLocationKey.value = coordinateKey

    if (!detectedCity && !detectedAddress) {
      locationResolveError.value = '暂未识别到城市，可手动填写'
    }
  } catch (error) {
    try {
      const fallback = await reverseGeocodeCheckin(form.value.latitude, form.value.longitude)
      if (requestId !== locationResolveRequestId) return
      const detectedCity = typeof fallback?.data?.city === 'string' ? fallback.data.city.trim() : ''
      const detectedAddress = typeof fallback?.data?.address === 'string' ? fallback.data.address.trim() : ''
      const detectedLocationName = detectedAddress || detectedCity

      if (detectedCity && (!form.value.city.trim() || form.value.city.trim() === initialCity || force)) {
        form.value.city = detectedCity
      }

      if (detectedAddress && (!form.value.address.trim() || form.value.address.trim() === initialAddress || force)) {
        form.value.address = detectedAddress
      }

      if (detectedLocationName && (!form.value.location_name.trim() || force)) {
        form.value.location_name = detectedLocationName
      }

      lastResolvedLocationKey.value = coordinateKey

      if (!detectedCity && !detectedAddress) {
        locationResolveError.value = '暂未识别到城市，可手动填写'
      }
    } catch (fallbackError) {
      if (requestId !== locationResolveRequestId) return
      console.error('Reverse geocode failed:', error, fallbackError)
      locationResolveError.value = '暂未识别到城市，可手动填写'
    }
  } finally {
    if (requestId === locationResolveRequestId) {
      resolvingLocation.value = false
    }
  }
}

async function handleSubmit() {
  if (!hasCoordinates.value) {
    ElMessage.warning('请先返回地图选择位置')
    return
  }

  if (!effectiveLocationName.value) {
    ElMessage.warning('请填写地点名称')
    return
  }

  if (mediaType.value === 'video' && !videoFile.value) {
    ElMessage.warning('请选择要上传的视频')
    return
  }

  submitting.value = true
  try {
    const formData = new FormData()
    formData.append('location_name', effectiveLocationName.value)
    formData.append('latitude', String(form.value.latitude))
    formData.append('longitude', String(form.value.longitude))

    if (form.value.city.trim()) formData.append('city', form.value.city.trim())
    if (form.value.address.trim()) formData.append('address', form.value.address.trim())
    if (form.value.content) formData.append('content', form.value.content)
    formData.append('is_public', form.value.is_public ? 'true' : 'false')
    formData.append('media_type', mediaType.value)

    if (mediaType.value === 'video') {
      formData.append('video', videoFile.value)
      // Upload thumbnail (first frame) as the preview photo
      if (videoThumbnailBlob.value) {
        const thumbFile = new File([videoThumbnailBlob.value], 'thumbnail.jpg', { type: 'image/jpeg' })
        formData.append('photos', thumbFile)
      }
    } else {
      fileList.value.forEach((file) => {
        if (file.raw) {
          formData.append('photos', file.raw)
        }
      })
    }

    const res = await publishCheckin(formData)
    ElMessage.success('打卡成功！🎉')
    router.push(`/checkins/${res.data.id}`)
  } catch (err) {
    console.error(err)
    ElMessage.error(err.response?.data?.detail || '发布失败，请重试')
  } finally {
    submitting.value = false
  }
}

async function collectAiImageBase64s() {
  const imageBase64s = []
  for (const file of fileList.value.slice(0, 1)) {
    if (file.raw && !isHeicLikeFile(file.raw)) {
      const b64 = await new Promise((resolve, reject) => {
        const reader = new FileReader()
        reader.onload = (e) => resolve(e.target.result)
        reader.onerror = reject
        reader.readAsDataURL(file.raw)
      })
      imageBase64s.push(b64)
    }
  }

  if (fileList.value.some((file) => file.raw && isHeicLikeFile(file.raw))) {
    ElMessage.info('AI 文案会忽略当前无法本地解析的 HEIC 照片')
  }

  if (fileList.value.length > 1) {
    ElMessage.info('AI 文案当前只使用第一张有效照片，以提升生成稳定性')
  }

  return imageBase64s
}

async function requestAiCaption(mode = 'generate') {
  if (!effectiveLocationName.value) {
    ElMessage.warning('先填写地点名称，再生成文案')
    return
  }
  if (mode === 'polish' && !hasDraftContent.value) {
    ElMessage.warning('先在短评里写一些内容，再进行润色')
    return
  }

  aiLoading.value = true
  aiPendingMode.value = mode
  aiError.value = ''
  const instantCaptions = mode === 'generate'
    ? createInstantCaptions({
      city: form.value.city,
      locationName: effectiveLocationName.value,
      style: aiStyle.value,
      captionType: aiType.value,
    })
    : []

  if (mode === 'generate') {
    aiCaptions.value = instantCaptions
    aiStatus.value = '极速草稿已生成，AI 正在后台润色...'
    aiStatusLevel.value = 'working'
  } else {
    aiCaptions.value = []
    aiStatus.value = '正在基于你已写的内容生成润色版本...'
    aiStatusLevel.value = 'working'
  }
  try {
    const imageBase64s = mode === 'generate' ? await collectAiImageBase64s() : []

    const res = await generateCaption({
      city: form.value.city || '',
      location_name: effectiveLocationName.value || '',
      image_base64s: imageBase64s,
      style: aiStyle.value,
      caption_type: aiType.value,
      mode,
      draft_content: mode === 'polish' ? form.value.content : '',
    })
    const finalCaptions = res.data.captions || []
    if (finalCaptions.length > 0) {
      aiCaptions.value = finalCaptions
      aiStatus.value = mode === 'polish' ? '已生成 2 条润色版本' : '已更新为 AI 润色版'
      aiStatusLevel.value = 'enhanced'
    } else if (instantCaptions.length > 0) {
      aiStatus.value = 'AI 未返回有效结果，当前保留极速草稿'
      aiStatusLevel.value = 'warning'
    } else if (mode === 'polish') {
      aiError.value = '未能生成润色结果，请重试'
      aiStatus.value = ''
      aiStatusLevel.value = 'idle'
    } else {
      aiError.value = '未能生成文案，请重试'
      aiStatus.value = ''
      aiStatusLevel.value = 'idle'
    }
  } catch (e) {
    if (instantCaptions.length > 0) {
      aiStatus.value = 'AI 响应较慢，当前先保留极速草稿'
      aiStatusLevel.value = 'warning'
    } else if (mode === 'polish') {
      aiError.value = e.response?.data?.detail || 'AI润色失败，请重试'
      aiStatus.value = ''
      aiStatusLevel.value = 'idle'
    } else {
      aiError.value = e.response?.data?.detail || 'AI生成失败，请重试'
      aiStatus.value = ''
      aiStatusLevel.value = 'idle'
    }
  } finally {
    aiLoading.value = false
  }
}

function applyCaption(caption) {
  form.value.content = caption
}

function createPhotoItem(file, options = {}) {
  return {
    raw: file,
    url: options.previewError ? '' : URL.createObjectURL(file),
    name: file.name,
    previewError: Boolean(options.previewError),
    fallbackText: options.fallbackText || '',
  }
}

function createFileFromNormalizedBlob(sourceFile, blob, extensionHeader) {
  const rawExtension = String(extensionHeader || '').trim().toLowerCase()
  const normalizedExtension = rawExtension.startsWith('.')
    ? rawExtension
    : (rawExtension ? `.${rawExtension}` : '.jpg')
  const baseName = (sourceFile.name || 'photo').replace(/\.[^.]+$/, '')

  return new File([blob], `${baseName || 'photo'}${normalizedExtension}`, {
    type: blob.type || 'image/jpeg',
    lastModified: sourceFile.lastModified || Date.now(),
  })
}

async function normalizeImageFileViaServer(sourceFile) {
  const response = await normalizeImageUpload(sourceFile)
  const extension = response.headers?.['x-normalized-extension']
  return createFileFromNormalizedBlob(sourceFile, response.data, extension)
}

async function handlePhotoInput(event) {
  const files = Array.from(event.target.files || [])
  if (!files.length) {
    event.target.value = ''
    return
  }

  processingPhotos.value = true
  try {
    for (const sourceFile of files) {
      if (fileList.value.length >= 9) break
      try {
        const normalizedFile = await normalizeImageFileForBrowser(sourceFile)
        const preparedFile = await compressImageFile(normalizedFile)
        fileList.value.push(createPhotoItem(preparedFile))
      } catch (error) {
        console.error('Photo preprocessing failed:', error)

        if (isHeicLikeFile(sourceFile)) {
          try {
            const serverNormalizedFile = await normalizeImageFileViaServer(sourceFile)
            const serverPreparedFile = await compressImageFile(serverNormalizedFile)
            fileList.value.push(createPhotoItem(serverPreparedFile))
            ElMessage.info('已通过服务端转换 HEIC，当前可直接预览')
            continue
          } catch (serverError) {
            console.error('Server-side photo preprocessing failed:', serverError)
            const fallbackText = canPreviewFileInBrowser(sourceFile) ? '无法预览' : 'HEIC 待上传'
            fileList.value.push(createPhotoItem(sourceFile, { previewError: true, fallbackText }))
            ElMessage.warning(`${formatImagePreparationError(error)}，已保留原图并会在上传后转换`)
            continue
          }
        }

        throw error
      }
    }
  } catch (error) {
    console.error('Photo preprocessing failed:', error)
    ElMessage.error(`${formatImagePreparationError(error)}，请换一张图片重试`)
  } finally {
    processingPhotos.value = false
    event.target.value = ''
  }
}

function markPreviewError(idx) {
  const file = fileList.value[idx]
  if (!file) return
  file.previewError = true
}

function removePhoto(idx) {
  const file = fileList.value[idx]
  if (file.url?.startsWith('blob:')) URL.revokeObjectURL(file.url)
  fileList.value.splice(idx, 1)
}

function switchMediaType(type) {
  if (mediaType.value === type) return
  mediaType.value = type
  // Clear the other type's data
  if (type === 'photo') {
    removeVideo()
  } else {
    fileList.value.forEach((f) => { if (f.url?.startsWith('blob:')) URL.revokeObjectURL(f.url) })
    fileList.value = []
  }
}

function removeVideo() {
  if (videoPreviewUrl.value?.startsWith('blob:')) URL.revokeObjectURL(videoPreviewUrl.value)
  if (videoThumbnailUrl.value?.startsWith('blob:')) URL.revokeObjectURL(videoThumbnailUrl.value)
  videoFile.value = null
  videoPreviewUrl.value = ''
  videoThumbnailUrl.value = ''
  videoThumbnailBlob.value = null
}

async function extractVideoFirstFrame(file) {
  return new Promise((resolve) => {
    const video = document.createElement('video')
    const url = URL.createObjectURL(file)
    video.preload = 'metadata'
    video.muted = true
    video.src = url

    const cleanup = () => URL.revokeObjectURL(url)

    video.addEventListener('loadeddata', () => {
      video.currentTime = 0
    })

    video.addEventListener('seeked', () => {
      try {
        const canvas = document.createElement('canvas')
        canvas.width = Math.min(video.videoWidth, 800)
        canvas.height = Math.round(video.videoHeight * (canvas.width / video.videoWidth))
        const ctx = canvas.getContext('2d')
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        canvas.toBlob((blob) => {
          cleanup()
          resolve(blob)
        }, 'image/jpeg', 0.8)
      } catch {
        cleanup()
        resolve(null)
      }
    }, { once: true })

    video.addEventListener('error', () => {
      cleanup()
      resolve(null)
    }, { once: true })

    // Trigger seek after a short delay to ensure video is ready
    setTimeout(() => { video.currentTime = 0.001 }, 100)
  })
}

async function handleVideoInput(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return

  const maxSize = 200 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('视频文件不能超过 200MB')
    return
  }

  processingVideo.value = true
  try {
    videoFile.value = file
    videoPreviewUrl.value = URL.createObjectURL(file)

    // Extract first frame as thumbnail
    const thumbBlob = await extractVideoFirstFrame(file)
    if (thumbBlob) {
      videoThumbnailBlob.value = thumbBlob
      videoThumbnailUrl.value = URL.createObjectURL(thumbBlob)
    }
  } catch (err) {
    console.error('Video processing failed:', err)
    ElMessage.warning('视频已选择，但封面提取失败，地图将不显示预览图')
  } finally {
    processingVideo.value = false
  }
}

watch(
  () => route.query,
  async () => {
    syncRouteLocation()

    if (hasCoordinates.value && (!form.value.city.trim() || !form.value.address.trim())) {
      await resolveLocationDetails()
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.checkin-page {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  background: var(--bg-base);
}

.checkin-container {
  max-width: 620px;
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

.checkin-card,
.empty-state {
  padding: 32px;
  position: relative;
}

/* ── Location panel ── */
.location-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  margin-bottom: 24px;
  border-radius: var(--radius-md);
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.12);
}

.location-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.location-badge {
  display: inline-flex;
  width: fit-content;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--brand-gradient);
  color: white;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.location-tip {
  color: var(--ink-300);
  font-size: 13px;
  max-width: 210px;
  line-height: 1.5;
}

.location-detail {
  color: var(--ink-500);
  font-size: 13px;
  line-height: 1.5;
  max-width: 320px;
}

.location-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.geo-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.geo-status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
  transition: all 0.25s ease;
}

.geo-status-pill.is-idle {
  color: var(--ink-300);
  background: var(--bg-muted);
}

.geo-status-pill.is-loading {
  color: var(--brand);
  background: var(--brand-light);
}

.geo-status-pill.is-ready {
  color: var(--success);
  background: rgba(45, 155, 111, 0.10);
}

.geo-status-pill.is-error {
  color: var(--error);
  background: rgba(217, 79, 61, 0.08);
}

.geo-refresh-btn {
  border: none;
  background: var(--bg-surface);
  color: var(--brand);
  border-radius: var(--radius-full);
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: transform var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
  box-shadow: var(--shadow-card);
}

.geo-refresh-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-float);
}

.geo-refresh-btn:disabled {
  opacity: 0.55;
  cursor: progress;
  transform: none;
}

/* ── Page title ── */
.page-title {
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 6px;
  letter-spacing: -0.03em;
  color: var(--ink-900);
}

.page-subtitle {
  font-size: 14px;
  color: var(--ink-300);
  margin-bottom: 28px;
  line-height: 1.5;
}

/* ── Form overrides ── */
.checkin-form :deep(.el-form-item__label) {
  color: var(--ink-500);
  font-weight: 600;
  font-size: 13px;
}

.checkin-form :deep(.el-input__wrapper) {
  border-radius: var(--radius-sm) !important;
  border: 1.5px solid var(--ink-100) !important;
  box-shadow: none !important;
  background: var(--bg-muted) !important;
  transition: border-color var(--fast) var(--ease-out) !important;
}

.checkin-form :deep(.el-input__wrapper:hover) {
  border-color: var(--ink-300) !important;
  background: var(--bg-hover) !important;
}

.checkin-form :deep(.el-input__wrapper.is-focus) {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px var(--brand-light) !important;
  background: var(--bg-surface) !important;
}

.checkin-form :deep(.el-textarea__inner) {
  border-radius: var(--radius-sm) !important;
  border: 1.5px solid var(--ink-100) !important;
  box-shadow: none !important;
  background: var(--bg-muted) !important;
  transition: border-color var(--fast) var(--ease-out) !important;
  padding: 14px 16px !important;
}

.checkin-form :deep(.el-textarea__inner:hover) {
  border-color: var(--ink-300) !important;
}

.checkin-form :deep(.el-textarea__inner:focus) {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px var(--brand-light) !important;
  background: var(--bg-surface) !important;
}

.full-width {
  width: 100%;
}

.location-readonly {
  width: 100%;
  padding: 9px 13px;
  border-radius: var(--radius-sm);
  background: var(--bg-muted);
  border: 1.5px solid var(--ink-100);
  font-size: 14px;
  color: var(--ink-700);
  line-height: 1.5;
  min-height: 38px;
}

/* ── Photo upload ── */
.photo-upload-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.photo-thumb {
  position: relative;
  width: 90px;
  height: 90px;
  border-radius: var(--radius-sm);
  overflow: visible;
  transition: transform var(--normal) var(--ease-out);
}

.photo-thumb:hover {
  transform: scale(1.03);
}

.thumb-img {
  width: 90px;
  height: 90px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  display: block;
  border: 1.5px solid var(--ink-100);
  box-shadow: var(--shadow-card);
}

.thumb-fallback {
  width: 90px;
  height: 90px;
  border-radius: var(--radius-sm);
  border: 1.5px solid var(--ink-100);
  background: var(--bg-muted);
  color: var(--ink-300);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.thumb-fallback-icon { font-size: 20px; }
.thumb-fallback-text { font-size: 11px; }

.thumb-remove {
  position: absolute;
  top: -7px;
  right: -7px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--error);
  color: white;
  border: 2px solid white;
  cursor: pointer;
  font-size: 12px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  z-index: 1;
  box-shadow: 0 2px 6px rgba(217, 79, 61, 0.30);
  transition: transform var(--fast) var(--ease-out);
}

.thumb-remove:hover {
  transform: scale(1.15);
}

.photo-add-btn {
  width: 90px;
  height: 90px;
  border: 2px dashed rgba(232, 93, 4, 0.20);
  border-radius: var(--radius-sm);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  background: var(--brand-light);
  transition: border-color var(--fast) var(--ease-out), background var(--fast) var(--ease-out);
}

.photo-add-btn:hover {
  border-color: var(--brand);
  background: rgba(232, 93, 4, 0.08);
}

.photo-add-btn.disabled {
  opacity: 0.55;
  cursor: progress;
  pointer-events: none;
}

/* ── Media type toggle ── */
.media-type-toggle {
  display: flex;
  gap: 10px;
}

.media-type-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 20px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: background var(--fast), color var(--fast), border-color var(--fast);
}

.media-type-btn.active {
  background: var(--brand-light);
  color: var(--brand);
  border-color: rgba(232, 93, 4, 0.35);
}

.media-type-btn:hover:not(.active) {
  background: var(--bg-hover);
  color: var(--ink-900);
}

/* ── Video upload ── */
.video-upload-area {
  width: 100%;
}

.video-add-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  min-height: 160px;
  border: 2px dashed rgba(232, 93, 4, 0.25);
  border-radius: var(--radius-md);
  background: var(--bg-muted);
  cursor: pointer;
  padding: 24px;
  transition: border-color var(--fast), background var(--fast);
  box-sizing: border-box;
}

.video-add-btn:hover {
  border-color: var(--brand);
  background: rgba(232, 93, 4, 0.04);
}

.video-add-btn.disabled {
  opacity: 0.55;
  cursor: progress;
  pointer-events: none;
}

.video-preview-wrap {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.video-preview {
  width: 100%;
  max-height: 280px;
  border-radius: var(--radius-md);
  background: #000;
  display: block;
}

.video-thumb-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.12);
}

.video-thumb-img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: var(--radius-sm);
  flex-shrink: 0;
}

.video-thumb-label {
  font-size: 12px;
  color: var(--ink-500);
}

.video-remove-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border: 1px solid rgba(255, 45, 85, 0.25);
  border-radius: var(--radius-full);
  background: rgba(255, 45, 85, 0.06);
  color: var(--pink, #ff2d55);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  width: fit-content;
  transition: background var(--fast), border-color var(--fast);
}

.video-remove-btn:hover {
  background: rgba(255, 45, 85, 0.12);
  border-color: rgba(255, 45, 85, 0.45);
}

/* ── Public control ── */
.public-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.public-hint {
  font-size: 13px;
  color: var(--ink-300);
}

/* ── Submit ── */
.submit-btn {
  width: 100%;
  padding: 16px;
  font-size: 16px;
  border-radius: var(--radius-md);
  font-family: var(--font-body);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── AI panel ── */
.ai-panel {
  border: 1px solid rgba(232, 93, 4, 0.14);
  border-radius: var(--radius-md);
  padding: 16px 18px;
  margin: 16px 0;
  background: var(--brand-light);
}

.ai-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-icon { font-size: 16px; }

.ai-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--ink-900);
  flex: 1;
  font-family: var(--font-body);
}

.ai-toggle {
  background: transparent;
  border: 1.5px solid rgba(232, 93, 4, 0.30);
  color: var(--brand);
  padding: 4px 12px;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
  font-family: inherit;
  transition: background var(--fast) var(--ease-out), border-color var(--fast) var(--ease-out);
}

.ai-toggle:hover {
  background: rgba(232, 93, 4, 0.08);
  border-color: rgba(232, 93, 4, 0.50);
}

.ai-body { margin-top: 14px; }

.ai-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
}

.option-group label {
  font-size: 12px;
  color: var(--ink-500);
  margin-bottom: 6px;
  display: block;
  font-weight: 600;
}

.option-btns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.opt-btn {
  padding: 5px 12px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-full);
  background: var(--bg-surface);
  cursor: pointer;
  font-size: 12px;
  color: var(--ink-500);
  font-weight: 500;
  font-family: inherit;
  transition: border-color var(--fast) var(--ease-out), color var(--fast) var(--ease-out), background var(--fast) var(--ease-out);
}

.opt-btn:hover {
  border-color: rgba(232, 93, 4, 0.25);
  background: var(--brand-light);
}

.opt-btn.active {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-light);
  font-weight: 700;
}

.ai-actions {
  display: flex;
  gap: 8px;
}

.ai-credit-row {
  margin-top: 10px;
  font-size: 11px;
  color: var(--ink-300);
  font-weight: 500;
  text-align: right;
}

.ai-generate-btn {
  flex: 1;
  padding: 12px;
  background: var(--brand-gradient);
  color: var(--ink-900);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  transition: filter var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out), transform var(--fast) var(--ease-out);
  box-shadow: 0 4px 12px rgba(232, 93, 4, 0.22);
}

.ai-generate-btn:hover:not(:disabled) {
  filter: brightness(0.93);
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(232, 93, 4, 0.30);
}

.ai-generate-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  box-shadow: none;
}

.ai-polish-btn {
  flex: 1;
  padding: 12px;
  background: var(--bg-surface);
  color: var(--brand);
  border: 1.5px solid rgba(232, 93, 4, 0.22);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  transition: background var(--fast) var(--ease-out), border-color var(--fast) var(--ease-out);
}

.ai-polish-btn:hover:not(:disabled) {
  background: var(--brand-light);
  border-color: rgba(232, 93, 4, 0.40);
}

.ai-polish-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ai-status {
  margin-top: 10px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  line-height: 1.6;
  font-weight: 500;
}

.ai-status.is-working {
  color: var(--brand);
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.12);
}

.ai-status.is-enhanced {
  color: var(--success);
  background: rgba(45, 155, 111, 0.06);
  border: 1px solid rgba(45, 155, 111, 0.12);
}

.ai-status.is-warning {
  color: var(--warning);
  background: rgba(232, 161, 0, 0.06);
  border: 1px solid rgba(232, 161, 0, 0.12);
}

.ai-error {
  color: var(--error);
  font-size: 12px;
  margin-top: 8px;
  font-weight: 500;
}

.ai-results { margin-top: 14px; }

.ai-results-hint {
  font-size: 12px;
  color: var(--ink-300);
  margin-bottom: 10px;
}

.ai-caption-item {
  padding: 12px 14px;
  background: var(--bg-surface);
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ink-700);
  cursor: pointer;
  transition: border-color var(--fast) var(--ease-out), background var(--fast) var(--ease-out), transform var(--fast) var(--ease-out), box-shadow var(--fast) var(--ease-out);
}

.ai-caption-item:hover {
  border-color: rgba(232, 93, 4, 0.25);
  background: var(--brand-light);
  transform: translateY(-1px);
  box-shadow: var(--shadow-card);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .checkin-page {
    padding: 16px;
  }

  .checkin-card,
  .empty-state {
    padding: 22px;
  }

  .location-panel {
    flex-direction: column;
  }

  .location-side,
  .geo-status-row {
    align-items: flex-start;
    justify-content: flex-start;
  }

  .ai-actions {
    flex-direction: column;
  }
}
</style>
