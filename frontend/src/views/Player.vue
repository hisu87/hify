<template>
  <div class="min-h-screen flex flex-col w-full relative pb-28">
    <!-- Header -->
    <div
      class="px-4 py-8 sm:px-6 xl:px-12 shrink-0 flex items-center justify-between"
    >
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-white drop-shadow-md">
          {{ t('player.title') }}
        </h1>
        <p class="mt-1 text-base text-white/70 drop-shadow">
          {{ t('player.subtitle') }}
        </p>
      </div>
      <!-- Open Fullscreen shortcut -->
      <button
        class="icon-btn-large hidden lg:flex"
        @click="openFullscreenLyrics"
        title="Full Screen Overlay"
      >
        <Icon icon="clarity:window-max-line" class="h-6 w-6" />
      </button>
    </div>

    <!-- Empty state -->
    <div
      v-if="player.playlist.value.length === 0 && !loading"
      class="flex-1 flex flex-col items-center justify-center text-center p-8"
    >
      <Icon
        icon="clarity:headphones-line"
        class="h-16 w-16 text-white/30 mb-4 drop-shadow"
      />
      <p class="text-white/60 text-lg drop-shadow">{{ t('player.empty') }}</p>
      <p class="text-white/50 text-sm mt-2 drop-shadow">
        {{ t('player.emptyHint') }}
      </p>
    </div>

    <!-- Skeleton -->
    <div
      v-else-if="loading && !player.currentTrack.value"
      class="flex-1 flex items-center justify-center"
    >
      <div class="space-y-4 w-full max-w-md">
        <div class="skeleton h-96 w-full rounded-[2.5rem] bg-white/10" />
        <div class="skeleton h-8 w-3/4 rounded-xl bg-white/10" />
        <div class="skeleton h-6 w-1/2 rounded-xl bg-white/10" />
      </div>
    </div>

    <!-- Player + queue/lyrics -->
    <div
      v-else
      class="flex-1 grid gap-10 lg:grid-cols-2 px-4 pb-8 sm:px-6 xl:px-12 w-full max-w-[1920px] mx-auto min-h-0"
    >
      <!-- Player Section (Left) -->
      <section
        class="flex flex-col items-center xl:items-start justify-center text-center xl:text-left h-full"
      >
        <!-- Massive Cover -->
        <div
          class="relative h-72 w-72 sm:h-80 sm:w-80 xl:h-[28rem] xl:w-[28rem] rounded-[2.5rem] bg-black/20 text-white flex items-center justify-center overflow-hidden shadow-2xl ring-1 ring-white/10"
          :class="{ 'pulse-glow-large': player.isPlaying.value }"
        >
          <img
            v-if="
              player.currentTrack.value &&
              player.currentTrack.value.cover &&
              !coverFailed[player.currentTrack.value.file]
            "
            :src="player.currentTrack.value.cover"
            :alt="player.currentTrack.value.title"
            class="absolute inset-0 h-full w-full object-cover"
            @error="markCoverFailed(player.currentTrack.value.file)"
          />
          <img
            v-else
            src="../assets/14882.png"
            class="h-32 w-32 object-contain opacity-60 drop-shadow-md"
          />
          <div
            v-if="player.isPlaying.value"
            class="absolute bottom-6 right-6 equalizer h-8"
            aria-hidden="true"
          >
            <span></span><span></span><span></span>
          </div>
        </div>

        <!-- Title / artist -->
        <div class="mt-12 w-full max-w-[28rem]">
          <p
            class="text-3xl sm:text-4xl font-extrabold tracking-tight truncate text-white drop-shadow-lg"
          >
            {{ trackTitle }}
          </p>
          <p
            class="text-lg sm:text-xl text-white/70 truncate mt-2 font-medium drop-shadow-md"
          >
            {{ trackArtist }}
          </p>
        </div>

        <!-- Progress -->
        <div class="mt-10 w-full max-w-[28rem]">
          <div
            class="relative h-3 rounded-full bg-black/30 overflow-hidden cursor-pointer group shadow-inner ring-1 ring-white/10"
            ref="progressBar"
            @click="onSeekClick"
            @pointerdown="onSeekStart"
          >
            <div
              class="h-full bg-white transition-[width] duration-150 shadow-[0_0_15px_rgba(255,255,255,0.8)]"
              :style="`width: ${player.progressPct.value}%`"
            />
            <div
              class="absolute top-1/2 -translate-y-1/2 h-5 w-5 rounded-full bg-white shadow-[0_0_20px_rgba(255,255,255,1)] transition-all duration-150 opacity-0 group-hover:opacity-100"
              :style="`left: calc(${player.progressPct.value}% - 10px)`"
            />
          </div>
          <div
            class="mt-3 flex items-center justify-between text-sm text-white/60 font-semibold tabular-nums drop-shadow"
          >
            <span>{{ formatTime(player.currentTime.value) }}</span>
            <span>{{ formatTime(player.duration.value) }}</span>
          </div>
        </div>

        <!-- Transport -->
        <div
          class="mt-8 flex items-center justify-center xl:justify-start gap-5 xl:gap-8 w-full max-w-[28rem]"
        >
          <button
            class="icon-btn-large"
            :class="{
              'text-primary drop-shadow-[0_0_12px_rgba(26,208,92,0.5)]':
                player.shuffle.value,
            }"
            @click="player.toggleShuffle()"
            :title="
              player.shuffle.value
                ? t('player.shuffleOn')
                : t('player.shuffleOff')
            "
          >
            <Icon icon="clarity:shuffle-line" class="h-6 w-6" />
          </button>
          <button
            class="icon-btn-large"
            @click="player.prev()"
            :title="t('player.previous')"
            :disabled="player.playlist.value.length === 0"
          >
            <Icon
              icon="clarity:step-forward-2-line"
              class="h-8 w-8 -scale-x-100"
            />
          </button>
          <button
            class="inline-flex h-20 w-20 items-center justify-center rounded-full bg-white text-black shadow-[0_0_30px_rgba(255,255,255,0.3)] hover:scale-105 active:scale-95 transition-all duration-300 disabled:opacity-50"
            @click="player.toggle()"
            :disabled="player.playlist.value.length === 0"
            :title="
              player.isPlaying.value ? t('player.pause') : t('player.play')
            "
          >
            <Icon
              :icon="
                player.isPlaying.value
                  ? 'clarity:pause-solid'
                  : 'clarity:play-solid'
              "
              class="h-10 w-10"
            />
          </button>
          <button
            class="icon-btn-large"
            @click="player.next()"
            :title="t('player.next')"
            :disabled="player.playlist.value.length === 0"
          >
            <Icon icon="clarity:step-forward-2-line" class="h-8 w-8" />
          </button>
          <button
            class="icon-btn-large relative"
            :class="{
              'text-primary drop-shadow-[0_0_12px_rgba(26,208,92,0.5)]':
                player.repeatMode.value !== 'off',
            }"
            @click="player.cycleRepeat()"
            :title="repeatTitle"
          >
            <Icon icon="clarity:refresh-line" class="h-6 w-6" />
            <span
              v-if="player.repeatMode.value === 'one'"
              class="absolute -bottom-1 -right-1 h-5 min-w-[1.25rem] px-1 rounded-full bg-primary text-black text-[10px] font-extrabold flex items-center justify-center shadow-md"
            >
              1
            </span>
          </button>
        </div>

        <!-- Volume -->
        <div class="mt-10 w-full max-w-[28rem] flex items-center gap-4">
          <button
            class="icon-btn-large"
            @click="player.toggleMute()"
            :title="
              player.isMuted.value ? t('player.unmute') : t('player.mute')
            "
          >
            <Icon
              :icon="
                player.isMuted.value || player.volume.value === 0
                  ? 'clarity:volume-mute-line'
                  : player.volume.value < 0.5
                    ? 'clarity:volume-down-line'
                    : 'clarity:volume-up-line'
              "
              class="h-6 w-6"
            />
          </button>
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            :value="player.isMuted.value ? 0 : player.volume.value"
            @input="onVolume($event)"
            class="player-range-large flex-1"
            :title="t('player.volume')"
          />
        </div>
      </section>

      <!-- Immersive Lyrics / Queue Section (Right) -->
      <aside
        class="flex flex-col h-[600px] lg:h-full w-full relative rounded-[2.5rem] overflow-hidden bg-black/10 backdrop-blur-xl ring-1 ring-white/10 shadow-2xl"
      >
        <!-- Tab Selector -->
        <div
          class="flex items-center justify-center gap-10 py-5 shrink-0 relative z-10 border-b border-white/10 bg-black/20"
        >
          <button
            class="text-sm font-extrabold uppercase tracking-[0.2em] transition-all duration-300"
            :class="
              activeTab === 'lyrics'
                ? 'text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.8)] scale-105'
                : 'text-white/40 hover:text-white/80'
            "
            @click="activeTab = 'lyrics'"
          >
            Lyrics
          </button>
          <button
            class="text-sm font-extrabold uppercase tracking-[0.2em] transition-all duration-300"
            :class="
              activeTab === 'queue'
                ? 'text-white drop-shadow-[0_0_12px_rgba(255,255,255,0.8)] scale-105'
                : 'text-white/40 hover:text-white/80'
            "
            @click="activeTab = 'queue'"
          >
            {{ t('player.queue') }}
          </button>
        </div>

        <!-- Tab: Lyrics -->
        <div
          v-show="activeTab === 'lyrics'"
          class="flex-1 relative w-full h-full min-h-0 lyrics-container-large"
        >
          <LyricsView inline />
        </div>

        <!-- Tab: Queue -->
        <div
          v-show="activeTab === 'queue'"
          class="flex-1 overflow-y-auto min-h-0 p-4 sm:p-6 relative z-10 custom-scrollbar"
        >
          <ul v-if="paginatedQueue.length > 0" class="space-y-2">
            <li
              v-for="item in paginatedQueue"
              :key="item.track.file + '-' + item.idx"
              class="rounded-2xl px-4 py-3 flex items-center gap-4 cursor-pointer transition-all duration-200"
              :class="
                item.idx === player.currentIndex.value
                  ? 'bg-white/20 shadow-lg ring-1 ring-white/30'
                  : 'hover:bg-white/10'
              "
              @click="onPick(item.idx)"
            >
              <div
                class="relative h-14 w-14 shrink-0 rounded-xl overflow-hidden flex items-center justify-center bg-black/40 shadow-inner"
              >
                <img
                  v-if="!coverFailed[item.track.file]"
                  :src="item.track.cover"
                  :alt="item.track.title"
                  class="absolute inset-0 h-full w-full object-cover"
                  loading="lazy"
                  @error="markCoverFailed(item.track.file)"
                />
                <span
                  v-if="
                    item.idx === player.currentIndex.value && player.isPlaying.value
                  "
                  class="relative equalizer h-5"
                  aria-hidden="true"
                >
                  <span></span><span></span><span></span>
                </span>
                <Icon
                  v-else-if="coverFailed[item.track.file]"
                  icon="clarity:music-note-line"
                  class="h-6 w-6 text-white/50"
                />
              </div>
              <div class="flex-1 min-w-0">
                <p
                  class="text-base font-bold text-white truncate drop-shadow-sm"
                >
                  {{ item.track.title }}
                </p>
                <p class="text-sm font-medium text-white/50 truncate">
                  {{ item.track.artist || t('common.unknownArtist') }}
                </p>
              </div>
              <div class="text-xs text-white/40 font-mono shrink-0 pl-2">
                {{ formatTime(item.track.duration_ms / 1000) }}
              </div>
            </li>
          </ul>
          
          <!-- Pagination Controls -->
          <div
            v-if="totalQueuePages > 1"
            class="mt-6 mb-2 flex items-center justify-center gap-4"
          >
            <button
              class="icon-btn hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent"
              @click="prevQueuePage"
              :disabled="queuePage <= 1"
            >
              <Icon icon="clarity:angle-left-line" class="h-5 w-5" />
            </button>
            <span class="text-sm font-bold text-white/60">
              {{ queuePage }} / {{ totalQueuePages }}
            </span>
            <button
              class="icon-btn hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent"
              @click="nextQueuePage"
              :disabled="queuePage >= totalQueuePages"
            >
              <Icon icon="clarity:angle-right-line" class="h-5 w-5" />
            </button>
          </div>

          <div v-else-if="paginatedQueue.length === 0" class="text-center py-24">
            <p class="text-white/50 text-xl font-semibold">
              {{ t('player.empty') }}
            </p>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'
