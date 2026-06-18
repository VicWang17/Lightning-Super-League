# LSL 前端 UI 统一化改造方案

> 背景：随着各模块功能快速迭代，前端页面出现了标签页样式不一致、卡片/面板实现分散、色彩 token 漂移、标题层级冗余等问题。本报告对现状进行完整定位，并提出以「半透明毛玻璃边框」为核心的一套统一设计系统与迁移方案。

---

## 1. 目标与范围

### 1.1 目标

- **统一视觉语言**：所有业务页面使用同一套标签、面板、色彩与标题规范。
- **统一组件实现**：停止「每个页面各自写一套 tab/card」的做法，收敛到共享组件。
- **提升沉浸感**：利用已铺设的页面背景图，将内容面板统一为半透明毛玻璃质感，降低厚重边框带来的割裂感。
- **消除冗余信息**：tab 标签、页面标题、内容区小标题三者职责清晰，不再互相重复。

### 1.2 范围

- **包含**：`MainLayout` 内的所有业务页面（Dashboard、Team、Training、League、Cup、World、Transfer、Youth、Finance、Match、Mail、Players）。
- **可兼容但暂不动**：`Home`（营销落地页）、`Auth`（登录注册），可后续按同一 token 系统轻度对齐。
- **不包含**：顶部全局导航 `TopNav` 与 `Header` 的交互结构，仅统一其视觉 token。

---

## 2. 现状问题定位

### 2.1 标签页实现混乱

目前至少存在 **4 种二级标签页样式**，玩家在不同页面会感受到明显的「换皮肤」：

| 样式 | 使用页面 | 视觉特征 | 主要问题 |
|------|---------|---------|---------|
| **Pill（实心药丸）** | `TrainingTabs`、`Team/Detail`、`World/Index`、`League/Detail` | 矩形粗边框，active 填充 `#C6F135` 或 `#0D7377` | 同一形状下 active 色不统一；与毛玻璃方向不符 |
| **Underline（下划线）** | `PlayerTabs`、`Transfer`、`Finance`、`Team/Tactics` | `border-b-2` 下划线，active 高亮文字+底部边框 | 视觉重量太轻，像链接而非切换器；active 色 `#C6F135` / `#0D7377` 不一致 |
| **Bookmark（书签格）** | `Team/PlayerDetail` | 自定义 CSS 网格 + `is-active` 类 | 完全独立，无法复用 |
| **Filter Pills（过滤按钮）** | `League/Index`、`Cup/Index` | 与 Pill 类似但 active 为 `#0D7377` | 职责模糊，是过滤还是导航？ |

**关键文件**：
- `frontend/src/pages/Training/components/TrainingTabs.tsx`（Pill）
- `frontend/src/components/players/PlayerTabs.tsx`（Underline）
- `frontend/src/pages/Team/PlayerDetail.tsx`（Bookmark，行 408–422）
- `frontend/src/pages/Team/Tactics.tsx`（Underline，行 1958–1974）
- `frontend/src/pages/Transfer/Market.tsx` / `Finance/Overview.tsx`（Underline，active `#0D7377`）

### 2.2 卡片/面板实现分散

内容承载层至少存在 **3 套体系**：

| 体系 | 使用场景 | 特征 | 问题 |
|------|---------|------|------|
| **全局 `.card` 类** | `World/Index` tab 内容、`Transfer/History` 统计卡片 | `bg-[#12121A] border-2 border-[#2D2D44] p-6` + 四角 `#B8E532` 装饰 + 投影 | 与 `<Card>` 组件重复；四角装饰在部分页面会显杂乱 |
| **`<Card>` 组件** | `Players/*`、`Training/History`、部分 Team 页面 | `bg-[#12121A] border-2 border-[#2D2D44]`，无四角装饰、有 `glass/outlined` 变体但很少用 | 与 `.card` 类不同步；`glass` 变体几乎没启用 |
| **自定义 CSS 面板** | `Team/Detail`（`locker-board`）、`Training/*`（`.training-panel`）、`Team/Tactics`（棕色边框）、`Dashboard`（`pixel-panel`） | 各自使用独立类名与 token | 无法系统维护；新增页面不知道抄哪套 |

