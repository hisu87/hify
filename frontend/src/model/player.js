import { ref, computed, watch } from 'vue'

const VOLUME_KEY = 'hify-player-volume'

const playlist = ref([])
const currentIndex = ref(-1)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(parseFloat(localStorage.getItem(VOLUME_KEY) || '0.85'))
const isMuted = ref(false)
const repeatMode = ref('off') // 'off' | 'all' | 'one'
const shuffle = ref(false)
const userQueue = ref([])
const history = ref([])
const currentTrack = ref(null)

const isAutomix = ref(localStorage.getItem('hify-automix') === 'true')
const crossfadeDuration = ref(
  parseInt(localStorage.getItem('hify-crossfade')) || 0
)

watch(isAutomix, (val) => localStorage.setItem('hify-automix', String(val)))
watch(crossfadeDuration, (val) =>
  localStorage.setItem('hify-crossfade', String(val))
)

let deckA = new Audio()
let deckB = new Audio()
let activeDeck = deckA
let standbyDeck = deckB

let shuffleOrder = []
let shufflePos = 0
let shuffledQueueOrder = []

let rafId = null
let activeFadeJob = null
let fadeIntervalId = null

const displayQueue = computed(() => {
  if (!shuffle.value) return userQueue.value
  return shuffledQueueOrder.map((idx) => userQueue.value[idx])
})

function setupDeck(deck) {
  deck.preload = 'metadata'
  deck.volume = volume.value
  deck.addEventListener('loadedmetadata', () => {
    if (deck === activeDeck) {
      duration.value = isFinite(deck.duration) ? deck.duration : 0
    }
  })
  deck.addEventListener('durationchange', () => {
    if (deck === activeDeck) {
      duration.value = isFinite(deck.duration) ? deck.duration : 0
    }
  })
  deck.addEventListener('ended', onEnded)
  deck.addEventListener('play', () => {
    if (deck === activeDeck) {
      isPlaying.value = true
      if (!rafId) rafId = requestAnimationFrame(updateTime)
      updateMediaSessionPosition()
    }
  })
  deck.addEventListener('pause', () => {
    if (deck === activeDeck && !activeFadeJob) {
      isPlaying.value = false
      if (rafId) {
        cancelAnimationFrame(rafId)
        rafId = null
      }
      currentTime.value = activeDeck.currentTime
      updateMediaSessionPosition()
    }
  })
}

setupDeck(deckA)
setupDeck(deckB)
setupMediaSession()

function getAudio() {
  return activeDeck
}

function fileUrl(file) {
  return `/downloads/${encodeURIComponent(file)}`
}

function coverUrl(file) {
  return `/cover?file=${encodeURIComponent(file)}`
}

function trackFromFile(file) {
  const noExt = file.replace(/\.[^.]+$/, '')
  let artist = ''
  let title = noExt
  const dash = noExt.indexOf(' - ')
  if (dash > 0) {
    artist = noExt.slice(0, dash).trim()
    title = noExt.slice(dash + 3).trim()
  }
  return {
    file,
    url: fileUrl(file),
    cover: coverUrl(file),
    title,
    artist,
  }
}

function buildShuffleOrder() {
  const indices = playlist.value.map((_, i) => i)
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[indices[i], indices[j]] = [indices[j], indices[i]]
  }
  shuffleOrder = indices
  shufflePos =
    currentIndex.value >= 0
      ? Math.max(0, shuffleOrder.indexOf(currentIndex.value))
      : 0
}

function rebuildQueueShuffle() {
  const indices = userQueue.value.map((_, i) => i)
  for (let i = indices.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[indices[i], indices[j]] = [indices[j], indices[i]]
  }
  shuffledQueueOrder = indices
}

