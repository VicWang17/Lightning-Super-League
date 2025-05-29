<template>
  <div class="home-container">
    <!-- 背景视频/图片 -->
    <div class="hero-background">
      <div class="background-overlay"></div>
      <img 
        src="https://images.unsplash.com/photo-1574629810360-7efbbe195018?q=80&w=2093&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" 
        alt="Football Stadium" 
        class="hero-image"
      />
    </div>

    <!-- 主要内容 -->
    <div class="hero-content">
      <div class="logo-section">
        <h1 class="game-title">
          <span class="lightning">⚡</span>
          闪电超级联赛
        </h1>
        <p class="game-subtitle">Lightning Super League</p>
      </div>

      <div class="intro-section">
        <h2 class="intro-title">体验执掌豪门的乐趣</h2>
        <p class="intro-description">
          打造一款高度拟真、数据驱动的在线足球经理游戏。<br>
          管理球队、参与比赛、进行球员交易，成为真正的足球战术大师。
        </p>
        
        <div class="features">
          <div class="feature">
            <span class="feature-icon">⚽</span>
            <span class="feature-text">真实比赛模拟</span>
          </div>
          <div class="feature">
            <span class="feature-icon">👥</span>
            <span class="feature-text">球员交易系统</span>
          </div>
          <div class="feature">
            <span class="feature-icon">🏆</span>
            <span class="feature-text">策略竞技对抗</span>
          </div>
          <div class="feature">
            <span class="feature-icon">🎯</span>
            <span class="feature-text">青训培养系统</span>
          </div>
        </div>
      </div>

      <div class="action-section">
        <n-button 
          type="primary" 
          size="large" 
          class="enter-game-btn"
          @click="enterGame"
        >
          <template #icon>
            <span style="font-size: 18px;">⚡</span>
          </template>
          开始游戏
        </n-button>
        
        <div class="quick-actions">
          <n-button text class="quick-btn" @click="$router.push('/login')">
            登录游戏
          </n-button>
          <span class="divider">|</span>
          <n-button text class="quick-btn" @click="$router.push('/login')">
            新手注册
          </n-button>
        </div>
      </div>
    </div>

    <!-- 底部装饰 -->
    <div class="bottom-decoration">
      <div class="stats-preview">
        <div class="stat-item">
          <span class="stat-number">1000+</span>
          <span class="stat-label">活跃球队</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">50000+</span>
          <span class="stat-label">球员数据</span>
        </div>
        <div class="stat-item">
          <span class="stat-number">24/7</span>
          <span class="stat-label">实时对战</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NButton } from 'naive-ui'
import { useRouter } from 'vue-router'

const router = useRouter()

const enterGame = () => {
  const token = localStorage.getItem('token')
  if (token) {
    router.push('/dashboard')
  } else {
    router.push('/login')
  }
}
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
}

.hero-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: -1;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: brightness(0.4) contrast(1.2);
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
    rgba(255, 102, 0, 0.2) 50%,
    rgba(0, 0, 0, 0.7) 100%
  );
  z-index: 1;
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  max-width: 800px;
  padding: 40px 20px;
}

.logo-section {
  margin-bottom: 40px;
}

.game-title {
  font-size: 4rem;
  font-weight: 900;
  background: linear-gradient(135deg, #00b051, #ffd700, #ff6600);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow: 0 0 30px rgba(0, 176, 81, 0.5);
  margin-bottom: 10px;
  line-height: 1.1;
}

.lightning {
  display: inline-block;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.1); }
}

.game-subtitle {
  font-size: 1.2rem;
  color: var(--text-secondary);
  font-weight: 300;
  letter-spacing: 2px;
  text-transform: uppercase;
}

.intro-section {
  margin-bottom: 50px;
}

.intro-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 20px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
}

.intro-description {
  font-size: 1.2rem;
  color: var(--text-secondary);
  line-height: 1.8;
  margin-bottom: 40px;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 30px;
}

.feature {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
}

.feature:hover {
  transform: translateY(-5px);
  background: rgba(255, 255, 255, 0.15);
  box-shadow: 0 10px 25px rgba(0, 176, 81, 0.3);
}

.feature-icon {
  font-size: 24px;
}

.feature-text {
  font-weight: 600;
  color: #ffffff;
}

.action-section {
  margin-bottom: 40px;
}

.enter-game-btn {
  font-size: 1.2rem !important;
  padding: 15px 40px !important;
  height: auto !important;
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color)) !important;
  border: none !important;
  border-radius: 25px !important;
  font-weight: 700 !important;
  box-shadow: 0 10px 30px rgba(0, 176, 81, 0.4) !important;
  transition: all 0.3s ease !important;
  margin-bottom: 30px;
}

.enter-game-btn:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 15px 40px rgba(0, 176, 81, 0.6) !important;
}

.quick-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.quick-btn {
  color: var(--text-secondary) !important;
  font-size: 1rem !important;
  transition: color 0.3s ease !important;
}

.quick-btn:hover {
  color: var(--primary-color) !important;
}

.divider {
  color: var(--text-muted);
  font-size: 1.2rem;
}

.bottom-decoration {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
}

.stats-preview {
  display: flex;
  gap: 60px;
  align-items: center;
}

.stat-item {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 2rem;
  font-weight: 900;
  color: var(--accent-color);
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.8);
}

.stat-label {
  display: block;
  font-size: 0.9rem;
  color: var(--text-muted);
  margin-top: 5px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .game-title {
    font-size: 2.5rem;
  }
  
  .intro-title {
    font-size: 1.8rem;
  }
  
  .intro-description {
    font-size: 1rem;
  }
  
  .features {
    grid-template-columns: 1fr;
  }
  
  .stats-preview {
    flex-direction: column;
    gap: 20px;
  }
  
  .quick-actions {
    flex-direction: column;
  }
  
  .divider {
    display: none;
  }
}
</style> 