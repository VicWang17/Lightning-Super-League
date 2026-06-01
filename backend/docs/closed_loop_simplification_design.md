# 闭环系统简化技术开发文档

## 1. 背景

当前合同、青训、选秀、自由市场、财政约束已经能形成基础闭环，但测试暴露出系统复杂度偏高：

- 硬工资帽会频繁卡住 AI 签约/续约，调高后又几乎没有存在感。
- 完整选秀大会引入了志愿、选秀池、待签约、24 小时过期、自由市场回流等多段流程，维护成本高。
- 15 人一线队上限过紧，导致 AI 和玩家几乎没有青训签约空间。
- 青训、自由市场、合同到期、退役已经足够支撑“新人出现、老人流失、球队补强”的基本游戏循环。

本方案目标是降低系统复杂度，同时保留核心游戏性。

## 2. 产品决策

### 2.1 工资帽

将硬工资帽移除，改为软财政压力。

取消内容：

- 签约/续约时不再因为 `wage_cap` 超限直接失败。
- AI 不再把工资帽作为硬性签约门槛。

保留内容：

- `wage_cap` 或 `wage_budget` 可继续作为财务分析和 UI 展示指标。
- 工资压力继续影响财务健康、赞助修正、预算策略、邮件提醒。
- 极端工资压力可以触发软惩罚，例如财政健康下降、赞助降低、转会预算减少、AI 降低续约出价。

建议语义调整：

- `wage_cap` 改名方向：`wage_guideline` 或 `wage_budget_reference`。
- 如果暂不改数据库字段，可保留字段名，但业务上只当参考线使用。

### 2.2 选秀大会

移除完整选秀大会，未签青训直接进入新人自由市场。

取消内容：

- 选秀池创建。
- 志愿排序。
- 每联赛倒序选秀。
- 选秀后 24 小时待签约结果。
- 未签选秀结果过期逻辑。

新增简化机制：

- 赛季末未被一线队签约的青训球员进入新人自由市场。
- 新人自由市场有保护期。
- 保护期内低排名球队 AI 先挑一轮。
- 保护期结束后，剩余新人进入普通自由市场，玩家和 AI 均可签约。

### 2.3 球队人数上限

保留一线队人数上限，但从 `15` 提高到 `18` 或 `20`。

推荐值：

- 一线队上限：`18`
- 一线队下限：`8`
- AI 目标人数：`15-17`
- AI 保留空位：至少 `1` 个，便于赛季末签青训或自由市场补人。

保留上限的理由：

- 防止强队无限囤积球员。
- 保持自由市场有流动性。
- 给弱队补强留下空间。

## 3. 新闭环流程

### 3.1 赛季中

1. 青训营按赛季配置刷新球员。
2. 青训球员自动训练成长。
3. 玩家可以随时签约青训球员。
4. AI 可以在刷新后或赛季中检查青训球员，但默认只签明显高价值球员，且不会填满全部名额。

### 3.2 赛季末

建议 `SEASON_END` 内部顺序：

1. AI 续约关键球员。
2. 34+ 球员按年龄概率退役。
3. 合同到期且未续约球员离队，进入普通自由市场。
4. 玩家球队保留人工入口处理青训签约。
5. AI 球队在释放名额后签约本队青训。
6. 未签青训进入新人自由市场保护池。
7. 新人自由市场保护期：低排名球队 AI 先挑一轮。
8. 保护期剩余新人进入普通自由市场。
9. 自动补员兜底，确保所有球队不低于 8 人。
10. 创建并启动下一赛季。

## 4. 新人自由市场保护期

### 4.1 设计目标

保护期用于替代选秀大会的公平性功能，但不引入复杂志愿和待签约系统。

目标：

- 给弱队优先补充年轻潜力球员的机会。
- 避免强队垄断青训流出球员。
- 保持流程自动化，便于 AI 联赛长期运行。

### 4.2 保护池来源

赛季末满足以下条件的青训球员进入保护池：

- `YouthAcademyPlayer.status == IN_ACADEMY`
- 当前赛季未被原队签约
- 球员未退役、未签约、无一线队 `team_id`

进入保护池后：

- `YouthAcademyPlayer.status` 可改为 `FREE_MARKET`
- `Player.origin_type` 保留 `ACADEMY`
- 创建 `FreeAgentListing`
- `FreeAgentListing.origin` 建议新增 `ACADEMY_RELEASED`
- `FreeAgentListing.extra_data` 标记：

```json
{
  "rookie_protected": true,
  "source_team_id": "...",
  "protection_round": 1
}
```

### 4.3 保护期规则

