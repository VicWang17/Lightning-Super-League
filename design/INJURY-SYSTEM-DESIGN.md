# 伤病系统设计文档

> 版本：v1.0  
> 范围：比赛引擎伤病触发、训练劳损联动、恢复机制与测试压测方案。  
> 约束：不新增训练系统，基于现有训练内容附加劳损标签；恢复时间从区间随机取数，无医疗系统介入；**一支球队一个赛季严重伤病不超过 1-2 次**。

---

## 1. 核心设计理念

| 维度 | 设计决策 |
|------|---------|
| **伤病本质** | 不是随机抽奖，而是**身体部位劳损值长期累积到临界点后爆发**。 |
| **可见性** | 劳损值对玩家隐藏，用颜色区间（绿/黄/橙/红）提示部位隐患。 |
| **触发逻辑** | 高危动作（凶狠铲球、危险犯规、疲劳临界点）+ 高劳损部位 = 伤病检定。 |
| **恢复机制** | 从固定区间 `[min, max]` 内**均匀随机取整数天数**，无外部医疗加速。 |
| **疲劳联动** | 与现有 `fatigue` 系统打通：`fatigue` 高 → 比赛 stamina 低 → 动作变形 → 劳损累积加速。 |
| **重伤控制** | 通过极低的**基础动作概率** + **劳损阈值门槛**，确保单队单赛季重伤 1-2 次。 |

---

## 2. 球员身体部位劳损系统

每名球员新增 **13 个部位的劳损值**，范围 `0~100`。劳损值会**自然恢复**，但训练/比赛会不断叠加。

### 2.1 数据结构

```go
type PlayerBodyWear struct {
    Hamstring    float64  // 腿筋（大腿后侧肌群）
    Quadriceps   float64  // 股四头肌
    Calf         float64  // 小腿（腓肠肌/比目鱼肌）
    Groin        float64  // 腹股沟
    Ankle        float64  // 脚踝
    Knee         float64  // 膝盖
    Achilles     float64  // 跟腱
    Foot         float64  // 足/脚趾
    Back         float64  // 腰背
    Ribs         float64  // 肋骨
    Shoulder     float64  // 肩部
    Fingers      float64  // 手指（门将关键）
    Head         float64  // 头/面部
}
```

### 2.2 劳损值对玩家的可见表达

不暴露精确数字，只给区间提示：

| 劳损区间 | 颜色 | UI 提示 |
|---------|------|--------|
| `0~25` | 🟢 绿色 | 无任何提示 |
| `26~50` | 🟡 黄色 | "XX 部位略有疲劳" |
| `51~70` | 🟠 橙色 | "XX 部位需要关注，建议控制负荷" |
| `71~90` | 🔴 红色 | "XX 部位濒临受伤，强烈建议轮休" |
| `91~100` | 🟤 深红 | "XX 部位极度疲劳，极易受伤" |

### 2.3 劳损值自然恢复（核心机制）

**劳损值会自己恢复**，恢复速度取决于球员当天的活动：

| 活动类型 | 恢复规则 |
|---------|---------|
| **完全休息**（无训练无比赛） | 所有部位 `-8.0` |
| **恢复性训练**（水疗、拉伸、单车、理疗） | 所有部位 `-5.0`（训练本身不加劳损） |
| **轻度训练**（定位球、分析、会议、录像） | 所有部位 `-2.0` |
| **正常强度训练**（传控、战术、技术） | 所有部位 `-1.5`（训练带来的劳损可能抵消恢复） |
| **高强度训练**（冲刺、对抗、身体、模型赛） | 无基础恢复（`0`），靠训练后的休息恢复 |
| **比赛日** | 无基础恢复，且根据比赛消耗叠加劳损 |
| **睡眠/日常**（每天基础） | 所有部位 `-1.5`（独立于上述活动，每天必触发） |

> **关键设计**：一个球员如果每天安排高强度训练而不给休息日，劳损会持续爬升；合理穿插恢复日，劳损可以维持在安全区间。

**特质修正（恢复速度）**：

| 特质 | 恢复速度修正 |
|------|------------|
| 铁人 | ×1.30 |
| 年轻气盛（`<23`岁） | ×1.20 |
| 普通 | ×1.00 |
| 老将（`>32`岁） | ×0.80 |
| 玻璃体质 | ×0.85 |

---

## 3. 劳损积累来源

### 3.1 训练劳损（给现有训练内容附加 `wear_impact`）

不新增训练系统，在现有训练内容池中增加一项 `wear_impact` 配置。

** wear_impact 设计原则**：
- 恢复类训练：`0` 或负值（即恢复劳损）
- 低强度技术/分析：少量或无
- 身体/对抗/高强度：明显增加对应部位劳损
- 门将训练：侧重肩、手指、背、膝

**现有训练内容 wear_impact 映射表**：

#### 终结训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `box_finish_one_touch` | 禁区一脚终结 | normal | `quadriceps: +2`, `groin: +1`, `knee: +1` |
| `box_finish_under_pressure` | 对抗下射门选择 | hard | `quadriceps: +3`, `groin: +2`, `back: +2`, `ankle: +1` |
| `cutback_finish` | 倒三角接应射门 | normal | `quadriceps: +2`, `groin: +1` |
| `near_post_finish` | 前点抢射 | normal | `quadriceps: +2`, `knee: +1`, `ankle: +1` |
| `far_post_arrival` | 后点包抄 | normal | `hamstring: +2`, `quadriceps: +2`, `knee: +1` |
| `weak_foot_finish` | 非惯用脚终结 | normal | `quadriceps: +2`, `ankle: +2`, `groin: +1` |
| `long_shot_window` | 禁区弧顶远射窗口 | normal | `quadriceps: +3`, `groin: +2`, `knee: +1` |
| `volley_second_ball` | 二点球凌空处理 | hard | `quadriceps: +3`, `groin: +2`, `back: +2`, `knee: +2` |
| `penalty_routine` | 点球助跑与角度 | light | `quadriceps: +1` |
| `penalty_pressure` | 压力点球模拟 | normal | `quadriceps: +1`, `groin: +1` |

