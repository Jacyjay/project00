<template>
  <div
    class="messages-page"
    :style="isMobile ? { '--input-bottom': inputBottomCSS } : {}"
  >
    <!-- Sidebar: conversation list -->
    <div class="sidebar" :class="{ 'sidebar-hidden': activePartnerId && isMobile }">
      <div class="sidebar-header">
        <h2 class="sidebar-title">私信</h2>
        <span v-if="totalUnread" class="unread-badge">{{ totalUnread }}</span>
      </div>

      <div v-if="loadingConversations" class="sidebar-loading">
        <div class="loading-spinner"></div>
      </div>

      <div v-else-if="conversations.length === 0" class="sidebar-empty">
        <p>还没有私信</p>
        <p class="hint-text">在用户主页点击「发私信」开始聊天</p>
      </div>

      <div v-else class="conversation-list">
        <button
          v-for="conv in conversations"
          :key="conv.partner_id"
          class="conv-item"
          :class="{ active: activePartnerId === conv.partner_id }"
          @click="openConversation(conv.partner_id)"
        >
          <div class="conv-avatar">{{ conv.partner_nickname?.charAt(0) || '?' }}</div>
          <div class="conv-info">
            <div class="conv-name">{{ conv.partner_nickname }}</div>
            <div class="conv-last">{{ conv.last_message }}</div>
          </div>
          <div class="conv-meta">
            <span class="conv-time">{{ formatDate(conv.last_message_time) }}</span>
            <span v-if="conv.unread_count" class="conv-unread">{{ conv.unread_count }}</span>
          </div>
        </button>
      </div>
    </div>

    <!-- Chat panel -->
    <div class="chat-panel" :class="{ 'chat-active': activePartnerId }">
      <template v-if="activePartnerId">
        <div class="chat-header">
          <button v-if="isMobile" class="back-btn" @click="activePartnerId = null">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M12 15L7 10L12 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
          <div class="chat-partner-avatar">{{ partnerName?.charAt(0) || '?' }}</div>
          <div class="chat-partner-info">
            <div class="chat-partner-name">{{ partnerName }}</div>
            <router-link :to="`/profile/${activePartnerId}`" class="chat-partner-link">查看主页</router-link>
          </div>
        </div>

        <!-- Messages list — on mobile, padding-bottom reserves space for the fixed input bar -->
        <div
          class="messages-list"
          ref="messagesContainer"
          :style="isMobile ? { paddingBottom: msgListPadding } : {}"
        >
          <div v-if="loadingMessages" class="msg-loading">
            <div class="loading-spinner"></div>
          </div>

          <div v-else-if="messages.length === 0" class="msg-empty">
            <p>开始你们的对话吧 ✨</p>
          </div>

          <template v-else>
            <div
              v-for="msg in messages"
              :key="msg.id"
              class="msg-bubble-wrap"
              :class="Number(msg.sender_id) === Number(userStore.userId) ? 'msg-self' : 'msg-other'"
            >
              <div class="msg-bubble">
                <div class="msg-text">{{ msg.content }}</div>
                <div class="msg-time">{{ formatTime(msg.created_at) }}</div>
              </div>
            </div>
          </template>
        </div>

        <!-- Input bar — fixed on mobile, normal flow on desktop -->
        <div class="chat-input-area" ref="inputAreaRef">
          <div class="input-inner">
            <textarea
              ref="textareaRef"
              v-model="inputText"
              class="msg-textarea"
              placeholder="输入消息…"
              rows="1"
              @keydown.enter.exact.prevent="sendMsg"
              @keydown.enter.shift.exact="inputText += '\n'"
              @focus="onInputFocus"
              @blur="onInputBlur"
              @input="autoResizeTextarea"
            ></textarea>
            <button
              class="btn-send"
              :disabled="!inputText.trim() || sending"
              @click="sendMsg"
              :title="sending ? '发送中…' : '发送'"
            >
              <svg v-if="!sending" width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M2 9L16 9M10 3L16 9L10 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <div v-else class="send-spinner"></div>
            </button>
          </div>
        </div>
      </template>

      <div v-else class="chat-empty">
        <div class="chat-empty-icon">💬</div>
        <p class="chat-empty-title">选择一个对话</p>
        <p class="chat-empty-hint">在左侧选择联系人，或在用户主页点击「发私信」开始新对话</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getConversations, getMessages, sendMessage } from '../api/messages'
