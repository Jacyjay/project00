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
      <div class="card-glow"></div>

      <div class="auth-brand">
        <div class="auth-logo-wrap">
          <div class="auth-logo">
            <LogoIcon :size="52" />
          </div>
          <div class="logo-ring"></div>
        </div>
        <h1 class="auth-title">开始旅程</h1>
        <p class="auth-subtitle">创建拾光坐标账号，记录每段旅途的故事</p>
      </div>

      <!-- Step indicator -->
      <div class="step-indicator">
        <div :class="['step', { active: step >= 1, done: step > 1 }]">
          <div class="step-bubble">
            <span v-if="step > 1" class="step-check">✓</span>
            <span v-else>1</span>
          </div>
          <span class="step-label">验证邮箱</span>
        </div>
        <div class="step-line-wrap">
          <div class="step-line" :class="{ active: step > 1 }">
            <div class="step-line-fill" :style="{ width: step > 1 ? '100%' : '0%' }"></div>
          </div>
        </div>
        <div :class="['step', { active: step >= 2 }]">
          <div class="step-bubble">2</div>
          <span class="step-label">完善资料</span>
        </div>
      </div>

      <!-- Step 1: Email Verification -->
      <transition name="step-fade" mode="out-in">
        <div v-if="step === 1" key="step1" class="step-panel">
          <el-form label-position="top" @submit.prevent>
            <div class="field-group">
              <label class="field-label">邮箱地址</label>
              <div class="input-wrap">
                <span class="input-icon">✉️</span>
                <el-input
                  v-model="form.email"
                  type="email"
                  placeholder="请输入你的邮箱"
                  size="large"
                  :disabled="codeSent"
                />
              </div>
            </div>

            <div v-if="codeSent" class="field-group">
              <label class="field-label">验证码</label>
              <div class="code-row">
                <div class="input-wrap" style="flex:1">
                  <span class="input-icon">🔑</span>
                  <el-input
                    v-model="form.code"
                    placeholder="请输入 6 位验证码"
                    size="large"
                    maxlength="6"
                    @keyup.enter="verifyAndNext"
                  />
                </div>
                <button
                  type="button"
                  class="btn-resend"
                  :disabled="countdown > 0"
                  @click="sendCode"
                >
                  {{ countdown > 0 ? `${countdown}s` : '重发' }}
                </button>
              </div>
            </div>

            <button
              v-if="!codeSent"
              type="button"
              class="btn-submit"
              @click="sendCode"
              :disabled="loadingSend"
            >
              <span>{{ loadingSend ? '发送中...' : '发送验证码' }}</span>
              <span v-if="!loadingSend" class="btn-submit-arrow">→</span>
            </button>
            <button
              v-else
              type="button"
              class="btn-submit"
              @click="verifyAndNext"
              :disabled="loadingVerify || form.code.length !== 6"
            >
              <span>{{ loadingVerify ? '验证中...' : '验证并继续' }}</span>
              <span v-if="!loadingVerify" class="btn-submit-arrow">→</span>
            </button>
          </el-form>

          <transition name="fade">
            <div v-if="codeSent" class="code-hint">
              <span class="code-hint-icon">📮</span>
              <span v-if="debugCode">
                当前为本地调试模式，验证码是 <strong>{{ debugCode }}</strong>。
              </span>
              <span v-else>
                验证码已发送至 <strong>{{ form.email }}</strong>，10 分钟内有效。
              </span>
            </div>
          </transition>
        </div>

        <!-- Step 2: Profile Setup -->
        <div v-else key="step2" class="step-panel">
          <el-form label-position="top" @submit.prevent>
            <div class="field-group">
              <label class="field-label">昵称</label>
              <div class="input-wrap">
                <span class="input-icon">👤</span>
                <el-input
                  v-model="form.nickname"
                  placeholder="给自己取个旅行者名字"
                  size="large"
                  autofocus
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
                  placeholder="至少 6 个字符"
                  show-password
                  size="large"
                  @keyup.enter="handleRegister"
                />
              </div>
            </div>

            <div class="field-group">
              <label class="field-label">确认密码</label>
              <div class="input-wrap">
                <span class="input-icon">🔒</span>
                <el-input
                  v-model="form.confirmPassword"
                  type="password"
                  placeholder="再次输入密码"
                  show-password
                  size="large"
                  @keyup.enter="handleRegister"
                />
              </div>
            </div>

            <button
              type="button"
              class="btn-submit"
              @click="handleRegister"
              :disabled="loadingRegister"
            >
              <span>{{ loadingRegister ? '注册中...' : '🚀 完成注册' }}</span>
            </button>
          </el-form>
        </div>
      </transition>

      <div class="auth-divider">
        <span>或</span>
      </div>

      <p class="auth-switch">
        已有账号？
        <router-link to="/login" class="auth-link">立即登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { sendVerificationCode, register } from '../api/auth'
