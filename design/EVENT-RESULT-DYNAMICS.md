# 事件结果动态分配方案 v1.0

> 目标：消除所有硬编码概率，所有事件子结果由参与球员属性、区域控制度、比赛状态动态计算。

---

## 1. 核心设计原则

1. **无硬编码阈值**：禁止 `rand < 0.5` 这类固定数值，全部替换为 `sigmoid(Δ_attr)` 或属性加权比较
2. **参与球员决定结果**：每个子结果必须由事件中实际参与对抗的球员属性差决定
3. **控制度作为偏移量**：区域控制度 `C` 以 ±20% 的幅度修正概率
4. **体能衰减传导**：球员当前体能通过 `effective_attr` 已参与计算，子结果无需单独处理

---

## 2. 射门事件结果分配 (CloseShot / LongShot)

### 2.1 参与角色
- ** shooter **: 射门球员
- ** keeper **: 对方门将
- ** nearest_defender **: 射门区域最近的防守球员（非门将）

### 2.2 判定流程

```
Step 1: 是否射正？
  onTarget = ResolveDuel(CalcShotAttack(shooter), CalcSaveDefense(keeper) - keeper_positioning_bonus)

Step 2: 若射正，是否进球？
  if onTarget:
    goal = ResolveDuel(CalcShotAttack(shooter), CalcSaveDefense(keeper) + keeper_reaction_bonus)

Step 3: 若射正但未进球，判定结果类型
  引入 defender_block_chance：由最近防守球员的 DEF/TKL/HEA 决定

  block_roll = rand()
  if block_roll < defender_block_chance:
    result = "blocked"          // 后卫封堵
  else:
    save_quality = keeper_save_roll(CalcSaveDefense(keeper))
    if save_quality < 0.3:
      result = "woodwork"       // 击中门框（门将指尖蹭到但未完全改变方向）
    else:
      result = "saved"          // 门将成功扑救
```

### 2.3 关键公式

**defender_block_chance（后卫封堵概率）**
```
nearest_defender = SelectDefender(defense_team, shot_zone)
block_atk = nearest_defender.EffectiveAttr("DEF") * 0.4
          + nearest_defender.EffectiveAttr("TKL") * 0.3
          + nearest_defender.EffectiveAttr("HEA") * 0.2
          + nearest_defender.EffectiveAttr("POS") * 0.1

block_def = shooter.EffectiveAttr("SHO") * 0.3
          + shooter.EffectiveAttr("ACC") * 0.3
          + shooter.EffectiveAttr("FIN") * 0.2
          + shooter.EffectiveAttr("STR") * 0.2

block_delta = block_atk - block_def + zone_control * 3.0
              // zone_control > 0 表示进攻方控制高，后卫难封堵
              // zone_control < 0 表示防守方控制高，后卫易封堵

defender_block_chance = sigmoid(block_delta / 5.0) * 0.6
// 乘以 0.6 是因为即使有封堵能力，最大概率不超过 60%
// 最低概率不低于 5%
```

**keeper_save_roll（门将扑救质量）**
```
save_roll = rand() * keeper.EffectiveAttr("SAV") / 20.0
// SAV=20 → save_roll 范围 0~1.0
// SAV=10 → save_roll 范围 0~0.5
// save_roll < 0.3 表示"指尖蹭到"→ woodwork
// save_roll >= 0.3 表示"成功扑救"→ saved
```

### 2.4 控制度修正
- 射门区域控制度 `C > 0.5`：后卫封堵概率 `-15%`（空间大好射门）
- 射门区域控制度 `C < -0.3`：后卫封堵概率 `+10%`（空间小易封堵）

---

## 3. 传球事件结果分配

### 3.1 后场/中场传球成功后的去向

当前硬编码：`30%推进 / 30%原地 / 30%回传`（隐含逻辑）

**动态方案**：
```
pass_target = SelectPassTarget(possession_team, from_zone, to_zone)

// 传球者的视野和传球精度决定传球质量
pass_quality = passer.EffectiveAttr("PAS") * 0.5
             + passer.EffectiveAttr("VIS") * 0.3
             + passer.EffectiveAttr("CON") * 0.2

// 接球者的跑位能力决定能否接到好球
receive_quality = target.EffectiveAttr("SPD") * 0.3
                + target.EffectiveAttr("ACC") * 0.3
                + target.EffectiveAttr("POS") * 0.4

// 区域控制度影响
control_bonus = zone_control * 10.0  // 高控制→更容易向前

advance_threshold = 12.0 + control_bonus
// 如果 pass_quality + receive_quality > advance_threshold → 向前推进
// 否则 → 原地接球或回传
```

### 3.2 传中失败后的分支

当前硬编码：`40%角球`

**动态方案**：
```
// 传中者的传中精度和防守者的头球/防守能力决定
cross_quality = crosser.EffectiveAttr("CRO") * 0.5
              + crosser.EffectiveAttr("PAS") * 0.3
              + crosser.EffectiveAttr("DRI") * 0.2

defend_quality = defender.EffectiveAttr("HEA") * 0.4
               + defender.EffectiveAttr("DEF") * 0.3
               + defender.EffectiveAttr("POS") * 0.3

corner_delta = cross_quality - defend_quality + zone_control * 2.5

corner_chance = 0.15 + sigmoid(corner_delta / 5.0) * 0.45
// 基础 15% + 动态 0~45% = 最终 15%~60%
// 传中差/防守好 → 15%
// 传中超神/防守烂 → 60%
```