import API from '/src/model/api'
import { usePlayer, formatTime, trackInfoFromFile } from '/src/model/player'
import { useI18n } from '/src/i18n'
import LyricsView from '/src/components/LyricsView.vue'

const { t } = useI18n()
const player = usePlayer()
const router = useRouter()

const activeTab = ref('queue') // 'queue' | 'lyrics'

const loading = ref(false)
const progressBar = ref(null)
const coverFailed = ref({})
let dragging = false

function coverUrlFor(file) {
  return API.coverFileURL(file)
}

function markCoverFailed(file) {
  coverFailed.value = { ...coverFailed.value, [file]: true }
}

async function load() {
  loading.value = true
  try {
    // If the player was completely empty, seed the playlist
    // with the library so the user has something to play.
    if (player.playlist.value.length === 0) {
      const res = await API.listDownloads()
      if (res.data && res.data.length > 0) {
        player.setPlaylist(res.data)
      }
    }
  } finally {
    loading.value = false
  }
}

function onPick(idx) {
  player.playAt(idx)
}

function trackInfo(file) {
  return trackInfoFromFile(file)
}

const trackTitle = computed(() => {
  const c = player.currentTrack.value
  if (c && c.title) return c.title
  return t('player.empty')
})

const trackArtist = computed(() => {
  const c = player.currentTrack.value
  if (c && c.artist) return c.artist
  if (c) return t('common.unknownArtist')
  return ''
})

