<template>
  <div class="auth-page">
    <!-- Decorative floating shapes -->
    <div class="auth-bg-decor">
      <div class="decor-blob decor-blob-1"></div>
      <div class="decor-blob decor-blob-2"></div>
      <div class="decor-blob decor-blob-3"></div>
      <div class="decor-ring decor-ring-1"></div>
      <div class="decor-ring decor-ring-2"></div>
      <div class="decor-dot-grid"></div>
    </div>

    <div class="auth-card animate-fade-in-up">
      <!-- Gradient border glow -->
      <div class="card-glow"></div>

      <div class="auth-brand">
        <div class="auth-logo-wrap">
          <div class="auth-logo">
            <LogoIcon :size="52" />
          </div>
          <div class="logo-ring"></div>
        </div>
        <h1 class="auth-title">欢迎回来</h1>
        <p class="auth-subtitle">登录你的拾光坐标账号，继续记录旅程</p>
      </div>

      <el-form :model="form" label-position="top" @submit.prevent="handleLogin">
        <div class="field-group">
          <label class="field-label">邮箱地址</label>
          <div class="input-wrap">
            <span class="input-icon">✉️</span>
            <el-input
              v-model="form.email"
              type="email"
              placeholder="请输入邮箱"
              id="login-email"
              size="large"
            />
          </div>
        </div>

        <div class="field-group">
          <label class="field-label">密码</label>
          <div class="input-wrap">
            <span class="input-icon">🔒</span>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              show-password
              id="login-password"
              size="large"
              @keyup.enter="handleLogin"
            />
          </div>
        </div>

        <button
          type="button"
          class="btn-submit"
          @click="handleLogin"
          :disabled="loading"
          id="btn-login"
        >
          <span class="btn-submit-text">{{ loading ? '登录中...' : '登 录' }}</span>
          <span v-if="!loading" class="btn-submit-arrow">→</span>
        </button>
      </el-form>

      <div class="auth-divider">
        <span>或</span>
      </div>

      <p class="auth-switch">
        <router-link to="/forgot-password" class="auth-link">忘记密码？</router-link>
      </p>

      <p class="auth-switch">
        还没有账号？
        <router-link to="/register" class="auth-link">立即注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../api/auth'
import { useUserStore } from '../stores/user'
import LogoIcon from '../components/LogoIcon.vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const form = ref({ email: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.email || !form.value.password) {
    ElMessage.warning('请填写邮箱和密码')
    return
  }
  loading.value = true
  try {
    const res = await login(form.value)
    userStore.setAuth(res.data.access_token, res.data.user)
    ElMessage.success('登录成功！')
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Page shell ── */
.auth-page {
  height: 100%;
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: var(--bg-base);
  position: relative;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

/* ── Background decorations ── */
.auth-bg-decor {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.decor-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.5;
}

.decor-blob-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(232, 93, 4, 0.14) 0%, transparent 70%);
  top: -10%;
  left: -5%;
  animation: floatY 8s ease-in-out infinite;
}

.decor-blob-2 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(244, 162, 97, 0.12) 0%, transparent 70%);
  top: 20%;
  right: -8%;
  animation: floatY 10s ease-in-out infinite reverse;
}

.decor-blob-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(232, 161, 0, 0.10) 0%, transparent 70%);
  bottom: -5%;
  left: 30%;
  animation: floatY 12s ease-in-out infinite;
}

.decor-ring {
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(232, 93, 4, 0.10);
}

.decor-ring-1 {
  width: 240px;
  height: 240px;
  top: 15%;
  right: 12%;
  animation: floatRotate 16s linear infinite;
}

.decor-ring-2 {
  width: 160px;
  height: 160px;
  bottom: 20%;
  left: 8%;
  border-color: rgba(244, 162, 97, 0.08);
  animation: floatRotate 20s linear infinite reverse;
}

.decor-dot-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(28, 16, 7, 0.04) 1px, transparent 1px);
  background-size: 28px 28px;
}

@keyframes floatY {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-20px); }
}