---

## 4. 突破/过人事件结果分配

### 4.1 边路突破成功后的去向

当前：成功就推进一格，失败就丢球权

**动态方案**：
```
// 突破者的盘带速度和加速度 vs 防守者的回追速度
break_quality = dribbler.EffectiveAttr("DRI") * 0.4
              + dribbler.EffectiveAttr("SPD") * 0.35
              + dribbler.EffectiveAttr("ACC") * 0.25

catch_quality = defender.EffectiveAttr("SPD") * 0.5
              + defender.EffectiveAttr("ACC") * 0.3
              + defender.EffectiveAttr("TKL") * 0.2

gap_delta = break_quality - catch_quality

if gap_delta > 3.0:
  // 完全甩开，可以直接内切或传中
  advance_zone = 2  // 推进两格
else if gap_delta > 0:
  // 小幅领先，推进一格
  advance_zone = 1
else:
  // 被缠住，只能维持或回传
  advance_zone = 0
```

---

## 5. 头球争顶事件结果分配

### 5.1 传中后头球成功后的分支

当前硬编码：`35%触发射门`

**动态方案**：
```
// 争顶成功者的头球能力和射门能力决定
header_winner = attacker (if success) or defender (if fail)

if attacker wins:
  shot_tendency = attacker.EffectiveAttr("HEA") * 0.3
                + attacker.EffectiveAttr("SHO") * 0.4
                + attacker.EffectiveAttr("FIN") * 0.3

  // 控制度修正
  if zone_control > 0.3:
    shot_tendency += 2.0

  shot_chance = sigmoid((shot_tendency - 12.0) / 4.0) * 0.7
  // 头球好+射术好 → 最高 70% 直接射门
  // 头球差+射术差 → 最低 5% 射门（摆渡给队友）

  if rand() < shot_chance:
    chain_to_shot()
  else:
    chain_to_pass()  // 头球摆渡，继续传导
```

---

## 6. 解围事件结果分配

### 6.1 解围后的乌龙球概率

当前硬编码：`0.5% ~ 1.5%`

**动态方案**：
```
// 解围者的镇定值和传球精度决定解围质量
clearance_quality = defender.EffectiveAttr("COM") * 0.5
                  + defender.EffectiveAttr("PAS") * 0.3
                  + defender.EffectiveAttr("DEF") * 0.2

// 防守压力越大（控制度越低），越容易失误
pressure_factor = max(0, -zone_control) * 2.0

// 体能低于 30% 大幅增加失误概率
stamina_penalty = 0
if defender.CurrentStamina < 30:
  stamina_penalty = 3.0

own_goal_delta = clearance_quality - 15.0 - pressure_factor - stamina_penalty

own_goal_chance = 0.001 + sigmoid(-own_goal_delta / 3.0) * 0.03
// 镇定20+无压力 → 0.1%
// 镇定5+高压+疲劳 → 3%
```

---

## 7. 犯规事件结果分配

### 7.1 犯规严重程度判定

当前：硬编码随机数决定黄牌/红牌

**动态方案**：
```
// 犯规动作的危险性由犯规者的铲球/防守风格决定
foul_severity = fouler.EffectiveAttr("TKL") * 0.3
              + fouler.EffectiveAttr("STR") * 0.3
              + (4 - fouler_tactics_tackling_aggression) * 2.0
              // 侵略性战术越高，动作越危险

// 受害者位置（射门/突破中被犯规更严重）
victim_context = 0
if last_event was shot or dribble:
  victim_context = 3.0

// 已有黄牌累积
card_history = fouler.YellowCards * 2.0

severity_score = foul_severity + victim_context - card_history

// 黄牌阈值
yellow_threshold = 8.0
if severity_score > yellow_threshold + rand()*4:
  give_yellow_card()

// 红牌阈值
red_threshold = 14.0
if severity_score > red_threshold + rand()*3:
  give_red_card()
```

---

## 8. 通用修正因子总结

| 因子 | 影响方式 | 范围 |
|------|---------|------|
| 区域控制度 C | 结果概率 ±20% 偏移 | [-0.2, +0.2] |
| 体能 < 30% | 所有主动动作成功率 -15% | -0.15 |
| 体能 < 15% | 所有主动动作成功率 -25% | -0.25 |
| 少打一人 | 防守事件成功率 -20% | -0.20 |
| 主场优势 | 进攻事件成功率 +5% | +0.05 |
| 落后状态 | 进攻冒险倾向 +10% | +0.10 |

---

## 9. 实施优先级

| 优先级 | 事件 | 当前问题 | 改动量 |
|--------|------|---------|--------|
| P0 | 射门子结果 (saved/blocked/woodwork) | 完全硬编码 | 中 |
| P0 | 传中失败分支 (角球/丢球) | 硬编码 40% | 小 |
| P1 | 传球成功去向 (推进/原地) | 硬编码 30% | 中 |
| P1 | 头球成功后分支 (射门/摆渡) | 硬编码 35% | 小 |
| P1 | 犯规严重程度 (黄牌/红牌) | 硬编码随机 | 中 |
| P2 | 解围乌龙球 | 硬编码 0.5~1.5% | 小 |
| P2 | 突破推进幅度 | 固定推进一格 | 小 |
