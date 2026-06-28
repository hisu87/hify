<template>
  <nav
    class="fixed inset-x-0 bottom-0 z-[120] flex items-center justify-around glass-player-bar lg:hidden pb-[env(safe-area-inset-bottom)]"
  >
    <div class="flex w-full items-center justify-around h-[64px]">
      <button
        v-for="item in navItems"
        :key="item.name"
        @click="navigate(item)"
        class="flex flex-col items-center justify-center w-full h-full min-h-[44px] min-w-[44px] text-base-content/60 transition-colors"
        :class="{ 'text-[#FA233B]': isActive(item.name) }"
        :title="item.label"
        :aria-label="item.label"
      >
        <Icon
          :icon="isActive(item.name) ? item.activeIcon : item.icon"
          class="h-6 w-6 mb-1"
        />
        <span class="text-[10px] font-medium">{{ item.label }}</span>
      </button>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Icon } from '@iconify/vue'

const route = useRoute()
const router = useRouter()

const navItems = [
  {
    name: 'Home',
    label: 'Home',
    icon: 'clarity:home-line',
    activeIcon: 'clarity:home-solid',
  },
  {
    name: 'Search',
    label: 'Search',
    icon: 'clarity:compass-line',
    activeIcon: 'clarity:compass-solid',
  },
  {
    name: 'Player',
    label: 'Listen',
    icon: 'clarity:headphones-line',
    activeIcon: 'clarity:headphones-solid',
  },
  {
    name: 'List',
    label: 'Library',
    icon: 'clarity:library-line',
    activeIcon: 'clarity:library-solid',
  },
]

function isActive(name) {
  return route.name === name
}

function navigate(item) {
  if (item.name === 'Search' && route.name !== 'Search') {
    router.push({ name: 'Search', params: { query: ' ' } })
    return
  }
  router.push({ name: item.name })
}
</script>
