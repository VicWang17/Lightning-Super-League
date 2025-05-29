<template>
  <div class="timeline">
    <div class="timeline-list">
      <div 
        v-for="(item, index) in items" 
        :key="index"
        class="timeline-item"
        :class="{ 'timeline-item--last': index === items.length - 1 }"
      >
        <!-- 时间轴线条 -->
        <div class="timeline-line" v-if="index !== items.length - 1"></div>
        
        <!-- 状态点 -->
        <div class="timeline-dot" :class="`timeline-dot--${item.type}`">
          <span class="timeline-icon">{{ getIcon(item.type) }}</span>
        </div>
        
        <!-- 内容区域 -->
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="timeline-status" :class="`timeline-status--${item.type}`">
              {{ getStatusText(item.type) }}
            </span>
            <span class="timeline-time">{{ item.time }}</span>
          </div>
          <div class="timeline-text">{{ item.content }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface TimelineItem {
  type: 'success' | 'error' | 'warning' | 'info'
  content: string
  time: string
}

interface Props {
  items: TimelineItem[]
}

defineProps<Props>()

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
</script>

<style scoped>
.timeline {
  width: 100%;
}

.timeline-list {
  position: relative;
}

.timeline-item {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  min-height: 45px;
}

.timeline-line {
  position: absolute;
  left: 11px;
  top: 24px;
  bottom: -8px;
  width: 1px;
  background: rgba(255, 255, 255, 0.2);
  z-index: 0;
}

.timeline-item--last .timeline-line {
  display: none;
}

.timeline-dot {
  position: relative;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.timeline-dot--success {
  background: #00f2b8;
  color: #000;
}

.timeline-dot--error {
  background: #ff6b6b;
  color: #fff;
}

.timeline-dot--warning {
  background: #ffa726;
  color: #000;
}

.timeline-dot--info {
  background: #42a5f5;
  color: #fff;
}

.timeline-icon {
  font-weight: bold;
  font-size: 0.7rem;
}

.timeline-content {
  flex: 1;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px;
  transition: background 0.2s ease;
}

.timeline-content:hover {
  background: rgba(255, 255, 255, 0.06);
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
  gap: 8px;
}

.timeline-status {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.timeline-status--success {
  background: rgba(0, 242, 184, 0.15);
  color: #00f2b8;
}

.timeline-status--error {
  background: rgba(255, 107, 107, 0.15);
  color: #ff6b6b;
}

.timeline-status--warning {
  background: rgba(255, 167, 38, 0.15);
  color: #ffa726;
}

.timeline-status--info {
  background: rgba(66, 165, 245, 0.15);
  color: #42a5f5;
}

.timeline-time {
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 500;
  white-space: nowrap;
}

.timeline-text {
  color: rgba(255, 255, 255, 0.85);
  font-size: 0.8rem;
  line-height: 1.4;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .timeline-item {
    gap: 10px;
  }
  
  .timeline-dot {
    width: 20px;
    height: 20px;
  }
  
  .timeline-line {
    left: 9px;
  }
  
  .timeline-content {
    padding: 10px;
  }
  
  .timeline-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  
  .timeline-text {
    font-size: 0.75rem;
  }
}
</style> 