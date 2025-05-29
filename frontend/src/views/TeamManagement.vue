<template>
  <div class="team-management">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <span class="title-icon">👥</span>
        球队管理
      </h1>
      <p class="page-subtitle">管理你的球员阵容，优化战术配置</p>
    </div>

    <!-- 球队概览 -->
    <div class="team-overview">
      <div class="overview-card">
        <h2 class="overview-title">球队概览</h2>
        <div class="overview-stats">
          <div class="stat-item">
            <span class="stat-label">球队价值</span>
            <span class="stat-value">€125M</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">平均年龄</span>
            <span class="stat-value">26.8岁</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">平均能力</span>
            <span class="stat-value">78.5</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">球队化学</span>
            <span class="stat-value">85%</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 战术设置和球员列表 -->
    <div class="team-content">
      <!-- 战术配置 -->
      <div class="tactics-section">
        <div class="section-card">
          <div class="card-header">
            <h2 class="card-title">
              <span class="title-icon">🎯</span>
              战术配置
            </h2>
          </div>
          <div class="card-content">
            <div class="formation-selector">
              <label class="formation-label">阵型选择</label>
              <select v-model="selectedFormation" class="formation-select">
                <option value="442">4-4-2</option>
                <option value="433">4-3-3</option>
                <option value="352">3-5-2</option>
                <option value="4231">4-2-3-1</option>
              </select>
            </div>
            
            <div class="tactics-options">
              <div class="tactic-item">
                <label>进攻风格</label>
                <select class="tactic-select">
                  <option>快速反击</option>
                  <option>控球进攻</option>
                  <option>边路突破</option>
                </select>
              </div>
              
              <div class="tactic-item">
                <label>防守策略</label>
                <select class="tactic-select">
                  <option>高位逼抢</option>
                  <option>中场拦截</option>
                  <option>稳固防守</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 球员列表 -->
      <div class="players-section">
        <div class="section-card">
          <div class="card-header">
            <h2 class="card-title">
              <span class="title-icon">⚽</span>
              球员阵容
            </h2>
            <div class="header-actions">
              <button class="action-btn" @click="filterPosition = 'all'" :class="{ active: filterPosition === 'all' }">
                全部
              </button>
              <button class="action-btn" @click="filterPosition = 'goalkeeper'" :class="{ active: filterPosition === 'goalkeeper' }">
                门将
              </button>
              <button class="action-btn" @click="filterPosition = 'defender'" :class="{ active: filterPosition === 'defender' }">
                后卫
              </button>
              <button class="action-btn" @click="filterPosition = 'midfielder'" :class="{ active: filterPosition === 'midfielder' }">
                中场
              </button>
              <button class="action-btn" @click="filterPosition = 'forward'" :class="{ active: filterPosition === 'forward' }">
                前锋
              </button>
            </div>
          </div>
          <div class="card-content">
            <div class="players-grid">
              <div v-for="player in filteredPlayers" :key="player.id" class="player-card">
                <div class="player-info">
                  <div class="player-avatar">
                    <span>{{ player.avatar }}</span>
                  </div>
                  <div class="player-details">
                    <h3 class="player-name">{{ player.name }}</h3>
                    <p class="player-position">{{ player.position }} | {{ player.age }}岁</p>
                  </div>
                </div>
                
                <div class="player-stats">
                  <div class="stat-row">
                    <span class="stat-label">能力</span>
                    <div class="stat-bar">
                      <div class="stat-fill" :style="{ width: player.rating + '%' }"></div>
                    </div>
                    <span class="stat-number">{{ player.rating }}</span>
                  </div>
                  
                  <div class="stat-row">
                    <span class="stat-label">状态</span>
                    <div class="stat-bar">
                      <div class="stat-fill" :style="{ width: player.condition + '%' }"></div>
                    </div>
                    <span class="stat-number">{{ player.condition }}%</span>
                  </div>
                </div>
                
                <div class="player-actions">
                  <button class="player-btn primary">查看详情</button>
                  <button class="player-btn">替换</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Player {
  id: number
  name: string
  position: string
  age: number
  rating: number
  condition: number
  avatar: string
  positionType: string
}

const selectedFormation = ref('442')
const filterPosition = ref('all')

