/**
 * LyricsAnimator — RAF loop chính
 */
import {
  getWordStore,
  resetWordStore,
  setStyleIfChanged,
  flushStyleBatch,
  clearBatch,
} from './AnimatorStore.js'
import {
  SCALE_CURVE,
  Y_OFFSET_CURVE,
  GLOW_CURVE,
  SCALE_SUNG,
  SCALE_NOT_SUNG,
  MAX_LINE_BLUR,
} from './CubicSpline.js'
import { Spring, SpringPresets } from './Spring.js'

const TokenState = { PAST: 0, ACTIVE: 1, FUTURE: 2 }

export class LyricsAnimator {
  constructor() {
    this.lines = []
    this._wordEls = new Map()
    this._lineEls = new Map()

    this._rafId = null
    this._lastTs = null
    this._cursorIdx = 0
    this._activeLineIdx = -1
    this.timeOffset = 0 // Sync Calibration (Giai đoạn 2.3)

    // Scroll spring with Critical Damping (Giai đoạn 4.2)
    this._scrollSpring = new Spring(2.2, 1.0, 0)

    this.audioElement = null
    this.isPlaying = () => false

    this._interpolatedTime = 0
    this._lastSyncTs = null
    this._lastRawTime = null
  }

  setLines(lines) {
    this.lines = lines || []
    this._cursorIdx = 0
    this._activeLineIdx = -1
    for (const [, refs] of this._wordEls) resetWordStore(refs.word)
    this._scrollSpring.snapTo(0)

    this._interpolatedTime = 0
    this._lastSyncTs = null
    this._lastRawTime = null
  }

  registerWord(lineIdx, wordIdx, el, isBg = false) {
    if (!el) return
    const key = `${lineIdx}-${isBg ? 'bg' : 'lead'}-${wordIdx}`
    const hlEl = el.querySelector('.word-hl')
    const baseEl = el.querySelector('.word-base')
    this._wordEls.set(key, { word: el, hl: hlEl, base: baseEl })
    el.style.willChange = 'opacity, mask-image, transform' // GPU hint (Giai đoạn 4.3)
    el.style.backfaceVisibility = 'hidden'
    el.style.transform = 'translate3d(0, 0, 0)'
  }

  unregisterWord(lineIdx, wordIdx, isBg = false) {
    const key = `${lineIdx}-${isBg ? 'bg' : 'lead'}-${wordIdx}`
    const refs = this._wordEls.get(key)
    if (refs) resetWordStore(refs.word)
    this._wordEls.delete(key)
  }

  registerLine(lineIdx, el) {
    if (!el) return
    this._lineEls.set(lineIdx, el)
  }

  unregisterLine(lineIdx) {
    this._lineEls.delete(lineIdx)
  }

  start() {
    if (this._rafId) return
    this._lastTs = performance.now()
    this._rafId = requestAnimationFrame(this._loop.bind(this))
  }

  stop() {
    if (this._rafId) {
      cancelAnimationFrame(this._rafId)
      this._rafId = null
    }
    this._lastTs = null
    this._interpolatedTime = 0
    this._lastSyncTs = null
    this._lastRawTime = null
    clearBatch()
  }

