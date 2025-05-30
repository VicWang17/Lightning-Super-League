<template>
  <div class="enhanced-timeline">
    <!-- 筛选器 -->
    <div class="timeline-filters" v-if="showFilters">
      <div class="filter-tabs">
        <button 
          v-for="type in eventTypes" 
          :key="type.key"
          @click="filterType = type.key"
          class="filter-tab"
          :class="{ active: filterType === type.key }"
        >
          <span class="filter-icon">{{ type.icon }}</span>
          {{ type.label }}
        </button>
      </div>
    </div>

    <!-- 时间轴主体 -->
    <div class="timeline-container">
      <div class="timeline-list">
        <div 
          v-for="(item, index) in filteredItems" 
          :key="index"
          class="timeline-item"
          :class="[
            `timeline-item--${item.type}`, 
            { 
              'timeline-item--last': index === filteredItems.length - 1,
              'timeline-item--expandable': item.details
            }
          ]"
          @click="toggleExpand(index)"
        >
          <!-- 时间轴线条 -->
          <div class="timeline-line" v-if="index !== filteredItems.length - 1">
            <div class="timeline-line-progress" :style="{ height: getProgressHeight(index) + '%' }"></div>
          </div>
          
          <!-- 状态点 -->
          <div class="timeline-dot" :class="`timeline-dot--${item.type}`">
            <span class="timeline-icon">{{ getIcon(item.type) }}</span>
            <div class="timeline-ripple"></div>
          </div>
          
          <!-- 内容区域 -->
          <div class="timeline-content" :class="{ expanded: expandedItems.includes(index) }">
            <div class="timeline-header">
              <div class="timeline-left">
                <span class="timeline-status" :class="`timeline-status--${item.type}`">
                  {{ getStatusText(item.type) }}
                </span>
                <span class="timeline-priority" v-if="item.priority" :class="`priority--${item.priority}`">
                  {{ getPriorityText(item.priority) }}
                </span>
              </div>
              <span class="timeline-time">{{ item.time }}</span>
            </div>
            
            <div class="timeline-text">{{ item.content }}</div>
            
            <!-- 元数据 -->
            <div class="timeline-meta" v-if="item.meta">
              <span class="meta-item" v-for="(meta, key) in item.meta" :key="key">
                <strong>{{ key }}:</strong> {{ meta }}
              </span>
            </div>
            
            <!-- 详细信息（可展开） -->
            <div class="timeline-details" v-if="item.details && expandedItems.includes(index)">
              <div class="details-content">
                {{ item.details }}
              </div>
              <div class="details-actions" v-if="item.actions">
                <button 
                  v-for="action in item.actions" 
                  :key="action.label"
                  @click.stop="handleAction(action, item)"
                  class="action-btn"
                  :class="action.type"
                >
                  {{ action.label }}
                </button>
              </div>
            </div>
            
            <!-- 展开指示器 -->
            <div class="expand-indicator" v-if="item.details">
              <span>{{ expandedItems.includes(index) ? '收起' : '展开详情' }}</span>
              <span class="expand-arrow" :class="{ rotated: expandedItems.includes(index) }">▼</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

export interface TimelineAction {
  label: string
  type: 'primary' | 'secondary' | 'danger'
  handler: () => void
}

export interface EnhancedTimelineItem {
  type: 'success' | 'error' | 'warning' | 'info'
  content: string
  time: string
  meta?: Record<string, string>
  details?: string
  priority?: 'high' | 'medium' | 'low'
  actions?: TimelineAction[]
}

interface Props {
  items: EnhancedTimelineItem[]
  showFilters?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showFilters: true
})

const filterType = ref<string>('all')
const expandedItems = ref<number[]>([])

const eventTypes = [
  { key: 'all', label: '全部', icon: '📋' },
  { key: 'success', label: '成功', icon: '✅' },
  { key: 'warning', label: '警告', icon: '⚠️' },
  { key: 'error', label: '错误', icon: '❌' },
  { key: 'info', label: '信息', icon: 'ℹ️' }
]

const filteredItems = computed(() => {
  if (filterType.value === 'all') {
    return props.items
  }
  return props.items.filter(item => item.type === filterType.value)
})

const getIcon = (type: string) => {
  switch (type) {
    case 'success': return '✓'
    case 'error': return '✗'
    case 'warning': return '!'
    case 'info': return 'i'
    default: return '•'
  }
}

const getStatusText = (type: string) => {
  switch (type) {
    case 'success': return '成功'
    case 'error': return '错误'
    case 'warning': return '警告'
    case 'info': return '信息'
    default: return '未知'
  }
}

const getPriorityText = (priority: string) => {
  switch (priority) {
    case 'high': return '高优先级'
    case 'medium': return '中优先级'
    case 'low': return '低优先级'
    default: return ''
  }
}

const getProgressHeight = (index: number) => {
  // 简单的进度计算，可以根据实际需求调整
  return Math.min(100, (index + 1) * 20)
}

const toggleExpand = (index: number) => {
  const item = filteredItems.value[index]
  if (!item.details) return
  
  const expandedIndex = expandedItems.value.indexOf(index)
  if (expandedIndex > -1) {
    expandedItems.value.splice(expandedIndex, 1)
  } else {
    expandedItems.value.push(index)
  }
}

const handleAction = (action: TimelineAction, _item: EnhancedTimelineItem) => {
  action.handler()
}

