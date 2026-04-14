<template>
  <transition name="modal-fade">
    <div class="fl-overlay" @click.self="$emit('close')">
      <div class="fl-modal">
        <div class="fl-header">
          <span class="fl-title">{{ title }}</span>
          <button class="fl-close" @click="$emit('close')">✕</button>
        </div>

        <div v-if="loading" class="fl-loading">
          <div class="fl-spinner"></div>
        </div>

        <div v-else-if="error" class="fl-empty">
          <span>🔒</span>
          <p>{{ error }}</p>
        </div>

        <div v-else-if="users.length === 0" class="fl-empty">
          <span>👤</span>
          <p>暂无用户</p>
        </div>

        <div v-else class="fl-list">
          <router-link
            v-for="u in users"
            :key="u.id"
            :to="`/profile/${u.id}`"
            class="fl-item"
            @click="$emit('close')"
          >
            <div class="fl-avatar">{{ u.nickname?.charAt(0) }}</div>
            <span class="fl-name">{{ u.nickname }}</span>
            <span class="fl-arrow">→</span>
          </router-link>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getFollowers, getFollowing } from '../api/follows'

const props = defineProps({
  userId: { type: [String, Number], required: true },
  type: { type: String, required: true }, // 'followers' | 'following'
})
defineEmits(['close'])

const title = props.type === 'followers' ? '粉丝' : '关注'
const users = ref([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const res = props.type === 'followers'
      ? await getFollowers(props.userId)
      : await getFollowing(props.userId)
    users.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || '列表不公开'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.fl-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(4px);
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.fl-modal {
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: 18px;
  width: 100%;
  max-width: 360px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.18);
  overflow: hidden;
}

.fl-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--ink-100);
  flex-shrink: 0;
}

.fl-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ink-900);
}

.fl-close {
  background: none;
  border: none;
  color: var(--ink-400);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 6px;
  transition: background 0.15s;
}
.fl-close:hover { background: var(--bg-muted); }

.fl-loading {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.fl-spinner {
  width: 26px;
  height: 26px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.fl-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 20px;
  color: var(--ink-400);
  font-size: 13px;
}
.fl-empty span { font-size: 32px; }

.fl-list {
  overflow-y: auto;
  padding: 8px 0;
}

.fl-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  text-decoration: none;
  color: var(--ink-900);
  transition: background 0.15s;
}
.fl-item:hover { background: var(--bg-muted); }

.fl-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--brand-gradient);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  flex-shrink: 0;
}

.fl-name {
  flex: 1;
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-800);
}

.fl-arrow {
  font-size: 14px;
  color: var(--ink-300);
}

.modal-fade-enter-active,
.modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from,
.modal-fade-leave-to { opacity: 0; }
</style>
