# 应急资金与伤病医疗联动设计文档

> 版本：v1.0  
> 范围：财政预算中的应急资金重设计、伤病缩短恢复时间的医疗支出、数据结构、数值平衡、前后端接口与压测指标。  
> 依赖：`design/ECONOMY-SYSTEM-DESIGN.md`、`design/INJURY-SYSTEM-DESIGN.md`。  
> 核心目标：让“应急资金”从静态预算项变成有明确用途、风险收益和赛季经营取舍的系统。

---

## 1. 设计目标

### 1.1 玩家体验目标

应急资金不再只是“放着不用的钱”，而是球队的赛季风险保险池。玩家在预算规划时要面对真实取舍：

- 少留应急资金：转会、青训、工资预算更宽裕，但伤病和财政意外会直接冲击赛季计划。
- 标准应急资金：能覆盖小型伤病医疗、短期工资波动和低频突发事件。
- 高应急资金：财政更稳定，医疗操作更从容，但会压缩竞技投入。

### 1.2 系统目标

| 目标 | 说明 |
| --- | --- |
| 提高预算决策价值 | `reserve_pct` 需要影响赛季风险承受能力，而不是只参与展示。 |
| 接入伤病系统 | 中伤/重伤可以支付医疗费用缩短恢复时间，但不能无脑买断风险。 |
| 控制滚雪球 | 强队可以花钱治疗核心，但价格随球员价值和剩余天数上升，避免无限堆钱。 |
| 保持闭环可解释 | 所有医疗支出写入 `finance_transactions`，应急资金使用有记录。 |
| 适配现有赛季节奏 | 当前伤病上限约 15 天，医疗系统只做“缩短若干天”，不引入长期医院经营。 |

### 1.3 非目标

- 不做复杂医院建筑、队医雇佣、保险公司谈判。
- 不做贷款、债务、医疗分期。
- 不允许立刻治愈所有伤病。
- 不把医疗加速做成必点按钮；高风险治疗必须有副作用。

---

## 2. 核心玩法概述

### 2.1 应急资金改名建议

前端展示建议从“应急储备”改为 **“风险准备金”**。

后端字段可以继续沿用 `reserve_budget` / `reserve_pct`，避免一次性迁移成本。UI 文案层改名即可。

### 2.2 风险准备金的三类用途

| 用途 | 触发方式 | 作用 |
| --- | --- | --- |
| 自动缓冲 | 系统自动 | 覆盖小型伤病基础医疗费、工资短缺缓冲、低额突发事件。 |
| 主动医疗 | 玩家主动 | 对中伤/重伤球员支付费用，缩短恢复天数。 |
| 赛季结算 | 系统自动 | 未使用准备金部分结转，并影响财政健康度。 |

### 2.3 玩家可见规则

预算规划页展示：

- 风险准备金比例。
- 可用准备金金额。
- 风险等级。
- 本赛季已使用准备金。
- 医疗加速预计可覆盖次数。

球员伤病页展示：

- 原始预计恢复天数。
- 当前剩余天数。
- 可选医疗方案。
- 花费金额。
- 缩短天数。
- 复发风险或残余劳损惩罚。

---

## 3. 风险准备金预算规则

### 3.1 推荐比例

| `reserve_pct` | 风险等级 | 玩法定位 |
| --- | --- | --- |
| `0-4` | 激进 | 几乎无缓冲，适合搏命冲成绩。 |
| `5-9` | 标准 | 可覆盖小额突发支出，默认推荐区间。 |
| `10-14` | 稳健 | 适合阵容老化、赛程密集或财政一般的球队。 |
| `15-20` | 保守 | 抗风险强，但转会和青训预算明显受限。 |

后端配置继续沿用当前 `reserve_min_pct = 5`、`reserve_max_pct = 20`。允许自定义低于 5%，但 UI 给出风险警告。

### 3.2 准备金状态字段

