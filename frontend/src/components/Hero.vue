<template>
  <section
    class="relative flex min-h-[calc(100dvh-4rem)] items-center justify-center px-6 pt-24 pb-16 overflow-hidden"
  >
    <div aria-hidden="true" class="pointer-events-none absolute inset-0 -z-10">
      <div
        class="blob-pulse-center absolute left-1/2 top-1/4 h-[420px] w-[420px] rounded-full blur-[120px] transition-colors duration-700"
        style="
          background-color: var(--dynamic-bg-light, rgba(250, 35, 59, 0.25));
        "
      ></div>
      <div
        class="blob-pulse-right absolute right-10 bottom-12 h-64 w-64 rounded-full blur-3xl transition-colors duration-700"
        style="
          background-color: var(--dynamic-bg-light, rgba(250, 35, 59, 0.1));
        "
      ></div>
    </div>

    <div class="relative w-full max-w-2xl text-center animate-slide-up">
      <div class="mx-auto mb-6 flex justify-center">
        <img
          src="../assets/14886.gif"
          class="hero-glow-pulse h-[250px] w-auto object-contain"
          alt="Loading animation"
        />
      </div>

      <h1 class="text-balance text-5xl sm:text-6xl font-bold tracking-tight">
        Spo<span class="text-primary">tify</span>
      </h1>
      <div class="mt-3 flex items-center justify-center gap-2">
        <span class="badge-soft">v{{ version }}</span>
        <span class="badge-neutral-soft">{{ t('hero.noAccount') }}</span>
      </div>
      <p
        class="mx-auto mt-5 max-w-md text-balance text-base sm:text-lg text-base-content/70"
      >
        {{ t('hero.tagline') }}
      </p>

      <div class="mt-10">
        <SearchInput class="w-full" />
        <div
          class="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs text-base-content/60"
        >
          <span class="pill bg-white/5 border border-white/10"
            ><span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
            {{ t('hero.songs') }}</span
          >
          <span class="pill bg-white/5 border border-white/10"
            ><span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
            {{ t('hero.albums') }}</span
          >
          <span class="pill bg-white/5 border border-white/10"
            ><span class="h-1.5 w-1.5 rounded-full bg-primary"></span>
            {{ t('hero.playlists') }}</span
          >
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import SearchInput from './SearchInput.vue'
import { useI18n } from '../i18n'

const { t } = useI18n()
const version = ref(localStorage.getItem('version') || '3.3.1-release')
onMounted(() => {
  const v = localStorage.getItem('version')
  if (v) version.value = v
})
</script>

<style scoped>
.hero-glow-pulse {
  animation: heroGlow 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite alternate;
}
@keyframes heroGlow {
  0% {
    filter: drop-shadow(
      0 0 60px var(--dynamic-bg-dark, rgba(250, 35, 59, 0.6))
    );
    transform: scale(1) translateY(0);
  }
  100% {
    filter: drop-shadow(
      0 0 120px var(--dynamic-bg-dark, rgba(250, 35, 59, 0.95))
    );
    transform: scale(1.03) translateY(-4px);
  }
}

.blob-pulse-center {
  animation: blobPulseCenter 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite
    alternate;
}
@keyframes blobPulseCenter {
  0% {
    transform: translateX(-50%) scale(1);
    opacity: 1;
  }
  100% {
    transform: translateX(-50%) scale(1.1);
    opacity: 0.95;
  }
}

.blob-pulse-right {
  animation: blobPulseRight 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite alternate;
}
@keyframes blobPulseRight {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(1.15);
    opacity: 0.9;
  }
}
</style>
