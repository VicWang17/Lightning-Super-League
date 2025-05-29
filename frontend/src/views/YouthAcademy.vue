<template>
  <div class="youth-academy">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <span class="title-icon">🌟</span>
        青训营
      </h1>
      <p class="page-subtitle">培养年轻天才，打造球队未来</p>
    </div>

    <!-- 青训营概况 -->
    <div class="academy-overview">
      <div class="overview-grid">
        <div class="overview-card">
          <div class="card-icon">🏆</div>
          <div class="card-content">
            <h3 class="card-title">青训营等级</h3>
            <div class="card-value">3级</div>
            <div class="card-desc">可培养潜力85+球员</div>
          </div>
        </div>
        
        <div class="overview-card">
          <div class="card-icon">👶</div>
          <div class="card-content">
            <h3 class="card-title">学员数量</h3>
            <div class="card-value">8名</div>
            <div class="card-desc">最大容量：12名</div>
          </div>
        </div>
        
        <div class="overview-card">
          <div class="card-icon">🎓</div>
          <div class="card-content">
            <h3 class="card-title">毕业球员</h3>
            <div class="card-value">15名</div>
            <div class="card-desc">本赛季已毕业</div>
          </div>
        </div>
        
        <div class="overview-card">
          <div class="card-icon">💰</div>
          <div class="card-content">
            <h3 class="card-title">月度开支</h3>
            <div class="card-value">€500K</div>
            <div class="card-desc">教练+设施费用</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 青年球员列表 -->
    <div class="players-section">
      <div class="section-card">
        <div class="card-header">
          <h2 class="card-title">
            <span class="title-icon">👦</span>
            青年球员
          </h2>
          <div class="header-actions">
            <button class="action-btn" @click="recruitPlayer">
              <span>🔍</span>
              球探招募
            </button>
            <button class="action-btn primary" @click="upgradeAcademy">
              <span>⬆️</span>
              升级设施
            </button>
          </div>
        </div>
        <div class="card-content">
          <div class="players-grid">
            <div v-for="player in youthPlayers" :key="player.id" class="player-card">
              <div class="player-info">
                <div class="player-avatar">
                  <span>{{ player.avatar }}</span>
                  <div class="player-age">{{ player.age }}岁</div>
                </div>
                <div class="player-details">
                  <h3 class="player-name">{{ player.name }}</h3>
                  <p class="player-position">{{ player.position }}</p>
                  <div class="player-progress">
                    <span class="progress-label">培养进度</span>
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: player.trainingProgress + '%' }"></div>
                    </div>
                    <span class="progress-value">{{ player.trainingProgress }}%</span>
                  </div>
                </div>
              </div>
              
              <div class="player-attributes">
                <div class="attribute-row">
                  <span class="attr-label">当前能力</span>
                  <div class="attr-bar">
                    <div class="attr-fill current" :style="{ width: player.currentRating + '%' }"></div>
                  </div>
                  <span class="attr-value">{{ player.currentRating }}</span>
                </div>
                
                <div class="attribute-row">
                  <span class="attr-label">潜在能力</span>
                  <div class="attr-bar">
                    <div class="attr-fill potential" :style="{ width: player.potential + '%' }"></div>
                  </div>
                  <span class="attr-value">{{ player.potential }}</span>
                </div>
                
                <div class="talent-badge" :class="getTalentClass(player.talentLevel)">
                  {{ getTalentText(player.talentLevel) }}
                </div>
              </div>
              
              <div class="player-training">
                <div class="training-info">
                  <span class="training-label">训练重点</span>
                  <select v-model="player.trainingFocus" class="training-select">
                    <option value="technical">技术</option>
                    <option value="physical">体能</option>
                    <option value="tactical">战术</option>
                    <option value="mental">心理</option>
                  </select>
                </div>
                
                <div class="graduation-time" v-if="player.graduationTime">
                  <span class="graduation-label">预计毕业</span>
                  <span class="graduation-value">{{ player.graduationTime }}</span>
                </div>
              </div>
              
              <div class="player-actions">
                <button class="player-btn primary" @click="viewPlayerDetails(player)">
                  查看详情
                </button>
                <button 
                  v-if="player.trainingProgress >= 100"
                  class="player-btn graduate"
                  @click="graduatePlayer(player)"
                >
                  提升一队
                </button>
                <button 
                  v-else
                  class="player-btn secondary"
                  @click="intensiveTraining(player)"
                >
                  强化训练
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 教练团队 -->
    <div class="coaches-section">
      <div class="section-card">
        <div class="card-header">
          <h2 class="card-title">
            <span class="title-icon">👨‍🏫</span>
            教练团队
          </h2>
        </div>
        <div class="card-content">
          <div class="coaches-grid">
            <div v-for="coach in coaches" :key="coach.id" class="coach-card">
              <div class="coach-avatar">{{ coach.avatar }}</div>
              <div class="coach-info">
                <h3 class="coach-name">{{ coach.name }}</h3>
                <p class="coach-specialty">专长：{{ coach.specialty }}</p>
                <div class="coach-rating">
                  <span>⭐ {{ coach.rating }}/10</span>
                </div>
              </div>
              <div class="coach-salary">
                <span class="salary-label">月薪</span>
                <span class="salary-value">€{{ coach.salary }}K</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface YouthPlayer {
  id: number
  name: string
  age: number
  position: string
  currentRating: number
  potential: number
  trainingProgress: number
  trainingFocus: string
  talentLevel: 1 | 2 | 3 | 4 | 5
  avatar: string
  graduationTime?: string
}