建议在 `team_season_finances` 增加缓存字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `reserve_budget` | DECIMAL | 当前已有，赛季锁定时的风险准备金总额。 |
| `reserve_spent` | DECIMAL | 本赛季已使用准备金。 |
| `reserve_available` | DECIMAL | 可用准备金，建议可计算也可缓存。 |
| `reserve_auto_used` | DECIMAL | 自动缓冲已使用金额。 |
| `reserve_medical_used` | DECIMAL | 医疗加速已使用金额。 |
| `reserve_events_used` | INT | 本赛季使用准备金的次数。 |

计算：

```text
reserve_available = max(0, reserve_budget - reserve_spent)
reserve_usage_pct = reserve_spent / reserve_budget
```

如果暂不加字段，也可以从 `finance_transactions.source_type = medical / reserve_event` 汇总，但赛季页面频繁展示时建议缓存。

---

## 4. 伤病医疗加速设计

### 4.1 可治疗范围

| 伤病严重度 | 是否可医疗加速 | 说明 |
| --- | --- | --- |
| 轻伤 `severity=1` | 不建议 | 只有 1-2 天，治疗收益小，避免 UI 噪音。 |
| 中伤 `severity=2` | 可以 | 主力短期缺阵时有明确决策价值。 |
| 重伤 `severity=3` | 可以 | 价格更高，且有更强副作用。 |

### 4.2 医疗方案

每名球员每次活跃伤病最多选择一次医疗方案，避免玩家多次点击叠加。

| 方案 | 缩短天数 | 价格倍率 | 副作用 | 推荐用途 |
| --- | ---: | ---: | --- | --- |
| 标准康复 | `0` | `0` | 无 | 默认自然恢复。 |
| 加强理疗 | `ceil(remaining_days * 0.25)`，最多 2 天 | `1.00` | 无明显副作用 | 中伤、普通轮换球员。 |
| 专家会诊 | `ceil(remaining_days * 0.40)`，最多 4 天 | `1.80` | 伤愈残余劳损 `+5` | 主力或关键赛程。 |
| 激进复出 | `ceil(remaining_days * 0.55)`，最多 6 天 | `3.00` | 复发风险上升，残余劳损 `+12` | 决赛、保级、争冠关键战。 |

硬性限制：

```text
new_remaining_days >= max(1, floor(original_total_days * 0.35))
```

即医疗无法把伤病完全抹掉，也不能把一个 12 天伤病压到 1 天以内。这样能保留伤病系统的经营压力。

### 4.3 缩短天数公式

```text
raw_reduction = ceil(remaining_days * plan_reduction_pct)
day_reduction = min(raw_reduction, plan_max_days)
minimum_remaining = max(1, floor(original_total_days * 0.35))
actual_reduction = min(day_reduction, remaining_days - minimum_remaining)
```

如果 `actual_reduction <= 0`，该方案不可选。

### 4.4 医疗费用公式

医疗费必须同时受球员价值、工资、伤病严重度和缩短天数影响。

```text
player_value_base = max(player_market_value * 0.012, weekly_wage * 2, league_floor)
severity_multiplier = { severity2: 1.0, severity3: 1.6 }
body_part_multiplier = 见 4.5
scarcity_multiplier = 1.0 + team_position_shortage * 0.15
days_multiplier = actual_reduction ^ 1.25
plan_multiplier = { enhanced: 1.0, specialist: 1.8, aggressive: 3.0 }

medical_cost =
  player_value_base
  * severity_multiplier
  * body_part_multiplier
  * scarcity_multiplier
  * days_multiplier
  * plan_multiplier
```

金额取整：

```text
medical_cost = round_to_1000(medical_cost)
```

### 4.5 部位价格倍率

| 部位 | 倍率 | 原因 |
| --- | ---: | --- |
| 腿筋、腹股沟、小腿、股四头肌 | `1.00` | 常规肌肉伤。 |
| 脚踝、膝盖、跟腱 | `1.25` | 复发和竞技影响更高。 |
| 腰背、肋骨、肩部 | `1.10` | 对抗和门将影响明显。 |
| 手指 | `0.90` | 非门将较低，门将按 `1.20`。 |
| 头/面部 | `1.30` | 脑震荡/鼻骨类需更保守。 |

门将修正：

```text
if player.position == GK and body_part in ["fingers", "shoulder", "head"]:
    body_part_multiplier += 0.30
```

