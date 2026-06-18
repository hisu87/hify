/**
 * LyricsAnimator — RAF loop chính, tách hoàn toàn 3 layer:
 *
 * 1. TimeSetter   — xác định status (NotSung / Active / Sung) cho từng word
 * 2. SplineSampler — lấy goal animation theo % tiến trình từ Catmull-Rom spline
 * 3. SpringStepper — advance spring vật lý, ghi style qua batcher
 *
 * Thiết kế seek-safe: khi audio seek, spring chỉ đổi goal, không snap,
 * vẫn đuổi theo mượt mà (không "nổ" giá trị).
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

// ─── Status enum ───────────────────────────────────────────────────────────────
const Status = {
  NOT_SUNG: 0,
  ACTIVE: 1,
  SUNG: 2,
}

export class LyricsAnimator {
  constructor() {
    /** @type {import('./LrcParser.js').LyricLine[]} */
    this.lines = []

    // DOM refs: Map<`${lineIdx}-${wordIdx}`, { word: Element, hl: Element|null, base: Element|null }>
    this._wordEls = new Map()
    // Map<lineIdx, Element> — container của cả line (cho blur)
    this._lineEls = new Map()

    this._rafId = null
    this._lastTs = null
    this._activeLineIdx = -1

    // Spring riêng cho scroll offset
    this._scrollSpring = new Spring(
      SpringPresets.scroll.frequency,
      SpringPresets.scroll.dampingRatio,
      0
    )

    // Callback được gọi mỗi frame với { activeLineIdx, scrollSpringPos }
    this.onFrame = null

    // Ref tới player (set bên ngoài)
    this.getTime = () => 0
  }

  // ─── Public API ──────────────────────────────────────────────────────────────

  setLines(lines) {
    this.lines = lines || []
    this._activeLineIdx = -1
    // Reset tất cả springs cho elements đang mount
    for (const [, refs] of this._wordEls) resetWordStore(refs.word)
    this._scrollSpring.snapTo(0)
  }

  /** Gọi từ v-for :ref khi word element mount */
  registerWord(lineIdx, wordIdx, el) {
    if (!el) return
    const key = `${lineIdx}-${wordIdx}`
    // Cache child refs ngay khi mount để không querySelectorAll trong RAF
    const hlEl = el.querySelector('.word-hl')
    const baseEl = el.querySelector('.word-base')
    this._wordEls.set(key, { word: el, hl: hlEl, base: baseEl })
    // GPU hints
    el.style.willChange = 'transform, filter'
    el.style.backfaceVisibility = 'hidden'
    el.style.transform = 'translate3d(0, 0, 0)'
  }

  unregisterWord(lineIdx, wordIdx) {
    const key = `${lineIdx}-${wordIdx}`
    const refs = this._wordEls.get(key)
    if (refs) resetWordStore(refs.word)
    this._wordEls.delete(key)
  }

  /** Gọi từ v-for :ref khi line container element mount */
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
    clearBatch()
  }

  // ─── Main Loop ────────────────────────────────────────────────────────────────

  _loop(ts) {
    const dt = Math.min((ts - (this._lastTs || ts)) / 1000, 0.1) // cap at 100ms (tab hidden)
    this._lastTs = ts

    const now = this.getTime()
    const lines = this.lines

    if (!lines.length) {
      this._rafId = requestAnimationFrame(this._loop.bind(this))
      return
    }

    // 1. TimeSetter — tìm active line
    const activeIdx = this._findActiveLine(now)
    if (activeIdx !== this._activeLineIdx) {
      this._activeLineIdx = activeIdx
    }

    // 2. Animate từng word
    for (let li = 0; li < lines.length; li++) {
      const line = lines[li]
      const isActiveLine = li === activeIdx
      const isSungLine = li < activeIdx
      for (let wi = 0; wi < line.words.length; wi++) {
        const key = `${li}-${wi}`
        const refs = this._wordEls.get(key)
        if (!refs || !refs.word.isConnected) continue

        const { word: wordEl, hl: hlEl, base: baseEl } = refs
        const word = line.words[wi]
        const store = getWordStore(wordEl)

        // Tính status của word này
        const wordStart = line.time + word.delay
        const wordEnd = wordStart + word.duration
        let wordStatus = Status.NOT_SUNG

        if (now >= wordEnd) {
          wordStatus = Status.SUNG
        } else if (now >= wordStart) {
          wordStatus = Status.ACTIVE
        }

        // 3. Spline sampler — tính goal theo % tiến trình
        let scaleGoal, yGoal, glowGoal, fillGoal, opacityGoal

        if (wordStatus === Status.ACTIVE) {
          const progress = Math.max(
            0,
            Math.min(1, (now - wordStart) / Math.max(word.duration, 0.05))
          )
          scaleGoal = SCALE_CURVE.at(progress)
          yGoal = Y_OFFSET_CURVE.at(progress)
          glowGoal = GLOW_CURVE.at(progress)
          fillGoal = progress * 100
          opacityGoal = 1.0
        } else if (wordStatus === Status.SUNG) {
          scaleGoal = SCALE_SUNG
          yGoal = 0
          glowGoal = 0
          fillGoal = 100
          opacityGoal = 0.85 // Sung: bright but slightly muted
        } else {
          // NOT_SUNG
          if (isActiveLine) {
            // Upcoming words within active line
            scaleGoal = SCALE_NOT_SUNG
            opacityGoal = 0.5
          } else if (isSungLine) {
            scaleGoal = SCALE_SUNG * 0.99
            opacityGoal = 0.65
          } else {
            // Future lines
            scaleGoal = 0.94
            opacityGoal = 0.35
          }
          yGoal = 0
          glowGoal = 0
          fillGoal = 0
        }

        // 4. Spring stepper
        store.scaleSpring.setGoal(scaleGoal)
        store.ySpring.setGoal(yGoal)
        store.glowSpring.setGoal(glowGoal)
        store.fillSpring.setGoal(fillGoal)
        store.opacitySpring.setGoal(opacityGoal)

        store.scaleSpring.step(dt)
        store.ySpring.step(dt)
        store.glowSpring.step(dt)
        store.fillSpring.step(dt)
        store.opacitySpring.step(dt)

        const scale = Math.max(0.92, Math.min(1.04, store.scaleSpring.position))
        const y = Math.max(-3, Math.min(3, store.ySpring.position))
        const glow = store.glowSpring.position
        const fill = Math.max(0, Math.min(100, store.fillSpring.position))
        const opacity = Math.max(0, Math.min(1, store.opacitySpring.position))

        // 5. Style batch writes (no DOM query — all refs cached)
        setStyleIfChanged(
          wordEl,
          'transform',
          `translate3d(0, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(4)})`,
          0.0005
        )

        // Glow via CSS custom properties
        const glowClamped = Math.max(0, Math.min(1, glow))
        setStyleIfChanged(
          wordEl,
          '--glow-opacity',
          glowClamped.toFixed(3),
          0.005
        )
        setStyleIfChanged(
          wordEl,
          '--glow-blur',
          `${(glowClamped * 18).toFixed(1)}px`,
          0.3
        )

        // Highlight layer (fill mask + opacity)
        if (hlEl) {
          setStyleIfChanged(hlEl, '--fill-pct', `${fill.toFixed(1)}%`, 0.4)
          setStyleIfChanged(hlEl, 'opacity', opacity.toFixed(3), 0.004)
        }

        // Base layer — always slightly visible, tied to opacity
        if (baseEl) {
          const baseOpacity = Math.max(0.12, opacity * 0.35)
          setStyleIfChanged(baseEl, 'opacity', baseOpacity.toFixed(3), 0.004)
        }
      }
    }

    // 6. Line-level blur (khoảng cách tới active)
    this._applyLineBlur(activeIdx)

    // 7. Flush tất cả pending styles vào DOM một lần
    flushStyleBatch()

    // 8. Scroll spring step + notify
    this._scrollSpring.step(dt)
    if (this.onFrame) {
      this.onFrame({
        activeLineIdx: activeIdx,
        scrollSpringPos: this._scrollSpring.position,
      })
    }

    this._rafId = requestAnimationFrame(this._loop.bind(this))
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────────

  _findActiveLine(now) {
    const lines = this.lines
    for (let i = lines.length - 1; i >= 0; i--) {
      if (now >= lines[i].time - 0.25) return i
    }
    return -1
  }

  _applyLineBlur(activeIdx) {
    for (const [lineIdx, el] of this._lineEls) {
      if (!el || !el.isConnected) continue
      if (activeIdx < 0) {
        // No active line yet — no blur
        setStyleIfChanged(el, 'filter', 'none', 0)
        continue
      }

      const dist = Math.abs(lineIdx - activeIdx)
      let blurPx = 0
      if (dist > 0) {
        blurPx = Math.min(MAX_LINE_BLUR, (dist - 0.5) * 0.9)
      }

      setStyleIfChanged(
        el,
        'filter',
        blurPx < 0.15 ? 'none' : `blur(${blurPx.toFixed(1)}px)`,
        0.08
      )
    }
  }

  setScrollGoal(targetY) {
    this._scrollSpring.setGoal(targetY)
  }
}
