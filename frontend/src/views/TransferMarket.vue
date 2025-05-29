<template>
  <div class="transfer-market">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <span class="title-icon">💰</span>
        转会市场
      </h1>
      <p class="page-subtitle">发现天才球员，打造梦幻阵容</p>
    </div>

    <!-- 搜索和筛选 -->
    <div class="search-section">
      <div class="search-card">
        <div class="search-controls">
          <div class="search-input-group">
            <input 
              v-model="searchQuery" 
              class="search-input" 
              placeholder="搜索球员姓名..."
              @input="filterPlayers"
            />
            <button class="search-btn">🔍</button>
          </div>
          
          <div class="filter-group">
            <select v-model="positionFilter" @change="filterPlayers" class="filter-select">
              <option value="">所有位置</option>
              <option value="goalkeeper">门将</option>
              <option value="defender">后卫</option>
              <option value="midfielder">中场</option>
              <option value="forward">前锋</option>
            </select>
            
            <select v-model="priceRangeFilter" @change="filterPlayers" class="filter-select">
              <option value="">所有价格</option>
              <option value="0-1">0-1M</option>
              <option value="1-5">1-5M</option>
              <option value="5-10">5-10M</option>
              <option value="10+">10M+</option>
            </select>
            
            <select v-model="ageRangeFilter" @change="filterPlayers" class="filter-select">
              <option value="">所有年龄</option>
              <option value="18-22">18-22岁</option>
              <option value="23-27">23-27岁</option>
              <option value="28-32">28-32岁</option>
              <option value="33+">33岁+</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 推荐球员 -->
    <div class="recommendations-section">
      <div class="section-card">
        <div class="card-header">
          <h2 class="card-title">
            <span class="title-icon">⭐</span>
            今日推荐
          </h2>
        </div>
        <div class="card-content">
          <div class="recommendations-grid">
            <div v-for="player in recommendedPlayers" :key="player.id" class="recommendation-card">
              <div class="player-badge hot" v-if="player.isHot">🔥</div>
              <div class="player-image">{{ player.avatar }}</div>
              <h3 class="player-name">{{ player.name }}</h3>
              <p class="player-info">{{ player.position }} | {{ player.age }}岁</p>
              <div class="player-rating">⭐ {{ player.rating }}</div>
              <div class="player-price">€{{ player.price }}M</div>
              <button class="quick-buy-btn" @click="quickBuy(player)">快速报价</button>
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
            <span class="title-icon">📋</span>
            可转会球员 ({{ filteredPlayers.length }})
          </h2>
          <div class="sort-controls">
            <select v-model="sortBy" @change="sortPlayers" class="sort-select">
              <option value="rating">按能力排序</option>
              <option value="price">按价格排序</option>
              <option value="age">按年龄排序</option>
              <option value="name">按姓名排序</option>
            </select>
          </div>
        </div>
        <div class="card-content">
          <div class="players-grid">
            <div v-for="player in displayedPlayers" :key="player.id" class="player-card">
              <div class="player-main-info">
                <div class="player-avatar">
                  <span>{{ player.avatar }}</span>
                  <div class="player-status" :class="player.availability">
                    {{ getAvailabilityText(player.availability) }}
                  </div>
                </div>
                <div class="player-details">
                  <h3 class="player-name">{{ player.name }}</h3>
                  <p class="player-meta">{{ player.position }} | {{ player.age }}岁 | {{ player.nationality }}</p>
                  <div class="player-club">🏟️ {{ player.currentClub }}</div>
                </div>
              </div>
              
              <div class="player-stats">
                <div class="stat-item">
                  <span class="stat-label">能力值</span>
                  <div class="stat-bar">
                    <div class="stat-fill" :style="{ width: player.rating + '%' }"></div>
                  </div>
                  <span class="stat-value">{{ player.rating }}</span>
                </div>
                
                <div class="stat-item">
                  <span class="stat-label">潜力</span>
                  <div class="stat-bar">
                    <div class="stat-fill potential" :style="{ width: player.potential + '%' }"></div>
                  </div>
                  <span class="stat-value">{{ player.potential }}</span>
                </div>
              </div>
              
              <div class="player-transfer-info">
                <div class="price-info">
                  <span class="price-label">转会费</span>
                  <span class="price-value">€{{ player.price }}M</span>
                </div>
                <div class="contract-info">
                  <span class="contract-label">合同到期</span>
                  <span class="contract-value">{{ player.contractEnd }}</span>
                </div>
              </div>
              
              <div class="player-actions">
                <button class="action-btn primary" @click="viewDetails(player)">
                  查看详情
                </button>
                <button class="action-btn secondary" @click="makeOffer(player)">
                  报价
                </button>
                <button class="action-btn watch" @click="addToWatchlist(player)">
                  关注
                </button>
              </div>
            </div>
          </div>
          
          <!-- 加载更多 -->
          <div class="load-more" v-if="filteredPlayers.length > displayedPlayers.length">
            <button class="load-more-btn" @click="loadMore">
              加载更多球员 ({{ filteredPlayers.length - displayedPlayers.length }} 名剩余)
            </button>
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
  potential: number
  price: number
  nationality: string
  currentClub: string
  contractEnd: string
  avatar: string
  positionType: string
  availability: 'available' | 'negotiating' | 'unavailable'
  isHot?: boolean
}