### 4.6 联赛底价

为避免低级别低工资球员医疗费过低，设置联赛底价：

| 联赛层级 | `league_floor` |
| --- | ---: |
| 顶级联赛 | `50000` |
| 二级联赛 | `35000` |
| 三级联赛 | `25000` |
| 四级及以下 | `15000` |

如果当前数据库没有稳定的球员估值字段，可以先用：

```text
player_market_value = player_ovr_value_estimate
weekly_wage = active_contract.salary / season_weeks
```

---

## 5. 准备金支付与余额支付

### 5.1 支付顺序

医疗支出优先从风险准备金扣除：

```text
reserve_pay = min(reserve_available, medical_cost)
cash_pay = medical_cost - reserve_pay
```

然后：

- `reserve_spent += reserve_pay`
- 球队余额扣除 `medical_cost`
- 财政流水记录完整医疗费用
- 流水 metadata 标记其中多少来自准备金

说明：准备金不是独立银行账户，而是锁定预算中的风险额度。真实现金仍从球队余额扣除，但财政健康计算会区别对待“准备金内支出”和“准备金外支出”。

### 5.2 财政健康影响

| 情况 | 财政健康影响 |
| --- | --- |
| 医疗费完全由准备金覆盖 | 不降健康度。 |
| 50% 以上由准备金覆盖 | 健康度压力轻微增加。 |
| 主要由余额硬付 | 计入预算外支出，可能提高 `overspend_level`。 |
| 准备金已用尽仍激进复出 | 额外财政风险警告。 |

预算压力建议：

```text
off_budget_medical = max(0, medical_cost - reserve_pay)
medical_pressure = off_budget_medical / locked_budget_total
```

当 `medical_pressure >= 0.03`，赛季财政健康评估扣分。

---

## 6. 自动缓冲规则

自动缓冲用于低成本、低操作价值的事件，不弹窗打扰玩家。

### 6.1 可自动覆盖事件

| 事件 | 自动覆盖上限 |
| --- | ---: |
| 轻伤基础处理 | `min(20000, reserve_available)` |
| 中伤诊断费 | `min(40000, reserve_available)` |
| 工资支付短缺 | 最多本周工资缺口的 `50%` |
| 青训意外补偿 | 最多事件损失的 `50%` |
| 小型设施事故 | 最多 `reserve_budget * 10%` |

自动缓冲只减少财政健康冲击，不改变球员恢复天数。恢复天数只能通过主动医疗方案改变。

### 6.2 自动缓冲频率限制

```text
reserve_auto_used <= reserve_budget * 0.50
reserve_events_used <= 5
```

超过后仍可发生事件，但不再自动保护。

---

## 7. 医疗副作用与复发风险

### 7.1 残余劳损

医疗加速不是免费时间机器。缩短恢复会增加伤愈后的残余劳损：

| 方案 | 伤愈残余劳损修正 |
| --- | --- |
| 加强理疗 | `+0` |
| 专家会诊 | `+5` |
| 激进复出 | `+12` |

现有伤病文档的残余劳损公式更新为：

```text
post_recovery_wear =
  max(current_wear_after_recovery, random(residual_min, residual_max) + treatment_residual_penalty)
```

### 7.2 复发风险

球员伤愈后 7 天内，如果使用过专家会诊或激进复出，触发复发修正：

```text
recurrence_multiplier =
  1.00
  + treatment_risk_bonus
  + same_part_recent_injury_bonus
```

| 方案 | `treatment_risk_bonus` |
| --- | ---: |
| 加强理疗 | `0.00` |
| 专家会诊 | `0.15` |
| 激进复出 | `0.35` |

这不会直接制造伤病，只在下一次伤病检定时提高概率。

---

## 8. 数据结构设计

### 8.1 新增伤病医疗记录表

