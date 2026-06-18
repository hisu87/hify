<template>
  <aside
    class="fixed inset-y-0 left-0 z-40 hidden w-[260px] flex-col px-4 py-5 glass-sidebar lg:flex"
  >
    <div class="flex items-center gap-3 px-3 pb-6 pt-2">
      <div
        class="flex h-9 w-9 items-center justify-center rounded-lg bg-[#FA233B] text-white shadow-[0_4px_12px_rgba(250,35,59,0.25)]"
      >
        <img
          src="../assets/downtify.svg"
          class="h-5 w-5 invert brightness-0"
          alt="Downtify"
        />
      </div>
      <div class="min-w-0">
        <h1
          class="text-lg font-bold tracking-tight text-base-content flex items-center gap-1"
        >
          <span class="text-[#FA233B]">Downtify</span>
          <span class="font-normal opacity-80">Music</span>
        </h1>
      </div>
    </div>

    <nav class="space-y-1 px-1">
      <button
        v-for="item in primaryItems"
        :key="item.name"
        class="apple-nav-item w-full"
        :class="isActive(item.name) ? 'apple-nav-item-active' : ''"
        @click="navigate(item)"
        :title="item.label"
      >
        <Icon
          :icon="isActive(item.name) ? item.activeIcon : item.icon"
          class="h-5 w-5 shrink-0"
        />
        <span>{{ item.label }}</span>
        <span
          v-if="item.badge === 'queue' && queueCount > 0"
          class="ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#FA233B] px-1.5 text-[10px] font-bold text-white"
        >
          {{ queueCount }}
        </span>
      </button>
    </nav>

    <div class="mt-8 px-1">
      <p class="apple-pill mb-3 text-base-content/45 text-[10px]">Library</p>
      <nav class="space-y-1">
        <button
          v-for="item in secondaryItems"
          :key="item.name"
          class="apple-nav-item w-full"
          :class="isActive(item.name) ? 'apple-nav-item-active' : ''"
          @click="navigate(item)"
          :title="item.label"
        >
          <Icon
            :icon="isActive(item.name) ? item.activeIcon : item.icon"
            class="h-5 w-5 shrink-0"
          />
          <span>{{ item.label }}</span>
        </button>
      </nav>
    </div>

    <div class="mt-auto space-y-3 px-1 pb-1 pt-6">
      <div
        class="rounded-xl border border-black/5 bg-black/5 dark:border-white/8 dark:bg-white/5 p-4 backdrop-blur-md"
      >
        <p
          class="text-[10px] font-semibold uppercase tracking-[0.25em] text-base-content/45"
        >
          Theme
        </p>
        <div class="mt-3 flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold tracking-tight text-base-content">
              {{ themeLabel }}
            </p>
            <p class="text-[11px] text-base-content/50">
              Glassmorphism enabled
            </p>
          </div>
          <button
            class="icon-btn"
            @click="toggleTheme"
            :title="themeActionLabel"
          >
            <Icon
              :icon="isDark ? 'clarity:sun-line' : 'clarity:moon-line'"
              class="h-5 w-5"
            />
          </button>
        </div>
      </div>

      <label
        for="settings-modal"
        class="apple-nav-item cursor-pointer"
        title="Settings"
      >
        <Icon icon="clarity:cog-line" class="h-5 w-5 shrink-0" />
        <span>Settings</span>
      </label>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { useRoute } from 'vue-router'

import router from '../router'
import { useBinaryThemeManager } from '../model/theme'
import { useProgressTracker } from '../model/download'

const route = useRoute()
const themeMgr = useBinaryThemeManager({
  newLightAlias: 'downtify-light',
  newDarkAlias: 'downtify-dark',
})
const pt = useProgressTracker()

const primaryItems = [
  {
    name: 'Home',
    label: 'Listen Now',
    icon: 'clarity:home-line',
    activeIcon: 'clarity:home-solid',
  },
  {
    name: 'Search',
    label: 'Browse',
    icon: 'clarity:compass-line',
    activeIcon: 'clarity:compass-solid',
  },
  {
    name: 'Download',
    label: 'Queue',
    icon: 'clarity:download-line',
    activeIcon: 'clarity:download-solid',
    badge: 'queue',
  },
]

const secondaryItems = [
  {
    name: 'List',
    label: 'Library',
    icon: 'clarity:library-line',
    activeIcon: 'clarity:library-solid',
  },
  {
    name: 'Player',
    label: 'Player',
    icon: 'clarity:headphones-line',
    activeIcon: 'clarity:headphones-solid',
  },
  {
    name: 'Monitor',
    label: 'Radio',
    icon: 'clarity:eye-line',
    activeIcon: 'clarity:eye-solid',
  },
]

const queueCount = computed(() => pt.downloadQueue.value.length)
const isDark = computed(() => themeMgr.currentTheme.value === 'dark')
const themeLabel = computed(() => (isDark.value ? 'Dark mode' : 'Light mode'))
const themeActionLabel = computed(() =>
  isDark.value ? 'Switch to light mode' : 'Switch to dark mode'
)

function isActive(name) {
  return route.name === name
}

function navigate(item) {
  if (item.name === 'Search') {
    router.push({ name: 'Search', params: { query: ' ' } })
    return
  }
  router.push({ name: item.name })
}

function toggleTheme() {
  themeMgr.setTheme(isDark.value ? 'light' : 'dark')
}
</script>
