# 合同与球员状态系统技术设计

> 版本：v1.0  
> 目标：先让合同、工资满意度、球员状态和比赛引擎快照跑通；训练、连续比赛疲劳、伤停等后续系统通过统一接口接入。

## 1. 系统目标

合同与状态系统要解决三件事：

1. **合同有经营意义**
   - 工资不只是财务支出，还会影响球员隐藏满意度。
   - 满意度进入球员状态聚合，轻微影响实际比赛表现。

2. **状态是多来源结果**
   - 状态不仅来自合同，还来自近期比赛表现、疲劳、训练负荷、连续出场、伤停、停赛、未来心理/士气事件。
   - 第一版先实现合同来源、近期比赛表现来源、基础体能来源，训练系统预留接口。

3. **玩家看到简单，系统内部可扩展**
   - 玩家只看箭头/标签：火热、良好、平淡、低迷，以及体能/伤停状态。
   - 后端保留精细数值，用于比赛引擎属性修正和后续调参。

## 2. 当前项目基础

现有 `Player` 已包含：

- `personality`：隐藏性格。
- `status`：`ACTIVE` / `INJURED` / `SUSPENDED` / `RETIRED`。
- `match_form`：`HOT` / `GOOD` / `NEUTRAL` / `LOW`。
- `fitness`：体能，0-100。
- `contract_type`：`NORMAL` / `ROOKIE` / `FREE`。
- `contract_end_season`。
- `wage`。
- `release_clause`。
- `squad_role`。

Go 比赛引擎的球员输入来自 FastAPI 组装的 `PlayerSetup`：

- `attributes`：21 项属性。
- `stamina`：初始体能。

因此第一版不需要修改 Go 引擎。后端在构建比赛请求前计算：

```
基础属性 + 状态修正 = 有效属性
fitness + 疲劳修正 = 初始 stamina
```

## 3. 核心概念

### 3.1 合同

合同定义球员与球队的雇佣关系：

- 合同类型：普通合同、新人合同、自由身。
- 合同到期赛季。
- 工资。
- 解约金。
- 阵容角色。

第一版不做复杂谈判 AI，只做玩家设定工资/年限后的结果计算。

### 3.2 工资满意度

工资满意度是隐藏值，来源于：

```
工资比例 = 实际工资 / 系统建议工资
```

工资满意度不直接展示给玩家，但影响状态聚合。

### 3.3 球员状态

球员状态是多个状态来源聚合后的结果：

```
综合状态分 = 比赛表现分 + 工资满意度分 + 疲劳分 + 训练负荷分 + 连续出场分 + 其他事件分
```

综合状态分映射为玩家可见 `match_form`：

| 综合状态分 | 可见状态 |
| --- | --- |
| `>= 6` | `HOT` 火热 |
| `2 ~ 5` | `GOOD` 良好 |
| `-1 ~ 1` | `NEUTRAL` 平淡 |
| `<= -2` | `LOW` 低迷 |

可见状态只是标签；真正进入比赛的是内部属性倍率。

### 3.4 状态来源

状态来源是可扩展接口。第一版建议支持：

| 来源 | 是否 v1 实现 | 说明 |
| --- | --- | --- |
| `contract` | 是 | 工资比例、合同年限、合同到期压力。 |
| `recent_match` | 是 | 最近 2-3 场评分。 |
| `fitness` | 是 | 现有 `fitness` 字段。 |
| `match_load` | 轻量实现 | 根据最近出场分钟数估算连续比赛劳累。 |
| `match_rust` | 是 | 连续 2–3 场未出场导致比赛生疏，轻微降低状态。 |
| `training_load` | 预留接口 | 等训练系统完成后写入。 |
| `injury` | 预留/兼容 | 已有 `status=INJURED`，后续扩展伤停天数。 |
| `suspension` | 预留/兼容 | 已有 `status=SUSPENDED`。 |
| `morale_event` | 预留 | 新闻、连胜、队长、关系等事件。 |

## 4. 数据模型

### 4.1 保留并扩展 `players`

建议新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `recommended_wage` | DECIMAL nullable | 当前合同签订时的系统建议工资快照。 |
| `wage_ratio` | DECIMAL nullable | `wage / recommended_wage`，签约后保存。 |
| `wage_satisfaction` | int default 0 | 隐藏工资满意度，范围 -3 到 +3。 |
| `state_score` | int default 0 | 最近一次聚合后的综合状态分。 |
| `state_updated_at` | datetime nullable | 最近聚合时间。 |
| `match_rust_score` | int default 0 | 比赛生疏分，范围 -4 ~ 0，栈式累积。 |