const repeatTitle = computed(() => {
  if (player.repeatMode.value === 'one') return t('player.repeatOne')
  if (player.repeatMode.value === 'all') return t('player.repeatAll')
  return t('player.repeatOff')
})

function onVolume(e) {
  player.setVolume(parseFloat(e.target.value))
}

function ratioFromEvent(e) {
  const el = progressBar.value
  if (!el) return 0
  const rect = el.getBoundingClientRect()
  const x = (e.clientX || 0) - rect.left
  return Math.max(0, Math.min(1, x / rect.width))
}

function onSeekClick(e) {
  player.seekRatio(ratioFromEvent(e))
}

function onSeekStart(e) {
  dragging = true
  player.seekRatio(ratioFromEvent(e))
  window.addEventListener('pointermove', onSeekDrag)
  window.addEventListener('pointerup', onSeekEnd, { once: true })
}

function onSeekDrag(e) {
  if (!dragging) return
  player.seekRatio(ratioFromEvent(e))
}

function onSeekEnd() {
  dragging = false
  window.removeEventListener('pointermove', onSeekDrag)
}

onMounted(() => {
  window.scroll(0, 0)
  load()
})

onUnmounted(() => {
  window.removeEventListener('pointermove', onSeekDrag)
})

const openFullscreenLyrics = () => {
  router.push('/lyrics')
}

