<template>
  <aside
    class="sticky top-0 z-40 hidden h-dvh flex-col py-5 glass-sidebar lg:flex transition-[width] duration-300"
    :class="
      layout.isLeftSidebarCollapsed.value ? 'w-[80px] px-2' : 'w-[260px] px-4'
    "
  >
    <div class="flex items-center px-3 pb-6 pt-2 justify-center">
      <div class="flex items-center justify-center">
        <img
          v-if="!layout.isLeftSidebarCollapsed.value"
          src="../assets/14884.png"
          class="h-[80px] w-auto object-contain"
          alt="Hify"
        />
        <img
          v-else
          src="../assets/14882.png"
          class="h-[40px] w-auto object-contain"
          alt="Hify"
        />
      </div>
    </div>

    <nav
      class="space-y-1"
      :class="layout.isLeftSidebarCollapsed.value ? '' : 'px-1'"
    >
      <button
        v-for="item in primaryItems"
        :key="item.name"
        class="apple-nav-item w-full"
        :class="[
          isActive(item.name) ? 'apple-nav-item-active' : '',
          layout.isLeftSidebarCollapsed.value ? 'justify-center px-0' : '',
        ]"
        @click="navigate(item)"
        :title="item.label"
      >
        <Icon
          :icon="isActive(item.name) ? item.activeIcon : item.icon"
          class="h-5 w-5 shrink-0"
        />
        <span v-show="!layout.isLeftSidebarCollapsed.value">{{
          item.label
        }}</span>
        <span
          v-if="
            item.badge === 'queue' &&
            queueCount > 0 &&
            !layout.isLeftSidebarCollapsed.value
          "
          class="ml-auto inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-[#FA233B] px-1.5 text-[10px] font-bold text-white"
        >
          {{ queueCount }}
        </span>
        <div
          v-else-if="
            item.badge === 'queue' &&
            queueCount > 0 &&
            layout.isLeftSidebarCollapsed.value
          "
          class="absolute top-1 right-1 h-2 w-2 rounded-full bg-[#FA233B]"
        ></div>
      </button>
    </nav>

    <div
      class="mt-8"
      :class="layout.isLeftSidebarCollapsed.value ? '' : 'px-1'"
    >
      <p
        class="apple-pill mb-3 text-base-content/45 text-[10px]"
        v-show="!layout.isLeftSidebarCollapsed.value"
      >
        Library
      </p>
      <div
        v-show="layout.isLeftSidebarCollapsed.value"
        class="h-[1px] w-8 bg-base-content/10 mx-auto mb-3"
      ></div>
      <nav class="space-y-1">
        <button
          v-for="item in secondaryItems"
          :key="item.name"
          class="apple-nav-item w-full"
          :class="[
            isActive(item.name) ? 'apple-nav-item-active' : '',
            layout.isLeftSidebarCollapsed.value ? 'justify-center px-0' : '',
          ]"
          @click="navigate(item)"
          :title="item.label"
        >
          <Icon
            :icon="isActive(item.name) ? item.activeIcon : item.icon"
            class="h-5 w-5 shrink-0"
          />
          <span v-show="!layout.isLeftSidebarCollapsed.value">{{
            item.label
          }}</span>
        </button>
      </nav>
    </div>

    <div
      class="mt-auto space-y-3 pb-1 pt-6"
      :class="layout.isLeftSidebarCollapsed.value ? '' : 'px-1'"
    >
      <div
        v-if="!layout.isLeftSidebarCollapsed.value"
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
      <button
        v-else
        class="apple-nav-item w-full justify-center px-0"
        @click="toggleTheme"
        :title="themeActionLabel"
      >
        <Icon
          :icon="isDark ? 'clarity:sun-line' : 'clarity:moon-line'"
          class="h-5 w-5 shrink-0"
        />
      </button>

      <label
        for="settings-modal"
        class="apple-nav-item cursor-pointer"
        :class="
          layout.isLeftSidebarCollapsed.value ? 'justify-center px-0' : ''
        "
        title="Settings"
      >
        <Icon icon="clarity:cog-line" class="h-5 w-5 shrink-0" />
        <span v-show="!layout.isLeftSidebarCollapsed.value">Settings</span>
      </label>

      <button
        class="apple-nav-item w-full"
        :class="
          layout.isLeftSidebarCollapsed.value ? 'justify-center px-0' : ''
        "
        @click="layout.toggleLeftSidebar()"
        title="Toggle Sidebar"
      >
        <Icon
          :icon="
            layout.isLeftSidebarCollapsed.value
              ? 'clarity:step-forward-line'
              : 'clarity:step-backward-line'
          "
          class="h-5 w-5 shrink-0"
        />
        <span v-show="!layout.isLeftSidebarCollapsed.value">Collapse</span>
      </button>
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
import { useLayout } from '../model/layout'

const route = useRoute()
const themeMgr = useBinaryThemeManager({
  newLightAlias: 'hify-light',
  newDarkAlias: 'hify-dark',
})
const pt = useProgressTracker()
const layout = useLayout()

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
