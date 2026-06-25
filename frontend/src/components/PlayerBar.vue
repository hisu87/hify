<template>
  <footer class="glass-player-bar fixed inset-x-0 bottom-0 z-[110]">
    <div
      class="mx-auto grid h-[88px] w-full max-w-[1600px] grid-cols-1 gap-4 px-4 py-2.5 sm:px-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)_minmax(0,1fr)] lg:px-8"
    >
      <div class="flex min-w-0 items-center gap-3">
        <div
          class="relative h-14 w-14 shrink-0 overflow-hidden rounded-lg bg-base-200 shadow-sm border border-black/5 dark:border-white/10"
        >
          <img
            v-if="currentTrack && !coverFailed"
            :src="currentTrack.cover"
            :alt="currentTrack.title"
            class="absolute inset-0 h-full w-full object-cover"
            @error="coverFailed = true"
          />
          <div
            v-else
            class="flex h-full w-full items-center justify-center bg-gradient-to-br from-[#FA233B]/25 to-[#ff8f9f]/10 text-[#FA233B]"
          >
            <Icon icon="clarity:music-note-line" class="h-6 w-6" />
          </div>
        </div>

        <div class="min-w-0 flex-1">
          <p
            class="truncate text-sm font-semibold tracking-tight text-base-content"
          >
            {{ trackTitle }}
          </p>
          <p class="truncate text-xs font-medium text-base-content/55">
            {{ trackArtist }}
          </p>
        </div>
      </div>

      <div class="flex min-w-0 flex-col items-center justify-center gap-1.5">
        <div class="flex items-center gap-2 sm:gap-3">
          <button
            class="icon-btn"
            @click="player.prev()"
            :disabled="!hasTracks"
            title="Previous"
          >
            <Icon
              icon="clarity:step-forward-2-line"
              class="h-5 w-5 -scale-x-100"
            />
          </button>

          <button
            class="inline-flex h-12 w-12 items-center justify-center rounded-full bg-[#FA233B] text-white shadow-[0_0_24px_rgba(250,35,59,0.25)] transition-[transform,box-shadow] duration-300 ease-[cubic-bezier(0.25,0.1,0.25,1)] hover:scale-105 active:scale-95 disabled:opacity-50"
            @click="player.toggle()"
            :disabled="!hasTracks"
            :title="player.isPlaying.value ? 'Pause' : 'Play'"
          >
            <Icon
              :icon="
                player.isPlaying.value
                  ? 'clarity:pause-solid'
                  : 'clarity:play-solid'
              "
              class="h-5 w-5"
            />
          </button>

          <button
            class="icon-btn"
            @click="player.next()"
            :disabled="!hasTracks"
            title="Next"
          >
            <Icon icon="clarity:step-forward-2-line" class="h-5 w-5" />
          </button>
        </div>

        <div class="flex w-full max-w-xl items-center gap-3">
          <span
            class="w-9 shrink-0 text-right text-[11px] tabular-nums text-base-content/45"
          >
            {{ formatTime(player.currentTime.value) }}
          </span>

          <div
            class="group relative h-5 flex-1 cursor-pointer items-center"
            @click="onSeekClick"
            @pointerdown="onSeekStart"
          >
            <div
              class="absolute top-1/2 h-1 w-full -translate-y-1/2 rounded-full bg-black/10 dark:bg-white/10"
            />
            <div
              class="player-progress-fill absolute top-1/2 h-1 -translate-y-1/2 rounded-full transition-[width] duration-150"
              :style="`width: ${player.progressPct.value}%`"
            />
            <div
              class="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-white border border-black/5 dark:border-white/10 opacity-0 shadow-[0_2px_6px_rgba(0,0,0,0.2)] transition-all duration-150 group-hover:opacity-100"
              :style="`left: calc(${player.progressPct.value}% - 6px)`"
            />
          </div>

          <span
            class="w-9 shrink-0 text-[11px] tabular-nums text-base-content/45"
          >
            {{ formatTime(player.duration.value) }}
          </span>
        </div>
      </div>

      <div class="flex items-center justify-end gap-2 lg:gap-3">
        <button
          class="icon-btn"
          :class="{ 'icon-btn-active': player.shuffle.value }"
          @click="player.toggleShuffle()"
          :title="player.shuffle.value ? 'Shuffle on' : 'Shuffle off'"
        >
          <Icon icon="clarity:shuffle-line" class="h-5 w-5" />
        </button>

        <button
          class="icon-btn"
          @click="router.push({ name: 'Download' })"
          title="Queue"
        >
          <Icon icon="clarity:download-line" class="h-5 w-5" />
        </button>

        <button
          class="icon-btn hidden sm:inline-flex"
          :class="{ 'icon-btn-active': isLyricsOpen }"
          :disabled="!hasTracks"
          @click="$emit('open-lyrics')"
          title="Lyrics"
        >
          <Icon icon="clarity:note-line" class="h-5 w-5" />
        </button>

        <div
          class="flex w-full max-w-[220px] items-center gap-3 pl-1 sm:w-auto"
        >
          <button
            class="icon-btn shrink-0"
            @click="player.toggleMute()"
            :title="player.isMuted.value ? 'Unmute' : 'Mute'"
          >
            <Icon :icon="volumeIcon" class="h-5 w-5" />
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            :value="player.isMuted.value ? 0 : player.volume.value"
            @input="onVolume($event)"
            class="player-range w-full"
            title="Volume"
          />
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Icon } from '@iconify/vue'

import router from '../router'
import { formatTime, usePlayer } from '../model/player'

const props = defineProps({ isLyricsOpen: Boolean })
const emit = defineEmits(['open-lyrics'])
const player = usePlayer()
const coverFailed = ref(false)

const currentTrack = computed(() => player.currentTrack.value)
const hasTracks = computed(() => player.playlist.value.length > 0)

const trackTitle = computed(() => {
  if (currentTrack.value?.title) return currentTrack.value.title
  return 'Nothing playing'
})

const trackArtist = computed(() => {
  if (currentTrack.value?.artist) return currentTrack.value.artist
  return 'Queue a track to start playback'
})

const volumeIcon = computed(() => {
  if (player.isMuted.value || player.volume.value === 0) {
    return 'clarity:volume-mute-line'
  }
  if (player.volume.value < 0.5) return 'clarity:volume-down-line'
  return 'clarity:volume-up-line'
})

watch(currentTrack, () => {
  coverFailed.value = false
})

function onVolume(event) {
  player.setVolume(Number(event.target.value))
}

function onSeekClick(event) {
  if (!player.duration.value) return
  const rect = event.currentTarget.getBoundingClientRect()
  const ratio = (event.clientX - rect.left) / rect.width
  player.seekRatio(ratio)
}

function onSeekStart(event) {
  onSeekClick(event)
}
</script>
