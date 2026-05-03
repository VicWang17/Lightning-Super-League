# Match Engine — 比赛模拟引擎

> 本 README 是当前引擎的**唯一权威文档**。`design/LSL-Tactics-and-Match-Engine-v1.md` 已废弃，请勿参考。

## 1. 概述

基于事件驱动的足球比赛模拟器，Go 1.22+ 实现。每场比赛由主循环按时间推进，在每个事件节点选择事件类型、执行事件、更新比赛状态。引擎输出完整的事件流（含叙事文本）和统计数据。

**当前目标指标（经调优后）**

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 场均进球 | ~3.2-3.5 | 双方合计 |
| 场均射门 | ~20 | 双方合计 |
| 射正率 | ~40% | 射正 / 射门 |
| 转化率 | ~15% | 进球 / 射门 |
| 场均传球 | ~150 | 双方合计 |
| 大比分(≥4球) | <10% | 现实足球约 5-10% |
| 点球占比 | ~15% | 点球进球 / 总进球 |

---

## 2. 架构概览

```
match-engine/
├── cmd/
│   ├── simulate/main.go      # CLI 入口：运行单场比赛
│   └── stats/main.go         # 统计工具
├── internal/
│   ├── config/
│   │   └── constants.go      # 事件常量、阵型权重、位置区域权重
│   ├── domain/
│   │   ├── player.go         # PlayerRuntime / PlayerSetup / PlayerMatchStats
│   │   ├── team.go           # TeamRuntime / TacticalSetup
│   │   ├── match.go          # MatchState / MatchEvent / Score
│   │   └── request.go        # SimulateRequest
│   ├── engine/
│   │   ├── simulator.go      # 主模拟器：Simulate() + 所有事件处理函数
│   │   ├── resolver.go       # 决斗系统：ResolveDuel + 所有攻击力/防御力计算
│   │   ├── selector.go       # 球员选择：按区域、传球目标、防守者
│   │   ├── control.go        # 控球矩阵计算、控球偏移、风险指数
│   │   ├── stamina.go        # 体力衰减、消耗、半场恢复
│   │   ├── narrative.go      # 事件叙事文本生成
│   │   └── step.go           # 单步模拟（用于外部调用）
│   └── api/
│       └── dto.go            # 对外 API 数据结构
├── docs/                     # 测试报告和调优记录
└── preview/                  # 预览工具
```

**核心设计原则**
- 每场比赛独立创建 `Simulator` 实例，无全局状态
- 随机种子由外部传入，保证可复现
- 所有事件通过 `MatchEvent` 记录，支持完整回放

---

## 3. 核心数据模型

### 3.1 球员属性（23 + DEC = 24 项）

属性值范围 **1-20**，由外部系统传入。引擎内部使用 `EffectiveAttrs`（受体力衰减影响）。

| 缩写 | 全称 | 主要用途 |
|------|------|----------|
| SHO | Shooting | 射门攻击力 |
| PAS | Passing | 传球、组织 |
| DRI | Dribbling | 盘带过人 |
| SPD | Speed | 跑动速度 |
| STR | Strength | 身体对抗 |
| STA | Stamina | 体力（决定衰减系数） |
| DEF | Defense | 防守站位 |
| HEA | Heading | 头球争顶 |
| VIS | Vision | 视野、传球创造力 |
| TKL | Tackling | 抢断能力 |
| ACC | Acceleration | 爆发力 |
| CRO | Crossing | 传中 |
| CON | Control | 控球稳定性 |
| FIN | Finishing | 远射/射门精度 |
| BAL | Balance | 身体平衡 |
| COM | Composure | 冷静度（决斗稳定化） |
| SAV | Saving | 门将扑救 |
| REF | Reflexes | 门将反应 |
| POS | Positioning | 门将/球员站位 |
| FK | Free Kick | 任意球 |
| PK | Penalty Kick | 点球 |
| RUS | Rushing | 门将出击 |
| DEC | Decision Making | 决策（影响事件选择权重） |

### 3.2 位置类型（8 种）

`GK / ST / WF / AMF / CMF / DMF / CB / SB`

### 3.3 比赛场地（3×3 区域矩阵）

```
[0,0] 前场左路  [0,1] 前场中路  [0,2] 前场右路
[1,0] 中场左路  [1,1] 中场中路  [1,2] 中场右路
[2,0] 后场左路  [2,1] 后场中路  [2,2] 后场右路
```

