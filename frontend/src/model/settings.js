import { ref, computed } from 'vue'

import API from '/src/model/api'

const settings = ref({
  audio_providers: [''],
  lyrics_providers: ['auto'],
  download_lyrics: true,
  format: '',
  bitrate: '320',
  output: '',
  generate_m3u: true,
  organize_by_artist: false,
  max_parallel_downloads: 3,
})

const settingsOptions = {
  audio_providers: ['youtube', 'youtube-music'],
  lyrics_providers: ['auto', 'lrclib', 'netease', 'amll', 'musixmatch'],
  format: ['mp3', 'flac', 'ogg', 'opus', 'm4a'],
  bitrate: ['128', '192', '256', '320'],
  max_parallel_downloads: [1, 2, 3, 5, 8],
  output: '{artists} - {title}.{output-ext}',
}

API.getSettings().then((res) => {
  if (res.status === 200) {
    console.log('Received settings:', res.data)
    settings.value = res.data
  } else {
    console.log('Error loading settings')
  }
})

export function useSettingsManager() {
  const isSaved = ref()
  const isSaving = ref(false)
  function saveSettings() {
    console.log('Saving settings:', settings.value)
    isSaving.value = true
    API.setSettings(settings.value)
      .then((res) => {
        isSaving.value = false
        if (res.status === 200) {
          console.log('Saved!')
          isSaved.value = true
          setTimeout(() => {
            isSaved.value = null
          }, 2000)
        } else {
          console.error('Error saving settings.', res)
          isSaved.value = false
          setTimeout(() => {
            isSaved.value = null
          }, 2000)
        }
      })
      .catch(() => {
        isSaving.value = false
      })
  }
  return { saveSettings, settings, settingsOptions, isSaved, isSaving }
}
