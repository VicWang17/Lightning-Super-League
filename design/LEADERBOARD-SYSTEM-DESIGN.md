# 联赛数据表 & 世界排名系统重构方案

> 基于现有代码库的调研结果，将散落的前后端排行榜逻辑统一为可扩展的「通用排行榜系统」。

---

## 一、现状分析

### 1.1 前端现状

| 页面 | 现有内容 | 问题 |
|------|---------|------|
| **联赛详情页** (`League/Detail.tsx`) | 5 个 Tab：积分榜、赛程、射手榜、助攻榜、联赛纪录 | 射手榜/助攻榜各占一个 Tab，浪费空间；零封榜 API 已存在但前端未接入；无抢断/拦截/评分等其他榜单 |
| **世界页** (`World/Index.tsx`) | 3 个 Tab：球队排名、球员 OVR 排名、世界纪录 | 球员只有 OVR 排序，无进球/助攻/评分等「实绩」排名 |

### 1.2 后端现状

- 联赛端有 3 个独立路由：`/top-scorers`、`/top-assists`、`/clean-sheets`，每新增一个榜单就要复制 30 行重复代码（赛季解析 + 三表 join + 排序）。
- 世界端只有 `/top-players`（按 OVR），无任何统计维度排名。
- `PlayerSeasonStats` 表已包含 30+ 个统计字段，数据层完全支撑扩展。

### 1.3 数据库可用字段（可直接用于榜单）

| 类别 | 可用字段 |
|------|---------|
| 进攻 | `goals`, `assists`, `shots`, `shots_on_target`, `dribbles`, `dribbles_succ`, `headers`, `headers_succ`, `free_kick_goals`, `penalty_goals` |
| 传球 | `passes`, `passes_succ`, `key_passes`, `crosses`, `crosses_succ` |
| 防守 | `tackles`, `tackles_succ`, `interceptions`, `clearances`, `blocks` |
| 门将 | `clean_sheets`, `saves` |
| 纪律 | `yellow_cards`, `red_cards`, `fouls`, `offsides` |
| 综合 | `matches_played`, `minutes_played`, `touches`, `average_rating` |

> 基于这些字段，可直接产出 **24+ 个榜单**；加上「率」类计算字段，可再扩展 **8+ 个榜单**。

---

## 二、设计目标

1. **联赛详情页**：把射手榜、助攻榜及所有衍生榜单收敛到一个「数据」Tab 内，通过子导航切换，默认展示射手榜（第一项）→ 助攻榜（第二项）。
2. **世界页**：球员排名支持按 OVR、进球、助攻、评分、抢断、拦截、扑救、零封等任意维度排序。
3. **扩展性**：新增一个榜单只需在配置表里注册一行，**零后端路由代码、零前端页面代码**。
4. **率类门槛**：所有和「率」（场均、成功率等）有关的排名，强制要求 `matches_played >= 10`。

---

## 三、后端方案：统一排行榜服务

### 3.1 核心思路

用「配置驱动」替代「硬编码路由」。定义一个 `LeaderboardType` 枚举 + `LeaderboardConfig` 配置表，由 `LeaderboardService` 根据配置动态拼装 SQL。

### 3.2 新增枚举与配置

