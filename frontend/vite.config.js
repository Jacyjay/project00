import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

function createProxy(target) {
  return {
    '/api': {
      target,
      changeOrigin: true,
    },
    '/uploads': {
      target,
      changeOrigin: true,
    },
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const defaultBackendTarget = mode === 'development' ? 'http://127.0.0.1:8000' : ''
  const backendTarget = (env.VITE_API_BASE_URL || defaultBackendTarget).replace(/\/$/, '')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        vue: 'vue/dist/vue.runtime.esm-bundler.js',
      },
    },
    server: {
      port: 5173,
      proxy: backendTarget ? createProxy(backendTarget) : undefined,
    },
    preview: {
      proxy: backendTarget ? createProxy(backendTarget) : undefined,
    },
  }
})
