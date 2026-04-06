<template>
  <el-config-provider :locale="zhCn">
    <div class="app-layout">
      <AppHeader v-if="!hideChrome" />
      <main :class="['app-main', { chromeless: hideChrome, immersive: immersiveDock }]">
        <RouterView v-slot="{ Component, route }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </el-config-provider>
</template>

<script setup>
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import AppHeader from './components/AppHeader.vue'
import { useUserStore } from './stores/user'
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'

const userStore = useUserStore()
const route = useRoute()
const hideChrome = computed(() => Boolean(route.meta.hideChrome))
const immersiveDock = computed(() => Boolean(route.meta.immersiveDock) && !hideChrome.value)

onMounted(async () => {
  if (userStore.token) {
    await userStore.fetchUser()
  }
})
</script>

<style scoped>
.app-layout {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-base);
}

.app-main {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  position: relative;
  padding-bottom: calc(100px + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.app-main.chromeless {
  padding-bottom: 0;
}

.app-main.immersive {
  padding-bottom: 0;
}
</style>