interface Coach {
  id: number
  name: string
  specialty: string
  rating: number
  salary: number
  avatar: string
}

const youthPlayers = ref<YouthPlayer[]>([
  {
    id: 1,
    name: '李小明',
    age: 17,
    position: '中场',
    currentRating: 62,
    potential: 88,
    trainingProgress: 75,
    trainingFocus: 'technical',
    talentLevel: 4,
    avatar: '⚽',
    graduationTime: '6个月后'
  },
  {
    id: 2,
    name: '王天才',
    age: 16,
    position: '前锋',
    currentRating: 58,
    potential: 92,
    trainingProgress: 45,
    trainingFocus: 'physical',
    talentLevel: 5,
    avatar: '🎯',
    graduationTime: '1年后'
  },
  {
    id: 3,
    name: '张速度',
    age: 18,
    position: '右翼',
    currentRating: 65,
    potential: 85,
    trainingProgress: 100,
    trainingFocus: 'tactical',
    talentLevel: 3,
    avatar: '💨'
  },
  {
    id: 4,
    name: '刘守门',
    age: 17,
    position: '门将',
    currentRating: 60,
    potential: 89,
    trainingProgress: 60,
    trainingFocus: 'mental',
    talentLevel: 4,
    avatar: '🥅',
    graduationTime: '8个月后'
  }
])

const coaches = ref<Coach[]>([
  {
    id: 1,
    name: '马尔科·技术',
    specialty: '技术训练',
    rating: 8,
    salary: 50,
    avatar: '👨‍🏫'
  },
  {
    id: 2,
    name: '约翰·体能',
    specialty: '体能训练',
    rating: 7,
    salary: 40,
    avatar: '💪'
  },
  {
    id: 3,
    name: '安东尼奥·战术',
    specialty: '战术训练',
    rating: 9,
    salary: 60,
    avatar: '🧠'
  }
])

const getTalentClass = (level: number) => {
  switch (level) {
    case 5: return 'legendary'
    case 4: return 'excellent'
    case 3: return 'good'
    case 2: return 'average'
    case 1: return 'poor'
    default: return 'average'
  }
}

const getTalentText = (level: number) => {
  switch (level) {
    case 5: return '传奇天赋'
    case 4: return '卓越天赋'
    case 3: return '良好天赋'
    case 2: return '普通天赋'
    case 1: return '一般天赋'
    default: return '未知'
  }
}

const recruitPlayer = () => {
  alert('球探系统开发中...')
}

const upgradeAcademy = () => {
  alert('青训营升级功能开发中...')
}

const viewPlayerDetails = (player: YouthPlayer) => {
  alert(`查看 ${player.name} 的详细信息`)
}

const graduatePlayer = (player: YouthPlayer) => {
  alert(`${player.name} 已准备好提升至一线队`)
}