说明：

- `recommended_wage` 和 `wage_ratio` 保存签约时快照，避免球员成长后历史合同满意度每天剧烈变化。
- 续约时重新计算建议工资并覆盖快照。

### 4.2 新表：`player_contracts`

长期建议把合同从 `players` 拆出来，支持合同历史。第一版可以新建此表，但仍同步当前合同字段到 `players`，方便现有页面兼容。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | uuid/string | 主键。 |
| `player_id` | FK players.id | 索引。 |
| `team_id` | FK teams.id nullable | 自由身可为空。 |
| `season_id` | FK seasons.id nullable | 签约发生赛季。 |
| `contract_type` | enum | `NORMAL` / `ROOKIE` / `FREE`。 |
| `start_season_number` | int | 起始赛季。 |
| `end_season_number` | int nullable | 到期赛季。 |
| `wage` | DECIMAL | 赛季工资。 |
| `recommended_wage` | DECIMAL | 签约时建议工资。 |
| `wage_ratio` | DECIMAL | 工资比例快照。 |
| `wage_satisfaction` | int | 签约后的隐藏满意度。 |
| `release_clause` | DECIMAL nullable | 解约金。 |
| `squad_role` | enum/string | 阵容角色承诺。 |
| `status` | enum | `active` / `expired` / `terminated`。 |
| `created_at` / `updated_at` | datetime | 标准字段。 |

### 4.3 新表：`player_state_snapshots`

记录每次状态聚合结果，方便调试和给玩家历史趋势。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | uuid/string | 主键。 |
| `player_id` | FK players.id | 索引。 |
| `team_id` | FK teams.id nullable |  |
| `season_id` | FK seasons.id nullable |  |
| `source_event` | string | `contract_signed`、`match_finished`、`daily_tick` 等。 |
| `contract_score` | int | 合同来源分。 |
| `recent_match_score` | int | 近期比赛来源分。 |
| `fitness_score` | int | 体能来源分。 |
| `match_load_score` | int | 连续比赛来源分。 |
| `match_rust_score` | int | 比赛生疏来源分。 |
| `training_load_score` | int | 训练来源分，v1 可为 0。 |
| `morale_score` | int | 其他士气事件来源分，v1 可为 0。 |
| `total_score` | int | 聚合分。 |
| `visible_form` | enum | `HOT` / `GOOD` / `NEUTRAL` / `LOW`。 |
| `attribute_modifier_pct` | DECIMAL | 比赛属性修正百分比。 |
| `stamina_modifier` | DECIMAL | 初始体能修正。 |
| `metadata` | JSON | 调试信息。 |
| `created_at` | datetime |  |

保留最近 10-20 条即可。后续可定期清理。

### 4.4 新表：`player_state_modifiers`

可选。如果希望所有状态来源都通过统一写入，可以加这张表。第一版也可以先不建，只在 `PlayerStateService` 中实时计算。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `player_id` | FK players.id |  |
| `source` | string | `contract` / `training_load` / `morale_event` 等。 |
| `score` | int | 可正可负。 |
| `expires_at` | datetime nullable | 过期时间。 |
| `metadata` | JSON | 来源细节。 |

推荐：第一版先不建，等训练和士气事件接入时再加。

## 5. 合同规则

### 5.1 建议工资计算

建议工资由客观条件决定：

```
recommended_wage =
  base_wage_by_ovr[ovr]
  * league_factor
  * age_factor
  * contract_type_factor
  * role_factor
```

### 5.2 基础工资表

先使用配置表，不要写死在 service 中。

| OVR | 赛季工资 |
| --- | --- |
| 30 | 15000 |
| 40 | 25000 |
| 50 | 30000 |
| 55 | 35000 |
| 60 | 40000 |
| 65 | 45000 |
| 70 | 60000 |
| 80 | 120000 |
| 85 | 180000 |
| 90 | 280000 |

未命中的 OVR 用线性插值。

### 5.3 系数

联赛系数：

| 联赛级别 | 系数 |
| --- | --- |
| 1 | 1.30 |
| 2 | 1.10 |
| 3 | 1.00 |
| 4 | 0.80 |