**关键文件**：
- `frontend/src/styles/globals.css` 行 608–630（`.card`）
- `frontend/src/components/ui/Card.tsx`
- `frontend/src/styles/training-system.css`
- `frontend/src/pages/Team/Detail.tsx` 行 397–401（`locker-board`）

### 2.3 色彩 token 严重漂移

同一语义在不同页面使用不同色值，导致品牌感被削弱：

| 语义 | 当前色值 | 出现位置 |
|------|---------|---------|
| 主强调色 | `#C6F135` | TrainingTabs、World、Team Detail、PlayerTabs |
| 主强调色 | `#0D7377` | Cup Detail active tab、Finance/Transfer tabs、League Index filters |
| 主强调色 | `#D5B15E` / `#E8C84A` | Tactics、PlayerDetail |
| 主强调色 | `#9ECF45` / `#CDEB7B` | Dashboard |
| 卡片背景 | `#12121A` | `.card`、`<Card>`、League/Cup |
| 卡片背景 | `#0D0B07` / `#15110A` | Tactics |
| 卡片背景 | `#07080A` | Dashboard |
| 边框色 | `#2D2D44` | 默认卡片 |
| 边框色 | `#3B3425` | Tactics |
| 边框色 | `#242832` | Dashboard |

**根因**：`--skin-*` 与 `--tr-*` CSS 变量仅在少数页面使用，多数组件直接写死 Tailwind 色值，`tailwind.config.js` 中定义的 `background / border / text` token 也未被充分利用。

### 2.4 标题层级冗余

存在三类重复：

1. **Tab 标签 vs 页面标题重复**
   - `Training/Progress.tsx` 页面标题「成长曲线」与 `TrainingTabs` 标签「成长曲线」完全一致。
   - `Training/History.tsx` 页面标题「训练历史」与标签「历史」语义重复。
2. **Tab 标签 vs 内容区小标题重复**
   - `World/Index.tsx` tab「球队排名」对应内容区 `<h3>球队世界排名</h3>`（行 522）。
   - 此前 `League/Detail` / `Cup/Detail` 各 tab 内容区也存在同类问题，已修复。
3. **Page H1 vs TopNav 重复**
   - TopNav 已显示「转会」，但 `Transfer/*` 各子页面 H1 仍为「转会市场」。
   - TopNav「董事会」vs `Finance/*` H1「财务中心」。
   - TopNav「青训」vs `Youth/Academy.tsx` H1「青训营」。
   - TopNav「赛程」vs `Match/Schedule.tsx` H1「赛程安排」。

> 说明：Page H1 与 TopNav 的重复是「模块名重复」，信息价值低；建议 H1 改为具体页面上下文（例如实体名称、功能副标题），而不是再次念一遍模块名。

### 2.5 页面扫描速查表

| 页面 | 标签样式 | 面板/卡片 | 标题冗余 | 备注 |
|------|---------|----------|---------|------|
| `Dashboard/Index` | 无 | `pixel-panel` 自定义 | 无 | 已自成风格，建议统一为 GlassCard |
| `Team/Detail` | Pill | `locker-board` / `.card` 混用 | 无 | 更衣室 tab 内容仍需去边框 |
| `Team/PlayerDetail` | Bookmark | 自定义 `profile-panel` | 能力/档案 tab 内容有重叠标题 | 最需改造 |
| `Team/Tactics` | Underline | 棕色边框面板 | 无 | 主题色独立，建议用 theme override 保留 |
| `Training/Weekly` | Pill（直接引用 TrainingTabs） | `.training-panel` | 无标题 | 未包入 `TrainingPageShell` |
| `Training/Calendar/Fatigue` | Pill（经 PageShell） | `.training-panel` | 无 | 与 Weekly 风格不一致 |
| `Training/History` | Pill（经 PageShell） | `<Card>` | 标题「训练历史」与 tab「历史」重复 | 卡片体系不一致 |
| `Training/Progress` | Pill（经 PageShell） | 硬编码容器 | 标题「成长曲线」与 tab 重复 | 未使用 Card |
| `League/Index` | 过滤 Pill | 自定义卡片 | 无 | 卡片可统一 |
| `League/Detail` | Pill | 无外层卡片 | 已修复 | active `#C6F135` |
| `Cup/Index` | 过滤 Pill | 自定义卡片 | 无 | 卡片可统一 |
| `Cup/Detail` | Pill | 无外层卡片 | 已修复 | active `#0D7377`，与 League 不一致 |
| `World/Index` | Pill | `.card` | tab「球队排名」与 h3「球队世界排名」重复 | 四角装饰与 League/Cup 不一致 |
| `Transfer/*` | Underline | `<Card>` / `.card` | H1「转会市场」重复 | active `#0D7377` |
| `Finance/*` | Underline | `.card` | H1「财务中心」重复 | active `#0D7377` |
| `Youth/Academy` | 无（只有跳转按钮） | `.card` | H1「青训营」重复 | 需补 tab |
| `Match/*` | 无 | 自定义 | H1 与 TopNav 重复 | 可轻度对齐 |
| `Mail/Index` | 左侧过滤 Pill | 自定义 | 无 | 左右布局可保留，面板统一为玻璃 |
| `Players/*` | Underline（PlayerTabs） | `<Card>` | 无页面标题 | 缺少 PageHeader |