`zone[0] == 0` 为前场，`zone[0] == 1` 为中场，`zone[0] == 2` 为后场。

### 3.4 战术参数

| 参数 | 范围 | 说明 |
|------|------|------|
| FormationID | F01-F08 | 阵型 |
| PassingStyle | 0-4 | 0=长传冲吊, 4=Tiki-taka |
| AttackTempo | 0-4 | 进攻节奏 |
| ShootingMentality | 0-4 | 射门倾向 |
| TacklingAggression | 0-4 | 抢断侵略性 |
| MarkingStrategy | 0-2 | 盯人策略 |
| DefensiveLineHeight | 0-4 | 防线高度 |
| DefensiveCompactness | 0-4 | 防守紧凑度 |
| CrossingStrategy | 0-4 | 传中策略 |
| PlaymakerFocus | 0-4 | 组织核心权重 |

---

## 4. 比赛主循环

```go
for ms.Half <= 2 {
    baseSec := 4.0 + rand*3.5   // 事件间隔 4.0-7.5 秒
    ms.AdvanceClock(baseSec)
    
    //  halftime at 25min, fulltime at 50min
    if ms.Minute >= 25.0 && ms.Half == 1 { handleHalftime() }
    if ms.Minute >= 50.0 && ms.Half == 2 { break }
    
    ApplyStaminaDecay(ms)
    decayControlShift(ms)
    sim.processEvent(ms)
}
```

每场比赛约 400-500 个事件，产出 50 分钟模拟时长。

---

## 5. 事件系统

### 5.1 事件候选池（`processEvent`）

每个事件节点，引擎根据**当前区域**、**控球方**、**控球率**生成候选事件池，按权重随机选择。

** always-available 事件**
- `short_pass` (weight: 25, 前场变为 16)
- `back_pass` (weight: 25)
- `mid_pass` (weight: 32)
- `long_pass` (weight: 8)

**传球风格调整**

| 风格 | short | back | mid | long | through |
|------|-------|------|-----|------|---------|
| 长传冲吊(0) | -5 | -5 | — | +10 | — |
| 直塞(1) | — | — | — | +3 | +5 |
| 短传(2) | +8 | — | — | — | +3 |
| Tiki-taka(4) | +12 | +8 | +5 | — | — |

**区域专属事件**

| 区域 | 事件 | 基础权重 | 触发条件 |
|------|------|----------|----------|
| 后场 | `goal_kick` | 12 | GK 持球 |
| 后场 | `keeper_short_pass` | 10 | GK 持球 |
| 后场 | `keeper_throw` | 5 | GK 持球 |
| 后场 | `build_up` | 8 | ctrl > 0.05 |
| 中场 | `through_ball` | 10 | — |
| 中场 | `long_shot` | 2 (+3) | ctrl > 0.2, mentality≥3 |
| 中场 | `pivot_pass` | 8 | — |
| 前场 | `close_shot` | 8 | — |
| 前场 | `header` | 6 (+4) | crossingStrategy≥3 |
| 前场 | `hold_ball` | 5 | ctrl > 0.1 |
| 前场 | `cross_run` | 4 | — |
| 边线 | `throw_in` | 3 | zone[1]==0/2 |
| 边线 | `overlap` | 5 | zone[1]==0/2 |
| 边线 | `wing_break` | 15 | zone[1]==0/2 |
| 边线 | `cut_inside` | 10 | zone[1]==0/2, zone[0]≤1 |

**防守事件**（仅在控球率低时触发）

| 事件 | 权重 | 触发条件 |
|------|------|----------|
| `tackle` | 8 | ctrl < 0.1 |
| `intercept` | 6 | ctrl < 0.1 |
| `clearance` | 6 (play-from-back→2) | ctrl < 0.1, zone[0]≤1 |
| `block_pass` | 5 | ctrl < 0.3 |

**禁区专属防守**（不依赖低控球）

| 事件 | 权重 |
|------|------|
| `tackle` | 3 |
| `intercept` | 2 |

**其他事件**