function setPlaylist(files, options = {}) {
  const tracks = (files || []).map((f) => {
    if (typeof f === 'string') return trackFromFile(f)
    return {
      ...f,
      url: f.url || fileUrl(f.file),
      cover:
        f.cover ||
        (f.cover_url
          ? f.cover_url.startsWith('http')
            ? f.cover_url
            : `/${f.cover_url}`
          : coverUrl(f.file)),
      title: f.title || f.file,
      artist: f.artist || '',
    }
  })
  playlist.value = tracks
  if (currentIndex.value >= tracks.length) currentIndex.value = -1
  if (shuffle.value) buildShuffleOrder()
  if (typeof options.startIndex === 'number') {
    playAt(options.startIndex)
  } else if (options.autoplay && tracks.length > 0 && currentIndex.value < 0) {
    playAt(0)
  }
}

function abortActiveFadeJob() {
  if (activeFadeJob) {
    clearInterval(fadeIntervalId)
    activeFadeJob = null
    standbyDeck.pause()
    standbyDeck.currentTime = 0
    activeDeck.volume = isMuted.value ? 0 : volume.value
  }
}

async function safeSeekAndPlay(deck, targetTime) {
  if (deck.readyState < 1) {
    await new Promise((res) => {
      const h = () => {
        deck.removeEventListener('loadedmetadata', h)
        res()
      }
      deck.addEventListener('loadedmetadata', h)
    })
  }
  deck.currentTime = targetTime
  await deck.play().catch(() => {})
}

function _playTrack(track, isGoingBack = false) {
  abortActiveFadeJob()
  if (fadeIntervalId) {
    clearInterval(fadeIntervalId)
    fadeIntervalId = null
  }

  if (currentTrack.value && !isGoingBack) {
    history.value.push(currentTrack.value)
  }

  currentTrack.value = track
  activeDeck.src = track.url

  if (isAutomix.value) {
    safeSeekAndPlay(activeDeck, 2.5)
  } else {
    activeDeck.currentTime = 0
    activeDeck.play().catch(() => {})
  }

  currentTime.value = 0
  updateMediaSession()
}

function playAt(index) {
  if (index < 0 || index >= playlist.value.length) return
  abortActiveFadeJob()

  currentIndex.value = index
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const pos = shuffleOrder.indexOf(index)
    if (pos >= 0) shufflePos = pos
  }
  _playTrack(playlist.value[index])
}

function play() {
  if (
    playlist.value.length === 0 &&
    userQueue.value.length === 0 &&
    !currentTrack.value
  )
    return

  if (!currentTrack.value) {
    next()
    return
  }

  if (activeFadeJob) {
    // Resume fade
    activeDeck.play().catch(() => {})
    standbyDeck.play().catch(() => {})
    isPlaying.value = true
    const stepTime = (activeFadeJob.durationSec * 1000) / activeFadeJob.steps
    runFadeInterval(stepTime)
  } else {
    if (!activeDeck.src) {
      activeDeck.src = currentTrack.value.url
    }
    activeDeck.play().catch(() => {})
  }
}

function pause() {
  if (activeFadeJob) {
    clearInterval(fadeIntervalId)
    fadeIntervalId = null
    activeDeck.pause()
    standbyDeck.pause()
    isPlaying.value = false
  } else {
    activeDeck.pause()
  }
}

function toggle() {
  if (isPlaying.value) pause()
  else play()
}

function seek(seconds) {
  const max = duration.value || 0
  const clamped = Math.max(0, Math.min(max, seconds))
  activeDeck.currentTime = clamped
  currentTime.value = clamped
  updateMediaSessionPosition()
}

function seekRatio(ratio) {
  if (!duration.value) return
  seek(duration.value * Math.max(0, Math.min(1, ratio)))
}

function setVolume(v) {
  const clamped = Math.max(0, Math.min(1, v))
  volume.value = clamped
  if (activeFadeJob) {
    activeFadeJob.targetVol = clamped
  } else {
    activeDeck.volume = clamped
  }
  try {
    localStorage.setItem(VOLUME_KEY, String(clamped))
  } catch {
    // ignore
  }
  if (clamped > 0 && isMuted.value) {
    isMuted.value = false
    activeDeck.muted = false
    standbyDeck.muted = false
  }
}