#### 传控训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `rondo_4v2` | 4v2 小圈保球 | normal | `ankle: +2`, `knee: +1`, `groin: +1` |
| `third_man_combination` | 第三人接应配合 | normal | `ankle: +1`, `knee: +1` |
| `wall_pass_timing` | 撞墙配合时机 | normal | `ankle: +1`, `knee: +1` |
| `switch_play` | 弱侧转移 | normal | `hamstring: +1`, `calf: +1`, `knee: +1` |
| `line_breaking_pass` | 穿线直塞 | normal | `ankle: +1` |
| `first_touch_escape` | 第一脚卸压 | normal | `ankle: +2`, `knee: +1` |
| `back_to_goal_link` | 背身接应做球 | hard | `back: +2`, `groin: +2`, `knee: +2`, `ankle: +1` |
| `cross_low_driven` | 低平传中 | normal | `groin: +2`, `hamstring: +1`, `knee: +1` |
| `cross_early` | 提前量传中 | normal | `groin: +2`, `hamstring: +1` |
| `build_out_under_press` | 后场出球抗压 | hard | `ankle: +2`, `knee: +2`, `back: +1`, `groin: +1` |

#### 个人技术

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `dribble_cone_tight` | 密集标志盘带 | normal | `ankle: +3`, `knee: +2`, `groin: +1` |
| `one_v_one_wing` | 边路 1v1 突破 | hard | `hamstring: +3`, `groin: +2`, `ankle: +2`, `knee: +2` |
| `receive_on_half_turn` | 半转身接球 | normal | `ankle: +1`, `knee: +1` |
| `shield_and_roll` | 护球转身摆脱 | hard | `back: +2`, `groin: +2`, `knee: +2`, `ankle: +1` |
| `carry_into_space` | 带球推进空间识别 | normal | `hamstring: +1`, `calf: +1`, `ankle: +1` |
| `touchline_escape` | 边线夹击脱困 | hard | `ankle: +3`, `groin: +2`, `knee: +2`, `hamstring: +2` |
| `receiving_scanning` | 接球前观察 | light | 无 |

#### 防守训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `body_shape_defense` | 防守身体朝向 | normal | `knee: +1`, `ankle: +1` |
| `delay_and_channel` | 延缓与逼向边线 | normal | `hamstring: +1`, `calf: +1`, `knee: +1` |
| `standing_tackle_timing` | 正面抢断时机 | hard | `ankle: +3`, `knee: +3`, `groin: +2`, `hamstring: +2` |
| `cover_shadow_press` | 遮挡传球线路逼抢 | hard | `hamstring: +3`, `calf: +2`, `groin: +2`, `knee: +2` |
| `recovery_run` | 回追路线 | hard | `hamstring: +4`, `calf: +3`, `groin: +2`, `quadriceps: +2` |
| `aerial_duel_defense` | 防守争顶 | normal | `back: +2`, `knee: +2`, `ankle: +1` |
| `box_marking` | 禁区盯人与保护 | normal | `knee: +1`, `ankle: +1`, `back: +1` |
| `counterpress_after_loss` | 丢球后 5 秒反抢 | hard | `hamstring: +3`, `calf: +3`, `groin: +2`, `ankle: +2`, `knee: +2` |

#### 定位球训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `corner_near_post` | 角球前点跑位 | light | `knee: +1` |
| `corner_far_post` | 角球后点包抄 | light | `knee: +1`, `back: +1` |
| `free_kick_direct` | 直接任意球脚法 | light | `quadriceps: +1`, `groin: +1` |
| `free_kick_routine` | 间接任意球配合 | light | `knee: +1` |
| `throw_in_pattern` | 边线球接应套路 | light | `shoulder: +1` |
| `set_piece_marking` | 定位球区域盯防 | light | `knee: +1` |
| `penalty_keeper_read` | 门将扑点预判 | light | `shoulder: +1` |

#### 身体训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `accel_5m` | 5 米启动 | hard | `hamstring: +4`, `calf: +3`, `groin: +2`, `quadriceps: +2` |
| `repeat_sprint` | 重复冲刺能力 | hard | `hamstring: +5`, `calf: +4`, `groin: +3`, `quadriceps: +3`, `knee: +2` |
| `max_velocity` | 最高速度跑 | hard | `hamstring: +5`, `calf: +3`, `groin: +2`, `quadriceps: +2` |
| `change_direction` | 变向制动 | hard | `ankle: +4`, `knee: +3`, `groin: +3`, `hamstring: +2` |
| `upper_body_duel` | 上肢对抗 | hard | `shoulder: +3`, `back: +3`, `ribs: +2` |
| `core_stability` | 核心稳定 | normal | `back: +2`, `groin: +1` |
| `aerobic_blocks` | 分段有氧跑 | hard | `hamstring: +3`, `calf: +3`, `quadriceps: +2`, `knee: +2` |
| `jump_power` | 起跳与落地 | normal | `knee: +3`, `back: +2`, `ankle: +2`, `achilles: +2` |

#### 战术训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `build_up_2_3` | 2-3 出球结构 | normal | `ankle: +1`, `knee: +1` |
| `wide_overload` | 边路局部人数优势 | normal | `hamstring: +1`, `groin: +1`, `ankle: +1` |
| `central_compactness` | 中路紧凑防守 | normal | `knee: +1`, `ankle: +1` |
| `press_trigger` | 逼抢触发点 | hard | `hamstring: +3`, `calf: +2`, `groin: +2`, `ankle: +2`, `knee: +2` |
| `rest_defense` | 进攻时防反站位 | normal | `hamstring: +1`, `knee: +1` |
| `transition_attack` | 抢回球后的第一传 | normal | `hamstring: +1`, `calf: +1` |
| `transition_defense` | 失球权后的回收 | hard | `hamstring: +3`, `calf: +2`, `groin: +2`, `quadriceps: +2` |
| `game_model_8v8` | 8v8 队内模型赛 | hard | `hamstring: +3`, `calf: +3`, `knee: +3`, `ankle: +3`, `groin: +2`, `back: +2` |