```python
# backend/app/schemas/leaderboard.py

class LeaderboardType(str, Enum):
    # 基础计数类（联赛级 & 世界级通用）
    GOALS = "goals"                     # 射手榜
    ASSISTS = "assists"                 # 助攻榜
    CLEAN_SHEETS = "clean_sheets"       # 零封榜（GK）
    SAVES = "saves"                     # 扑救榜（GK）
    TACKLES = "tackles"                 # 抢断榜
    INTERCEPTIONS = "interceptions"     # 拦截榜
    CLEARANCES = "clearances"           # 解围榜
    BLOCKS = "blocks"                   # 封堵榜
    SHOTS = "shots"                     # 射门榜
    SHOTS_ON_TARGET = "shots_on_target" # 射正榜
    KEY_PASSES = "key_passes"           # 关键传球榜
    PASSES = "passes"                   # 传球榜
    CROSSES = "crosses"                 # 传中榜
    DRIBBLES = "dribbles"               # 盘带榜
    YELLOW_CARDS = "yellow_cards"       # 黄牌榜
    RED_CARDS = "red_cards"             # 红牌榜
    FOULS = "fouls"                     # 犯规榜
    OFFSIDES = "offsides"               # 越位榜
    TOUCHES = "touches"                 # 触球榜
    FREE_KICK_GOALS = "free_kick_goals" # 任意球进球榜
    PENALTY_GOALS = "penalty_goals"     # 点球进球榜
    MINUTES = "minutes_played"          # 出场时间榜
    APPEARANCES = "matches_played"      # 出场榜
    RATING = "average_rating"           # 场均评分榜

    # 比率/场均类（自动附加 matches_played >= 10）
    SHOT_ACCURACY = "shot_accuracy"         # 射正率
    PASS_ACCURACY = "pass_accuracy"         # 传球成功率
    TACKLE_ACCURACY = "tackle_accuracy"     # 抢断成功率
    DRIBBLE_ACCURACY = "dribble_accuracy"   # 盘带成功率
    CROSS_ACCURACY = "cross_accuracy"       # 传中成功率
    HEADER_ACCURACY = "header_accuracy"     # 头球成功率
    GOALS_PER_GAME = "goals_per_game"       # 场均进球
    ASSISTS_PER_GAME = "assists_per_game"   # 场均助攻


@dataclass
class LeaderboardConfig:
    type: LeaderboardType
    label: str                    # 中文名，如 "射手榜"
    order_field: Any              # SQLAlchemy column 或 expression
    value_label: str              # 前端展示单位，如 "进球"
    value_format: str             # "int" | "float1" | "percent"
    position_filter: Optional[str] = None   # 如 "GK"
    min_matches: int = 0          # 最低出场次数（率类自动 >=10）
    is_rate: bool = False         # 是否需要在 SQL 里做除法
```

### 3.3 统一返回 Schema

```python
class LeaderboardItem(BaseSchema):
    rank: int
    player_id: str
    player_name: str
    avatar_url: Optional[str]
    position: str                 # FW/MF/DF/GK
    team_name: str
    team_id: str
    value: float                  # 统一用 float，前端根据 value_format 决定显示
    value_label: str              # "进球" / "射正率" 等
    matches: int                  # 场次，用于率类展示「基于 N 场计算」
```

### 3.4 新增 API 端点

#### 联赛级
```
GET /api/v1/leagues/{league_id}/leaderboard
  ?type=goals&season_id=xxx&limit=20
```
- `type`: LeaderboardType（必填）
- `season_id`: 赛季 ID（可选，默认当前赛季）
- `limit`: 1-50，默认 20

#### 世界级
```
GET /api/v1/world/leaderboard
  ?type=goals&limit=100&position=FW
```
- `type`: LeaderboardType（必填）
- `position`: GK/DF/MF/FW（可选）
- `limit`: 1-500，默认 100

> **兼容策略**：保留现有 `/top-scorers`、`/top-assists`、`/clean-sheets`、`/top-players` 作为别名（内部直接调用新服务），避免前端其他页面或第三方调用断裂。

### 3.5 服务层实现要点

新建 `backend/app/services/leaderboard_service.py`：

```python
class LeaderboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_league_leaderboard(
        self, league_id, season_id, lb_type: LeaderboardType, limit=20
    ) -> List[LeaderboardItem]:
        config = LEADERBOARD_CONFIGS[lb_type]
        # 基础 query：join PlayerSeasonStats + Player + Team
        # WHERE league_id = ? AND season_id = ?
        # 若 config.position_filter: 加 Player.position == filter
        # 若 config.is_rate: SELECT 时做 CAST 除法
        # 若 config.min_matches > 0: HAVING matches_played >= config.min_matches
        # ORDER BY config.order_field DESC
        # LIMIT limit
        ...

    async def get_world_leaderboard(
        self, lb_type: LeaderboardType, limit=100, position=None
    ) -> List[LeaderboardItem]:
        config = LEADERBOARD_CONFIGS[lb_type]
        # 与联赛级区别：不限制 league_id，且需要 GROUP BY player_id
        # SUM(config.order_field) 作为聚合值
        # SUM(matches_played) 作为总场次
        # 若 is_rate: 用 SUM(分子) / SUM(分母) 或 AVG(加权) 计算全局比率
        # 当前赛季范围：取所有 ONGOING / 最近 FINISHED 赛季
        ...
```

