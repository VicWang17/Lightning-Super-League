# 训练场页面重构方案（P1 + P2）

> 范围：交互效率、冲突预警、视觉统一、模板反馈、撤销保护

---

## 一、交互效率重构：从「三级点选」到「批量设计」

### 1.1 核心问题
当前路径：`选格子 → 选分组（如有）→ 右侧找训练 → 点卡片`。
21 个格子全部手动设置，效率极低，且 `selectedGroupId` 全局跳动导致误操作。

### 1.2 重构目标
- 支持「先选训练，再批量刷入格子」的反向流程
- 支持拖拽/多选/复制粘贴等批量操作
- 分组模式下的组切换稳定、可预测

### 1.3 具体方案

#### A. 新增「画笔模式（Paint Mode）」
在右侧训练库顶部增加一个开关：

```
[ 画笔模式: 关闭 ▼ ]  ← 默认关闭，即现有行为
```

- **关闭时**：现有行为，点击卡片写入当前选中的格子。
- **开启时**：
  1. 用户先点击一张训练卡片，此时鼠标变为「画笔」状态（cursor: copy），卡片高亮并显示「已选中」。
  2. 用户去左侧计划板「刷」格子：hover 时格子显示该训练的半透明预览，点击即写入。
  3. 连续点击多个格子，无需重复选择训练。
  4. 按 `Esc` 或再次点击卡片取消画笔。

**交互收益**：把 21 次「找训练→点卡片」压缩为 1 次选训练 + 21 次点格子，且避免了右侧滚动。

#### B. 格子多选 + 批量填充
计划板支持 `Ctrl/Cmd + 点击` 多选格子（类似日历多选）。

- 多选时，右侧「时段设置」面板变为「批量设置」面板。
- 批量面板文案：「已选 5 个时段」，操作按钮：「填充当前训练」「清空所选」「复制到下周」。
- 如果所选格子包含比赛日，比赛日自动被排除并给出 toast：「已跳过 1 个比赛日」。

**实现要点**：
```ts
// Weekly.tsx 状态新增
const [multiSelected, setMultiSelected] = useState<Set<string>>(new Set())
const isMultiMode = multiSelected.size > 1

// 点击逻辑
const handleSlotClick = (dayOffset: number, periodIndex: number, event: React.MouseEvent) => {
  const key = `${dayOffset}-${periodIndex}`
  if (event.ctrlKey || event.metaKey) {
    setMultiSelected(prev => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  } else {
    setMultiSelected(new Set([key]))
    setSelectedCell({ dayOffset, periodIndex })
  }
}
```

#### C. 复制粘贴（Ctrl+C / Ctrl+V）
- `Ctrl+C`：复制当前选中格子的内容（训练项 ID、分组映射）。
- `Ctrl+V`：粘贴到当前悬停或选中的格子。
- 跨天粘贴时，分组模式保留组结构，仅替换训练项。

#### D. 分组 Tab 状态绑定到格子
**问题**：`selectedGroupId` 是全局状态，切换格子后分组选择乱跳。
**修复**：将 `selectedGroupId` 改为按格子记忆。

```ts
// 原：const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
// 新：
const [slotGroupSelection, setSlotGroupSelection] = useState<Map<string, string>>(new Map())

const getSlotGroupId = (dayOffset: number, periodIndex: number) => {
  const key = `${dayOffset}-${periodIndex}`
  const cell = getCell(dayOffset, PERIODS[periodIndex].key)
  return slotGroupSelection.get(key) || cell?.groups?.[0]?.group_id || null
}
```

当选中格子时，自动恢复上次在该格子选择的分组，不再乱跳。

---

## 二、冲突预警系统：让训练计划「自带教练」

### 2.1 预警规则表

| 规则 ID | 触发条件 | 前端展示 | 严重级别 |
|---|---|---|---|
| `MATCH_EVE_LOCK` | 比赛日晚间格子自动锁定 | 现有蓝色锁定块，不变 | info |
| `PRE_MATCH_HIGH` | 比赛日前一天安排高强度训练 | 格子左上角显示 ⚠️ 橙色角标，hover 提示「比赛前高强度训练会降低比赛状态」 | warn |
| `DAILY_OVERLOAD` | 同一天 3 个时段累计疲劳变化 > 20 | 该列日期 header 显示 🔥 红色脉冲点，tooltip 显示「当日疲劳累计 +X」 | error |
| `PLAYER_FATIGUE` | 某分组/全队中包含疲劳 > 70 的球员，且训练疲劳 delta > 5 | 训练卡片和对应格子边框显示红色虚线，tooltip 列出受影响球员 | error |
| `NO_RECOVERY` | 连续 3 天无恢复类训练（`is_recovery`） | 周计划板顶部横幅提示「已连续 3 天无恢复训练，伤病风险上升」 | warn |
| `GK_MISMatch` | 分组模式为 groups_3 时，门将组被安排了非门将训练 | 格子内门将组名称显示红色 | warn |

