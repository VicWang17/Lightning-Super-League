# 闪电超级联赛 - UI 设计规范

## 1. 设计概述

**风格定位**：科技运动风 × 像素艺术 (Tech-Sport Pixel)  
**核心关键词**：专业、现代、沉浸、动感、复古像素  
**参考方向**：Football Manager 的数据呈现 + 经典像素游戏的视觉语言

> 本项目采用 **像素艺术 (Pixel Art)** 作为核心视觉语言，所有 UI 元素（卡片、按钮、边框、进度条）均带有硬边像素特征，与足球经理游戏的策略深度形成独特反差美学。

---

## 2. 色彩系统

### 2.1 品牌色

| 色彩 | 色值 | 用途 |
|------|------|------|
| **深空黑** | `#0A0A0F` | 主背景 |
| **闪电青** | `#0D7377` | 品牌主色、按钮、强调（像素风核心色）|
| **草场绿** | `#059669` | 足球元素、成功状态 |

> **像素设计说明**：主色 `#0D7377` 是一个低饱和度的深青色，在像素边框和 8-bit 风格界面中具有极佳的可读性，避免了高饱和色在像素化后的视觉疲劳。

### 2.2 中性色阶

| 色值 | Token | 用途 |
|------|-------|------|
| `#0A0A0F` | `bg-primary` | 页面背景 |
| `#12121A` | `bg-secondary` | 卡片背景 |
| `#1E1E2D` | `bg-tertiary` | 悬停/选中状态 |
| `#2D2D44` | `border` | 边框、分隔线（2px 硬边）|
| `#4B4B6A` | `text-muted` | 次要文字、禁用 |
| `#8B8BA7` | `text-secondary` | 辅助说明 |
| `#E2E2F0` | `text-primary` | 主要文字（高对比）|

### 2.3 强调色阶

```
Cyan (像素品牌主色):
  #14A085 (青绿) - 按钮角标装饰
  #0D7377 (500) - 主品牌色 ★
  #0A5A5D (700) - 按下/深强调
  #072e30 (900) - 按钮阴影色
  #0D4A4D (dark) - 暗色背景装饰

Green (足球/成功):
  #34D399 (400) - 悬停
  #10B981 (500) - 草地/进攻
  #059669 (600) - 成功状态 ★
  #065F46 (800) - 稳重

Red (危险/进攻):
  #F87171 (400) - 悬停
  #EF4444 (500) - 错误、前锋位置 ★
  #DC2626 (600) - 严重警告
```

### 2.4 功能色

| 色值 | 用途 |
|------|------|
| `#EF4444` | 错误、警告、负向指标、前锋位置 |
| `#F59E0B` | 警告、注意、门将位置 |
| `#FCD34D` | VIP、金币、特殊奖励、导航选中指示 |
| `#6366F1` | 链接、特殊功能 |

---

## 3. 字体系统

### 3.1 字体族

| 用途 | 字体 | 备选 |
|------|------|------|
| 标题/正文 | `Inter` | `SF Pro Display`, `Noto Sans SC` |
| 数据/数字 | `Roboto Mono` | `JetBrains Mono` |
| **像素大标题** | **`Press Start 2P`** | `monospace` |

> **Press Start 2P** 仅用于品牌大标题、比分牌、核心数据展示，正文和 UI 标签保持 Inter 以确保可读性。

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
| `text-4xl` | 36px | 品牌标题（像素字体）|

### 3.3 数字展示

```css
.stat-number {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  font-weight: 600;
}

.pixel-number {
  font-family: 'Press Start 2P', monospace;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.04em;
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

> **像素设计核心原则：不使用圆角（或极小圆角）**。所有元素保持硬边直角，强化像素风格。

| Token | 值 | 用途 |
|-------|-----|------|
| `radius-none` | 0px | **所有卡片、按钮、输入框默认** |
| `radius-sm` | 6px | 极少数圆角标签（尽量不用）|

---

## 6. 组件风格（像素化）

### 6.1 卡片 (Pixel Card)

```css
.card {
  background: #12121A;
  border: 2px solid #2D2D44;
  padding: 24px;
  position: relative;
  box-shadow: 4px 4px 0px rgba(0, 0, 0, 0.5);
}