#### 门将训练

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `gk_set_position` | 准备姿势与重心 | normal | `knee: +1`, `ankle: +1` |
| `gk_low_save` | 低平球扑救 | normal | `shoulder: +2`, `knee: +2`, `back: +1` |
| `gk_close_range` | 近距离封堵 | hard | `shoulder: +3`, `knee: +3`, `fingers: +2`, `back: +2` |
| `gk_cross_claim` | 传中球摘取 | normal | `shoulder: +2`, `back: +2`, `knee: +2`, `fingers: +1` |
| `gk_one_v_one` | 单刀出击 | hard | `knee: +3`, `ankle: +3`, `shoulder: +2`, `back: +2` |
| `gk_distribution_short` | 短传出球 | light | `shoulder: +1` |
| `gk_distribution_long` | 长距离开球 | normal | `shoulder: +2`, `back: +2`, `groin: +1` |
| `gk_penalty_read` | 点球方向读取 | light | `shoulder: +1` |

#### 恢复与分析

| 训练 ID | 名称 | 强度 | wear_impact |
|---------|------|------|-------------|
| `full_rest` | 完全休息 | recovery | 所有部位 `-8.0` |
| `mobility_session` | 活动度与拉伸 | recovery | 所有部位 `-5.0` |
| `recovery_bike` | 低强度单车恢复 | recovery | 所有部位 `-4.0` |
| `hydro_recovery` | 水疗恢复 | recovery | 所有部位 `-5.0` |
| `individual_treatment` | 个人理疗 | recovery | 所有部位 `-6.0`（指定球员） |
| `match_review_unit` | 分组录像复盘 | light | 无 |
| `opponent_clip_study` | 对手片段研究 | light | 无 |
| `role_meeting` | 位置职责会议 | light | 无 |
| `captain_meeting` | 队长沟通会 | light | 无 |

> **结算方式**：每天训练结束后，累加当天所有训练时段的 `wear_impact`，然后减去当天基础恢复（睡眠 `-1.5` + 活动恢复），得到净变化。

### 3.2 比赛劳损（实时微量累积）

比赛引擎中，每次动作后对相关部位**微量加值**：

| 比赛动作 | 涉及部位与加值 |
|---------|--------------|
| **高速冲刺**（每次） | `hamstring: +0.15`, `calf: +0.12`, `groin: +0.08`, `quadriceps: +0.08`, `knee: +0.05` |
| **变向急停**（每次） | `ankle: +0.15`, `knee: +0.12`, `groin: +0.10` |
| **射门/大力传球**（每次） | `quadriceps: +0.12`, `groin: +0.10`, `knee: +0.08`, `back: +0.05` |
| **争顶/头球**（每次） | `back: +0.10`, `shoulder: +0.12`, `head: +0.08`, `knee: +0.05` |
| **铲球/被铲**（每次） | `ankle: +0.20`, `knee: +0.18`, `hamstring: +0.10`, `calf: +0.08`, `groin: +0.05` |
| **门将扑救/鱼跃**（每次） | `shoulder: +0.20`, `back: +0.15`, `fingers: +0.15`, `knee: +0.12`, `head: +0.08` |
| **门将开大脚**（每次） | `quadriceps: +0.10`, `groin: +0.08`, `back: +0.05` |
| **每分钟比赛时间**（基础消耗） | `hamstring: +0.03`, `quadriceps: +0.03`, `calf: +0.03`, `knee: +0.02`, `back: +0.01` |
| **每分钟加时时间** | 上述所有 ×1.5 |

**疲劳放大效应**（与 stamina 联动）：

| stamina 区间 | 劳损累积倍率 | 说明 |
|-------------|-------------|------|
| `> 60` | ×1.00 | 正常 |
| `30~60` | ×1.30 | 肌肉控制力下降 |
| `< 30` | ×1.80 | 动作严重变形，代偿受伤风险剧增 |

**示例**：一名中场球员打满 90 分钟，冲刺 18 次，被铲 2 次，射门 3 次：
- 基础时间：`hamstring +2.7`, `quadriceps +2.7`, `calf +2.7`, `knee +1.8`, `back +0.9`
- 冲刺：`hamstring +2.7`, `calf +2.16`, `groin +1.44`, `quadriceps +1.44`, `knee +0.9`
- 被铲：`ankle +0.4`, `knee +0.36`, `hamstring +0.2`, `calf +0.16`
- 射门：`quadriceps +0.36`, `groin +0.3`, `knee +0.24`, `back +0.15`
- **单场合计**：`hamstring ≈ 5.6`, `quadriceps ≈ 4.5`, `calf ≈ 5.0`, `knee ≈ 3.3`, `ankle ≈ 0.4`

一场比赛后，若不安排恢复，这些劳损会保留到次日训练。

---

## 4. 伤病触发与部位选择逻辑

### 4.1 触发时机

在以下时刻进行**部位伤病检定**：

1. **凶狠铲球后**（已有逻辑扩展）
2. **危险犯规后**（已有逻辑扩展）
3. **冲刺后**（新增，尤其是 stamina < 30 时）
4. **争顶倒地后**（新增）
5. **门将出击碰撞后**（新增）
6. **stamina < 15 时每分钟**（新增，疲劳性伤病）
7. **赛后结算**（新增，当 stamina 最终 < 10 且出场 > 80 分钟）

### 4.2 检定公式

```
检定通过 = random(0, 1) < 基础动作概率 × 劳损系数 × 体质修正
```

**基础动作概率**（极低，这是控制重伤率的关键）：

| 触发动作 | 轻伤基础概率 | 中伤基础概率 | 重伤基础概率 |
|---------|------------|------------|------------|
| 凶狠铲球（tackleIntensity > 14） | 1.0% | 0.15% | **0.02%** |
| 危险犯规（红牌级别） | 2.0% | 0.30% | **0.05%** |
| 冲刺后（stamina < 30） | 0.8% | 0.10% | **0.01%** |
| 争顶倒地 | 0.5% | 0.08% | **0.01%** |
| 疲劳临界点（stamina < 15） | 1.5% | 0.20% | **0.02%** |
| 赛后过度消耗 | 1.0% | 0.15% | **0.01%** |

