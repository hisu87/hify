import { ref, watch, onMounted, onUnmounted } from 'vue'
import { FastAverageColor } from 'fast-average-color'
import { usePlayer } from './player'

const fac = new FastAverageColor()
const dominantColor = ref('var(--fallback-b1, oklch(var(--b1)))')
const dominantColorLight = ref('')
const dominantColorDark = ref('')

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
      fac.getColorAsync(img, { algorithm: 'dominant' })
        .then(color => {
          // color.hex, color.isDark, color.isLight
          dominantColor.value = color.hex
          
          // Set opacity variations for backgrounds
          const rgba = color.rgba.replace(')', ', 0.15)').replace('rgb', 'rgba')
          const rgbaDark = color.rgba.replace(')', ', 0.4)').replace('rgb', 'rgba')
          
          dominantColorLight.value = rgba
          dominantColorDark.value = rgbaDark

          applyColors()
        })
        .catch(e => {
          console.error('Failed to extract dominant color', e)
          resetColors()
        })
    }
    img.onerror = () => {
      resetColors()
    }
  }

  function applyColors() {
    document.documentElement.style.setProperty('--dynamic-bg-hex', dominantColor.value)
    document.documentElement.style.setProperty('--dynamic-bg-light', dominantColorLight.value)
    document.documentElement.style.setProperty('--dynamic-bg-dark', dominantColorDark.value)
  }

  function resetColors() {
    dominantColor.value = 'transparent'
    dominantColorLight.value = 'transparent'
    dominantColorDark.value = 'transparent'
    document.documentElement.style.removeProperty('--dynamic-bg-hex')
    document.documentElement.style.removeProperty('--dynamic-bg-light')
    document.documentElement.style.removeProperty('--dynamic-bg-dark')
  }

  watch(() => player.currentTrack.value?.cover, (newCover) => {
    updateThemeColor(newCover)
  }, { immediate: true })

  return {
    dominantColor
  }
}
