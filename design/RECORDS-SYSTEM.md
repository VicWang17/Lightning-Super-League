# 纪录与历史系统设计方案 (Records & History System)

> 目标：建立完整的纪录中心（球队纪录 + 球员纪录）和球员生涯历史页，支持世界纪录 / 联赛纪录 / 队伍纪录三级维度。

---

## 1. 需求概览

### 1.1 纪录中心 (`/records`)
- **入口**：左侧菜单栏新增「纪录」导航项
- **Tab 切换**：
  - `世界纪录` — 全服所有时间/所有联赛的纪录
  - `联赛纪录` — 当前玩家所在联赛的历史纪录
  - `队伍纪录` — 玩家自己球队的历史纪录
- **分类展示**：
  - `球队纪录` — 团队层面的纪录
  - `球员纪录` — 个人层面的纪录
- **每条纪录展示**：纪录名称 + 保持者 + 纪录数值 + 创造时间/赛季 + 相关比赛链接

### 1.2 球员历史页 (`/players/:id/history`)
- **入口**：球员详情页 (`/players/:id`) 增加「生涯历史」Tab
- **内容**：
  - 每个赛季的汇总数据（赛季进球、助攻、出场、评分、黄牌、红牌等）
  - 生涯总计数据
  - 赛季趋势图表（可选）

---

## 2. 技术方案选型

采用**混合策略**：

| 数据类型 | 策略 | 理由 |
|---------|------|------|
| 生涯累计数据 | 实时聚合 `PlayerSeasonStats` | 数据量可控，SQL 聚合即可 |
| 单赛季纪录 | 实时聚合 `PlayerSeasonStats` / `LeagueStanding` | 已有维度表，聚合简单 |
| 单场/比赛级纪录 | 预计算 `Record` 表 |  fastest goal / 最大分差等需要扫描 `MatchResult.events`，计算昂贵 |

**核心原则**：比赛结束时，由 `MatchSimulator._persist_engine_result()` 触发纪录检测与更新。

---

## 3. 后端数据模型

### 3.1 新增 `Record` 模型

