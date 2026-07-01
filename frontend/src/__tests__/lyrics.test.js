import { describe, expect, it, vi, beforeAll, afterAll } from 'vitest'
import { parseLrc } from '../utils/lyrics/LrcParser.js'
import { LyricsAnimator } from '../utils/lyrics/LyricsAnimator.js'

describe('Lyrics Parser and Animator', () => {
  beforeAll(() => {
    global.requestAnimationFrame = vi.fn((cb) => setTimeout(cb, 16))
    global.cancelAnimationFrame = vi.fn((id) => clearTimeout(id))
  })

  afterAll(() => {
    delete global.requestAnimationFrame
    delete global.cancelAnimationFrame
  })

  it('correctly parses standard LRC and estimates word timings', () => {
    const lrc = `[00:00.00] Line 1
[00:10.00] Line 2 Word`
    const parsed = parseLrc(lrc)
    expect(parsed.length).toBe(2)
    expect(parsed[0].startTime).toBe(0)
    expect(parsed[0].endTime).toBe(10) // 10s gap
    expect(parsed[0].lead.length).toBe(2) // 'Line', '1'
    expect(parsed[0].lead[0].text).toBe('Line')
    expect(parsed[0].lead[1].text).toBe('1')
    expect(parsed[0].lead[0].startTime).toBe(0)
    expect(parsed[0].lead[1].startTime).toBeGreaterThan(0)
  })

  it('correctly calculates fractional active line index', () => {
    const animator = new LyricsAnimator()
    animator.lines = [
      { startTime: 0, endTime: 10, rawText: 'Line 1', lead: [] },
      { startTime: 10, endTime: 30, rawText: 'Line 2', lead: [] },
      { startTime: 30, endTime: 40, rawText: 'Line 3', lead: [] },
    ]

    // Exactly at start
    expect(animator._findActiveLineFrac(0, 0)).toBe(0)
    // Halfway between line 1 and 2
    expect(animator._findActiveLineFrac(5, 0)).toBe(0.5)
    // Exactly at line 2
    expect(animator._findActiveLineFrac(10, 1)).toBe(1)
    // Quarter way between line 2 and 3 (range 10 to 30, duration 20, at time 15 it is 5/20 = 0.25 progress)
    expect(animator._findActiveLineFrac(15, 1)).toBe(1.25)
    // At the end
    expect(animator._findActiveLineFrac(35, 2)).toBe(2)
  })

  it('interpolates time smoothly when isPlaying is true', () => {
    const animator = new LyricsAnimator()
    animator.lines = [
      { startTime: 0, endTime: 10, rawText: 'Line 1', lead: [] },
    ]

    // Mock the window.devicePixelRatio since LyricsAnimator checks it
    global.window = { devicePixelRatio: 2 }

    let mockTime = 5.0
    animator.audioElement = {
      get currentTime() {
        return mockTime
      },
    }
    animator.isPlaying = () => true

    // Frame 1: initial sync
    animator._loop(1000)
    expect(animator._interpolatedTime).toBe(5.0)
    expect(animator._lastSyncTs).toBe(1000)

    // Frame 2: 100ms later, audio time also advances to 5.1
    mockTime = 5.1
    animator._loop(1100)
    expect(animator._interpolatedTime).toBeCloseTo(5.1, 2)
    expect(animator._lastSyncTs).toBe(1100)

    delete global.window
  })

  it('snaps time when a seek is detected', () => {
    const animator = new LyricsAnimator()
    animator.lines = [
      { startTime: 0, endTime: 10, rawText: 'Line 1', lead: [] },
    ]

    global.window = { devicePixelRatio: 2 }

    let mockTime = 5.0
    animator.audioElement = {
      get currentTime() {
        return mockTime
      },
    }
    animator.isPlaying = () => true

    // Frame 1
    animator._loop(1000)

    // Frame 2: seek to 20.0 (sudden change > 0.15s)
    mockTime = 20.0
    animator._loop(1100)
    expect(animator._interpolatedTime).toBe(20.0)

    delete global.window
  })

  it('safely estimates word timings for lines with irregular whitespace or empty content', () => {
    const weirdSpacingLrc = `
[00:10.00] \t   \t
[00:15.00]
[00:20.00] Hify \t\t rocks   !
    `.trim()

    const parsed = parseLrc(weirdSpacingLrc)

    expect(parsed).toHaveLength(3)

    // 1. Pure whitespace line
    expect(parsed[0].lead).toEqual([])

    // 2. Empty content line
    expect(parsed[1].lead).toEqual([])

    // 3. Irregular tabs and spaces between valid words
    const lineThreeWords = parsed[2].lead
    expect(lineThreeWords).toHaveLength(3)
    expect(lineThreeWords[0].text).toBe('Hify')
    expect(lineThreeWords[1].text).toBe('rocks')
    expect(lineThreeWords[2].text).toBe('!')

    // Verify delays and durations calculated cleanly without NaN
    for (const w of lineThreeWords) {
      expect(Number.isNaN(w.endTime)).toBe(false)
      expect(Number.isNaN(w.startTime)).toBe(false)
      expect(w.endTime).toBeGreaterThan(w.startTime)
    }
  })
  it('gracefully skips invalid or malformed LRC lines', () => {
    const malformedLrc = `
[ar: Awesome Artist]
[ti: Cool Song]
Just some plain introductory text without brackets
[invalid:time] Malformed bracket line
[00:10.50] First valid lyric line
[99:99.9999] Out of bounds regex line
[00:15.20] Second valid lyric line
    `.trim()

    const parsed = parseLrc(malformedLrc)

    // Should strictly parse only the 2 valid timestamp lines
    expect(parsed).toHaveLength(2)
    expect(parsed[0].rawText).toBe('First valid lyric line')
    expect(parsed[1].rawText).toBe('Second valid lyric line')
  })

  it('gracefully handles malformed enhanced word timings within a valid line', () => {
    // Line is valid, but inner word tags contain malformed brackets
    const mixedWordLrc = `[00:10.00] <00:10.10> Hello <broken:tag> world <00:10.50> !`

    const parsed = parseLrc(mixedWordLrc)

    expect(parsed).toHaveLength(1)
    expect(parsed[0].lead).toBeDefined()
    // Ensure the parser didn't crash and extracted valid segments
    expect(parsed[0].lead.length).toBeGreaterThan(0)
  })

  it('handles non-string inputs gracefully', () => {
    expect(parseLrc(null)).toEqual([])
    expect(parseLrc(undefined)).toEqual([])
    expect(parseLrc(123)).toEqual([])
  })
})