年龄系数：

| 年龄 | 系数 |
| --- | --- |
| `<=20` | 0.60 |
| `21-25` | 1.00 |
| `26-28` | 1.10 |
| `29-30` | 0.90 |
| `31-33` | 0.70 |
| `>=34` | 0.50 |

合同类型系数：

| 类型 | 系数 |
| --- | --- |
| 普通合同 | 1.00 |
| 新人合同 | 0.40 |
| 自由身短约 | 0.85 |

阵容角色系数：

| 角色 | 系数 |
| --- | --- |
| `key_player` | 1.25 |
| `first_team` | 1.10 |
| `rotation` | 1.00 |
| `backup` | 0.85 |
| `hot_prospect` | 0.80 |
| `youngster` | 0.70 |
| `not_needed` | 0.60 |

### 5.4 工资比例与满意度

```
wage_ratio = offered_wage / recommended_wage
```

| 工资比例 | 基础满意度 |
| --- | --- |
| `< 0.70` | -3 |
| `0.70 - 0.84` | -2 |
| `0.85 - 0.94` | -1 |
| `0.95 - 1.14` | 0 |
| `1.15 - 1.29` | +1 |
| `>= 1.30` | +2 |

### 5.5 性格修正

性格隐藏，不直接展示。它只改变工资满意度对状态的权重。

| 性格 | 工资敏感系数 |
| --- | --- |
| `materialistic` 拜金 | 1.6 |
| `ambitious` 野心 | 1.4 |
| `professional` 职业 | 1.0 |
| `passionate` 激情 | 0.8 |
| `loyal` 忠诚 | 0.6 |
| `team_oriented` 团队 | 0.5 |

合同来源分：

```
contract_score = round(wage_satisfaction * money_sensitivity)
```

范围建议 clamp 到 `-4 ~ +4`。

### 5.6 合同到期压力

合同快到期时加入轻微负面状态，推动玩家处理续约。

| 条件 | 修正 |
| --- | --- |
| 合同剩 1 个赛季 | -1 |
| 合同本赛季到期 | -2 |
| 自由身 | 0，不参与球队比赛 |

这个修正可以并入 `contract_score`。

## 6. 状态聚合规则

### 6.1 来源分计算

#### 合同来源

```
contract_score = clamp(
  round(wage_satisfaction * personality_money_sensitivity) + contract_expiry_modifier,
  -4,
  +4
)
```

#### 近期比赛来源

取最近 3 场有出场的评分：

```
avg_rating = average(last_3_ratings)
```

| 平均评分 | 来源分 |
| --- | --- |
| `>= 8.0` | +4 |
| `7.2 - 7.9` | +2 |
| `6.5 - 7.1` | 0 |
| `6.0 - 6.4` | -1 |
| `< 6.0` | -3 |

如果没有近期比赛，来源分为 0。

#### 体能来源

当前项目已有 `fitness`，它是 0-100。先解释为赛前身体可用度。

| `fitness` | 来源分 | 初始体能修正 |
| --- | --- | --- |
| `>= 90` | +1 | +3 |
| `70 - 89` | 0 | 0 |
| `50 - 69` | -1 | -8 |
| `30 - 49` | -3 | -18 |
| `< 30` | -5 | -30 |

#### 连续比赛劳累来源

第一版轻量实现，不依赖训练系统：

```
recent_minutes = 最近 7 个赛季日内出场分钟数
```

| 最近出场负荷 | 来源分 |
| --- | --- |
| `>= 160 分钟` | -3 |
| `100 - 159 分钟` | -2 |
| `60 - 99 分钟` | -1 |
| `< 60 分钟` | 0 |

如果当前赛季日难以查询，先用最近 3 场出场次数估算。

#### 比赛生疏来源

`match_rust_score` 是一个带状态的累积值，像**栈**一样工作：每缺席一场正式比赛就往栈里压一层（-1），每出场一场就弹出一层（+1），始终回补之前的生疏惩罚，不单独额外加分。

**维护规则（由赛后/赛事件写入 `players.match_rust_score`）：**

| 事件 | 变化 | 说明 |
| --- | --- | --- |
| 赛季内正式比赛有出场（≥1 分钟） | +1 | 逐场回补生疏分，`min(当前值 + 1, 0)`。 |
| 赛季内正式比赛未出场（非伤停/停赛） | -1 | 进入大名单但未上场，或未进大名单均计入，`max(当前值 - 1, -4)`。 |
| 伤停/停赛期间的比赛 | 不变 | 不计入缺席，避免球员康复后立刻被惩罚。 |