```python
# app/models/record.py

class RecordScope(str, PyEnum):
    WORLD = "world"      # 世界纪录
    LEAGUE = "league"    # 联赛纪录 (scope_target_id = league_id)
    TEAM = "team"        # 队伍纪录 (scope_target_id = team_id)

class RecordCategory(str, PyEnum):
    TEAM = "team"        # 球队纪录
    PLAYER = "player"    # 球员纪录
    MATCH = "match"      # 比赛纪录 (如最大分差)

class RecordType(str, PyEnum):
    # --- 球员纪录 ---
    CAREER_GOALS = "career_goals"                    # 生涯总进球最多
    CAREER_ASSISTS = "career_assists"                # 生涯总助攻最多
    CAREER_APPEARANCES = "career_appearances"        # 生涯出场最多
    CAREER_YELLOW_CARDS = "career_yellow_cards"      # 生涯黄牌最多
    CAREER_RED_CARDS = "career_red_cards"            # 生涯红牌最多
    CAREER_RATING = "career_rating"                  # 生涯最高场均评分(min 50场)
    
    SEASON_GOALS = "season_goals"                    # 单赛季进球最多
    SEASON_ASSISTS = "season_assists"                # 单赛季助攻最多
    SEASON_RATING = "season_rating"                  # 单赛季最高场均评分(min 10场)
    
    MATCH_GOALS = "match_goals"                      # 单场进球最多
    MATCH_ASSISTS = "match_assists"                  # 单场助攻最多
    FASTEST_GOAL = "fastest_goal"                    # 最快进球 (秒)
    YOUNGEST_SCORER = "youngest_scorer"              # 最年轻进球者
    OLDEST_SCORER = "oldest_scorer"                  # 最年长进球者
    HAT_TRICKS = "hat_tricks"                        # 帽子戏法次数
    
    # --- 球队纪录 ---
    SEASON_TEAM_GOALS = "season_team_goals"          # 单赛季球队进球最多
    SEASON_TEAM_GOALS_AGAINST = "season_team_goals_against"  # 单赛季失球最少
    SEASON_TEAM_POINTS = "season_team_points"        # 单赛季积分最高
    SEASON_TEAM_WINS = "season_team_wins"            # 单赛季胜场最多
    
    BIGGEST_WIN_MARGIN = "biggest_win_margin"        # 最大比分胜利
    BIGGEST_DEFEAT_MARGIN = "biggest_defeat_margin"  # 最大比分失利
    MOST_GOALS_IN_MATCH = "most_goals_in_match"      # 单场总进球最多
    LONGEST_WIN_STREAK = "longest_win_streak"        # 最长连胜
    LONGEST_UNBEATEN = "longest_unbeaten"            # 最长不败
    LONGEST_LOSING_STREAK = "longest_losing_streak"  # 最长连败

class Record(Base):
    __tablename__ = "records"
    
    # 复合唯一索引: 同 scope + type 只能有一条当前纪录
    __table_args__ = (
        UniqueConstraint("scope", "scope_target_id", "record_type", name="uix_record_scope_type"),
    )
    
    scope: Mapped[RecordScope] = mapped_column(Enum(RecordScope), nullable=False, index=True)
    scope_target_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    # scope_target_id: WORLD=null, LEAGUE=league_id, TEAM=team_id
    
    category: Mapped[RecordCategory] = mapped_column(Enum(RecordCategory), nullable=False)
    record_type: Mapped[RecordType] = mapped_column(Enum(RecordType), nullable=False, index=True)
    
    # 纪录保持者
    holder_player_id: Mapped[str | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )
    holder_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True
    )
    
    # 纪录数值
    record_value: Mapped[str] = mapped_column(String(100), nullable=False)
    # 使用字符串存储，因为不同类型数值单位不同 (进球数/秒数/年龄)
    record_value_numeric: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False, index=True)
    # 用于排序的数值版本
    
    # 创造背景
    season_id: Mapped[str | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"), nullable=True
    )
    fixture_id: Mapped[str | None] = mapped_column(
        ForeignKey("fixtures.id", ondelete="SET NULL"), nullable=True
    )
    match_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    
    # 额外上下文 (JSON)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # e.g. {"streak_length": 15, "start_date": "...", "end_date": "..."}
    
    # 关系
    holder_player: Mapped["Player | None"] = relationship("Player")
    holder_team: Mapped["Team | None"] = relationship("Team")
    season: Mapped["Season | None"] = relationship("Season")
    fixture: Mapped["Fixture | None"] = relationship("Fixture")
```

### 3.2 新增 `TeamSeasonHistory` 视图模型（只读聚合）

不需要新建表，通过 API 层聚合 `LeagueStanding` 即可：

```python
# app/schemas/records.py
class TeamSeasonHistoryItem(BaseSchema):
    season_number: int
    league_name: str
    league_level: int
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    top_scorer_name: str | None
    top_scorer_goals: int
```

### 3.3 新增 `PlayerCareerHistory` 视图模型（只读聚合）

聚合 `PlayerSeasonStats`：

```python
# app/schemas/records.py
class PlayerSeasonHistoryItem(BaseSchema):
    season_number: int
    team_name: str
    team_id: str
    matches_played: int
    minutes_played: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    clean_sheets: int
    average_rating: float
    # 联赛 + 杯赛合并统计
    competition_breakdown: list[dict]  # [{"competition": "联赛", "goals": 10, ...}, {"competition": "闪电杯", ...}]

class PlayerCareerSummary(BaseSchema):
    total_seasons: int
    total_matches: int
    total_goals: int
    total_assists: int
    total_minutes: int
    total_yellow_cards: int
    total_red_cards: int
    overall_average_rating: float
    best_season: dict | None  # {"season_number": 3, "goals": 25, "assists": 10}
```

---

## 4. API 设计

### 4.1 纪录中心 API

