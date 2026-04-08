# 闪电超级联赛 - UI 设计规范

## 1. 设计概述

**风格定位**：科技运动风 (Tech-Sport)  
**核心关键词**：专业、现代、沉浸、动感  
**参考方向**：Football Manager、EA FC 的数据呈现风格

---

## 2. 色彩系统

### 2.1 品牌色

| 色彩 | 色值 | 用途 |
|------|------|------|
| **深空黑** | `#0A0A0F` | 主背景 |
| **闪电蓝** | `#3B82F6` | 品牌主色、按钮、强调 |
| **草场绿** | `#059669` | 足球元素、成功状态 |

### 2.2 中性色阶

| 色值 | Token | 用途 |
|------|-------|------|
| `#0A0A0F` | `bg-primary` | 页面背景 |
| `#12121A` | `bg-secondary` | 卡片背景 |
| `#1E1E2D` | `bg-tertiary` | 悬停/选中状态 |
| `#2D2D44` | `border` | 边框、分隔线 |
| `#4B4B6A` | `text-muted` | 次要文字、禁用 |
| `#8B8BA7` | `text-secondary` | 辅助说明 |
| `#E2E2F0` | `text-primary` | 主要文字（高对比） |

### 2.3 强调色阶

```
Blue (品牌):
  #93C5FD (300) - 微光装饰
  #60A5FA (400) - 悬停高亮
  #3B82F6 (500) - 主品牌色 ★
  #1D4ED8 (700) - 按下/深强调

Green (足球/成功):
  #34D399 (400) - 悬停
  #10B981 (500) - 草地/进攻
  #059669 (600) - 成功状态 ★
  #065F46 (800) - 稳重
```

### 2.4 功能色

| 色值 | 用途 |
|------|------|
| `#EF4444` | 错误、警告、负向指标 |
| `#F59E0B` | 警告、注意、门将位置 |
| `#FCD34D` | VIP、金币、特殊奖励 |
| `#6366F1` | 链接、特殊功能 |

---

## 3. 字体系统

### 3.1 字体族

| 用途 | 字体 | 备选 |
|------|------|------|
| 标题/正文 | `Inter` | `SF Pro Display`, `Noto Sans SC` |
| 数据/数字 | `Roboto Mono` | `JetBrains Mono` |

### 3.2 字号规范

| Token | 尺寸 | 用途 |
|-------|------|------|
| `text-xs` | 12px | 标签、徽章 |
| `text-sm` | 14px | 辅助文字 |
| `text-base` | 16px | 正文 |
| `text-lg` | 18px | 小标题 |
| `text-xl` | 20px | 面板标题 |
| `text-2xl` | 24px | 页面标题 |
| `text-3xl` | 30px | 大数字（比分）|
| `text-4xl` | 36px | 品牌标题 |

### 3.3 数字展示

```css
.stat-number {
  font-family: 'Roboto Mono', monospace;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
}
```

---

## 4. 间距系统

基于 4px 基准的间距体系：

| Token | 值 | 用途 |
|-------|-----|------|
| `space-1` | 4px | 紧凑间距 |
| `space-2` | 8px | 元素内边距 |
| `space-3` | 12px | 小间隙 |
| `space-4` | 16px | 标准间距 ★ |
| `space-6` | 24px | 卡片内边距 |
| `space-8` | 32px | 区块间距 |

### 布局规范

```
--container-max: 1440px
--sidebar-width: 240px
--card-padding: 24px
--card-gap: 16px
```

---

## 5. 圆角规范

| Token | 值 | 用途 |
|-------|-----|------|
| `radius-sm` | 6px | 小按钮、标签 |
| `radius-md` | 8px | 按钮、输入框 ★ |
| `radius-lg` | 12px | 卡片、面板 ★ |
| `radius-xl` | 16px | 大卡片、弹窗 |
| `radius-full` | 9999px | 圆形元素 |

---

## 6. 组件风格

### 6.1 卡片 (Glassmorphism)

```css
.card {
  background: rgba(18, 18, 26, 0.9);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  box-shadow: 
    0 4px 6px rgba(0, 0, 0, 0.3),
    0 0 0 1px rgba(59, 130, 246, 0.1);
}

.card-hover:hover {
  border-color: rgba(59, 130, 246, 0.3);
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
}
```

### 6.2 按钮

**主按钮**:
```css
.btn-primary {
  background: linear-gradient(135deg, #3B82F6, #2563EB);
  color: white;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}
```

**次级按钮**:
```css
.btn-secondary {
  background: transparent;
  border: 1px solid #2D2D44;
  color: #E2E2F0;
}
.btn-secondary:hover {
  border-color: #3B82F6;
  background: rgba(59, 130, 246, 0.1);
}
```

### 6.3 输入框

```css
.input {
  background: #0A0A0F;
  border: 1px solid #2D2D44;
  border-radius: 8px;
  padding: 10px 16px;
  color: #E2E2F0;
}
.input:focus {
  border-color: #3B82F6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}
```

### 6.4 位置徽章

| 位置 | 背景色 | 文字色 |
|------|--------|--------|
| GK (门将) | `#F59E0B` | `#000000` |
| DF (后卫) | `#3B82F6` | `#FFFFFF` |
| MF (中场) | `#059669` | `#FFFFFF` |
| FW (前锋) | `#EF4444` | `#FFFFFF` |

### 6.5 状态徽章

```css
/* 健康 */
.status-active {
  background: rgba(5, 150, 105, 0.2);
  color: #34D399;
  border: 1px solid rgba(5, 150, 105, 0.3);
}

/* 受伤 */
.status-injured {
  background: rgba(239, 68, 68, 0.2);
  color: #F87171;
  border: 1px solid rgba(239, 68, 68, 0.3);
}
```

---

## 7. 动效规范

### 7.1 时间函数

```css
--transition-fast: 150ms;
--transition-normal: 250ms;
--transition-slow: 350ms;
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);
```

### 7.2 关键动效

| 场景 | 效果 | 时长 |
|------|------|------|
| 卡片悬停 | 上浮 4px + 阴影加深 | 250ms |
| 按钮悬停 | 亮度提升 + 阴影扩散 | 200ms |
| 页面切换 | 淡入淡出 | 300ms |
| 比分更新 | 缩放脉冲 1.0 → 1.1 → 1.0 | 400ms |
| 进球特效 | 金色闪光 + 缩放 | 600ms |

---

## 8. 页面氛围

### 8.1 首页 (Hero)
- 全屏深色背景视频/动图（球场灯光）
- 品牌文字带蓝色光晕 `text-shadow: 0 0 40px rgba(59, 130, 246, 0.5)`
- CTA 按钮蓝色渐变 + 微妙脉冲动画

### 8.2 主界面 (Dashboard)
- 左侧深色导航栏，选中项蓝色高亮
- 玻璃拟态卡片展示数据
- 关键数字使用等宽字体

### 8.3 战术板
- 深绿渐变球场背景 + 白线
- 球员按位置颜色区分（蓝/绿/红）
- 选中球员发光效果

---

## 9. Tailwind 配置参考

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0A0A0F',
          secondary: '#12121A',
          tertiary: '#1E1E2D',
        },
        border: '#2D2D44',
        brand: {
          blue: '#3B82F6',
          green: '#059669',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'sans-serif'],
        mono: ['Roboto Mono', 'monospace'],
      },
    }
  }
}
```

---

*文档版本：v1.0*  
*最后更新：2026-04-09*