**边界：**
- 上限 `0`（栈空，无生疏）。
- 下限 `-4`（栈满，连续 4 场及以上未出场的最大惩罚）。
- 友谊赛、热身赛不计入。
- 赛季切换时重置为 `0`。

**示例：**
- 连续 3 场未出场：`0 → -1 → -2 → -3`
- 第 4 场出场：`-3 → -2`
- 第 5 场出场：`-2 → -1`
- 第 6 场出场：`-1 → 0`

**聚合时：** 直接读取 `players.match_rust_score` 进入 `total_score`，不再实时统计。

与 `match_load` 形成平衡：打得太多会疲劳，太久不打会生疏，交替出场和休息才能维持最佳状态。

#### 训练负荷来源

第一版预留接口：

```
training_load_score = TrainingLoadProvider.get_player_state_score(player_id)
```

训练系统未实现时返回 0。

未来训练系统可以写入：

- 高强度训练疲劳：负分。
- 恢复训练：正分。
- 赛前专项训练：短期正分或指定属性加成。

### 6.2 聚合公式

```
total_score =
  contract_score
  + recent_match_score
  + fitness_score
  + match_load_score
  + match_rust_score
  + training_load_score
  + morale_score
```

聚合后 clamp 到 `-10 ~ +10`。

### 6.3 映射到可见状态

| `total_score` | `match_form` |
| --- | --- |
| `>= 6` | `HOT` |
| `2 - 5` | `GOOD` |
| `-1 - 1` | `NEUTRAL` |
| `<= -2` | `LOW` |

### 6.4 属性修正

状态影响要小，避免玩家感觉玄学或破坏 OVR 判断。

```
attribute_modifier_pct = clamp(total_score * 0.005, -0.05, +0.05)
```

即综合状态最多约 -5% 到 +5%。

第一版建议再收紧：

```
attribute_modifier_pct = clamp(total_score * 0.004, -0.04, +0.04)
```

合同单项通常只贡献 -2% 到 +2%，极端拜金/低薪才接近 -3%。

### 6.5 初始体能修正

```
initial_stamina =
  player.fitness
  + fitness_stamina_modifier
  + training_stamina_modifier
```

最终 clamp 到 `30 ~ 100`。

如果后续训练系统引入 PRD 中的疲劳值，可改为：

```
initial_stamina = 85 + (STA - 10) * 1.5 - fatigue * 0.3 + state_stamina_bonus
```

## 7. 服务设计

### 7.1 `ContractService`

职责：

- 计算建议工资。
- 创建合同。
- 续约合同。
- 终止合同。
- 同步 `players` 当前合同字段。
- 调用 `PlayerStateService` 刷新合同来源状态。
- 调用经济系统检查工资帽和工资支出。

核心方法：

```python
calculate_recommended_wage(player_id: str, team_id: str, contract_type: str, squad_role: str) -> Decimal
preview_contract_offer(command: ContractOfferCommand) -> ContractPreview
sign_contract(command: SignContractCommand) -> PlayerContract
renew_contract(command: RenewContractCommand) -> PlayerContract
release_player(player_id: str, team_id: str) -> None
expire_contracts(season_id: str) -> None
```

`preview_contract_offer` 返回：

- 建议工资。
- 实际工资。
- 工资比例。
- 满意度区间。
- 签约后工资帽压力。
- 是否允许提交。

### 7.2 `PlayerStateService`

职责：

- 计算所有状态来源分。
- 更新 `players.match_form`、`players.state_score`。
- 写入 `player_state_snapshots`。
- 为比赛引擎构建有效属性和初始体能。

核心方法：

```python
recalculate_player_state(player_id: str, source_event: str) -> PlayerStateSnapshot
recalculate_team_state(team_id: str, source_event: str) -> list[PlayerStateSnapshot]
calculate_state_components(player: Player) -> PlayerStateComponents
build_match_player_setup(player: Player) -> dict
apply_state_to_attributes(attributes: dict[str, int], snapshot: PlayerStateSnapshot) -> dict[str, int]
calculate_initial_stamina(player: Player, snapshot: PlayerStateSnapshot) -> float
```

### 7.3 `TrainingStateProvider`

训练系统未完成时先做空实现。