> **为什么重伤概率这么低？** 一支球队赛季 30 场，每场约 14 人上场，每人每场平均遭遇 2-3 次高危动作。`0.02%` × 30场 × 14人 × 3次 ≈ **0.25 次/赛季/队**，加上训练累积和疲劳放大，最终落在 **1-2 次/赛季/队** 区间。

**劳损系数**（根据触发动作涉及部位的**最高劳损值**计算）：

```
劳损系数 = (1 + 最高劳损值 / 50) ^ 2
```

| 最高劳损值 | 劳损系数 | 示例说明 |
|-----------|---------|---------|
| 0 | 1.00 | 健康状态，纯基础概率 |
| 25 | 2.25 | 略有疲劳，概率翻倍 |
| 50 | 4.00 | 明显疲劳，概率翻 4 倍 |
| 75 | 9.00 | 濒临受伤，概率翻 9 倍 |
| 90 | 12.96 | 极度疲劳，概率翻 13 倍 |
| 100 | 16.00 | 临界点，极易受伤 |

**体质修正**：

| 特质 | 修正倍率 |
|------|---------|
| 铁人 | ×0.60 |
| 年轻气盛（`<23`岁） | ×0.85 |
| 普通 | ×1.00 |
| 老将（`>32`岁） | ×1.20 |
| 玻璃体质 | ×1.50 |
| 近 30 天同部位受过伤 | ×1.30（叠加） |

**检定示例**：
- 某球员腿筋劳损 75，被凶狠铲球
- 轻伤概率 = 1.0% × 9.0 × 1.0 = **9%**
- 中伤概率 = 0.15% × 9.0 × 1.0 = **1.35%**
- 重伤概率 = 0.02% × 9.0 × 1.0 = **0.18%**

### 4.3 发生伤病后：确定受伤部位与类型

**Step 1：确定候选部位**
根据触发动作，列出最可能受伤的部位：

| 触发动作 | 候选部位（按优先级排序） |
|---------|------------------------|
| 铲球/被铲 | `ankle`, `knee`, `hamstring`, `calf`, `groin` |
| 危险犯规 | `ankle`, `knee`, `hamstring`, `groin`, `quadriceps`, `calf`, `ribs`, `head` |
| 冲刺/急停 | `hamstring`, `groin`, `calf`, `quadriceps`, `ankle` |
| 争顶/碰撞 | `head`, `shoulder`, `back`, `ribs`, `knee` |
| 门将扑救 | `shoulder`, `fingers`, `back`, `head`, `knee` |
| 疲劳自发 | `hamstring`, `quadriceps`, `calf`, `groin` |
| 赛后过度消耗 | `hamstring`, `quadriceps`, `calf`, `groin`, `back` |

**Step 2：选择实际受伤部位**
在候选部位中，选择**当前劳损值最高**的部位。如果多个部位相同，按候选列表的优先级选第一个。

> 这模拟了"最疲劳的部位先崩"。

**Step 3：确定严重程度**
根据该部位的劳损值决定：

| 劳损值 | 轻伤概率 | 中伤概率 | 重伤概率 |
|-------|---------|---------|---------|
| `0~40` | 75% | 20% | 5% |
| `41~60` | 50% | 35% | 15% |
| `61~80` | 30% | 40% | 30% |
| `81~100` | 15% | 35% | 50% |

> 即使检定通过了，如果最终 roll 到"轻伤"而触发动作本来就是中/高危，叙事上表现为"XX 一瘸一拐但继续比赛"。

---

## 5. 真实伤病映射表

### 5.1 伤病类型库

恢复时间从对应区间的 `[min, max]` 内**均匀随机取一个整数**。

| 部位 | 轻伤（继续比赛，属性下降） | 中伤（休战） | 重伤（休战） |
|------|------------------------|------------|------------|
| **腿筋** | 肌肉紧绷（1~2天） | 轻度拉伤（4~6天） | 中度拉伤（7~12天） |
| **股四头肌** | 肌肉酸痛（1~2天） | 轻度拉伤（4~6天） | 中度拉伤/挫伤（7~12天） |
| **小腿** | 小腿紧绷（1~2天） | 轻度拉伤（4~6天） | 中度拉伤（7~12天） |
| **腹股沟** | 腹股沟紧绷（1~2天） | 轻度拉伤（5~7天） | 中度拉伤（7~12天） |
| **脚踝** | 轻度扭伤（1~2天） | 中度扭伤（5~8天） | 严重扭伤（7~12天） |
| **膝盖** | 膝盖不适（1~2天） | 膝盖挫伤/滑囊炎（5~8天） | MCL轻度扭伤（7~12天） |
| **跟腱** | 跟腱紧绷（1~2天） | 轻度肌腱炎（5~8天） | 中度炎症（8~12天） |
| **足/脚趾** | 脚趾不适（1天） | 足部瘀伤/足底筋膜炎（5~8天） | 脚趾骨折（7~12天） |
| **腰背** | 腰背僵硬（1~2天） | 腰部肌肉痉挛（5~8天） | 下背部拉伤（7~12天） |
| **肋骨** | 肋部不适（1~2天） | 肋骨挫伤（6~9天） | 单根肋骨骨折（8~12天） |
| **肩部** | 肩部僵硬（1~2天） | 肩袖拉伤（5~8天） | 肩关节扭伤（7~12天） |
| **手指** | 手指不适（1天） | 手指挫伤/脱臼（4~6天） | 手指骨折（7~12天） |
| **头/面部** | 面部擦伤（1天） | 面部淤肿/鼻骨挫伤（5~8天） | 鼻骨骨折/轻度脑震荡（7~12天） |

> **关键约束**：所有伤病恢复时间上限为 **15 天**。不存在需要 16 天以上的伤病。

### 5.2 轻伤在比赛中的属性影响

废除统一 `×0.85`，改为**部位关联属性衰减**：

```
EffectiveAttr[i] = BaseAttr[i] × FatigueMultiplier × InjuryMultiplier[i]
```