import { useUserStore } from '../stores/user'

const props = defineProps({ partnerId: [String, Number] })
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const conversations = ref([])
const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const loadingConversations = ref(true)
const loadingMessages = ref(false)
const activePartnerId = ref(props.partnerId ? Number(props.partnerId) : null)
const messagesContainer = ref(null)
const inputAreaRef = ref(null)
const textareaRef = ref(null)
const isMobile = ref(window.innerWidth < 768)
const BEIJING_TIME_ZONE = 'Asia/Shanghai'

// ─── Keyboard / viewport tracking ──────────────────────────────────────────

// Height of bottom dock nav (measured on mount so we include env(safe-area-inset-bottom))
let dockHeight = 96

// Current keyboard height in px (0 when keyboard closed)
const keyboardHeight = ref(0)

// Current input bar height in px (updates as textarea grows)
const inputAreaHeight = ref(64)

/**
 * CSS value for the input bar's `bottom` property.
 * • Keyboard closed → sit above the dock nav pill
 * • Keyboard open   → sit just above the keyboard
 */
const inputBottomCSS = computed(() => {
  if (keyboardHeight.value > 50) {
    return `${keyboardHeight.value}px`
  }
  // Use a CSS calc so env(safe-area-inset-bottom) is honoured by the browser.
  // dockHeight already includes the safe-area pixels (measured on mount).
  return `${dockHeight}px`
})

/**
 * Padding-bottom for the messages list so the last bubble is not hidden
 * behind the fixed input bar.
 */
const msgListPadding = computed(() => `${inputAreaHeight.value + 12}px`)

function handleViewportResize() {
  if (!window.visualViewport || !isMobile.value) return
  const vv = window.visualViewport
  // Works on both iOS (offsetTop shifts) and Android (height shrinks)
  const kbh = Math.max(0, Math.round(window.innerHeight - vv.offsetTop - vv.height))
  const prev = keyboardHeight.value
  keyboardHeight.value = kbh

  // After keyboard appears, scroll chat to bottom so newest message stays visible
  if (kbh > 50 && prev <= 50) {
    nextTick(() => scrollToBottom())
  }

  // Keep input area height in sync
  if (inputAreaRef.value) {
    inputAreaHeight.value = inputAreaRef.value.offsetHeight
  }
}

function measureDockHeight() {
  // Create a sentinel element with the same bottom offset as the dock nav,
  // then read its computed pixel height so env(safe-area-inset-bottom) is included.
  const el = document.createElement('div')
  // bottom-dock on mobile: bottom: calc(14px + env(safe-area-inset-bottom)), height ~52px
  // We need to clear the whole pill — add a generous buffer.
  el.style.cssText =
    'position:fixed;width:1px;pointer-events:none;opacity:0;' +
    'height:calc(14px + env(safe-area-inset-bottom, 0px) + 62px)'
  document.body.appendChild(el)
  dockHeight = Math.ceil(el.getBoundingClientRect().height) || 96
  document.body.removeChild(el)
}

// ─── Textarea auto-resize ────────────────────────────────────────────────────

function autoResizeTextarea() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  // Re-measure input bar height after resize
  nextTick(() => {
    if (inputAreaRef.value) {
      inputAreaHeight.value = inputAreaRef.value.offsetHeight
    }
  })
}

function resetTextareaHeight() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
}

