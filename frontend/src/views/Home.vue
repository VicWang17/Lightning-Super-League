<template>
  <div class="home-container">
    <!-- 动态背景 -->
    <div class="hero-background">
      <div class="background-overlay"></div>
      <!-- 使用更现代的足球场夜景图片 -->
      <img 
        v-if="imageLoaded"
        src="https://images.unsplash.com/photo-1599158150601-1417ebbaafdd?q=80&w=2672&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
        alt="Football Stadium" 
        class="hero-image"
        crossorigin="anonymous"
        @error="handleImageError"
      />
      <!-- 备用背景 -->
      <div class="fallback-bg" v-else></div>
      <!-- 动态光效 -->
      <div class="light-effects">
        <div class="light-beam light-beam-1"></div>
        <div class="light-beam light-beam-2"></div>
        <div class="light-beam light-beam-3"></div>
      </div>
      <!-- 添加粒子效果背景 -->
      <div class="particles">
        <div class="particle" v-for="i in 50" :key="i"></div>
      </div>
    </div>

    <!-- 主要内容 -->
    <div class="hero-content">
      <!-- Logo区域 -->
      <div class="logo-section">
        <div class="logo-wrapper">
          <div class="logo-icon">⚡</div>
          <h1 class="game-title">闪电超级联赛</h1>
        </div>
        <p class="game-subtitle">Lightning Super League</p>
        <div class="tagline">未来足球经理体验，就在今朝</div>
        <div class="tagline">Bilibili闪电杰尼倾情开发</div>
      </div>

      <!-- 主按钮区域 - 提前到更显眼的位置 -->
      <div class="main-action-section">
        <AnimatedButton 
          text="开始你的传奇之旅"
          icon="🚀"
          @click="enterGame"
        />
        
        <div class="quick-actions">
          <n-button text class="quick-btn" @click="$router.push('/login')">
            <span class="quick-icon">👤</span>
            登录游戏
          </n-button>
          <n-button text class="quick-btn register-btn" @click="$router.push('/login')">
            <span class="quick-icon">✨</span>
            新手注册
          </n-button>
        </div>
      </div>

      <!-- 特性展示 -->
      <div class="features-section">
        <h2 class="features-title">体验世界级足球管理</h2>
        <div class="features-grid">
          <FeatureCard 
            v-for="(feature, index) in features" 
            :key="index"
            :icon="feature.icon"
            :title="feature.title"
            :description="feature.desc"
          />
        </div>
      </div>

      <!-- 数据展示 -->
      <div class="stats-section">
        <div class="stats-grid">
          <StatCard 
            v-for="(stat, index) in stats" 
            :key="index"
            :number="stat.number"
            :label="stat.label"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'
import { useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'
import FeatureCard from '@/components/FeatureCard.vue'
import StatCard from '@/components/StatCard.vue'
import AnimatedButton from '@/components/AnimatedButton.vue'

const router = useRouter()

const features = ref([
  {
    icon: '🎯',
    title: '战术大师',
    desc: '深度战术系统，每一个决策都影响比赛结果'
  },
  {
    icon: '💎',
    title: '球星养成',
    desc: '从青训挖掘天才，培养下一个梅西'
  },
  {
    icon: '🔥',
    title: '实时对战',
    desc: '与全球玩家同台竞技，争夺联赛冠军'
  },
  {
    icon: '🌟',
    title: '巨星转会',
    desc: '智能转会系统，打造你的梦幻阵容'
  }
])

const stats = ref([
  { number: '0+', label: '活跃经理' },
  { number: '1K+', label: '球员数据' },
  { number: '24/7', label: '现实同步' },
  { number: '0+', label: '支持联赛' }
])

const enterGame = () => {
  const token = localStorage.getItem('token')
  if (token) {
    router.push('/dashboard')
  } else {
    router.push('/login')
  }
}

const imageLoaded = ref(false)

const handleImageError = () => {
  console.log('图片加载失败，使用备用背景')
  imageLoaded.value = false
}

// 在mounted时尝试预加载图片
onMounted(() => {
  const particles = document.querySelectorAll('.particle')
  particles.forEach((particle: Element, _index: number) => {
    const element = particle as HTMLElement
    element.style.left = Math.random() * 100 + '%'
    element.style.top = Math.random() * 100 + '%'
    element.style.animationDelay = Math.random() * 6 + 's'
    element.style.animationDuration = (4 + Math.random() * 4) + 's'
  })

  // 预加载图片
  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    console.log('图片加载成功')
    imageLoaded.value = true
  }
  img.onerror = () => {
    console.log('图片预加载失败')
    imageLoaded.value = false
  }
  img.src = 'https://images.unsplash.com/photo-1599158150601-1417ebbaafdd?q=80&w=2672&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'
})
</script>

<style scoped>
.home-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background: linear-gradient(135deg, #00b051 0%, #00d084 50%, #00f2b8 100%);
}

.hero-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: brightness(0.4) contrast(1.3) saturate(1.5) hue-rotate(10deg);
  transform: scale(1.02);
}

.background-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    135deg,
    rgba(0, 176, 81, 0.3) 0%,
    rgba(0, 242, 184, 0.25) 25%,
    rgba(255, 107, 53, 0.15) 50%,
    rgba(255, 215, 0, 0.2) 75%,
    rgba(0, 188, 212, 0.1) 100%
  );
  z-index: 2;
}