// Pagination logic
const queuePage = ref(1)
const queuePageSize = 8

const paginatedQueue = computed(() => {
  const start = (queuePage.value - 1) * queuePageSize
  const end = start + queuePageSize
  return player.playlist.value
    .map((track, idx) => ({ track, idx }))
    .slice(start, end)
})

const totalQueuePages = computed(() => Math.max(1, Math.ceil(player.playlist.value.length / queuePageSize)))

function prevQueuePage() {
  if (queuePage.value > 1) queuePage.value--
}

function nextQueuePage() {
  if (queuePage.value < totalQueuePages.value) queuePage.value++
}

watch(() => player.currentIndex.value, (newIdx) => {
  if (newIdx >= 0 && player.playlist.value.length > 0) {
    queuePage.value = Math.floor(newIdx / queuePageSize) + 1
  }
})
</script>

<style scoped>
.player-range-large {
  -webkit-appearance: none;
  appearance: none;
  background: rgba(255, 255, 255, 0.2);
  height: 6px;
  border-radius: 9999px;
  outline: none;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.3);
}
.player-range-large::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  height: 20px;
  width: 20px;
  border-radius: 9999px;
  background: white;
  cursor: pointer;
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
}
.player-range-large::-moz-range-thumb {
  height: 20px;
  width: 20px;
  border-radius: 9999px;
  background: white;
  border: none;
  cursor: pointer;
  box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
}

.icon-btn-large {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 3.5rem;
  height: 3.5rem;
  border-radius: 50%;
  background: transparent;
  border: none;
  cursor: pointer;
  color: white;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0.8;
}
.icon-btn-large:hover {
  background: rgba(255, 255, 255, 0.1);
  opacity: 1;
  transform: scale(1.05);
}

.pulse-glow-large {
  animation: glow-large 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}
@keyframes glow-large {
  0%,
  100% {
    box-shadow: 0 0 60px var(--dynamic-bg-dark, rgba(0, 0, 0, 0.5));
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 120px var(--dynamic-bg-dark, rgba(0, 0, 0, 0.8));
    transform: scale(1.02);
  }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Ensure LyricsView scales properly inside the new massive container */
:deep(.lyrics-inline-mode) {
  padding: 0 !important;
  margin: 0 !important;
  background: transparent !important;
}
</style>
