# 合同签约、自由市场、退役与青训闭环技术开发文档

> 版本：v1.0  
> 日期：2026-05-29  
> 范围：合同签约页、合同到期流转、自由市场页、34+ 退役、球队人数兜底、青训营成长/刷新/签约、联赛选秀大会。  
> 参考：`LSL-PRD-v5.md`、`CONTRACT-PLAYER-STATE-SYSTEM-DESIGN.md`、当前后端模型与前端路由。

## 1. 背景与目标

当前项目已经有一部分合同和球员状态基础：

- `players` 已有 `team_id`、`contract_type`、`contract_end_season`、`wage`、`recommended_wage`、`wage_ratio`、`wage_satisfaction`、`state_score`、`match_form`。
- `player_contracts`、`wage_configs`、`player_state_snapshots`、`ContractService`、`PlayerStateService` 已有雏形。
- 前端已有球员详情页合同弹窗，`/transfer/free-market`、`/youth/academy`、`/youth/draft` 页面存在，但自由市场和青训仍是 mock 数据。
- 赛季推进使用 `EventQueue`，当前赛季模板是 25 天，预算、财务、比赛、升降级和赛季结束已有事件。

本阶段目标是补齐球员流转闭环：

```
合同签约/续约
  -> 合同到期未续约
  -> 自由市场
  -> 球队低于 8 人时自动补员

青训投入
  -> 青训营自动刷新与成长
  -> 玩家签约青训球员
  -> 未签约球员进入联赛选秀
  -> 选秀未中/被放弃球员进入自由市场
```

本阶段不做复杂球员谈判 AI，不做跨队转会竞价，不做青年联赛。AI 球队只做规则驱动的基础运营。所有数值先做可配置、可调参、可测试的 v1。

## 2. PRD 口径简述与本版调整

### 2.1 保留的产品规则

- 一线队人数上限 15 人，下限 8 人。
- 合同年限可选 1-4 个赛季。
- 合同开始时间视为赛季初，合同结束时间视为赛季末。
- 合同工资允许围绕系统建议工资调整，并影响隐藏工资满意度，进而影响球员状态。
- 合同到期未续约，球员离队进入自由市场。
- 34+ 球员赛季末可能退役，年龄越高概率越高。
- 青训营有上限，每赛季自动刷新两次，把空位补满。
- 青训刷新固定在赛季第 4 天和第 8 天。
- 青训投入越高，越容易刷出低年龄、高潜力球员；球队所在联赛级别越高，刷新质量也越高。
- 青训球员在营内自动训练和成长。
- 15-17 岁青训球员允许签入一线队，但初始能力通常不足，优势主要在成长速度。
- 玩家可以签约青训球员，签约工资在正常估价上打折。
- 赛季末未被签约的青训球员进入本联赛选秀。
- 玩家可提前排序选秀志愿，默认按 OVR 排序。
- 联赛内按排名倒序选择球员。
- 选秀选中后生成 24 小时待签约入口，玩家可以签约或放弃；玩家未处理时，只要有钱且有空位就自动签约；roster 已满时跳过并发邮件提醒。
- 选秀剩余球员进入自由市场。
- 自由市场签约需要支付少量签字费。
- AI 球队需要具备基础自主运营能力，能续约、签青训、处理选秀和补足名单。

### 2.2 相对早期 PRD 的调整

- 早期 PRD 有“选秀最多 2 人”“选秀落选先进入拍卖”的描述。本版按新需求改为：每支球队每赛季选秀选择 1 名，落选直接进入自由市场。
- 早期 PRD 中新人合同系数偏低。本版使用“正常建议工资约 0.7 折”的青训/选秀签约折扣，避免青训工资低到破坏工资帽平衡。
- 当前项目赛季模板是 25 天。青训刷新固定为第 4/8 天，志愿截止和选秀日也应写入 `SeasonTimelineConfig`，不要散落在 service 中。
- 合同到期采用“赛季号 + 赛季末事件”语义，不使用真实日期跨度判断。

## 3. 关键设计原则

- `players.team_id is null` 表示自由身，但自由市场展示和价格需要独立 listing 表，不直接从 `players` 推断全部信息。
- `player_contracts` 保留合同历史，`players` 同步当前合同快照，保证现有页面兼容。
- 青训球员和一线队球员共用基础属性模型，但青训阶段需要额外状态表，避免污染一线队 roster。
- 所有赛季关键动作走 `EventQueue`，保证自动化推进和测试可复现。
- 自动补员是兜底逻辑，只在赛季末结算后执行，且优先不伤害玩家可操作空间。
- 数值放配置表或配置文件，v1 不追求最终平衡，先保证闭环可跑。

## 4. 数据模型设计

### 4.1 修改 `players`

建议新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `origin_type` | enum/string | `generated` / `academy` / `draft` / `free_market` / `auto_fill`。 |
| `academy_team_id` | FK teams.id nullable | 青训母队，用于展示和未来保护规则。 |
| `draft_league_id` | FK leagues.id nullable | 选秀所属联赛。 |
| `joined_first_team_season` | int nullable | 首次进入一线队的赛季。 |
| `retired_at_season` | int nullable | 退役发生赛季。 |