### 2.2 数据结构扩展

```ts
// types/training.ts 新增
export interface TrainingConflict {
  rule_id: string
  level: 'info' | 'warn' | 'error'
  message: string
  affected_slots?: Array<{ dayOffset: number; periodIndex: number }>
  affected_players?: string[] // player_ids
}

// Weekly.tsx 新增计算属性
const conflicts = useMemo(() => {
  const list: TrainingConflict[] = []
  // 逐规则检查...
  return list
}, [localPlan, matchDays, fatigue, items])
```

### 2.3 视觉实现

#### 预警角标（Slot Warning Badge）
在 `training-slot-block` 内部新增：

```tsx
{conflictsForSlot.map(c => (
  <div key={c.rule_id} className={`slot-warning ${c.level}`} title={c.message}>
    {c.level === 'error' ? '!' : '▲'}
  </div>
))}
```

```css
.slot-warning {
  position: absolute;
  top: -1px;
  left: -1px;
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 1000;
  clip-path: polygon(0 0, 100% 0, 0 100%);
}
.slot-warning.warn { background: #D7A94A; color: #050609; }
.slot-warning.error { background: #D75A4A; color: #050609; }
```

#### 当日过载指示（Day Column Header）
在 `training-day-column header` 中，如果该日有 `DAILY_OVERLOAD`：

```tsx
<header>
  <strong>{DAYS[...]}</strong>
  <span>第 {seasonDay} 天</span>
  {dayConflicts.some(c => c.rule_id === 'DAILY_OVERLOAD') && (
    <em className="day-overload-badge">🔥 过载</em>
  )}
</header>
```

#### 训练卡片冲突提示
当用户选中一张训练卡片，若该卡片与当前球队疲劳状态冲突：

在 `TrainingItemCard` 顶部新增：
```tsx
{conflict && (
  <div className="training-item-alert">
    <WarningDiamond className="h-3 w-3" />
    {conflict.message}
  </div>
)}
```

### 2.4 右侧「球员负荷」面板增强

**现状**：只显示前 8 人，无滚动。
**重构**：
1. 改为可滚动完整列表（`max-height: 320px; overflow-y: auto`）。
2. 增加「按当前选中训练筛选」开关：开启后，仅显示会被该训练影响的球员（即其所在分组包含在该时段中）。
3. 每条球员增加 micro 标签：
   - 疲劳 > 70 且训练 fatigue_delta > 0 → 红色 `危险`
   - `can_high_intensity === false` 且训练 intensity === 'hard' → 红色 `不适合`

```tsx
// TrainingFatiguePanel 新增 props
interface FatiguePanelProps {
  fatigue: PlayerFatigueItem[]
  selectedTrainingItem?: TrainingItem | null
  selectedCellGroups?: PlanGroup[] | null
}
```

---

## 三、子页面视觉统一：建立训练场设计体系

### 3.1 问题
Weekly 是重度像素风（850 行自定义 CSS），Calendar/History/Fatigue 是纯 Tailwind，两者像两个游戏。

### 3.2 统一策略：提取「训练场设计令牌」

新建 `frontend/src/styles/training-system.css`，将 Weekly 的视觉资产抽象为令牌，供全部训练子页面复用。

```css
/* === 训练场设计令牌 === */
:root {
  /* 色彩 */
  --tr-bg-deep: #050609;
  --tr-panel: rgba(7, 8, 10, 0.94);
  --tr-border: rgba(79, 91, 104, 0.62);
  --tr-border-strong: rgba(126, 151, 91, 0.42);
  --tr-accent: #B8E532;
  --tr-accent-soft: rgba(184, 229, 50, 0.35);
  --tr-blue: #63B3FF;
  --tr-red: #D75A4A;
  --tr-gold: #D7A94A;
  --tr-cyan: #50D1C8;
  --tr-text: #F4F7DF;
  --tr-muted: #8B9A7E;

  /* 像素风几何 */
  --tr-clip-small: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
  --tr-clip-medium: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
  --tr-shadow: 4px 4px 0 rgba(0,0,0,0.42);
  --tr-grid: linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px),
             linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px);
}
```