| 事件 | 权重 | 条件 |
|------|------|------|
| `counter_attack` | 25 / 8 | 反击 buff 激活 / 对方半场 ctrl<-0.1 |
| `one_on_one` | 6 | 前场, ctrl > 0.5 |
| `double_team` | 4 | ctrl < 0.2, zone[0]≤1 |
| `press_together` | 3 | ctrl < 0.2, zone[0]≤1 |
| `foul` | 1+ | 始终存在（见下文） |
| `drop_ball` | 1 | 概率 0.002 |

### 5.2 控球因子（Control Factor）

所有非传球事件的权重在基础值上再乘以 `(1.0 + ctrl * 0.4)`，最低强制为 1。

`ctrl` 是当前区域的**有效控球率**，范围约 [-1, 1]。

### 5.3 组织核心加成（Playmaker Focus）

```
passBoost  = 1.0 + pf * 0.08
shotReduce = 1.0 - pf * 0.075
throughBoost = 1.0 + pf * 0.05
```

高 PlaymakerFocus 会提升传球权重、降低射门权重、提升直塞权重。

---

## 6. 决斗系统（Duel System）

所有对抗通过 `ResolveDuel(attackValue, defenseValue, rand, com...)` 判定。

### 6.1 核心公式

```
pSuccess = sigmoid((attack - defense) / 6.0)

// COM 稳定化（可选）
stability = min(1.0, COM / 15.0)
pSuccess = 0.5 + (pSuccess - 0.5) * (0.5 + 0.5 * stability)

// 硬边界
pSuccess = clamp(pSuccess, 0.03, 0.97)
```

COM 的作用：**高 COM 把概率推离 0.5（更确定），低 COM 把概率拉向 0.5（更随机）**。

### 6.2 各事件攻击力/防御力公式

| 事件 | 攻击力 | 防御力 |
|------|--------|--------|
| **传球** | PAS×0.55 + VIS×0.35 + CON×0.15 + ctrl×2.5 (+0.3 CMF/DMF) | DEF×0.25 + TKL×0.15 + SPD×0.10 + (1-ctrl)×1.0 |
| **射门(close)** | SHO×0.50 + FIN×0.20 + STR×0.15 + ACC×0.10 | SAV×0.20 + REF×0.15 + POS×0.10 + 5.0 |
| **射门(long)** | FIN×0.45 + SHO×0.30 + STR×0.15 + BAL×0.10 | SAV×0.15 + POS×0.10 + REF×0.10 + 5.0 |
| **头球** | HEA×0.5 + STR×0.3 + SPD×0.2 | HEA×0.5 + STR×0.3 + DEF×0.2 |
| **抢断** | TKL×0.5 + DEF×0.3 + STR×0.2 | DRI×0.25 + CON×0.25 + STR×0.25 + BAL×0.25 |
| **传中** | CRO×0.45 + PAS×0.30 + DRI×0.25 | DEF×0.4 + SPD×0.3 + HEA×0.3 |
| **直塞** | PAS×0.40 + VIS×0.50 + ACC×0.10 | DEF×0.5 + SPD×0.3 + POS×0.2 |
| **长传** | PAS×0.45 + STR×0.20 + VIS×0.35 | HEA×0.4 + SPD×0.4 + POS×0.2 |
| **盘带** | DRI×0.45 + SPD×0.25 + ACC×0.15 + BAL×0.15 | DEF×0.40 + TKL×0.30 + SPD×0.30 |
| **点球** | PK×0.85 + SHO×0.25 + FIN×0.15 + 2.5 | SAV×0.30 + REF×0.20 + POS×0.15 |
| **1v1 门将** | SHO×0.5 + DRI×0.3 + COM×0.2 | REF×0.30 + SAV×0.25 + POS×0.10 + 0.2 |
| **射门封堵** | DEF×0.4 + TKL×0.3 + STR×0.3 | SHO×0.4 + STR×0.4 + ACC×0.2 |
| **二过一** | p1.PAS×0.35 + p2.DRI×0.35 + p2.ACC×0.3 | DEF×0.5 + SPD×0.3 + TKL×0.2 |
| **三角配合** | avg(PAS)×0.5 + DRI×0.2 + min(COM)×0.3 | avg(DEF)×0.7 + min(COM)×0.3 |
| **后场组织** | avg(PAS)×0.5 + CON×0.2 + min(COM)×0.3 | DEF×0.4 + POS×0.3 + SPD×0.3 |

---

## 7. 关键机制详解

### 7.1 射门机制（三步过滤）

```
射门事件 → [Step 1] 后卫封堵 → [Step 2] 射正判定 → [Step 3] 门将扑救 → 结果
```