```
GET /api/v1/records
  Query:
    - scope: world | league | team
    - scope_target_id: (optional, league_id or team_id)
    - category: team | player | match | all
  Response:
    { success, data: { "team": [RecordItem...], "player": [RecordItem...], "match": [RecordItem...] } }

GET /api/v1/records/world
  快捷接口，返回所有 scope=world 的纪录

GET /api/v1/records/league/{league_id}
  快捷接口，返回指定联赛纪录

GET /api/v1/records/team/{team_id}
  快捷接口，返回指定球队纪录
```

```python
# schemas
class RecordItem(BaseSchema):
    id: str
    scope: str
    category: str
    record_type: str
    record_type_label: str  # "单赛季进球最多"
    holder_name: str        # 球员名或球队名
    holder_id: str
    holder_avatar_url: str | None
    holder_team_name: str | None  # 球员所属球队
    record_value: str       # "34球"
    record_value_numeric: float
    season_number: int | None
    match_date: date | None
    fixture_id: str | None
    context: dict
```

### 4.2 球员历史 API

```
GET /api/v1/players/{player_id}/history
  Response:
    {
      success,
      data: {
        seasons: [PlayerSeasonHistoryItem...],
        summary: PlayerCareerSummary,
        milestones: [PlayerMilestone...]  # 生涯里程碑事件
      }
    }
```

```python
class PlayerMilestone(BaseSchema):
    milestone_type: str     # "debut", "first_goal", "100_goals", "50_appearances", "transfer", "award"
    season_number: int
    match_date: date | None
    description: str        # "第100个进球"
    fixture_id: str | None
```

### 4.3 球队历史 API

```
GET /api/v1/teams/{team_id}/history
  Response:
    {
      success,
      data: {
        seasons: [TeamSeasonHistoryItem...],
        record_count: int,  # 该球队保持的纪录数量
        trophies: [TrophyItem...]
      }
    }
```

---

## 5. 纪录检测逻辑 (Record Detection Service)

新增 `app/services/record_service.py`：

```python
class RecordService:
    """比赛结束后检测并更新纪录"""
    
    @staticmethod
    async def process_match_records(fixture: Fixture, match_result: MatchResult, db: AsyncSession):
        """主入口，在比赛结果被持久化后调用"""
        
        # 1. 检测单场纪录
        await RecordService._check_match_level_records(fixture, match_result, db)
        
        # 2. 检测球员单场纪录 (hat-trick, match goals, fastest goal)
        await RecordService._check_player_match_records(fixture, match_result, db)
        
        # 3. 检测连胜/连败 streak (需要在 Fixture 上额外查询最近 N 场)
        await RecordService._check_streak_records(fixture, db)
        
        # 4. 赛季级纪录在每赛季结束时批量计算，或每次更新 standing 后检查
    
    @staticmethod
    async def _check_match_level_records(fixture, match_result, db):
        total_goals = fixture.home_score + fixture.away_score
        margin = abs(fixture.home_score - fixture.away_score)
        
        # 最大分差
        await RecordService._update_record_if_better(
            scope=RecordScope.WORLD,
            scope_target_id=None,
            record_type=RecordType.BIGGEST_WIN_MARGIN,
            category=RecordCategory.MATCH,
            value_str=f"{margin}球",
            value_num=margin,
            holder_team_id=fixture.winner_team_id,
            fixture_id=fixture.id,
            db=db
        )
        # ... 同理处理 league / team scope
        
        # 单场最多进球
        await RecordService._update_record_if_better(
            ...,
            record_type=RecordType.MOST_GOALS_IN_MATCH,
            value_str=f"{total_goals}球",
            value_num=total_goals,
            ...
        )
    
    @staticmethod
    async def _check_player_match_records(fixture, match_result, db):
        events = match_result.events or []
        player_stats = match_result.player_stats or []
        
        # 最快进球
        first_goal = next((e for e in events if e.get("type") == "GOAL"), None)
        if first_goal:
            minute = first_goal.get("minute", 0)
            second = first_goal.get("second", 0)
            total_seconds = minute * 60 + second
            
            await RecordService._update_record_if_better(
                scope=RecordScope.WORLD,
                record_type=RecordType.FASTEST_GOAL,
                value_str=f"{minute}分{second}秒",
                value_num=-total_seconds,  # 越小越好，所以存负数
                holder_player_id=first_goal.get("player_id"),
                fixture_id=fixture.id,
                db=db
            )
        
        # 单场进球最多
        for ps in player_stats:
            goals = ps.get("goals", 0)
            if goals >= 3:  # hat-trick 级别才考虑
                player_id = ps.get("player_id")
                team_id = ps.get("team_id")
                
                # 更新 world / league / team scope
                for scope, target_id in [
                    (RecordScope.WORLD, None),
                    (RecordScope.LEAGUE, fixture.league_id),
                    (RecordScope.TEAM, team_id),
                ]:
                    await RecordService._update_record_if_better(
                        scope=scope,
                        scope_target_id=target_id,
                        record_type=RecordType.MATCH_GOALS,
                        value_str=f"{goals}球",
                        value_num=goals,
                        holder_player_id=player_id,
                        holder_team_id=team_id,
                        fixture_id=fixture.id,
                        db=db
                    )
    
    @staticmethod
    async def _update_record_if_better(scope, scope_target_id, record_type, category,
                                       value_str, value_num, holder_player_id=None,
                                       holder_team_id=None, fixture_id=None, season_id=None, db=None):
        """通用更新逻辑：如果新数值打破纪录，则更新"""
        existing = await db.execute(
            select(Record).where(
                Record.scope == scope,
                Record.scope_target_id == scope_target_id,
                Record.record_type == record_type
            )
        )
        record = existing.scalar_one_or_none()
        
        is_better = False
        if not record:
            is_better = True
        elif record_type in (RecordType.FASTEST_GOAL, RecordType.YOUNGEST_SCORER):
            is_better = value_num < record.record_value_numeric  # 越小越好
        else:
            is_better = value_num > record.record_value_numeric  # 越大越好
        
        if is_better:
            if not record:
                record = Record(...)
                db.add(record)
            else:
                record.record_value = value_str
                record.record_value_numeric = value_num
                record.holder_player_id = holder_player_id
                record.holder_team_id = holder_team_id
                record.fixture_id = fixture_id
                record.updated_at = datetime.utcnow()
            await db.commit()
```