### 3.3 统一页面框架

为 Calendar / History / Fatigue 增加与 Weekly 一致的页面框架：

```tsx
// 新建 components/training/TrainingPageShell.tsx
export function TrainingPageShell({
  title,
  subtitle,
  children,
  actionBar,
}: {
  title: string
  subtitle: string
  children: React.ReactNode
  actionBar?: React.ReactNode
}) {
  return (
    <div className="training-console-page">
      <section className="training-hero training-hero--compact">
        <div className="training-hero-copy">
          <div className="training-chip"><span />训练场</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        {actionBar && <div className="training-command-strip">{actionBar}</div>}
      </section>
      <main className="training-body">{children}</main>
    </div>
  )
}
```

### 3.4 Calendar 页面重构

**布局**：
```
[ Hero：训练日历 ]
[ 模式 Tab：计划视图 / 执行视图 ]
[ 周选择器（Token 风格按钮组）]
[ 统计行（4 张 Token 卡片）]
[ 日历网格（复用 Weekly 的 day-column 风格）]
[ 底部：训练成果列表 ]
```

**关键改动**：
1. 废弃原生 `<table>`，改用 `training-week-grid` + `training-day-column` 的卡片网格，与 Weekly 保持一致。
2. 每个时段块复用 `TrainingBlock` 组件，保留 Category 色条和强度标签。
3. 已执行的天显示绿色勾选标记，未执行的计划显示灰色虚线边框。
4. 周选择器从原生 button 改为 `training-mode-card` 风格按钮组。

### 3.5 History 页面重构

**布局**：
```
[ Hero：训练历史 ]
[ 统计行 ]
[ 分类筛选（Token Tab）]
[ 训练项目聚合卡片（横向展开）]
[ 最近明细表格（精简为 5 列）]
```

**关键改动**：
1. 聚合卡片复用 `training-item-card` 样式，增加 Category 色条。
2. 分类筛选使用 `training-category-tabs`。
3. 明细表格增加行 hover 高亮（`training-slot-block:hover` 同款）。
4. 增加「导出 CSV」按钮，放在 Hero 的 actionBar。

### 3.6 Fatigue 页面重构

**布局**：
```
[ Hero：球员疲劳 ]
[ 统计行 ]
[ 高风险球员预警区（红色主题 panel）]
[ 全队疲劳列表 ]
```

**关键改动**：
1. 统计卡片复用 `training-stat-tile`。
2. 疲劳列表项改为 `training-fatigue-row`（已在 Weekly 中定义），确保视觉一致。
3. 高风险球员卡片复用 `training-focus-card tone-red`。
4. 列表排序按钮改为 `training-ghost-btn`。
5. **新增快捷行动**：每个高疲劳球员卡片增加「去周计划调整」按钮，点击跳转到 Weekly 并自动选中下一个包含该球员的时段。

---

## 四、模板系统重构：让用户「看得懂、敢试用」

### 4.1 问题
- `<select>` 太简陋，5 套模板差异不透明。
- 「重置模板」与模板选择器物理分离。
- 应用后没有视觉反馈，用户不知道哪些格子被改了。

### 4.2 模板选择器升级为「套餐卡片」

废弃 `<select>`，改为横向滚动的套餐卡片：

```tsx
<section className="training-template-strip">
  {TRAINING_TEMPLATES.map(template => (
    <button
      key={template.id}
      onClick={() => handleTemplateClick(template)}
      className={`training-template-card ${activeTemplate.id === template.id ? 'is-active' : ''}`}
    >
      <strong>{template.name}</strong>
      <p>{template.description}</p>
      <div className="template-mini-grid">
        {template.schedule.map((day, i) => (
          <div key={i}>
            {day.map(slot => (
              <span key={slot} className={`tone-${getCategoryTone(slot)}`} />
            ))}
          </div>
        ))}
      </div>
    </button>
  ))}
</section>
```

**卡片内容**：
- 模板名称 + 一句话描述
- 7×3 的 micro 色块图（每个色块 4px，代表该时段训练的 Category 颜色），让用户一眼看出模板的全周节奏
- 选中态：边框高亮 + 底部 accent 色条

### 4.3 应用模板的视觉反馈

当用户切换模板时：
1. **即将变化的格子**先显示「预览态」：半透明的新训练内容覆盖在旧内容上，边框变为虚线 accent 色。
2. 提供一个「确认应用」按钮（2 秒自动确认，或手动点击）。
3. 确认后，旧内容淡出，新内容淡入（CSS transition 200ms）。
4. 被保护的格子（`isUserModified && !force`）显示一个锁图标，并 tooltip：「已手动调整，未更改」。