const intensiveTraining = (player: YouthPlayer) => {
  alert(`为 ${player.name} 安排强化训练`)
}
</script>

<style scoped>
.youth-academy {
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

.academy-overview {
  margin-bottom: 30px;
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.overview-card {
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

.overview-card:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
}

.card-icon {
  font-size: 2.5rem;
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
}

.card-title {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  margin: 0 0 4px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-value {
  font-size: 1.8rem;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 4px;
}

.card-desc {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}

.players-section,
.coaches-section {
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
  gap: 12px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
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

.action-btn.primary {
  background: #00f2b8;
  color: #000;
  border-color: #00f2b8;
}

.action-btn.primary:hover {
  background: #00d084;
}

.card-content {
  padding: 20px 24px;
}

.players-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.player-card {
  display: grid;
  grid-template-columns: 2fr 2fr 1.5fr 1fr;
  gap: 24px;
  align-items: center;
  padding: 20px;
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
  gap: 16px;
}

.player-avatar {
  position: relative;
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.8rem;
  flex-shrink: 0;
}

.player-age {
  position: absolute;
  bottom: -4px;
  right: -4px;
  background: #00f2b8;
  color: #000;
  font-size: 0.6rem;
  font-weight: 600;
  padding: 2px 4px;
  border-radius: 4px;
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
  margin: 0 0 8px 0;
}

.player-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.7rem;
}

.progress-label {
  color: rgba(255, 255, 255, 0.6);
  width: 50px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00f2b8, #00d084);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-value {
  color: #00f2b8;
  font-weight: 600;
  width: 30px;
  text-align: right;
}

.player-attributes {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.attribute-row {
  display: grid;
  grid-template-columns: 60px 1fr 30px;
  gap: 8px;
  align-items: center;
  font-size: 0.7rem;
}

.attr-label {
  color: rgba(255, 255, 255, 0.6);
}

.attr-bar {
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.attr-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.attr-fill.current {
  background: linear-gradient(90deg, #00f2b8, #00d084);
}

.attr-fill.potential {
  background: linear-gradient(90deg, #ffd700, #ffed4e);
}

.attr-value {
  color: #00f2b8;
  font-weight: 600;
  text-align: right;
}

.talent-badge {
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 0.6rem;
  font-weight: 600;
  text-align: center;
  margin-top: 8px;
}

.talent-badge.legendary {
  background: rgba(138, 43, 226, 0.3);
  color: #8a2be2;
}

.talent-badge.excellent {
  background: rgba(255, 215, 0, 0.3);
  color: #ffd700;
}

.talent-badge.good {
  background: rgba(76, 175, 80, 0.3);
  color: #4caf50;
}

.talent-badge.average {
  background: rgba(255, 193, 7, 0.3);
  color: #ffc107;
}

.talent-badge.poor {
  background: rgba(158, 158, 158, 0.3);
  color: #9e9e9e;
}

.player-training {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.training-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.training-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}

.training-select {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  color: #ffffff;
  font-size: 0.7rem;
  outline: none;
}

.graduation-time {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.graduation-label {
  font-size: 0.6rem;
  color: rgba(255, 255, 255, 0.5);
}

.graduation-value {
  font-size: 0.7rem;
  color: #ffd700;
  font-weight: 600;
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
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.player-btn.primary {
  background: #00f2b8;
  color: #000;
}

.player-btn.primary:hover {
  background: #00d084;
}

.player-btn.secondary {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.player-btn.secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.player-btn.graduate {
  background: #ffd700;
  color: #000;
}

.player-btn.graduate:hover {
  background: #ffed4e;
}

.coaches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.coach-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  transition: all 0.2s;
}

.coach-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-1px);
}

.coach-avatar {
  width: 50px;
  height: 50px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.coach-info {
  flex: 1;
}

.coach-name {
  font-size: 1rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px 0;
}

.coach-specialty {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 4px 0;
}

.coach-rating {
  font-size: 0.8rem;
  color: #ffd700;
}

.coach-salary {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.salary-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}

.salary-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: #00f2b8;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .player-card {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  
  .coaches-grid {
    grid-template-columns: 1fr;
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
    padding: 16px;
  }
}
</style> 