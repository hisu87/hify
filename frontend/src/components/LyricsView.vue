<template>
  <transition name="lyrics-modal">
    <div
      v-if="isOpen"
      class="lyrics-root fixed inset-0 z-[100] flex flex-col overflow-hidden"
    >
      <!-- ─── Background (blurred album art) ─── -->
      <div class="lyrics-bg" :style="bgStyle"></div>
      <div class="lyrics-bg-overlay"></div>

      <!-- ─── Top Nav ─── -->
      <div class="lyrics-nav">
        <button
          class="icon-btn"
          @click="close"
          title="Close Lyrics"
          id="lyrics-close-btn"
        >
          <Icon icon="clarity:window-min-line" class="h-5 w-5" />
        </button>
        <div class="lyrics-nav-title">Lyrics</div>
        <div style="width: 2.25rem"></div>
      </div>

      <!-- ─── Content ─── -->
      <div class="lyrics-content" ref="scrollerEl">
        <!-- Loading -->
        <div v-if="loading" class="lyrics-state">
          <div class="lyrics-state-dots"><span /><span /><span /></div>
          <p>Loading lyrics…</p>
        </div>

        <!-- Error -->
        <div v-else-if="error" class="lyrics-state opacity-50">
          {{ error }}
        </div>

        <!-- No lyrics -->
        <div v-else-if="!parsedLyrics.length" class="lyrics-state opacity-40">
          No synced lyrics available.
        </div>

        <!-- Lyrics list -->
        <div
          v-else
          class="lyrics-list"
          :style="{ transform: `translate3d(0, ${scrollY}px, 0)` }"
        >
          <!-- Spacer: đẩy dòng đầu ra giữa màn -->
          <div :style="{ height: topPad + 'px' }"></div>

          <div
            v-for="(line, li) in parsedLyrics"
            :key="li"
            class="lyric-line"
            :ref="(el) => registerLineEl(li, el)"
            @click="player.seek(line.time)"
          >
            <!-- Instrument / empty line -->
            <span v-if="!line.words.length" class="lyric-instrument">♪</span>

            <!-- Words -->
            <span
              v-for="(word, wi) in line.words"
              :key="wi"
              class="lyric-word"
              :ref="(el) => registerWordEl(li, wi, el)"
            >
              <!-- Faded base layer -->
              <span class="word-base">{{ word.text }}</span>
              <!-- Animated highlight layer — filled by --fill-pct CSS var -->
              <span class="word-hl">{{ word.text }}</span>
            </span>
          </div>

          <!-- Bottom spacer -->
          <div :style="{ height: botPad + 'px' }"></div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { Icon } from '@iconify/vue'
import { usePlayer } from '../model/player'
import { parseLrc } from '../utils/lyrics/LrcParser.js'
import { LyricsAnimator } from '../utils/lyrics/LyricsAnimator.js'

// ─── Props / Emits ────────────────────────────────────────────────────────────
const props = defineProps({ isOpen: Boolean })
const emit = defineEmits(['close'])

// ─── Player ───────────────────────────────────────────────────────────────────
const player = usePlayer()
const currentTrack = computed(() => player.currentTrack.value)

// ─── State ────────────────────────────────────────────────────────────────────
const loading = ref(false)
const error = ref('')
const parsedLyrics = ref([])

// Scroll
const scrollerEl = ref(null)
const scrollY = ref(0)
const topPad = ref(200)
const botPad = ref(300)
const activeLineIdx = ref(-1)

// ─── Lyrics cache ─────────────────────────────────────────────────────────────
const lyricsCache = new Map()
const lyricsRequests = new Map()

// ─── Animator ─────────────────────────────────────────────────────────────────
const animator = new LyricsAnimator()
animator.getTime = () => player.currentTime.value

// Line element refs
const lineElMap = new Map()

animator.onFrame = ({ activeLineIdx: ali, scrollSpringPos }) => {
  if (ali !== activeLineIdx.value) {
    activeLineIdx.value = ali
    updateScrollGoal(ali)
  }
  scrollY.value = scrollSpringPos
}

function registerWordEl(li, wi, el) {
  if (el) {
    animator.registerWord(li, wi, el)
  } else {
    animator.unregisterWord(li, wi)
  }
}

function registerLineEl(li, el) {
  if (el) {
    animator.registerLine(li, el)
    lineElMap.set(li, el)
  } else {
    animator.unregisterLine(li)
    lineElMap.delete(li)
  }
}

// ─── Scroll logic ─────────────────────────────────────────────────────────────
function updateScrollGoal(lineIdx) {
  if (lineIdx < 0 || !scrollerEl.value) return
  nextTick(() => {
    const containerH = scrollerEl.value?.clientHeight || 600
    const el = lineElMap.get(lineIdx)
    if (!el) return

    const elTop = el.offsetTop
    const elH = el.offsetHeight
    const center = elTop + elH / 2
    // Scroll goal: đặt active line ở 40% chiều cao (cao hơn trung điểm một chút, giống Apple Music)
    const goal = -(center - containerH * 0.4)
    animator.setScrollGoal(goal)
  })
}