---

## 3. 根因分析

1. **缺少强制落地的 Design System**：`design/UI-DESIGN.md` 定义了颜色，但没有给出可执行的组件规范，导致开发者各自实现。
2. **组件与工具类重复**：`.card`（CSS）和 `<Card>`（React）并存且细节不同，新人不知道用哪个。
3. **页面背景与内容面板风格脱节**：近期为 `game-shell` 各路由增加了背景图，但内容面板仍是厚重 opaque 卡片，视觉层次混乱。
4. **Tab 组件没有统一出口**：每个页面按当时心情选择 Pill 或 Underline，没有「唯一正确答案」。
5. **Title 规范缺失**：没有文档说明 TopNav / PageHeader / Tab / Section Title 四层分别该写什么。

---

## 4. 设计系统方案

### 4.1 设计原则

1. **一套标签**：所有二级切换统一为「玻璃分段标签（Glass Segmented Tabs）」。
2. **一套面板**：所有内容承载统一为 `GlassCard`（半透明毛玻璃）/ `SolidCard`（实色）/ `OutlinedCard`（透明边框）三种变体。
3. **一套 Token**：颜色、边框、阴影全部收敛到 CSS 变量 + Tailwind theme；硬编码色值仅允许出现在 token 定义处。
4. **标题只出现一次**：TopNav 负责模块入口，PageHeader 负责页面上下文，Tabs 负责切换，内容区不再重复 tab 名。
5. **保留像素足球特色**：直角、粗边框、像素投影、硬边切角；玻璃质感通过 `backdrop-blur` + 半透明边框实现，而非圆角或渐变遮罩。

### 4.2 色彩与 Token 规范

以现有 `tailwind.config.js` 为基础，扩展语义化 token，并在 `:root` 提供 CSS 变量，方便 `backdrop-blur` 与透明度场景。

```css
/* frontend/src/styles/ui-tokens.css */
:root {
  /* 背景 */
  --ui-bg-base: #050609;
  --ui-bg-page: #0A0A0F;
  --ui-surface-solid: #12121A;
  --ui-surface-hover: #1E1E2D;

  /* 毛玻璃（新核心） */
  --ui-surface-glass: rgba(10, 10, 15, 0.72);
  --ui-surface-glass-hover: rgba(18, 18, 26, 0.82);
  --ui-glass-border: rgba(255, 255, 255, 0.10);
  --ui-glass-border-strong: rgba(255, 255, 255, 0.16);

  /* 边框 */
  --ui-border-subtle: #2D2D44;
  --ui-border-strong: #3B3B55;

  /* 强调色 */
  --ui-accent: #C6F135;          /* 默认：草场荧光绿 */
  --ui-accent-secondary: #0D7377; /* 闪电青，用于次要强调 */
  --ui-accent-glow: rgba(198, 241, 53, 0.35);

  /* 文字 */
  --ui-text-primary: #E2E2F0;
  --ui-text-secondary: #8B8BA7;
  --ui-text-muted: #4B4B6A;

  /* 阴影 */
  --ui-shadow-pixel: 4px 4px 0 rgba(0, 0, 0, 0.45);
}
```

