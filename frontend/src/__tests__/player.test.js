import { describe, it, expect } from 'vitest'
import { formatTime } from '../model/player'

describe('formatTime', () => {
  it('formats standard integer seconds into M:SS', () => {
    expect(formatTime(0)).toBe('0:00')
    expect(formatTime(9)).toBe('0:09')
    expect(formatTime(45)).toBe('0:45')
    expect(formatTime(60)).toBe('1:00')
    expect(formatTime(125)).toBe('2:05')
    expect(formatTime(3661)).toBe('61:01')
  })

  it('truncates floating-point seconds cleanly', () => {
    expect(formatTime(125.994)).toBe('2:05')
    expect(formatTime(59.9)).toBe('0:59')
  })

  it('returns "0:00" for non-finite values (NaN, Infinity, undefined)', () => {
    expect(formatTime(NaN)).toBe('0:00')
    expect(formatTime(Infinity)).toBe('0:00')
    expect(formatTime(-Infinity)).toBe('0:00')
    expect(formatTime(undefined)).toBe('0:00')
    expect(formatTime('invalid_string')).toBe('0:00')
  })

  it('returns "0:00" for negative time values', () => {
    expect(formatTime(-1)).toBe('0:00')
    expect(formatTime(-150)).toBe('0:00')
  })

  it('handles falsy numeric coerces safely', () => {
    expect(formatTime(null)).toBe('0:00')
    expect(formatTime('')).toBe('0:00')
  })
})