已有字段继续使用：

- `team_id = null`：自由身或尚未入队。
- `contract_type = FREE`：当前无球队合同。
- `status = RETIRED`：退役后不进入比赛和市场。
- `contract_end_season`：当前合同到期赛季号。

### 4.2 调整 `player_contracts`

已有表可继续使用，但合同年限语义要修正：

```
start_season_number = current_season.season_number
end_season_number = start_season_number + years - 1
```

示例：第 3 赛季签 1 年合同，`start=3`，`end=3`，第 3 赛季末到期。

约束：

- `years` 只能是 1-4。
- 合同生效记录同一球员只能有一条 `status=active`。
- 续约时旧 active 合同标记 `expired` 或 `terminated`，新建 active 合同。
- 青训/选秀签约使用 `contract_type=ROOKIE`，但年限仍允许 1-4；默认值建议 2。

### 4.3 新表：`free_agent_listings`

自由市场页和自动签约都从这张表读取，而不是直接列出所有无队球员。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 主键。 |
| `player_id` | FK players.id | 球员。 |
| `league_id` | FK leagues.id nullable | 来源联赛，用于本联赛优先展示或限制。 |
| `season_id` | FK seasons.id | 上架赛季。 |
| `origin` | enum/string | `contract_expired` / `released` / `draft_unselected` / `draft_declined` / `auto_generated`。 |
| `signing_fee` | DECIMAL | 自由市场签字费，签约时一次性支付。 |
| `recommended_wage` | DECIMAL | 当前建议工资快照。 |
| `listed_at_day` | int nullable | 上架赛季日。 |
| `status` | enum/string | `active` / `signed` / `expired` / `retired`。 |
| `signed_team_id` | FK teams.id nullable | 被哪队签走。 |
| `metadata` | JSON | 价格折扣、来源球队、选秀轮次等。 |

签字费通过 `FinanceService` 写入 `TRANSFER` 支出流水。签字费不替代工资，只是自由市场立即签约的轻量成本。

### 4.4 新表：`youth_academy_players`

青训营在营状态表。球员基础信息仍写入 `players`，但 `team_id` 为空，直到签约进入一线队。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 主键。 |
| `player_id` | FK players.id unique | 对应球员。 |
| `team_id` | FK teams.id | 所属青训营。 |
| `season_id` | FK seasons.id | 入营赛季。 |
| `joined_season_number` | int | 入营赛季号。 |
| `joined_day` | int | 入营日。 |
| `status` | enum/string | `in_academy` / `signed` / `released_to_draft` / `drafted` / `free_market`。 |
| `growth_speed` | enum/string | `fast` / `normal` / `slow`，前端可见。 |
| `growth_score` | DECIMAL | 内部成长速度，用于结算。 |
| `last_trained_day` | int nullable | 上次自动成长日。 |
| `signed_at_season` | int nullable | 签约赛季。 |
| `metadata` | JSON | 刷新批次、投入等级、成长历史简表。 |

年龄规则：

- 青训刷新年龄 15-18。
- 年龄仍由 `birth_offset` 和当前赛季号计算。
- 15-17 岁允许签入一线队，但生成时初始 OVR 应明显低于 18 岁球员；优势体现在成长速度和潜力。
- 未签约球员赛季末全部进入选秀池。新需求没有保留 U18 继续留营规则，v1 不做跨季留营，降低流程复杂度。

### 4.5 新表：`youth_academy_snapshots`

记录青训成长曲线，前端展示趋势。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `academy_player_id` | FK youth_academy_players.id | 青训记录。 |
| `season_id` | FK seasons.id | 赛季。 |
| `season_day` | int | 第几天。 |
| `ovr` | int | 当日 OVR。 |
| `attributes` | JSON | 当日属性快照。 |
| `growth_delta` | JSON | 本次成长的属性变化。 |

可以只保留每 2-3 天一条，避免数据膨胀。

### 4.6 新表：`draft_pools`

每个联赛每个赛季一条选秀池。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 主键。 |
| `season_id` | FK seasons.id | 赛季。 |
| `league_id` | FK leagues.id | 联赛。 |
| `status` | enum/string | `preparing` / `preferences_open` / `completed`。 |
| `opened_at_day` | int | 志愿开放日。 |
| `draft_day` | int | 选秀执行日。 |

### 4.7 新表：`draft_pool_players`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `draft_pool_id` | FK draft_pools.id | 选秀池。 |
| `player_id` | FK players.id | 球员。 |
| `source_team_id` | FK teams.id nullable | 青训来源球队。 |
| `status` | enum/string | `available` / `selected` / `free_market`。 |
| `selected_by_team_id` | FK teams.id nullable | 中选球队。 |
| `rank_snapshot` | int | 默认排序，OVR 降序后按潜力、年龄。 |

### 4.8 新表：`draft_preferences`

玩家可提前排序志愿。未提交时默认按 `rank_snapshot`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `draft_pool_id` | FK draft_pools.id | 选秀池。 |
| `team_id` | FK teams.id | 球队。 |
| `player_id` | FK players.id | 志愿球员。 |
| `priority` | int | 1 为最高。 |
| `excluded` | bool | 是否明确不选。 |