function toggleMute() {
  isMuted.value = !isMuted.value
  activeDeck.muted = isMuted.value
  standbyDeck.muted = isMuted.value
}

function nextIndex() {
  if (playlist.value.length === 0) return -1

  if (isAutomix.value && currentTrack.value) {
    const candidates = playlist.value
      .map((t, idx) => ({ t, idx }))
      .filter(
        (x) =>
          x.idx !== currentIndex.value &&
          ((x.t.artist && x.t.artist === currentTrack.value.artist) ||
            (x.t.genre && x.t.genre === currentTrack.value.genre))
      )
    if (candidates.length > 0) {
      const pick = candidates[Math.floor(Math.random() * candidates.length)]
      return pick.idx
    }
  }

  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const nextPos = (shufflePos + 1) % shuffleOrder.length
    return shuffleOrder[nextPos]
  }
  const i = currentIndex.value + 1
  if (i >= playlist.value.length) {
    return repeatMode.value === 'all' ? 0 : -1
  }
  return i
}

function prevIndex() {
  if (playlist.value.length === 0) return -1
  if (shuffle.value) {
    if (shuffleOrder.length !== playlist.value.length) buildShuffleOrder()
    const prevPos = (shufflePos - 1 + shuffleOrder.length) % shuffleOrder.length
    return shuffleOrder[prevPos]
  }
  const i = currentIndex.value - 1
  if (i < 0) {
    return repeatMode.value === 'all' ? playlist.value.length - 1 : 0
  }
  return i
}

function next() {
  abortActiveFadeJob()

  if (userQueue.value.length > 0) {
    let trackToPlay = null
    if (shuffle.value) {
      const rawIdx = shuffledQueueOrder.shift()
      for (let i = 0; i < shuffledQueueOrder.length; i++) {
        if (shuffledQueueOrder[i] > rawIdx) shuffledQueueOrder[i]--
      }
      trackToPlay = userQueue.value.splice(rawIdx, 1)[0]
    } else {
      trackToPlay = userQueue.value.shift()
    }
    _playTrack(trackToPlay)
    return
  }

  const i = nextIndex()
  if (i < 0) {
    pause()
    return
  }
  playAt(i)
}

function prev() {
  abortActiveFadeJob()

  if (activeDeck.currentTime > 3 || history.value.length === 0) {
    seek(0)
    return
  }

  const prevTrack = history.value.pop()

  if (currentTrack.value) {
    userQueue.value.unshift(currentTrack.value)
    if (shuffle.value) {
      for (let i = 0; i < shuffledQueueOrder.length; i++) {
        shuffledQueueOrder[i]++
      }
      shuffledQueueOrder.unshift(0)
    }
  }

  const idx = playlist.value.findIndex((t) => t.url === prevTrack.url)
  if (idx !== -1) currentIndex.value = idx

  _playTrack(prevTrack, true)
}

function addToQueue(fileOrTrack) {
  let track =
    typeof fileOrTrack === 'string' ? trackFromFile(fileOrTrack) : fileOrTrack
  if (!track.url) {
    track = {
      ...track,
      url: track.url || fileUrl(track.file),
      cover:
        track.cover ||
        (track.cover_url
          ? track.cover_url.startsWith('http')
            ? track.cover_url
            : `/${track.cover_url}`
          : coverUrl(track.file)),
      title: track.title || track.file,
      artist: track.artist || '',
    }
  }
  userQueue.value.push(track)
  if (shuffle.value) {
    const newIdx = userQueue.value.length - 1
    const insertPos = Math.floor(
      Math.random() * (shuffledQueueOrder.length + 1)
    )
    shuffledQueueOrder.splice(insertPos, 0, newIdx)
  }
}