**SQL 示例（联赛级射手榜）**：
```sql
SELECT p.id, p.name, p.avatar_url, p.position, t.id, t.name, ps.goals AS value, ps.matches_played
FROM player_season_stats ps
JOIN players p ON ps.player_id = p.id
LEFT JOIN teams t ON ps.team_id = t.id
WHERE ps.league_id = :league_id AND ps.season_id = :season_id
ORDER BY ps.goals DESC
LIMIT 20;
```

**SQL 示例（世界级射正率）**：
```sql
SELECT p.id, p.name, p.avatar_url, p.position,
       SUM(ps.shots_on_target) / NULLIF(SUM(ps.shots), 0) AS value,
       SUM(ps.matches_played) AS matches
FROM player_season_stats ps
JOIN players p ON ps.player_id = p.id
WHERE ps.season_id IN (:current_season_ids)   -- 各区域当前赛季
GROUP BY p.id
HAVING SUM(ps.matches_played) >= 10            -- 率类门槛
  AND SUM(ps.shots) > 0
ORDER BY value DESC
LIMIT 100;
```

---

## 四、前端方案

### 4.1 联赛详情页改造

**当前 Tab 结构**：
- 积分榜 | 赛程 | 射手榜 | 助攻榜 | 联赛纪录

**新 Tab 结构**：
- 积分榜 | 赛程 | **数据** | 联赛纪录

> 将「射手榜、助攻榜」及所有新榜单全部收敛进「数据」Tab。

**「数据」Tab 内部布局**：

