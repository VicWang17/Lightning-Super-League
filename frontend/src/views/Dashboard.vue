<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <span class="title-icon">🏠</span>
        主页概览
      </h1>
      <p class="page-subtitle">欢迎回到闪电超级联赛，查看你的球队概况</p>
    </div>

    <!-- 主要统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">🏆</div>
        <div class="stat-content">
          <h3 class="stat-title">联赛排名</h3>
          <div class="stat-value">第 8 名</div>
          <div class="stat-change positive">↑ 2</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">💰</div>
        <div class="stat-content">
          <h3 class="stat-title">球队资金</h3>
          <div class="stat-value">5.2M</div>
          <div class="stat-change positive">+0.3M</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">👥</div>
        <div class="stat-content">
          <h3 class="stat-title">球员数量</h3>
          <div class="stat-value">25</div>
          <div class="stat-change">不变</div>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon">⚽</div>
        <div class="stat-content">
          <h3 class="stat-title">下场比赛</h3>
          <div class="stat-value">3天后</div>
          <div class="stat-desc">vs 巴塞罗那</div>
        </div>
      </div>
    </div>

    <!-- 两列布局 -->
    <div class="dashboard-content">
      <!-- 左侧内容 -->
      <div class="content-left">
        <!-- 近期比赛 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h2 class="card-title">
              <span class="title-icon">📅</span>
              近期比赛
            </h2>
            <router-link to="/matches" class="card-action">查看全部</router-link>
          </div>
          <div class="card-content">
            <div class="match-list">
              <div class="match-item">
                <div class="match-date">12月25日</div>
                <div class="match-info">
                  <span class="team-home">我的球队</span>
                  <span class="match-score">2 - 1</span>
                  <span class="team-away">皇家马德里</span>
                </div>
                <div class="match-result win">胜</div>
              </div>
              
              <div class="match-item">
                <div class="match-date">12月22日</div>
                <div class="match-info">
                  <span class="team-home">利物浦</span>
                  <span class="match-score">1 - 1</span>
                  <span class="team-away">我的球队</span>
                </div>
                <div class="match-result draw">平</div>
              </div>

              <div class="match-item upcoming">
                <div class="match-date">12月28日</div>
                <div class="match-info">
                  <span class="team-home">我的球队</span>
                  <span class="match-score">vs</span>
                  <span class="team-away">巴塞罗那</span>
                </div>
                <div class="match-result">即将开始</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 球队动态 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h2 class="card-title">
              <span class="title-icon">📰</span>
              球队动态
            </h2>
          </div>
          <div class="card-content">
            <Timeline :items="timelineItems" />
          </div>
        </div>
      </div>

      <!-- 右侧内容 -->
      <div class="content-right">
        <!-- 球队状态 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h2 class="card-title">
              <span class="title-icon">📊</span>
              球队状态
            </h2>
          </div>
          <div class="card-content">
            <div class="status-list">
              <div class="status-item">
                <span class="status-label">球员士气</span>
                <div class="status-bar">
                  <div class="status-fill" style="width: 85%"></div>
                </div>
                <span class="status-value">85%</span>
              </div>
              
              <div class="status-item">
                <span class="status-label">体能状况</span>
                <div class="status-bar">
                  <div class="status-fill" style="width: 72%"></div>
                </div>
                <span class="status-value">72%</span>
              </div>
              
              <div class="status-item">
                <span class="status-label">训练强度</span>
                <div class="status-bar">
                  <div class="status-fill" style="width: 90%"></div>
                </div>
                <span class="status-value">90%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 快速操作 -->
        <div class="dashboard-card">
          <div class="card-header">
            <h2 class="card-title">
              <span class="title-icon">⚡</span>
              快速操作
            </h2>
          </div>
          <div class="card-content">
            <div class="quick-actions">
              <router-link to="/team" class="quick-action-btn">
                <span class="action-icon">👥</span>
                <span class="action-text">管理球队</span>
              </router-link>
              
              <router-link to="/market" class="quick-action-btn">
                <span class="action-icon">💰</span>
                <span class="action-text">转会市场</span>
              </router-link>
              
              <router-link to="/youth" class="quick-action-btn">
                <span class="action-icon">🌟</span>
                <span class="action-text">青训营</span>
              </router-link>
              
              <button class="quick-action-btn" @click="startTraining">
                <span class="action-icon">🏃</span>
                <span class="action-text">开始训练</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import Timeline, { TimelineItem } from '@/components/Timeline.vue'
import { ref } from 'vue'

const timelineItems = ref<TimelineItem[]>([
  {
    type: 'success',
    content: '球员张三在训练中表现出色，能力值提升+2',
    time: '2小时前'
  },
  {
    type: 'warning',
    content: '收到来自AC米兰的转会报价，目标球员：李四',
    time: '5小时前'
  },
  {
    type: 'info',
    content: '青训营发现了一名天赋异禀的年轻球员',
    time: '1天前'
  },
  {
    type: 'error',
    content: '球员王五在训练中受伤，预计休息2周',
    time: '2天前'
  },
  {
    type: 'success',
    content: '成功签约新球员赵六，转会费€15M',
    time: '3天前'
  }
])

const startTraining = () => {
  alert('训练功能开发中...')
}
</script>

<style scoped>
.dashboard {
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.stat-icon {
  font-size: 2.5rem;
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-title {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  margin: 0 0 4px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 4px;
}

.stat-change {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.stat-change.positive {
  color: #4caf50;
}

.stat-desc {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.dashboard-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 30px;
}

.dashboard-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  margin-bottom: 20px;
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.card-action {
  color: #00f2b8;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: color 0.2s;
}

.card-action:hover {
  color: #ffffff;
}

.card-content {
  padding: 20px 24px;
}

.match-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.match-item {
  display: grid;
  grid-template-columns: 80px 1fr 80px;
  gap: 16px;
  align-items: center;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  transition: background 0.2s;
}

.match-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.match-item.upcoming {
  border: 1px solid rgba(255, 193, 7, 0.3);
}

.match-date {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  text-align: center;
}

.match-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 500;
}

.team-home, .team-away {
  color: #ffffff;
  flex: 1;
}

.team-away {
  text-align: right;
}

.match-score {
  color: #00f2b8;
  font-weight: 700;
  padding: 0 12px;
}

.match-result {
  text-align: center;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 8px;
}

.match-result.win {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.match-result.draw {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-label {
  width: 80px;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
}

.status-bar {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
}

.status-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f2b8, #00d084);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.status-value {
  width: 40px;
  font-size: 0.8rem;
  color: #00f2b8;
  font-weight: 600;
  text-align: right;
}

.quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.quick-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.8);
  transition: all 0.2s;
  cursor: pointer;
}

.quick-action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transform: translateY(-2px);
}

.action-icon {
  font-size: 1.5rem;
}

.action-text {
  font-size: 0.8rem;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .dashboard-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .quick-actions {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .match-item {
    grid-template-columns: 1fr;
    gap: 8px;
    text-align: center;
  }
  
  .page-title {
    font-size: 1.8rem;
  }
}
</style> 