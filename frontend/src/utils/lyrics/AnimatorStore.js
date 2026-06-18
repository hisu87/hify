/**
 * AnimatorStore — Per-element Spring store với style batching
 *
 * Dùng WeakMap để tránh memory leak khi DOM element bị unmount.
 * Style batching: chỉ ghi DOM nếu giá trị thay đổi vượt epsilon.
 */
import { Spring, SpringPresets } from './Spring.js'

// WeakMap lưu AnimatorEntry cho từng DOM element
const storeMap = new WeakMap()

// Pending style writes (element → Map<prop, value>)
const pendingWrites = new Map()

// Cache giá trị đã ghi để so sánh epsilon
const styleCache = new WeakMap()

/**
 * @typedef {Object} WordAnimatorEntry
 * @property {Spring} scaleSpring
 * @property {Spring} ySpring
 * @property {Spring} glowSpring
 * @property {Spring} opacitySpring
 * @property {Spring} fillSpring   - % gradient fill [0, 100]
 */

/**
 * Lấy (hoặc lazy-init) animator entry cho element
 * @param {Element} el
 * @returns {WordAnimatorEntry}
 */
export function getWordStore(el) {
  if (storeMap.has(el)) return storeMap.get(el)

  const entry = {
    scaleSpring: new Spring(
      SpringPresets.word.frequency,
      SpringPresets.word.dampingRatio,
      0.94
    ),
    ySpring: new Spring(
      SpringPresets.word.frequency,
      SpringPresets.word.dampingRatio,
      0
    ),
    glowSpring: new Spring(
      SpringPresets.glow.frequency,
      SpringPresets.glow.dampingRatio,
      0
    ),
    opacitySpring: new Spring(
      SpringPresets.opacity.frequency,
      SpringPresets.opacity.dampingRatio,
      0.35
    ),
    fillSpring: new Spring(4.0, 0.85, 0),
  }

  storeMap.set(el, entry)
  styleCache.set(el, {})
  return entry
}

/**
 * Snap tất cả spring của element về trạng thái mặc định (khi song thay đổi)
 */
export function resetWordStore(el) {
  if (!storeMap.has(el)) return
  const entry = storeMap.get(el)
  entry.scaleSpring.snapTo(0.92)
  entry.ySpring.snapTo(0)
  entry.glowSpring.snapTo(0)
  entry.opacitySpring.snapTo(0.35)
  entry.fillSpring.snapTo(0)
}

/**
 * Xóa entry (khi component unmount hoàn toàn)
 */
export function clearWordStore(el) {
  storeMap.delete(el)
  styleCache.delete(el)
  pendingWrites.delete(el)
}

// ─── Style Batching ────────────────────────────────────────────────────────────

/**
 * Enqueue style write nếu giá trị thay đổi vượt epsilon.
 * Không ghi DOM ngay — dồn lại ghi một lần ở flushStyleBatch().
 *
 * @param {Element} el
 * @param {string} prop - CSS property name
 * @param {string} value - computed string value
 * @param {number} epsilon - nếu 0, luôn ghi
 */
export function setStyleIfChanged(el, prop, value, epsilon = 0) {
  if (!el) return

  let cache = styleCache.get(el)
  if (!cache) {
    cache = {}
    styleCache.set(el, cache)
  }

  if (epsilon > 0) {
    const prev = cache[prop]
    if (
      prev !== undefined &&
      Math.abs(parseFloat(value) - parseFloat(prev)) < epsilon
    ) {
      return // Skip: thay đổi nhỏ hơn epsilon, không đáng ghi
    }
  } else {
    if (cache[prop] === value) return // exact match
  }

  cache[prop] = value

  if (!pendingWrites.has(el)) pendingWrites.set(el, new Map())
  pendingWrites.get(el).set(prop, value)
}

/**
 * Ghi tất cả pending styles vào DOM — gọi một lần cuối mỗi frame
 */
export function flushStyleBatch() {
  for (const [el, writes] of pendingWrites) {
    // Bỏ qua element không còn trong DOM (bị virtualizer unmount)
    if (!el.isConnected) {
      pendingWrites.delete(el)
      continue
    }
    for (const [prop, value] of writes) {
      if (prop.startsWith('--')) {
        el.style.setProperty(prop, value)
      } else {
        el.style[prop] = value
      }
    }
    writes.clear()
  }
  pendingWrites.clear()
}

/**
 * Reset toàn bộ batch (khi close lyrics hoặc đổi bài)
 */
export function clearBatch() {
  pendingWrites.clear()
}
