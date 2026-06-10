# 球员荣誉/奖项系统设计方案

## 一、需求概述

为游戏增加一套完整的球员荣誉体系，让球员的成长轨迹更有叙事感，也为世界页和球员页增加可展示的内容。

### 奖项清单

| # | 奖项名称 | 级别 | 评选周期 | 评选范围 |
|---|---------|------|---------|---------|
| 1 | **本场最佳球员** (Match MVP) | 单场 | 每场赛后 | 该场比赛 |
| 2 | **联赛最佳阵容** (League Team of the Season) | 联赛 | 赛季末 | 单个联赛 |
| 3 | **联赛最佳前锋/中场/后卫/门将** | 联赛 | 赛季末 | 单个联赛 |
| 4 | **联赛金靴奖** — 进球最多 | 联赛 | 赛季末 | 单个联赛 |
| 5 | **联赛助攻王** — 助攻最多 | 联赛 | 赛季末 | 单个联赛 |
| 6 | **联赛金手套奖** — 零封最多 | 联赛 | 赛季末 | 单个联赛 |
| 7 | **联赛金墙奖** — 抢断+拦截最多 | 联赛 | 赛季末 | 单个联赛 |
| 8 | **杯赛金靴/助攻王/金手套/金墙** | 杯赛 | 杯赛结束 | 单个杯赛 |
| 9 | **年度最佳球员** (闪电足球先生) | 赛季 | 赛季末 | 全服所有球员 |
| 10 | **年度最佳前锋/中场/后卫/门将** | 赛季 | 赛季末 | 全服所有球员 |
| 11 | **赛季金靴奖** — 进球最多 | 赛季 | 赛季末 | 全服所有球员 |
| 12 | **赛季助攻王** — 助攻最多 | 赛季 | 赛季末 | 全服所有球员 |
| 13 | **赛季金手套奖** — 零封最多 | 赛季 | 赛季末 | 全服所有球员 |
| 14 | **赛季金墙奖** — 抢断+拦截最多 | 赛季 | 赛季末 | 全服所有球员 |

---

## 二、数据库设计

### 2.1 player_awards 表

存储所有球员获得的荣誉记录。一张表覆盖全部奖项类型。