| 受伤部位 | 核心衰减属性 | 衰减幅度 | 次要衰减属性 | 衰减幅度 |
|---------|------------|---------|------------|---------|
| 腿筋 | 加速、最高速、耐力 | -15% | 盘带、射门力量 | -8% |
| 股四头肌 | 射门力量、跳跃、加速 | -12% | 盘带、传球 | -5% |
| 小腿 | 加速、耐力、平衡 | -10% | 传球精度 | -5% |
| 腹股沟 | 变向、盘带、射门 | -15% | 加速 | -10% |
| 脚踝 | 盘带、敏捷、传球精度 | -12% | 射门、平衡 | -8% |
| 膝盖 | 加速、跳跃、对抗 | -15% | 耐力、射门力量 | -10% |
| 跟腱 | 加速、跳跃、耐力 | -12% | 盘带 | -8% |
| 足/脚趾 | 传球精度、盘带 | -8% | 射门、加速 | -5% |
| 腰背 | 对抗、头球、力量 | -10% | 传球、射门 | -5% |
| 肋骨 | 对抗、耐力（呼吸受限） | -10% | 头球 | -8% |
| 肩部 | 对抗、手抛球、头球 | -10% | — | — |
| 手指 | 手抛球（门将） | -15% | 平衡 | -3% |
| 头/面部 | 头球 | -5% | — | — |

**门将专属加码**：
- 手指受伤：扑救反应 -20%，手控球 -25%
- 肩部受伤：扑救范围 -15%，手抛球 -20%
- 头/面部受伤：出击果断性 -10%
- 腿部受伤：出击速度 -15%，开球精度 -10%

**中伤/重伤**：球员**立即被换下**（如果还有换人名额），或**坚持到比赛结束但赛后强制休战**（无名额时）。理想情况下，中伤和重伤应直接触发换人动画/事件。

---

## 6. 恢复机制与劳损清除

### 6.1 恢复时间确定

伤病发生时：

```go
days := rand.Intn(max-min+1) + min  // [min, max] 闭区间均匀随机
```

### 6.2 伤病期间每日结算

伤病期间，每天对该球员执行：

| 结算项 | 规则 |
|-------|------|
| **伤病倒计时** | `remaining_days -= 1`，到 `0` 时标记为伤愈 |
| **受伤部位劳损清除** | 受伤部位每天 `-15`（因为强制休息） |
| **其他部位劳损** | 按当天活动正常结算（如果球员当天还安排了训练——应该禁止） |

**伤病期间行为限制**：
- 中伤/重伤球员：**禁止安排任何训练**，只能"完全休息"
- 轻伤球员（比赛中）：**当天比赛后继续参赛不受影响**，但次日训练建议降为恢复性

### 6.3 伤愈后的残余劳损（玻璃人机制）

这是让伤病系统有长期管理深度的关键设计：

```
伤愈后该部位劳损值 = max(当前值 - 恢复期间清除的量, random(15, 30))
```

- 假设球员腿筋原本劳损 85，受伤休战 12 天
- 12 天强制清除：12 × 15 = 180，但只降到随机残余值
- 实际伤愈后：腿筋劳损 ≈ `random(15, 30)`，比如 22
- 如果玩家让该球员立即参加高强度训练/比赛，22 的残余值很快再次爬升

**反复受伤惩罚**（同一部位 30 天内）：

| 次数 | 效果 |
|------|------|
| 第 1 次 | 标准恢复区间 |
| 第 2 次 | 恢复区间上限 `+2` 天，残余值 `random(20, 35)` |
| 第 3 次及以上 | 恢复区间上限 `+5` 天，残余值 `random(30, 45)`，且基础概率额外 ×1.3 |

> 这创造了真实的"玻璃人"球员——某个球员如果腿筋反复出问题，玩家必须长期控制他的冲刺训练和出场时间。

### 6.4 非受伤部位的日常恢复

即使球员没有受伤，劳损值也会自然波动：

```
每日净变化 = 训练/比赛带来的劳损累加 - 基础恢复 - 睡眠恢复
```

- 一个训练周示例（单部位）：
  - Day 1 高强度：`+5` 劳损，睡眠 `-1.5`，净 `+3.5`
  - Day 2 中强度：`+2` 劳损，睡眠 `-1.5`，净 `+0.5`
  - Day 3 恢复训练：`-5` 恢复，睡眠 `-1.5`，净 `-6.5`
  - Day 4 比赛：`+6` 劳损，睡眠 `-1.5`，净 `+4.5`
  - Day 5 完全休息：`-8` 恢复，睡眠 `-1.5`，净 `-9.5`
  - **周净变化**：`-7.5`（健康波动）

只有连续高强度不休息，才会让劳损突破 60 临界线。

---

## 7. 体质与特质影响

通过**修正劳损积累速度**和**恢复清除速度**实现：

| 特质 | 劳损积累 | 恢复速度 | 残余值 | 说明 |
|------|---------|---------|--------|------|
| **铁人** | ×0.70 | ×1.30 | 10~20 | 极难受伤，恢复快 |
| **年轻气盛**（`<23`岁） | ×1.00 | ×1.20 | 标准 | 正常累积，恢复稍快 |
| **普通** | ×1.00 | ×1.00 | 15~30 | 基准 |
| **老将**（`>32`岁） | ×1.20 | ×0.80 | 标准 | 更容易疲劳，恢复更慢 |
| **玻璃体质** | ×1.50 | ×0.85 | 25~40 | 极易反复受伤 |
| **近 30 天受过伤** | ×1.20 | 标准 | +5~10 | 叠加惩罚 |

---

## 8. 数据结构设计

### 8.1 球员结构扩展

