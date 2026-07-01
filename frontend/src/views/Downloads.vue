<template>
  <div class="min-h-screen">
    <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <!-- Header -->
      <div class="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">
            {{ t('library.title') }}
          </h1>
          <p class="mt-1 text-sm text-base-content/60">
            {{ t('library.subtitle') }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            v-if="files.length > 0"
            class="btn btn-primary btn-sm h-11 px-5 rounded-full"
            @click="playAll"
            :title="t('library.play')"
          >
            <Icon icon="clarity:play-line" class="h-4 w-4 mr-1.5" />
            {{ t('library.play') }}
          </button>
          <button
            class="btn btn-sm h-11 px-5 rounded-full border-white/10 bg-base-100/85 hover:bg-base-100"
            @click="refresh"
            :disabled="loading"
          >
            <img
              v-if="loading"
              src="../assets/14886.gif"
              class="h-4 w-4 object-contain mr-2"
            />
            <Icon v-else icon="clarity:refresh-line" class="h-4 w-4 mr-2" />
            {{ t('common.refresh') }}
          </button>
        </div>
      </div>

      <!-- Error -->
      <div
        v-if="error"
        class="surface rounded-2xl p-4 mb-4 flex gap-3 items-center text-sm text-error"
      >
        <Icon icon="clarity:exclamation-circle-line" class="h-5 w-5 shrink-0" />
        <span>{{ error }}</span>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading && files.length === 0" class="space-y-3">
        <div v-for="n in 4" :key="n" class="skeleton h-16 rounded-2xl" />
      </div>

      <!-- Empty state -->
      <div
        v-else-if="files.length === 0"
        class="surface rounded-2xl p-12 flex flex-col items-center text-center"
      >
        <Icon
          icon="clarity:library-line"
          class="h-12 w-12 text-base-content/20 mb-4"
        />
        <p class="text-base-content/50 text-sm">{{ t('library.empty') }}</p>
        <p class="text-base-content/40 text-xs mt-1">
          {{ t('library.emptyHint') }}
        </p>
      </div>

      <!-- File list (Virtual Scroller) -->
      <RecycleScroller
        v-else
        class="scroller h-[70vh] pr-2 -mr-2"
        :items="virtualFiles"
        :item-size="80"
        key-field="id"
        v-slot="{ item: { file } }"
      >
        <div class="py-1">
        <li
          class="surface rounded-2xl p-3 sm:p-4 flex items-center gap-3"
        >
          <!-- Cover thumb -->
          <div
            class="relative h-11 w-11 shrink-0 rounded-xl bg-primary/10 text-primary flex items-center justify-center overflow-hidden"
          >
            <img
              v-if="!coverFailed[file]"
              :src="coverUrlFor(file)"
              :alt="file"
              class="absolute inset-0 h-full w-full object-cover"
              loading="lazy"
              @error="markCoverFailed(file)"
            />
            <Icon v-else icon="clarity:music-note-line" class="h-5 w-5" />
          </div>

          <!-- Filename -->
          <div class="flex-1 min-w-0">
            <span class="text-sm font-medium truncate block">{{
              displayName(file)
            }}</span>
            <span class="text-xs text-base-content/40 truncate block">
              <span v-if="folderOf(file)" class="mr-2 text-primary/70">
                <Icon
                  icon="clarity:folder-line"
                  class="inline h-3 w-3 mr-0.5 align-text-top"
                />{{ folderOf(file) }}
              </span>
              {{ formatExt(file) }}
            </span>
          </div>

          <!-- Actions -->
          <div class="flex items-center gap-1 shrink-0">
            <button
              class="icon-btn text-primary hover:bg-primary/10"
              @click="playFile(files.indexOf(file))"
              :title="t('library.play')"
            >
              <Icon icon="clarity:play-line" class="h-4 w-4" />
            </button>
            <a
              class="icon-btn"
              :href="API.downloadFileURL(file)"
              download
              :title="t('library.downloadToDevice')"
            >
              <Icon icon="clarity:download-line" class="h-4 w-4" />
            </a>
            <button
              class="icon-btn text-error/70 hover:text-error hover:bg-error/10"
              :disabled="deleting[file] === true"
              @click="onDelete(file)"
              :title="t('library.deleteFile')"
            >
              <img
                v-if="deleting[file] === true"
                src="../assets/14886.gif"
                class="h-4 w-4 object-contain"
              />
              <Icon v-else icon="clarity:trash-line" class="h-4 w-4" />
            </button>
          </div>
        </li>
        </div>
      </RecycleScroller>

      <!-- Count footer -->
      <p
        v-if="files.length > 0"
        class="mt-6 text-xs text-base-content/40 text-center"
      >
        {{
          files.length === 1
            ? t('library.countOne', { count: files.length })
            : t('library.countMany', { count: files.length })
        }}
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useRouter } from 'vue-router'
import API from '/src/model/api'
import { useI18n } from '/src/i18n'
import { usePlayer } from '/src/model/player'

const PAGE_SIZE = 10

const { t } = useI18n()
const player = usePlayer()
const router = useRouter()

const files = ref([])
const virtualFiles = computed(() => files.value.map((f, i) => ({ id: typeof f === 'object' ? f.id || i : f, file: f })))
const loading = ref(false)
const error = ref('')
const deleting = ref({})
const coverFailed = ref({})

function coverUrlFor(file) {
  if (typeof file === 'object' && file.cover_url) return file.cover_url
  const name = typeof file === 'string' ? file : file.file || ''
  return API.coverFileURL(name)
}

function markCoverFailed(file) {
  const name = typeof file === 'string' ? file : file.file || ''
  coverFailed.value = { ...coverFailed.value, [name]: true }
}

async function refresh() {
  loading.value = true
  error.value = ''
  try {
    const res = await API.listDownloads()
    files.value = res.data || []
  } catch {
    error.value = t('library.failedLoad')
  } finally {
    loading.value = false
  }
}

async function onDelete(file) {
  const name = typeof file === 'string' ? file : file.file
  if (!confirm(t('library.deletePrompt', { file: name }))) return
  deleting.value = { ...deleting.value, [name]: true }
  try {
    await API.deleteDownload(name)
    files.value = files.value.filter((f) => (typeof f === 'string' ? f : f.file) !== name)
  } catch {
    error.value = t('library.failedDelete', { file: name })
  } finally {
    deleting.value = { ...deleting.value, [name]: false }
  }
}

function formatExt(file) {
  const name = typeof file === 'string' ? file : file.file || ''
  const dot = name.lastIndexOf('.')
  return dot > 0 ? name.slice(dot + 1).toUpperCase() : ''
}

function displayName(file) {
  if (typeof file === 'object' && file.title) return file.title
  const name = typeof file === 'string' ? file : file.file || ''
  const slash = name.lastIndexOf('/')
  return slash >= 0 ? name.slice(slash + 1) : name
}

function folderOf(file) {
  const name = typeof file === 'string' ? file : file.file || ''
  const slash = name.lastIndexOf('/')
  return slash >= 0 ? name.slice(0, slash) : ''
}

function playFile(index) {
  player.setPlaylist(files.value, { startIndex: index })
  router.push({ name: 'Player' })
}

function playAll() {
  if (!files.value.length) return
  player.setPlaylist(files.value, { startIndex: 0 })
  router.push({ name: 'Player' })
}

onMounted(refresh)
</script>
