<template>
  <div class="feature-card" :class="{ hover: isHovered }" @mouseenter="isHovered = true" @mouseleave="isHovered = false">
    <div class="feature-icon-wrapper">
      <span class="feature-icon">{{ icon }}</span>
    </div>
    <h3 class="feature-title">{{ title }}</h3>
    <p class="feature-desc">{{ description }}</p>
    <div class="feature-shine"></div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  icon: string
  title: string
  description: string
}

defineProps<Props>()

const isHovered = ref(false)
</script>

<style scoped>
.feature-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  padding: 30px 20px;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #ff6b35, #ffd700, #00f2b8);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.feature-card:hover::before {
  opacity: 1;
}

.feature-card:hover,
.feature-card.hover {
  transform: translateY(-10px) scale(1.02);
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
}

.feature-icon-wrapper {
  width: 70px;
  height: 70px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(0, 242, 184, 0.2));
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon-wrapper,
.feature-card.hover .feature-icon-wrapper {
  transform: scale(1.1);
  box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3);
}

.feature-icon {
  font-size: 2rem;
  transition: all 0.3s ease;
}

.feature-card:hover .feature-icon,
.feature-card.hover .feature-icon {
  transform: rotate(10deg);
}

.feature-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 12px;
  transition: color 0.3s ease;
}

.feature-card:hover .feature-title,
.feature-card.hover .feature-title {
  color: #ffd700;
}

.feature-desc {
  font-size: 0.95rem;
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
}

.feature-shine {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.1), transparent);
  transform: rotate(45deg);
  transition: all 0.6s ease;
  opacity: 0;
}

.feature-card:hover .feature-shine,
.feature-card.hover .feature-shine {
  opacity: 1;
  transform: rotate(45deg) translate(50%, 50%);
}
</style> 