唯一约束：`(draft_pool_id, team_id, player_id)`。

### 4.9 新表：`draft_selections`

选秀选中后不立即入队，而是生成一个 24 小时待签约结果。玩家可以进入签约页接受，也可以放弃；玩家未处理时，系统在窗口结束时尝试自动签约。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `draft_pool_id` | FK draft_pools.id | 选秀池。 |
| `team_id` | FK teams.id | 获得选择权的球队。 |
| `player_id` | FK players.id | 被选中的球员。 |
| `season_id` | FK seasons.id | 赛季。 |
| `status` | enum/string | `pending` / `signed` / `declined` / `expired` / `skipped_roster_full`。 |
| `selection_order` | int | 联赛内选择顺位。 |
| `expires_at` | datetime | 签约入口失效时间，选秀结果生成后 24 小时。 |
| `metadata` | JSON | 跳过原因、默认建议工资等。 |

约束：

- 同一 `draft_pool_id + team_id` 最多一条未取消选择。
- `status=skipped_roster_full` 时不绑定球员也可以，或绑定被跳过前的候选并记录原因；实现上推荐绑定候选，方便邮件解释。

## 5. 合同签约功能

### 5.1 后端服务

扩展现有 `ContractService`：

```python
preview_contract_offer(player_id, team_id, contract_type, years, wage, squad_role)
sign_contract(player_id, team_id, contract_type, years, wage, squad_role, source)
renew_contract(player_id, team_id, years, wage, squad_role)
expire_contracts_for_season_end(season_id)
sign_free_agent(player_id, team_id, years, wage, squad_role)
sign_academy_player(academy_player_id, team_id, years, wage, squad_role)
```

需要修正：

- `years` 校验改为 1-4。
- `end_season_number = current_season_number + years - 1`。
- `calculate_recommended_wage` 的年龄应使用当前赛季号计算，而不是只用 `abs(birth_offset)`。
- `sign_contract` 前校验球队人数上限 15。
- `sign_contract` 前调用 `FinanceService.can_sign_player` 或等价方法，避免工资帽和财务限制绕过。
- 续约不改变 `team_id`，自由市场/青训签约才改变 `team_id`。
- 签约成功后刷新 `PlayerStateService`，并更新当前赛季工资支出快照。

### 5.2 工资与满意度

继续使用现有建议工资公式：

```
recommended_wage =
  base_wage_by_ovr
  * league_factor
  * age_factor
  * contract_type_factor
  * role_factor
```

本阶段调整：

- 普通合同 `contract_type_factor = 1.00`。
- 自由市场普通签约可用 `FREE` 或 `NORMAL`，推荐签约后落为 `NORMAL`。
- 青训/选秀新人签约推荐工资为正常建议工资的 `0.70`，即 `contract_type_factor.ROOKIE = 0.70`。
- 前端工资滑动范围建议为 `recommended_wage * 0.70` 到 `recommended_wage * 1.30`，但后端不依赖前端限制。

满意度映射可沿用当前设计，建议微调为：

| 工资比例 | 满意度 |
| --- | --- |
| `< 0.70` | -3 |
| `0.70 - 0.84` | -2 |
| `0.85 - 0.94` | -1 |
| `0.95 - 1.14` | 0 |
| `1.15 - 1.29` | 1 |
| `>= 1.30` | 2 |

状态影响继续由 `PlayerStateService` 汇总，不在签约服务里直接改比赛属性。

### 5.3 API

