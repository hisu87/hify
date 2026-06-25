<template>
  <div
    class="min-h-dvh overflow-x-hidden bg-transparent text-base-content relative z-0"
  >
    <!-- Lucid Dynamic Background -->
    <div class="fixed inset-0 z-[-1] overflow-hidden pointer-events-none">
      <div
        class="absolute inset-[-10%] bg-cover bg-center transition-all duration-[1500ms] ease-out"
        :style="{
          backgroundImage: player.currentTrack.value?.cover
            ? `url(${player.currentTrack.value.cover})`
            : 'none',
          filter: 'blur(60px) saturate(200%)',
          transform: 'scale(1.15)',
        }"
      ></div>
      <div
        class="absolute inset-0 bg-base-300/40 dark:bg-black/60 transition-colors duration-500"
      ></div>
    </div>

    <LyricsView :is-open="isLyricsOpen" @close="isLyricsOpen = false" />
    <Sidebar />
    <router-view v-slot="{ Component, route }">
      <main class="relative min-h-dvh lg:pl-[260px]">
        <div
          class="mx-auto flex min-h-dvh w-full max-w-[1600px] flex-col px-4 pb-[104px] pt-4 sm:px-6 lg:px-8 lg:pb-[96px] lg:pt-6"
        >
          <transition name="page" mode="out-in">
            <component :is="Component" :key="route.fullPath" />
          </transition>
        </div>
      </main>
    </router-view>
    <PlayerBar
      :is-lyrics-open="isLyricsOpen"
      @open-lyrics="isLyricsOpen = !isLyricsOpen"
    />
    <Settings />
  </div>
</template>

<script setup>
import { onBeforeMount, ref } from 'vue'
import PlayerBar from './components/PlayerBar.vue'
import Sidebar from './components/Sidebar.vue'
import Settings from './components/Settings.vue'
import LyricsView from './components/LyricsView.vue'
import { useBinaryThemeManager } from './model/theme'
import { useDynamicTheme } from './model/dynamicTheme'
import { usePlayer } from './model/player'

const isLyricsOpen = ref(false)
const themeMgr = useBinaryThemeManager()
const player = usePlayer()
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
