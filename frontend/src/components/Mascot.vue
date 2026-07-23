<script setup>
import { ref, computed, watch, onUnmounted } from "vue";
import idleImg from "../assets/mascot-idle.png";
import thinkingImg from "../assets/mascot-thinking.png";
import talkClosedImg from "../assets/mascot-talking-closed.png";
import talkOpenImg from "../assets/mascot-talking-open.png";

const props = defineProps({
  // "idle" | "thinking" | "talking"
  state: { type: String, default: "idle" },
  size: { type: Number, default: 130 },
});

// While talking, the mouth alternates between two frames.
const mouthOpen = ref(false);
let mouthTimer = null;

function startTalking() {
  stopTalking();
  mouthTimer = setInterval(() => {
    mouthOpen.value = !mouthOpen.value;
  }, 220);
}

function stopTalking() {
  if (mouthTimer) clearInterval(mouthTimer);
  mouthTimer = null;
  mouthOpen.value = false;
}

watch(
  () => props.state,
  (s) => (s === "talking" ? startTalking() : stopTalking()),
  { immediate: true }
);

onUnmounted(stopTalking);

const currentImage = computed(() => {
  if (props.state === "thinking") return thinkingImg;
  if (props.state === "talking") return mouthOpen.value ? talkOpenImg : talkClosedImg;
  return idleImg;
});
</script>

<template>
  <div class="mascot" :class="state" :style="{ width: size + 'px' }">
    <img :src="currentImage" alt="TARCian assistant" />
    <!-- Thinking dots -->
    <div v-if="state === 'thinking'" class="dots">
      <span></span><span></span><span></span>
    </div>
  </div>
</template>

<style scoped>
.mascot {
  position: relative;
  user-select: none;
  pointer-events: none;
}

.mascot img {
  width: 100%;
  height: auto;
  display: block;
  /* Frames are pre-aligned, so swapping them never shifts the mascot. */
  filter: drop-shadow(0 6px 14px rgba(17, 24, 39, 0.16));
}

/* Idle: slow, subtle breathing float */
.mascot.idle img {
  animation: float 3.4s ease-in-out infinite;
}

/* Thinking: smaller, quicker bob */
.mascot.thinking img {
  animation: think 1.6s ease-in-out infinite;
}

/* Talking: tiny bounce synced with the mouth frames */
.mascot.talking img {
  animation: talk 0.44s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50%      { transform: translateY(-8px) rotate(-1.5deg); }
}

@keyframes think {
  0%, 100% { transform: translateY(0) rotate(-2deg); }
  50%      { transform: translateY(-4px) rotate(2deg); }
}

@keyframes talk {
  0%, 100% { transform: translateY(0) scale(1); }
  50%      { transform: translateY(-3px) scale(1.02); }
}

/* Thinking dots bubble */
.dots {
  position: absolute;
  top: 4%;
  right: -6px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 6px 10px;
  display: flex;
  gap: 4px;
  box-shadow: 0 4px 12px rgba(17, 24, 39, 0.1);
}

.dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #9ca3af;
  animation: blink 1.2s infinite;
}

.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes blink {
  0%, 80%, 100% { opacity: 0.3; transform: translateY(0); }
  40%           { opacity: 1;   transform: translateY(-3px); }
}

/* Respect users who prefer reduced motion */
@media (prefers-reduced-motion: reduce) {
  .mascot img { animation: none !important; }
  .dots span { animation: none; }
}
</style>