function playNext(fileOrTrack) {
  let track =
    typeof fileOrTrack === 'string' ? trackFromFile(fileOrTrack) : fileOrTrack
  if (!track.url) {
    track = {
      ...track,
      url: track.url || fileUrl(track.file),
      cover:
        track.cover ||
        (track.cover_url
          ? track.cover_url.startsWith('http')
            ? track.cover_url
            : `/${track.cover_url}`
          : coverUrl(track.file)),
      title: track.title || track.file,
      artist: track.artist || '',
    }
  }
  userQueue.value.unshift(track)
  if (shuffle.value) {
    for (let i = 0; i < shuffledQueueOrder.length; i++) {
      shuffledQueueOrder[i]++
    }
    shuffledQueueOrder.unshift(0)
  }
}

function removeFromQueue(displayIndex) {
  if (displayIndex < 0 || displayIndex >= displayQueue.value.length) return
  let rawIndex = displayIndex
  if (shuffle.value) {
    rawIndex = shuffledQueueOrder[displayIndex]
    shuffledQueueOrder.splice(displayIndex, 1)
    for (let i = 0; i < shuffledQueueOrder.length; i++) {
      if (shuffledQueueOrder[i] > rawIndex) {
        shuffledQueueOrder[i]--
      }
    }
  }
  userQueue.value.splice(rawIndex, 1)
}

function clearQueue() {
  userQueue.value = []
  shuffledQueueOrder = []
}

function onEnded(event) {
  // Ghost Ended Trigger safeguard
  if (event.target !== activeDeck) return

  if (repeatMode.value === 'one') {
    safeSeekAndPlay(activeDeck, 0)
    return
  }
  next()
}

function setRepeat(mode) {
  if (['off', 'all', 'one'].includes(mode)) repeatMode.value = mode
}

function cycleRepeat() {
  const order = ['off', 'all', 'one']
  const i = order.indexOf(repeatMode.value)
  setRepeat(order[(i + 1) % order.length])
}

function setShuffle(v) {
  shuffle.value = !!v
  if (shuffle.value) {
    buildShuffleOrder()
    rebuildQueueShuffle()
  }
}

function toggleShuffle() {
  setShuffle(!shuffle.value)
}

function updateTime() {
  if (activeDeck && isPlaying.value) {
    currentTime.value = activeDeck.currentTime

    const effectiveCrossfade = isAutomix.value ? 6.0 : crossfadeDuration.value
    const timeLeft = activeDeck.duration - activeDeck.currentTime
    const triggerTime = isAutomix.value
      ? effectiveCrossfade + 2.0
      : effectiveCrossfade

    if (
      effectiveCrossfade > 0 &&
      timeLeft > 0 &&
      timeLeft <= triggerTime &&
      !activeFadeJob
    ) {
      if (fadeIntervalId) {
        clearInterval(fadeIntervalId)
        fadeIntervalId = null
      }
      startCrossfade(effectiveCrossfade)
    }

    rafId = requestAnimationFrame(updateTime)
  }
}

let nextTrackObjForFade = null

function startCrossfade(durationSec) {
  let trackToPlay = null
  let useAutomixOffset = isAutomix.value

  if (userQueue.value.length > 0) {
    if (shuffle.value) {
      const rawIdx = shuffledQueueOrder.shift()
      for (let i = 0; i < shuffledQueueOrder.length; i++) {
        if (shuffledQueueOrder[i] > rawIdx) shuffledQueueOrder[i]--
      }
      trackToPlay = userQueue.value.splice(rawIdx, 1)[0]
    } else {
      trackToPlay = userQueue.value.shift()
    }
  } else {
    const nIdx = nextIndex()
    if (nIdx < 0) return
    currentIndex.value = nIdx
    trackToPlay = playlist.value[nIdx]
  }

  nextTrackObjForFade = trackToPlay
  standbyDeck.src = trackToPlay.url
  standbyDeck.volume = 0

  if (useAutomixOffset) {
    safeSeekAndPlay(standbyDeck, 2.5)
  } else {
    standbyDeck.currentTime = 0
    standbyDeck.play().catch(() => {})
  }

  const steps = 50
  const stepTime = (durationSec * 1000) / steps
  const targetVol = isMuted.value ? 0 : volume.value

  activeFadeJob = {
    steps,
    currentStep: 0,
    targetVol,
    durationSec,
  }

  runFadeInterval(stepTime)
}