import { useUserStore } from '../stores/user'
import LogoIcon from '../components/LogoIcon.vue'

const router = useRouter()
const userStore = useUserStore()

const step = ref(1)
const codeSent = ref(false)
const countdown = ref(0)
const loadingSend = ref(false)
const loadingVerify = ref(false)
const loadingRegister = ref(false)
const debugCode = ref('')

const form = ref({
  email: '',
  code: '',
  nickname: '',
  password: '',
  confirmPassword: '',
})

let countdownTimer = null

function startCountdown(seconds = 60) {
  countdown.value = seconds
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(countdownTimer)
      countdownTimer = null
    }
  }, 1000)
}

async function sendCode() {
  if (!form.value.email || !form.value.email.includes('@')) {
    ElMessage.warning('请输入有效的邮箱地址')
    return
  }
  debugCode.value = ''
  loadingSend.value = true
  try {
    const res = await sendVerificationCode(form.value.email)
    codeSent.value = true
    debugCode.value = String(res.data?.dev_code || '')
    if (debugCode.value) {
      form.value.code = debugCode.value
    }
    startCountdown(60)
    ElMessage.success(debugCode.value ? '已生成本地调试验证码' : '验证码已发送，请查收邮件')
  } catch (err) {
    debugCode.value = ''
    const detail = err.response?.data?.detail
    const message = detail || (
      err.request
        ? '后端接口未正常响应，可能是线上仍在跑旧版本、后端未重启，或域名跨域/反代配置未生效'
        : '发送失败，请稍后重试'
    )
    ElMessage.error(message)
  } finally {
    loadingSend.value = false
  }
}

function verifyAndNext() {
  if (form.value.code.length !== 6) {
    ElMessage.warning('请输入 6 位验证码')
    return
  }
  step.value = 2
}

async function handleRegister() {
  if (!form.value.nickname.trim()) {
    ElMessage.warning('请填写昵称')
    return
  }
  if (form.value.password.length < 6) {
    ElMessage.warning('密码至少需要 6 个字符')
    return
  }
  if (form.value.password !== form.value.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  loadingRegister.value = true
  try {
    const res = await register({
      email: form.value.email,
      code: form.value.code,
      nickname: form.value.nickname.trim(),
      password: form.value.password,
    })
    userStore.setAuth(res.data.access_token, res.data.user)
    ElMessage.success('注册成功，欢迎加入拾光坐标！')
    router.push('/')
  } catch (err) {
    const detail = err.response?.data?.detail || '注册失败'
    ElMessage.error(detail)
    if (detail.includes('验证码')) {
      step.value = 1
      codeSent.value = false
      debugCode.value = ''
      form.value.code = ''
    }
  } finally {
    loadingRegister.value = false
  }
}

onUnmounted(() => {
  if (countdownTimer) clearInterval(countdownTimer)
})
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
  right: -5%;
  animation: floatY 9s ease-in-out infinite;
}

.decor-blob-2 {
  width: 350px;
  height: 350px;
  background: radial-gradient(circle, rgba(244, 162, 97, 0.12) 0%, transparent 70%);
  bottom: 0%;
  left: -8%;
  animation: floatY 11s ease-in-out infinite reverse;
}

.decor-blob-3 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(232, 161, 0, 0.10) 0%, transparent 70%);
  top: 40%;
  right: 20%;
  animation: floatY 13s ease-in-out infinite;
}

.decor-ring {
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(232, 93, 4, 0.10);
}

.decor-ring-1 {
  width: 200px;
  height: 200px;
  top: 10%;
  left: 10%;
  animation: floatRotate 18s linear infinite;
}

.decor-ring-2 {
  width: 140px;
  height: 140px;
  bottom: 15%;
  right: 10%;
  border-color: rgba(244, 162, 97, 0.08);
  animation: floatRotate 22s linear infinite reverse;
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
  padding: 40px 40px 32px;
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  z-index: 1;
  margin: auto 0;
}

.card-glow { display: none; }

/* ── Brand block ── */
.auth-brand {
  text-align: center;
  margin-bottom: 28px;
}

.auth-logo-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
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
  margin: 0 0 8px;
  color: var(--ink-900);
}