```sql
CREATE TABLE player_awards (
    id              CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    player_id       CHAR(36) NOT NULL,
    season_id       CHAR(36) NOT NULL,          -- 所属赛季
    season_number   INT NOT NULL,               -- 冗余，方便查询

    -- 奖项类型
    award_type      VARCHAR(40) NOT NULL,       -- 见 AwardType 枚举
    award_level     VARCHAR(20) NOT NULL,       -- match / league / season / world

    -- 关联范围（根据奖项类型填写）
    league_id       CHAR(36) NULL,              -- 联赛级奖项必填
    cup_id          CHAR(36) NULL,              -- 杯赛级奖项时填
    fixture_id      CHAR(36) NULL,              -- 单场MVP必填

    -- 位置信息（最佳阵容/最佳位置时用）
    position        VARCHAR(10) NULL,           -- FW / MF / DF / GK

    -- 评选依据（JSON，记录当时的评选数据，方便回溯）
    metadata        JSON NULL,
    -- 示例：{"rating": 8.5, "matches": 28, "goals": 15, "championships": 2, "mvp_count": 3}

    -- 额外描述
    description     VARCHAR(255) NULL,          -- 如 "第3赛季 甲级联赛A组 最佳前锋"

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE,
    FOREIGN KEY (league_id) REFERENCES leagues(id) ON DELETE CASCADE,
    FOREIGN KEY (cup_id) REFERENCES cup_competitions(id) ON DELETE CASCADE,
    FOREIGN KEY (fixture_id) REFERENCES fixtures(id) ON DELETE CASCADE,

    -- 同赛季同球员同类型不重复
    UNIQUE KEY uk_player_award (
        player_id, season_id, award_type, league_id, position
    ),
    INDEX idx_season_award (season_id, award_type),
    INDEX idx_player (player_id),
    INDEX idx_league_season (league_id, season_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.2 枚举定义

```python
class AwardType(str, PyEnum):
    # 单场级
    MATCH_MVP = "match_mvp"                     # 本场最佳球员

    # 联赛级 — 最佳阵容/位置
    LEAGUE_TEAM_OF_SEASON = "league_team_of_season"  # 联赛最佳阵容
    LEAGUE_BEST_FW = "league_best_fw"           # 联赛最佳前锋
    LEAGUE_BEST_MF = "league_best_mf"           # 联赛最佳中场
    LEAGUE_BEST_DF = "league_best_df"           # 联赛最佳后卫
    LEAGUE_BEST_GK = "league_best_gk"           # 联赛最佳门将

    # 联赛级 — 数据之王
    LEAGUE_GOLDEN_BOOT = "league_golden_boot"   # 联赛金靴奖（进球最多）
    LEAGUE_PLAYMAKER = "league_playmaker"       # 联赛助攻王（助攻最多）
    LEAGUE_GOLDEN_GLOVE = "league_golden_glove" # 联赛金手套奖（零封最多）
    LEAGUE_GOLDEN_WALL = "league_golden_wall"   # 联赛金墙奖（抢断+拦截最多）

    # 杯赛级 — 数据之王
    CUP_GOLDEN_BOOT = "cup_golden_boot"         # 杯赛金靴奖
    CUP_PLAYMAKER = "cup_playmaker"             # 杯赛助攻王
    CUP_GOLDEN_GLOVE = "cup_golden_glove"       # 杯赛金手套奖
    CUP_GOLDEN_WALL = "cup_golden_wall"         # 杯赛金墙奖

    # 赛季级（全服）— 最佳球员/位置
    SEASON_BEST_PLAYER = "season_best_player"   # 年度最佳球员（闪电足球先生）
    SEASON_BEST_FW = "season_best_fw"           # 年度最佳前锋
    SEASON_BEST_MF = "season_best_mf"           # 年度最佳中场
    SEASON_BEST_DF = "season_best_df"           # 年度最佳后卫
    SEASON_BEST_GK = "season_best_gk"           # 年度最佳门将

    # 赛季级（全服）— 数据之王
    SEASON_GOLDEN_BOOT = "season_golden_boot"   # 赛季金靴奖
    SEASON_PLAYMAKER = "season_playmaker"       # 赛季助攻王
    SEASON_GOLDEN_GLOVE = "season_golden_glove" # 赛季金手套奖
    SEASON_GOLDEN_WALL = "season_golden_wall"   # 赛季金墙奖

class AwardLevel(str, PyEnum):
    MATCH = "match"       # 单场
    LEAGUE = "league"     # 联赛
    SEASON = "season"     # 赛季（全服）