现有 `/players/{player_id}/contract/*` 可以保留，补充专用入口：

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/players/{id}/contract` | 当前合同。 |
| `POST` | `/api/v1/players/{id}/contract/preview` | 预览普通签约/续约。 |
| `POST` | `/api/v1/players/{id}/contract/sign` | 普通签约。 |
| `POST` | `/api/v1/players/{id}/contract/renew` | 续约。 |
| `POST` | `/api/v1/players/{id}/contract/release` | 解约入自由市场。 |
| `POST` | `/api/v1/free-market/{listing_id}/preview` | 自由市场签约预览。 |
| `POST` | `/api/v1/free-market/{listing_id}/sign` | 自由市场签约。 |
| `POST` | `/api/v1/youth/academy/{academy_player_id}/preview-signing` | 青训签约预览。 |
| `POST` | `/api/v1/youth/academy/{academy_player_id}/sign` | 青训签约。 |

签约请求：

```json
{
  "team_id": "uuid",
  "years": 2,
  "wage": 42000,
  "squad_role": "youngster"
}
```

预览响应：

```json
{
  "recommended_wage": 60000,
  "offered_wage": 42000,
  "wage_ratio": 0.70,
  "visible_reaction": "不满",
  "wage_cap_after_pct": 82,
  "roster_after_count": 14,
  "can_submit": true,
  "warnings": []
}
```

## 6. 合同到期、退役与自由市场

### 6.1 赛季末处理顺序

在 `SeasonService._handle_season_end` 中不要只结束赛季并立刻创建新赛季，应插入 roster 闭环服务。建议顺序：

1. 关闭赛季财务。
2. 处理 34+ 球员退役。
3. 处理合同到期未续约。
4. 生成自由市场 listing。
5. 青训未签约球员进入选秀池。
6. 执行选秀分配。
7. 选秀未中或被放弃签约的球员进入自由市场。
8. 对低于 8 人的球队执行自动补员。
9. 完成赛季结束，创建并启动下赛季。

实现上可新增 `RosterLifecycleService.close_season(season_id)`，由 `SeasonService` 调用。

### 6.2 退役规则

只在赛季末判断 `status=ACTIVE` 且未进入青训营的球员。

建议概率：

| 年龄 | 退役概率 |
| --- | --- |
| 34 | 8% |
| 35 | 15% |
| 36 | 25% |
| 37 | 40% |
| 38 | 60% |
| 39+ | 85% |

退役动作：

- `players.status = RETIRED`
- `players.team_id = null`
- `players.contract_type = FREE`
- active 合同标记 `terminated`
- active free listing 标记 `retired`
- 发邮件通知原球队

### 6.3 合同到期

赛季末处理：

```python
active_contract.end_season_number <= current_season.season_number
```

到期动作：

- 合同标记 `expired`。
- 球员 `team_id = null`。
- 球员 `contract_type = FREE`。
- 球员 `contract_end_season = null`。
- 工资快照可保留作历史，也可将当前工资设为 0；推荐设为 0，listing 保留建议工资。
- 创建 `free_agent_listings(origin="contract_expired")`。
- 邮件通知原球队。

### 6.4 自由市场签约

自由市场页展示 `free_agent_listings.status=active` 且球员未退役。

签约流程：

1. 玩家点击签约。
2. 进入合同签约页或弹窗。
3. 默认带入系统建议工资和 1-4 年合同。
4. 提交后调用 `ContractService.sign_free_agent`。
5. 校验 roster 上限、工资帽、listing 状态。
6. 校验并扣除签字费。
7. 写合同，设置 `player.team_id`，listing 标记 `signed`。

签字费建议公式：

```python
base_fee = player.market_value * origin_factor * age_factor
signing_fee = clamp(base_fee, min_fee, max_fee)
```

建议参数：

| 来源 | `origin_factor` |
| --- | --- |
| 合同到期自由身 | 0.08 |
| 解约球员 | 0.06 |
| 选秀未签约/落选 | 0.04 |
| 选秀被放弃 | 0.04 |
| 系统兜底生成 | 0.02 |

年龄系数：

| 年龄 | `age_factor` |
| --- | --- |
| `<=20` | 1.15 |
| `21-28` | 1.00 |
| `29-33` | 0.75 |
| `>=34` | 0.45 |

`min_fee` 建议为同联赛 1 名 OVR 35 球员建议工资的 `10%`，`max_fee` 建议为该球员建议工资的 `50%`。这样自由市场有成本，但不会比一个赛季工资更重要。

v1 暂不做每 48 小时最多 2 人的限制，除非需要强约束市场节奏；这个规则可作为 `free_agent_signing_cooldowns` 后续补充。

## 7. 球队人数上下限与自动补员

### 7.1 校验规则

- 手动签约前：球队当前 active roster 数 `< 15`。
- 解约/放弃操作后允许暂时低于 8，但赛季末必须自动修复。
- 比赛阵容选择继续由现有比赛逻辑处理，不在本阶段改比赛人数规则。

active roster 定义：

```sql
players.team_id = :team_id
AND players.status IN ('ACTIVE', 'INJURED', 'SUSPENDED')
```

### 7.2 自动补员顺序

当赛季末球队人数 `< 8`：

1. 优先自动签约本队青训营剩余球员，按 OVR 降序、年龄升序、潜力降序。
2. 若青训不足，从本联赛选秀未中/被放弃池里签 OVR 较低且符合工资帽的球员。
3. 若仍不足，生成低数值兜底球员。

兜底球员规则：

- 年龄 20-28。
- OVR 35-45。
- 潜力 C/D。
- 合同 `NORMAL`，1 年。
- 工资使用同级最低建议工资或 `wage_config` 中 OVR 35 插值。
- `origin_type = auto_fill`。

自动补员必须写邮件，避免玩家觉得球员凭空出现。

## 8. 青训系统

### 8.1 服务划分

新增 `YouthAcademyService`：

```python
refresh_academy_players(season_id, day)
train_academy_players(season_id, day)
list_academy(team_id, season_id)
preview_signing(academy_player_id, team_id, years, wage)
sign_player(academy_player_id, team_id, years, wage, squad_role)
release_to_draft(academy_player_id)
release_unsigned_to_draft(season_id)
```

新增 `DraftService`：

```python
open_preferences(season_id)
upsert_preferences(draft_pool_id, team_id, preferences)
run_draft(season_id)
move_unselected_to_free_market(season_id)
```

新增或扩展 `PlayerGenerator`：

```python
generate_youth_player(team, season_number, investment_level)
generate_auto_fill_player(team, season_number)
```

### 8.2 青训刷新

每赛季固定刷新两次，配置放进 `SeasonTimelineConfig`：

```python
youth_refresh_days = (4, 8)
youth_training_interval_days = 2
youth_capacity = 8
draft_preferences_open_day = 22
draft_day = 24
```

刷新规则：

- 对每支球队计算当前在营人数。
- 空位数 = `8 - in_academy_count`。
- 每次刷新最多填满空位。
- 生成年龄 15-18 的青训球员。
- 球员 `team_id = null`，`origin_type = academy`，`academy_team_id = team.id`。
- 创建 `youth_academy_players(status=in_academy)`。
- 创建初始 `youth_academy_snapshots`。

### 8.3 青训投入影响

使用 `TeamBudgetPlan.youth_pct` 或 `TeamSeasonFinance.youth_budget` 推导投入等级，同时叠加球队当前联赛级别。

建议 v1 分桶：

| 青训投入比例 | 年龄倾向 | 潜力倾向 | 初始 OVR |
| --- | --- | --- | --- |
| `<= 10%` | 17-18 更多 | C/D 更多 | 28-42 |
| `11%-17%` | 均衡 | B/C 更多 | 30-45 |
| `18%-25%` | 15-16 更多 | A/B 更多，少量 S | 32-48 |

联赛级别修正：

| 联赛级别 | 潜力池修正 | 初始 OVR 修正 | 说明 |
| --- | --- | --- | --- |
| 1 | 高潜概率 +20% | +3 到 +6 | 顶级联赛更容易吸引优质苗子。 |
| 2 | 高潜概率 +10% | +1 到 +3 | 略优于平均。 |
| 3 | 无修正 | 0 | 基准。 |
| 4 | 高潜概率 -10% | -1 到 -3 | 仍可能出好苗子，但概率更低。 |

年龄与初始能力修正：

| 年龄 | 初始 OVR 修正 | 成长速度倾向 |
| --- | --- | --- |
| 15 | -8 到 -12 | fast 概率最高 |
| 16 | -5 到 -8 | fast/normal |
| 17 | -2 到 -5 | normal 为主 |
| 18 | 0 | 当前战力最好，成长速度略低 |

注意：高投入和高级联赛只提高概率，不保证每次出高潜。否则会破坏长期平衡。

### 8.4 青训成长

每 `youth_training_interval_days` 自动训练一次。

成长算法：

```python
growth_budget =
  base_growth
  * growth_speed_factor
  * youth_investment_factor
  * facility_factor
  * age_factor
  * random_factor
