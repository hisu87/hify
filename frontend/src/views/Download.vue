<template>
  <div class="min-h-screen">
    <DownloadList />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import DownloadList from '/src/components/DownloadList.vue'

onMounted(() => window.scroll(0, 0))
</script>