function runFadeInterval(stepTime) {
  fadeIntervalId = setInterval(() => {
    if (!isPlaying.value) return

    activeFadeJob.currentStep++
    const t = activeFadeJob.currentStep / activeFadeJob.steps

    // Logarithmic (quadratic) curve for natural human hearing perception
    const volA = Math.max(0, activeFadeJob.targetVol * Math.pow(1 - t, 2))
    const volB = Math.min(
      activeFadeJob.targetVol,
      activeFadeJob.targetVol * Math.pow(t, 2)
    )

    activeDeck.volume = volA
    standbyDeck.volume = volB

    if (activeFadeJob.currentStep >= activeFadeJob.steps) {
      clearInterval(fadeIntervalId)
      fadeIntervalId = null
      completeHandoff()
    }
  }, stepTime)
}

function completeHandoff() {
  activeDeck.pause()
  activeDeck.volume = isMuted.value ? 0 : volume.value

  const temp = activeDeck
  activeDeck = standbyDeck
  standbyDeck = temp

  if (currentTrack.value) {
    history.value.push(currentTrack.value)
  }

  currentTrack.value = nextTrackObjForFade
  duration.value = isFinite(activeDeck.duration) ? activeDeck.duration : 0
  activeFadeJob = null

  updateMediaSession()
}

const progressPct = computed(() =>
  duration.value > 0 ? (currentTime.value / duration.value) * 100 : 0
)

function updateMediaSession() {
  if ('mediaSession' in navigator && currentTrack.value) {
    const track = currentTrack.value
    const coverFullUrl = new URL(track.cover, window.location.origin).href

    navigator.mediaSession.metadata = new MediaMetadata({
      title: track.title,
      artist: track.artist,
      album: 'Hify',
      artwork: [{ src: coverFullUrl, sizes: '512x512', type: 'image/jpeg' }],
    })
    updateMediaSessionPosition()
  }
}

function updateMediaSessionPosition() {
  if (
    'mediaSession' in navigator &&
    activeDeck &&
    isFinite(activeDeck.duration) &&
    activeDeck.duration > 0
  ) {
    try {
      navigator.mediaSession.setPositionState({
        duration: activeDeck.duration,
        playbackRate: activeDeck.playbackRate,
        position: activeDeck.currentTime,
      })
    } catch (e) {
      // Ignore
    }
  }
}

function setupMediaSession() {
  if ('mediaSession' in navigator) {
    navigator.mediaSession.setActionHandler('play', play)
    navigator.mediaSession.setActionHandler('pause', pause)
    navigator.mediaSession.setActionHandler('previoustrack', prev)
    navigator.mediaSession.setActionHandler('nexttrack', next)
    navigator.mediaSession.setActionHandler('seekto', (details) => {
      seek(details.seekTime)
    })
  }
}

export function formatTime(seconds) {
  if (!isFinite(seconds) || seconds < 0) return '0:00'
  const total = Math.floor(seconds)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function trackInfoFromFile(file) {
  return trackFromFile(file)
}

export function usePlayer() {
  return {
    playlist,
    userQueue,
    displayQueue,
    history,
    currentIndex,
    currentTrack,
    isPlaying,
    currentTime,
    duration,
    progressPct,
    volume,
    isMuted,
    repeatMode,
    shuffle,
    isAutomix,
    crossfadeDuration,
    setPlaylist,
    addToQueue,
    playNext,
    removeFromQueue,
    clearQueue,
    playAt,
    play,
    pause,
    toggle,
    seek,
    seekRatio,
    setVolume,
    toggleMute,
    next,
    prev,
    setRepeat: cycleRepeat,
    cycleRepeat,
    setShuffle,
    toggleShuffle,
    getAudio,
    getShufflePos: () => shufflePos,
    getShuffleOrder: () => shuffleOrder,
  }
}
