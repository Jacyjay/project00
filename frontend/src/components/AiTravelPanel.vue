<template>
  <div class="ai-chat-panel">
    <!-- Header -->
    <div class="panel-header">
      <div class="header-left">
        <span class="header-icon">🧭</span>
        <div class="header-meta">
          <span class="header-title">AI旅行建议</span>
          <span v-if="locationSummary" class="header-sub">{{ locationSummary }}</span>
        </div>
      </div>
      <div class="header-actions">
        <button v-if="messages.length" type="button" class="btn-ghost" @click="emit('newChat')">新对话</button>
        <button type="button" class="btn-ghost" @click="emit('close')">收起</button>
      </div>
    </div>

    <!-- Chat scroll area -->
    <div ref="scrollRef" class="chat-body">
      <!-- Initial loading -->
      <div v-if="loading && !messages.length" class="msg-row msg-ai">
        <div class="avatar-ai">豆</div>
        <div class="bubble bubble-ai bubble-loading">
          <div class="typing-dots"><span /><span /><span /></div>
          <span class="loading-hint">正在结合当前位置生成旅行建议...</span>
        </div>
      </div>

      <!-- Initial error -->
      <div v-if="error && !messages.length" class="msg-row msg-ai">
        <div class="avatar-ai">豆</div>
        <div class="bubble bubble-ai bubble-error">
          <span>{{ error }}</span>
          <button type="button" class="btn-retry" @click="emit('newChat')">重新生成</button>
        </div>
      </div>

      <!-- Messages -->
      <template v-for="msg in messages" :key="msg.id">
        <!-- User bubble -->
        <div v-if="msg.role === 'user'" class="msg-row msg-user">
          <div class="bubble bubble-user">{{ msg.content }}</div>
        </div>

        <!-- AI: initial recommendations -->
        <div v-else-if="msg.role === 'assistant' && msg.type === 'recommendations'" class="msg-row msg-ai">
          <div class="avatar-ai">豆</div>
          <div class="ai-content">
            <div v-if="msg.summary" class="bubble bubble-ai">{{ msg.summary }}</div>
            <div v-if="msg.recommendations && msg.recommendations.length" class="rec-list">
              <article
                v-for="item in msg.recommendations"
                :key="item.name + item.latitude"
                class="rec-card"
              >
                <div class="rec-header">
                  <strong class="rec-name">{{ item.name }}</strong>
                  <div class="rec-tags">
                    <span v-if="item.type" class="tag">{{ item.type }}</span>
                    <span v-if="item.distance_text" class="tag tag-dist">{{ item.distance_text }}</span>
                  </div>
                </div>
                <p class="rec-reason">{{ item.reason }}</p>
                <div v-if="item.best_time || item.tips" class="rec-extra">
                  <span v-if="item.best_time">推荐时段：{{ item.best_time }}</span>
                  <span v-if="item.tips">{{ item.tips }}</span>
                </div>
                <p v-if="item.address" class="rec-address">{{ item.address }}</p>
                <div class="rec-actions">
                  <button type="button" class="btn-outline" @click="emit('locate', item)">地图查看</button>
                  <button type="button" class="btn-brand" @click="emit('checkin', item)">去这里打卡</button>
                </div>
              </article>
            </div>
          </div>
        </div>

        <!-- AI: streaming or completed chat reply -->
        <div v-else-if="msg.role === 'assistant' && msg.type === 'chat'" class="msg-row msg-ai">
          <div class="avatar-ai">豆</div>
          <div class="bubble bubble-ai">
            <span v-if="msg.content">{{ msg.content }}</span>
            <div v-else-if="msg.streaming" class="typing-dots"><span /><span /><span /></div>
            <span v-if="msg.streaming && msg.content" class="cursor-blink" aria-hidden="true">|</span>
          </div>
        </div>
      </template>

      <div ref="bottomRef" class="scroll-anchor" aria-hidden="true" />
    </div>

    <!-- Input area -->
    <form class="chat-input-area" @submit.prevent="submit">
      <textarea
        ref="inputRef"
        v-model.trim="draft"
        class="chat-textarea"
        rows="2"
        maxlength="150"
        placeholder="继续追问，比如：适合晚上去吗、有没有适合情侣的..."
        :disabled="loading || isStreaming"
        @keydown.enter.exact.prevent="submit"
        @keydown.enter.shift.exact="() => {}"
      />
      <button
        type="submit"
        class="btn-send"
        :disabled="loading || isStreaming || !draft"
      >
        {{ isStreaming ? '...' : '发送' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: '',
  },
  locationSummary: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['close', 'newChat', 'ask', 'locate', 'checkin'])

const draft = ref('')
const scrollRef = ref(null)
const bottomRef = ref(null)
const inputRef = ref(null)

// Whether any message is currently streaming
const isStreaming = computed(() =>
  props.messages.some((m) => m.role === 'assistant' && m.streaming)
)

function scrollToBottom() {
  nextTick(() => {
    bottomRef.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  })
}

