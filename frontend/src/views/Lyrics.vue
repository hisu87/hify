<template>
  <div class="min-h-screen flex flex-col w-full relative">
    <!-- Header -->
    <div
      class="px-4 py-8 sm:px-6 xl:px-12 shrink-0 flex items-center justify-between z-10 relative"
    >
      <button
        class="icon-btn-large flex items-center justify-center bg-black/20 hover:bg-black/40 backdrop-blur-md rounded-full w-12 h-12 text-white"
        @click="router.back()"
        title="Back"
      >
        <Icon icon="clarity:arrow-left-line" class="h-6 w-6" />
      </button>
      <div class="text-center">
        <h1 class="text-xl font-bold tracking-tight text-white drop-shadow-md">
          {{ player.currentTrack.value?.title || 'Lyrics' }}
        </h1>
        <p class="text-sm text-white/70 drop-shadow">
          {{ player.currentTrack.value?.artist || '' }}
        </p>
      </div>
      <div class="w-12 h-12"></div>
      <!-- Spacer for centering -->
    </div>

    <!-- Lyrics Container -->
    <div class="flex-1 relative w-full h-full min-h-0 z-10 pb-[100px]">
      <LyricsView inline />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import { usePlayer } from '/src/model/player'
import LyricsView from '/src/components/LyricsView.vue'

const router = useRouter()
const player = usePlayer()

onMounted(() => {
  if (!player.currentTrack.value) {
    router.replace('/player')
  }
})
</script>

<style scoped>
.icon-btn-large {
  transition: all 0.2s ease;
}
.icon-btn-large:hover {
  transform: scale(1.05);
}
</style>