### 5.2 赛季级纪录批量计算

```python
# app/services/record_service.py

class RecordService:
    @staticmethod
    async def recalculate_season_records(season_id: str, db: AsyncSession):
        """赛季结束时调用，批量计算所有赛季级纪录"""
        
        # 1. 球员单赛季纪录
        # 最高进球
        top_scorer = await db.execute(
            select(PlayerSeasonStats, Player, Team)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .join(Team, Player.team_id == Team.id)
            .where(PlayerSeasonStats.season_id == season_id)
            .order_by(PlayerSeasonStats.goals.desc())
            .limit(1)
        )
        # 更新 world / league scope 的 SEASON_GOALS 纪录
        
        # 2. 球队单赛季纪录
        # 最高积分
        top_points = await db.execute(
            select(LeagueStanding, Team, League)
            .join(Team, LeagueStanding.team_id == Team.id)
            .join(League, LeagueStanding.league_id == League.id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(LeagueStanding.points.desc())
            .limit(1)
        )
        # 更新 SEASON_TEAM_POINTS 等纪录
```

---

## 6. 前端设计

### 6.1 路由与菜单

```tsx
// frontend/src/routes.tsx
import RecordsPage from './pages/Records/Index'

// 在 MainLayout children 中添加:
{
  path: 'records',
  element: <RecordsPage />,
}

// 球员详情页增加子路由:
{
  path: 'players/:id',
  children: [
    { path: '', element: <PlayerDetail /> },
    { path: 'history', element: <PlayerHistory /> },
  ]
}
```

```tsx
// frontend/src/components/layout/Sidebar.tsx
// menuItems 增加:
{ path: '/records', label: '纪录', icon: ScrollText },  // 需要添加图标
```

### 6.2 纪录中心页面 (`/records`)