建议新增 `injury_treatments`。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | UUID/string | 主键。 |
| `team_id` | FK | 球队。 |
| `player_id` | FK | 球员。 |
| `season_id` | FK | 赛季。 |
| `injury_record_id` | FK/string | 对应活跃伤病。 |
| `plan` | enum | `enhanced`, `specialist`, `aggressive`。 |
| `cost` | DECIMAL | 实际医疗费用。 |
| `reserve_paid` | DECIMAL | 被准备金覆盖的金额。 |
| `cash_paid` | DECIMAL | 准备金外支出。 |
| `days_before` | INT | 治疗前剩余天数。 |
| `days_reduced` | INT | 实际缩短天数。 |
| `days_after` | INT | 治疗后剩余天数。 |
| `residual_wear_penalty` | INT | 伤愈残余劳损惩罚。 |
| `recurrence_risk_bonus` | DECIMAL | 复发风险修正。 |
| `created_at` | DATETIME | 创建时间。 |

唯一约束：

```text
unique(injury_record_id)
```

保证同一次伤病只能治疗一次。

### 8.2 财政流水扩展

`finance_transactions.source_type` 增加：

| source_type | direction | 说明 |
| --- | --- | --- |
| `medical` | expense | 主动医疗加速。 |
| `reserve_auto_cover` | expense | 自动缓冲事件。 |
| `reserve_settlement` | income/expense | 赛季末准备金结转或惩罚。 |

医疗流水 metadata：

```json
{
  "player_id": "player-id",
  "injury_record_id": "injury-id",
  "treatment_id": "treatment-id",
  "plan": "specialist",
  "days_before": 8,
  "days_reduced": 3,
  "days_after": 5,
  "reserve_paid": "120000.00",
  "cash_paid": "30000.00"
}
```

### 8.3 伤病记录扩展

在 `InjuryRecord` 增加：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `original_total_days` | INT | 原始伤停总天数，医疗底线计算需要。 |
| `remaining_days` | INT | 当前剩余天数。 |
| `treatment_applied` | BOOL | 是否已治疗。 |
| `treatment_risk_bonus` | DECIMAL | 复发风险修正。 |
| `residual_wear_penalty` | INT | 伤愈残余劳损惩罚。 |

---

## 9. 后端服务设计

### 9.1 服务职责

新增 `InjuryTreatmentService`。

| 方法 | 说明 |
| --- | --- |
| `list_treatment_options(team_id, player_id, injury_id)` | 返回可选方案、缩短天数、费用和副作用。 |
| `apply_treatment(team_id, player_id, injury_id, plan)` | 执行治疗，扣款，更新伤病天数，写入流水。 |
| `auto_cover_event(team_id, season_id, event_type, amount)` | 自动准备金缓冲。 |
| `settle_reserve_carryover(team_id, season_id)` | 赛季末结算未用准备金。 |

### 9.2 接口建议

```text
GET /api/v1/teams/{team_id}/injuries/{injury_id}/treatment-options
POST /api/v1/teams/{team_id}/injuries/{injury_id}/treat
GET /api/v1/teams/{team_id}/finance/reserve
```

`POST treat` 请求：

```json
{
  "plan": "specialist"
}
```

响应：

```json
{
  "treatment_id": "id",
  "player_id": "id",
  "plan": "specialist",
  "cost": "150000.00",
  "reserve_paid": "120000.00",
  "cash_paid": "30000.00",
  "days_before": 8,
  "days_reduced": 3,
  "days_after": 5,
  "reserve_available_after": "850000.00"
}
```

### 9.3 幂等与并发

执行治疗时必须：

1. 在事务内锁定 `injury_record` 和 `team_season_finance`。
2. 检查 `injury_record.is_active = true`。
3. 检查 `treatment_applied = false`。
4. 重新计算费用和缩短天数，不能信任前端传入金额。
5. 写入 `injury_treatments`。
6. 写入 `finance_transactions`。
7. 更新 `remaining_days`、`reserve_spent`、球队余额。

---

## 10. AI 决策规则

AI 不需要复杂策略，先用可解释规则：

### 10.1 AI 是否治疗

```text
score =
  player_importance_score
  + schedule_importance_score
  + promotion_or_relegation_pressure
  - financial_risk_score
  - recurrence_risk_score
```

触发条件：