@keyframes floatRotate {
  0%   { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* ── Card ── */
.auth-card {
  position: relative;
  width: 100%;
  max-width: 460px;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  padding: 44px 40px 36px;
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  z-index: 1;
  margin: auto 0;
}

.card-glow {
  display: none;
}

/* ── Brand block ── */
.auth-brand {
  text-align: center;
  margin-bottom: 36px;
}

.auth-logo-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 1;
}

.logo-ring {
  position: absolute;
  inset: -12px;
  border-radius: 50%;
  background: var(--brand-light);
}

.auth-title {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--ink-900);
  margin: 0 0 8px;
}

.auth-subtitle {
  font-size: 14px;
  color: var(--ink-500);
  margin: 0;
  line-height: 1.5;
}

/* ── Field groups ── */
.field-group {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink-500);
  letter-spacing: 0.01em;
  margin-bottom: 8px;
}

.input-wrap {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  z-index: 1;
  pointer-events: none;
  line-height: 1;
}

/* Override Element Plus */
.auth-card :deep(.el-form-item) {
  margin-bottom: 0;
}

.auth-card :deep(.el-form-item__label) {
  display: none;
}

.input-wrap :deep(.el-input__wrapper) {
  border-radius: var(--radius-sm) !important;
  border: 1.5px solid var(--ink-100) !important;
  box-shadow: none !important;
  padding: 14px 16px 14px 42px !important;
  background: var(--bg-muted) !important;
  transition: border-color var(--fast) var(--ease-out) !important;
}

.input-wrap :deep(.el-input__wrapper:hover) {
  border-color: var(--ink-300) !important;
  background: var(--bg-hover) !important;
}

.input-wrap :deep(.el-input__wrapper.is-focus) {
  border-color: var(--brand) !important;
  box-shadow: 0 0 0 3px var(--brand-light) !important;
  background: var(--bg-surface) !important;
}

.auth-card :deep(.el-input__inner) {
  font-size: 15px !important;
  color: var(--ink-900) !important;
  font-family: inherit !important;
}

.auth-card :deep(.el-input__inner::placeholder) {
  color: var(--ink-300) !important;
}

/* ── Submit button ── */
.btn-submit {
  width: 100%;
  margin-top: 28px;
  padding: 16px 24px;
  background: var(--brand-gradient);
  color: var(--ink-900);
  border: none;
  border-radius: var(--radius-md);
  font-size: 16px;
  font-weight: 700;
  font-family: var(--font-body);
  letter-spacing: -0.01em;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(232, 93, 4, 0.28);
  transition:
    transform var(--fast) var(--ease-spring),
    box-shadow var(--fast) var(--ease-out),
    filter var(--fast) var(--ease-out);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-2px);
  filter: brightness(0.93);
  box-shadow: 0 8px 24px rgba(232, 93, 4, 0.34);
}

.btn-submit:active:not(:disabled) {
  transform: scale(0.97);
  transition-duration: 80ms;
}

.btn-submit:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.btn-submit-arrow {
  font-size: 18px;
  transition: transform var(--fast) var(--ease-out);
}

.btn-submit:hover .btn-submit-arrow {
  transform: translateX(4px);
}

/* ── Divider ── */
.auth-divider {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 28px 0 20px;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--ink-100);
}

.auth-divider span {
  font-size: 12px;
  color: var(--ink-300);
  font-weight: 500;
}

/* ── Footer switch link ── */
.auth-switch {
  text-align: center;
  font-size: 14px;
  color: var(--ink-300);
  margin-top: 0;
  margin-bottom: 0;
}

.auth-link {
  color: var(--brand);
  text-decoration: none;
  font-weight: 700;
  transition: color var(--fast) var(--ease-out);
}

.auth-link:hover {
  color: var(--brand-hover);
  text-decoration: underline;
  text-underline-offset: 3px;
}

/* ── Mobile ── */
@media (max-width: 640px) {
  .auth-page {
    align-items: flex-start;
    justify-content: flex-start;
    padding: max(20px, env(safe-area-inset-top)) 16px 28px;
  }

  .auth-card {
    margin: 0 auto;
    padding: 34px 22px 26px;
  }

  .auth-title {
    font-size: 22px;
  }

  .auth-brand {
    margin-bottom: 28px;
  }

  .field-group {
    margin-bottom: 16px;
  }

  .btn-submit {
    margin-top: 22px;
    padding: 15px 20px;
  }

  .decor-blob-1,
  .decor-blob-2 {
    width: 250px;
    height: 250px;
  }

  .decor-ring-1,
  .decor-ring-2 {
    display: none;
  }
}
</style>