**Step 1: 后卫封堵**

```
blockAtk = nearestDefender.DEF×0.4 + TKL×0.3 + HEA×0.2 + POS×0.1
blockDef = shooter.SHO×0.3 + ACC×0.3 + FIN×0.2 + STR×0.2
blockDelta = blockAtk - blockDef + ctrl×3.0
blockChance = sigmoid(blockDelta/5.0) × 0.75 + DefensiveCompactness × 0.12

// 封顶
blockChance = clamp(blockChance, 0.05, 0.50)

// 深位防守加成（射门方在防守方禁区内）
if zone[0] >= 2: blockChance += 0.25
```

封堵后：生成 `shot_block` 事件，球权可能转换。

**Step 2: 射正判定**（仅未被封堵时）

```
onTargetProb = 0.60 + sigmoid((SHO + FIN - 20.0)/5.0) × 0.20
onTargetProb = clamp(onTargetProb, 0.45, 0.80)

if rand >= onTargetProb:
    // 射偏：球门球，球权转换给门将
```

**Step 3: 门将扑救**（仅射正时）

```
success = ResolveDuel(atkVal, defVal + 4.0, rand, COM)
// success = true → 进球
// success = false → 被扑出或门框

// 被扑出后：
saveQuality = keeper.SAV×0.6 + keeper.REF×0.4
stability = saveQuality / 20.0
woodworkChance = (1.0 - stability) × 0.4
woodworkChance = max(woodworkChance, 0.05)

if rand < woodworkChance: result = "woodwork"  // 门框
else: result = "saved"  // 被扑出
```

### 7.2 传球机制（无压力 vs 有压力）

**无压力传球判定**

```
// 后场
noPressureProb = 0.55 + ctrl×0.25 + VIS×0.005
// 中场
noPressureProb = 0.40 + ctrl×0.30 + VIS×0.005
// 前场
noPressureProb = 0.15 + ctrl×0.30 + VIS×0.005

noPressureProb = clamp(noPressureProb, 0.05, 0.80)
```

无压力时：传球自动成功，不选防守人。但 `forwardProb` 和 `backwardProb` 都乘以 0.4，推进幅度很小。

**有压力时：决斗判定**

```
// 激进传球
riskIndex = sigmoid((control + mentality×1.5 - 2.0) / 3.0) × 0.6
aggroProb = clamp(riskIndex, 0.05, 0.80)

// 安全传球：1 - aggroProb

// 激进传球攻击力惩罚
atkVal -= 0.20

// 安全传球攻击力加成
atkVal += 0.25

// 防守方加成
defVal += 0.25
if DefensiveCompactness >= 2: defVal += 0.30
```

**传球质量与推进**

```
passQuality = PAS×0.5 + VIS×0.3 + CON×0.2
receiveQuality = SPD×0.3 + ACC×0.3 + POS×0.4

forwardProb  = 0.15 + sigmoid((passQuality - 20.0 + ctrl×5.0)/5.0) × 0.50
backwardProb = 0.10 + sigmoid((20.0 - passQuality - ctrl×5.0)/5.0) × 0.30

forwardProb  = clamp(forwardProb,  0.10, 0.70)
backwardProb = clamp(backwardProb, 0.05, 0.40)
```

### 7.3 犯规机制

**犯规权重**

```
foulWeight = 1
if TacklingAggression >= 2:
    foulWeight += aggression / 2  // 双方战术都影响

// 禁区内（前场中路）
if zone == [0,1]:
    foulWeight *= 0.20
    foulWeight = max(foulWeight, 1)
```

**犯规严重性**

```
foulSeverity = TKL×0.3 + STR×0.3 - DEC×0.15
aggressionBonus = (4 - aggression) × 1.5
victimContext = 3.0 (前场) / 1.5 (中场) / 0.0 (后场)
cardHistory = YellowCards × 2.0

severityScore = foulSeverity + aggressionBonus + victimContext - cardHistory

yellowThreshold = 10.0 + rand×4.0
redThreshold    = 16.0 + rand×3.0
```

**禁区犯规判罚率**

```
callChance = 0.25          // 基础
if 出牌: callChance = 0.50  // 明显犯规更可能被判

if rand > callChance:
    // 未判罚，进攻方保持球权
```

**罚球结果**

