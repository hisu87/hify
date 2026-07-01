<template>
  <div
    class="ambient-mesh-root fixed inset-0 overflow-hidden pointer-events-none z-[-10]"
  >
    <div
      class="low-res-viewport"
      :class="{ 'is-paused': !player.isPlaying.value }"
    >
      <div class="blob blob-main"></div>
      <div class="blob blob-accent"></div>
      <div class="blob blob-base"></div>
    </div>

    <div class="grain-shield"></div>
  </div>
</template>

<script setup>
import { usePlayer } from '../model/player'

const player = usePlayer()
</script>

<style scoped>
.ambient-mesh-root {
  background-color: #0a0a0c; /* Nền tối tối thượng */
}

.low-res-viewport {
  width: 25vw;
  height: 25vh;
  transform-origin: top left;
  transform: scale(4);
  filter: blur(32px); /* Tương đương blur 128px sau khi scale */
  will-change: filter, transform;
}

.blob {
  position: absolute;
  border-radius: 50%;
  will-change: transform;
}

/* BLOB 1: MÀU CHÍNH (To nhất, quỹ đạo elip dẹt) */
.blob-main {
  top: -10%;
  left: -10%;
  width: 70%;
  height: 70%;
  background: var(--dynamic-primary, #4a1d96);
  opacity: 0.65;
  animation: orbit-prime-1 17s infinite alternate
    cubic-bezier(0.45, 0.05, 0.55, 0.95);
}

/* BLOB 2: MÀU ACCENT (Vừa, quỹ đạo chéo góc ngược) */
.blob-accent {
  bottom: -15%;
  right: -10%;
  width: 60%;
  height: 60%;
  background: var(--dynamic-accent, #9333ea);
  opacity: 0.55;
  animation: orbit-prime-2 23s infinite alternate cubic-bezier(0.37, 0, 0.63, 1);
}

/* BLOB 3: MÀU NỀN TỐI (Nằm giữa giữ trọng tâm, nhịp thở chậm) */
.blob-base {
  top: 25%;
  left: 20%;
  width: 55%;
  height: 55%;
  background: var(--dynamic-bg-dark, #1e1b4b);
  opacity: 0.8;
  animation: pulse-prime-3 31s infinite alternate ease-in-out;
}

@keyframes orbit-prime-1 {
  0% {
    transform: translate3d(0, 0, 0) scale(1) rotate(0deg);
  }
  50% {
    transform: translate3d(45%, 25%, 0) scale(1.35, 0.85) rotate(140deg);
  }
  100% {
    transform: translate3d(15%, 60%, 0) scale(0.9, 1.2) rotate(290deg);
  }
}

@keyframes orbit-prime-2 {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  100% {
    transform: translate3d(-55%, -45%, 0) scale(1.4) rotate(-200deg);
  }
}

@keyframes pulse-prime-3 {
  0% {
    transform: translate3d(0, 0, 0) scale(0.85);
  }
  100% {
    transform: translate3d(-15%, 20%, 0) scale(1.35);
  }
}

/* Lớp hạt Noise SVG inline siêu nhẹ giúp xóa hoàn toàn vệt bậc thang màu */
.grain-shield {
  position: absolute;
  inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.04'/%3E%3C/svg%3E");
}

/* Khi Pause nhạc, quỹ đạo không dừng lại, mà giảm tốc độ xuống 10 lần (Slow-motion trôi dạt) */
.low-res-viewport.is-paused .blob {
  transition: animation-duration 2s;
  animation-play-state: running; /* Vẫn chạy */
  filter: saturate(0.7); /* Giảm nhẹ độ tươi của nền khi nhạc dừng */
}

/* Trick: Ép chu kỳ giãn ra thành 180s */
.low-res-viewport.is-paused .blob-main {
  animation-duration: 170s;
}
.low-res-viewport.is-paused .blob-accent {
  animation-duration: 230s;
}
</style>