```
+----------------------------------------------------------+
|  纪录中心                                    [世界纪录 ▼]  |
+----------------------------------------------------------+
|  [球队纪录]  [球员纪录]  [比赛纪录]                        |
+----------------------------------------------------------+
|                                                          |
|  ┌────────────────────────────────────────────────────┐  |
|  │  🏆 单赛季进球最多                                    │  |
|  │     哈兰德 · 曼城                                   │  |
|  │     34球  ·  第3赛季                                 │  |
|  │     [查看赛季]                                        │  |
|  └────────────────────────────────────────────────────┘  |
|                                                          |
|  ┌────────────────────────────────────────────────────┐  |
|  │  ⚽ 生涯总进球最多                                    │  |
|  │     梅西 · 巴萨                                      │  |
|  │     128球  ·  5个赛季                                │  |
|  │     [查看球员]                                        │  |
|  └────────────────────────────────────────────────────┘  |
|                                                          |
|  ┌────────────────────────────────────────────────────┐  |
|  │  ⚡ 最快进球                                         │  |
|  │     罗纳尔多 · 曼联                                  │  |
|  │     11秒  ·  vs 利物浦  ·  第2赛季                    │  |
|  │     [查看比赛]                                        │  |
|  └────────────────────────────────────────────────────┘  |
|                                                          |
+----------------------------------------------------------+
```

**组件拆分**：

```
frontend/src/pages/Records/
├── Index.tsx              # 主页面，管理 scope tab + category tab
├── components/
│   ├── RecordCard.tsx     # 单条纪录卡片
│   ├── RecordCategoryTabs.tsx  # 球队/球员/比赛分类 Tab
│   └── RecordScopeSelector.tsx # 世界/联赛/队伍选择器
```

### 6.3 球员历史页 (`/players/:id/history`)

```
+----------------------------------------------------------+
|  ← 返回球员资料                                          |
+----------------------------------------------------------+
|  [球员档案]  [生涯历史]  [比赛记录]                        |
+----------------------------------------------------------+
|                                                          |
|  +------------------------+  +------------------------+  |
|  │      生涯总计           │  │       最佳赛季         │  |
|  │  出场  128             │  │  第3赛季               │  |
|  │  进球  86              │  │  25球 10助攻           │  |
|  │  助攻  42              │  │  场均 8.2分            │  |
|  │  评分  7.6             │  │                        │  |
|  +------------------------+  +------------------------+  |
|                                                          |
|  赛季表现                                                 |
|  +----------------------------------------------------+  |
|  │ 赛季 │ 球队   │ 出场 │ 进球 │ 助攻 │ 评分 │ 黄牌 │ 红牌 │  |
|  +----------------------------------------------------+  |
|  │  1   │ 曼联   │  22  │  8   │  4   │ 7.1  │  2   │  0   │  |
|  │  2   │ 曼联   │  26  │  15  │  8   │ 7.8  │  3   │  0   │  |
|  │  3   │ 曼联   │  28  │  25  │  10  │ 8.2  │  2   │  1   │  |
|  │  4   │ 曼城   │  24  │  18  │  12  │ 7.9  │  4   │  0   │  |
|  │  5   │ 曼城   │  28  │  20  │  8   │ 8.0  │  3   │  0   │  |
|  +----------------------------------------------------+  |
|                                                          |
|  生涯里程碑                                               |
|  +----------------------------------------------------+  |
|  │ 2024-03-15  第1个赛季  生涯首秀                        │  |
|  │ 2024-05-20  第1个赛季  首个进球                        │  |
|  │ 2025-11-10  第3个赛季  达成 50 球里程碑                │  |
|  │ 2026-02-28  第4个赛季  转会至 曼城                      │  |
|  +----------------------------------------------------+  |
|                                                          |
+----------------------------------------------------------+
```

**组件拆分**：

```
frontend/src/pages/Players/
├── History.tsx            # 球员生涯历史页
frontend/src/pages/Team/
├── PlayerDetail.tsx       # 现有页面，增加 Tab 导航
frontend/src/components/players/
├── CareerSummary.tsx      # 生涯总计卡片
├── SeasonStatsTable.tsx   # 赛季数据表格
├── MilestoneTimeline.tsx  # 里程碑时间线
```