.light-effects {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 3;
  pointer-events: none;
}

.light-beam {
  position: absolute;
  background: linear-gradient(45deg, rgba(255, 255, 255, 0.05), rgba(0, 242, 184, 0.1), rgba(255, 255, 255, 0.05));
  filter: blur(1px);
  animation: light-sweep 12s ease-in-out infinite;
}

.light-beam-1 {
  top: 10%;
  left: -20%;
  width: 40%;
  height: 2px;
  transform: rotate(25deg);
  animation-delay: 0s;
}

.light-beam-2 {
  top: 60%;
  right: -20%;
  width: 30%;
  height: 1px;
  transform: rotate(-15deg);
  animation-delay: 4s;
}

.light-beam-3 {
  bottom: 20%;
  left: 10%;
  width: 50%;
  height: 1px;
  transform: rotate(5deg);
  animation-delay: 8s;
}

@keyframes light-sweep {
  0%, 100% {
    opacity: 0;
    transform: translateX(-100px) scale(0.8);
  }
  50% {
    opacity: 1;
    transform: translateX(100px) scale(1.2);
  }
}

.particles {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 4;
}

.particle {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgba(255, 215, 0, 0.6);
  border-radius: 50%;
  animation: float 6s ease-in-out infinite;
}

.particle:nth-child(odd) {
  background: rgba(0, 242, 184, 0.5);
  animation-delay: -2s;
}

.particle:nth-child(3n) {
  background: rgba(255, 255, 255, 0.4);
  animation-delay: -4s;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px) translateX(0px);
    opacity: 0;
  }
  10% {
    opacity: 1;
  }
  90% {
    opacity: 1;
  }
  50% {
    transform: translateY(-100px) translateX(50px);
  }
}

.hero-content {
  position: relative;
  z-index: 10;
  text-align: center;
  max-width: 1000px;
  padding: 20px;
}

.logo-section {
  margin-bottom: 60px;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 15px;
}

.logo-icon {
  font-size: 5rem;
  background: linear-gradient(45deg, #ffd700, #ffed4e, #ffd700);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  animation: pulse-glow 2s ease-in-out infinite;
  filter: drop-shadow(0 0 10px rgba(255, 215, 0, 0.5));
}

@keyframes pulse-glow {
  0%, 100% { 
    transform: scale(1);
    filter: drop-shadow(0 0 10px rgba(255, 215, 0, 0.5));
  }
  50% { 
    transform: scale(1.1);
    filter: drop-shadow(0 0 20px rgba(255, 215, 0, 0.8));
  }
}

.game-title {
  font-size: 4.5rem;
  font-weight: 900;
  background: linear-gradient(135deg, #ffffff, #f0f0f0, #ffffff);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
  letter-spacing: -2px;
}

.game-subtitle {
  font-size: 1.3rem;
  color: rgba(255, 255, 255, 0.9);
  font-weight: 400;
  letter-spacing: 3px;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.tagline {
  font-size: 1.1rem;
  color: rgba(255, 215, 0, 0.95);
  font-weight: 500;
  font-style: italic;
}

.main-action-section {
  margin-bottom: 80px;
}

.quick-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
  flex-wrap: wrap;
}

.quick-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.9) !important;
  font-size: 1.1rem !important;
  font-weight: 600 !important;
  padding: 12px 24px !important;
  border-radius: 25px !important;
  background: rgba(255, 255, 255, 0.1) !important;
  backdrop-filter: blur(10px) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
  transition: all 0.3s ease !important;
}

.quick-btn:hover {
  background: rgba(255, 255, 255, 0.2) !important;
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2) !important;
}

.register-btn:hover {
  background: rgba(255, 215, 0, 0.2) !important;
  color: #ffd700 !important;
}

.quick-icon {
  font-size: 1.1em;
}

.features-section {
  margin-bottom: 60px;
}

.features-title {
  font-size: 2.2rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 40px;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.5);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 25px;
  max-width: 900px;
  margin: 0 auto;
}

.stats-section {
  margin-top: 40px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 30px;
  max-width: 700px;
  margin: 0 auto;
}

.fallback-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(circle at 25% 75%, rgba(255, 215, 0, 0.3) 0%, transparent 50%),
    radial-gradient(circle at 75% 25%, rgba(0, 242, 184, 0.2) 0%, transparent 50%),
    linear-gradient(135deg, 
      #0f4c3a 0%, 
      #1a5d4a 25%, 
      #2d7f5f 50%, 
      #3a9d6f 75%, 
      #4bb97f 100%
    );
  z-index: 1;
  animation: subtle-shift 20s ease-in-out infinite;
}

@keyframes subtle-shift {
  0%, 100% {
    filter: hue-rotate(0deg) brightness(1);
  }
  50% {
    filter: hue-rotate(10deg) brightness(1.1);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .logo-icon {
    font-size: 3.5rem;
  }
  
  .game-title {
    font-size: 3rem;
  }
  
  .logo-wrapper {
    flex-direction: column;
    gap: 10px;
  }
  
  .features-grid {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  
  .quick-actions {
    flex-direction: column;
    gap: 15px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
}

@media (max-width: 480px) {
  .hero-content {
    padding: 15px;
  }
  
  .logo-icon {
    font-size: 2.5rem;
  }
  
  .game-title {
    font-size: 2.2rem;
  }
  
  .features-title {
    font-size: 1.8rem;
  }
}
</style> 