```
┌─────────────────────────────────────────────────────┐
│  [数据 Tab 标题]                                      │
├─────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────────────┐ │
│  │ 榜单选择栏    │  │  榜单表格                     │ │
│  │              │  │                              │ │
│  │ · 射手榜     │  │  排名 球员 球队 进球 场次     │ │
│  │ · 助攻榜     │  │  ─────────────────────────   │ │
│  │ · 零封榜     │  │  1   张三  A队   15   20     │ │
│  │ · 抢断榜     │  │  2   李四  B队   12   18     │ │
│  │ · ...        │  │  ...                         │ │
│  │              │  │                              │ │
│  └──────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

**响应式处理**：
- **桌面端**：左侧固定宽度榜单选择栏（类似侧边导航），右侧表格区域。
- **移动端**：榜单选择栏变为横向可滚动标签栏（或下拉选择器）。

**榜单选择栏数据**：
```ts
const LEAGUE_LEADERBOARDS = [
  { type: 'goals',             label: '射手榜',      icon: Target },
  { type: 'assists',           label: '助攻榜',      icon: ArrowUpRight },
  { type: 'clean_sheets',      label: '零封榜',      icon: Shield },
  { type: 'saves',             label: '扑救榜',      icon: Hand },
  { type: 'tackles',           label: '抢断榜',      icon: Sword },
  { type: 'interceptions',     label: '拦截榜',      icon: Crosshair },
  { type: 'clearances',        label: '解围榜',      icon: Flag },
  { type: 'blocks',            label: '封堵榜',      icon: Wall },
  { type: 'rating',            label: '场均评分',    icon: Star },
  { type: 'shots',             label: '射门榜',      icon: Target },
  { type: 'shots_on_target',   label: '射正榜',      icon: Target2 },
  { type: 'shot_accuracy',     label: '射正率',      icon: Percent },
  { type: 'key_passes',        label: '关键传球',    icon: Key },
  { type: 'passes',            label: '传球榜',      icon: Share },
  { type: 'pass_accuracy',     label: '传球成功率',  icon: Percent },
  { type: 'crosses',           label: '传中榜',      icon: Cross },
  { type: 'dribbles',          label: '盘带榜',      icon: Footprints },
  { type: 'yellow_cards',      label: '黄牌榜',      icon: Square },
  { type: 'red_cards',         label: '红牌榜',      icon: Octagon },
  { type: 'fouls',             label: '犯规榜',      icon: AlertTriangle },
  { type: 'offsides',          label: '越位榜',      icon: FlagOff },
  { type: 'touches',           label: '触球榜',      icon: CircleDot },
  { type: 'free_kick_goals',   label: '任意球',      icon: Circle },
  { type: 'penalty_goals',     label: '点球',        icon: CircleDot },
  { type: 'minutes',           label: '出场时间',    icon: Clock },
  { type: 'appearances',       label: '出场榜',      icon: Users },
  { type: 'goals_per_game',    label: '场均进球',    icon: TrendingUp },
  { type: 'assists_per_game',  label: '场均助攻',    icon: TrendingUp },
]
```

> 用户说「射手榜和助攻榜作为里面的第一项和第二项」，所以数组前两项固定为 `goals`、`assists`，其余顺序可按重要性排列。

**表格列设计**：

| 列 | 说明 |
|---|---|
| 排名 | 前三名色块背景（金/银/铜），与现有风格一致 |
| 球员 | 头像 + 姓名，可点击跳转 `/players/{id}` |
| 位置 | FW/MF/DF/GK 标签 |
| 球队 | 可点击跳转 `/teams/{id}` |
| 数据值 | 主数值，大字号高亮 |
| 场次 | 次要信息，小字号灰色；**率类榜单此项额外重要**（显示「基于 N 场」） |

**新增/复用组件**：

```
frontend/src/components/leaderboard/
├── LeaderboardTable.tsx      # 通用榜单表格（接收 LeaderboardItem[]）
├── LeaderboardSidebar.tsx    # 榜单选择栏（桌面端侧边 / 移动端横滑）
└── LeaderboardValue.tsx      # 数值渲染（根据 value_format 显示整数/1位小数/百分比）
```

### 4.2 世界页改造

**当前「球员排名」Tab**：
- 标题：球员 OVR 排名
- 筛选：全部 / 前锋 / 中场 / 后卫 / 门将
- 表格列：排名 | 球员 | 位置 | 年龄 | OVR | 球队

**新「球员排名」Tab**：
- 标题改为「球员排名」
- 保留位置筛选器（全部 / 前锋 / 中场 / 后卫 / 门将）
- **新增「排序维度」筛选器**：
  ```
  OVR（默认）| 进球 | 助攻 | 场均评分 | 射门 | 射正率 | 抢断 | 拦截 | 扑救 | 零封 | 出场 | ...
  ```
- 当切换排序维度时，表格「高亮列」随之变化（OVR 列高亮 → 进球列高亮 → 评分列高亮...）。

**表格列动态化设计**：

| 固定列 | 动态高亮列（根据排序维度变化） |
|--------|------------------------------|
| 排名 | OVR / 进球 / 助攻 / 评分 / 抢断 ... |
| 球员（头像+姓名） | |
| 位置 | |
| 年龄 | |
| 球队 | |

> 这样设计的好处：
> 1. 不因为维度多而列数爆炸。
> 2. 用户一眼看到「我按什么排的」。
> 3. 如果想看球员的多维数据，点击球员进入详情页即可。

**API 调用**：
```ts
// 默认 OVR（调用旧接口保持兼容，或统一调用新接口 type=ovr）
const { players, loading } = useWorldLeaderboard('ovr', 100, position)

// 切到进球榜
const { players, loading } = useWorldLeaderboard('goals', 100, position)
```

> 也可以把 OVR 也纳入 `LeaderboardType`，但 OVR 不在 `PlayerSeasonStats` 里而在 `Player` 表里，需要在服务层做特殊分支处理。

### 4.3 新增 Hooks

```ts
// frontend/src/hooks/useLeagues.ts
export function useLeagueLeaderboard(
  leagueId: string | undefined,
  type: LeaderboardType,
  seasonId?: string,
  limit = 20
) { ... }