  _loop(ts) {
    const dt = Math.min((ts - (this._lastTs || ts)) / 1000, 0.1)
    this._lastTs = ts

    const rawTime = this.audioElement ? this.audioElement.currentTime : 0
    const isPlaying = this.isPlaying ? this.isPlaying() : false

    const isSeek = this._lastRawTime === null || this._lastRawTime === undefined || Math.abs(rawTime - this._lastRawTime) > 0.5
    
    if (isSeek) {
      this._interpolatedTime = rawTime
      this._lastSyncTs = ts
    } else if (isPlaying) {
      const frameDelta = (ts - (this._lastSyncTs || ts)) / 1000
      this._interpolatedTime += frameDelta
      const drift = rawTime - this._interpolatedTime
      if (Math.abs(drift) < 0.2) {
        this._interpolatedTime += drift * 0.1
      } else {
        this._interpolatedTime = rawTime
      }
      this._lastSyncTs = ts
    } else {
      this._interpolatedTime = rawTime
      this._lastSyncTs = ts
    }
    this._lastRawTime = rawTime

    const now = Math.max(0, this._interpolatedTime) + this.timeOffset
    const lines = this.lines

    if (!lines.length) {
      this._rafId = requestAnimationFrame(this._loop.bind(this))
      return
    }

    // Sliding Cursor or Binary Search (Giai đoạn 2.1)
    let cursor = this._cursorIdx
    if (isSeek) {
      let l = 0, r = lines.length - 1
      let found = 0
      while (l <= r) {
        const mid = Math.floor((l + r) / 2)
        if (now < lines[mid].startTime) {
          r = mid - 1
        } else {
          found = mid
          l = mid + 1
        }
      }
      cursor = found
    } else {
      while (cursor < lines.length - 1 && now >= lines[cursor + 1].startTime) cursor++
      while (cursor > 0 && now < lines[cursor].startTime) cursor--
    }
    this._cursorIdx = cursor
    this._activeLineIdx = cursor

    const activeLineFrac = this._findActiveLineFrac(now, cursor)

    // Determine device capabilities (Giai đoạn 4.3)
    const isMobile = window.devicePixelRatio && window.devicePixelRatio < 2

    for (let li = 0; li < lines.length; li++) {
      const line = lines[li]
      const isActiveLine = li === cursor
      const isSungLine = li < cursor

      // Process lead and background vocals
      this._processTokens(line.lead, li, false, now, dt, isActiveLine, isSungLine, isMobile)
      if (line.background) {
        this._processTokens(line.background, li, true, now, dt, isActiveLine, isSungLine, isMobile)
      }
    }

    this._applyLineBlur(activeLineFrac)
    flushStyleBatch()

    this._scrollSpring.step(dt)
    if (this.onFrame) {
      this.onFrame({
        activeLineIdx: cursor,
        scrollSpringPos: this._scrollSpring.position,
      })
    }

    this._rafId = requestAnimationFrame(this._loop.bind(this))
  }

  _processTokens(tokens, lineIdx, isBg, now, dt, isActiveLine, isSungLine, isMobile) {
    if (!tokens || !tokens.length) return

    // Token State Machine (Giai đoạn 2.2)
    const states = tokens.map(token => {
      if (now < token.startTime) return TokenState.FUTURE
      if (now >= token.endTime) return TokenState.PAST
      return TokenState.ACTIVE
    })

    // Prepare goals
    const goals = tokens.map(() => ({ scale: 1, y: 0, glow: 0, fill: 0, opacity: 0 }))

    // First pass: Calculate base goals
    for (let wi = 0; wi < tokens.length; wi++) {
      const token = tokens[wi]
      const state = states[wi]
      
      if (state === TokenState.ACTIVE) {
        const progress = Math.max(0, Math.min(1, (now - token.startTime) / Math.max(token.endTime - token.startTime, 0.05)))
        goals[wi].scale = SCALE_CURVE.at(progress)
        goals[wi].y = Y_OFFSET_CURVE.at(progress)
        goals[wi].glow = GLOW_CURVE.at(progress)
        goals[wi].fill = progress * 100
        goals[wi].opacity = 1.0
      } else if (state === TokenState.PAST) {
        goals[wi].scale = SCALE_SUNG
        goals[wi].y = 0
        goals[wi].glow = 0
        goals[wi].fill = 100
        goals[wi].opacity = 0.85
      } else {
        // FUTURE
        if (isActiveLine) {
          goals[wi].scale = SCALE_NOT_SUNG
          goals[wi].opacity = 0.5
        } else if (isSungLine) {
          goals[wi].scale = SCALE_SUNG * 0.99
          goals[wi].opacity = 0.65
        } else {
          goals[wi].scale = 0.94
          goals[wi].opacity = 0.35
        }
        goals[wi].y = 0
        goals[wi].glow = 0
        goals[wi].fill = 0
      }
    }

    // Second pass: Neighbor Falloff Scale (Giai đoạn 3.1)
    for (let wi = 0; wi < tokens.length; wi++) {
      if (states[wi] === TokenState.ACTIVE) {
        const activeScale = goals[wi].scale
        if (activeScale > 1.0) {
          // Falloff 1
          if (wi - 1 >= 0 && states[wi - 1] !== TokenState.ACTIVE) goals[wi - 1].scale = Math.max(goals[wi - 1].scale, 1.0 + (activeScale - 1.0) * 0.38)
          if (wi + 1 < tokens.length && states[wi + 1] !== TokenState.ACTIVE) goals[wi + 1].scale = Math.max(goals[wi + 1].scale, 1.0 + (activeScale - 1.0) * 0.38)
          // Falloff 2
          if (wi - 2 >= 0 && states[wi - 2] !== TokenState.ACTIVE) goals[wi - 2].scale = Math.max(goals[wi - 2].scale, 1.0 + (activeScale - 1.0) * 0.12)
          if (wi + 2 < tokens.length && states[wi + 2] !== TokenState.ACTIVE) goals[wi + 2].scale = Math.max(goals[wi + 2].scale, 1.0 + (activeScale - 1.0) * 0.12)
        }
      }
    }

    // Apply goals and step springs
    for (let wi = 0; wi < tokens.length; wi++) {
      const key = `${lineIdx}-${isBg ? 'bg' : 'lead'}-${wi}`
      const refs = this._wordEls.get(key)
      if (!refs || !refs.word.isConnected) continue

      const { word: wordEl, hl: hlEl, base: baseEl } = refs
      const store = getWordStore(wordEl)

      store.scaleSpring.setGoal(goals[wi].scale)
      store.ySpring.setGoal(goals[wi].y)
      store.glowSpring.setGoal(goals[wi].glow)
      store.fillSpring.setGoal(goals[wi].fill)
      store.opacitySpring.setGoal(goals[wi].opacity)

      store.scaleSpring.step(dt)
      store.ySpring.step(dt)
      store.glowSpring.step(dt)
      store.fillSpring.step(dt)
      store.opacitySpring.step(dt)

      const scale = Math.max(0.92, Math.min(1.06, store.scaleSpring.position))
      const y = Math.max(-3, Math.min(3, store.ySpring.position))
      const glow = store.glowSpring.position
      const fill = Math.max(0, Math.min(100, store.fillSpring.position))
      const opacity = Math.max(0, Math.min(1, store.opacitySpring.position))

      setStyleIfChanged(wordEl, 'transform', `translate3d(0, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(4)})`, 0.0005)

      if (!isMobile) {
        const glowClamped = Math.max(0, Math.min(1, glow))
        setStyleIfChanged(wordEl, '--glow-opacity', glowClamped.toFixed(3), 0.005)
        setStyleIfChanged(wordEl, '--glow-blur', `${(glowClamped * 18).toFixed(1)}px`, 0.3)
      } else {
        setStyleIfChanged(wordEl, '--glow-opacity', '0', 0)
        setStyleIfChanged(wordEl, '--glow-blur', '0px', 0)
      }

      if (hlEl) {
        setStyleIfChanged(hlEl, '--fill-pct', `${fill.toFixed(1)}%`, 0.4)
        setStyleIfChanged(hlEl, 'opacity', opacity.toFixed(3), 0.004)
        setStyleIfChanged(hlEl, 'webkitMaskImage', fill >= 99.5 ? 'none' : '', 0)
        setStyleIfChanged(hlEl, 'maskImage', fill >= 99.5 ? 'none' : '', 0)
      }

      if (baseEl) {
        const baseOpacity = Math.max(0.12, opacity * 0.35)
        setStyleIfChanged(baseEl, 'opacity', baseOpacity.toFixed(3), 0.004)
      }
    }
  }

