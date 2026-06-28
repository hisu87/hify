<template>
  <transition name="lyrics-modal">
    <div
      v-if="isOpen"
      class="lyrics-root fixed inset-0 z-[100] flex flex-col overflow-hidden"
      @touchstart="onTouchStart"
      @touchend="onTouchEnd"
      @mouseup="cancelScrub"
      @touchend.passive="cancelScrub"
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
          :style="{ transform: `translate3d(0, ${scrollY}px, 0)`, fontFamily: `'${currentFont}', sans-serif` }"
        >
          <!-- Top Spacer -->
          <div :style="{ height: topPad + topSpacerHeight + 'px' }"></div>

          <div
            v-for="item in visibleLines"
            :key="item.index"
            class="lyric-line flex-col"
            :class="[
              getLineClass(item.index),
              `agent-${item.line.agent_id || 'default'}`,
              {
                'scrubbing-active': isScrubbing && scrubLineIdx === item.index,
                'scrubbing-dimmed': isScrubbing && scrubLineIdx !== item.index,
              },
            ]"
            :ref="(el) => registerLineEl(item.index, el)"
            @mousedown="onLineDown(item.index)"
            @touchstart="onLineDown(item.index)"
            @click="onLineClick(item.index, item.line.startTime)"
          >
            <!-- Scrub indicator -->
            <div
              v-if="isScrubbing && scrubLineIdx === item.index"
              class="scrub-indicator"
            >
              <Icon icon="ph:play-fill" class="h-4 w-4 mr-2" />
            </div>

            <!-- Instrument / empty line -->
            <span
              v-if="item.line.isInstrumental || !item.line.lead.length"
              class="lyric-instrument"
            >
              {{ item.line.isInstrumental ? '• • •' : '♪' }}
            </span>

            <!-- Lead Words -->
            <div
              class="lead-words flex flex-wrap"
              :class="getAlignClass(item.index)"
            >
              <span
                v-for="(word, wi) in item.line.lead"
                :key="'lead-' + wi"
                class="lyric-word"
                :data-has-space="word.isTrailingSpace"
                :ref="(el) => registerWordEl(item.index, wi, el, false)"
              >
                <span class="word-base">{{ word.text }}</span>
                <span class="word-hl-wrapper">
                  <span class="word-hl">{{ word.text }}</span>
                </span>
              </span>
            </div>

            <!-- Background Words -->
            <div
              v-if="item.line.background"
              class="bg-words flex flex-wrap scale-75 opacity-70 mt-1"
              :class="getAlignClass(item.index)"
            >
              <span
                v-for="(word, wi) in item.line.background"
                :key="'bg-' + wi"
                class="lyric-word"
                :data-has-space="word.isTrailingSpace"
                :ref="(el) => registerWordEl(item.index, wi, el, true)"
              >
                <span class="word-base">{{ word.text }}</span>
                <span class="word-hl-wrapper">
                  <span class="word-hl">{{ word.text }}</span>
                </span>
              </span>
            </div>
          </div>

          <!-- Bottom spacer -->
          <div :style="{ height: botPad + bottomSpacerHeight + 'px' }"></div>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch, onUnmounted, nextTick } from 'vue'
import { Icon } from '@iconify/vue'
import { usePlayer } from '../model/player'
import api from '../model/api'
import { LyricsAnimator } from '../utils/lyrics/LyricsAnimator.js'

// ─── Props / Emits ────────────────────────────────────────────────────────────
const props = defineProps({ isOpen: Boolean })
const emit = defineEmits(['close'])

// ─── Fonts ────────────────────────────────────────────────────────────────────
const LYRIC_FONTS = [
  'Be Vietnam Pro', 'Inter', 'Plus Jakarta Sans', 'Lexend',
  'Playfair Display', 'Lora', 'Bodoni Moda', 'Cinzel',
  'Patrick Hand', 'Dancing Script', 'Pacifico', 'Caveat',
  'Anton', 'Alfa Slab One', 'Bungee', 'Space Grotesk',
  'Space Mono', 'Courier Prime', 'Comfortaa', 'Prata'
]