```go
// 身体部位劳损值
type PlayerBodyWear struct {
    Hamstring    float64
    Quadriceps   float64
    Calf         float64
    Groin        float64
    Ankle        float64
    Knee         float64
    Achilles     float64
    Foot         float64
    Back         float64
    Ribs         float64
    Shoulder     float64
    Fingers      float64
    Head         float64
}

type InjuryRecord struct {
    ID            string
    PlayerID      string
    
    BodyPart      string           // "hamstring", "ankle" 等
    InjuryName    string           // "腿筋中度拉伤"
    Severity      int              // 1=轻伤(比赛中继续) 2=中伤 3=重伤(休战)
    
    TotalDays     int              // 从 [min,max] 随机取的总天数
    RemainingDays int              // 剩余天数，每日 -1
    
    MatchID       *string          // 导致伤病的比赛（nullable）
    Minute        int              // 比赛分钟（0表示训练导致）
    CauseEvent    string           // "tackle" / "foul" / "sprint" / "collision" / "fatigue" / "training" / "post_match"
    
    AttrImpact    map[string]float64 // 仅 severity=1 有效，如 {"pace": 0.85, "dribbling": 0.92}
    
    IsActive      bool
    CreatedAt     time.Time
    RecoveredAt   *time.Time
}

type Player struct {
    // 现有字段...
    
    BodyWear      PlayerBodyWear    // 13个部位劳损值
    CurrentInjury *InjuryRecord     // 当前活跃伤病（nil=健康）
    InjuryHistory []InjuryRecord    // 历史伤病（近30天记录用于反复惩罚）
    
    Traits        []string          // ["铁人", "玻璃体质"] 等
    Age           int
}
```

### 8.2 训练内容扩展

```go
type TrainingItem struct {
    ID          string
    Name        string
    Category    string
    Intensity   string       // light / normal / hard / recovery
    
    // 现有字段：attribute_weights, base_gain 等...
    
    // 新增：劳损影响映射
    WearImpact  map[string]float64  // 如 {"hamstring": 4.0, "calf": 3.0, "knee": 2.0}
}
```

### 8.3 比赛引擎内扩展

```go
// 比赛动作后调用
func (sim *Simulator) applyWearAfterAction(ms *MatchState, player *Player, action string) {
    multiplier := 1.0
    if player.Stamina < 30 {
        multiplier = 1.8
    } else if player.Stamina < 60 {
        multiplier = 1.3
    }
    
    switch action {
    case "sprint":
        player.BodyWear.Hamstring += 0.15 * multiplier
        player.BodyWear.Calf += 0.12 * multiplier
        // ...
    case "tackle", "tackled":
        player.BodyWear.Ankle += 0.20 * multiplier
        player.BodyWear.Knee += 0.18 * multiplier
        // ...
    }
    
    // 每分钟基础消耗
    player.BodyWear.Hamstring += 0.03 * multiplier
    // ...
}

// 伤病检定
func (sim *Simulator) checkInjury(ms *MatchState, player *Player, action string, candidateParts []string) {
    maxWear := 0.0
    selectedPart := ""
    for _, part := range candidateParts {
        wear := player.BodyWear.Get(part)
        if wear > maxWear {
            maxWear = wear
            selectedPart = part
        }
    }
    
    if selectedPart == "" {
        return
    }
    
    wearFactor := math.Pow(1.0 + maxWear/50.0, 2.0)
    traitMod := sim.getTraitModifier(player)
    
    baseRates := map[string][3]float64{
        "brutal_tackle":  {0.010, 0.0015, 0.0002},  // 轻/中/重
        "dangerous_foul": {0.020, 0.0030, 0.0005},
        "sprint_fatigue": {0.008, 0.0010, 0.0001},
        "aerial_clash":   {0.005, 0.0008, 0.0001},
        "fatigue_crit":   {0.015, 0.0020, 0.0002},
        "post_overuse":   {0.010, 0.0015, 0.0001},
    }
    
    rates := baseRates[action]
    lightProb := rates[0] * wearFactor * traitMod
    medProb := rates[1] * wearFactor * traitMod
    severeProb := rates[2] * wearFactor * traitMod
    
    roll := sim.r.Float64()
    // ... 根据概率 roll 严重程度
}
```

---

## 9. 与现有系统的衔接点

| 现有文件/模块 | 修改内容 |
|-------------|---------|
| `internal/domain/player.go` | Player 结构体加 `BodyWear` 和 `CurrentInjury` |
| `internal/engine/simulator.go` | 铲球/犯规/冲刺/争顶后加 `applyWear()` + `checkInjury()`；重伤球员强制离场逻辑 |
| `internal/engine/stamina.go` | stamina 结算时同步调用 `applyWearPerMinute()`；stamina<15 时触发疲劳伤病检定 |
| `internal/engine/narrative.go` | 为每种真实伤病增加叙事文本 |
| `internal/config/constants.go` | 新增伤病名称常量、部位常量、恢复区间表、基础概率表 |
| 后端训练模块 | `training_items` 表加 `wear_impact` JSON 字段；训练结算时更新球员 `BodyWear` |
| 后端每日结算 | 新增每日 `BodyWear` 自然恢复逻辑；伤病 `RemainingDays--` |
| 后端阵容校验 | 赛前检查 `CurrentInjury != nil && Severity >= 2`，禁止入选 |
| 前端球员卡片 | 部位健康色条（不显示精确数字）；伤病状态 tooltip |

---

## 10. 测试与压测方案

### 10.1 单元测试

#### 测试 1：劳损自然恢复
```go
func TestBodyWearNaturalRecovery(t *testing.T) {
    player := NewPlayer()
    player.BodyWear.Hamstring = 50.0
    
    // 模拟一天完全休息
    player.ApplyDailyRecovery(ActivityFullRest)
    
    // 期望：50 - 8(完全休息) - 1.5(睡眠) = 40.5
    assert.InDelta(t, 40.5, player.BodyWear.Hamstring, 0.01)
}
```

#### 测试 2：训练劳损累加
```go
func TestTrainingWearAccumulation(t *testing.T) {
    player := NewPlayer()
    training := TrainingItem{WearImpact: map[string]float64{
        "hamstring": 5.0, "calf": 3.0,
    }}
    
    player.ApplyTrainingWear(training)
    
    assert.InDelta(t, 5.0, player.BodyWear.Hamstring, 0.01)
    assert.InDelta(t, 3.0, player.BodyWear.Calf, 0.01)
}
```