  _findActiveLineFrac(now, activeIdx) {
    const lines = this.lines
    if (!lines.length || activeIdx === -1) return 0
    if (activeIdx === lines.length - 1) return activeIdx

    const tStart = lines[activeIdx].startTime
    const tEnd = lines[activeIdx + 1].startTime
    const duration = tEnd - tStart
    if (duration <= 0) return activeIdx

    const pct = Math.max(0, Math.min(1, (now - tStart) / duration))
    return activeIdx + pct
  }

  _applyLineBlur(activeLineFrac) {
    for (const [lineIdx, el] of this._lineEls) {
      if (!el || !el.isConnected) continue
      if (activeLineFrac < 0) {
        setStyleIfChanged(el, 'filter', 'none', 0)
        setStyleIfChanged(el, 'transform', 'none', 0)
        continue
      }

      const dist = Math.abs(lineIdx - activeLineFrac)
      let blurPx = 0
      let scale = 0.92

      if (dist < 1) {
        const t = dist
        scale = 1.06 - t * (1.06 - 0.95)
        blurPx = t * 0.4
      } else {
        const t = Math.min(3, dist - 1)
        scale = 0.95 - t * 0.02
        blurPx = 0.4 + (dist - 1) * 0.8
        blurPx = Math.min(MAX_LINE_BLUR, blurPx)
      }

      setStyleIfChanged(el, 'filter', blurPx < 0.15 ? 'none' : `blur(${blurPx.toFixed(1)}px)`, 0.08)
      setStyleIfChanged(el, 'transform', `scale(${scale.toFixed(3)})`, 0.005)
    }
  }

  setScrollGoal(targetY) {
    this._scrollSpring.setGoal(targetY)
  }
}
