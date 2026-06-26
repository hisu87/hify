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
    expect(parsed[0].time).toBe(0)
    expect(parsed[0].duration).toBe(10) // 10s gap
    expect(parsed[0].words.length).toBe(2) // 'Line', '1'
    expect(parsed[0].words[0].text).toBe('Line')
    expect(parsed[0].words[1].text).toBe('1')
    // Estimated delay for word 2 is proportional to character length
    expect(parsed[0].words[0].delay).toBe(0)
    expect(parsed[0].words[1].delay).toBeGreaterThan(0)
  })

  it('correctly calculates fractional active line index', () => {
    const animator = new LyricsAnimator()
    animator.lines = [
      { time: 0, duration: 10, text: 'Line 1', words: [] },
      { time: 10, duration: 20, text: 'Line 2', words: [] },
      { time: 30, duration: 10, text: 'Line 3', words: [] },
    ]

    // Exactly at start
    expect(animator._findActiveLineFrac(0)).toBe(0)
    // Halfway between line 1 and 2
    expect(animator._findActiveLineFrac(5)).toBe(0.5)
    // Exactly at line 2
    expect(animator._findActiveLineFrac(10)).toBe(1)
    // Quarter way between line 2 and 3 (range 10 to 30, duration 20, at time 15 it is 5/20 = 0.25 progress)
    expect(animator._findActiveLineFrac(15)).toBe(1.25)
    // At the end
    expect(animator._findActiveLineFrac(35)).toBe(2)
  })

  it('interpolates time smoothly when isPlaying is true', () => {
    const animator = new LyricsAnimator()
    animator.lines = [{ time: 0, duration: 10, text: 'Line 1', words: [] }]
    let mockTime = 5.0
    animator.getTime = () => mockTime
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
  })

  it('snaps time when a seek is detected', () => {
    const animator = new LyricsAnimator()
    animator.lines = [{ time: 0, duration: 10, text: 'Line 1', words: [] }]
    animator.getTime = () => 5.0
    animator.isPlaying = () => true

    // Frame 1
    animator._loop(1000)

    // Frame 2: seek to 20.0 (sudden change > 0.15s)
    animator.getTime = () => 20.0
    animator._loop(1100)
    expect(animator._interpolatedTime).toBe(20.0)
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
    `.trim();

    const parsed = parseLrc(malformedLrc);

    // Should strictly parse only the 2 valid timestamp lines
    expect(parsed).toHaveLength(2);
    expect(parsed[0].text).toBe('First valid lyric line');
    expect(parsed[1].text).toBe('Second valid lyric line');
  });

  it('gracefully handles malformed enhanced word timings within a valid line', () => {
    // Line is valid, but inner word tags contain malformed brackets
    const mixedWordLrc = `[00:10.00] <00:10.10> Hello <broken:tag> world <00:10.50> !`;

    const parsed = parseLrc(mixedWordLrc);

    expect(parsed).toHaveLength(1);
    expect(parsed[0].words).toBeDefined();
    // Ensure the parser didn't crash and extracted valid segments
    expect(parsed[0].words.length).toBeGreaterThan(0);
  });

  it('handles non-string inputs gracefully', () => {
    expect(parseLrc(null)).toEqual([]);
    expect(parseLrc(undefined)).toEqual([]);
    expect(parseLrc(123)).toEqual([]);
  });
})