#### 测试 3：伤病概率边界
```go
func TestInjuryProbabilityBounds(t *testing.T) {
    // 验证：健康球员（劳损=0）被凶狠铲球，重伤概率 <= 0.02%
    prob := CalculateInjuryProbability("brutal_tackle", 0, 1.0)
    assert.LessOrEqual(t, prob, 0.0002)
    
    // 验证：疲劳球员（劳损=80）被凶狠铲球，重伤概率 <= 0.4%
    prob = CalculateInjuryProbability("brutal_tackle", 80, 1.0)
    assert.LessOrEqual(t, prob, 0.004)
}
```

#### 测试 4：恢复区间随机性
```go
func TestRecoveryDaysInRange(t *testing.T) {
    for i := 0; i < 1000; i++ {
        days := RandomRecoveryDays(10, 15)
        assert.GreaterOrEqual(t, days, 10)
        assert.LessOrEqual(t, days, 15)
    }
}
```

#### 测试 5：伤愈残余劳损
```go
func TestPostRecoveryResidualWear(t *testing.T) {
    player := NewPlayer()
    player.BodyWear.Hamstring = 85.0
    
    // 模拟伤愈（12天）
    player.RecoverFromInjury("hamstring", 12)
    
    // 期望：残余值在 15~30 之间
    assert.GreaterOrEqual(t, player.BodyWear.Hamstring, 15.0)
    assert.LessOrEqual(t, player.BodyWear.Hamstring, 30.0)
}
```

#### 测试 6：反复受伤惩罚
```go
func TestRepeatedInjuryPenalty(t *testing.T) {
    player := NewPlayer()
    
    // 同一部位 30 天内受伤 3 次
    player.RecordInjury("hamstring")
    player.RecordInjury("hamstring")
    player.RecordInjury("hamstring")
    
    days := player.GenerateRecoveryDays("hamstring", 10, 15)
    // 第 3 次：上限 +5，即 10~20，但受全局上限 15 限制，所以 10~15
    // 如果上层允许突破，则为 10~20
    assert.GreaterOrEqual(t, days, 10)
}
```

### 10.2 压测（Monte Carlo 模拟）

压测目标是验证：**一支球队一个赛季最多 1-2 次严重伤病**。

#### 压测 1：赛季重伤率基准测试
```go
func BenchmarkSeasonInjuryRate(b *testing.B) {
    const (
        seasons = 10000       // 模拟 10000 个赛季
        teamsPerSeason = 20   // 20 支球队
        matchesPerTeam = 30   // 每队 30 场
        squadSize = 25        // 每队 25 人
    )
    
    totalSevere := 0
    
    for s := 0; s < seasons; s++ {
        for t := 0; t < teamsPerSeason; t++ {
            teamSevere := simulateTeamSeason(squadSize, matchesPerTeam)
            totalSevere += teamSevere
        }
    }
    
    avgPerTeam := float64(totalSevere) / float64(seasons*teamsPerSeason)
    
    // 断言：平均每队每赛季重伤次数应在 0.5 ~ 2.0 之间
    assert.GreaterOrEqual(b, avgPerTeam, 0.5)
    assert.LessOrEqual(b, avgPerTeam, 2.0)
    
    b.Logf("Average severe injuries per team per season: %.3f", avgPerTeam)
}
```

**压测参数设计**：

```go
func simulateTeamSeason(squadSize, matches int) int {
    teamSevere := 0
    
    for m := 0; m < matches; m++ {
        // 每场比赛约 14 人上场
        starters := pickStarters(squadSize, 14)
        
        for _, player := range starters {
            // 模拟比赛中的动作
            tackles := rand.Intn(4)          // 0-3 次被铲
            sprints := rand.Intn(15) + 5     // 5-19 次冲刺
            aerials := rand.Intn(6)          // 0-5 次争顶
            minutes := 90
            
            // 累积劳损
            player.accumulateMatchWear(tackles, sprints, aerials, minutes)
            
            // 伤病检定
            if player.checkMatchInjuries(tackles, sprints, aerials) {
                if player.CurrentInjury.Severity == 3 {
                    teamSevere++
                }
            }
        }
        
        // 赛后训练（模拟典型训练周）
        for _, player := range squad {
            player.applyWeeklyTraining()
            player.applyDailyRecovery()
        }
    }
    
    return teamSevere
}
```

#### 压测 2：不同管理策略对比
```go
func BenchmarkManagementStrategyImpact(b *testing.B) {
    strategies := []struct {
        name string
        fn   func(*Player)
    }{
        {"high_intensity", highIntensitySchedule},   // 大量 hard 训练
        {"balanced", balancedSchedule},              // 正常轮换
        {"conservative", conservativeSchedule},      // 多恢复日
    }
    
    for _, strat := range strategies {
        totalInjuries := 0
        totalSevere := 0
        
        for i := 0; i < 5000; i++ {
            team := generateRandomTeam(25)
            severe, all := simulateSeasonWithStrategy(team, strat.fn)
            totalInjuries += all
            totalSevere += severe
        }
        
        b.Logf("%s: avg injuries=%.2f, avg severe=%.2f",
            strat.name,
            float64(totalInjuries)/5000,
            float64(totalSevere)/5000)
    }
}
```

**期望结果**：
| 策略 | 场均伤病 | 赛季重伤 | 说明 |
|------|---------|---------|------|
| 高强度不休息 | ~8-12 次 | ~3-5 次 | 应明显高于基准，证明系统有管理深度 |
| 均衡轮换 | ~3-5 次 | ~1-2 次 | 基准，符合设计目标 |
| 保守恢复 | ~1-3 次 | ~0-1 次 | 极低，但有成长代价 |

#### 压测 3：极端情况应力测试
```go
func BenchmarkExtremeWearScenario(b *testing.B) {
    // 场景：连续 3 周高强度训练 + 一周双赛，不休息
    player := NewPlayer()
    player.BodyWear.Hamstring = 75.0  // 已濒临受伤
    
    injuries := 0
    for week := 0; week < 3; week++ {
        for day := 0; day < 7; day++ {
            if day == 0 || day == 4 {
                // 比赛日
                player.accumulateMatchWear(3, 15, 3, 90)
                if player.checkMatchInjuries(3, 15, 3) {
                    injuries++
                    // 重置继续测试（模拟下一个球员）
                    player = NewPlayer()
                    player.BodyWear.Hamstring = 75.0
                }
            } else {
                // 高强度训练
                player.BodyWear.Hamstring += 5.0
            }
        }
    }
    
    b.Logf("Injuries in extreme scenario: %d", injuries)
}
```