// Scroll on new messages or loading state changes
watch(() => props.messages.length, scrollToBottom)
watch(
  () => {
    const last = props.messages[props.messages.length - 1]
    return last?.content?.length ?? 0
  },
  scrollToBottom,
)
watch(() => props.loading, scrollToBottom)

function submit() {
  const q = draft.value.trim()
  if (!q || props.loading || isStreaming.value) return
  emit('ask', q)
  draft.value = ''
}
</script>

<style scoped>
.ai-chat-panel {
  display: flex;
  flex-direction: column;
  /*
   * 高度上限：同时避免超过 58vh 以及避免底部超过底部导航栏。
   * 底部导航栏占用约 83px（18px gap + 65px 高度）+ safe-area-inset-bottom。
   * 工具栏顶部 14px + 顶部内容约 155px + 导航栏空间 100px = ~270px 固定偏移。
   */
  height: min(58vh, calc(100vh - 350px - env(safe-area-inset-bottom)));
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

/* ── Header ── */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border-bottom: 1px solid var(--ink-100);
  flex: 0 0 auto;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.header-icon {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--brand-light);
  border-radius: 10px;
  font-size: 15px;
  flex-shrink: 0;
}

.header-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.header-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
}

.header-sub {
  font-size: 11px;
  color: var(--ink-300);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.btn-ghost {
  padding: 5px 10px;
  border: none;
  border-radius: var(--radius-full);
  background: var(--brand-light);
  color: var(--brand);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
}

/* ── Chat body ── */
.chat-body {
  flex: 1 1 auto;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scrollbar-width: thin;
  scrollbar-color: rgba(232, 93, 4, 0.25) transparent;
}

.msg-row {
  display: flex;
  gap: 8px;
  max-width: 100%;
}

.msg-ai {
  align-items: flex-start;
}

.msg-user {
  justify-content: flex-end;
}

/* Avatar */
.avatar-ai {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--brand-gradient);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}

/* Bubbles */
.bubble {
  padding: 10px 13px;
  border-radius: 14px;
  font-size: 13px;
  line-height: 1.7;
  word-break: break-word;
}

.bubble-user {
  background: var(--brand);
  color: #fff;
  border-bottom-right-radius: 4px;
  max-width: 78%;
}

.bubble-ai {
  background: var(--bg-muted);
  color: var(--ink-700);
  border-bottom-left-radius: 4px;
  max-width: 88%;
}

.bubble-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ink-300);
}

.loading-hint {
  font-size: 12px;
}

.bubble-error {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--ink-500);
}

/* AI content wrapper (for recommendations) */
.ai-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

/* Recommendation cards */
.rec-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rec-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 13px;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-md);
}

.rec-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.rec-name {
  font-size: 14px;
  color: var(--ink-900);
  line-height: 1.4;
}

.rec-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  flex-shrink: 0;
}

.tag {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: var(--bg-muted);
  color: var(--ink-300);
  white-space: nowrap;
}

.tag-dist {
  background: var(--brand-light);
  color: var(--brand);
}

.rec-reason {
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: var(--ink-700);
}

.rec-extra {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 11px;
  color: var(--ink-300);
}

.rec-address {
  margin: 0;
  font-size: 11px;
  line-height: 1.5;
  color: var(--ink-300);
}

.rec-actions {
  display: flex;
  gap: 8px;
}

.btn-outline,
.btn-brand,
.btn-retry {
  border: none;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 700;
  padding: 6px 12px;
  cursor: pointer;
  font-family: inherit;
}

.btn-outline {
  background: transparent;
  border: 1px solid var(--ink-100);
  color: var(--ink-700);
}

.btn-brand,
.btn-retry {
  background: var(--brand-gradient);
  color: #fff;
}

/* Typing cursor */
.cursor-blink {
  display: inline-block;
  margin-left: 1px;
  color: var(--brand);
  animation: blink 1s step-end infinite;
}

/* Typing dots */
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}

.typing-dots span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--ink-300);
  animation: bounce 1.1s ease-in-out infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.18s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.36s;
}

/* ── Input area ── */
.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px 12px;
  border-top: 1px solid var(--ink-100);
  background: var(--bg-surface);
  flex: 0 0 auto;
}

.chat-textarea {
  flex: 1;
  resize: none;
  padding: 9px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--ink-100);
  background: var(--bg-muted);
  color: var(--ink-700);
  font: inherit;
  font-size: 13px;
  line-height: 1.5;
  box-sizing: border-box;
  min-height: 40px;
}

.chat-textarea:disabled {
  opacity: 0.5;
}

.chat-textarea:focus {
  outline: none;
  border-color: var(--brand);
}

.btn-send {
  border: none;
  border-radius: var(--radius-full);
  padding: 9px 16px;
  background: var(--brand-gradient);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  flex-shrink: 0;
  white-space: nowrap;
}

.btn-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.scroll-anchor {
  height: 1px;
}

/* Animations */
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
  40% { transform: translateY(-5px); opacity: 1; }
}
</style>