```

建议系数：

| 项 | 值 |
| --- | --- |
| `base_growth` | 0.20-0.45 属性点/次 |
| fast | 1.30 |
| normal | 1.00 |
| slow | 0.70 |
| age 15 | 1.20 |
| age 16 | 1.10 |
| age 17 | 1.00 |
| age 18 | 0.90 |

属性增长不能超过 `potential_max` 对应上限。实现可优先提升该位置权重高的属性，少量随机提升其他属性。

### 8.5 青训签约

玩家在青训营页点击签约，进入合同签约弹窗：

- 默认 `contract_type=ROOKIE`。
- 默认年限 2，可选 1-4。
- 建议工资 = 普通建议工资 * 0.70。
- 阵容角色默认 `youngster` 或 `hot_prospect`。
- 成功后：
  - `players.team_id = team_id`
  - `youth_academy_players.status = signed`
  - `players.joined_first_team_season = current_season_number`
  - 生成 `player_contracts`
  - 刷新球员状态

签约失败常见原因：

- 一线队已满 15 人。
- 工资帽或财务危机限制。
- 该青训球员已进入选秀或市场。

## 9. 选秀大会

### 9.1 选秀池来源

赛季末将所有未签约青训球员按所属球队当前联赛聚合：

```python
league_id = academy_team.current_league_id
```

每个联赛创建一个 `draft_pool`。同联赛球队只从本联赛池选择。

### 9.2 志愿排序

志愿开放日开始后：

- 玩家可以查看本联赛选秀池。
- 默认排序为 OVR 降序、潜力档降序、年龄升序。
- 玩家可以提交 `priority` 或排除某些球员。
- 截止到选秀执行前。

### 9.3 分配规则

按联赛排名倒序，每队选择 1 名：

1. 获取当前赛季 `LeagueStanding`，按 `position DESC` 排序，第 8 名先选，第 1 名后选。
2. 对每队读取志愿列表；未提交则使用默认排序。
3. 跳过 `excluded=true` 和已被选球员。
4. 选中第一名可用球员。
5. 若志愿内无可用球员，则按默认池补选。
6. 球队若 roster 已满 15，跳过本队选择，并发送邮件提醒“阵容已满，无法参与本次选秀签约”。

选中后动作：

- 创建 `draft_selections(status=pending)`。
- 玩家进入选秀结果页或球员详情页，点击签约入口进入新人合同签约页。
- 默认 `contract_type=ROOKIE`、默认 2 年、建议工资为正常建议工资的 0.70。
- 玩家可以选择放弃签约；放弃后该球员进入自由市场。
- AI 球队由 `AITeamManagementService` 自动判断接受或放弃。

24 小时窗口结束：

- 玩家球队若未处理，系统尝试自动签约。
- 自动签约条件：roster `< 15`、球队余额足够支付签字费或签约即时成本、工资帽/财务限制允许、球员仍未被签走且未退役。
- 自动签约成功：`draft_selections.status=signed`，生成新人合同，并发送邮件说明“选秀球员已自动签约”。
- 自动签约失败：`draft_selections.status=expired`，球员进入自由市场，并发送邮件说明失败原因。
- AI 球队不使用“未处理自动签”兜底作为主要逻辑；AI 在选秀结束后由 `AITeamManagementService` 简单判断签约或放弃。若 AI 判断流程异常未处理，再走同样的 24 小时兜底。

未中球员：

- `draft_pool_players.status = free_market`
- `youth_academy_players.status = free_market`
- 创建 `free_agent_listings(origin="draft_unselected")`

被选中但被玩家或 AI 放弃的球员创建 `free_agent_listings(origin="draft_declined")`。

## 10. 赛季事件接入

扩展 `EventType`：

```python
YOUTH_REFRESH = "youth_refresh"
YOUTH_TRAINING = "youth_training"
DRAFT_PREFERENCES_OPENED = "draft_preferences_opened"
DRAFT_RUN = "draft_run"
ROSTER_LIFECYCLE_CLOSED = "roster_lifecycle_closed"
```

扩展 `EventQueue.build_season_events`：

- `youth_refresh_days`：推送 `YOUTH_REFRESH`。
- 每 2 天推送 `YOUTH_TRAINING`，或在每日 `MATCH_DAY` 后轻量调用。
- `draft_preferences_open_day`：推送 `DRAFT_PREFERENCES_OPENED`。
- `draft_day`：推送 `DRAFT_RUN`。
- `SEASON_END` 前推送 `ROSTER_LIFECYCLE_CLOSED`，或在 `_handle_season_end` 内同步调用。

推荐先用 `_handle_season_end` 同步调用 `RosterLifecycleService.close_season`，减少事件数量；青训刷新和训练则独立事件，方便玩家看到赛季中变化。

AI 球队运营不需要单独事件类型，v1 直接挂在既有事件之后：

- `YOUTH_REFRESH` 后调用 `run_midseason_academy_decisions`。
- `DRAFT_PREFERENCES_OPENED` 后调用 `run_pre_draft_preferences`。
- `DRAFT_RUN` 后调用 `run_draft_selection_decisions`。
- `ROSTER_LIFECYCLE_CLOSED` 前调用 `run_season_end_roster_decisions`。

## 11. 后端 API 规划

### 11.1 青训

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/teams/{team_id}/youth/academy` | 青训营列表、预算、刷新信息。 |
| `POST` | `/api/v1/youth/academy/{id}/preview-signing` | 青训签约预览。 |
| `POST` | `/api/v1/youth/academy/{id}/sign` | 签约入一线队。 |
| `POST` | `/api/v1/youth/academy/{id}/release` | 放弃，进入选秀候选。 |
| `GET` | `/api/v1/youth/academy/{id}/growth` | 成长曲线。 |

