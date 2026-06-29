<template>
  <div
    class="fixed inset-y-0 right-0 z-[100] w-full sm:w-[400px] transform bg-base-200/95 backdrop-blur-2xl shadow-2xl transition-transform duration-300 ease-[cubic-bezier(0.2,0.8,0.2,1)] pt-[calc(env(safe-area-inset-top)+64px)] pb-[calc(140px+env(safe-area-inset-bottom))] lg:pt-0 lg:pb-[96px] border-l border-black/5 dark:border-white/5 flex flex-col"
    :class="layout.isQueueOpen.value ? 'translate-x-0' : 'translate-x-full'"
  >
    <div
      class="flex items-center justify-between px-6 py-4 border-b border-black/5 dark:border-white/5 shrink-0 lg:mt-6"
    >
      <h2 class="text-xl font-bold tracking-tight text-base-content">Queue</h2>
      <div class="flex items-center gap-2">
        <button
          class="icon-btn"
          :class="{ 'icon-btn-active': player.shuffle.value }"
          @click="player.toggleShuffle()"
          :title="player.shuffle.value ? 'Shuffle on' : 'Shuffle off'"
        >
          <Icon icon="clarity:shuffle-line" class="h-5 w-5" />
        </button>
        <button
          class="icon-btn h-8 w-8 ml-2 lg:hidden"
          @click="layout.toggleQueue()"
        >
          <Icon icon="clarity:window-close-line" class="h-6 w-6" />
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto min-h-0 px-2 py-4">
      <!-- Next in Queue -->
      <div v-if="player.displayQueue.value.length > 0" class="mb-8">
        <div class="flex items-center justify-between px-4 mb-3">
          <h3
            class="text-sm font-semibold tracking-wider text-base-content/50 uppercase"
          >
            Next in Queue
          </h3>
          <button
            class="text-xs font-medium text-base-content/50 hover:text-base-content"
            @click="player.clearQueue()"
          >
            Clear
          </button>
        </div>

        <div class="space-y-1">
          <div
            v-for="(track, idx) in player.displayQueue.value"
            :key="'queue-' + idx"
            class="group relative flex items-center gap-3 rounded-lg p-2 hover:bg-base-content/5 transition-colors"
          >
            <div
              class="relative h-10 w-10 shrink-0 overflow-hidden rounded bg-base-300"
            >
              <img :src="track.cover" class="h-full w-full object-cover" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-base-content">
                {{ track.title }}
              </p>
              <p class="truncate text-xs text-base-content/60">
                {{ track.artist }}
              </p>
            </div>
            <button
              class="icon-btn h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
              @click.stop="player.removeFromQueue(idx)"
              title="Remove from queue"
            >
              <Icon icon="clarity:remove-line" class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <!-- Next from Playlist -->
      <div v-if="upcomingPlaylist.length > 0">
        <div class="px-4 mb-3">
          <h3
            class="text-sm font-semibold tracking-wider text-base-content/50 uppercase"
          >
            Next from Playlist
          </h3>
        </div>

        <div class="space-y-1">
          <div
            v-for="(track, idx) in upcomingPlaylist"
            :key="'pl-' + idx"
            class="group relative flex items-center gap-3 rounded-lg p-2 hover:bg-base-content/5 transition-colors cursor-pointer"
            @click="player.playAt(track.originalIndex)"
          >
            <div
              class="relative h-10 w-10 shrink-0 overflow-hidden rounded bg-base-300"
            >
              <img :src="track.cover" class="h-full w-full object-cover" />
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-base-content">
                {{ track.title }}
              </p>
              <p class="truncate text-xs text-base-content/60">
                {{ track.artist }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="
          player.displayQueue.value.length === 0 &&
          upcomingPlaylist.length === 0
        "
        class="flex flex-col items-center justify-center h-40 text-base-content/40"
      >
        <Icon
          icon="clarity:music-note-line"
          class="h-12 w-12 mb-3 opacity-50"
        />
        <p class="text-sm">Queue is empty</p>
      </div>
    </div>
  </div>

  <!-- Mobile Backdrop -->
  <div
    v-if="layout.isQueueOpen.value"
    class="fixed inset-0 z-[90] bg-black/20 backdrop-blur-sm lg:hidden"
    @click="layout.toggleQueue()"
  />
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { usePlayer } from '../model/player'
import { useLayout } from '../model/layout'

const player = usePlayer()
const layout = useLayout()

const upcomingPlaylist = computed(() => {
  if (player.playlist.value.length === 0 || player.currentIndex.value < 0)
    return []

  const upcoming = []

  if (player.isAutomix.value) {
    // Automix: We don't know the exact future playlist easily since it's dynamic
    // Just show a hint
    const current = player.playlist.value[player.currentIndex.value]
    if (current) {
      upcoming.push({
        title: 'Smart Automix is active',
        artist: 'Next track will be matched dynamically',
        cover: current.cover,
        originalIndex: player.currentIndex.value,
      })
    }
    return upcoming
  }

  if (player.shuffle.value) {
    const pos = player.getShufflePos()
    const order = player.getShuffleOrder()
    for (let i = 1; i < Math.min(20, order.length - pos); i++) {
      const pIdx = order[pos + i]
      upcoming.push({
        ...player.playlist.value[pIdx],
        originalIndex: pIdx,
      })
    }
  } else {
    // Sequential
    const start = player.currentIndex.value + 1
    for (
      let i = start;
      i < Math.min(player.playlist.value.length, start + 20);
      i++
    ) {
      upcoming.push({
        ...player.playlist.value[i],
        originalIndex: i,
      })
    }
  }
  return upcoming
})
</script>