// 添加进入动画
onMounted(() => {
  // 触发动画
  setTimeout(() => {
    const items = document.querySelectorAll('.timeline-item')
    items.forEach((item, index) => {
      setTimeout(() => {
        item.classList.add('animate-in')
      }, index * 100)
    })
  }, 100)
})
</script>

<style scoped>
.enhanced-timeline {
  width: 100%;
}

.timeline-filters {
  margin-bottom: 24px;
}

.filter-tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.filter-tab:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
}

.filter-tab.active {
  background: linear-gradient(135deg, #00f2b8, #00d084);
  color: #000;
  border-color: #00f2b8;
  font-weight: 600;
}

.filter-icon {
  font-size: 1rem;
}

.timeline-container {
  position: relative;
}

.timeline-list {
  position: relative;
}

.timeline-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 20px;
  padding: 16px 0;
  min-height: 80px;
  opacity: 0;
  transform: translateX(-30px);
  transition: all 0.5s ease;
}

.timeline-item.animate-in {
  opacity: 1;
  transform: translateX(0);
}

.timeline-item--expandable {
  cursor: pointer;
}

.timeline-line {
  position: absolute;
  left: 19px;
  top: 40px;
  bottom: -16px;
  width: 3px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  z-index: 0;
  overflow: hidden;
}

.timeline-line-progress {
  width: 100%;
  background: linear-gradient(180deg, #00f2b8, #00d084);
  border-radius: 2px;
  transition: height 1s ease;
}

.timeline-item--last .timeline-line {
  display: none;
}

.timeline-dot {
  position: relative;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  flex-shrink: 0;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.3);
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  overflow: hidden;
}

.timeline-dot--success {
  background: linear-gradient(135deg, #00f2b8, #00d084);
  border: 3px solid #00f2b8;
}

.timeline-dot--error {
  background: linear-gradient(135deg, #ff6b6b, #ff5252);
  border: 3px solid #ff6b6b;
}

.timeline-dot--warning {
  background: linear-gradient(135deg, #ffa726, #ff9800);
  border: 3px solid #ffa726;
}

.timeline-dot--info {
  background: linear-gradient(135deg, #42a5f5, #2196f3);
  border: 3px solid #42a5f5;
}

.timeline-icon {
  color: #ffffff;
  font-weight: bold;
  font-size: 1rem;
  z-index: 2;
}

.timeline-ripple {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  transform: translate(-50%, -50%) scale(0);
  background: rgba(255, 255, 255, 0.3);
  animation: ripple 2s infinite;
}

@keyframes ripple {
  0% {
    transform: translate(-50%, -50%) scale(0);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(2);
    opacity: 0;
  }
}

.timeline-content {
  flex: 1;
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(15px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.4s ease;
  overflow: hidden;
}

.timeline-content:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.timeline-content.expanded {
  background: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.3);
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.timeline-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.timeline-status {
  font-size: 0.8rem;
  font-weight: 700;
  padding: 6px 12px;
  border-radius: 8px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.timeline-status--success {
  background: rgba(0, 242, 184, 0.25);
  color: #00f2b8;
  border: 1px solid rgba(0, 242, 184, 0.4);
}

.timeline-status--error {
  background: rgba(255, 107, 107, 0.25);
  color: #ff6b6b;
  border: 1px solid rgba(255, 107, 107, 0.4);
}

.timeline-status--warning {
  background: rgba(255, 167, 38, 0.25);
  color: #ffa726;
  border: 1px solid rgba(255, 167, 38, 0.4);
}

.timeline-status--info {
  background: rgba(66, 165, 245, 0.25);
  color: #42a5f5;
  border: 1px solid rgba(66, 165, 245, 0.4);
}

.timeline-priority {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}

.priority--high {
  background: rgba(255, 82, 82, 0.2);
  color: #ff5252;
}

.priority--medium {
  background: rgba(255, 167, 38, 0.2);
  color: #ffa726;
}

.priority--low {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.timeline-time {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.6);
  font-weight: 500;
}

.timeline-text {
  color: rgba(255, 255, 255, 0.95);
  font-size: 0.95rem;
  line-height: 1.6;
  margin-bottom: 8px;
}

.timeline-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 8px;
}

.meta-item {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.05);
  padding: 4px 8px;
  border-radius: 6px;
}

.timeline-details {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.details-content {
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.9rem;
  line-height: 1.5;
  margin-bottom: 12px;
}

.details-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.action-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.primary {
  background: #00f2b8;
  color: #000;
}

.action-btn.secondary {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.action-btn.danger {
  background: #ff6b6b;
  color: #fff;
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.expand-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
  padding: 8px;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.8rem;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  transition: all 0.2s;
}

.expand-indicator:hover {
  color: rgba(255, 255, 255, 0.9);
  background: rgba(255, 255, 255, 0.08);
}

.expand-arrow {
  transition: transform 0.3s ease;
}

.expand-arrow.rotated {
  transform: rotate(180deg);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .timeline-item {
    gap: 16px;
  }
  
  .timeline-dot {
    width: 32px;
    height: 32px;
  }
  
  .timeline-line {
    left: 15px;
  }
  
  .timeline-content {
    padding: 16px;
  }
  
  .timeline-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .filter-tabs {
    gap: 6px;
  }
  
  .filter-tab {
    padding: 6px 12px;
    font-size: 0.8rem;
  }
}
</style> 