页面级主题覆盖（保留少数模块个性，但结构统一）：

```css
[data-ui-theme="tactics"] {
  --ui-accent: #D5B15E;
  --ui-surface-glass: rgba(13, 11, 7, 0.78);
  --ui-glass-border: rgba(255, 255, 255, 0.08);
}
[data-ui-theme="cup"] {
  --ui-accent: #63B3FF;
}
```

Tailwind 扩展：

```js
// tailwind.config.js
colors: {
  surface: {
    DEFAULT: 'var(--ui-surface-solid)',
    glass: 'var(--ui-surface-glass)',
    hover: 'var(--ui-surface-hover)',
  },
  glass: {
    border: 'var(--ui-glass-border)',
    'border-strong': 'var(--ui-glass-border-strong)',
  },
  accent: {
    DEFAULT: 'var(--ui-accent)',
    secondary: 'var(--ui-accent-secondary)',
    glow: 'var(--ui-accent-glow)',
  },
  // 复用已有的 background / border / text
}
```

### 4.3 布局框架

保留 `MainLayout` 的页面背景与 `max-w-[1400px]` 容器，新增三层结构：

```
PageShell
├── PageHeader        # icon + title + subtitle + action
├── SegmentedTabs     # 若页面有二级 tab
└── PageContent       # 内容区，内部使用 GlassCard/SolidCard/OutlinedCard
```

#### PageHeader

```tsx
// frontend/src/components/ui/PageHeader.tsx
interface PageHeaderProps {
  icon?: React.ComponentType<{ className?: string }>
  title: string
  subtitle?: string
  action?: React.ReactNode
}

export function PageHeader({ icon: Icon, title, subtitle, action }: PageHeaderProps) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div className="flex items-center gap-3">
        {Icon && <Icon className="w-7 h-7 text-accent" />}
        <div>
          <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
          {subtitle && <p className="text-sm text-text-secondary mt-1">{subtitle}</p>}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
```

> 标题规则：
> - 列表页：用模块功能名，如「联赛体系」「杯赛一览」「世界排名」。
> - 详情页：用实体名，如 `{league.name}`、`{cup.name}`、`{player.name}`。
> - 避免再用「联赛」「杯赛」「财务中心」这种与 TopNav 完全同义的词作为 H1。

#### SegmentedTabs

统一所有二级切换的视觉：

```tsx
// frontend/src/components/ui/SegmentedTabs.tsx
import { NavLink, useLocation } from 'react-router-dom'
import { clsx } from 'clsx'

export interface SegmentedTab {
  path?: string
  value?: string
  label: string
  icon?: React.ComponentType<{ className?: string }>
}

interface SegmentedTabsProps {
  tabs: SegmentedTab[]
  value?: string
  onChange?: (value: string) => void
  mode?: 'route' | 'state'
}

export function SegmentedTabs({ tabs, value, onChange, mode = 'state' }: SegmentedTabsProps) {
  // route 模式用 NavLink；state 模式用 button + onChange
  return (
    <nav className="flex flex-wrap gap-2 mb-6">
      {tabs.map((tab) => {
        const Icon = tab.icon
        const active = mode === 'route'
          ? useLocation().pathname === tab.path
          : value === tab.value
        const base = 'px-4 py-2 text-sm font-medium border-2 transition-all flex items-center gap-2'
        const inactive =
          'bg-surface-glass/40 border-glass-border text-text-secondary hover:border-glass-border-strong hover:text-text-primary'
        const activeCls =
          'bg-accent/10 border-accent text-accent shadow-[0_0_16px_var(--ui-accent-glow)]'
        return (
          <button
            key={tab.value ?? tab.path}
            className={clsx(base, active ? activeCls : inactive)}
            onClick={() => mode === 'state' && onChange?.(tab.value!)}
          >
            {Icon && <Icon className="w-4 h-4" />}
            {tab.label}
          </button>
        )
      })}
    </nav>
  )
}
```