### 11.2 选秀

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/leagues/{league_id}/draft` | 当前赛季选秀池和阶段。 |
| `GET` | `/api/v1/teams/{team_id}/draft/preferences` | 我的志愿。 |
| `PUT` | `/api/v1/teams/{team_id}/draft/preferences` | 保存志愿排序。 |
| `GET` | `/api/v1/leagues/{league_id}/draft/results` | 选秀结果。 |
| `GET` | `/api/v1/teams/{team_id}/draft/selections` | 本队待签约选秀结果。 |
| `POST` | `/api/v1/draft/selections/{selection_id}/preview-signing` | 选秀球员签约预览。 |
| `POST` | `/api/v1/draft/selections/{selection_id}/sign` | 签约选秀球员。 |
| `POST` | `/api/v1/draft/selections/{selection_id}/decline` | 放弃签约，球员进入自由市场。 |
| `POST` | `/api/v1/internal/draft/selections/expire` | 处理 24 小时到期的待签约结果，由事件或后台任务调用。 |

### 11.3 自由市场

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/free-market` | listing 列表，支持位置、年龄、OVR、来源筛选。 |
| `GET` | `/api/v1/free-market/{listing_id}` | listing 详情。 |
| `POST` | `/api/v1/free-market/{listing_id}/preview` | 签约预览。 |
| `POST` | `/api/v1/free-market/{listing_id}/sign` | 签约。 |

自由市场 preview 响应需要额外返回：

```json
{
  "signing_fee": 24000,
  "balance_after_fee": 1380000,
  "can_pay_signing_fee": true
}
```

## 12. 前端开发

### 12.1 合同签约弹窗

已有 `ContractModal` 可扩展：

- 年限选择改为 1-4。
- 支持来源模式：普通续约、自由市场、青训签约、选秀签约。
- 工资输入默认建议工资，提供 `70% / 100% / 130%` 快捷按钮。
- 展示：
  - 建议工资
  - 预计工资帽压力
  - 签约后 roster 人数
  - 球员可见反应
  - 警告文案