```

### 2.3 与现有表的关系

- `team_honors`：记录球队荣誉（冠军）
- `player_awards`：记录球员个人荣誉
- `PlayerSeasonStats`：评选数据来源
- `match_results.player_stats`：单场 MVP 数据来源

---

## 三、评选逻辑

### 3.1 本场最佳球员 (Match MVP)

**触发时机**：每场比赛结束后，由 MatchSimulator 或 MatchResult 处理流程调用。

**评选规则**：
1. 从 `match_results.player_stats` 中取该场所有球员的 `rating`
2. 取 `rating` 最高的球员
3. 若并列：
   - 优先比较 `goals`（进球多的胜出）
   - 再比较 `assists`（助攻多的胜出）
   - 再比较 `key_passes + tackles + interceptions + saves`（关键数据总和）
   - 仍并列则随机（或取第一个）
4. 写入 `player_awards`，`fixture_id` 必填

**Metadata 示例**：
```json
{"rating": 9.2, "goals": 2, "assists": 1, "team": "红魔联", "opponent": "蓝鹰联", "match_result": "2:1"}
```

---

### 3.2 联赛最佳阵容 (League Team of the Season)

**触发时机**：联赛赛季结束后（`LeagueSeasonService.end_season` 或类似流程）。

**评选规则**：
1. 筛选条件：该联赛本赛季出场 ≥ 10 场（`PlayerSeasonStats.matches_played >= 10`）
2. 按位置分组，每组取 `average_rating` 最高的球员：
   - `FW` 取 1~3 人（看该联赛有多少活跃前锋，最少1人，最多3人）
   - `MF` 取 2~4 人
   - `DF` 取 2~4 人
   - `GK` 取 1 人
3. **阵容配置不一定**：如果某位置没有满足出场门槛的球员，可以少选；如果某位置人才济济，可以多选。总体控制在 8~11 人。
4. 具体算法：
   - GK：固定取1人
   - DF：取 `min(4, max(2, 有资格的DF人数))`
   - MF：取 `min(4, max(2, 有资格的MF人数))`
   - FW：取 `min(3, max(1, 有资格的FW人数))`
5. 每人写入一条 `LEAGUE_TEAM_OF_SEASON` 记录，`position` 字段标注其入选位置

**Metadata 示例**：
```json
{"rating": 8.1, "matches": 28, "goals": 12, "position_rank": 1}
```

---

### 3.3 联赛最佳位置球员

**触发时机**：与最佳阵容同时评选。

**评选规则**：
1. 同最佳阵容的筛选条件（出场 ≥ 10 场）
2. 每个位置独立评选，取该位置 `average_rating` 最高的球员
3. 每个联赛每个赛季产生 4 个奖项（最佳前锋/中场/后卫/门将）

**Metadata 示例**：
```json
{"rating": 8.3, "matches": 26, "goals": 18, "position": "FW"}
```

---

### 3.4 联赛数据之王（金靴 / 助攻王 / 金手套 / 金墙）

**触发时机**：与联赛最佳阵容同时评选（联赛赛季结束后）。

**评选规则**：
1. 筛选条件：该联赛本赛季出场 ≥ 10 场
2. 各奖项独立评选，按单一数据指标排序：

| 奖项 | 指标 | 指标字段 | 并列打破规则 |
|-----|------|---------|-------------|
| **联赛金靴奖** | 总进球 | `goals` | 出场少者优先 → 助攻多 → 评分高 |
| **联赛助攻王** | 总助攻 | `assists` | 出场少者优先 → 进球多 → 评分高 |
| **联赛金手套奖** | 总零封 | `clean_sheets` | 出场多者优先 → 扑救多 → 失球少 |
| **联赛金墙奖** | 抢断+拦截 | `tackles + interceptions` | 出场少者优先 → 评分高 → 解围多 |

3. 每个联赛每个赛季各产生 1 名获奖者

**Metadata 示例**：
```json
{"goals": 22, "matches": 28, "assists": 5, "rating": 7.8}
```

---

### 3.5 杯赛数据之王

**触发时机**：杯赛结束后（杯赛冠军产生时）。

**评选规则**：
1. 从 `PlayerSeasonStats` 中筛选 `cup_competition_id == 该杯赛ID` 的记录
2. 出场门槛：≥ 3 场（杯赛场次少，门槛相应降低）
3. 指标同联赛数据之王：进球 / 助攻 / 零封 / 抢断+拦截
4. 每个杯赛各产生 1 名获奖者

**Metadata 示例**：
```json
{"goals": 8, "matches": 6, "team": "红魔联", "cup_name": "闪电杯"}
```

---

### 3.6 年度最佳球员 (闪电足球先生)

**触发时机**：当赛季所有联赛和杯赛全部结束后（可在 `SeasonService` 的赛季结算流程末尾调用）。

**评选规则**（这是核心难点，需要平衡评分与荣誉）：

#### 计分公式

```
综合得分 = (场均评分 × 权重A) + (冠军数 × 权重B) + (MVP次数 × 权重C) + (出场数 × 权重D) + (最佳阵容入选 × 权重E)
```

建议权重：
| 指标 | 权重 | 说明 |
|-----|------|------|
| 场均评分 | × 15 | 基础分，8.0分 = 120分 |
| 联赛冠军 | + 30 | 每座联赛冠军 |
| 杯赛冠军 | + 25 | 每座杯赛冠军（闪电杯/杰尼杯）|
| 单场MVP | + 3 | 每场最佳 |
| 出场数 | + 0.2 | 每出场1场 |
| 联赛最佳阵容入选 | + 10 | 每入选1次 |
| 联赛最佳位置 | + 15 | 每获得1次 |

**示例对比**：
- 球员A：评分8.0，2座冠军（联赛+杯赛），10场MVP，30场出场，1次最佳阵容
  - 得分 = 8.0×15 + 2×30 + 10×3 + 30×0.2 + 1×10 = 120 + 60 + 30 + 6 + 10 = **226**
- 球员B：评分8.5，0座冠军，5场MVP，28场出场，1次最佳阵容
  - 得分 = 8.5×15 + 0 + 5×3 + 28×0.2 + 1×10 = 127.5 + 0 + 15 + 5.6 + 10 = **158.1**

→ 球员A胜出，符合"评分8.0但拿了两个冠军的球员比8.5但两手空空的球员更应该拿奖"的需求。

**评选范围**：全服所有球员（跨联赛、跨杯赛）。

---

### 3.7 年度最佳位置球员

**触发时机**：与年度最佳球员同时评选。

**评选规则**：
1. 全服所有球员，按位置分组
2. 计分公式同年度最佳球员，但在各自位置内排名
3. 每个位置产生1名获奖者（共4名：最佳前锋/中场/后卫/门将）

---

## 四、后端架构

### 4.1 新增文件

```
backend/app/services/award_service.py      # 核心评选服务
backend/app/routers/awards.py              # API 路由
backend/app/models/player_award.py         # 数据模型
backend/app/schemas/award.py               # Pydantic  schemas
backend/alembic/versions/xxxx_add_player_awards.py  # 迁移
```

### 4.2 AwardService 核心接口

```python
class AwardService:
    @staticmethod
    async def award_match_mvp(fixture_id: str, result: MatchResult, db: AsyncSession) -> Optional[PlayerAward]:
        """评选单场MVP并入库"""

    @staticmethod
    async def award_league_end_of_season(league_id: str, season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """联赛赛季结束后：评选最佳阵容 + 最佳位置球员 + 数据之王"""

    @staticmethod
    async def award_cup_end(cup_id: str, season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """杯赛结束后：评选杯赛数据之王（金靴/助攻王/金手套/金墙）"""

    @staticmethod
    async def award_season_end_of_season(season_id: str, season_number: int, db: AsyncSession) -> List[PlayerAward]:
        """整个赛季结束后：评选年度最佳球员 + 年度最佳位置 + 赛季数据之王"""

    @staticmethod
    async def get_player_awards(player_id: str, db: AsyncSession) -> List[PlayerAward]:
        """获取某球员的全部荣誉"""

    @staticmethod
    async def get_season_awards(season_id: str, db: AsyncSession) -> Dict[str, List[PlayerAward]]:
        """获取某赛季的全部奖项（按类型分组）"""

    @staticmethod
    async def get_league_awards(league_id: str, season_id: str, db: AsyncSession) -> Dict[str, List[PlayerAward]]:
        """获取某联赛某赛季的全部奖项"""

    @staticmethod
    async def get_cup_awards(cup_id: str, db: AsyncSession) -> Dict[str, List[PlayerAward]]:
        """获取某杯赛的全部奖项"""
```

### 4.3 触发点

| 触发事件 | 调用方法 | 位置 |
|---------|---------|------|
| 单场比赛结束 | `award_match_mvp()` | `match_simulator.py` / `MatchEngineClient` |
| 联赛赛季结束 | `award_league_end_of_season()` | `league_season_service.py` / `season_service.py` |
| 杯赛结束 | `award_cup_end()` | `cup_progression.py` / `honor_service.py` |
| 全赛季结束 | `award_season_end_of_season()` | `season_service.py` 赛季结算末尾 |

### 4.4 API 路由

```
POST /awards/match-mvp/{fixture_id}          # 手动触发单场MVP评选（调试用）
POST /awards/league/{league_id}/season-end   # 手动触发联赛奖项评选（调试用）
POST /awards/cup/{cup_id}/end                # 手动触发杯赛奖项评选（调试用）
POST /awards/season-end/{season_id}          # 手动触发赛季大奖评选（调试用）

GET  /players/{player_id}/awards             # 球员荣誉列表
GET  /seasons/{season_id}/awards             # 某赛季全部奖项
GET  /leagues/{league_id}/awards             # 某联赛当前赛季奖项
GET  /cups/{cup_id}/awards                   # 某杯赛奖项
GET  /world/awards?season_id=xxx             # 世界页奖项展示
```

---

## 五、前端架构

### 5.1 新增/修改页面

#### 球员详情页 — 新增「荣誉室」Tab

路径：`/players/{id}/awards` 或作为球员页的一个 tab。

展示内容：
- 按赛季倒序分组
- 每个奖项用卡片展示：
  - 奖项图标（🏆 MVP / ⭐ 最佳阵容 / 👑 足球先生 等）
  - 奖项名称 + 赛季
  - 评选依据（评分、进球、冠军数等）
- 顶部统计：总荣誉数、MVP次数、冠军伴随次数、入选最佳阵容次数

#### 世界页 — 新增「奖项」Tab

路径：作为 `/world` 的第四个 tab（球队排名 / 球员排名 / 世界纪录 / **赛季奖项**）。

展示内容：
- 赛季选择器
- **闪电足球先生**（大图 + 球员信息）
- **年度最佳阵容**（4个位置的最佳球员卡片）
- **赛季数据之王**（金靴/助攻王/金手套/金墙 四张卡片）
- **各联赛最佳阵容**（可选，或折叠展示）

#### 联赛详情页 — 新增「赛季最佳」Tab

路径：`/leagues/{id}` 新增 tab。

展示内容：
- 该联赛本赛季最佳阵容（FW/MF/DF/GK 入选球员）
- 各位置最佳球员
- **联赛数据之王**（金靴/助攻王/金手套/金墙 横向四卡片）

### 5.2 前端类型

```typescript
interface PlayerAward {
  id: string
  player_id: string
  player_name: string
  player_avatar_url?: string
  season_id: string
  season_number: number
  award_type: AwardType
  award_level: 'match' | 'league' | 'season'
  league_id?: string
  league_name?: string
  cup_id?: string
  cup_name?: string
  fixture_id?: string
  position?: 'FW' | 'MF' | 'DF' | 'GK'
  description: string
  metadata: {
    rating?: number
    matches?: number
    goals?: number
    assists?: number
    championships?: number
    mvp_count?: number
    [key: string]: any
  }
  created_at: string
}

type AwardType =
  | 'match_mvp'
  | 'league_team_of_season'
  | 'league_best_fw' | 'league_best_mf' | 'league_best_df' | 'league_best_gk'
  | 'season_best_player'
  | 'season_best_fw' | 'season_best_mf' | 'season_best_df' | 'season_best_gk'

const AWARD_LABELS: Record<AwardType, string> = {
  match_mvp: '本场最佳',
  league_team_of_season: '联赛最佳阵容',
  league_best_fw: '联赛最佳前锋',
  league_best_mf: '联赛最佳中场',
  league_best_df: '联赛最佳后卫',
  league_best_gk: '联赛最佳门将',
  league_golden_boot: '联赛金靴奖',
  league_playmaker: '联赛助攻王',
  league_golden_glove: '联赛金手套奖',
  league_golden_wall: '联赛金墙奖',
  cup_golden_boot: '杯赛金靴奖',
  cup_playmaker: '杯赛助攻王',
  cup_golden_glove: '杯赛金手套奖',
  cup_golden_wall: '杯赛金墙奖',
  season_best_player: '闪电足球先生',
  season_best_fw: '年度最佳前锋',
  season_best_mf: '年度最佳中场',
  season_best_df: '年度最佳后卫',
  season_best_gk: '年度最佳门将',
  season_golden_boot: '赛季金靴奖',
  season_playmaker: '赛季助攻王',
  season_golden_glove: '赛季金手套奖',
  season_golden_wall: '赛季金墙奖',
}
```

---

## 六、关键算法伪代码

### 6.1 单场 MVP

```python
async def award_match_mvp(fixture_id, result, db):
    stats = result.player_stats  # List[PlayerMatchStat]

    # 按评分降序，评分相同按进球、助攻、关键数据排序
    sorted_stats = sorted(stats, key=lambda s: (
        -s.rating,
        -s.goals,
        -s.assists,
        -(s.key_passes + s.tackles + s.interceptions + s.saves)
    ))

    winner = sorted_stats[0]
    player = await db.get(Player, winner.player_id)

    award = PlayerAward(
        player_id=player.id,
        season_id=fixture.season_id,
        season_number=season.season_number,
        award_type=AwardType.MATCH_MVP,
        award_level=AwardLevel.MATCH,
        fixture_id=fixture_id,
        metadata={
            "rating": winner.rating,
            "goals": winner.goals,
            "assists": winner.assists,
            "team": winner.team_name,
        },
        description=f"第{season.season_number}赛季 第{fixture.season_day}天 {winner.team_name} vs {opponent} 本场最佳"
    )
    db.add(award)
    return award
```

### 6.2 联赛最佳阵容

```python
async def award_league_team_of_season(league_id, season_id, db):
    ps = PlayerSeasonStats
    query = select(ps, Player).join(Player, ps.player_id == Player.id).where(
        ps.league_id == league_id,
        ps.season_id == season_id,
        ps.matches_played >= 10
    )
    rows = await db.execute(query)

    by_position = {"FW": [], "MF": [], "DF": [], "GK": []}
    for stat, player in rows:
        pos = player.position.value
        if pos in by_position:
            by_position[pos].append((stat, player))

    # 每个位置按场均评分排序
    for pos in by_position:
        by_position[pos].sort(key=lambda x: -x[0].average_rating)

    # 阵容配置策略
    slots = {
        "GK": 1,
        "DF": min(4, max(2, len(by_position["DF"]))),
        "MF": min(4, max(2, len(by_position["MF"]))),
        "FW": min(3, max(1, len(by_position["FW"]))),
    }

    awards = []
    for pos, count in slots.items():
        for i in range(count):
            if i >= len(by_position[pos]):
                break
            stat, player = by_position[pos][i]
            awards.append(PlayerAward(
                player_id=player.id,
                season_id=season_id,
                award_type=AwardType.LEAGUE_TEAM_OF_SEASON,
                award_level=AwardLevel.LEAGUE,
                league_id=league_id,
                position=pos,
                metadata={
                    "rating": float(stat.average_rating),
                    "matches": stat.matches_played,
                    "goals": stat.goals,
                    "position_rank": i + 1,
                }
            ))
    return awards
```

### 6.3 联赛/杯赛数据之王

```python
async def award_data_kings(scope_type, scope_id, season_id, db, min_matches=10):
    """
    通用数据之王评选
    scope_type: 'league' | 'cup'
    scope_id: league_id 或 cup_id
    """
    ps = PlayerSeasonStats
    filter_col = ps.league_id if scope_type == 'league' else ps.cup_competition_id

    query = select(ps, Player).join(Player, ps.player_id == Player.id).where(
        filter_col == scope_id,
        ps.season_id == season_id,
        ps.matches_played >= min_matches
    )
    rows = await db.execute(query)

    candidates = [(stat, player) for stat, player in rows]

    award_configs = [
        (AwardType.LEAGUE_GOLDEN_BOOT if scope_type == 'league' else AwardType.CUP_GOLDEN_BOOT,
         lambda s: s.goals, "goals", lambda s: (-s.assists, -s.average_rating)),
        (AwardType.LEAGUE_PLAYMAKER if scope_type == 'league' else AwardType.CUP_PLAYMAKER,
         lambda s: s.assists, "assists", lambda s: (-s.goals, -s.average_rating)),
        (AwardType.LEAGUE_GOLDEN_GLOVE if scope_type == 'league' else AwardType.CUP_GOLDEN_GLOVE,
         lambda s: s.clean_sheets, "clean_sheets", lambda s: (-s.saves, s.goals_against)),
        (AwardType.LEAGUE_GOLDEN_WALL if scope_type == 'league' else AwardType.CUP_GOLDEN_WALL,
         lambda s: s.tackles + s.interceptions, "tackles_interceptions", lambda s: (-s.average_rating, -s.clearances)),
    ]

    awards = []
    for award_type, primary_key, meta_key, tie_breaker in award_configs:
        # 排序：主指标降序 → tie_breaker
        sorted_candidates = sorted(candidates, key=lambda x: (
            -primary_key(x[0]),
            *tie_breaker(x[0])
        ))
        if not sorted_candidates:
            continue
        winner_stat, winner_player = sorted_candidates[0]
        primary_value = primary_key(winner_stat)
        if primary_value == 0:
            continue  # 指标为0不颁奖

        awards.append(PlayerAward(
            player_id=winner_player.id,
            season_id=season_id,
            award_type=award_type,
            award_level=AwardLevel.LEAGUE if scope_type == 'league' else AwardLevel.CUP,
            league_id=scope_id if scope_type == 'league' else None,
            cup_id=scope_id if scope_type == 'cup' else None,
            metadata={
                "primary_value": primary_value,
                "matches": winner_stat.matches_played,
                "goals": winner_stat.goals,
                "assists": winner_stat.assists,
                "rating": float(winner_stat.average_rating or 0),
            }
        ))
    return awards
```

### 6.4 年度最佳球员（闪电足球先生）

```python
async def award_season_best_player(season_id, season_number, db):
    # 1. 获取全服所有球员的赛季统计
    query = select(PlayerSeasonStats, Player).join(Player, PlayerSeasonStats.player_id == Player.id).where(
        PlayerSeasonStats.season_id == season_id,
        PlayerSeasonStats.matches_played >= 10
    )
    rows = await db.execute(query)

    # 2. 预加载该赛季所有奖项和球队荣誉（冠军）
    all_awards = await db.execute(select(PlayerAward).where(PlayerAward.season_id == season_id))
    all_honors = await db.execute(select(TeamHonor).where(TeamHonor.season_id == season_id))

    # 3. 计算综合得分
    candidates = []
    for stat, player in rows:
        score = 0.0
        score += float(stat.average_rating or 0) * 15          # 评分权重
        score += stat.matches_played * 0.2                      # 出场权重

        # MVP次数
        mvp_count = sum(1 for a in all_awards if a.player_id == player.id and a.award_type == AwardType.MATCH_MVP)
        score += mvp_count * 3

        # 冠军数（通过球队荣誉反查）
        # 先找到球员本赛季效力过的球队（可能有转会，但简化为当前球队或统计表中team_id）
        team_id = stat.team_id
        champ_count = sum(1 for h in all_honors if h.team_id == team_id and h.honor_type in [HonorType.LEAGUE_CHAMPION, HonorType.CUP_CHAMPION])
        score += champ_count * 30  # 联赛/杯赛冠军统一30分

        # 联赛最佳阵容/最佳位置
        league_awards = [a for a in all_awards if a.player_id == player.id and a.award_level == AwardLevel.LEAGUE]
        score += len([a for a in league_awards if a.award_type == AwardType.LEAGUE_TEAM_OF_SEASON]) * 10
        score += len([a for a in league_awards if a.award_type.startswith("league_best_")]) * 15

        candidates.append({
            "player": player,
            "stat": stat,
            "score": score,
            "metadata": {
                "rating": float(stat.average_rating or 0),
                "matches": stat.matches_played,
                "goals": stat.goals,
                "championships": champ_count,
                "mvp_count": mvp_count,
            }
        })

    # 4. 取最高分
    candidates.sort(key=lambda x: -x["score"])
    winner = candidates[0]

    award = PlayerAward(
        player_id=winner["player"].id,
        season_id=season_id,
        season_number=season_number,
        award_type=AwardType.SEASON_BEST_PLAYER,
        award_level=AwardLevel.SEASON,
        metadata=winner["metadata"],
        description=f"第{season_number}赛季 闪电足球先生"
    )
    return award
```

---

## 七、实现优先级

| 优先级 | 内容 | 预估工作量 |
|-------|------|----------|
| P0 | 数据库迁移 + PlayerAward 模型 | 1h |
| P0 | AwardService + Match MVP 自动评选 | 2h |
| P0 | 联赛奖项评选（最佳阵容 + 最佳位置 + 数据之王） | 3h |
| P0 | 杯赛数据之王评选（金靴/助攻王/金手套/金墙） | 1.5h |
| P0 | 赛季大奖评选（足球先生 + 年度最佳位置 + 赛季数据之王） | 2.5h |
| P0 | 后端 API 路由 | 1h |
| P1 | 球员页「荣誉室」Tab | 2h |
| P1 | 世界页「赛季奖项」Tab | 2h |
| P2 | 联赛页「赛季最佳」Tab | 1h |
| P2 | 杯赛页「数据之王」展示 | 1h |
| P2 | 单元测试 | 2h |

**总计：约 19.5 小时**

---

## 八、边界情况

1. **赛季中转会**：球员可能换队。统计以 `PlayerSeasonStats.team_id` 为准（即赛季结束时所在球队）。
2. **并列评分**：所有评选都有明确的 tie-breaker 规则（进球 → 助攻 → 关键数据 → 随机）。
3. **无资格球员**：出场 < 10 场的不参与联赛/赛季级奖项评选，但单场 MVP 不受影响。
4. **空赛季**：如果某赛季没有任何数据，所有奖项返回空列表。
5. **重复评选**：通过数据库 UNIQUE 约束防止同球员同赛季同类型重复获奖。