视觉特征：
- 直角、2px 边框。
- inactive：半透明深底 + 半透明白边框，hover 边框变亮。
- active：accent 色边框 + accent/10 底色 + 微 glow，不使用实心填充，避免与玻璃主题冲突。

#### GlassCard / SolidCard / OutlinedCard

重构 `<Card>` 组件，废弃全局 `.card` 类：

```tsx
// frontend/src/components/ui/Card.tsx
const variants = {
  glass:
    'bg-surface-glass backdrop-blur-sm border-2 border-glass-border shadow-pixel',
  solid:
    'bg-surface border-2 border-border-subtle shadow-pixel',
  outlined:
    'bg-transparent border-2 border-border-subtle',
}

const paddings = { none: '', sm: 'p-4', md: 'p-6', lg: 'p-8' }
```

- **glass（默认）**：列表、表格、图表、详情面板。
- **solid**：需要强对比的统计 KPI、操作按钮组。
- **outlined**：占位、空状态、轻量分组。

如果需要四角像素装饰，统一作为可选 `corners` prop 实现，而不是全局 `.card::before/::after`，避免与玻璃风格冲突。

### 4.4 标签页与标题层级约定

| 层级 | 组件/元素 | 应该写什么 | 不应该写什么 |
|------|----------|-----------|-------------|
| L1 模块入口 | `TopNav` | 模块简称：办公室、更衣室、训练、联赛… | 不要写长标题 |
| L2 页面上下文 | `PageHeader` | 功能/实体名称，可带一句副标题 | 不要重复 L1 的模块名 |
| L3 内容切换 | `SegmentedTabs` | 当前页面下的子视图 | 标签名不要与 L2 标题重复 |
| L4 内容区 | `GlassCard` 内部 | 过滤、工具栏、列表、图表 | 不要再用 h2/h3 重复当前 tab 标签 |

### 4.5 分页面改造路线

#### 4.5.1 训练模块

- `TrainingPageShell` 保留，但内部改为 `PageHeader` + `SegmentedTabs`。
- `Training/Weekly.tsx` 必须包入 `TrainingPageShell`，消除「只有 Weekly 没有 hero」的问题。
- `Training/History.tsx`：卡片从 `<Card>` 改为 `GlassCard`；页面标题从「训练历史」改为「训练执行统计」，避免与 tab「历史」重复。
- `Training/Progress.tsx`：页面标题从「成长曲线」改为「球员成长曲线对比」或去掉标题仅保留 tab；所有硬编码容器替换为 `GlassCard`。
- `Training/Calendar.tsx` / `Fatigue.tsx`：`.training-panel` 统一为 `GlassCard`。
- 保留 `.training-system.css` 中的背景与 hero 结构，但 hero 与 panel 使用新 token。

#### 4.5.2 球队模块

- `Team/Detail.tsx`：
  - 用 `PageShell` + `SegmentedTabs` 替换当前手写 pill tabs。
  - 移除 `locker-board` / `locker-layout` 等自定义面板，统一用 `GlassCard`。
  - 历史 tab 的裸表格包入 `GlassCard`。
- `Team/PlayerDetail.tsx`：
  - 移除 `dossier-bookmarks` 自定义 tab，改用 `SegmentedTabs`。
  - 自定义 `profile-panel`、`intel-panel` 等统一为 `GlassCard`。
  - 调整「能力」与「档案」tab 的内容边界，避免能力概览重复。
- `Team/Tactics.tsx`：
  - 保留战术板独立视觉，但将外围 tab、面板、滑块容器统一为 glass，通过 `data-ui-theme="tactics"` 覆盖 accent 为金色。
  - 替换 underline tab 为 `SegmentedTabs`。

#### 4.5.3 联赛 / 杯赛 / 世界

- `League/Detail.tsx` / `Cup/Detail.tsx`：
  - tab 统一为 `SegmentedTabs`。
  - active accent 统一为 `--ui-accent`（荧光绿）；若希望杯赛个性，用 `data-ui-theme="cup"` 覆盖，不要局部写死 `#0D7377`。
  - tab 内容 wrapper 统一用 `GlassCard`（或去掉 `World` 的 `.card` 四角装饰，保持三者一致）。