保护期只执行一轮 AI 优先挑选。

排序规则：

1. 按联赛等级分组处理，低级联赛和高级联赛可以各自处理。
2. 同一联赛内按上赛季排名倒序。
3. 如果没有上赛季排名，按当前球队战力或随机顺序兜底。
4. 每支队最多签 1 名保护池新人。
5. 只有 AI 球队自动参与保护挑选。
6. 玩家球队不自动挑选，但可以在保护期结束后从普通自由市场签约。

是否允许玩家参与保护期：

- v1 不建议。玩家参与会需要 UI、排序、倒计时、确认等额外流程。
- 玩家球队可以收到邮件：“新人自由市场保护期结束，若干新人进入自由市场。”

### 4.4 AI 保护期挑选逻辑

每支 AI 球队按以下条件判断是否签约：

硬条件：

- 一线队人数 `< ROSTER_MAX`
- 球员无队伍
- 球员 listing 仍 active
- 球队现金余额不为严重负数

建议软条件：

- 一线队人数低于 AI 目标人数时更积极。
- 位置短缺时提高该位置评分。
- 年龄越小、潜力越高、成长速度越快，评分越高。
- 如果工资压力高，降低签约意愿，但不硬拦截。

示例评分：

```text
rookie_score =
  potential_score
  + growth_speed_score
  + age_score
  + ovr_score
  + position_need_score
  + roster_need_score
  - wage_pressure_penalty
```

建议阈值：

- `rookie_score >= 35`：签约
- `25 <= rookie_score < 35`：仅当阵容人数低于 14 时签约
- `< 25`：跳过

合同建议：

- 合同类型：`ROOKIE`
- 年限：`2` 年
- 工资：正常估价的 `0.70-0.80`
- 角色：`YOUNGSTER`
- 签字费：无或极低

### 4.5 保护期结束

保护期一轮完成后：

- 已签约 listing 标记为 `SIGNED`
- 未签约 listing 清除 `rookie_protected` 标记，变成普通自由市场 active listing
- AI 普通自由市场补人逻辑可以继续处理低人数球队

## 5. 数据模型调整

### 5.1 FreeAgentOrigin

建议新增：

```python
ACADEMY_RELEASED = "academy_released"
```

用于区分：

- 合同到期自由球员
- 解约自由球员
- 青训流出新人
- 自动生成兜底球员

### 5.2 FreeAgentListing.extra_data

复用 JSON 字段，不新增表也可以完成 v1。

建议字段：

```json
{
  "rookie_protected": true,
  "source_team_id": "team_id",
  "source_academy_player_id": "academy_player_id",
  "protection_season_number": 3,
  "protection_processed": false
}
```

### 5.3 Draft 相关表

v1 可不删除表，只停止写入和使用：

- `draft_pools`
- `draft_pool_players`
- `draft_preferences`
- `draft_selections`

保留表的好处：

- 避免大规模迁移风险。
- 如果未来重新引入选秀，可以复用。

需要移除或停用的事件：

- `DRAFT_PREFERENCES_OPEN`
- `DRAFT_RUN`
- `DRAFT_SIGNING_EXPIRE`

可以保留枚举定义，但不再排入赛季事件。

## 6. 服务改造点

### 6.1 FinanceService

调整方向：

- `can_sign_player()` 不再因为工资参考线超限返回 false。
- 保留余额校验，例如余额低于极端阈值时拒绝非兜底签约。
- 新增或调整工资压力计算方法，用于 AI 决策。

建议方法：

```python
async def get_wage_pressure(team_id: str, season_id: str | None = None) -> Decimal:
    ...
```

工资压力影响：

- 赞助健康修正
- AI 续约出价
- AI 自由市场积极性
- 邮件提醒

### 6.2 ContractService

调整方向：

- 签约/续约不再因为工资帽超限失败。
- 保留 roster 上限校验。
- 保留余额/破产校验。
- 青训签约继续使用折扣工资。

重点：

- 续约失败不能污染旧合同状态。
- 新合同创建成功后再关闭旧合同。

### 6.3 RosterLifecycleService

新的赛季末职责：

```text
close_season:
  process_retirements
  process_contract_expirations
  ai_sign_academy_after_slots_open
  release_unsigned_academy_to_rookie_market
  run_rookie_market_protection
  release_remaining_rookies_to_normal_market
  auto_fill_min_roster
```

移除职责：

- 创建选秀池
- 执行选秀
- 处理选秀待签过期

### 6.4 YouthAcademyService

新增或改造：

```python
async def release_unsigned_to_rookie_market(season_id: str) -> dict:
    ...
```

行为：

