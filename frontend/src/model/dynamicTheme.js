import { ref, watch, onMounted, onUnmounted } from 'vue'
import { FastAverageColor } from 'fast-average-color'
import { usePlayer } from './player'

/**
 * Chuyển RGB sang HSL, ép Saturation và Lightness về vùng an toàn,
 * sau đó chuyển ngược lại ra mảng [R, G, B].
 * Mặc định: Saturation 50% (đỡ chói), Lightness 60% (đọc chữ không bị chìm).
 */
function HSLToRGB(h, s, l) {
  const c = (1 - Math.abs(2 * l - 1)) * s
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1))
  const m = l - c / 2

  let [r2, g2, b2] = [0, 0, 0]
  if (h >= 0 && h < 60) [r2, g2, b2] = [c, x, 0]
  else if (h >= 60 && h < 120) [r2, g2, b2] = [x, c, 0]
  else if (h >= 120 && h < 180) [r2, g2, b2] = [0, c, x]
  else if (h >= 180 && h < 240) [r2, g2, b2] = [0, x, c]
  else if (h >= 240 && h < 300) [r2, g2, b2] = [x, 0, c]
  else [r2, g2, b2] = [c, 0, x]

  return [r2, g2, b2].map((v) => Math.round((v + m) * 255))
}

function clampToSafeHSL(r, g, b, targetS = 0.5, targetL = 0.6) {
  r /= 255
  g /= 255
  b /= 255
  const max = Math.max(r, g, b),
    min = Math.min(r, g, b)
  let h = 0
  const d = max - min

  if (d !== 0) {
    if (max === r) h = ((g - b) / d) % 6
    else if (max === g) h = (b - r) / d + 2
    else h = (r - g) / d + 4
  }
  h = Math.round((h * 60 + 360) % 360)

  const [safeR, safeG, safeB] = HSLToRGB(h, targetS, targetL)
  return [safeR, safeG, safeB, h, targetS, targetL]
}

const fac = new FastAverageColor()
const dominantColor = ref('var(--fallback-b1, oklch(var(--b1)))')
const dominantColorLight = ref('')
const dominantColorDark = ref('')
const dominantColorHighlight = ref('')
const dominantColorPrimary = ref('')
const dominantColorAccent = ref('')

let observer = null

export function useDynamicTheme() {
  const player = usePlayer()

  function updateThemeColor(coverUrl) {
    if (!coverUrl) {
      resetColors()
      return
    }

    const img = new Image()
    img.crossOrigin = 'Anonymous'
    img.src = coverUrl
    img.onload = () => {
      fac
        .getColorAsync(img, { algorithm: 'dominant' })
        .then((color) => {
          dominantColor.value = color.hex

          const [safeR, safeG, safeB, h, s, l] = clampToSafeHSL(
            color.value[0],
            color.value[1],
            color.value[2]
          )

          dominantColorLight.value = `rgba(${safeR}, ${safeG}, ${safeB}, 0.15)`
          dominantColorDark.value = `rgba(${safeR}, ${safeG}, ${safeB}, 0.4)`
          dominantColorHighlight.value = `rgb(${safeR}, ${safeG}, ${safeB})`
          dominantColorPrimary.value = `rgb(${safeR}, ${safeG}, ${safeB})`

          const h2 = (h + 35) % 360
          const [r2, g2, b2] = HSLToRGB(h2, s * 0.9, Math.min(0.75, l * 1.15))
          dominantColorAccent.value = `rgb(${r2}, ${g2}, ${b2})`

          applyColors()
        })
        .catch((e) => {
          console.error('Failed to extract dominant color', e)
          resetColors()
        })
    }
    img.onerror = () => {
      resetColors()
    }
  }

  function applyColors() {
    document.documentElement.style.setProperty(
      '--dynamic-bg-hex',
      dominantColor.value
    )
    document.documentElement.style.setProperty(
      '--dynamic-bg-light',
      dominantColorLight.value
    )
    document.documentElement.style.setProperty(
      '--dynamic-bg-dark',
      dominantColorDark.value
    )
    if (dominantColorHighlight.value) {
      document.documentElement.style.setProperty(
        '--dynamic-highlight',
        dominantColorHighlight.value
      )
      document.documentElement.style.setProperty(
        '--dynamic-primary',
        dominantColorPrimary.value
      )
      document.documentElement.style.setProperty(
        '--dynamic-accent',
        dominantColorAccent.value
      )
    }
  }

  function resetColors() {
    dominantColor.value = 'transparent'
    dominantColorLight.value = 'transparent'
    dominantColorDark.value = 'transparent'
    dominantColorHighlight.value = 'transparent'
    dominantColorPrimary.value = 'transparent'
    dominantColorAccent.value = 'transparent'
    document.documentElement.style.removeProperty('--dynamic-bg-hex')
    document.documentElement.style.removeProperty('--dynamic-bg-light')
    document.documentElement.style.removeProperty('--dynamic-bg-dark')
    document.documentElement.style.removeProperty('--dynamic-highlight')
    document.documentElement.style.removeProperty('--dynamic-primary')
    document.documentElement.style.removeProperty('--dynamic-accent')
  }

  watch(
    () => player.currentTrack.value?.cover,
    (newCover) => {
      updateThemeColor(newCover)
    },
    { immediate: true }
  )

  return {
    dominantColor,
  }
}