.auth-subtitle {
  font-size: 14px;
  color: var(--ink-500);
  margin: 0;
  line-height: 1.5;
}

/* ── Step indicator ── */
.step-indicator {
  display: flex;
  align-items: flex-start;
  margin-bottom: 28px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.step-bubble {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  background: var(--bg-muted);
  color: var(--ink-300);
  transition: all var(--normal) var(--ease-spring);
  position: relative;
}

.step.active .step-bubble {
  background: var(--brand-gradient);
  color: var(--ink-900);
  box-shadow: 0 4px 16px rgba(232, 93, 4, 0.28);
}

.step.done .step-bubble {
  background: linear-gradient(135deg, #2D9B6F, #22876A);
  color: #ffffff;
  box-shadow: 0 4px 16px rgba(45, 155, 111, 0.25);
}

.step-check {
  animation: scaleIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes scaleIn {
  from { transform: scale(0); }
  to { transform: scale(1); }
}

.step-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-300);
  white-space: nowrap;
  transition: color var(--normal) var(--ease-out);
}

.step.active .step-label { color: var(--brand); }
.step.done .step-label { color: var(--success); }

.step-line-wrap {
  flex: 1;
  padding: 0 8px;
  margin-top: 18px;
}

.step-line {
  height: 3px;
  background: var(--ink-100);
  border-radius: 3px;
  overflow: hidden;
}

.step-line-fill {
  height: 100%;
  border-radius: 3px;
  background: var(--brand-gradient);
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

/* ── Step panel transition ── */
.step-fade-enter-active {
  transition: opacity var(--normal) var(--ease-out), transform var(--normal) var(--ease-out);
}
.step-fade-leave-active {
  transition: opacity var(--fast) var(--ease-out), transform var(--fast) var(--ease-out);
}
.step-fade-enter-from {
  opacity: 0;
  transform: translateX(20px);
}
.step-fade-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* ── Step panel ── */
.step-panel {
  display: flex;
  flex-direction: column;
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
.auth-card :deep(.el-form-item) { margin-bottom: 0; }
.auth-card :deep(.el-form-item__label) { display: none; }

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

.auth-card :deep(.el-input.is-disabled .el-input__wrapper) {
  background: var(--bg-muted) !important;
  border-color: var(--ink-100) !important;
}

.auth-card :deep(.el-input__inner) {
  font-size: 15px !important;
  color: var(--ink-900) !important;
  font-family: inherit !important;
}

.auth-card :deep(.el-input__inner::placeholder) {
  color: var(--ink-300) !important;
}

/* ── Code row ── */
.code-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.btn-resend {
  flex-shrink: 0;
  min-width: 64px;
  height: 52px;
  padding: 0 16px;
  background: var(--bg-muted);
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-sm);
  color: var(--ink-500);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition: border-color var(--fast) var(--ease-out), color var(--fast) var(--ease-out), background var(--fast) var(--ease-out);
}

.btn-resend:not(:disabled):hover {
  border-color: var(--brand);
  color: var(--brand);
  background: var(--brand-light);
}

.btn-resend:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ── Code sent hint ── */
.code-hint {
  margin-top: 16px;
  padding: 14px 16px;
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.12);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--ink-500);
  line-height: 1.6;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.code-hint-icon {
  font-size: 16px;
  flex-shrink: 0;
  line-height: 1.4;
}

.code-hint strong {
  color: var(--brand);
  font-weight: 600;
}

/* ── Submit button ── */
.btn-submit {
  width: 100%;
  margin-top: 24px;
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
  margin: 24px 0 16px;
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
  margin: 0;
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

/* ── Transition: fade ── */
.fade-enter-active, .fade-leave-active {
  transition: opacity var(--normal) var(--ease-out);
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
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
    padding: 30px 22px 24px;
  }

  .auth-title { font-size: 22px; }

  .auth-brand {
    margin-bottom: 24px;
  }

  .step-indicator {
    margin-bottom: 22px;
  }

  .field-group {
    margin-bottom: 16px;
  }

  .code-row {
    flex-direction: column;
    align-items: stretch;
  }

  .btn-resend {
    width: 100%;
    height: 46px;
  }

  .btn-submit {
    margin-top: 20px;
    padding: 15px 18px;
  }

  .step-bubble { width: 32px; height: 32px; font-size: 12px; }
  .step-label { font-size: 10px; }

  .decor-blob-1,
  .decor-blob-2 { width: 250px; height: 250px; }

  .decor-ring-1,
  .decor-ring-2 { display: none; }
}
</style>