const currentFont = ref('Inter')

function updateFontForTrack(track) {
  if (!track) {
    currentFont.value = 'Inter'
    return
  }
  const genre = (track.genre || '').toLowerCase()
  let validGroups = []
  
  if (/(rap|hip-hop|hip hop|dance)/.test(genre)) {
    validGroups = [0, 3] // Groups 1 & 4
  } else if (/(r&b|soul|ballad)/.test(genre)) {
    validGroups = [1, 2] // Groups 2 & 3
  } else if (/(pop|indie)/.test(genre)) {
    validGroups = [0, 1, 2, 3, 4] // All groups
  } else {
    validGroups = [0, 1, 2, 3, 4]
  }
  
  const chosenGroup = validGroups[Math.floor(Math.random() * validGroups.length)]
  const fontInGroup = Math.floor(Math.random() * 4)
  currentFont.value = LYRIC_FONTS[chosenGroup * 4 + fontInGroup]
}

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

// Virtualization
const estimatedLineHeight = 80
const measuredHeights = new Map()
const visibleStartIndex = computed(() => Math.max(0, activeLineIdx.value - 4))
const visibleEndIndex = computed(() =>
  Math.min(parsedLyrics.value.length, activeLineIdx.value + 6)
)
const visibleLines = computed(() => {
  if (parsedLyrics.value.length === 0) return []
  return parsedLyrics.value
    .slice(visibleStartIndex.value, visibleEndIndex.value)
    .map((l, i) => ({ line: l, index: visibleStartIndex.value + i }))
})

const topSpacerHeight = computed(() => {
  let h = 0
  for (let i = 0; i < visibleStartIndex.value; i++) {
    h += measuredHeights.get(i) || estimatedLineHeight
  }
  return h
})

const bottomSpacerHeight = computed(() => {
  let h = 0
  for (let i = visibleEndIndex.value; i < parsedLyrics.value.length; i++) {
    h += measuredHeights.get(i) || estimatedLineHeight
  }
  return h
})

// Scrubbing
const isScrubbing = ref(false)
const scrubLineIdx = ref(-1)

function onLineDown(li) {
  isScrubbing.value = true
  scrubLineIdx.value = li
}

function cancelScrub() {
  if (isScrubbing.value) {
    // Delay slightly to let click register
    setTimeout(() => {
      isScrubbing.value = false
      scrubLineIdx.value = -1
    }, 100)
  }
}

function onLineClick(li, time) {
  player.seek(time)
  isScrubbing.value = false
  scrubLineIdx.value = -1
}

// ─── Lyrics cache ─────────────────────────────────────────────────────────────
const lyricsCache = new Map()
const lyricsRequests = new Map()

// ─── Animator ─────────────────────────────────────────────────────────────────
const animator = new LyricsAnimator()
animator.audioElement = player.getAudio()
animator.isPlaying = () => player.isPlaying.value

// Line element refs
const lineElMap = new Map()

animator.onFrame = ({ activeLineIdx: ali, scrollSpringPos }) => {
  if (ali !== activeLineIdx.value) {
    activeLineIdx.value = ali
    if (!isScrubbing.value) {
      updateScrollGoal(ali)
    }
  }
  if (!isScrubbing.value) {
    scrollY.value = scrollSpringPos
  }
}

function registerWordEl(li, wi, el, isBg) {
  if (el) {
    animator.registerWord(li, wi, el, isBg)
  } else {
    animator.unregisterWord(li, wi, isBg)
  }
}