- 不展示隐藏满意度。

### 12.2 自由市场页

替换 mock 数据：

- 调用 `GET /free-market`。
- 卡片展示姓名、年龄、位置、OVR、潜力档、来源、签字费、建议工资、上架赛季。
- 点击签约打开合同弹窗。
- 筛选：位置、年龄、OVR、来源。

### 12.3 青训营页

替换 mock 数据：

- 调用 `GET /teams/{team_id}/youth/academy`。
- 展示在营人数 `x/8`、本赛季青训投入、下次刷新日、训练成长曲线。
- 每名球员展示年龄、位置、OVR、成长速度、入营天数。
- 操作：签约、放弃。
- 签约按钮应在 roster 15 人时禁用并提示。

### 12.4 选秀页

替换 mock 数据：

- 调用 `GET /leagues/{league_id}/draft`。
- `preferences_open` 阶段允许拖拽排序并提交。
- 默认按 OVR 排序。
- `completed` 阶段展示每队选择结果。
- 当前球队高亮展示选中球员、待签约状态和放弃入口。

## 13. 迁移与初始化

新增 Alembic migration：

- `players` 新字段。
- `free_agent_listings`。
- `youth_academy_players`。
- `youth_academy_snapshots`。
- `draft_pools`。
- `draft_pool_players`。
- `draft_preferences`。
- `draft_selections`。
- 必要索引和唯一约束。

初始化脚本：

- `backend/scripts/init_wage_configs.py` 调整 `ROOKIE` 系数为 `0.70`。
- 新增 `backend/scripts/backfill_contracts.py`：为已有 `players` 创建 active `player_contracts`。
- 新增 `backend/scripts/seed_youth_for_current_season.py`：开发环境补青训数据。

## 14. AI 球队自主运营设计

### 14.1 目标

AI 球队不需要在 v1 做复杂长期规划，但必须保证全 AI 联赛可以持续运转：

- 会续约核心球员，避免全队合同自然流失。
- 会签约合适青训球员。
- 会处理选秀待签约结果。
- 会在自由市场补足短板和人数。
- 会遵守工资帽、roster 上限 15 和下限 8。
- 决策有基础判断，不是纯随机。

### 14.2 服务设计

新增 `AITeamManagementService`：

```python
run_season_start_planning(season_id)
run_midseason_academy_decisions(season_id, day)
run_pre_draft_preferences(season_id)
run_draft_selection_decisions(season_id)
run_season_end_roster_decisions(season_id)
```

推荐在这些节点调用：

| 节点 | 动作 |
| --- | --- |
| 赛季开始 | 检查合同结构、工资帽、名单人数。 |
| 青训刷新后 | 判断是否提前签约明显高潜或可用球员。 |
| 志愿开放日 | 为 AI 球队生成选秀志愿。 |
| 选秀结束后 | 判断是否签约 `draft_selections`。 |
| 赛季末闭环前 | 续约关键球员、补足人数、放弃低价值青训。 |

### 14.3 AI 续约策略

AI 对每名合同本赛季到期或下赛季到期的球员计算留队分：

```python
keep_score =
  ovr_score
  + potential_score
  + age_score
  + position_need_score
  + form_score
  - wage_pressure_penalty
```

建议规则：

- OVR 排名前 8 的球员优先续约。
- 年龄 34+ 球员除非仍是位置前 2，否则通常不续约。
- 18-23 岁且潜力 A/S 的球员优先续约。
- 工资帽压力超过 95% 时，只续约 `keep_score` 前 6-8 名。
- 工资报价使用建议工资：
  - 核心球员：`recommended_wage * 1.00`
  - 普通轮换：`recommended_wage * 0.95`
  - 老将/边缘：`recommended_wage * 0.85`
- 合同年限：
  - 18-24 岁高潜：3-4 年
  - 25-30 岁主力：2-3 年
  - 31-33 岁：1-2 年
  - 34+：1 年

### 14.4 AI 青训签约策略

AI 对本队青训球员计算青训签约分：

```python
academy_score =
  potential_letter_score
  + growth_speed_score
  + position_need_score
  + age_growth_score
  + current_ovr_score
  - roster_pressure_penalty
```

建议规则：

- roster 未满 15 且球员潜力 A/S，倾向签约。
- 15-17 岁球员只在成长速度 fast 或潜力 A/S 时优先签。
- 18 岁且 OVR 能进入本队前 12，倾向签约。
- 工资使用 `ROOKIE` 建议工资，不主动压低，避免状态惩罚。
- 若 roster 接近 15，只签 `academy_score` 最高的 1-2 人。

### 14.5 AI 选秀策略

志愿排序：

- 默认按 `draft_value_score` 排序，而不是纯 OVR。

```python
draft_value_score =
  ovr * 1.0
  + potential_bonus
  + growth_speed_bonus
  + position_need_bonus
  - age_penalty
```

签约判断：

