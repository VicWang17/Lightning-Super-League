<template>
  <div class="matches">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <span class="title-icon">⚽</span>
        比赛赛程
      </h1>
      <p class="page-subtitle">查看upcoming和历史比赛，分析战术数据</p>
    </div>

    <!-- 比赛筛选 -->
    <div class="filter-section">
      <div class="filter-card">
        <div class="filter-tabs">
          <button 
            v-for="tab in tabs" 
            :key="tab.key"
            @click="activeTab = tab.key"
            class="filter-tab"
            :class="{ active: activeTab === tab.key }"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- 比赛列表 -->
    <div class="matches-section">
      <div class="section-card">
        <div class="card-header">
          <h2 class="card-title">
            <span class="title-icon">📅</span>
            {{ getTabTitle(activeTab) }}
          </h2>
        </div>
        <div class="card-content">
          <div class="matches-list">
            <div v-for="match in filteredMatches" :key="match.id" class="match-card">
              <div class="match-time">
                <div class="match-date">{{ match.date }}</div>
                <div class="match-hour">{{ match.time }}</div>
              </div>
              
              <div class="match-teams">
                <div class="team home">
                  <div class="team-logo">{{ match.homeTeam.logo }}</div>
                  <div class="team-name">{{ match.homeTeam.name }}</div>
                </div>
                
                <div class="match-score" :class="{ finished: match.status === 'finished' }">
                  <div v-if="match.status === 'finished'" class="score">
                    {{ match.score.home }} - {{ match.score.away }}
                  </div>
                  <div v-else class="vs">VS</div>
                </div>
                
                <div class="team away">
                  <div class="team-logo">{{ match.awayTeam.logo }}</div>
                  <div class="team-name">{{ match.awayTeam.name }}</div>
                </div>
              </div>
              
              <div class="match-info">
                <div class="match-competition">{{ match.competition }}</div>
                <div class="match-status" :class="match.status">
                  {{ getStatusText(match.status) }}
                </div>
              </div>
              
              <div class="match-actions">
                <button 
                  v-if="match.status === 'upcoming'"
                  class="action-btn primary"
                  @click="prepareMatch(match)"
                >
                  战术部署
                </button>
                <button 
                  v-if="match.status === 'finished'"
                  class="action-btn secondary"
                  @click="viewReport(match)"
                >
                  比赛报告
                </button>
                <button 
                  v-if="match.status === 'live'"
                  class="action-btn live"
                  @click="watchLive(match)"
                >
                  观看直播
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 赛季统计 -->
    <div class="stats-section">
      <div class="section-card">
        <div class="card-header">
          <h2 class="card-title">
            <span class="title-icon">📊</span>
            赛季统计
          </h2>
        </div>
        <div class="card-content">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">🏆</div>
              <div class="stat-content">
                <div class="stat-label">总比赛</div>
                <div class="stat-value">24</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">✅</div>
              <div class="stat-content">
                <div class="stat-label">胜利</div>
                <div class="stat-value">16</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">🤝</div>
              <div class="stat-content">
                <div class="stat-label">平局</div>
                <div class="stat-value">4</div>
              </div>
            </div>
            
            <div class="stat-card">
              <div class="stat-icon">❌</div>
              <div class="stat-content">
                <div class="stat-label">失败</div>
                <div class="stat-value">4</div>
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

interface Team {
  name: string
  logo: string
}

interface Match {
  id: number
  date: string
  time: string
  homeTeam: Team
  awayTeam: Team
  competition: string
  status: 'upcoming' | 'live' | 'finished'
  score?: {
    home: number
    away: number
  }
}

const activeTab = ref('upcoming')

const tabs = [
  { key: 'upcoming', label: '即将开始' },
  { key: 'live', label: '正在进行' },
  { key: 'finished', label: '已结束' }
]