- `League/Index.tsx` / `Cup/Index.tsx`：
  - 列表卡片统一为 `GlassCard`（hover 变体）。
  - 顶部过滤 pills 若本质是导航，改为 `SegmentedTabs`；若只是过滤，保持但样式与 `SegmentedTabs` 一致。
- `World/Index.tsx`：
  - 移除 tab 内容区的 `.card` 四角装饰，改用 `GlassCard`。
  - 移除「球队世界排名」等小标题与 tab 重复的文字。

#### 4.5.4 转会 / 财务 / 青训

- 所有子页面增加 `PageHeader`，H1 使用具体上下文而非模块名。
- 子导航从 underline 改为 `SegmentedTabs`。
- 统计 KPI 与表格统一用 `GlassCard` / `SolidCard`。

#### 4.5.5 比赛 / 邮件 / 仪表盘

- `Match/*`：统一 panel 为 `GlassCard`，标题改为具体功能（如「本轮赛程」）。
- `Mail/Index.tsx`：左右布局保留，侧边栏与邮件列表面板统一为 glass。
- `Dashboard/Index.tsx`：将 `pixel-panel` 等自定义面板逐步迁移到 `GlassCard`。

#### 4.5.6 球员中心

- `Players/*`：增加 `PageHeader`（标题为球员名），`PlayerTabs` 替换为 `SegmentedTabs`。

---

## 5. 迁移优先级与节奏

建议按以下顺序推进，避免一次性大面积冲突：

| 阶段 | 时间 | 内容 | 风险 |
|------|------|------|------|
| **Phase 1：基础层** | 3–4 天 | 新建 `ui-tokens.css`、扩展 Tailwind、实现 `PageHeader`、`SegmentedTabs`、`GlassCard` | 低 |
| **Phase 2：低风险页面** | 5–7 天 | 改造 `League/Index`、`Cup/Index`、`World/Index`、`Transfer/*`、`Finance/*`、`Youth/*`、`Match/*` | 中 |
| **Phase 3：中风险页面** | 5–7 天 | 改造 `Team/Detail`、`Training/History`、`Training/Progress`、`Players/*` | 中 |
| **Phase 4：高风险页面** | 7–10 天 | 改造 `Team/PlayerDetail`、`Team/Tactics`、`Training/Weekly`、`Dashboard` | 高 |
| **Phase 5：收尾** | 2–3 天 | 删除 `.card` 全局类与旧 CSS、删除废弃自定义类、更新 `design/UI-DESIGN.md`、视觉回归 | 中 |

---

## 6. 实施检查清单

- [ ] 新增 `frontend/src/styles/ui-tokens.css` 并在 `main.tsx` 引入。
- [ ] 扩展 `tailwind.config.js` 的 `colors` 与 `boxShadow`。
- [ ] 实现 `PageHeader`、`SegmentedTabs`、`GlassCard`。
- [ ] 所有二级 tab 切换均使用 `SegmentedTabs`，不再手写 pill/underline/bookmark。
- [ ] 所有内容面板均使用 `GlassCard` / `SolidCard` / `OutlinedCard`，不再使用 `.card` 全局类或自定义面板类。
- [ ] 移除 tab 内容区与 tab 标签同名的 h2/h3。
- [ ] 页面 H1 不再与 `TopNav` 模块名简单重复（详情页用实体名，列表页用功能名）。
- [ ] 删除 `frontend/src/styles/globals.css` 中的 `.card`、`.card-hover` 及四角装饰。
- [ ] 删除 `locker-board`、`dossier-bookmarks`、`pixel-panel` 等迁移后不再使用的自定义类（或确认仅 Dashboard 保留至 Phase 4）。
- [ ] 更新 `design/UI-DESIGN.md`，将本方案中的 token 与组件规范纳入。
- [ ] 跑通 `npm run build` 与关键页面人工走查。

---

## 7. 代码示例（规范参考）

### 7.1 一个标准化页面

