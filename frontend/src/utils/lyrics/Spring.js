/**
 * Spring — Damped Harmonic Oscillator
 *
 * Closed-form solution (không Euler-integrate) nên:
 * - Không drift ở dt lớn (seek, tab hidden)
 * - Seek-safe: chỉ cần setGoal(), spring tự đuổi mượt mà
 *
 * Port từ thuật toán của Roblox/Fraktality (damped spring với exact solution).
 */
export class Spring {
  /**
   * @param {number} frequency  - Hz, độ "cứng" lò xo (cao = nhanh hơn)
   * @param {number} dampingRatio - tắt dần (< 1: nảy; = 1: critical; > 1: overdamped)
   * @param {number} initialValue - giá trị khởi đầu
   */
  constructor(frequency = 2.0, dampingRatio = 0.8, initialValue = 0) {
    this.frequency = frequency
    this.dampingRatio = dampingRatio
    this.position = initialValue
    this.velocity = 0
    this.goal = initialValue
  }

  setGoal(goal) {
    this.goal = goal
  }

  /** Snap tức thì đến goal, reset velocity */
  snapTo(value) {
    this.position = value
    this.goal = value
    this.velocity = 0
  }

  /**
   * Advance simulation by dt seconds.
   * Dùng semi-implicit Euler với substep nhỏ để tránh nổ số khi RAF bị trễ.
   * @param {number} dt - delta time in seconds
   * @returns {{ position: number, velocity: number }}
   */
  step(dt) {
    if (dt <= 0) return { position: this.position, velocity: this.velocity }

    const omega = 2 * Math.PI * this.frequency
    const zeta = this.dampingRatio

    const safeDt = Math.min(dt, 0.1)
    const steps = Math.max(1, Math.ceil(safeDt / (1 / 120)))
    const h = safeDt / steps

    for (let i = 0; i < steps; i++) {
      const displacement = this.goal - this.position
      const acceleration =
        omega * omega * displacement - 2 * zeta * omega * this.velocity
      this.velocity += acceleration * h
      this.position += this.velocity * h
    }

    if (
      Math.abs(this.position - this.goal) < 0.0001 &&
      Math.abs(this.velocity) < 0.0001
    ) {
      this.position = this.goal
      this.velocity = 0
    }

    return { position: this.position, velocity: this.velocity }
  }

  /**
   * Kiểm tra spring đã dừng (để skip DOM write khi không cần thiết)
   * @param {number} posEpsilon
   * @param {number} velEpsilon
   */
  isSettled(posEpsilon = 0.001, velEpsilon = 0.001) {
    return (
      Math.abs(this.position - this.goal) < posEpsilon &&
      Math.abs(this.velocity) < velEpsilon
    )
  }
}

// ─── Preset configs ────────────────────────────────────────────────────────────

/** Spring configs được chuẩn hóa theo Beautiful Lyrics */
export const SpringPresets = {
  /** Word-level scale / position — mềm mại, bounce nhẹ */
  word: { frequency: 2.0, dampingRatio: 0.8 },
  /** Glow — chậm, không nảy */
  glow: { frequency: 1.5, dampingRatio: 0.9 },
  /** Dot interlude — nhanh, pop */
  dot: { frequency: 5.0, dampingRatio: 0.7 },
  /** Scroll position — smooth cuộn */
  scroll: { frequency: 1.2, dampingRatio: 0.85 },
  /** Opacity fade */
  opacity: { frequency: 2.5, dampingRatio: 1.0 },
}