### 4.4 模板与重置的聚合

将「重置模板」从 Hero 移除，改为每个模板卡片内的操作：

```
[ 标准微周期    ]  [ 禁区终结周    ]  [ 控球出球周 ▲ ]
   描述...          描述...           描述...
   [应用]           [应用]           [已应用 ✓]
                                   [强制重置 ↻]
```

- 当前激活的模板显示「已应用」。
- 点击其他模板 → 「应用」；点击当前模板的「强制重置」→ 覆盖所有手动修改。

---

## 五、撤销栈与模式切换保护

### 5.1 撤销/重做系统（Undo/Redo）

#### 状态设计
```ts
// Weekly.tsx
interface PlanSnapshot {
  plan: Map<string, PlanSlotData>
  globalMode: TrainingMode
  groupConfig: PlanGroup[] | null
  activeTemplate: TrainingTemplateDetail
}

const [history, setHistory] = useState<PlanSnapshot[]>([])
const [historyIndex, setHistoryIndex] = useState(-1)
const MAX_HISTORY = 30

const pushHistory = useCallback((nextPlan: Map<string, PlanSlotData>) => {
  setHistory(prev => {
    const trimmed = prev.slice(0, historyIndex + 1)
    const snap: PlanSnapshot = {
      plan: new Map(nextPlan),
      globalMode,
      groupConfig,
      activeTemplate,
    }
    return [...trimmed, snap].slice(-MAX_HISTORY)
  })
  setHistoryIndex(prev => Math.min(prev + 1, MAX_HISTORY - 1))
}, [globalMode, groupConfig, activeTemplate, historyIndex])

const undo = useCallback(() => {
  if (historyIndex <= 0) return
  const snap = history[historyIndex - 1]
  setLocalPlan(snap.plan)
  setGlobalMode(snap.globalMode)
  setGroupConfig(snap.groupConfig)
  setActiveTemplate(snap.activeTemplate)
  setHistoryIndex(historyIndex - 1)
}, [history, historyIndex])

const redo = useCallback(() => {
  if (historyIndex >= history.length - 1) return
  const snap = history[historyIndex + 1]
  setLocalPlan(snap.plan)
  setGlobalMode(snap.globalMode)
  setGroupConfig(snap.groupConfig)
  setActiveTemplate(snap.activeTemplate)
  setHistoryIndex(historyIndex + 1)
}, [history, historyIndex])
```

#### 快捷键
- `Ctrl+Z` / `Cmd+Z` → undo
- `Ctrl+Shift+Z` / `Cmd+Shift+Z` → redo

#### UI 入口
在 Hero 的 `training-command-strip` 中新增：

```tsx
<button onClick={undo} disabled={historyIndex <= 0} className="training-ghost-btn">
  <Undo className="h-4 w-4" /> 撤销
</button>
<button onClick={redo} disabled={historyIndex >= history.length - 1} className="training-ghost-btn">
  <Redo className="h-4 w-4" /> 重做
</button>
```

#### 自动快照时机
- 应用训练项到格子
- 清空格子
- 切换全局模式
- 应用模板（确认后）
- 批量填充（执行后算一次）

**不记录快照**：画笔模式 hover 预览、分组 tab 切换（纯 UI 状态）。

### 5.2 模式切换改为「预览 → 确认」

**现状**：点击 `groups_2` 或 `groups_3` 直接弹 `confirm` 并破坏计划。
**重构**：

```ts
const [pendingMode, setPendingMode] = useState<TrainingMode | null>(null)
```

1. 用户点击 `groups_2`。
2. `training-mode-card` 进入「预览态」：边框变为虚线 accent，显示「预览中」标签。
3. 右侧计划板实时渲染 preview（不写入 `localPlan`），格子显示半透明分组结构。
4. 底部浮出确认条：
   ```
   [ 正在预览：双组训练 ]   [ 确认切换 ]   [ 取消 ]
   ```
5. 用户点击「确认」才真正执行模式切换、pushHistory、写入 plan。
6. 点击「取消」恢复原来的 `globalMode`，计划板无损。

**视觉实现**：
```css
.training-mode-card.is-preview {
  border-style: dashed;
  border-color: var(--skin-accent);
  background: color-mix(in srgb, var(--skin-accent-dark) 30%, #050609);
}
.training-mode-card.is-preview::after {
  content: '预览';
  position: absolute;
  top: 4px;
  right: 4px;
  font-size: 10px;
  padding: 2px 5px;
  background: var(--skin-accent);
  color: #050609;
}
```

