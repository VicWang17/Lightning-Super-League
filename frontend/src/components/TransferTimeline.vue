<template>
  <div class="transfer-timeline">
    <div class="timeline-header">
      <h3 class="timeline-title">
        <span class="title-icon">📈</span>
        转会动态
      </h3>
      <button class="refresh-btn" @click="refreshData">
        <span>🔄</span>
        刷新
      </button>
    </div>
    
    <EnhancedTimeline 
      :items="transferItems" 
      :show-filters="false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import EnhancedTimeline, { EnhancedTimelineItem } from './EnhancedTimeline.vue'

const transferItems = ref<EnhancedTimelineItem[]>([
  {
    type: 'success',
    content: '球员转会成功：梅西 → 巴黎圣日耳曼',
    time: '30分钟前',
    meta: {
      '转会费': '免费转会',
      '年薪': '€30M',
      '合同期': '2年'
    },
    details: '阿根廷巨星梅西正式加盟巴黎圣日耳曼，这是今夏最重大的转会之一。',
    priority: 'high'
  },
  {
    type: 'warning',
    content: '转会传闻：哈兰德可能离开多特蒙德',
    time: '1小时前',
    meta: {
      '目标球队': '曼城',
      '预期转会费': '€150M',
      '可能性': '70%'
    },
    details: '多家媒体报道哈兰德即将离开多特蒙德，曼城是最有力的竞争者。',
    priority: 'medium'
  },
  {
    type: 'info',
    content: '新星涌现：年仅17岁的佩德里获得金童奖',
    time: '3小时前',
    meta: {
      '年龄': '17岁',
      '位置': '中场',
      '身价涨幅': '+€20M'
    },
    details: '巴塞罗那的年轻中场佩德里获得金童奖，身价暴涨。',
    priority: 'low'
  },
  {
    type: 'error',
    content: '转会失败：姆巴佩续约巴黎',
    time: '5小时前',
    meta: {
      '原目标': '皇家马德里',
      '新合同': '3年',
      '年薪': '€50M'
    },
    details: '皇马的转会目标姆巴佩选择续约巴黎，转会失败。',
    priority: 'medium'
  }
])

const refreshData = () => {
  // 模拟刷新数据
  console.log('刷新转会数据...')
}
</script>

<style scoped>
.transfer-timeline {
  width: 100%;
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 0 4px;
}

.timeline-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.1rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0;
}

.title-icon {
  font-size: 1rem;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transform: translateY(-1px);
}
</style> 