---

## 7. 纪录类型完整清单

### 7.1 球员纪录 (Player Records)

| 纪录类型 | 代码 | 比较方向 | 数据来源 |
|---------|------|---------|---------|
| 生涯总进球最多 | `career_goals` | 越大越好 | `Player.goals` |
| 生涯总助攻最多 | `career_assists` | 越大越好 | `Player.assists` |
| 生涯出场最多 | `career_appearances` | 越大越好 | `Player.matches_played` |
| 生涯黄牌最多 | `career_yellow_cards` | 越大越好 | `Player.yellow_cards` |
| 生涯红牌最多 | `career_red_cards` | 越大越好 | `Player.red_cards` |
| 生涯最高场均评分 | `career_rating` | 越大越好 | `Player.average_rating` (min 50场) |
| 单赛季进球最多 | `season_goals` | 越大越好 | `PlayerSeasonStats.goals` |
| 单赛季助攻最多 | `season_assists` | 越大越好 | `PlayerSeasonStats.assists` |
| 单赛季最高场均评分 | `season_rating` | 越大越好 | `PlayerSeasonStats.average_rating` (min 10场) |
| 单场进球最多 | `match_goals` | 越大越好 | `MatchResult.player_stats[].goals` |
| 单场助攻最多 | `match_assists` | 越大越好 | `MatchResult.player_stats[].assists` |
| 最快进球 | `fastest_goal` | 越小越好 | `MatchResult.events[].minute/second` |
| 最年轻进球者 | `youngest_scorer` | 越小越好 | `MatchResult.events` + `Player.birth_offset` |
| 最年长进球者 | `oldest_scorer` | 越大越好 | `MatchResult.events` + `Player.birth_offset` |
| 帽子戏法次数 | `hat_tricks` | 越大越好 | `MatchResult.player_stats` 计数 |
| 连续进球场次 | `scoring_streak` | 越大越好 | `MatchResult` 聚合 |
| 连续助攻场次 | `assist_streak` | 越大越好 | `MatchResult` 聚合 |

### 7.2 球队纪录 (Team Records)

| 纪录类型 | 代码 | 比较方向 | 数据来源 |
|---------|------|---------|---------|
| 单赛季进球最多 | `season_team_goals` | 越大越好 | `LeagueStanding.goals_for` |
| 单赛季失球最少 | `season_team_goals_against` | 越小越好 | `LeagueStanding.goals_against` |
| 单赛季积分最高 | `season_team_points` | 越大越好 | `LeagueStanding.points` |
| 单赛季胜场最多 | `season_team_wins` | 越大越好 | `LeagueStanding.won` |
| 最大比分胜利 | `biggest_win_margin` | 越大越好 | `Fixture.home_score/away_score` |
| 最大比分失利 | `biggest_defeat_margin` | 越大越好 | `Fixture.home_score/away_score` (取负) |
| 单场总进球最多 | `most_goals_in_match` | 越大越好 | `Fixture` |
| 最长连胜 | `longest_win_streak` | 越大越好 | `Fixture` 序列分析 |
| 最长不败 | `longest_unbeaten` | 越大越好 | `Fixture` 序列分析 |
| 最长连败 | `longest_losing_streak` | 越大越好 | `Fixture` 序列分析 |
| 单赛季零封最多 | `season_clean_sheets` | 越大越好 | `PlayerSeasonStats.clean_sheets` (GK) |

### 7.3 比赛纪录 (Match Records)

| 纪录类型 | 代码 | 说明 |
|---------|------|------|
| 单场总进球最多 | `most_goals_in_match` | 双方进球之和 |
| 最大分差 | `biggest_win_margin` | 净胜球 |
| 最快进球 | `fastest_goal` | 比赛开始到首个进球 |

---

## 8. 实现阶段

### Phase 1: 基础设施 (1-2 天)
- [ ] 新建 `Record` 模型 + Alembic migration
- [ ] 新建 `app/schemas/records.py`
- [ ] 新建 `app/routers/records.py` (基础 CRUD)
- [ ] 前端 Sidebar 增加「纪录」菜单项
- [ ] 前端新建 `/records` 路由和空页面

