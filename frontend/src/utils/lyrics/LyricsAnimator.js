/**
 * LyricsAnimator — RAF loop chính
 */
import {
  setStyleIfChanged,
  flushStyleBatch,
  clearBatch,
} from './AnimatorStore.js'
import { Spring, SpringPresets } from './Spring.js'

export class LyricsAnimator {
  constructor() {
    this.lines = []
    this._lineEls = new Map()

    this._rafId = null
    this._lastTs = null
    this._scrollSpring = new Spring(2.2, 1.0, 0)

    // Current state
    this._cursorIdx = 0
    this._activeLineIdx = -1
    this._scrollSpring.snapTo(0)

    this._interpolatedTime = 0
    this._lastSyncTs = null
    this._lastRawTime = null
  }

  registerLine(lineIdx, el) {
    if (!el) return
    this._lineEls.set(lineIdx, el)
  }

  unregisterLine(lineIdx) {
    this._lineEls.delete(lineIdx)
  }

  setLines(lines) {
    this.lines = lines || []
    this._cursorIdx = 0
    this._activeLineIdx = -1
    clearBatch()
  }

  start() {
    if (this._rafId) return
    this._lastTs = performance.now()
    this._scrollSpring.snapTo(this._scrollSpring.position)
    this._loop(this._lastTs)
  }

  stop() {
    if (this._rafId) cancelAnimationFrame(this._rafId)
    this._rafId = null
  }

  updateTime(now) {
    if (!this.lines.length) return
    const ts = performance.now()
    this._lastRawTime = now
    this._lastSyncTs = ts
    this._interpolatedTime = now
  }

  _loop(ts) {
    const dt = this._lastTs ? Math.min((ts - this._lastTs) / 1000, 0.1) : 0.016
    this._lastTs = ts

    if (this._lastSyncTs !== null && this._lastRawTime !== null) {
      this._interpolatedTime = this._lastRawTime + (ts - this._lastSyncTs) / 1000
    }

    const now = this._interpolatedTime
    const lines = this.lines

    if (!lines.length) {
      this._rafId = requestAnimationFrame(this._loop.bind(this))
      return
    }

    let cursor = 0
    for (let i = lines.length - 1; i >= 0; i--) {
      if (now >= lines[i].startTime) {
        cursor = i
        break
      }
    }
    this._cursorIdx = cursor

    for (let li = 0; li < lines.length; li++) {
      const line = lines[li]
      const isActiveLine = li === cursor
      const isSungLine = li < cursor

      // Calculate line-level progress for smooth gradient karaoke
      let lineProgressPct = 0
      if (isSungLine) {
        lineProgressPct = 100
      } else if (isActiveLine) {
        let tEnd = line.endTime
        if (!tEnd || tEnd <= line.startTime) {
           tEnd = li + 1 < lines.length ? lines[li + 1].startTime : line.startTime + 2
        }
        const duration = Math.max(tEnd - line.startTime, 0.05)
        lineProgressPct = Math.min(100, Math.max(0, (now - line.startTime) / duration * 100))
      }

      const lineEl = this._lineEls.get(li)
      if (lineEl) {
        setStyleIfChanged(
          lineEl,
          '--line-progress',
          `${lineProgressPct.toFixed(2)}%`,
          0.2
        )
      }
    }

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

  setScrollGoal(targetY) {
    this._scrollSpring.setGoal(targetY)
  }
}