禁区内犯规被判 → `doFreeKickEvent` → 直接点球（跳过任意球准备）。

### 7.4 头球机制

1. 选择争顶球员（攻方持球者 vs 守方防守者）
2. `ResolveDuel(CalcHeaderAttack, CalcHeaderDefense)`
3. 攻方胜出后，检查是否直接射门：

```
shotTendency = HEA×0.3 + SHO×0.4 + FIN×0.3
if ctrl > 0.3: shotTendency += 1.0

shotChance = 0.05 + sigmoid((shotTendency - 12.0)/4.0) × 0.25
shotChance = clamp(shotChance, 0.05, 0.45)
```

### 7.5 点球机制

```
atkVal = PK×0.85 + SHO×0.25 + FIN×0.15 + 2.5
defVal = SAV×0.30 + REF×0.20 + POS×0.15

success = ResolveDuel(atkVal, defVal, rand, COM)

if !success && rand < 0.15:
    result = "fail"  // 踢飞
else if !success:
    result = "saved"
```

---

## 8. 控球与动量系统

### 8.1 控球矩阵

每场比赛维护一个 3×3 控球矩阵 `ControlMatrix`，表示每个区域的**绝对控球优势**（正 = 主队，负 = 客队）。

```
raw = 0.28×formationDelta + 0.40×playerDelta + 0.18×tacticDelta + 0.03×dynamicDelta + 0.01×momentum
ControlMatrix[r][c] = tanh(raw × 2.0)
```

### 8.2 控球偏移（Control Shift）

每次事件后会修改 `ControlShift`（3×3 矩阵），叠加在基础控球矩阵上：

- 进攻成功 → 正向偏移
- 防守成功 → 负向偏移
- 进球 → +0.15（前场）
- 门框 → +0.03
- 被扑 → +0.05
- 犯规 → +0.03/+0.06

偏移衰减：
- 活跃区域：`×0.92`
- 非活跃区域：`×0.60`
- 边界：`clamp(-0.5, 0.5)`
- 死球时：`resetControlShift` 归零

### 8.3 有效控球率

```
EffectiveControl = ControlMatrix[zone] + ControlShift[zone]
```

范围约 [-1.5, 1.5]，用于事件权重加成和决斗计算。

### 8.4 全局动量

`GlobalMomentum` 记录比赛的整体倾向，进球/关键事件时小幅调整（±0.01~0.04），自然衰减。

### 8.5 反击加成

成功的防守事件（抢断、拦截）可能激活 `CounterBoost`，在接下来若干事件中大幅提升反击事件权重。

---

## 9. 体力系统

### 9.1 体力衰减

根据当前体力水平，所有有效属性乘以衰减系数：

| 体力范围 | 衰减系数 |
|----------|----------|
| ≥70 | 1.00 |
| 50-69 | 0.95 |
| 30-49 | 0.90 |
| 15-29 | 0.82 |
| <15 | 0.75 |

受伤额外衰减：轻伤 ×0.85，重伤 ×0.60。

### 9.2 体力消耗

```
staFactor = 1.0 - (STA - 10.0) / 30.0  // 10→1.0, 20→0.67
staFactor = max(staFactor, 0.5)
cost = intensity × staFactor
```

**各事件体力消耗**

| 事件 | 消耗 |
|------|------|
| 短传/回传/中传 | 0.6 |
| 长传/直塞 | 1.0 |
| 任意球 | 1.5 |
| 传中 | 1.8 |
| 射门/头球/1v1/封堵 | 2.5 |
| 抢断/拦截/解围 | 2.0 |
| 反击 | 2.8 |
| 犯规 | 1.5 |

### 9.3 半场恢复

中场休息时所有球员体力 +30。

---

## 10. 球员选择逻辑

### 10.1 按区域选择（`SelectPlayerByZone`）

```
weight = zoneWeight(position, zone) × staminaFactor × realismFactor
```

GK 在前场区域的权重被惩罚为 ×0.0005。

### 10.2 传球目标选择（`SelectPassTarget`）

```
weight = zoneWeight(position, targetZone) × staminaFactor
```

GK 在中前场区域作为传球目标的权重被强制设为 0。

### 10.3 防守者选择（`SelectDefender`）

```
weight = zoneWeight(position, zone) × staminaFactor
```

GK 被**明确排除**在防守者选择之外。

---