function onInputFocus() {
  if (!isMobile.value) return
  // A brief delay lets the browser finish showing the keyboard before we scroll
  setTimeout(() => scrollToBottom(), 350)
}

function onInputBlur() {
  // When keyboard dismisses on iOS, visualViewport fires resize — nothing extra needed
}

// ─── Utilities ───────────────────────────────────────────────────────────────

const totalUnread = computed(() =>
  conversations.value.reduce((sum, c) => sum + c.unread_count, 0)
)

const partnerName = computed(() => {
  const conv = conversations.value.find((c) => c.partner_id === activePartnerId.value)
  return conv?.partner_nickname || ''
})

function formatDate(dateStr) {
  const d = parseServerDate(dateStr)
  if (!d) return ''
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: BEIJING_TIME_ZONE, month: 'numeric', day: 'numeric',
  }).format(d)
}

function formatTime(dateStr) {
  const d = parseServerDate(dateStr)
  if (!d) return ''
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: BEIJING_TIME_ZONE, hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(d)
}

function parseServerDate(value) {
  if (!value) return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  const raw = String(value).trim()
  if (!raw) return null
  const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T')
  const hasTimezone = /([zZ]|[+-]\d{2}:\d{2})$/.test(normalized)
  const parsed = new Date(hasTimezone ? normalized : `${normalized}Z`)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

// ─── Data loading ─────────────────────────────────────────────────────────────

async function loadConversations() {
  loadingConversations.value = true
  try {
    const res = await getConversations()
    conversations.value = res.data
  } catch (err) {
    console.error(err)
  } finally {
    loadingConversations.value = false
  }
}

async function loadMessages(partnerId) {
  loadingMessages.value = true
  try {
    const res = await getMessages(partnerId)
    messages.value = res.data
    await nextTick()
    scrollToBottom()
    const conv = conversations.value.find((c) => c.partner_id === partnerId)
    if (conv) conv.unread_count = 0
  } catch (err) {
    console.error(err)
    ElMessage.error('加载消息失败')
  } finally {
    loadingMessages.value = false
  }
}

function scrollToBottom() {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

async function openConversation(partnerId) {
  activePartnerId.value = partnerId
  router.replace({ name: 'chat', params: { partnerId } })
  await loadMessages(partnerId)
}

async function sendMsg() {
  const content = inputText.value.trim()
  if (!content || sending.value) return
  sending.value = true
  try {
    const res = await sendMessage(activePartnerId.value, content)
    messages.value.push(res.data)
    inputText.value = ''
    resetTextareaHeight()
    await nextTick()
    scrollToBottom()
    await loadConversations()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '发送失败')
  } finally {
    sending.value = false
  }
}

function handleResize() {
  isMobile.value = window.innerWidth < 768
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(async () => {
  measureDockHeight()
  await loadConversations()
  if (activePartnerId.value) {
    await loadMessages(activePartnerId.value)
  }
  window.addEventListener('resize', handleResize)
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', handleViewportResize)
    window.visualViewport.addEventListener('scroll', handleViewportResize)
  }
  // Initial input bar height measurement
  await nextTick()
  if (inputAreaRef.value) {
    inputAreaHeight.value = inputAreaRef.value.offsetHeight
  }
})

watch(
  () => props.partnerId,
  async (id) => {
    if (id) {
      activePartnerId.value = Number(id)
      await loadMessages(Number(id))
    }
  }
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (window.visualViewport) {
    window.visualViewport.removeEventListener('resize', handleViewportResize)
    window.visualViewport.removeEventListener('scroll', handleViewportResize)
  }
})
</script>

<style scoped>
.messages-page {
  height: 100%;
  display: flex;
  gap: 0;
  background: var(--bg-base);
  overflow: hidden;
}

/* ── Sidebar ── */
.sidebar {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--ink-100);
  background: var(--bg-surface);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--ink-100);
  flex-shrink: 0;
}

.sidebar-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--ink-900);
}