const searchQuery = ref('')
const positionFilter = ref('')
const priceRangeFilter = ref('')
const ageRangeFilter = ref('')
const sortBy = ref('rating')
const displayCount = ref(10)

const allPlayers = ref<Player[]>([
  { id: 1, name: '哈兰德', position: '中锋', age: 23, rating: 92, potential: 96, price: 120, nationality: '挪威', currentClub: '曼城', contractEnd: '2027', avatar: '⚡', positionType: 'forward', availability: 'available', isHot: true },
  { id: 2, name: '姆巴佩', position: '左翼', age: 24, rating: 93, potential: 95, price: 150, nationality: '法国', currentClub: '巴黎圣日耳曼', contractEnd: '2024', avatar: '🏃‍♂️', positionType: 'forward', availability: 'negotiating' },
  { id: 3, name: '贝林厄姆', position: '中场', age: 20, rating: 86, potential: 93, price: 80, nationality: '英格兰', currentClub: '皇家马德里', contractEnd: '2029', avatar: '🎯', positionType: 'midfielder', availability: 'available', isHot: true },
  { id: 4, name: '鲁迪格', position: '中后卫', age: 30, rating: 84, potential: 84, price: 35, nationality: '德国', currentClub: '皇家马德里', contractEnd: '2026', avatar: '🛡️', positionType: 'defender', availability: 'available' },
  { id: 5, name: '阿里森', position: '门将', age: 30, rating: 89, potential: 89, price: 45, nationality: '巴西', currentClub: '利物浦', contractEnd: '2027', avatar: '🥅', positionType: 'goalkeeper', availability: 'unavailable' },
  { id: 6, name: '维尼修斯', position: '左翼', age: 23, rating: 88, potential: 92, price: 100, nationality: '巴西', currentClub: '皇家马德里', contractEnd: '2027', avatar: '💨', positionType: 'forward', availability: 'available' },
  { id: 7, name: '佩德里', position: '中场', age: 21, rating: 85, potential: 94, price: 90, nationality: '西班牙', currentClub: '巴塞罗那', contractEnd: '2026', avatar: '🎨', positionType: 'midfielder', availability: 'available', isHot: true },
  { id: 8, name: '德容', position: '中场', age: 26, rating: 87, potential: 90, price: 70, nationality: '荷兰', currentClub: '巴塞罗那', contractEnd: '2026', avatar: '⚽', positionType: 'midfielder', availability: 'negotiating' },
  { id: 9, name: '坎塞洛', position: '右后卫', age: 29, rating: 86, potential: 86, price: 40, nationality: '葡萄牙', currentClub: '曼城', contractEnd: '2027', avatar: '🏃', positionType: 'defender', availability: 'available' },
  { id: 10, name: '萨拉赫', position: '右翼', age: 31, rating: 89, potential: 89, price: 55, nationality: '埃及', currentClub: '利物浦', contractEnd: '2025', avatar: '🌟', positionType: 'forward', availability: 'available' }
])

const filteredPlayers = ref<Player[]>([...allPlayers.value])

const recommendedPlayers = computed(() => {
  return allPlayers.value.filter(p => p.isHot).slice(0, 3)
})

const displayedPlayers = computed(() => {
  return filteredPlayers.value.slice(0, displayCount.value)
})