```tsx
// League/Detail.tsx 改造后结构示例
import { PageShell } from '@/components/ui/PageShell'
import { PageHeader } from '@/components/ui/PageHeader'
import { SegmentedTabs } from '@/components/ui/SegmentedTabs'
import { GlassCard } from '@/components/ui/Card'

const TABS = [
  { value: 'standings', label: '积分榜', icon: TrendingUp },
  { value: 'fixtures', label: '赛程', icon: Calendar },
  { value: 'stats', label: '数据', icon: BarChart },
  { value: 'records', label: '纪录', icon: Award },
]

export default function LeagueDetail() {
  const [tab, setTab] = useState('standings')

  return (
    <PageShell>
      <PageHeader
        icon={Trophy}
        title={league.name}
        subtitle={`${league.system_name} · ${league.season_name}`}
      />
      <SegmentedTabs tabs={TABS} value={tab} onChange={setTab} />
      <GlassCard>
        {tab === 'standings' && <Standings />}
        {tab === 'fixtures' && <Fixtures />}
        {tab === 'stats' && <Stats />}
        {tab === 'records' && <RecordsBoard />}
      </GlassCard>
    </PageShell>
  )
}
```

### 7.2 一个路由型 Tab 页面

```tsx
// Transfer/Market.tsx 改造后结构示例
const NAV = [
  { path: '/transfer/market', label: '球员市场' },
  { path: '/transfer/free', label: '自由市场' },
  { path: '/transfer/watchlist', label: '关注列表' },
  { path: '/transfer/my-offers', label: '我的报价' },
  { path: '/transfer/my-listings', label: '我的挂牌' },
  { path: '/transfer/history', label: '转会历史' },
]

<PageShell>
  <PageHeader
    icon={ArrowLeftRight}
    title="球员市场"
    subtitle="浏览球员并发送转会报价"
  />
  <SegmentedTabs tabs={NAV} mode="route" />
  <GlassCard>{/* table / list */}</GlassCard>
</PageShell>
```

### 7.3 玻璃卡片使用

```tsx
// 统计 KPI：需要强对比
<SolidCard>
  <div className="text-sm text-text-secondary">总支出</div>
  <div className="text-2xl font-bold text-red-400 stat-number">1200 万</div>
</SolidCard>

// 列表/表格：默认玻璃
<GlassCard>
  <h3 className="text-lg font-semibold mb-4">转会记录</h3>
  {/* ... */}
</GlassCard>

// 空状态/占位
<OutlinedCard className="py-12 text-center text-text-secondary">
  暂无数据
</OutlinedCard>
```

---

## 8. 风险与回退

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 改造 `Tactics`/`Training Weekly` 时可能破坏复杂布局 | 高 | 按 Phase 4 单独排期，改动前截图对比；保留原 CSS 类名做 fallback，确认无误后再删除 |
| 统一 tab active 色后，某些页面个性消失 | 中 | 通过 `data-ui-theme` 做页面级 accent 覆盖，不影响组件实现 |
| 玻璃面板在低端设备或旧浏览器上性能/兼容性问题 | 低 | `backdrop-blur` 作为渐进增强，不支持时自动回退到半透明实色 |
| 与正在进行的功能开发冲突 | 中 | 采用「新增组件 → 逐页替换」策略，不直接改旧组件签名，降低合并冲突 |
| 删除 `.card` 全局类影响未覆盖页面 | 中 | 全局搜索 `.card` 与 `card` 字符串，确认全部替换后再删除；可先弃用警告 |

---

## 9. 结论

当前 LSL 前端的核心问题不是「丑」，而是**缺乏统一的设计系统执行层**：同样的 tab 和卡片被重复实现了多次，颜色和边框各自为政，标题层级也没有约束。

本方案建议：
1. 以 **半透明毛玻璃卡片 + 玻璃分段标签** 统一所有二级页面；
2. 以 **CSS 变量 + Tailwind token** 统一色彩；
3. 以 **PageHeader / SegmentedTabs / GlassCard** 三个组件统一页面结构；
4. 以 **标题层级约定** 消除冗余标题。

按 Phase 1→5 逐步推进，可在 3–4 周内完成全站视觉统一，同时保持像素足球的硬核风格。
