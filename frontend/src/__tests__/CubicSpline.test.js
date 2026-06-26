import { describe, it, expect } from 'vitest'
import {
  CubicSpline,
  SCALE_CURVE,
  Y_OFFSET_CURVE,
  GLOW_CURVE,
} from '../utils/lyrics/CubicSpline'

describe('CubicSpline', () => {
  it('throws an error if less than 2 keypoints are provided', () => {
    expect(() => new CubicSpline()).toThrow(
      'CubicSpline cần ít nhất 2 keypoints'
    )
    expect(() => new CubicSpline([])).toThrow()
    expect(() => new CubicSpline([{ t: 0, v: 1 }])).toThrow()
  })

  it('sorts keypoints by t ascending', () => {
    const spline = new CubicSpline([
      { t: 1, v: 10 },
      { t: 0, v: 0 },
      { t: 0.5, v: 5 },
    ])
    expect(spline.points[0].t).toBe(0)
    expect(spline.points[1].t).toBe(0.5)
    expect(spline.points[2].t).toBe(1)
  })

  it('clamps values at lower and upper boundaries', () => {
    const spline = new CubicSpline([
      { t: 0, v: 10 },
      { t: 1, v: 20 },
    ])
    expect(spline.at(-0.5)).toBe(10)
    expect(spline.at(1.5)).toBe(20)
  })

  it('evaluates exactly at keypoints (segment boundaries)', () => {
    const spline = new CubicSpline([
      { t: 0, v: 0 },
      { t: 0.3, v: 5 },
      { t: 0.7, v: 10 },
      { t: 1.0, v: 20 },
    ])
    // Floating point math in splines necessitates toBeCloseTo
    expect(spline.at(0)).toBeCloseTo(0)
    expect(spline.at(0.3)).toBeCloseTo(5)
    expect(spline.at(0.7)).toBeCloseTo(10)
    expect(spline.at(1.0)).toBeCloseTo(20)
  })

  it('handles a 2-point minimum (linear-like fallback)', () => {
    const spline = new CubicSpline([
      { t: 0, v: 0 },
      { t: 1, v: 10 },
    ])
    expect(spline.at(0)).toBeCloseTo(0)
    // A 2-point Catmull-Rom effectively degrades gracefully to linear
    expect(spline.at(0.5)).toBeCloseTo(5)
    expect(spline.at(1)).toBeCloseTo(10)
  })

  it('interpolates smoothly at midpoints', () => {
    const spline = new CubicSpline([
      { t: 0, v: 0 },
      { t: 0.5, v: 10 },
      { t: 1, v: 0 },
    ])
    const mid = spline.at(0.25)
    expect(mid).toBeGreaterThan(0)
    expect(mid).toBeLessThan(10)
  })

  it('handles negative v values correctly', () => {
    const spline = new CubicSpline([
      { t: 0, v: 0 },
      { t: 0.5, v: -10 },
      { t: 1, v: 0 },
    ])
    expect(spline.at(0.5)).toBeCloseTo(-10)

    // Test a midpoint to ensure it interpolates downwards into the negative
    const mid = spline.at(0.25)
    expect(mid).toBeLessThan(0)
    expect(mid).toBeGreaterThan(-10)
  })
})

describe('Exported Constants', () => {
  it('evaluates SCALE_CURVE safely across the domain', () => {
    expect(SCALE_CURVE.at(0)).toBeTypeOf('number')
    expect(SCALE_CURVE.at(0.5)).toBeTypeOf('number')
    expect(SCALE_CURVE.at(1)).toBeTypeOf('number')
    expect(Number.isNaN(SCALE_CURVE.at(0.5))).toBe(false)
  })

  it('evaluates Y_OFFSET_CURVE safely across the domain', () => {
    expect(Y_OFFSET_CURVE.at(0)).toBeTypeOf('number')
    expect(Y_OFFSET_CURVE.at(0.5)).toBeTypeOf('number')
    expect(Y_OFFSET_CURVE.at(1)).toBeTypeOf('number')
    expect(Number.isNaN(Y_OFFSET_CURVE.at(0.5))).toBe(false)
  })

  it('evaluates GLOW_CURVE safely across the domain', () => {
    expect(GLOW_CURVE.at(0)).toBeTypeOf('number')
    expect(GLOW_CURVE.at(0.5)).toBeTypeOf('number')
    expect(GLOW_CURVE.at(1)).toBeTypeOf('number')
    expect(Number.isNaN(GLOW_CURVE.at(0.5))).toBe(false)
  })
})