const filterPlayers = () => {
  let filtered = [...allPlayers.value]
  
  // 搜索过滤
  if (searchQuery.value) {
    filtered = filtered.filter(p => 
      p.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }
  
  // 位置过滤
  if (positionFilter.value) {
    filtered = filtered.filter(p => p.positionType === positionFilter.value)
  }
  
  // 价格过滤
  if (priceRangeFilter.value) {
    const [min, max] = priceRangeFilter.value.split('-').map(v => 
      v === '' ? Infinity : parseInt(v.replace('+', ''))
    )
    filtered = filtered.filter(p => {
      if (priceRangeFilter.value.includes('+')) {
        return p.price >= min
      }
      return p.price >= min && p.price <= max
    })
  }
  
  // 年龄过滤
  if (ageRangeFilter.value) {
    const [min, max] = ageRangeFilter.value.split('-').map(v => 
      v === '' ? Infinity : parseInt(v.replace('+', ''))
    )
    filtered = filtered.filter(p => {
      if (ageRangeFilter.value.includes('+')) {
        return p.age >= min
      }
      return p.age >= min && p.age <= max
    })
  }
  
  filteredPlayers.value = filtered
  sortPlayers()
}

const sortPlayers = () => {
  filteredPlayers.value.sort((a, b) => {
    switch (sortBy.value) {
      case 'rating':
        return b.rating - a.rating
      case 'price':
        return a.price - b.price
      case 'age':
        return a.age - b.age
      case 'name':
        return a.name.localeCompare(b.name)
      default:
        return 0
    }
  })
}

const getAvailabilityText = (status: string) => {
  switch (status) {
    case 'available': return '可转会'
    case 'negotiating': return '谈判中'
    case 'unavailable': return '不可转会'
    default: return ''
  }
}

const loadMore = () => {
  displayCount.value += 10
}

const quickBuy = (player: Player) => {
  alert(`正在为 ${player.name} 发起快速报价...`)
}

const viewDetails = (player: Player) => {
  alert(`查看 ${player.name} 的详细信息`)
}

const makeOffer = (player: Player) => {
  alert(`为 ${player.name} 制定转会报价`)
}

const addToWatchlist = (player: Player) => {
  alert(`已将 ${player.name} 添加到关注列表`)
}
</script>

<style scoped>
.transfer-market {
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

.search-section {
  margin-bottom: 30px;
}

.search-card {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 16px;
  padding: 24px;
}

.search-controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-input-group {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-input {
  flex: 1;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: #ffffff;
  font-size: 1rem;
  outline: none;
}

.search-input:focus {
  border-color: #00f2b8;
  background: rgba(255, 255, 255, 0.15);
}

.search-btn {
  padding: 12px 16px;
  background: #00f2b8;
  border: none;
  border-radius: 12px;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
}

.search-btn:hover {
  background: #00d084;
  transform: scale(1.05);
}

.filter-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.filter-select,
.sort-select {
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #ffffff;
  font-size: 0.9rem;
  outline: none;
  min-width: 120px;
}

.filter-select:focus,
.sort-select:focus {
  border-color: #00f2b8;
  background: rgba(255, 255, 255, 0.15);
}

.recommendations-section,
.players-section {
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

.card-content {
  padding: 20px 24px;
}

.recommendations-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
}

.recommendation-card {
  position: relative;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  transition: all 0.3s ease;
}

.recommendation-card:hover {
  background: rgba(255, 255, 255, 0.08);
  transform: translateY(-4px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
}

.player-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
}

.player-badge.hot {
  background: rgba(255, 87, 34, 0.8);
  color: #ffffff;
}

.player-image {
  font-size: 3rem;
  margin-bottom: 12px;
}

.player-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px 0;
}

.player-info {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 8px 0;
}

.player-rating {
  font-size: 0.9rem;
  color: #ffd700;
  margin-bottom: 8px;
}

.player-price {
  font-size: 1.1rem;
  font-weight: 700;
  color: #00f2b8;
  margin-bottom: 12px;
}

.quick-buy-btn {
  width: 100%;
  padding: 8px;
  background: #00f2b8;
  border: none;
  border-radius: 8px;
  color: #000;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-buy-btn:hover {
  background: #00d084;
  transform: scale(1.02);
}

.players-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.player-card {
  display: grid;
  grid-template-columns: 2fr 1.5fr 1fr 1fr;
  gap: 20px;
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

.player-main-info {
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

.player-status {
  position: absolute;
  bottom: -4px;
  right: -4px;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 0.6rem;
  font-weight: 600;
  color: #000;
}

.player-status.available {
  background: #4caf50;
}

.player-status.negotiating {
  background: #ff9800;
}

.player-status.unavailable {
  background: #f44336;
  color: #fff;
}

.player-name {
  font-size: 1.1rem;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px 0;
}

.player-meta {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 4px 0;
}

.player-club {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.5);
}

.player-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
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

.stat-fill.potential {
  background: linear-gradient(90deg, #ffd700, #ffed4e);
}

.stat-value {
  font-size: 0.7rem;
  color: #00f2b8;
  font-weight: 600;
  text-align: right;
}

.player-transfer-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.price-info,
.contract-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.price-label,
.contract-label {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.6);
}

.price-value {
  font-size: 0.9rem;
  font-weight: 700;
  color: #00f2b8;
}

.contract-value {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.8);
}

.player-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 0.7rem;
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

.action-btn.watch {
  background: rgba(255, 215, 0, 0.2);
  color: #ffd700;
  border: 1px solid rgba(255, 215, 0, 0.3);
}

.action-btn.watch:hover {
  background: rgba(255, 215, 0, 0.3);
  color: #ffffff;
}

.load-more {
  text-align: center;
  margin-top: 30px;
}

.load-more-btn {
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.load-more-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  transform: translateY(-1px);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .player-card {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .search-controls {
    flex-direction: column;
  }
}

@media (max-width: 768px) {
  .filter-group {
    flex-direction: column;
  }
  
  .filter-select,
  .sort-select {
    min-width: auto;
    width: 100%;
  }
  
  .recommendations-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .page-title {
    font-size: 1.8rem;
  }
  
  .search-input-group {
    flex-direction: column;
  }
  
  .search-input,
  .search-btn {
    width: 100%;
  }
}
</style> 