| 条件 | 建议 |
| --- | --- |
| 核心球员，剩余天数 5+，未来 7 天有关键比赛 | 可选专家会诊。 |
| 门将受伤且无可用替补 | 可选专家会诊或加强理疗。 |
| 财政健康 C/D | 只允许加强理疗，除非阵容不足 8 人。 |
| 激进复出 | AI 默认不用，只在决赛/保级生死战使用。 |

### 10.2 AI 预算策略联动

| 球队状态 | reserve_pct 倾向 |
| --- | --- |
| 老龄化阵容 | `10-14` |
| 阵容深度不足 | `10-14` |
| 财政健康 D | `5-8`，避免锁太多预算但保留基础缓冲 |
| 冲冠强队 | `5-10` |
| 青训重建队 | `8-12` |

---

## 11. 前端设计

### 11.1 财政预算页

把“应急储备”改为“风险准备金”，增加说明数据：

- 风险等级：激进 / 标准 / 稳健 / 保守。
- 预计可覆盖：例如“约 2 次中等医疗支出”。
- 已使用金额。
- 剩余可用金额。

### 11.2 球员详情页

伤病状态区域增加医疗按钮：

| 状态 | 展示 |
| --- | --- |
| 无伤病 | 不展示医疗模块。 |
| 轻伤 | 展示自然恢复提示，不展示治疗按钮。 |
| 中伤/重伤 | 展示三种医疗方案卡片。 |
| 已治疗 | 展示已治疗方案、缩短天数、复发风险提示。 |

按钮文案示例：

```text
专家会诊
花费 15 万，预计缩短 3 天
伤愈后该部位复发风险小幅上升
```

### 11.3 邮件与提醒

新增邮件类型：

| message_type | 触发 |
| --- | --- |
| `injury_treatment_available` | 核心球员中伤/重伤后。 |
| `reserve_low_warning` | 准备金可用额低于 25%。 |
| `treatment_completed` | 玩家执行医疗后。 |
| `injury_recurrence_warning` | 激进复出球员 7 天内再次高负荷。 |

---

## 12. 赛季末结算

### 12.1 未使用准备金结转

未使用准备金不应完全浪费：

```text
unused_reserve = reserve_budget - reserve_spent
carryover_amount = unused_reserve * carryover_rate
```

建议：

| 财政健康 | `carryover_rate` |
| --- | ---: |
| A | `0.70` |
| B | `0.60` |
| C | `0.50` |
| D | `0.40` |

结转以 `reserve_settlement` 写入财政流水。

### 12.2 财政健康修正

| 条件 | 修正 |
| --- | --- |
| `reserve_usage_pct <= 0.25` 且无预算外医疗 | 健康评分小幅加分。 |
| `reserve_usage_pct >= 0.90` | 健康评分小幅扣分。 |
| 预算外医疗支出超过锁定预算 `3%` | 扣分。 |
| 激进复出 2 次及以上 | 扣分，表示管理层风险控制差。 |

---

## 13. 数值样例

### 13.1 中场主力腿筋中度拉伤

输入：

```text
球员估值：8,000,000
周薪：80,000
联赛底价：50,000
伤病：腿筋中度拉伤，剩余 8 天，总天数 10 天
方案：专家会诊
```

计算：

```text
player_value_base = max(8,000,000 * 0.012, 80,000 * 2, 50,000) = 160,000
actual_reduction = min(ceil(8 * 0.40), 4, 8 - floor(10 * 0.35)) = 4
medical_cost = 160,000 * 1.0 * 1.0 * 1.0 * 4^1.25 * 1.8
             ≈ 1,630,000
```

这个价格偏高，说明高估值主力缩短 4 天应该是重大经营决策。若希望更温和，可以把 `player_market_value * 0.012` 下调到 `0.006-0.008`。

### 13.2 推荐 v1 参数

为了符合当前游戏资金规模，v1 建议采用较温和版本：

```text
player_value_base = max(player_market_value * 0.006, weekly_wage * 1.5, league_floor)
days_multiplier = actual_reduction ^ 1.15
```

同样样例：

```text
player_value_base = max(8,000,000 * 0.006, 80,000 * 1.5, 50,000) = 120,000
medical_cost = 120,000 * 4^1.15 * 1.8 ≈ 1,060,000
```