## 11. 叙事系统

`narrative.go` 为每种事件类型提供中文叙事文本模板，通过 `NarrativeGenerator` 随机选择。叙事不影响力学，仅用于前端展示。

主要叙事类型：所有 gameplay 事件 + setup 事件（罚球准备、任意球准备等）。

---

## 12. 参数速查表

### 12.1 时间参数

| 参数 | 值 |
|------|-----|
| 半场时长 | 25 分钟 |
| 全场时长 | 50 分钟 |
| 事件间隔 | 4.0 + rand×3.5 秒 |
| 中场休息 | 体力 +30 |

### 12.2 射门参数

| 参数 | 值 |
|------|-----|
| close_shot 权重 | 8 |
| long_shot 权重 | 2 |
| blockChance sigmoid 乘数 | 0.75 |
| blockChance 封顶 | 0.50 |
| blockChance 深位防守加成 | +0.25 |
| onTargetProb 基础 | 0.60 |
| onTargetProb 封顶 | 0.80 |
| keeper 防御加成 | +4.0 |
| woodworkChance 基础 | (1-stability)×0.4 |
| woodworkChance 最低 | 0.05 |

### 12.3 犯规参数

| 参数 | 值 |
|------|-----|
| 犯规基础权重 | 1 |
| 禁区犯规折扣 | ×0.20 |
| 禁区犯规判罚率 | 0.25 (黄牌/红牌: 0.50) |
| 黄牌阈值 | 10 + rand×4 |
| 红牌阈值 | 16 + rand×3 |
| 重伤概率（红牌犯规） | 0.50 |
| 轻伤概率（黄牌级） | 0.06 |

### 12.4 头球参数

| 参数 | 值 |
|------|-----|
| header 权重 | 6 |
| 传中质量加成 | crossQuality × 0.15 |
| 高传中策略加成 | +0.4 atkVal |
| shotChance 基础 | 0.05 |
| shotChance 封顶 | 0.45 |

### 12.5 点球参数

| 参数 | 值 |
|------|-----|
| PK 权重 | 0.85 |
| SHO 权重 | 0.25 |
| FIN 权重 | 0.15 |
| 基础加成 | +2.5 |
| 踢飞概率（被扑后） | 0.15 |

### 12.6 控球参数

| 参数 | 值 |
|------|-----|
| formationDelta 权重 | 0.28 |
| playerDelta 权重 | 0.40 |
| tacticDelta 权重 | 0.18 |
| dynamicDelta 权重 | 0.03 |
| momentum 权重 | 0.01 |
| tanh 缩放 | ×2.0 |
| control factor 事件加成 | (1 + ctrl×0.4) |

---

## 13. 测试与调优

测试文件位于 `internal/engine/`：

| 测试文件 | 用途 |
|----------|------|
| `variance_analysis_test.go` | 50 场方差分析：比分、射门、射正、传球分布 |
| `variance_analysis2_test.go` | 200 场深度分析：转化率、扑救率、点球占比、大比分 |
| `benchmark_test.go` | 性能基准测试 |
| `control_test.go` | 控球矩阵验证 |
| `quick_test.go` / `quick2_test.go` | 快速功能验证 |
| `narrative_demo_test.go` | 叙事文本演示 |

运行方差分析：
```bash
go test ./internal/engine -run TestVarianceAnalysis -v
go test ./internal/engine -run TestVarianceDeepAnalysis -v
```

---

## 14. 注意事项（给 AI 维护者）

1. **所有数值参数都是调优后的结果**，修改前请先运行方差分析测试验证影响。
2. **射门机制是三层过滤**（block → onTarget → keeper），调整任何一层都会影响其他指标。
3. **禁区犯规权重有 bug 历史**：`control factor` 后的强制最小值 2 曾完全抵消了 ×0.25 折扣。当前修复为：禁区折扣 ×0.20 + 最小值 1 + control factor 最小值 1。
4. **GK 参与进攻**：已通过 `SelectPassTarget` 和 `SelectDefender` 的权重惩罚解决，GK 不会在前场被选中。
5. **COM 稳定化**：仅影响决斗概率的确定性，不改变期望值。高 COM 球员在关键时刻更可靠。
6. **事件权重体系**：传球事件不受 control factor 影响（始终可用），其他事件都受 `ctrl` 加成。修改 control factor 最小值会影响所有非传球事件。
