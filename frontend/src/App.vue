<template>
  <div
    class="min-h-dvh overflow-x-hidden bg-transparent text-base-content relative z-0"
  >
    <!-- Ambient Mesh Canvas (Low-Res Scaled Blur) -->
    <DynamicCanvas />

    <LyricsView :is-open="isLyricsOpen" @close="isLyricsOpen = false" />
    <div
      class="flex flex-col min-h-dvh w-full overflow-hidden transition-[padding] duration-300"
      :class="
        route?.name === 'Player' || route?.name === 'Lyrics'
          ? 'pb-[env(safe-area-inset-bottom)] lg:pb-0'
          : 'pb-[calc(80px_+_env(safe-area-inset-bottom))] lg:pb-[96px]'
      "
    >
      <div class="flex flex-1 min-h-0 relative">
        <Sidebar />
        <main class="relative flex-1 min-w-0 transition-all duration-300 overflow-y-auto">
          <div
            class="mx-auto flex w-full max-w-[1600px] flex-col px-4 pt-4 sm:px-6 lg:px-8 lg:pt-6 h-full"
          >
            <router-view v-slot="{ Component, route }">
              <transition name="page" mode="out-in">
                <keep-alive :include="['Player']">
                  <component :is="Component" :key="route.fullPath" />
                </keep-alive>
              </transition>
            </router-view>
          </div>
        </main>
        <NowPlayingSidebar />
      </div>
      
      <!-- Fixed PlayerBar at the bottom -->
      <div class="fixed bottom-0 left-0 w-full z-50">
        <PlayerBar
          :is-lyrics-open="isLyricsOpen"
          @open-lyrics="isLyricsOpen = !isLyricsOpen"
        />
      </div>
    </div>
    <MobileNav />
    <Settings />
    <QueueDrawer />
  </div>
</template>

<script setup>
import { onBeforeMount, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import PlayerBar from './components/PlayerBar.vue'
import Sidebar from './components/Sidebar.vue'
import NowPlayingSidebar from './components/NowPlayingSidebar.vue'
import Settings from './components/Settings.vue'
import LyricsView from './components/LyricsView.vue'
import MobileNav from './components/MobileNav.vue'
import QueueDrawer from './components/QueueDrawer.vue'
import { useBinaryThemeManager } from './model/theme'
import { useDynamicTheme } from './model/dynamicTheme'
import { usePlayer } from './model/player'
import { useLayout } from './model/layout'
import DynamicCanvas from './components/DynamicCanvas.vue'

const isLyricsOpen = ref(false)
const route = useRoute()
const themeMgr = useBinaryThemeManager()
const player = usePlayer()
const layout = useLayout()
useDynamicTheme()

const toggleLyrics = () => {
  isLyricsOpen.value = !isLyricsOpen.value
}
const forceOpenLyrics = () => {
  isLyricsOpen.value = true
}

onBeforeMount(() => {
  themeMgr.setLightAlias('hify-light')
  themeMgr.setDarkAlias('hify-dark')
})

onMounted(() => {
  window.addEventListener('toggle-lyrics', toggleLyrics)
  window.addEventListener('open-lyrics', forceOpenLyrics)
})

onUnmounted(() => {
  window.removeEventListener('toggle-lyrics', toggleLyrics)
  window.removeEventListener('open-lyrics', forceOpenLyrics)
})
</script>

<style>
.page-enter-active,
.page-leave-active {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}
.page-enter-from,
.page-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
