<template>
  <div
    class="min-h-dvh overflow-x-hidden bg-transparent text-base-content relative z-0"
  >
    <!-- Lucid Dynamic Background (Gradient Bleed) -->
    <div
      class="fixed inset-0 z-[-1] overflow-hidden pointer-events-none transition-colors duration-1000 ease-out"
      style="
        background: linear-gradient(
          to bottom,
          var(--dynamic-bg-light),
          transparent
        );
      "
    >
      <!-- The Bleed Blob -->
      <div
        class="absolute top-1/2 left-1/2 w-3/4 h-3/4 -translate-x-1/2 -translate-y-1/2 rounded-full transition-colors duration-1000 ease-out"
        style="
          background-color: var(--dynamic-bg-dark);
          filter: blur(150px);
          transform: translate(-50%, -50%) scale(1.2);
        "
      ></div>
      <div
        class="absolute inset-0 bg-base-300/40 dark:bg-black/60 transition-colors duration-500"
      ></div>
    </div>

    <LyricsView :is-open="isLyricsOpen" @close="isLyricsOpen = false" />
    <div
      class="flex min-h-dvh w-full overflow-hidden transition-[padding] duration-300"
      :class="
        route?.name === 'Player'
          ? 'pb-[calc(64px_+_env(safe-area-inset-bottom))] lg:pb-0'
          : 'pb-[calc(136px_+_env(safe-area-inset-bottom))] lg:pb-[96px]'
      "
    >
      <Sidebar />
      <main class="relative flex-1 min-w-0 transition-all duration-300">
        <div
          class="mx-auto flex w-full max-w-[1600px] flex-col px-4 pt-4 sm:px-6 lg:px-8 lg:pt-6"
        >
          <router-view v-slot="{ Component, route }">
            <transition name="page" mode="out-in">
              <component :is="Component" :key="route.fullPath" />
            </transition>
          </router-view>
        </div>
      </main>
      <NowPlayingSidebar />
    </div>
    <PlayerBar
      v-show="route?.name !== 'Player'"
      :is-lyrics-open="isLyricsOpen"
      @open-lyrics="isLyricsOpen = !isLyricsOpen"
    />
    <MobileNav />
    <Settings />
  </div>
</template>

<script setup>
import { onBeforeMount, ref } from 'vue'
import { useRoute } from 'vue-router'
import PlayerBar from './components/PlayerBar.vue'
import Sidebar from './components/Sidebar.vue'
import NowPlayingSidebar from './components/NowPlayingSidebar.vue'
import Settings from './components/Settings.vue'
import LyricsView from './components/LyricsView.vue'
import MobileNav from './components/MobileNav.vue'
import { useBinaryThemeManager } from './model/theme'
import { useDynamicTheme } from './model/dynamicTheme'
import { usePlayer } from './model/player'
import { useLayout } from './model/layout'

const isLyricsOpen = ref(false)
const route = useRoute()
const themeMgr = useBinaryThemeManager()
const player = usePlayer()
const layout = useLayout()
useDynamicTheme()
onBeforeMount(() => {
  themeMgr.setLightAlias('downtify-light')
  themeMgr.setDarkAlias('downtify-dark')
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