```python
class TrainingStateProvider:
    async def get_player_state_score(self, player_id: str) -> int:
        return 0

    async def get_player_stamina_modifier(self, player_id: str) -> float:
        return 0.0

    async def get_attribute_modifiers(self, player_id: str) -> dict[str, float]:
        return {}
```

未来训练系统接入时，只替换 provider，不改合同/比赛快照逻辑。

## 8. 比赛引擎集成

### 8.1 接入点

当前 `MatchEngineClient._player_payload` 直接读取基础属性和 `player.fitness`。

改造为：

1. 查询或计算玩家最新状态快照。
2. 计算 `attribute_modifier_pct`。
3. 对 21 项属性应用倍率。
4. 计算初始 `stamina`。
5. 将有效属性和初始体能传给 Go 引擎。

示例：

```python
snapshot = await player_state_service.recalculate_player_state(
    player.id,
    source_event="pre_match_snapshot",
)

attributes = player_state_service.apply_state_to_attributes(base_attributes, snapshot)
stamina = player_state_service.calculate_initial_stamina(player, snapshot)
```

Go 引擎无需知道状态来源，只消费最终属性和体能。

### 8.2 属性取整规则

基础属性范围是 1-20。状态修正后：

```
effective_attr = round(base_attr * (1 + attribute_modifier_pct))
effective_attr = clamp(effective_attr, 1, 20)
```

如果后续希望支持 20 以上的临时爆发，需要先确认 Go 引擎是否允许。第一版不要突破 20。

### 8.3 赛后回写

比赛结束后：

1. 根据 Go 引擎 `player_stats.rating` 更新球员和赛季统计。
2. 调用 `PlayerStateService.recalculate_player_state(player_id, "match_finished")`。
3. 根据出场分钟降低 `fitness` 或写入连续比赛负荷。
4. 更新 `match_rust_score`：
   - 本场有出场（≥1 分钟）：`match_rust_score = min(match_rust_score + 1, 0)`
   - 本场未出场且非伤停/停赛：`match_rust_score = max(match_rust_score - 1, -4)`
   - 伤停/停赛期间不更新。
5. 如果受伤/红黄牌系统已实现，再更新 `status`。

第一版可以先做：

```
出场 50 分钟：fitness -= 12
出场 70 分钟：fitness -= 18
未出场：fitness += 5
```

最终 clamp 到 `0 ~ 100`。

## 9. 事件流

### 9.1 签约/续约

```
玩家打开合同界面
-> ContractService.preview_contract_offer
-> 前端展示建议工资、工资比例、工资帽压力、球员大致反应
-> 玩家确认
-> ContractService.sign_contract / renew_contract
-> 写入 player_contracts
-> 同步 players 当前合同字段
-> PlayerStateService.recalculate_player_state(source_event="contract_signed")
-> InboxService 可选发送签约结果消息
```

### 9.2 赛前

```
MATCH_DAY event
-> FastAPI 加载 fixture 和首发
-> PlayerStateService 为每名首发计算状态
-> MatchEngineClient 发送有效属性和初始 stamina
-> Go 引擎模拟
```

### 9.3 赛后

```
Go 引擎返回结果
-> MatchSimulator 持久化 player_stats
-> 更新 fitness / recent match source
-> PlayerStateService.recalculate_player_state(source_event="match_finished")
-> 如状态大幅变化，可发 inbox 提醒
```

### 9.4 每日自然恢复

训练系统未完成前，增加轻量每日恢复事件：

```
DAILY_PLAYER_STATE_TICK
-> 未比赛球员 fitness +5
-> 比赛后球员不额外恢复或只 +2
-> 重算状态
```

训练系统完成后，这个事件由训练结果替代或合并。

## 10. API 设计

### 10.1 合同 API

```
GET /api/v1/players/{player_id}/contract
POST /api/v1/players/{player_id}/contract/preview
POST /api/v1/players/{player_id}/contract/sign
POST /api/v1/players/{player_id}/contract/renew
POST /api/v1/players/{player_id}/contract/release
```

`preview` 请求：

```json
{
  "team_id": "team_1",
  "contract_type": "NORMAL",
  "years": 2,
  "wage": 120000,
  "squad_role": "first_team"
}
```

`preview` 响应：