const matches = ref<Match[]>([
  {
    id: 1,
    date: '12月28日',
    time: '19:30',
    homeTeam: { name: '我的球队', logo: '⚡' },
    awayTeam: { name: '巴塞罗那', logo: '🔵' },
    competition: '欧冠小组赛',
    status: 'upcoming'
  },
  {
    id: 2,
    date: '12月31日',
    time: '16:00',
    homeTeam: { name: '皇家马德里', logo: '👑' },
    awayTeam: { name: '我的球队', logo: '⚡' },
    competition: '西甲联赛',
    status: 'upcoming'
  },
  {
    id: 3,
    date: '12月25日',
    time: '已结束',
    homeTeam: { name: '我的球队', logo: '⚡' },
    awayTeam: { name: '利物浦', logo: '🔴' },
    competition: '友谊赛',
    status: 'finished',
    score: { home: 2, away: 1 }
  },
  {
    id: 4,
    date: '12月22日',
    time: '已结束',
    homeTeam: { name: '曼城', logo: '🩵' },
    awayTeam: { name: '我的球队', logo: '⚡' },
    competition: '英超联赛',
    status: 'finished',
    score: { home: 1, away: 1 }
  }
])

const filteredMatches = computed(() => {
  return matches.value.filter(match => match.status === activeTab.value)
})

const getTabTitle = (tab: string) => {
  const tabInfo = tabs.find(t => t.key === tab)
  return tabInfo ? tabInfo.label : ''
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'upcoming': return '即将开始'
    case 'live': return '正在进行'
    case 'finished': return '已结束'
    default: return ''
  }
}

const prepareMatch = (match: Match) => {
  alert(`为与${match.awayTeam.name}的比赛进行战术部署`)
}

const viewReport = (match: Match) => {
  alert(`查看与${match.awayTeam.name}的比赛报告`)
}

const watchLive = (match: Match) => {
  alert(`观看与${match.awayTeam.name}的直播`)
}
</script>

<style scoped>
.matches {
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

.filter-section {
  margin-bottom: 30px;
}

.filter-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 8px;
}

.filter-tabs {
  display: flex;
  gap: 4px;
}

.filter-tab {
  flex: 1;
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.7);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-tab:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.filter-tab.active {
  background: #00f2b8;
  color: #000;
}

.matches-section,
.stats-section {
  margin-bottom: 30px;
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

.card-content {
  padding: 20px 24px;
}

.matches-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.match-card {
  display: grid;
  grid-template-columns: 120px 1fr 150px 120px;
  gap: 20px;
  align-items: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  transition: all 0.2s;
}

.match-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.match-time {
  text-align: center;
}

.match-date {
  font-size: 0.9rem;
  color: #ffffff;
  font-weight: 600;
  margin-bottom: 4px;
}

.match-hour {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.match-teams {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 20px;
  align-items: center;
}

.team {
  display: flex;
  align-items: center;
  gap: 12px;
}

.team.away {
  flex-direction: row-reverse;
  text-align: right;
}

.team-logo {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.team-name {
  font-weight: 600;
  color: #ffffff;
  font-size: 0.9rem;
}

.match-score {
  text-align: center;
  font-size: 1.2rem;
  font-weight: 700;
  color: #00f2b8;
}

.match-score.finished {
  color: #ffd700;
}

.vs {
  color: rgba(255, 255, 255, 0.5);
  font-size: 1rem;
}

.match-info {
  text-align: center;
}

.match-competition {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 4px;
}

.match-status {
  font-size: 0.7rem;
  padding: 4px 8px;
  border-radius: 8px;
  font-weight: 600;
}

.match-status.upcoming {
  background: rgba(33, 150, 243, 0.2);
  color: #2196f3;
}

.match-status.live {
  background: rgba(255, 87, 34, 0.2);
  color: #ff5722;
}

.match-status.finished {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.match-actions {
  display: flex;
  justify-content: center;
}

.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.primary {
  background: #00f2b8;
  color: #000;
}

.action-btn.primary:hover {
  background: #00d084;
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.action-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.action-btn.live {
  background: rgba(255, 87, 34, 0.8);
  color: #ffffff;
}

.action-btn.live:hover {
  background: #ff5722;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all 0.2s;
}

.stat-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.stat-icon {
  font-size: 2rem;
  width: 50px;
  height: 50px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 4px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 800;
  color: #ffffff;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .match-card {
    grid-template-columns: 1fr;
    gap: 16px;
    text-align: center;
  }
  
  .team.away {
    flex-direction: row;
    text-align: center;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .filter-tabs {
    flex-direction: column;
    gap: 8px;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.8rem;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .match-card {
    padding: 16px;
  }
}
</style> 