### 5.3 未保存更改保护

**现状**：`hasUserChanges` 只改变按钮文字，用户很容易忽略。
**重构**：

1. **强提示**：当 `hasUserChanges === true` 时，页面底部固定显示悬浮条：
   ```
   ┌────────────────────────────────────────────┐
   │  ⚠ 你有未保存的修改（调整了 X 个时段）        │
   │     [ 保存修改 ]  [ 放弃更改 ]               │
   └────────────────────────────────────────────┘
   ```
2. **离开拦截**：监听 `beforeunload`，如果有未保存更改提示浏览器默认弹窗。
3. **保存成功反馈**：保存成功后，悬浮条向上滑出，hero 区域的「微调」数字清零并闪一下绿色。

---

## 六、组件拆分计划（工程化）

当前 `Weekly.tsx` 897 行，全部耦合在一起。重构时按以下结构拆分：

```
src/pages/Training/
├── Weekly.tsx                 # 容器，负责数据流和布局
├── Calendar.tsx               # 复用 TrainingPageShell + 新网格
├── History.tsx                # 复用 TrainingPageShell + 卡片列表
├── Fatigue.tsx                # 复用 TrainingPageShell + 列表
└── components/
    ├── TrainingPageShell.tsx    # 统一页面框架
    ├── PlanBoard.tsx            # 左侧 7 天计划板（含多选逻辑）
    ├── PlanSlot.tsx             # 单个时段格子（含预警角标）
    ├── GroupBlock.tsx           # 分组模式下格子内容
    ├── TeamBlock.tsx            # 全队模式下格子内容
    ├── MatchBlock.tsx           # 比赛日锁定块
    ├── EditorPanel.tsx          # 右侧「时段设置」面板
    ├── BatchEditorPanel.tsx     # 多选时的批量设置面板
    ├── TrainingLibrary.tsx      # 右侧训练库（含画笔模式）
    ├── TrainingItemCard.tsx     # 训练卡片（含冲突提示）
    ├── TemplateStrip.tsx        # 模板套餐卡片条
    ├── FatiguePanel.tsx         # 球员负荷面板（增强版）
    ├── ConflictEngine.ts        # 纯函数：计算冲突规则
    └── useTrainingHistory.ts    # Hook：撤销栈逻辑
```

---

## 七、改动清单与优先级

| 模块 | 改动项 | 预估工时 | 依赖 |
|---|---|---|---|
| **交互效率** | 画笔模式 | 1.5d | 无 |
| | 格子多选+批量填充 | 1.5d | 无 |
| | Ctrl+C/V 复制粘贴 | 0.5d | 多选 |
| | 分组 Tab 绑定格子 | 0.5d | 无 |
| **冲突预警** | ConflictEngine + 6 条规则 | 2d | 无 |
| | 预警角标与 Tooltip | 0.5d | ConflictEngine |
| | 疲劳面板增强（完整列表+冲突筛选） | 1d | 无 |
| **视觉统一** | TrainingPageShell 组件 | 0.5d | 提取 CSS Token |
| | training-system.css Token | 0.5d | 无 |
| | Calendar 重构 | 1.5d | Shell + Token |
| | History 重构 | 1d | Shell + Token |
| | Fatigue 重构 | 1d | Shell + Token |
| **模板反馈** | TemplateStrip 组件 | 1d | 无 |
| | 模板预览态 + 确认 | 1d | 无 |
| | 应用动画与保护提示 | 0.5d | 预览态 |
| **撤销保护** | useTrainingHistory Hook | 1d | 无 |
| | 模式切换预览 → 确认 | 1d | useTrainingHistory |
| | 未保存更改悬浮条 | 0.5d | 无 |
| **合计** | | **15d** | |

---

## 八、最小可用迭代（MVP）

如果资源有限，先只做以下 5 项，预计 **5 天**，解决最痛的体验问题：

1. **ConflictEngine + 3 条核心规则**（`PRE_MATCH_HIGH`、`DAILY_OVERLOAD`、`PLAYER_FATIGUE`）+ 角标提示。
2. **分组 Tab 绑定格子**（修复乱跳）。
3. **画笔模式**（反向流程，解决右侧滚动地狱）。
4. **TrainingPageShell + Calendar/Fatigue 视觉统一**（先统一2个页面）。
5. **未保存更改悬浮条**（防止丢失进度）。
