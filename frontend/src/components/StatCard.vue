<template>
  <div class="stat-card" @mouseenter="isHovered = true" @mouseleave="isHovered = false">
    <div class="stat-number" :class="{ pulse: isHovered }">{{ number }}</div>
    <div class="stat-label">{{ label }}</div>
    <div class="stat-glow"></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  number: string
  label: string
}

defineProps<Props>()

const isHovered = ref(false)
</script>

<style scoped>
.stat-card {
  text-align: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.stat-card:hover {
  transform: translateY(-3px);
  background: rgba(255, 255, 255, 0.12);
  box-shadow: 0 8px 25px rgba(0, 242, 184, 0.2);
}

.stat-number {
  font-size: 2.2rem;
  font-weight: 900;
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 5px;
  transition: all 0.3s ease;
}

.stat-number.pulse {
  animation: numberPulse 0.6s ease-in-out;
}

@keyframes numberPulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

.stat-label {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-glow {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100px;
  height: 100px;
  background: radial-gradient(circle, rgba(255, 215, 0, 0.2) 0%, transparent 70%);
  transform: translate(-50%, -50%) scale(0);
  transition: transform 0.3s ease;
  border-radius: 50%;
}

.stat-card:hover .stat-glow {
  transform: translate(-50%, -50%) scale(1);
}
</style> 