### 10.3 平衡性调整指南

如果压测结果显示重伤率偏离目标（1-2 次/队/赛季），按以下优先级调整：

| 偏离方向 | 调整手段 | 影响 |
|---------|---------|------|
| **重伤太多** | 降低 `base_severe_rate`（如从 0.02% 降到 0.015%） | 直接降低重伤率 |
| **重伤太多** | 提高自然恢复速度（如完全休息从 -8 提高到 -10） | 让玩家更容易维持低劳损 |
| **重伤太多** | 提高劳损系数分母（如从 `/50` 改为 `/60`） | 高劳损不再那么致命 |
| **重伤太少** | 提高 `base_severe_rate`（如从 0.02% 提高到 0.03%） | 直接提高重伤率 |
| **重伤太少** | 降低自然恢复速度（如完全休息从 -8 降到 -6） | 劳损更容易累积 |
| **中伤太少** | 提高 `base_medium_rate` | 中伤是赛季常态，应比重伤多 3-5 倍 |
| **轻伤太多/太少** | 调整 `base_light_rate` 或 stamina 放大倍率 | 轻伤是比赛氛围的一部分，不影响长期规划 |

**推荐初始校准流程**：
1. 跑 10000 赛季基准测试，记录每队平均 `轻伤/中伤/重伤` 次数
2. 目标比例：`轻伤 : 中伤 : 重伤 ≈ 10 : 3 : 1`
3. 如果重伤均值 > 2.5，降低 `base_severe_rate` 25%
4. 如果重伤均值 < 0.5，提高 `base_severe_rate` 50%
5. 重复直到落在 `0.8 ~ 1.8` 区间

---

## 11. 玩家层面交互设计

### 11.1 球员详情页

```
┌─────────────────────────────┐
│  张三  │  位置: CM  │  年龄: 24  │
├─────────────────────────────┤
│ 身体部位健康度               │
│ 🟢 腿筋  🟢 股四  🟡 小腿    │
│ 🟠 脚踝  🟢 膝盖  🟢 跟腱    │
│ 🟢 足部  🟢 腰背  🟢 肋骨    │
│ 🟢 肩部  🟢 手指  🟢 头部    │
├─────────────────────────────┤
│ 当前状态: 健康               │
│ 历史伤病: 腿筋拉伤(2个月前)  │
└─────────────────────────────┘
```

### 11.2 阵容选择界面

- 重伤/中伤球员：**灰色不可选**，hover 显示"腿筋中度拉伤 · 恢复中 7/12 天"
- 轻伤球员：**黄色边框可选**，选中后属性面板显示黄色衰减标记，如"加速 ↓15%（腿筋紧绷）"
- 部位隐患球员（劳损 >70 但未受伤）：**橙色警告角标**，提示"XX 部位疲劳，建议轮休"

### 11.3 比赛直播叙事

| 严重程度 | 叙事示例 |
|---------|---------|
| 轻伤 | "🔶 张三在一次拼抢中捂住了大腿后侧，队医进场简单处理后他选择继续比赛。" |
| 中伤 | "🔴 张三倒地不起！看起来是脚踝扭伤了，队医正在检查... 他被担架抬出场外，预计将缺席数日。" |
| 重伤 | "🔴🔴 这是一次严重的碰撞！张三痛苦地抱着膝盖，队医迅速进场... 情况不太乐观，可能需要长期休战。" |

### 11.4 每日报告

- 训练后："经过今日的重复冲刺训练，多名球员腿部疲劳有所上升。"
- 恢复后："李四经过一天休息，腰背疲劳明显缓解。"
- 伤病预警："王五的脚踝疲劳已达到临界值（89），下一场比赛存在受伤风险。"

---

## 12. 实施优先级

| 阶段 | 内容 | 预计工期 |
|------|------|---------|
| **Phase 1** | `PlayerBodyWear` 数据结构 + 训练 `wear_impact` 配置 + 每日恢复结算 | 3 天 |
| **Phase 2** | 比赛引擎 `applyWear()` + `checkInjury()` + 真实伤病映射 | 4 天 |
| **Phase 3** | 阵容校验（伤病球员禁止入选）+ 恢复倒计时 + 伤愈残余劳损 | 2 天 |
| **Phase 4** | 前端部位健康色条 + 伤病叙事文本 + 每日报告接入 | 3 天 |
| **Phase 5** | 压测校准（Monte Carlo 调整参数到 1-2 重伤/队/赛季） | 2 天 |

---

## 附录：快速参考表

### A. 部位常量

```go
const (
    PartHamstring  = "hamstring"
    PartQuadriceps = "quadriceps"
    PartCalf       = "calf"
    PartGroin      = "groin"
    PartAnkle      = "ankle"
    PartKnee       = "knee"
    PartAchilles   = "achilles"
    PartFoot       = "foot"
    PartBack       = "back"
    PartRibs       = "ribs"
    PartShoulder   = "shoulder"
    PartFingers    = "fingers"
    PartHead       = "head"
)
```

### B. 恢复区间表

```go
var RecoveryRanges = map[string]map[int][2]int{
    "hamstring": {
        1: {1, 2},   // 轻伤
        2: {4, 6},   // 中伤
        3: {10, 15}, // 重伤
    },
    "quadriceps": {
        1: {1, 2},
        2: {4, 6},
        3: {10, 15},
    },
    // ... 所有部位
}
```

### C. 基础概率表

```go
var BaseInjuryRates = map[string][3]float64{
    "brutal_tackle":  {0.010, 0.0015, 0.0002},
    "dangerous_foul": {0.020, 0.0030, 0.0005},
    "sprint_fatigue": {0.008, 0.0010, 0.0001},
    "aerial_clash":   {0.005, 0.0008, 0.0001},
    "fatigue_crit":   {0.015, 0.0020, 0.0002},
    "post_overuse":   {0.010, 0.0015, 0.0001},
}
```