/* 四角装饰 */
.card::before, .card::after {
  content: '';
  position: absolute;
  width: 6px;
  height: 6px;
  background: #0D7377;
  pointer-events: none;
}
.card::before { top: -2px; left: -2px; }
.card::after { bottom: -2px; right: -2px; }

.card-hover:hover {
  border-color: rgba(13, 115, 119, 0.6);
  box-shadow: 6px 6px 0px rgba(0, 0, 0, 0.6);
  transform: translate(-2px, -2px);
}
```

> 卡片hover时采用 **"像素位移"** 效果：元素向左上方移动 2px，同时阴影加大，模拟 8-bit 游戏中的选中反馈。

### 6.2 按钮 (Pixel Button)

**主按钮**:
```css
.btn-primary {
  background: #0D7377;
  color: white;
  font-weight: bold;
  padding: 12px 24px;
  border: 2px solid #0A5A5D;
  box-shadow: 4px 4px 0px #072e30;
  position: relative;
}

/* 按钮四角高光 */
.btn-primary::before, .btn-primary::after {
  content: '';
  position: absolute;
  width: 4px;
  height: 4px;
  background: #14A085;
}
.btn-primary::before { top: -2px; left: -2px; }
.btn-primary::after { bottom: -2px; right: -2px; }

.btn-primary:hover {
  background: #0A5A5D;
  box-shadow: 6px 6px 0px #072e30;
  transform: translate(-2px, -2px);
}

.btn-primary:active {
  box-shadow: 2px 2px 0px #072e30;
  transform: translate(2px, 2px);
}
```

**次级按钮**:
```css
.btn-secondary {
  background: #1E1E2D;
  color: #E2E2F0;
  border: 2px solid #2D2D44;
  box-shadow: 4px 4px 0px rgba(0, 0, 0, 0.5);
}
```

> **按钮状态设计**：hover 时元素"浮起"（阴影增大+位移），active 时"按下"（阴影减小+反向位移），完全模拟物理按键的像素反馈。

### 6.3 输入框

```css
.pixel-input {
  background: #0A0A0F;
  border: 2px solid #2D2D44;
  color: #E2E2F0;
  padding: 12px 16px;
  outline: none;
}

