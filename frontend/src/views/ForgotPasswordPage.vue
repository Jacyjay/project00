<template>
  <div class="auth-page">
    <div class="auth-decorations">
      <div class="deco-circle deco-1"></div>
      <div class="deco-circle deco-2"></div>
      <div class="deco-circle deco-3"></div>
    </div>

    <div class="auth-card">
      <div class="auth-header">
        <h1 class="auth-title">重置密码</h1>
        <p class="auth-subtitle">输入你的邮箱地址，我们将发送验证码</p>
      </div>

      <form @submit.prevent="handleSubmit" class="auth-form">
        <div class="form-group">
          <label for="email">邮箱</label>
          <input
            id="email"
            v-model="form.email"
            type="email"
            placeholder="your@email.com"
            required
            :disabled="codeSent"
          />
        </div>

        <div v-if="!codeSent" class="form-actions">
          <button type="button" @click="sendCode" class="btn-primary" :disabled="sending">
            {{ sending ? '发送中...' : '发送验证码' }}
          </button>
        </div>

        <template v-if="codeSent">
          <div class="form-group">
            <label for="code">验证码</label>
            <input
              id="code"
              v-model="form.code"
              type="text"
              placeholder="6位验证码"
              maxlength="6"
              required
            />
          </div>

          <div class="form-group">
            <label for="password">新密码</label>
            <input
              id="password"
              v-model="form.password"
              type="password"
              placeholder="至少6个字符"
              required
            />
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="resetting">
              {{ resetting ? '重置中...' : '重置密码' }}
            </button>
            <button type="button" @click="sendCode" class="btn-secondary" :disabled="sending">
              {{ sending ? '发送中...' : '重新发送验证码' }}
            </button>
          </div>
        </template>

        <div v-if="devCode" class="dev-code-notice">
          <strong>调试模式验证码：</strong> {{ devCode }}
        </div>

        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>
      </form>

      <div class="auth-footer">
        <router-link to="/login" class="auth-link">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const form = ref({
  email: '',
  code: '',
  password: '',
})

const codeSent = ref(false)
const sending = ref(false)
const resetting = ref(false)
const devCode = ref('')
const errorMessage = ref('')
const successMessage = ref('')

async function sendCode() {
  if (!form.value.email) {
    errorMessage.value = '请输入邮箱地址'
    return
  }

  sending.value = true
  errorMessage.value = ''
  devCode.value = ''

  try {
    const response = await axios.post('/api/auth/send-reset-code', {
      email: form.value.email,
    })

    successMessage.value = response.data.message
    codeSent.value = true

    if (response.data.delivery === 'debug' && response.data.dev_code) {
      devCode.value = response.data.dev_code
    }
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '发送验证码失败'
  } finally {
    sending.value = false
  }
}

async function handleSubmit() {
  if (!form.value.code || !form.value.password) {
    errorMessage.value = '请填写所有字段'
    return
  }

  if (form.value.password.length < 6) {
    errorMessage.value = '密码至少需要6个字符'
    return
  }

  resetting.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const response = await axios.post('/api/auth/reset-password', {
      email: form.value.email,
      code: form.value.code,
      new_password: form.value.password,
    })

    successMessage.value = response.data.message

    setTimeout(() => {
      router.push('/login')
    }, 1500)
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || '重置密码失败'
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 24px;
  position: relative;
  overflow: hidden;
}

.auth-decorations {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.deco-circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(40px);
}

.deco-1 {
  width: 400px;
  height: 400px;
  top: -200px;
  right: -100px;
  animation: float 20s infinite ease-in-out;
}

.deco-2 {
  width: 300px;
  height: 300px;
  bottom: -150px;
  left: -100px;
  animation: float 15s infinite ease-in-out reverse;
}

.deco-3 {
  width: 200px;
  height: 200px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: pulse 10s infinite ease-in-out;
}

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-30px) rotate(10deg); }
}

@keyframes pulse {
  0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.1; }
  50% { transform: translate(-50%, -50%) scale(1.2); opacity: 0.15; }
}

.auth-card {
  background: white;
  border-radius: 24px;
  padding: 48px;
  width: 100%;
  max-width: 440px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  position: relative;
  z-index: 1;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--ink-900);
  margin-bottom: 8px;
}

.auth-subtitle {
  font-size: 15px;
  color: var(--ink-500);
  line-height: 1.5;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-700);
}

.form-group input {
  padding: 12px 16px;
  border: 2px solid var(--ink-200);
  border-radius: 12px;
  font-size: 15px;
  transition: all 0.2s;
  background: white;
}

.form-group input:focus {
  outline: none;
  border-color: var(--brand);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.form-group input:disabled {
  background: var(--ink-50);
  color: var(--ink-400);
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.btn-primary,
.btn-secondary {
  padding: 14px 24px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: white;
  color: var(--brand);
  border: 2px solid var(--brand);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--brand-50);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.dev-code-notice {
  padding: 12px 16px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 8px;
  font-size: 13px;
  color: #856404;
}

.error-message {
  padding: 12px 16px;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 8px;
  color: #c33;
  font-size: 14px;
}

.success-message {
  padding: 12px 16px;
  background: #d4edda;
  border: 1px solid #c3e6cb;
  border-radius: 8px;
  color: #155724;
  font-size: 14px;
}

.auth-footer {
  margin-top: 24px;
  text-align: center;
}

.auth-link {
  color: var(--brand);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
}

.auth-link:hover {
  color: var(--brand-dark);
  text-decoration: underline;
}
</style>