结论：对核心球员缩短 4 天约 100 万，是有痛感但可接受的决策。

---

## 14. 平衡指标与压测

### 14.1 关键指标

压测报告增加：

| 指标 | 目标区间 |
| --- | --- |
| 单队单赛季主动医疗次数 | 平均 `0.2-1.0` 次 |
| 单队单赛季激进复出次数 | 平均 `<0.15` 次 |
| 医疗支出 / 锁定预算 | 平均 `<3%` |
| 准备金使用率 | 中位数 `20%-60%` |
| 准备金耗尽球队比例 | `<15%` |
| 治疗后 7 天同部位复发率 | `<8%` |
| 因准备金不足进入财政危机比例 | `<5%` |

### 14.2 需要观察的异常

- AI 频繁治疗低价值替补。
- 强队总能用钱抹平所有伤病，伤病失去意义。
- 弱队因一次伤病医疗直接财政崩盘。
- 激进复出成为最优解。
- 玩家没有理由选择 10% 以上风险准备金。

### 14.3 调参旋钮

| 问题 | 调整 |
| --- | --- |
| 医疗太便宜 | 提高 `player_value_base` 系数或 `plan_multiplier`。 |
| 医疗太贵没人用 | 降低联赛底价或 `days_multiplier` 指数。 |
| 激进复出太强 | 提高复发风险和残余劳损。 |
| 准备金仍然无感 | 提高自动缓冲覆盖范围，增加赛季末健康度加成。 |
| 弱队太容易崩 | 提高准备金覆盖比例，降低低级别联赛底价。 |

---

## 15. 分阶段实施

### Phase 1：准备金可用化

- `team_season_finances` 增加 `reserve_spent` 等缓存字段。
- 财政页展示风险等级、已用/可用准备金。
- 赛季末未用准备金结转。

### Phase 2：医疗加速 MVP

- 新增 `injury_treatments`。
- 实现治疗选项计算和执行接口。
- 中伤/重伤支持一次性缩短恢复时间。
- 写入财政流水。

### Phase 3：副作用与 AI

- 接入残余劳损惩罚和复发风险。
- AI 根据球员重要性和财政健康自动选择治疗。
- 邮件提醒。

### Phase 4：压测与调参

- 闭环压测增加医疗和准备金指标。
- 根据准备金使用率、医疗次数、复发率调整参数。

---

## 16. 推荐默认配置

```python
RESERVE_MIN_PCT = 5
RESERVE_MAX_PCT = 20

RESERVE_CARRYOVER_RATE = {
    "A": 0.70,
    "B": 0.60,
    "C": 0.50,
    "D": 0.40,
}

TREATMENT_PLANS = {
    "enhanced": {
        "reduction_pct": 0.25,
        "max_days": 2,
        "cost_multiplier": 1.0,
        "residual_wear_penalty": 0,
        "recurrence_risk_bonus": 0.00,
    },
    "specialist": {
        "reduction_pct": 0.40,
        "max_days": 4,
        "cost_multiplier": 1.8,
        "residual_wear_penalty": 5,
        "recurrence_risk_bonus": 0.15,
    },
    "aggressive": {
        "reduction_pct": 0.55,
        "max_days": 6,
        "cost_multiplier": 3.0,
        "residual_wear_penalty": 12,
        "recurrence_risk_bonus": 0.35,
    },
}

MEDICAL_COST = {
    "market_value_pct": 0.006,
    "weekly_wage_multiplier": 1.5,
    "days_exponent": 1.15,
    "minimum_remaining_pct": 0.35,
}
```

---

## 17. 最小可行结论

v1 最值得先做的是：

1. 风险准备金显示“可用/已用/风险等级”。
2. 中伤/重伤出现医疗方案。
3. 治疗只能选一次，不能完全治愈。
4. 费用优先被准备金覆盖，超出部分计入预算外医疗。
5. 未用准备金赛季末部分结转并影响财政健康。

这样“应急资金”会同时服务于财政、伤病、赛季决策三条线，玩家能明确感受到它的价值，也不会让金钱完全抹掉伤病系统的管理深度。