// ─── Background style ─────────────────────────────────────────────────────────
const bgStyle = computed(() => ({
  backgroundImage: currentTrack.value?.cover
    ? `url(${currentTrack.value.cover})`
    : 'none',
}))

// ─── Lifecycle ────────────────────────────────────────────────────────────────
watch(
  () => props.isOpen,
  (open) => {
    if (open) {
      fetchLyrics()
      animator.start()
    } else {
      animator.stop()
    }
  }
)

watch(
  () => currentTrack.value?.title,
  (newTitle) => {
    if (newTitle) prefetchLyrics()
    if (props.isOpen) {
      parsedLyrics.value = []
      activeLineIdx.value = -1
      scrollY.value = 0
      animator.setLines([])
      fetchLyrics()
    }
  }
)

onUnmounted(() => {
  animator.stop()
})

function close() {
  emit('close')
}

// ─── Fetch ────────────────────────────────────────────────────────────────────
async function prefetchLyrics() {
  if (!currentTrack.value) return
  const key = cacheKey()
  if (lyricsCache.has(key)) return
  try {
    await getLyrics(key)
  } catch {
    // keep prefetch silent
  }
}

async function fetchLyrics() {
  if (!currentTrack.value) return
  const key = cacheKey()
  if (lyricsCache.has(key)) {
    applyLyrics(lyricsCache.get(key))
    return
  }
  loading.value = true
  error.value = ''
  try {
    const lines = await getLyrics(key)
    if (cacheKey() === key) applyLyrics(lines)
  } catch (err) {
    if (cacheKey() === key) {
      error.value = err.message || 'Error loading lyrics'
      loading.value = false
    }
  }
}

function cacheKey() {
  const t = currentTrack.value
  return `${t?.title || ''}|${t?.artist || ''}`
}

async function getLyrics(key) {
  if (lyricsCache.has(key)) return lyricsCache.get(key)
  if (lyricsRequests.has(key)) return lyricsRequests.get(key)

  const request = doFetch(key).finally(() => {
    lyricsRequests.delete(key)
  })
  lyricsRequests.set(key, request)
  return request
}

async function doFetch(key) {
  const t = currentTrack.value
  if (!t) throw new Error('No track selected')

  const params = new URLSearchParams()
  if (t.title) params.append('track_name', t.title)
  if (t.artist) params.append('artist_name', t.artist)

  const res = await fetch(`https://lrclib.net/api/get?${params}`)
  if (!res.ok)
    throw new Error(
      res.status === 404 ? 'Lyrics not found' : 'Failed to fetch lyrics'
    )

  const data = await res.json()
  let lines = []

  if (data.syncedLyrics) {
    lines = parseLrc(data.syncedLyrics)
  } else if (data.plainLyrics) {
    // plain: treat each line as a single word block
    lines = data.plainLyrics
      .split('\n')
      .filter(Boolean)
      .map((text, i) => ({
        time: i * 3,
        duration: 3,
        text,
        hasWordTiming: false,
        words: text
          .split(/\s+/)
          .filter(Boolean)
          .map((w, wi, arr) => ({
            text: w,
            delay: (wi / arr.length) * 3,
            duration: 3 / arr.length,
          })),
      }))
  } else {
    throw new Error('No lyrics available')
  }

  lyricsCache.set(key, lines)
  return lines
}

function applyLyrics(lines) {
  parsedLyrics.value = lines
  loading.value = false
  error.value = ''
  animator.setLines(lines)

  // Jump scroll to active line on open
  nextTick(() => {
    const now = player.currentTime.value
    let startIdx = 0
    for (let i = lines.length - 1; i >= 0; i--) {
      if (now >= lines[i].time - 0.25) {
        startIdx = i
        break
      }
    }
    // snap scroll spring to position
    const containerH = scrollerEl.value?.clientHeight || 600
    const el = lineElMap.get(startIdx)
    if (el) {
      const center = el.offsetTop + el.offsetHeight / 2
      const snap = -(center - containerH * 0.4)
      animator._scrollSpring.snapTo(snap)
      scrollY.value = snap
    }
    activeLineIdx.value = startIdx
  })
}
</script>

<style scoped>
/* ─── Root ───────────────────────────────────────────────────────────────────── */
.lyrics-root {
  color: white;
  font-family:
    'Tahoma',
    'Geneva',
    sans-serif;
}

/* ─── Background ─────────────────────────────────────────────────────────────── */
.lyrics-bg {
  position: absolute;
  inset: -10%;
  z-index: 0;
  background-size: cover;
  background-position: center;
  filter: blur(70px) saturate(180%) brightness(0.6);
  transform: scale(1.15);
  transition: background-image 1.2s ease;
}
.lyrics-bg-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: rgba(0, 0, 0, 0.62);
  backdrop-filter: blur(4px);
}