.pixel-input:focus {
  border-color: #0D7377;
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

### 6.6 像素进度条

```css
.pixel-progress-track {
  width: 100%;
  height: 12px;
  background: #0A0A0F;
  border: 2px solid #2D2D44;
}

.pixel-progress-fill {
  height: 100%;
  background: #0D7377;
  box-shadow: inset -2px -2px 0px rgba(0,0,0,0.2), inset 2px 2px 0px rgba(255,255,255,0.1);
}
```

> 进度条内部有像素风格的内阴影高光，模拟 3D 像素块的立体感。

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
| 卡片悬停 | 上浮 2px + 阴影加大 + 边框变色 | 250ms |
| 按钮悬停 | 阴影扩散 + 位移 -2px,-2px | 200ms |
| 按钮按下 | 阴影收缩 + 位移 +2px,+2px | 100ms |
| 页面切换 | 淡入淡出 | 300ms |
| 比分更新 | 缩放脉冲 1.0 → 1.1 → 1.0 | 400ms |
| 进球特效 | 金色闪光 + 像素抖动 shake | 600ms |
| 像素闪烁 | 两帧闪烁（opacity 1→0）| 1s steps(1) |

### 7.3 像素专属动画

```css
/* 像素闪烁（两帧） */
@keyframes pixel-blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

/* 像素抖动 */
@keyframes pixel-shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-3px); }
  75% { transform: translateX(3px); }
}

/* 扫描线效果 */
.scanlines::after {
  content: '';
  position: absolute;
  inset: 0;
  background: repeating-linear-gradient(
    0deg, transparent, transparent 2px,
    rgba(0,0,0,0.03) 2px, rgba(0,0,0,0.03) 4px
  );
  pointer-events: none;
}
```

---

## 8. 页面氛围

### 8.1 首页 (Hero)
- 全屏深色背景 + 像素网格纹理
- 品牌文字带青色光晕 `text-shadow: 0 0 40px rgba(13, 115, 119, 0.5)`
- CTA 按钮像素风格 + 微妙脉冲动画
- 像素化数据展示（大数字使用 Press Start 2P）

### 8.2 主界面 (Dashboard)
- 左侧深色导航栏，选中项青色高亮 + 像素角标 + ▶ 指示器
- 玻璃拟态卡片（像素硬边版本）展示数据
- 关键数字使用等宽字体 / 像素字体
- 财务快捷看板、工资帽进度条

### 8.3 战术板
- 深绿渐变球场背景 + 白线（像素化线条）
- 球员按位置颜色区分（蓝/绿/红）
- 选中球员发光效果 + 像素边框

### 8.4 训练中心
- 7×3 训练格子矩阵，像素边框
- 当前时段高亮闪烁（pixel-blink）
- 疲劳条使用像素进度条

---

## 9. 全局背景与纹理

### 9.1 像素网格背景

```css
.pixel-grid-bg {
  background-color: #0A0A0F;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.015) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.015) 1px, transparent 1px);
  background-size: 4px 4px;
}
```

### 9.2 像素草地纹理

```css
.pixel-grass-bg {
  background-color: #0A0A0F;
  background-image: repeating-linear-gradient(
    0deg, transparent, transparent 2px,
    rgba(13, 115, 119, 0.03) 2px, rgba(13, 115, 119, 0.03) 4px
  );
}
```

### 9.3 滚动条（像素风）

```css
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0A0A0F; border: 2px solid #1E1E2D; }
::-webkit-scrollbar-thumb { background: #2D2D44; border: 2px solid #0A0A0F; }
::-webkit-scrollbar-thumb:hover { background: #0D7377; }
```

---

## 10. Tailwind 配置参考

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
          cyan: '#0D7377',
          green: '#059669',
          cyanDark: '#0A5A5D',
          cyanShadow: '#072e30',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Noto Sans SC', 'sans-serif'],
        mono: ['Roboto Mono', 'monospace'],
        pixel: ['"Press Start 2P"', 'monospace'],
      },
      boxShadow: {
        'pixel': '4px 4px 0px rgba(0, 0, 0, 0.5)',
        'pixel-lg': '6px 6px 0px rgba(0, 0, 0, 0.6)',
        'pixel-green': '4px 4px 0px #072e30',
        'pixel-green-lg': '6px 6px 0px #072e30',
      },
    }
  }
}
```

---

## 11. 图标系统

本项目使用 **pixelarticons** 作为图标库——一套专门为像素风格设计的 SVG 图标。

**使用方式**：
```tsx
import { Trophy, Users, Sword } from '../ui/pixel-icons'
```

**特点**：
- 所有图标均为 1px 线条宽度的像素风格
- stroke-width 统一为 2.5px，shape-rendering: crispEdges
- 与整体 UI 的硬边像素风格完美融合

**lucide-react 兼容性**：部分 lucide 图标也允许使用，但会自动应用 `shape-rendering: crispEdges` 以匹配像素风格。

---

*文档版本：v2.0*  
*最后更新：2026-04-30*  
*更新说明：全面加入像素艺术 (Pixel Art) 设计规范，统一品牌主色为 `#0D7377` 闪电青，所有组件增加像素硬边、位移阴影、四角装饰等像素特征。*
