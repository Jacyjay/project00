<template>
  <div class="download-page">
    <div class="download-bg">
      <div class="bg-blob bg-blob-1"></div>
      <div class="bg-blob bg-blob-2"></div>
      <div class="bg-blob bg-blob-3"></div>
      <div class="bg-grid"></div>
    </div>

    <div class="download-content">
      <div class="download-hero animate-fade-in-up">
        <div class="hero-badge">Coming Soon</div>
        <h1 class="hero-title">拾光坐标</h1>
        <p class="hero-subtitle">随时随地，记录你的生活坐标</p>
        <p class="hero-desc">沉浸式地图体验，AI 智能文案，让每一次旅行都值得被记录</p>
      </div>

      <div class="download-cards">
        <div class="download-card" :class="{ 'card-visible': showCards }" style="--delay: 0.15s">
          <div class="card-shine"></div>
          <div class="card-icon-wrap">
            <div class="card-icon">
              <svg viewBox="0 0 384 512" width="36" height="36" fill="currentColor">
                <path d="M318.7 268.7c-.2-36.7 16.4-64.4 50-84.8-18.8-26.9-47.2-41.7-84.7-44.6-35.5-2.8-74.3 20.7-88.5 20.7-15 0-49.4-19.7-76.4-19.7C63.3 141.2 4 184.8 4 273.5q0 39.3 14.4 81.2c12.8 36.7 59 126.7 107.2 125.2 25.2-.6 43-17.9 75.8-17.9 31.8 0 48.3 17.9 76.4 17.9 48.6-.7 90.4-82.5 102.6-119.3-65.2-30.7-61.7-90-61.7-91.9zm-56.6-164.2c27.3-32.4 24.8-61.9 24-72.5-24.1 1.4-52 16.4-67.9 34.9-17.5 19.8-27.8 44.3-25.6 71.9 26.1 2 49.9-11.4 69.5-34.3z"/>
              </svg>
            </div>
            <div class="card-icon-glow"></div>
          </div>
          <h3 class="card-title">iOS 客户端</h3>
          <p class="card-status">即将登陆 App Store</p>
          <div class="card-badge">
            <span class="badge-dot"></span>
            开发中
          </div>

          <div class="card-features">
            <div class="feature-item">
              <span class="feature-icon">📍</span>
              <span>离线地图支持</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">📸</span>
              <span>原生相机接入</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🔔</span>
              <span>实时推送通知</span>
            </div>
          </div>
        </div>

        <div class="download-card" :class="{ 'card-visible': showCards }" style="--delay: 0.30s">
          <div class="card-shine"></div>
          <div class="card-icon-wrap">
            <div class="card-icon android-icon">
              <svg viewBox="0 0 576 512" width="36" height="36" fill="currentColor">
                <path d="M420.55 301.93a24 24 0 1 1 24-24 24 24 0 0 1-24 24m-265.1 0a24 24 0 1 1 24-24 24 24 0 0 1-24 24m273.7-144.48l47.94-83a10 10 0 1 0-17.27-10l-48.54 84.07a301.25 301.25 0 0 0-246.56 0L116.18 64.45a10 10 0 1 0-17.27 10l47.94 83C64.53 202.22 8.24 285.55 0 384h576c-8.24-98.45-64.54-181.78-146.85-226.55"/>
              </svg>
            </div>
            <div class="card-icon-glow android-glow"></div>
          </div>
          <h3 class="card-title">Android 客户端</h3>
          <p class="card-status">即将登陆各大应用商店</p>
          <div class="card-badge">
            <span class="badge-dot"></span>
            开发中
          </div>

          <div class="card-features">
            <div class="feature-item">
              <span class="feature-icon">🗺️</span>
              <span>多地图引擎切换</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">🤖</span>
              <span>AI 旅行助手</span>
            </div>
            <div class="feature-item">
              <span class="feature-icon">⚡</span>
              <span>极速离线同步</span>
            </div>
          </div>
        </div>
      </div>

      <div class="download-footer animate-fade-in" style="animation-delay: 0.5s">
        <p class="download-hint">目前请使用网页版体验完整功能</p>
        <router-link to="/" class="btn-back-map">
          <span>🗺️</span>
          <span>前往地图广场</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const showCards = ref(false)
onMounted(() => {
  setTimeout(() => { showCards.value = true }, 200)
})
</script>

<style scoped>
.download-page {
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 40%, #FDF2F8 80%, #EEF2FF 100%);
}

/* ── Background ── */
.download-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.bg-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
}

.bg-blob-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(232, 93, 4, 0.12) 0%, transparent 70%);
  top: -10%;
  left: -10%;
  animation: blobFloat 10s ease-in-out infinite;
}

.bg-blob-2 {
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, rgba(244, 162, 97, 0.10) 0%, transparent 70%);
  top: 30%;
  right: -10%;
  animation: blobFloat 13s ease-in-out infinite reverse;
}

