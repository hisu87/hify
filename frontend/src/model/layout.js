import { ref } from 'vue'

const isLeftSidebarCollapsed = ref(false)
const isRightSidebarOpen = ref(false)
const isQueueOpen = ref(false)

export function useLayout() {
  return {
    isLeftSidebarCollapsed,
    isRightSidebarOpen,
    isQueueOpen,
    toggleLeftSidebar: () => {
      isLeftSidebarCollapsed.value = !isLeftSidebarCollapsed.value
    },
    toggleRightSidebar: () => {
      isRightSidebarOpen.value = !isRightSidebarOpen.value
    },
    toggleQueue: () => {
      isQueueOpen.value = !isQueueOpen.value
    },
  }
}