function registerLineEl(li, el) {
  if (el) {
    animator.registerLine(li, el)
    lineElMap.set(li, el)
    measuredHeights.set(li, el.offsetHeight)
    if (li === activeLineIdx.value && !isScrubbing.value) {
      updateScrollGoal(li)
    }
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
    if (!el) {
      let estimatedY = topPad.value
      for (let i = 0; i < lineIdx; i++) {
        estimatedY += measuredHeights.get(i) || estimatedLineHeight
      }
      animator.setScrollGoal(-(estimatedY - containerH * 0.4))
      return
    }

    const elTop = el.offsetTop
    const elH = el.offsetHeight
    const center = elTop + elH / 2
    const goal = -(center - containerH * 0.4)
    animator.setScrollGoal(goal)
  })
}

// ─── Alignment logic ──────────────────────────────────────────────────────────
function getLineClass(li) {
  const rand = Math.sin(li + 1) * 10000
  const val = rand - Math.floor(rand)
  if (val < 0.33) return 'align-left'
  if (val < 0.66) return 'align-center'
  return 'align-right'
}

function getAlignClass(li) {
  const align = getLineClass(li)
  if (align === 'align-left') return 'justify-start origin-left'
  if (align === 'align-center') return 'justify-center origin-center'
  return 'justify-end origin-right'
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

// ─── Touch gestures ───────────────────────────────────────────────────────────
let touchStartX = 0
let touchStartY = 0

function onTouchStart(event) {
  if (event.touches.length !== 1) return
  touchStartX = event.touches[0].screenX
  touchStartY = event.touches[0].screenY
}

function onTouchEnd(event) {
  if (event.changedTouches.length !== 1) return
  const touchEndX = event.changedTouches[0].screenX
  const touchEndY = event.changedTouches[0].screenY

  const diffX = Math.abs(touchEndX - touchStartX)
  const diffY = touchEndY - touchStartY

  if (diffY > 80 && diffY > diffX * 1.5) {
    close()
  }
}

// ─── Fetch ────────────────────────────────────────────────────────────────────
async function prefetchLyrics() {
  if (!currentTrack.value) return
  const key = cacheKey()
  if (lyricsCache.has(key)) return
  try {
    await getLyrics(key)
  } catch {}
}

let _lastFetchId = null

async function fetchLyrics() {
  if (!currentTrack.value) return
  const key = cacheKey()
  updateFontForTrack(currentTrack.value)

  const reqId = Symbol()
  _lastFetchId = reqId

  if (lyricsCache.has(key)) {
    applyLyrics(lyricsCache.get(key).lines)
    return
  }
  loading.value = true
  error.value = ''
  try {
    const ast = await getLyrics(key)
    if (_lastFetchId !== reqId) return
    applyLyrics(ast.lines)
    loading.value = false
  } catch (err) {
    if (_lastFetchId === reqId) {
      error.value = err?.message || 'Error loading lyrics'
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

  try {
    let ast
    ast = await api.searchTrackLyrics(
      t.title || '',
      t.artist || '',
      t.album || '',
      t.duration_ms || 0,
      t.file || '',
      t.id || ''
    )

    if (!ast || !ast.lines) {
      throw new Error('No lyrics available')
    }
    lyricsCache.set(key, ast)
    return ast
  } catch (err) {
    if (err.response && err.response.status === 404) {
      throw new Error('Lyrics not found')
    }
    throw new Error('Failed to fetch lyrics')
  }
}

function applyLyrics(lines) {
  loading.value = false
  if (!Array.isArray(lines)) {
    error.value = 'Invalid lyrics format'
    return
  }

  // Map snake_case from backend API to camelCase for frontend Animator
  const mappedLines = lines.map((line) => ({
    startTime: line.start_time ?? line.startTime,
    endTime: line.end_time ?? line.endTime,
    rawText: line.raw_text ?? line.rawText,
    isInstrumental: line.is_instrumental ?? line.isInstrumental,
    lead: (line.lead || []).map((t) => ({
      text: t.text,
      startTime: t.start_time ?? t.startTime,
      endTime: t.end_time ?? t.endTime,
      isTrailingSpace: t.is_trailing_space ?? t.isTrailingSpace,
    })),
    background: (line.background || []).map((t) => ({
      text: t.text,
      startTime: t.start_time ?? t.startTime,
      endTime: t.end_time ?? t.endTime,
      isTrailingSpace: t.is_trailing_space ?? t.isTrailingSpace,
    })),
  }))

  parsedLyrics.value = mappedLines
  error.value = ''
  animator.setLines(mappedLines)

  nextTick(() => {
    const now = player.currentTime.value
    let startIdx = 0
    for (let i = mappedLines.length - 1; i >= 0; i--) {
      if (now >= mappedLines[i].startTime - 0.25) {
        startIdx = i
        break
      }
    }
    const containerH = scrollerEl.value?.clientHeight || 600
    let snap = -(
      topPad.value +
      startIdx * estimatedLineHeight -
      containerH * 0.4
    )
    animator._scrollSpring.snapTo(snap)
    scrollY.value = snap
    activeLineIdx.value = startIdx
  })
}
</script>

<style scoped>
.lyrics-root {
  color: white;
  font-family: 'Tahoma', 'Geneva', sans-serif;
  overscroll-behavior: contain;
}

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

.lyrics-content {
  position: relative;
  z-index: 10;
  flex: 1;
  overflow: hidden;
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

.lyrics-list {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  will-change: transform;
  padding: 0 clamp(1.25rem, 5vw, 4rem);
  user-select: none;
}

.lyric-line {
  display: flex;
  width: 100%;
  padding: 0.4rem 0;
  margin-bottom: 2.5rem;
  line-height: 1.1;
  cursor: pointer;
  will-change: filter, transform;
  transition:
    transform 0.25s cubic-bezier(0.25, 1, 0.5, 1),
    opacity 0.2s ease;
}

.scrubbing-active {
  filter: none !important;
  opacity: 1 !important;
}

.scrubbing-dimmed {
  opacity: 0.15 !important;
}

.scrub-indicator {
  position: absolute;
  left: -2rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  opacity: 0.5;
  width: 100vw;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.3);
  z-index: -1;
}

.align-left {
  align-items: flex-start;
  transform-origin: left center;
}

.align-center {
  align-items: center;
  transform-origin: center center;
}

.align-right {
  align-items: flex-end;
  transform-origin: right center;
}

.lyric-instrument {
  font-size: clamp(1.8rem, 4vw, 3rem);
  opacity: 0.3;
  padding: 0.3rem 0;
  align-self: center;
}

.lead-words,
.bg-words {
  width: 100%;
}

.lyric-word {
  display: inline-grid;
  will-change: transform, opacity;
  transform: translate3d(0, 0, 0) scale(var(--word-scale, 1));
  margin-right: 0.1em;
  margin-bottom: 0.25em;
  transform-origin: bottom center;
  cursor: pointer;
  backface-visibility: hidden;
  font-size: clamp(1.6rem, 4.5vw, 3.75rem);
  font-weight: 900;
  letter-spacing: 0.05rem;
}

.lyric-word[data-has-space='true'] {
  margin-right: 0.35em;
}

.word-base {
  grid-column: 1;
  grid-row: 1;
  color: white;
  white-space: pre;
  opacity: 0.28;
}

.word-hl-wrapper {
  grid-column: 1;
  grid-row: 1;
  display: inline-grid;
  will-change: filter;
  filter: drop-shadow(
      0 0 var(--glow-blur, 0px) rgba(255, 255, 255, var(--glow-opacity, 0))
    )
    drop-shadow(
      0 0 calc(var(--glow-blur, 0px) * 2.5)
        rgba(255, 255, 255, calc(var(--glow-opacity, 0) * 0.5))
    );
}

.word-hl {
  grid-column: 1;
  grid-row: 1;
  white-space: pre;
  color: white;
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
  opacity: 0.01;
  will-change:
    opacity,
    mask-image,
    -webkit-mask-image;
}

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
