# 时间轴组件使用指南

本项目包含两个时间轴组件，用于在闪电超级联赛游戏中展示各种动态信息。

## 组件概览

### 1. Timeline.vue (基础时间轴)
基础的时间轴组件，支持不同状态的事件显示。

### 2. EnhancedTimeline.vue (增强时间轴)
功能更丰富的时间轴组件，支持筛选、展开详情、优先级、操作按钮等高级功能。

### 3. TransferTimeline.vue (转会时间轴)
专门用于转会市场的时间轴组件示例。

## 使用方式

### 基础时间轴组件

```vue
<template>
  <Timeline :items="timelineItems" title="球队动态" />
</template>

<script setup>
import Timeline, { TimelineItem } from '@/components/Timeline.vue'

const timelineItems: TimelineItem[] = [
  {
    type: 'success',
    content: '球员训练成功',
    time: '2小时前',
    meta: '技术训练成果显著'
  }
]
</script>
```

### 增强时间轴组件

```vue
<template>
  <EnhancedTimeline :items="enhancedItems" :show-filters="true" />
</template>

<script setup>
import EnhancedTimeline, { EnhancedTimelineItem } from '@/components/EnhancedTimeline.vue'

const enhancedItems: EnhancedTimelineItem[] = [
  {
    type: 'warning',
    content: '收到转会报价',
    time: '1小时前',
    meta: {
      '报价金额': '€25M',
      '球员位置': '中场'
    },
    details: '详细的转会信息...',
    priority: 'high',
    actions: [
      {
        label: '接受报价',
        type: 'primary',
        handler: () => console.log('接受')
      }
    ]
  }
]
</script>
```

## 数据类型定义

### TimelineItem (基础)
```typescript
interface TimelineItem {
  type: 'success' | 'error' | 'warning' | 'info'
  content: string
  time: string
  meta?: string
}
```

### EnhancedTimelineItem (增强)
```typescript
interface EnhancedTimelineItem {
  type: 'success' | 'error' | 'warning' | 'info'
  content: string
  time: string
  meta?: Record<string, string>        // 元数据对象
  details?: string                     // 详细信息
  priority?: 'high' | 'medium' | 'low' // 优先级
  actions?: TimelineAction[]           // 操作按钮
}

interface TimelineAction {
  label: string
  type: 'primary' | 'secondary' | 'danger'
  handler: () => void
}
```

## 状态类型说明

- **success**: 成功事件 (绿色) - 如训练成功、转会成功等
- **error**: 错误事件 (红色) - 如球员受伤、转会失败等  
- **warning**: 警告事件 (橙色) - 如收到报价、需要关注的事件
- **info**: 信息事件 (蓝色) - 如新闻、一般性通知等

## 设计特性

### 视觉效果
- 现代化的毛玻璃效果背景
- 渐变色彩的状态指示器
- 平滑的悬浮和过渡动画
- 响应式设计，支持移动设备

### 交互功能 (增强版)
- 事件类型筛选
- 点击展开详细信息
- 优先级标识
- 自定义操作按钮
- 进度条动画效果

### 动画效果
- 从左侧滑入的进入动画
- 时间轴进度条动画
- 悬浮缩放效果
- 波纹扩散动画

## 最佳实践

1. **数据更新**: 使用 Vue 的响应式数据，时间轴会自动更新
2. **性能优化**: 大量数据时考虑虚拟滚动或分页
3. **用户体验**: 合理使用优先级和状态类型，提供清晰的信息层次
4. **操作反馈**: 为用户操作提供明确的反馈和确认

## 在项目中的使用

目前在以下页面中使用：
- **Dashboard.vue**: 球队动态展示
- **TransferMarket.vue**: 可集成转会动态
- **Matches.vue**: 可集成比赛事件时间轴

根据不同的业务场景，选择合适的时间轴组件来展示相关信息。 