.bg-blob-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(232, 161, 0, 0.08) 0%, transparent 70%);
  bottom: -5%;
  left: 30%;
  animation: blobFloat 16s ease-in-out infinite;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle, rgba(28, 16, 7, 0.03) 1px, transparent 1px);
  background-size: 32px 32px;
}

@keyframes blobFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33%      { transform: translate(20px, -30px) scale(1.05); }
  66%      { transform: translate(-15px, 15px) scale(0.95); }
}

/* ── Content ── */
.download-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px calc(132px + env(safe-area-inset-bottom));
  position: relative;
  z-index: 1;
  min-height: max-content;
}

/* ── Hero ── */
.download-hero {
  text-align: center;
  margin-bottom: 48px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  padding: 6px 16px;
  border-radius: 999px;
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.18);
  color: var(--brand);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  margin-bottom: 20px;
}

.hero-title {
  font-family: var(--font-display);
  font-size: 52px;
  font-weight: 800;
  letter-spacing: -0.04em;
  margin-bottom: 12px;
  background: linear-gradient(135deg, var(--ink-900) 20%, #E85D04 55%, #F4A261 100%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: gradientText 4s ease-in-out infinite;
}

@keyframes gradientText {
  0%, 100% { background-position: 0% 50%; }
  50%      { background-position: 100% 50%; }
}

.hero-subtitle {
  font-size: 20px;
  font-weight: 500;
  color: var(--ink-700);
  margin-bottom: 8px;
}

.hero-desc {
  font-size: 14px;
  color: var(--ink-500);
  max-width: 380px;
  margin: 0 auto;
  line-height: 1.6;
}

/* ── Cards ── */
.download-cards {
  display: flex;
  gap: 24px;
  margin-bottom: 48px;
}

.download-card {
  position: relative;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  padding: 36px 32px 28px;
  text-align: center;
  border: 1px solid var(--ink-100);
  box-shadow: var(--shadow-float);
  opacity: 0;
  transform: translateY(30px);
  transition:
    opacity 0.6s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.6s cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 0.3s ease;
  transition-delay: var(--delay, 0s);
  cursor: default;
  min-width: 260px;
  overflow: hidden;
}

.card-shine {
  display: none;
}

.card-visible {
  opacity: 1;
  transform: translateY(0);
}

.download-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 50px rgba(28, 16, 7, 0.10);
}

.card-visible:hover {
  transform: translateY(-6px);
}

.card-icon-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.card-icon {
  position: relative;
  z-index: 1;
  color: var(--ink-900);
}

.android-icon { color: #10B981; }

.card-icon-glow {
  position: absolute;
  inset: -16px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(232, 93, 4, 0.08) 0%, transparent 70%);
  animation: breatheGlow 3s ease-in-out infinite;
}

.android-glow {
  background: radial-gradient(circle, rgba(16, 185, 129, 0.08) 0%, transparent 70%);
}

@keyframes breatheGlow {
  0%, 100% { opacity: 0.5; transform: scale(1); }
  50%      { opacity: 1; transform: scale(1.2); }
}

.card-title {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  color: var(--ink-900);
  margin-bottom: 6px;
  letter-spacing: -0.02em;
}

.card-status {
  font-size: 13px;
  color: var(--ink-300);
  margin-bottom: 16px;
}

.card-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--brand-light);
  border: 1px solid rgba(232, 93, 4, 0.15);
  color: var(--brand);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  margin-bottom: 24px;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand);
  animation: pulseDot 2s ease-in-out infinite;
}

@keyframes pulseDot {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50%      { opacity: 1; transform: scale(1.3); }
}

.card-features {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--ink-700);
  font-weight: 500;
}

.feature-icon {
  font-size: 14px;
  flex-shrink: 0;
}

/* ── Footer ── */
.download-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.download-hint {
  color: var(--ink-300);
  font-size: 14px;
}

.btn-back-map {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  background: var(--bg-surface);
  border: 1px solid var(--ink-100);
  border-radius: 999px;
  color: var(--ink-900);
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  box-shadow: var(--shadow-card);
  transition: all 0.25s ease;
}

.btn-back-map:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-float);
  background: var(--bg-hover);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .download-page {
    overflow-x: hidden;
  }

  .download-cards {
    flex-direction: column;
    gap: 20px;
    width: 100%;
    max-width: 360px;
  }

  .download-content {
    align-items: stretch;
    justify-content: flex-start;
    padding: max(28px, env(safe-area-inset-top)) 16px calc(136px + env(safe-area-inset-bottom));
  }

  .download-hero,
  .download-footer {
    text-align: center;
  }

  .hero-title {
    font-size: 36px;
  }

  .hero-subtitle {
    font-size: 17px;
  }

  .hero-desc {
    max-width: 100%;
  }

  .download-card {
    padding: 28px 24px 24px;
    min-width: unset;
    width: 100%;
  }

  .bg-blob-1,
  .bg-blob-2 {
    width: 300px;
    height: 300px;
  }
}
</style>