const players = ref<Player[]>([
  { id: 1, name: '张伟', position: '门将', age: 28, rating: 82, condition: 95, avatar: '🥅', positionType: 'goalkeeper' },
  { id: 2, name: '李强', position: '中后卫', age: 26, rating: 85, condition: 88, avatar: '🛡️', positionType: 'defender' },
  { id: 3, name: '王涛', position: '右后卫', age: 24, rating: 78, condition: 92, avatar: '⚡', positionType: 'defender' },
  { id: 4, name: '刘明', position: '左后卫', age: 25, rating: 80, condition: 90, avatar: '🏃', positionType: 'defender' },
  { id: 5, name: '陈杰', position: '后腰', age: 27, rating: 83, condition: 87, avatar: '🔧', positionType: 'midfielder' },
  { id: 6, name: '赵磊', position: '中场', age: 23, rating: 86, condition: 94, avatar: '⚽', positionType: 'midfielder' },
  { id: 7, name: '孙亮', position: '前腰', age: 25, rating: 88, condition: 91, avatar: '🎨', positionType: 'midfielder' },
  { id: 8, name: '周鹏', position: '右翼', age: 22, rating: 84, condition: 96, avatar: '🏃‍♂️', positionType: 'forward' },
  { id: 9, name: '吴凯', position: '中锋', age: 29, rating: 90, condition: 85, avatar: '🎯', positionType: 'forward' },
  { id: 10, name: '郑浩', position: '左翼', age: 24, rating: 82, condition: 89, avatar: '💨', positionType: 'forward' }
])

const filteredPlayers = computed(() => {
  if (filterPosition.value === 'all') {
    return players.value
  }
  return players.value.filter(player => player.positionType === filterPosition.value)
})
</script>

<style scoped>
.team-management {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 2.2rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 8px;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.title-icon {
  font-size: 1.8rem;
}

.page-subtitle {
  color: rgba(255, 255, 255, 0.8);
  font-size: 1.1rem;
  margin: 0;
}

.team-overview {
  margin-bottom: 30px;
}

.overview-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 24px;
}

.overview-title {
  font-size: 1.3rem;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 20px;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
}

.stat-label {
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
}

.stat-value {
  color: #00f2b8;
  font-weight: 700;
  font-size: 1.1rem;
}

.team-content {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 30px;
}

.section-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.2rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.action-btn.active {
  background: #00f2b8;
  color: #000;
  border-color: #00f2b8;
}

.card-content {
  padding: 20px 24px;
}

.formation-selector {
  margin-bottom: 20px;
}

.formation-label {
  display: block;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  margin-bottom: 8px;
}

.formation-select,
.tactic-select {
  width: 100%;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #ffffff;
  font-size: 0.9rem;
  outline: none;
}

.formation-select:focus,
.tactic-select:focus {
  border-color: #00f2b8;
  background: rgba(255, 255, 255, 0.15);
}

.tactics-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tactic-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tactic-item label {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
}

.players-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.player-card {
  display: grid;
  grid-template-columns: 2fr 3fr auto;
  gap: 20px;
  align-items: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  transition: all 0.2s;
}

.player-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.player-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.player-avatar {
  width: 50px;
  height: 50px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.player-name {
  font-size: 1rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px 0;
}

.player-position {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
}

.player-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-row {
  display: grid;
  grid-template-columns: 50px 1fr 40px;
  gap: 8px;
  align-items: center;
}

.stat-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}

.stat-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f2b8, #00d084);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.stat-number {
  font-size: 0.7rem;
  color: #00f2b8;
  font-weight: 600;
  text-align: right;
}

.player-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.player-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 0.7rem;
  cursor: pointer;
  transition: all 0.2s;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.player-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.player-btn.primary {
  background: #00f2b8;
  color: #000;
  border-color: #00f2b8;
}

.player-btn.primary:hover {
  background: #00d084;
  border-color: #00d084;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .team-content {
    grid-template-columns: 1fr;
  }
  
  .overview-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-stats {
    grid-template-columns: 1fr;
  }
  
  .player-card {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .header-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.8rem;
  }
  
  .player-card {
    padding: 12px;
  }
}
</style> 