- roster 满 15 时自动跳过，并写邮件。
- roster 未满时，若选中球员 `draft_value_score` 高于最低门槛则签约。
- 门槛建议按联赛级别调整：
  - 1 级联赛：只签高潜或 OVR 接近替补水平的球员。
  - 2-3 级联赛：签大多数 B+ 潜力或位置短缺球员。
  - 4 级联赛：更积极签约，补充低成本战力。
- 放弃的选秀球员进入自由市场。
- AI 如果在选秀后没有成功处理 pending selection，24 小时到期任务仍会按通用自动签约条件兜底。

### 14.6 AI 自由市场与自动补员

AI 自由市场签约只用于两类场景：

- roster 少于 10，需要补深度。
- 某位置人数为 0 或明显不足。

选择规则：

- 优先本联赛来源球员。
- 优先签字费低、工资不超过建议工资 1.0 倍的球员。
- 只签 1-2 年。
- 工资帽压力超过 100% 时不主动签自由市场，除非 roster 低于 8。

自动补员仍由 `RosterLifecycleService` 兜底，不依赖 AI 判断。

### 14.7 AI 与玩家球队边界

- `Team.user_id` 对应系统 AI 用户或用户类型可用于判断 AI 球队；若当前没有明确字段，应在 `User` 增加 `is_ai` 或 `user_type`。
- AI 服务只处理 AI 球队，不替玩家自动续约或签约，除非是 roster 下限兜底。
- 对玩家球队的自动行为必须发邮件；对 AI 球队也应记录邮件或系统日志，方便调试。

## 15. 测试计划

### 15.1 单元测试

- 合同年限 1-4，`end_season_number = start + years - 1`。
- 建议工资按当前赛季年龄计算。
- 青训折扣为普通建议工资 0.70。
- 工资比例映射满意度。
- roster 上限 15 校验。
- 34+ 退役概率函数可用固定 random seed 测试。
- 自动补员将球队补到 8 人。
- 青训刷新把营位补到 8 人。
- 青训成长不超过潜力上限。
- 选秀按排名倒序且每队最多 1 人。
- 选秀选中后生成 24 小时 `draft_selections`，不会立即签约。
- 玩家 24 小时未处理时，有钱且有空位会自动签约，否则进入自由市场并发邮件。
- roster 满员球队在选秀中被跳过并生成邮件。
- 选秀未中或被放弃签约的球员进入自由市场。
- AI 续约策略会保留核心球员并放弃低价值老将。
- AI 青训策略会优先签高潜快成长球员。

### 15.2 集成测试

- 赛季末：退役 -> 合同到期 -> 自由市场 -> 青训入选秀 -> 选秀 -> 自动补员的完整链路。
- 合同到期未续约球员在自由市场可签回。
- 低于 8 人球队优先签青训，青训不足时生成低数值球员。
- 青训球员签约后出现在球队名单，原青训记录变为 `signed`。
- 选秀提交志愿后，按志愿选择未被选中的最高优先级球员。
- 选秀签约入口接受后球员入队，放弃后球员进入自由市场。
- 全 AI 联赛跑 2-3 个赛季后，各队 roster 仍在 8-15 人内。

### 15.3 前端验证

- 球员详情续约弹窗年限 1-4 可用。
- 自由市场列表为空、加载中、错误、签约成功状态可用。
- 青训营人数、成长曲线、签约/放弃状态可用。
- 选秀志愿排序保存后刷新页面仍保持。

## 16. 推荐开发顺序

1. 修正并补强 `ContractService`：合同年限、赛季末到期、工资帽/roster 校验。
2. 实现 `free_agent_listings` 和自由市场 API，把合同到期/解约接入自由市场。
3. 实现 `RosterLifecycleService`：退役、合同到期、自动补员。
4. 实现青训数据模型、青训刷新和成长事件。
5. 实现青训签约，复用合同弹窗和 `ContractService`。
6. 实现选秀池、志愿排序、选秀执行、`draft_selections` 24 小时签约入口、到期自动处理、落选/放弃入自由市场。
7. 实现 `AITeamManagementService`，先接入续约、青训签约、选秀签约三个关键点。
8. 替换前端自由市场、青训营、选秀页 mock 数据。
9. 补完整链路集成测试和全 AI 多赛季冒烟测试。

## 17. 已确认口径

1. 15-17 岁青训球员允许直接签入一线队，但初始能力通常不足，主要价值是成长速度快。
2. 青训刷新质量同时受青训投入和联赛级别影响，高级联赛更容易刷出高潜力、高质量球员。
3. 自由市场签约需要支付少量签字费，签字费按身价、来源和年龄折算，不能压过工资帽主约束。
4. 选秀 roster 满员球队跳过本次选择，并发送邮件提醒。
5. 选秀选中后生成 24 小时签约入口，玩家可以签约，也可以放弃签约；未处理时有钱且有空位会自动签约，否则进入自由市场。
6. 退役球员保留历史数据，但不再进入比赛、合同和市场流程。
7. 青训刷新固定为赛季第 4 天和第 8 天。
8. AI 球队需要基础自主运营能力，保证全 AI 联赛能自行续约、签青训、处理选秀和补足名单。
