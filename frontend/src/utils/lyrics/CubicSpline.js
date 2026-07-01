/**
 * CubicSpline — Catmull-Rom spline qua N keypoints
 *
 * Dùng để định nghĩa "animation curves" cho scale/Y/glow theo % tiến trình từ.
 * Goal của spring = spline.at(progress) mỗi frame.
 *
 * Tại sao Catmull-Rom? Tự động smooth, không cần định nghĩa tangent thủ công.
 */
export class CubicSpline {
  /**
   * @param {Array<{t: number, v: number}>} points - mảng keypoints, t ∈ [0,1] tăng dần
   */
  constructor(points) {
    if (!points || points.length < 2) {
      throw new Error('CubicSpline cần ít nhất 2 keypoints')
    }
    // Đảm bảo sắp xếp theo t tăng dần
    this.points = [...points].sort((a, b) => a.t - b.t)
  }

  /**
   * Nội suy Catmull-Rom tại t ∈ [0,1]
   * @param {number} t
   * @returns {number}
   */
  at(t) {
    const pts = this.points
    const n = pts.length

    // Clamp ngoài biên
    if (t <= pts[0].t) return pts[0].v
    if (t >= pts[n - 1].t) return pts[n - 1].v

    // Tìm đoạn chứa t
    let segIdx = 0
    for (let i = 0; i < n - 1; i++) {
      if (t <= pts[i + 1].t) {
        segIdx = i
        break
      }
    }

    // 4 control points cho Catmull-Rom
    const p0 = pts[Math.max(0, segIdx - 1)]
    const p1 = pts[segIdx]
    const p2 = pts[segIdx + 1]
    const p3 = pts[Math.min(n - 1, segIdx + 2)]

    // Normalize t trong đoạn [p1.t, p2.t]
    const u = (t - p1.t) / (p2.t - p1.t)

    // Catmull-Rom: alpha = 0.5 (standard)
    const alpha = 0.5
    const v0 = p0.v,
      v1 = p1.v,
      v2 = p2.v,
      v3 = p3.v

    const t1 = (v2 - v0) * alpha
    const t2 = (v3 - v1) * alpha

    const u2 = u * u
    const u3 = u2 * u

    return (
      (2 * u3 - 3 * u2 + 1) * v1 +
      (u3 - 2 * u2 + u) * t1 +
      (-2 * u3 + 3 * u2) * v2 +
      (u3 - u2) * t2
    )
  }
}

// ─── Animation Curves ──────────────────────────────────────────────────────────
// Mỗi curve định nghĩa theo % tiến trình của từ/syllable (0 = bắt đầu, 1 = kết thúc)

/**
 * Scale curve:
 * - Bắt đầu gần 1 để tránh chữ nhảy khỏi viewport
 * - Nhấn nhẹ tại ~60% rồi về 1.0 lúc kết thúc
 */
export const SCALE_CURVE = new CubicSpline([
  { t: 0.0, v: 1.0 },
  { t: 0.08, v: 0.97 },
  { t: 0.35, v: 1.06 },
  { t: 0.7, v: 1.01 },
  { t: 1.0, v: 1.0 },
])

/**
 * Y-offset curve (pixel, âm = đi lên):
 * - Bắt đầu: 0
 * - Nhấc lên nhẹ tại giữa (cảm giác "bật")
 * - Hạ về 0 lúc xong
 */
export const Y_OFFSET_CURVE = new CubicSpline([
  { t: 0.0, v: 0 },
  { t: 0.3, v: -1 },
  { t: 0.7, v: -1.5 },
  { t: 1.0, v: 0 },
])

/**
 * Glow intensity curve [0, 1]:
 * - Bùng sáng lên tại 30-70%, tắt dần
 */
export const GLOW_CURVE = new CubicSpline([
  { t: 0.0, v: 0.0 },
  { t: 0.25, v: 0.22 },
  { t: 0.5, v: 0.36 },
  { t: 0.75, v: 0.25 },
  { t: 1.0, v: 0.0 },
])

/**
 * Scale cho word ở trạng thái "Sung" (đã hát xong) — nhỏ hơn chút
 */
export const SCALE_SUNG = 0.99

/**
 * Scale cho word ở trạng thái "NotSung" (chưa hát)
 */
export const SCALE_NOT_SUNG = 0.98

/**
 * Blur (px) cực đại cho dòng không active theo khoảng cách
 */
export const MAX_LINE_BLUR = 2