// frontend/src/hooks/useWorld.ts
export function useWorldLeaderboard(
  type: LeaderboardType,
  limit = 100,
  position?: string
) { ... }
```

### 4.4 类型定义扩展

```ts
// frontend/src/types/leaderboard.ts
export type LeaderboardType =
  | 'goals' | 'assists' | 'clean_sheets' | 'saves' | 'tackles'
  | 'interceptions' | 'clearances' | 'blocks' | 'shots' | 'shots_on_target'
  | 'shot_accuracy' | 'key_passes' | 'passes' | 'pass_accuracy'
  | 'crosses' | 'dribbles' | 'yellow_cards' | 'red_cards' | 'fouls'
  | 'offsides' | 'touches' | 'free_kick_goals' | 'penalty_goals'
  | 'minutes' | 'appearances' | 'rating'
  | 'tackle_accuracy' | 'dribble_accuracy' | 'cross_accuracy'
  | 'header_accuracy' | 'goals_per_game' | 'assists_per_game'
  | 'ovr'   // 世界页专用，OVR 排序

export interface LeaderboardItem {
  rank: number
  player_id: string
  player_name: string
  avatar_url?: string
  position: string
  team_name: string
  team_id: string
  value: number
  value_label: string
  matches: number
}
```

---

## 五、完整榜单清单

### 5.1 联赛详情页可用榜单（28 项）

| 序号 | 榜单类型 | 名称 | 排序字段 | 率类 | 门槛 | 专属位置 |
|-----|---------|------|---------|------|------|---------|
| 1 | `goals` | **射手榜** | `goals` | ❌ | — | — |
| 2 | `assists` | **助攻榜** | `assists` | ❌ | — | — |
| 3 | `clean_sheets` | **零封榜** | `clean_sheets` | ❌ | — | GK |
| 4 | `saves` | **扑救榜** | `saves` | ❌ | — | GK |
| 5 | `rating` | **场均评分** | `average_rating` | ✅ | 10场 | — |
| 6 | `tackles` | **抢断榜** | `tackles` | ❌ | — | — |
| 7 | `interceptions` | **拦截榜** | `interceptions` | ❌ | — | — |
| 8 | `clearances` | **解围榜** | `clearances` | ❌ | — | — |
| 9 | `blocks` | **封堵榜** | `blocks` | ❌ | — | — |
| 10 | `shots` | **射门榜** | `shots` | ❌ | — | — |
| 11 | `shots_on_target` | **射正榜** | `shots_on_target` | ❌ | — | — |
| 12 | `shot_accuracy` | **射正率** | `shots_on_target / shots` | ✅ | 10场 | — |
| 13 | `key_passes` | **关键传球** | `key_passes` | ❌ | — | — |
| 14 | `passes` | **传球榜** | `passes` | ❌ | — | — |
| 15 | `pass_accuracy` | **传球成功率** | `passes_succ / passes` | ✅ | 10场 | — |
| 16 | `crosses` | **传中榜** | `crosses` | ❌ | — | — |
| 17 | `cross_accuracy` | **传中成功率** | `crosses_succ / crosses` | ✅ | 10场 | — |
| 18 | `dribbles` | **盘带榜** | `dribbles` | ❌ | — | — |
| 19 | `dribble_accuracy` | **盘带成功率** | `dribbles_succ / dribbles` | ✅ | 10场 | — |
| 20 | `tackle_accuracy` | **抢断成功率** | `tackles_succ / tackles` | ✅ | 10场 | — |
| 21 | `header_accuracy` | **头球成功率** | `headers_succ / headers` | ✅ | 10场 | — |
| 22 | `yellow_cards` | **黄牌榜** | `yellow_cards` | ❌ | — | — |
| 23 | `red_cards` | **红牌榜** | `red_cards` | ❌ | — | — |
| 24 | `fouls` | **犯规榜** | `fouls` | ❌ | — | — |
| 25 | `offsides` | **越位榜** | `offsides` | ❌ | — | — |
| 26 | `touches` | **触球榜** | `touches` | ❌ | — | — |
| 27 | `free_kick_goals` | **任意球进球** | `free_kick_goals` | ❌ | — | — |
| 28 | `penalty_goals` | **点球进球** | `penalty_goals` | ❌ | — | — |
| 29 | `minutes` | **出场时间** | `minutes_played` | ❌ | — | — |
| 30 | `appearances` | **出场榜** | `matches_played` | ❌ | — | — |
| 31 | `goals_per_game` | **场均进球** | `goals / matches_played` | ✅ | 10场 | — |
| 32 | `assists_per_game` | **场均助攻** | `assists / matches_played` | ✅ | 10场 | — |

### 5.2 世界页可用榜单（同上 + OVR）

世界页额外增加 `ovr` 类型（从 `Player` 表取 `ovr` 排序），其余 32 项全部可用。

> 世界榜单的范围：**当前赛季所有大区所有联赛**的 `PlayerSeasonStats` 聚合。如果赛季已结束，取最近一个已结束赛季。

---

## 六、实施步骤（建议迭代顺序）

### Phase 1：后端统一服务（1-2 天）
1. 新建 `backend/app/schemas/leaderboard.py`（枚举 + Item Schema）。
2. 新建 `backend/app/services/leaderboard_service.py`（配置表 + 查询构建器）。
   - 先实现 **计数类**（goals/assists/tackles 等），再实现 **率类**（需要除法的）。
3. 在 `backend/app/routers/leagues.py` 新增 `/leagues/{league_id}/leaderboard` 端点。
4. 在 `backend/app/routers/world.py` 新增 `/world/leaderboard` 端点。
5. **保留旧端点不变**，内部改为调用 `LeaderboardService`（避免前端其他页面崩溃）。
6. 写单元测试验证每个榜单类型的 SQL 正确性。

### Phase 2：联赛详情页数据表（1 天）
1. 新建 `frontend/src/components/leaderboard/` 目录及 3 个组件。
2. 新建 `frontend/src/types/leaderboard.ts`。
3. 新增 `useLeagueLeaderboard` hook。
4. 改造 `League/Detail.tsx`：
   - 合并 scorers/assists 为「数据」Tab。
   - 接入 `LeaderboardSidebar` + `LeaderboardTable`。
   - 默认选中 `goals`（射手榜）。
5. 移除 `useTopScorers`、`useTopAssists` 在 Detail 页的直接使用（保留 hook 供其他地方使用）。

### Phase 3：世界页球员多维排名（0.5-1 天）
1. 新增 `useWorldLeaderboard` hook。
2. 改造 `World/Index.tsx`「球员排名」Tab：
   - 增加排序维度下拉/标签栏。
   - 默认 `ovr`。
   - 表格动态高亮排序列。
3. 保持球队排名和纪录 Tab 不变。

### Phase 4：收尾与优化（0.5 天）
1. 给率类榜单的表格添加 tooltip 说明：「基于至少 10 场比赛计算」。
2. 给零封榜/扑救榜添加 GK 专属图标或提示。
3. 移动端适配测试（榜单选择栏的横滑体验）。
4. 可以考虑给榜单选择栏加入「搜索/过滤」功能（如果列表太长）。

---

## 七、技术细节补充

### 7.1 关于「率」的计算精度

所有比率字段在 SQL 中使用 `FLOAT` 或 `DECIMAL` 计算，返回前端时保留 **1 位小数**（如 `72.3%`）。

### 7.2 关于零封榜的 GK 过滤

- 联赛级：`clean_sheets` 和 `saves` 两个榜单在 SQL 中过滤 `Player.position == 'GK'`。
- 但 stats 表里只有 GK 会有 `clean_sheets > 0` 和 `saves > 0`，加过滤是为了避免非门将球员以 0 值出现在榜单末尾。

### 7.3 关于世界级聚合的赛季选择

世界级聚合需要一个「当前赛季」定义。因为不同 zone 的赛季是独立的，算法：
1. 取每个 `zone_id` 最新的 `ONGOING` 赛季；
2. 若该 zone 无 `ONGOING`，取最新的 `FINISHED` 赛季；
3. 汇总所有 zone 的当前赛季 ID 列表，作为 `WHERE season_id IN (...)` 条件。

这样保证不同 zone 的球员在各自当前赛季内公平竞争。

### 7.4 兼容性说明

- **后端**：旧路由 `/top-scorers` 等保留，但内部一行代码代理到新服务。前端可以逐步迁移，也可以一次性迁移。
- **前端**：`useTopScorers`、`useTopAssists` 等 hook 可以保留（内部改为调用 `useLeagueLeaderboard` 的别名），避免影响其他页面（如球队详情页可能也引用了这些 hook）。

---

## 八、文件变更清单

| 文件路径 | 动作 | 说明 |
|---------|------|------|
| `backend/app/schemas/leaderboard.py` | 新增 | 枚举 + Schema |
| `backend/app/services/leaderboard_service.py` | 新增 | 核心服务 |
| `backend/app/routers/leagues.py` | 修改 | 新增 `/leaderboard` 端点，旧端点内部代理 |
| `backend/app/routers/world.py` | 修改 | 新增 `/leaderboard` 端点，旧端点内部代理 |
| `frontend/src/types/leaderboard.ts` | 新增 | 类型定义 |
| `frontend/src/hooks/useLeagues.ts` | 修改 | 新增 `useLeagueLeaderboard` |
| `frontend/src/hooks/useWorld.ts` | 修改 | 新增 `useWorldLeaderboard` |
| `frontend/src/components/leaderboard/LeaderboardTable.tsx` | 新增 | 通用表格组件 |
| `frontend/src/components/leaderboard/LeaderboardSidebar.tsx` | 新增 | 榜单选择栏 |
| `frontend/src/components/leaderboard/LeaderboardValue.tsx` | 新增 | 数值渲染组件 |
| `frontend/src/pages/League/Detail.tsx` | 修改 | 合并数据 Tab |
| `frontend/src/pages/World/Index.tsx` | 修改 | 球员排名增加维度切换 |

---

## 九、UI 示意图（文字描述）

### 联赛详情页「数据」Tab（桌面端）

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [积分榜] [赛程] [数据▼] [联赛纪录]                                        │
├──────────────────────────────────────────────────────────────────────────┤
│  第 3 赛季 ▼                                                             │
├──────────────┬───────────────────────────────────────────────────────────┤
│              │                                                           │
│  🎯 射手榜   │   排名   球员        位置   球队      进球    场次         │
│  ➡️ 助攻榜   │   ──────────────────────────────────────────────────     │
│  🛡️ 零封榜   │   1      张三        FW     红队      15      20           │
│  🧤 扑救榜   │   2      李四        MF     蓝队      12      18           │
│  ⚔️ 抢断榜   │   3      王五        FW     绿队      11      19           │
│  🚫 拦截榜   │   4      ...                                              │
│  ...         │                                                           │
│              │                                                           │
└──────────────┴───────────────────────────────────────────────────────────┘
```

