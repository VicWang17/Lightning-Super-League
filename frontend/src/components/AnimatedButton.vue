<template>
  <button 
    class="animated-button" 
    :class="{ 'is-loading': isLoading }"
    @click="handleClick"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div class="button-bg"></div>
    <div class="button-content">
      <span class="button-icon" v-if="icon">{{ icon }}</span>
      <span class="button-text">{{ text }}</span>
      <div class="button-ripple" v-if="isHovered"></div>
    </div>
    <div class="button-particles">
      <span v-for="i in 8" :key="i" class="particle"></span>
    </div>
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  text: string
  icon?: string
  isLoading?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  click: []
}>()

const isHovered = ref(false)

const handleClick = () => {
  emit('click')
}
</script>

<style scoped>
.animated-button {
  position: relative;
  font-size: 1.8rem;
  padding: 25px 60px;
  border: none;
  border-radius: 50px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 1px;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: transparent;
  color: white;
  margin-bottom: 30px;
  outline: none;
}

.button-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #ff6b35, #f7931e, #ffd700);
  border-radius: 50px;
  transition: all 0.3s ease;
  z-index: 1;
}

.animated-button:hover .button-bg {
  background: linear-gradient(135deg, #ff8a65, #ffb74d, #fff176);
  transform: scale(1.05);
  box-shadow: 0 20px 50px rgba(255, 107, 53, 0.6), 0 10px 25px rgba(255, 215, 0, 0.5);
}

.button-content {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  transition: all 0.3s ease;
}

.animated-button:hover .button-content {
  transform: translateY(-2px);
}

.button-icon {
  font-size: 1.2em;
  transition: transform 0.3s ease;
}

.animated-button:hover .button-icon {
  transform: rotate(20deg) scale(1.1);
}

.button-text {
  font-weight: inherit;
  transition: all 0.3s ease;
}

.button-ripple {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  animation: ripple 0.6s ease-out;
}

@keyframes ripple {
  to {
    width: 300px;
    height: 300px;
    opacity: 0;
  }
}

.button-particles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: #ffd700;
  border-radius: 50%;
  opacity: 0;
  transition: all 0.3s ease;
}

.animated-button:hover .particle {
  opacity: 1;
  animation: particleFloat 2s ease-in-out infinite;
}

.particle:nth-child(1) { top: 20%; left: 10%; animation-delay: 0s; }
.particle:nth-child(2) { top: 30%; right: 15%; animation-delay: 0.2s; }
.particle:nth-child(3) { bottom: 25%; left: 20%; animation-delay: 0.4s; }
.particle:nth-child(4) { top: 40%; left: 50%; animation-delay: 0.6s; }
.particle:nth-child(5) { bottom: 30%; right: 20%; animation-delay: 0.8s; }
.particle:nth-child(6) { top: 60%; left: 30%; animation-delay: 1s; }
.particle:nth-child(7) { top: 15%; right: 30%; animation-delay: 1.2s; }
.particle:nth-child(8) { bottom: 20%; right: 40%; animation-delay: 1.4s; }

@keyframes particleFloat {
  0%, 100% {
    transform: translateY(0px) scale(1);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-20px) scale(1.2);
    opacity: 1;
  }
}

.animated-button.is-loading {
  pointer-events: none;
}

.animated-button.is-loading .button-content {
  opacity: 0.7;
}

.animated-button.is-loading .button-bg {
  animation: loadingPulse 1.5s ease-in-out infinite;
}

@keyframes loadingPulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.02);
    opacity: 0.9;
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .animated-button {
    font-size: 1.5rem;
    padding: 20px 45px;
  }
}

@media (max-width: 480px) {
  .animated-button {
    font-size: 1.3rem;
    padding: 18px 40px;
  }
}
</style> 