- 将未签青训创建为 `FreeAgentListing`
- 标记 `rookie_protected = true`
- 更新青训状态为 `FREE_MARKET`

原 `release_unsigned_to_draft()` 停用。

### 6.5 AITeamManagementService

保留：

- AI 续约
- AI 青训签约
- AI 自由市场补人

新增：

```python
async def run_rookie_market_protection(season_id: str) -> dict:
    ...
```

输出统计：

```json
{
  "teams_processed": 256,
  "rookie_candidates": 1800,
  "signed": 42,
  "skipped_full": 120,
  "skipped_low_score": 90,
  "skipped_finance": 4
}
```

日志要求：

- 终端压测必须打印保护期签约情况。
- 如果签约数为 0，日志必须能看出原因。

示例：

```text
[rookie-market] protected candidates=1840 signed=37 full=120 low_score=89 finance=2 released=1803
```

### 6.6 EventQueue / SeasonService

建议移除赛季事件中的：

- `DRAFT_PREFERENCES_OPEN`
- `DRAFT_RUN`
- `DRAFT_SIGNING_EXPIRE`

新增可选事件：

- 不新增事件：直接在 `SEASON_END` 内同步处理新人自由市场保护期。
- 或新增 `ROOKIE_MARKET_PROTECTION`：如果希望将休赛期拆成多个可观察阶段。

v1 推荐不新增事件，减少复杂度。

## 7. 前端影响

### 7.1 可删除或隐藏页面

- 选秀大会页
- 选秀志愿排序页
- 选秀待签约入口

### 7.2 需要保留/增强页面

自由市场页：

- 增加来源筛选：合同到期、青训流出、自动生成。
- 增加年龄/潜力/成长速度展示。
- 增加新人标签。

青训营页：

- 保留签约入口。
- 明确赛季末未签约会进入自由市场。

财政页：

- 工资帽改为工资压力/工资参考线展示。
- 文案不要写“禁止签约”，改为“工资压力偏高，会影响财务健康”。

## 8. 压测与验证

### 8.1 关键指标

完整性：

- 所有球队一线队人数在 `8-18` 或 `8-20`
- 无 active 球员无合同且在队
- 无 retired 球员仍在队
- 无 active listing 指向已签约球员

新人市场：

- 每季青训生成数
- 青训签约数
- 新人保护期签约数
- 新人转普通自由市场数
- 弱队签约新人数量

财政：

- 工资压力平均值、P90、最大值
- 财务健康分布
- 余额分布
- 是否出现大量签不起人的 AI

游戏性：

- 强球员 OVR 与评分/积分正相关
- 强队不会因为自由市场保护期无限增强
- 弱队有稳定获得新人机会

状态系统：

- HOT/GOOD/NEUTRAL/LOW 分布合理
- 不应长期全员 LOW
- fitness/load/rust 不应压倒近期表现

### 8.2 压测日志

需要新增或保留日志：

```text
[youth] refresh=2048 ai_signed=12 candidates=2048 full=1800 low_score=200 failed=0
[rookie-market] protected candidates=1800 signed=44 full=80 low_score=160 finance=0 released=1756
[finance] wage_pressure avg=58.4 p90=72.0 max=98.5
[state] avg=-0.8 hot=30 good=420 neutral=2900 low=180
```

## 9. 推荐实施顺序

### Phase 1：降低阻塞

1. 去掉签约/续约的硬工资帽拦截。
2. 一线队上限改为 `18`。
3. AI 目标人数改为 `15-17`，避免长期满员。

### Phase 2：移除选秀

1. 停止排选秀事件。
2. `RosterLifecycleService` 停止创建选秀池。
3. 未签青训进入新人自由市场。
4. 新增自由市场来源 `ACADEMY_RELEASED`。

### Phase 3：新人自由市场保护期

1. 实现保护池 listing。
2. 实现低排名球队 AI 先挑一轮。
3. 剩余新人转普通自由市场。
4. 加入压测日志和统计字段。

### Phase 4：前端清理

1. 隐藏选秀页。
2. 自由市场增加新人筛选。
3. 财政页改工资压力文案。

## 10. 最终闭环

简化后的长期循环：

```text
青训刷新
  -> 青训成长
  -> 玩家/AI 签青训
  -> 老球员退役
  -> 合同到期流入自由市场
  -> 未签青训进入新人自由市场
  -> 低排名 AI 保护期先挑一轮
  -> 剩余新人进入普通自由市场
  -> AI/玩家自由市场补人
  -> 自动补员兜底
  -> 下一赛季
```

这条闭环比完整选秀系统更短、更稳定，也更容易做平衡测试。