.unread-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: var(--radius-full);
  background: var(--error);
  color: white;
  font-size: 11px;
  font-weight: 700;
}

.sidebar-loading,
.sidebar-empty {
  padding: 32px 20px;
  text-align: center;
  color: var(--ink-300);
  font-size: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hint-text {
  font-size: 12px;
  color: var(--ink-300);
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: background var(--fast) var(--ease-out);
  border-radius: var(--radius-sm);
}

.conv-item:hover { background: var(--bg-hover); }
.conv-item.active { background: var(--brand-light); }

.conv-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  font-weight: 700;
  color: var(--ink-900);
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(232, 93, 4, 0.18);
}

.conv-info { flex: 1; min-width: 0; }

.conv-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-900);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-last {
  font-size: 12px;
  color: var(--ink-300);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-top: 2px;
}

.conv-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.conv-time { font-size: 11px; color: var(--ink-300); }

.conv-unread {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: var(--radius-full);
  background: var(--brand-gradient);
  color: white;
  font-size: 10px;
  font-weight: 700;
}

/* ── Chat panel ── */
.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--ink-100);
  flex-shrink: 0;
  background: var(--bg-surface);
}

.back-btn {
  background: none;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  cursor: pointer;
  color: var(--ink-500);
  border-radius: var(--radius-sm);
  transition: background var(--fast) var(--ease-out), color var(--fast) var(--ease-out);
}

.back-btn:hover { background: var(--bg-muted); color: var(--brand); }

.chat-partner-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--brand-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.18);
}

.chat-partner-info { flex: 1; }

.chat-partner-name {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.02em;
}

.chat-partner-link {
  font-size: 12px;
  color: var(--brand);
  text-decoration: none;
  font-weight: 500;
}

.chat-partner-link:hover {
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* ── Messages list ── */
.messages-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  /* Smooth scroll for programmatic scrollToBottom */
  scroll-behavior: smooth;
}

.msg-loading,
.msg-empty {
  text-align: center;
  color: var(--ink-300);
  font-size: 14px;
  padding: 40px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.msg-bubble-wrap {
  display: flex;
  animation: msgSlideIn 0.22s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes msgSlideIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

.msg-self  { justify-content: flex-end; }
.msg-other { justify-content: flex-start; }

.msg-bubble {
  max-width: 68%;
  padding: 10px 15px;
  border-radius: 18px;
  position: relative;
}

.msg-self .msg-bubble {
  background: var(--brand-gradient);
  color: var(--ink-900);
  border-bottom-right-radius: 5px;
  box-shadow: 0 3px 10px rgba(232, 93, 4, 0.20);
}

.msg-other .msg-bubble {
  background: var(--bg-surface);
  color: var(--ink-900);
  border: 1px solid var(--ink-100);
  border-bottom-left-radius: 5px;
  box-shadow: var(--shadow-card);
}

.msg-text {
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

.msg-time {
  font-size: 10px;
  margin-top: 4px;
  opacity: 0.5;
  text-align: right;
}

/* ── Input bar ──────────────────────────────────────────────────────────────
   Desktop: normal flex child at the bottom of .chat-panel
   Mobile:  position:fixed, bottom controlled by --input-bottom CSS variable
            set from JS via visualViewport measurements
   ────────────────────────────────────────────────────────────────────────── */
.chat-input-area {
  flex-shrink: 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--ink-100);
  padding: 10px 14px;
  /* Prevent tap highlight on mobile */
  -webkit-tap-highlight-color: transparent;
}

/* Wrapper that holds textarea + send button side-by-side */
.input-inner {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--bg-base);
  border: 2px solid var(--ink-200, #d0c5bd);
  border-radius: 22px;
  padding: 8px 8px 8px 16px;
  transition: border-color 180ms var(--ease-out), box-shadow 180ms var(--ease-out);
}

.input-inner:focus-within {
  border-color: var(--brand);
  box-shadow: 0 0 0 4px var(--brand-light);
  background: var(--bg-surface);
}

/* Native textarea — fully controlled, no El-Plus overhead */
.msg-textarea {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  resize: none;
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.55;
  color: var(--ink-900);
  /* Start at 1 row, expand via JS up to ~3 rows */
  min-height: 24px;
  max-height: 120px;
  overflow-y: auto;
  padding: 0;
  /* Kill iOS default styling */
  -webkit-appearance: none;
}

.msg-textarea::placeholder {
  color: var(--ink-300);
  font-size: 15px;
}

/* Send icon button */
.btn-send {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  background: var(--brand-gradient);
  color: white;
  box-shadow: 0 2px 8px rgba(232, 93, 4, 0.28);
  transition: filter var(--fast) var(--ease-out),
              transform var(--fast) var(--ease-spring),
              box-shadow var(--fast) var(--ease-out),
              opacity var(--fast) var(--ease-out);
}

.btn-send:not(:disabled):hover {
  filter: brightness(0.92);
  transform: scale(1.06);
  box-shadow: 0 4px 14px rgba(232, 93, 4, 0.35);
}

.btn-send:not(:disabled):active {
  transform: scale(0.94);
}

.btn-send:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  box-shadow: none;
}

/* Spinner inside send button while sending */
.send-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

/* ── Empty state ── */
.chat-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--ink-300);
  padding: 40px;
}

