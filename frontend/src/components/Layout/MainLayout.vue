<template>
  <div class="main-layout">
    <!-- 顶栏 -->
    <header class="top-bar">
      <div class="top-bar-left">
        <div class="logo-section">
          <span class="logo-icon">⚡</span>
          <span class="logo-text">闪电超级联赛</span>
        </div>
        <button class="menu-toggle" @click="toggleSidebar" v-if="isMobile">
          <span class="hamburger"></span>
        </button>
      </div>
      
      <div class="top-bar-right">
        <div class="user-info">
          <div class="user-avatar">
            <span>👤</span>
          </div>
          <div class="user-details">
            <span class="user-name">足球经理</span>
            <span class="user-level">Lv.1</span>
          </div>
        </div>
        
        <div class="top-actions">
          <button class="action-btn" title="通知">
            <span>🔔</span>
          </button>
          <button class="action-btn" title="设置">
            <span>⚙️</span>
          </button>
          <button class="action-btn logout-btn" @click="logout" title="退出">
            <span>🚪</span>
          </button>
        </div>
      </div>
    </header>

    <!-- 主体区域 -->
    <div class="main-content">
      <!-- 左侧菜单栏 -->
      <aside class="sidebar" :class="{ 'sidebar-collapsed': !sidebarExpanded }">
        <nav class="sidebar-nav">
          <div class="nav-section">
            <h3 class="nav-title">主要功能</h3>
            <ul class="nav-list">
              <li v-for="item in mainMenuItems" :key="item.name" class="nav-item">
                <router-link 
                  :to="item.path" 
                  class="nav-link"
                  :class="{ active: $route.name === item.name }"
                >
                  <span class="nav-icon">{{ item.icon }}</span>
                  <span class="nav-text" v-show="sidebarExpanded">{{ item.label }}</span>
                </router-link>
              </li>
            </ul>
          </div>
          
          <div class="nav-section">
            <h3 class="nav-title" v-show="sidebarExpanded">管理功能</h3>
            <ul class="nav-list">
              <li v-for="item in managementMenuItems" :key="item.name" class="nav-item">
                <router-link 
                  :to="item.path" 
                  class="nav-link"
                  :class="{ active: $route.name === item.name }"
                >
                  <span class="nav-icon">{{ item.icon }}</span>
                  <span class="nav-text" v-show="sidebarExpanded">{{ item.label }}</span>
                </router-link>
              </li>
            </ul>
          </div>
        </nav>
        
        <!-- 侧边栏折叠按钮 -->
        <button class="sidebar-toggle" @click="toggleSidebar" v-if="!isMobile">
          <span>{{ sidebarExpanded ? '◀' : '▶' }}</span>
        </button>
      </aside>

      <!-- 页面内容区域 -->
      <main class="content-area">
        <router-view />
      </main>
    </div>

    <!-- 移动端遮罩层 -->
    <div class="mobile-overlay" v-if="isMobile && sidebarExpanded" @click="closeSidebar"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 响应式状态
const sidebarExpanded = ref(true)
const windowWidth = ref(window.innerWidth)

// 计算属性
const isMobile = computed(() => windowWidth.value < 768)

// 菜单项配置
const mainMenuItems = ref([
  { name: 'dashboard', path: '/dashboard', icon: '🏠', label: '主页概览' },
  { name: 'team', path: '/team', icon: '👥', label: '球队管理' },
  { name: 'matches', path: '/matches', icon: '⚽', label: '比赛赛程' },
  { name: 'market', path: '/market', icon: '💰', label: '转会市场' }
])

const managementMenuItems = ref([
  { name: 'youth', path: '/youth', icon: '🌟', label: '青训营' }
])

// 方法
const toggleSidebar = () => {
  sidebarExpanded.value = !sidebarExpanded.value
}

const closeSidebar = () => {
  if (isMobile.value) {
    sidebarExpanded.value = false
  }
}

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}

// 窗口大小监听
const handleResize = () => {
  windowWidth.value = window.innerWidth
  if (windowWidth.value >= 768) {
    sidebarExpanded.value = true
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  if (isMobile.value) {
    sidebarExpanded.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.main-layout {
  min-height: 100vh;
  background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
  display: flex;
  flex-direction: column;
}

/* 顶栏样式 */
.top-bar {
  height: 70px;
  background: rgba(15, 15, 25, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(100, 255, 218, 0.2);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.5);
}

.top-bar-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 2rem;
  background: linear-gradient(45deg, #ffd700, #ffed4e);
  background-clip: text;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0 0 8px rgba(255, 215, 0, 0.5));
}

.logo-text {
  font-size: 1.4rem;
  font-weight: 800;
  color: #ffffff;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.menu-toggle {
  display: none;
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: background 0.2s;
}

.menu-toggle:hover {
  background: rgba(255, 255, 255, 0.1);
}

.top-bar-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  border: 2px solid rgba(255, 255, 255, 0.2);
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-weight: 600;
  color: #ffffff;
  font-size: 0.9rem;
}

.user-level {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-btn {
  width: 40px;
  height: 40px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1.1rem;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
}

.logout-btn:hover {
  background: rgba(255, 82, 82, 0.2);
}

/* 主体区域 */
.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 侧边栏样式 */
.sidebar {
  width: 260px;
  background: rgba(15, 15, 25, 0.95);
  backdrop-filter: blur(20px);
  border-right: 1px solid rgba(100, 255, 218, 0.2);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow-y: auto;
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.3);
}

.sidebar-collapsed {
  width: 70px;
}

.sidebar-nav {
  padding: 20px 0;
}

.nav-section {
  margin-bottom: 30px;
}

.nav-title {
  font-size: 0.8rem;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.6);
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 0 20px;
  margin-bottom: 12px;
}

.nav-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.nav-item {
  margin-bottom: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
  transition: all 0.2s;
  position: relative;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.nav-link.active {
  background: rgba(100, 255, 218, 0.15);
  color: #64ffda;
  border-right: 3px solid #64ffda;
  box-shadow: inset 0 0 20px rgba(100, 255, 218, 0.1);
}

.nav-icon {
  font-size: 1.2rem;
  width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.nav-text {
  font-weight: 500;
  white-space: nowrap;
}

.sidebar-toggle {
  position: absolute;
  bottom: 20px;
  right: 20px;
  width: 30px;
  height: 30px;
  background: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 50%;
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.sidebar-toggle:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

/* 内容区域 */
.content-area {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: rgba(0, 0, 0, 0.1);
}

/* 移动端遮罩层 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 50;
  display: none;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .top-bar {
    padding: 0 15px;
  }
  
  .logo-text {
    font-size: 1.2rem;
  }
  
  .user-details {
    display: none;
  }
  
  .menu-toggle {
    display: block;
  }
  
  .sidebar {
    position: fixed;
    top: 70px;
    left: 0;
    height: calc(100vh - 70px);
    z-index: 60;
    transform: translateX(-100%);
  }
  
  .sidebar:not(.sidebar-collapsed) {
    transform: translateX(0);
  }
  
  .mobile-overlay {
    display: block;
  }
  
  .content-area {
    padding: 15px;
  }
}

@media (max-width: 480px) {
  .top-bar {
    padding: 0 10px;
  }
  
  .logo-icon {
    font-size: 1.8rem;
  }
  
  .logo-text {
    font-size: 1.1rem;
  }
  
  .content-area {
    padding: 10px;
  }
}
</style> 