/* ─── Nav ────────────────────────────────────────────────────────────────────── */
.lyrics-nav {
  position: relative;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 72px;
  padding: 0 1.5rem;
  flex-shrink: 0;
}
.lyrics-nav-title {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.45;
}

/* ─── Content area ───────────────────────────────────────────────────────────── */
.lyrics-content {
  position: relative;
  z-index: 10;
  flex: 1;
  overflow: hidden;
  /* Vertical mask: fade top & bottom 15% */
  mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 12%,
    black 82%,
    transparent 100%
  );
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 12%,
    black 82%,
    transparent 100%
  );
}

/* ─── Lyrics list ────────────────────────────────────────────────────────────── */
.lyrics-list {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  will-change: transform;
  padding: 0 clamp(1.25rem, 5vw, 4rem);
  /* Prevent text selection while animating */
  user-select: none;
}

/* ─── Line ───────────────────────────────────────────────────────────────────── */
.lyric-line {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  width: 100%;
  padding: 0.4rem 0;
  margin-bottom: 0.5rem;
  line-height: 1.1;
  cursor: pointer;
  /* GPU hint for blur animation */
  will-change: filter;
}

.lyric-instrument {
  font-size: clamp(1.8rem, 4vw, 3rem);
  opacity: 0.3;
  padding: 0.3rem 0;
}

/* ─── Word ───────────────────────────────────────────────────────────────────── */
.lyric-word {
  /* Inline-grid: base and hl layers stacked exactly */
  display: inline-grid;
  margin-right: 0.18em;
  margin-bottom: 0.15em;
  transform-origin: bottom center;
  cursor: pointer;
  /* Spring will write transform — GPU composited */
  will-change: transform, filter;
  backface-visibility: hidden;
  /* Glow via CSS custom properties written by spring */
  filter:
    drop-shadow(0 0 var(--glow-blur, 0px) rgba(255, 255, 255, var(--glow-opacity, 0)))
    drop-shadow(0 0 calc(var(--glow-blur, 0px) * 2.5) rgba(255, 255, 255, calc(var(--glow-opacity, 0) * 0.5)));
}

/* Base (faded) layer */
.word-base {
  grid-column: 1;
  grid-row: 1;
  color: white;
  font-size: clamp(1.6rem, 4.5vw, 3.75rem);
  font-weight: 900;
  letter-spacing: -0.025em;
  /* opacity set by spring via AnimatorStore */
  opacity: 0.28;
}

/* Highlight (filled) layer */
.word-hl {
  grid-column: 1;
  grid-row: 1;
  font-size: clamp(1.6rem, 4.5vw, 3.75rem);
  font-weight: 900;
  letter-spacing: -0.025em;
  white-space: nowrap;
  color: white;
  /* Gradient fill: --fill-pct is written by spring each frame */
  /* Feather region is BEHIND the fill point to avoid white leading-edge artifact */
  -webkit-mask-image: linear-gradient(
    90deg,
    black calc(var(--fill-pct, 0%) - 18%),
    transparent var(--fill-pct, 0%),
    transparent 100%
  );
  mask-image: linear-gradient(
    90deg,
    black calc(var(--fill-pct, 0%) - 18%),
    transparent var(--fill-pct, 0%),
    transparent 100%
  );
  /* opacity set by spring */
  opacity: 0.01;
  will-change:
    opacity,
    mask-image,
    -webkit-mask-image;
}

/* ─── State screens ──────────────────────────────────────────────────────────── */
.lyrics-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 1rem;
  font-size: 1.1rem;
  font-weight: 500;
  color: white;
  opacity: 0.5;
}

/* Loading dots animation */
.lyrics-state-dots {
  display: flex;
  gap: 0.5rem;
}
.lyrics-state-dots span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: white;
  opacity: 0.7;
  animation: dot-bounce 1.4s ease-in-out infinite both;
}
.lyrics-state-dots span:nth-child(1) {
  animation-delay: 0s;
}
.lyrics-state-dots span:nth-child(2) {
  animation-delay: 0.2s;
}
.lyrics-state-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dot-bounce {
  0%,
  80%,
  100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* ─── Modal transition ───────────────────────────────────────────────────────── */
.lyrics-modal-enter-active,
.lyrics-modal-leave-active {
  transition:
    opacity 0.4s ease,
    transform 0.4s cubic-bezier(0.32, 0.72, 0, 1);
}
.lyrics-modal-enter-from,
.lyrics-modal-leave-to {
  opacity: 0;
  transform: translateY(24px);
}

/* ─── Icon button ────────────────────────────────────────────────────────────── */
.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  cursor: pointer;
  color: white;
  transition: background 0.2s;
}
.icon-btn:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