### 世界页「球员排名」Tab

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [球队排名] [球员排名▼] [世界纪录]                                        │
├──────────────────────────────────────────────────────────────────────────┤
│  全部 / 前锋 / 中场 / 后卫 / 门将      排序：OVR▼                        │
├──────────────────────────────────────────────────────────────────────────┤
│  排名   球员          位置   年龄   OVR    球队                           │
│  ──────────────────────────────────────────────────────────              │
│  1      张三          FW     24     88     红队                          │
│  2      李四          MF     26     86     蓝队                          │
│  ...                                                                    │
│                                                                         │
│  （当切换排序为「进球」时，「进球」列高亮，OVR 列变为普通灰色）          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 十、风险评估与应对

| 风险 | 应对 |
|------|------|
| 榜单类型多达 30+，SQL 除法可能出现除零 | 所有率类 SQL 加 `NULLIF(denominator, 0)`，返回 `0` 或排除该记录 |
| 世界级聚合查询数据量大 | 加 `limit` 硬上限 500；可加 Redis 缓存（15 分钟），但第一期可以不加 |
| 移动端榜单选择栏过长 | 使用横向滚动标签栏，或增加「更多」折叠按钮；首屏只展示前 8 项 |
| 旧前端 hook 被多处引用 | 保留旧 hook 签名不变，内部改为调用新 hook，实现无痛迁移 |