```json
{
  "recommended_wage": 100000,
  "offered_wage": 120000,
  "wage_ratio": 1.2,
  "visible_reaction": "satisfied",
  "hidden_wage_satisfaction": 1,
  "wage_cap_after_pct": 78,
  "can_submit": true,
  "warnings": []
}
```

`hidden_wage_satisfaction` 可以只在开发环境返回，正式前端不展示。

### 10.2 状态 API

```
GET /api/v1/players/{player_id}/state
GET /api/v1/teams/{team_id}/player-states
POST /api/v1/internal/players/{player_id}/state/recalculate
```

玩家可见响应只返回：

```json
{
  "player_id": "player_1",
  "visible_form": "GOOD",
  "fitness": 84,
  "availability": "ACTIVE",
  "trend": "up",
  "hints": [
    "近期表现稳定",
    "体能良好"
  ]
}
```

管理/调试响应可返回各来源分。

## 11. 前端设计

### 11.1 球员详情页

新增或完善模块：

- 当前合同：工资、到期赛季、合同类型、阵容角色。
- 续约按钮。
- 状态标签：火热/良好/平淡/低迷。
- 体能条。
- 简短提示，不展示精确分数。

提示示例：

- “近期表现不错。”
- “体能略有下降。”
- “合同问题可能影响他的投入程度。”

不要显示：“工资满意度 +2、属性 +1.5%”。

### 11.2 合同弹窗

字段：

- 年限：1-3 年，新人合同固定 2 年。
- 工资滑杆或输入框。
- 阵容角色。
- 预览：
  - 建议工资。
  - 工资帽压力。
  - 球员反应：不满 / 平常 / 满意 / 非常满意。

### 11.3 球队列表

在球员列表中展示：

- 状态小图标。
- 体能条或简写。
- 合同到期提示。

## 12. MVP 开发阶段

### Phase 1：状态快照基础

- 新增 `player_state_snapshots`。
- 给 `players` 加 `wage_ratio`、`wage_satisfaction`、`state_score`、`state_updated_at`。
- 实现 `PlayerStateService`。
- 根据现有 `fitness` 和 `match_form` 能生成快照。

### Phase 2：合同服务

- 新增 `player_contracts`。
- 实现建议工资计算。
- 实现合同 preview/sign/renew。
- 签约后写入工资满意度并刷新状态。

### Phase 3：比赛引擎快照接入

- 改造 `MatchEngineClient._player_payload`。
- 传有效属性和初始 stamina。
- 赛后根据评分和出场分钟刷新状态。

### Phase 4：前端接入

- 球员详情页展示合同和状态。
- 合同续约弹窗。
- 球队列表展示状态/体能/合同提醒。

### Phase 5：预留训练接口

- 加 `TrainingStateProvider` 空实现。
- 日后训练系统写入训练负荷和短期属性修正。

## 13. 测试策略

### 单元测试

- OVR 工资表插值。
- 建议工资计算。
- 工资比例到满意度映射。
- 性格对合同来源分的修正。
- 多来源状态聚合。
- 属性修正 clamp。
- 初始体能计算。

### 集成测试

- 签约后生成合同、同步 player 字段、生成状态快照。
- 续约后推荐工资按当前 OVR/年龄重算。
- 赛前 payload 使用有效属性而非基础属性。
- 赛后评分更新后 `match_form` 会变化。
- 低体能球员进入比赛时 stamina 下降。

### 回归测试

- Go 引擎仍能接收请求。
- 属性不会低于 1 或高于 20。
- 伤停/停赛球员不会进入首发。
- 没有合同记录的旧球员能用 `players` 字段兼容生成状态。

## 14. 默认决策与待确认项

### 默认决策

- 第一版不修改 Go 引擎。
- 状态修正在 FastAPI 构建赛前快照时完成。
- 合同影响隐藏状态，玩家只看状态箭头和简短提示。
- 训练系统未完成前，训练来源分固定为 0。
- 先不做完整球员谈判 AI，只做工资/年限/角色预览。

### 待确认项

1. `wage` 最终语义是赛季工资还是周薪。建议统一为赛季工资。
2. 是否允许球员主动拒绝低工资合同。建议 v1 不拒绝，只给强负面状态和警告。
3. 新人合同是否固定 2 年。建议固定，减少操作复杂度。
4. 是否在正式接口返回调试状态分。建议只在 admin/debug 接口返回。
5. 合同到期是否自动进入自由市场。建议做，但可以放到转会市场联动阶段。