### Phase 2: 纪录检测引擎 (2-3 天)
- [ ] 实现 `RecordService.process_match_records()`
- [ ] 接入 `MatchSimulator._persist_engine_result()` 调用点
- [ ] 实现单场纪录检测 (进球、最快进球、分差)
- [ ] 实现 streak 检测 (连胜/连败/不败)
- [ ] 实现赛季结束时批量计算 `recalculate_season_records()`

### Phase 3: 纪录中心前端 (2-3 天)
- [ ] 实现 `Records/Index.tsx` 页面框架
- [ ] 实现 Scope 切换 (世界/联赛/队伍)
- [ ] 实现 Category 切换 (球队/球员/比赛)
- [ ] 实现 `RecordCard` 组件
- [ ] 对接后端 API

### Phase 4: 球员历史页 (2-3 天)
- [ ] 后端: `GET /players/{id}/history` API
- [ ] 前端: 球员详情页增加 Tab 导航
- [ ] 前端: `PlayerHistory.tsx` 页面
- [ ] 前端: `SeasonStatsTable` 组件
- [ ] 前端: `CareerSummary` 组件

### Phase 5: 数据回填与测试 (1-2 天)
- [ ] 编写数据回填脚本：遍历历史比赛生成已有纪录
- [ ] 测试各类纪录边界情况
- [ ] 性能优化（必要时为 Record 表加 Redis 缓存）

---

## 9. 关键边界情况处理

1. **并列纪录**：如果新数值等于当前纪录但保持者不同，如何处理？
   - 建议：默认保留先创造的纪录。或设计「并列纪录」模式，允许多个保持者。
   - 简单方案：先创造者优先，在 UI 上显示 `(并列)` 标记。

2. **转会后纪录归属**：
   - 球员纪录：始终跟随球员本人（`holder_player_id`）
   - 队伍纪录：始终跟随球队（`holder_team_id`）
   - 联赛纪录：`scope_target_id` 指向当时的联赛，不因升级/降级改变

3. **世界纪录 vs 联赛纪录同步**：
   - 当某条联赛纪录被打破时，同时检测是否也打破了世界纪录
   - `process_match_records` 中会依次检测 world / league / team 三个 scope

4. **历史数据迁移**：
   - 编写一次性脚本，遍历所有 `MatchResult` 和 `LeagueStanding`，调用 RecordService 生成历史纪录
   - 脚本位置：`backend/scripts/backfill_records.py`

---

## 10. 文件变更清单

### 后端
```
backend/app/models/record.py              # 新增
backend/app/models/__init__.py            # 导出 Record
backend/app/schemas/records.py            # 新增
backend/app/schemas/__init__.py           # 导出新增 schemas
backend/app/routers/records.py            # 新增
backend/app/routers/players.py            # 新增 /{id}/history
backend/app/routers/teams.py              # 新增 /{id}/history
backend/app/services/record_service.py    # 新增
backend/app/services/match_simulator.py   # 接入纪录检测
backend/alembic/versions/xxx_add_records.py  # 新增 migration
backend/scripts/backfill_records.py       # 数据回填脚本
```

### 前端
```
frontend/src/routes.tsx                   # 新增 /records 路由
frontend/src/components/layout/Sidebar.tsx # 新增菜单项
frontend/src/pages/Records/
├── Index.tsx
└── components/
    ├── RecordCard.tsx
    ├── RecordCategoryTabs.tsx
    └── RecordScopeSelector.tsx
frontend/src/pages/Players/
└── History.tsx                           # 新增
frontend/src/pages/Team/PlayerDetail.tsx  # 增加 Tab 导航
frontend/src/components/players/
├── CareerSummary.tsx
├── SeasonStatsTable.tsx
└── MilestoneTimeline.tsx
frontend/src/types/records.ts             # 新增类型定义
frontend/src/api/client.ts                # 如有需要新增方法
```

---

*设计完成。建议先review数据模型和API设计，确认后从Phase 1开始逐步实施。*