.chat-empty-icon { font-size: 48px; opacity: 0.35; }

.chat-empty-title {
  font-family: var(--font-display);
  font-size: 18px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: -0.02em;
}

.chat-empty-hint {
  font-size: 14px;
  color: var(--ink-300);
  text-align: center;
  max-width: 280px;
  line-height: 1.6;
}

/* ── Shared spinner ── */
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--ink-100);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ══════════════════════════════════════════════════════════════════
   MOBILE  (<768 px)
   Key change: .chat-input-area becomes position:fixed so the browser
   never auto-scrolls the whole page when the keyboard opens.
   Its `bottom` is driven by the JS-computed --input-bottom variable.
   ══════════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .messages-page {
    position: relative;
  }

  /* ── Sidebar fills screen above dock ── */
  .sidebar {
    width: 100%;
    position: absolute;
    inset: 0;
    /* Leave room for dock nav at the bottom */
    bottom: var(--input-bottom, 96px);
    z-index: 1;
  }

  .sidebar-hidden { display: none; }

  /* ── Chat panel fills screen above dock (before keyboard) ── */
  .chat-panel {
    position: absolute;
    inset: 0;
    z-index: 2;
    display: none;
    background: var(--bg-base);
    /* Bottom clearance is just enough for the fixed input bar when keyboard is closed;
       the messages-list padding-bottom handles the visual gap. */
    bottom: 0;
  }

  .chat-panel.chat-active { display: flex; }

  /* ── Input bar: FIXED, moves with keyboard ── */
  .chat-input-area {
    position: fixed;
    left: 0;
    right: 0;
    /* bottom is set via --input-bottom on .messages-page (JS-driven) */
    bottom: var(--input-bottom, 96px);
    z-index: 100;
    padding: 10px 12px;
    /* Subtle top shadow to visually separate from messages */
    box-shadow: 0 -1px 0 var(--ink-100), 0 -8px 24px rgba(28, 16, 7, 0.06);
    /* Prevent the input area itself from triggering page scroll on iOS */
    touch-action: none;
  }

  /* Input inner: slightly larger touch target on mobile */
  .input-inner {
    padding: 10px 10px 10px 16px;
    border-radius: 24px;
  }

  .msg-textarea { font-size: 16px; /* 16px prevents iOS auto-zoom */ }
  .msg-textarea::placeholder { font-size: 16px; }

  .chat-header { padding: 12px 14px; }

  .messages-list { padding: 16px 12px 16px; }

  .msg-bubble { max-width: 78%; }
}
</style>
