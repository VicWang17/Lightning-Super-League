# 训练系统玩法设计

> 版本：v1.0  
> 范围：训练系统的玩法、成长数值、数据模型和 AI 规划设计。  
> 当前目标：先形成可评审的设计文档，不直接改实现代码。

## 1. 设计定位

训练系统是《闪电超级联赛》的长期养成核心。它不只是每周点格子的日常功能，而是连接球员成长、球队风格、阵容轮换和赛季规划的主要系统。

项目当前已经具备以下基础：

- 球员模型已有 23 项能力，范围 1-20。
- 球员已有 `potential_max` 潜力上限。
- 球员已有 `fitness`、`match_form`、`match_rust_score`、`state_training_load_score` 等状态字段。
- 前端已有 `/training/weekly`、`/training/calendar`、`/training/fatigue`、`/training/history` 页面，但主要是 mock。
- 后端已有空的 `TrainingStateProvider`，适合后续接入训练状态来源。

训练系统 v1 的核心原则：

1. **永久成长为主**
   - 训练产生永久能力成长，而不是只给临时加成。
   - 比赛前备战类训练可以提高某类专项成长效率，但不直接绑定下一场比赛。

2. **成长由球员曲线决定**
   - 同样的训练，不同球员得到的成长不同。
   - 年龄、潜力、成长速度、当前能力、训练适配度共同影响结果。

3. **玩家决策要有清晰差异**
   - 统一训练适合快速管理。
   - 分组训练适合精细培养。
   - 套餐适合一键规划七天。

4. **数值要慢、有积累感**
   - 单次训练可以只提升 `0.02-0.12`。
   - 前端显示和比赛使用向下取整，能力小数藏在内部。
   - 玩家能感受到长期规划带来的整数突破。

5. **先不做伤病**
   - 训练强度和疲劳风险先设计为 TODO，不在 v1 强实现伤病。

## 2. 玩家体验目标

玩家每个虚拟日最多安排 3 个训练时段：

| 时段 | 定位 |
| --- | --- |
| 上午 | 主要训练时段，适合高强度技术/体能/战术。 |
| 下午 | 第二训练时段，适合专项或分组训练。 |
| 晚上 | 低强度时段，适合恢复、录像、定位球、心理和复盘。 |

玩家最多规划未来 7 天，每天 3 格，共 21 个训练决策点。

玩家可以：

- 一键套用训练套餐。
- 单独修改某一天或某一格。
- 对全队统一训练。
- 分成 2 个小组训练。
- 分成 3 个小组训练：进攻组、防守组、门将组。
- 使用一键按位置分组，再手动拖拽调整球员。

## 3. 核心循环

```
查看赛程与阵容需求
  -> 选择训练套餐或手动规划
  -> 选择统一/分组训练
  -> 每日训练事件结算
  -> 球员获得小数成长
  -> 能力小数累计到整数突破
  -> 球队风格和阵容价值逐步变化
```

训练不消耗资金，也不直接强绑定下一场对手。训练的代价主要来自时间占用和未来可扩展的疲劳/伤病风险。

## 4. 明确非目标

v1 不做：

- 伤病发生和伤病恢复细节。
- 训练设施升级。
- 教练组雇佣和教练能力。
- 训练资源消耗。
- 和下一场对手的强制克制关系。
- 复杂球员情绪反馈。

预留但不实现：

- 高强度训练增加伤病概率。
- 恢复训练降低伤病风险。
- 专项教练提高某类训练效率。
- 训练设施决定单日成长上限。

## 5. 疲劳联动设计

### 5.1 当前项目状态

项目当前没有完整独立的疲劳系统，但已有可复用的体力基础：

| 位置 | 当前实现 |
| --- | --- |
| `players.fitness` | 已存在，0-100，当前被用作赛前初始体力基础。 |
| 赛后回写 | 出场球员 `fitness` 下降，未出场球员 `fitness` 恢复；这更接近“赛后体力恢复状态”，不是长期疲劳。 |
| 比赛引擎 | 赛前 payload 使用 `fitness` 计算初始 `stamina`。 |
| `state_training_load_score` | 已有字段，但当前训练系统未写入。 |
| `TrainingStateProvider` | 已有空实现，预留训练对状态和 stamina 的影响。 |
| 前端疲劳页 | 当前仍是 mock 数据。 |

训练系统应把“体力”和“疲劳”拆开：

| 概念 | 英文字段建议 | 范围 | 定义 |
| --- | --- | --- | --- |
| 体力 | `fitness` | 0-100 | 球员进入比赛时的即时身体可用度，主要影响单场初始 `stamina`。 |
| 疲劳 | `fatigue` | 0-100 | 长期负荷累积，来自连续比赛、高强度训练、恢复不足，会折扣赛前可用体力。 |

关键差异：

- 体力是短周期资源，单场比赛中快速消耗，赛后和休息后恢复较快。
- 疲劳是中周期负荷，通常需要 1-5 天恢复，不应因为一天没比赛就完全清空。
- 疲劳不直接替代体力，而是影响“带着多少体力上场”。
- 门将受疲劳影响较小，但不是完全免疫。

### 5.2 核心公式

赛前进入比赛引擎的初始体力建议由三部分组成：

```
base_match_stamina = fitness + (STA - 10) * 1.2
fatigue_stamina_multiplier = 1 - fatigue * fatigue_impact_by_position
initial_stamina = clamp(base_match_stamina * fatigue_stamina_multiplier, 35, 100)
```

位置疲劳影响系数：

| 位置 | `fatigue_impact_by_position` | 说明 |
| --- | --- | --- |
| `GK` | `0.0012` | 门将跑动少，疲劳对初始体力影响较小。 |
| `DF` | `0.0020` | 后卫中等。 |
| `MF` | `0.0026` | 中场覆盖大，受疲劳影响最大。 |
| `FW` | `0.0023` | 前锋冲刺多，影响高于后卫。 |

示例：

| 球员 | 体力 | 疲劳 | 位置 | 初始体力折扣 |
| --- | --- | --- | --- | --- |
| 门将 | 95 | 50 | GK | `1 - 50*0.0012 = 94%` |
| 后卫 | 95 | 50 | DF | `90%` |
| 中场 | 95 | 50 | MF | `87%` |
| 前锋 | 95 | 50 | FW | `88.5%` |

当一个中场 `fitness=95`、`STA=12`、`fatigue=50`：

```
base_match_stamina = 95 + (12 - 10) * 1.2 = 97.4
multiplier = 1 - 50 * 0.0026 = 0.87
initial_stamina = 84.7
```

玩家可以理解为“体力看起来很满，但长期疲劳让他只能带着约 85 的状态开场”。

### 5.3 疲劳区间与效果

| fatigue | 状态 | 比赛影响 | 训练成长倍率 | 训练安排建议 |
| --- | --- | --- | --- | --- |
| `0-15` | 清爽 | 初始体力几乎无折扣 | `1.05` | 适合专项质量课。 |
| `16-35` | 正常 | 轻微折扣 | `1.00` | 正常训练。 |
| `36-55` | 累积负荷 | 明显折扣 | `0.92` | 控制高强度频次。 |
| `56-75` | 疲劳 | 初始体力大幅折扣 | `0.78` | 优先恢复或低强度。 |
| `76-90` | 重疲劳 | 比赛表现明显受损 | `0.60` | 不建议高强度训练。 |
| `91-100` | 透支 | 强制禁止高强度训练 | `0.40` | 只能恢复/分析。 |

伤病系统 v1 仍不实现，但 `fatigue >= 91` 的强制训练限制建议实现，否则玩家可以用极端训练堆收益。

### 5.4 训练对体力与疲劳的影响

每个训练内容同时配置：

| 字段 | 说明 |
| --- | --- |
| `fitness_delta` | 对即时体力的影响，通常小于疲劳变化。 |
| `fatigue_delta` | 对长期疲劳的影响。 |
| `load_points` | 用于计算近期训练负荷状态分。 |

默认数值：

| 类型 | `fitness_delta` | `fatigue_delta` | `load_points` | 说明 |
| --- | --- | --- | --- | --- |
| 完全休息 | `+14` | `-16` | `-2` | 无训练成长。 |
| 恢复理疗/水疗 | `+10` | `-12` | `-1` | 指定球员或全队恢复。 |
| 活动度/拉伸 | `+6` | `-6` | `0` | 维持身体活性。 |
| 分析/会议 | `+2` | `-2` | `0` | 低负荷认知课。 |
| 定位球/轻技术 | `-2` | `+3` | `1` | 低强度。 |
| 常规技术/传控 | `-4` | `+7` | `2` | 中强度。 |
| 战术模型/对抗 | `-6` | `+10` | `3` | 中高强度。 |
| 高压反抢/重复冲刺 | `-9` | `+14` | `4` | 高强度。 |
| 队内模型赛 | `-12` | `+18` | `5` | 最高负荷。 |

结算：

```
player.fitness = clamp(player.fitness + fitness_delta, 0, 100)
player.fatigue = clamp(player.fatigue + fatigue_delta, 0, 100)
```

恢复训练提高体力并降低疲劳。高强度训练同时降低体力并增加疲劳。

### 5.5 比赛对体力与疲劳的影响

比赛结束后同时回写体力和疲劳。

出场分钟带来的基础变化：

| 出场分钟 | `fitness_delta` | `fatigue_delta` |
| --- | --- | --- |
| `0` | `+8` | `-4` |
| `1-20` | `-4` | `+5` |
| `21-40` | `-7` | `+9` |
| `41-55` | `-10` | `+13` |
| `56-70` | `-14` | `+18` |
| `71+` | `-18` | `+24` |

比赛强度修正：

| 场景 | 疲劳修正 |
| --- | --- |
| 常规比赛 | `x1.00` |
| 杯赛淘汰赛 | `x1.10` |
| 加时 | `x1.20` |
| 点球大战 | `x1.05` |
| 红牌少打一人时出场球员 | `x1.10` |

位置修正：

| 位置 | 比赛疲劳修正 |
| --- | --- |
| `GK` | `x0.45` |
| `DF` | `x0.95` |
| `MF` | `x1.10` |
| `FW` | `x1.00` |

示例：

```
中场出场 70 分钟，杯赛淘汰赛：
fatigue_delta = 18 * 1.10 * 1.10 = 21.78 -> 22
fitness_delta = -14
```

未出场球员当天应恢复体力并小幅降低疲劳，但不能完全清空疲劳。

### 5.6 自然恢复

每天日结时，如果球员当天没有比赛且训练负荷不高，执行自然恢复：

| 条件 | `fitness_delta` | `fatigue_delta` |
| --- | --- | --- |
| 当天无训练无比赛 | `+10` | `-8` |
| 当天只有恢复/分析训练 | 已由训练结算处理 | 额外 `-2` |
| 当天有中高强度训练 | `0` | `0` |
| 当天有比赛 | 由比赛结算处理 | 由比赛结算处理 |

体能 `fitness` 可以 1-2 天恢复到较高水平，疲劳 `fatigue` 应该需要更长时间恢复，这正是二者分开的价值。

### 5.7 疲劳对训练成长的影响

成长公式增加一项：

```
gain =
  base_gain
  * attribute_weight
  * age_factor
  * growth_speed
  * potential_factor
  * position_fit
  * group_fit
  * fatigue_factor
  * diminishing_factor
  * random_factor
```

`fatigue_factor` 由疲劳区间表提供。若球员疲劳过高，继续训练不但低效，还会积累更多疲劳。

### 5.8 训练负荷状态分

`fitness` 表示当前体力，`fatigue` 表示长期负荷，`state_training_load_score` 表示近期训练负荷对状态的短期影响。三者都应该接入。

建议训练结算后，按最近 3 天训练强度计算训练负荷分：

| 最近 3 天训练负荷 | `state_training_load_score` |
| --- | --- |
| 恢复/低负荷 | `+1` |
| 正常负荷 | `0` |
| 偏高负荷 | `-1` |
| 高负荷 | `-2` |
| 极高负荷 | `-3` |

负荷计算示例：

| 时段强度 | 负荷点 |
| --- | --- |
| 恢复 | `-1` |
| 低强度 | `1` |
| 中强度 | `2` |
| 高强度 | `3` |

```
3_day_load = 最近 3 天所有训练负荷点之和
```

映射：

| `3_day_load` | 状态 |
| --- | --- |
| `<= 6` | 恢复/低负荷 |
| `7-12` | 正常负荷 |
| `13-18` | 偏高负荷 |
| `19-24` | 高负荷 |
| `25+` | 极高负荷 |

### 5.9 比赛联动

比赛链路保持现有方向：

```
训练安排
  -> 改变 fitness 和 fatigue
  -> 写入 state_training_load_score
  -> PlayerStateService 聚合状态
  -> MatchEngineClient 按 fitness、fatigue、STA、位置生成初始 stamina
  -> 比赛后根据出场时间回写 fitness 和 fatigue
  -> 次日训练需要考虑恢复
```

这样训练系统会自然形成约束：

- 高强度训练带来更高成长，但降低 `fitness` 并增加 `fatigue`。
- `fitness` 决定当前可用体力，`fatigue` 决定能带着多少折扣上场。
- 高 `fatigue` 会降低训练收益，也降低比赛初始 `stamina`。
- 恢复训练没有明显属性成长，但能修复训练和比赛后的体力/疲劳问题。
- 密集赛程中，玩家必须在成长和比赛表现之间取舍。

### 5.10 UI 表达

前端需要同时展示“体力”和“疲劳”：

| UI 指标 | 来源 | 展示建议 |
| --- | --- | --- |
| 体力 | `fitness` | 绿色/黄色/红色进度条，越高越好。 |
| 疲劳 | `fatigue` | 黄色/红色负担条，越低越好。 |
| 预计开场体力 | `initial_stamina` 预估 | 在赛前和训练页显示。 |

页面展示：

- 当前体力。
- 当前疲劳。
- 疲劳造成的开场体力折扣，例如“预计以 88% 体力开场”。
- 最近 7 天训练负荷曲线。
- 最近比赛出场造成的体能下降。
- 推荐训练：高疲劳时推荐恢复，低疲劳时推荐专项。

伤病风险暂时不展示，或展示为“后续开放”。避免 UI 给出当前系统无法兑现的承诺。

### 5.11 数据字段建议

修改 `players`：

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `fitness` | int | `100` | 保留现有字段，解释为当前体力。 |
| `fatigue` | int | `0` | 新增，长期疲劳，0-100。 |
| `fatigue_updated_at` | datetime nullable | null | 最近疲劳结算时间。 |

新增训练结果字段见后续 `training_results`。比赛结算时建议在 `MatchResult.player_stats` 中写入：

```json
{
  "fitness_before": 92,
  "fitness_after": 78,
  "fatigue_before": 36,
  "fatigue_after": 58,
  "initial_stamina": 81.4
}
```

## 6. 训练单位

### 6.1 训练时段

一个训练时段是最小结算单位。

字段建议：

| 字段 | 说明 |
| --- | --- |
| `season_day` | 赛季第几天。 |
| `slot` | `morning` / `afternoon` / `evening`。 |
| `mode` | `team` / `groups`。 |
| `training_item_id` | 统一训练时使用。 |
| `groups` | 分组训练时使用，最多 3 组。 |
| `intensity` | `light` / `normal` / `hard`，v1 可以固定由训练内容决定。 |
| `status` | `planned` / `locked` / `completed` / `missed`。 |

### 6.2 训练锁定

当前时段开始后不可修改。

建议锁定规则：

- 当前时段和已过去时段不可改。
- 未来时段可改。
- 当前赛季最多向后规划 7 天。
- 赛季结束后的训练格不可规划。

### 6.3 默认训练

如果玩家没有安排训练，系统使用默认计划：

| 场景 | 默认行为 |
| --- | --- |
| 普通日 | 均衡训练：传球/基础防守/拉伸。 |
| 连续两天无计划 | 套用“均衡发展”。 |
| AI 球队 | 每天由 AI 生成计划。 |

## 7. 分组训练

### 7.1 分组模式

支持三种模式：

| 模式 | 说明 |
| --- | --- |
| 全队统一 | 所有可训练球员执行同一训练。 |
| 两组训练 | 玩家自定义两组，例如主力/替补、进攻/防守。 |
| 三组训练 | 进攻组、防守组、门将组。 |

### 7.2 一键分组规则

按位置自动分组：

| 组名 | 自动包含 |
| --- | --- |
| 进攻组 | `FW`，以及玩家手动加入的攻击型 `MF`。 |
| 防守组 | `DF`、大部分 `MF`。 |
| 门将组 | `GK`。 |

八人制项目的位置目前只有 `FW/MF/DF/GK` 四大类，因此一键分组应该简单直接。更细的位置标签可以后续从战术站位或个人指令推断。

### 7.3 手动拖拽

玩家可以把球员拖到任意训练组。

限制：

- 每名球员同一时段只能在一个组。
- 空组不允许保存。
- `INJURED` 和 `SUSPENDED` 球员默认不参与训练，后续伤病系统完成后可进入康复训练组。
- 门将可以参加全队训练，但门将参加非门将专项时成长效率降低。

### 7.4 分组收益

分组训练的意义不是总收益更高，而是收益更精准。

建议：

| 模式 | 效率 | 特点 |
| --- | --- | --- |
| 全队统一 | 100% 基础效率 | 操作简单，适合大众玩家。 |
| 两组训练 | 105% 适配效率 | 轻度精细化。 |
| 三组训练 | 110% 适配效率 | 最高精度，但操作成本更高。 |

效率只作用于“训练内容与球员位置适配”的部分，避免三组训练无脑最强。

## 8. 训练内容分类

训练分为 7 大类。分类不直接等于 UI 标签，UI 可以合并展示；分类的主要作用是让数值配置、AI 选课和历史统计更清晰。

| 类别 | 核心作用 |
| --- | --- |
| 终结训练 | 射门、远射、点球、临门镇定。 |
| 传控训练 | 传球、视野、控球、传中、球商。 |
| 个人技术 | 盘带、接应、摆脱、第一脚触球。 |
| 防守训练 | 站位、抢断、争顶、协防、防守判断。 |
| 身体训练 | 速度、体能、力量、爆发、平衡，但年龄衰减更明显。 |
| 门将训练 | 扑救、反应、站位、出击、门将出球。 |
| 恢复训练 | 恢复体力、降低疲劳；不产生或少量产生能力成长。 |
| 分析训练 | 录像、复盘、心理、点球准备，偏 `dec/com/pk/fk/vis`。 |

## 9. 训练内容池

训练名称应尽量像真实训练课表，而不是泛泛的“某某特训”。UI 上可以展示短名，详情中展示训练目的、适配人群和成长属性。

### 9.1 终结训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `box_finish_one_touch` | 禁区一脚终结 | 进攻组 | `sho` | `com`, `acc` | normal |
| `box_finish_under_pressure` | 对抗下射门选择 | 进攻组 | `sho`, `com` | `bal`, `dec` | hard |
| `cutback_finish` | 倒三角接应射门 | 进攻组/中场 | `sho` | `pas`, `dec` | normal |
| `near_post_finish` | 前点抢射 | 进攻组 | `sho`, `acc` | `com` | normal |
| `far_post_arrival` | 后点包抄 | 进攻组/中场 | `sho`, `dec` | `hea`, `acc` | normal |
| `weak_foot_finish` | 非惯用脚终结 | 进攻组 | `sho` | `com`, `bal` | normal |
| `long_shot_window` | 禁区弧顶远射窗口 | 中场/进攻组 | `fin` | `sho`, `dec` | normal |
| `volley_second_ball` | 二点球凌空处理 | 进攻组/防守组 | `sho` | `hea`, `bal` | hard |
| `penalty_routine` | 点球助跑与角度 | 指定球员/进攻组 | `pk` | `com`, `sho` | light |
| `penalty_pressure` | 压力点球模拟 | 指定球员/全队 | `pk`, `com` | `dec` | normal |

### 9.2 传控训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `rondo_4v2` | 4v2 小圈保球 | 全队/中场 | `pas`, `con` | `dec`, `vis` | normal |
| `third_man_combination` | 第三人接应配合 | 中场/进攻组 | `pas`, `vis` | `dec`, `con` | normal |
| `wall_pass_timing` | 撞墙配合时机 | 进攻组/中场 | `pas` | `acc`, `dec` | normal |
| `switch_play` | 弱侧转移 | 中场/防守组 | `pas`, `vis` | `cro`, `dec` | normal |
| `line_breaking_pass` | 穿线直塞 | 中场 | `vis`, `pas` | `dec`, `com` | normal |
| `first_touch_escape` | 第一脚卸压 | 全队/中场 | `con` | `dri`, `bal` | normal |
| `back_to_goal_link` | 背身接应做球 | 进攻组 | `con`, `pas` | `str`, `dec` | hard |
| `cross_low_driven` | 低平传中 | 边路球员 | `cro` | `pas`, `dec` | normal |
| `cross_early` | 提前量传中 | 边路球员 | `cro`, `vis` | `pas` | normal |
| `build_out_under_press` | 后场出球抗压 | 防守组/门将 | `pas`, `con` | `dec`, `com` | hard |

### 9.3 个人技术

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `dribble_cone_tight` | 密集标志盘带 | 进攻组/中场 | `dri` | `con`, `bal` | normal |
| `one_v_one_wing` | 边路 1v1 突破 | 进攻组 | `dri`, `acc` | `spd`, `bal` | hard |
| `receive_on_half_turn` | 半转身接球 | 中场/进攻组 | `con`, `dec` | `dri`, `vis` | normal |
| `shield_and_roll` | 护球转身摆脱 | 中场/进攻组 | `con`, `str` | `bal`, `dri` | hard |
| `carry_into_space` | 带球推进空间识别 | 中场/进攻组 | `dri`, `dec` | `spd`, `con` | normal |
| `touchline_escape` | 边线夹击脱困 | 边路球员 | `dri`, `con` | `bal`, `pas` | hard |
| `receiving_scanning` | 接球前观察 | 全队/中场 | `dec`, `vis` | `con`, `pas` | light |

### 9.4 防守训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `body_shape_defense` | 防守身体朝向 | 防守组 | `defe` | `dec`, `bal` | normal |
| `delay_and_channel` | 延缓与逼向边线 | 防守组 | `defe`, `dec` | `spd`, `tkl` | normal |
| `standing_tackle_timing` | 正面抢断时机 | 防守组 | `tkl` | `defe`, `bal` | hard |
| `cover_shadow_press` | 遮挡传球线路逼抢 | 全队/防守组 | `dec`, `defe` | `sta`, `acc` | hard |
| `recovery_run` | 回追路线 | 防守组/中场 | `spd`, `defe` | `sta`, `dec` | hard |
| `aerial_duel_defense` | 防守争顶 | 防守组 | `hea`, `str` | `defe`, `bal` | normal |
| `box_marking` | 禁区盯人与保护 | 防守组/门将 | `defe`, `dec` | `hea`, `pos` | normal |
| `counterpress_after_loss` | 丢球后 5 秒反抢 | 全队 | `tkl`, `sta` | `dec`, `acc` | hard |

### 9.5 定位球训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `corner_near_post` | 角球前点跑位 | 进攻组 | `fk`, `hea` | `dec`, `acc` | light |
| `corner_far_post` | 角球后点包抄 | 进攻组/防守组 | `hea`, `dec` | `str`, `fk` | light |
| `free_kick_direct` | 直接任意球脚法 | 指定球员 | `fk` | `com`, `sho` | light |
| `free_kick_routine` | 间接任意球配合 | 进攻组 | `fk`, `dec` | `pas`, `hea` | light |
| `throw_in_pattern` | 边线球接应套路 | 全队 | `dec`, `pas` | `con` | light |
| `set_piece_marking` | 定位球区域盯防 | 防守组/门将 | `defe`, `pos` | `hea`, `dec` | light |
| `penalty_keeper_read` | 门将扑点预判 | 门将组 | `ref`, `com` | `sav`, `dec` | light |

### 9.6 身体训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `accel_5m` | 5 米启动 | 进攻组/防守组 | `acc` | `spd`, `bal` | hard |
| `repeat_sprint` | 重复冲刺能力 | 全队 | `sta`, `spd` | `acc` | hard |
| `max_velocity` | 最高速度跑 | 进攻组/防守组 | `spd` | `acc` | hard |
| `change_direction` | 变向制动 | 全队 | `bal`, `acc` | `dri`, `tkl` | hard |
| `upper_body_duel` | 上肢对抗 | 防守组/进攻组 | `str` | `bal`, `hea` | hard |
| `core_stability` | 核心稳定 | 全队 | `bal` | `str`, `con` | normal |
| `aerobic_blocks` | 分段有氧跑 | 全队 | `sta` | `bal` | hard |
| `jump_power` | 起跳与落地 | 进攻组/防守组 | `hea`, `str` | `bal` | normal |

### 9.7 战术训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `build_up_2_3` | 2-3 出球结构 | 全队/防守组 | `dec`, `pas` | `con`, `vis` | normal |
| `wide_overload` | 边路局部人数优势 | 进攻组/中场 | `dec`, `pas` | `cro`, `dri` | normal |
| `central_compactness` | 中路紧凑防守 | 防守组/中场 | `defe`, `dec` | `tkl`, `sta` | normal |
| `press_trigger` | 逼抢触发点 | 全队 | `dec`, `sta` | `tkl`, `acc` | hard |
| `rest_defense` | 进攻时防反站位 | 防守组/中场 | `defe`, `dec` | `spd`, `pos` | normal |
| `transition_attack` | 抢回球后的第一传 | 全队 | `dec`, `pas` | `spd`, `vis` | normal |
| `transition_defense` | 失球权后的回收 | 全队 | `dec`, `sta` | `defe`, `spd` | hard |
| `game_model_8v8` | 8v8 队内模型赛 | 全队 | `dec` | `pas`, `defe`, `sta` | hard |

### 9.8 门将训练

| ID | 名称 | 推荐组 | 主属性 | 副属性 | 强度 |
| --- | --- | --- | --- | --- | --- |
| `gk_set_position` | 准备姿势与重心 | 门将组 | `pos`, `ref` | `bal`, `com` | normal |
| `gk_low_save` | 低平球扑救 | 门将组 | `sav` | `ref`, `pos` | normal |
| `gk_close_range` | 近距离封堵 | 门将组 | `ref`, `sav` | `com`, `rus` | hard |
| `gk_cross_claim` | 传中球摘取 | 门将组 | `rus`, `pos` | `com`, `hea` | normal |
| `gk_one_v_one` | 单刀出击 | 门将组 | `rus`, `com` | `ref`, `dec` | hard |
| `gk_distribution_short` | 短传出球 | 门将组 | `pas`, `com` | `dec`, `con` | light |
| `gk_distribution_long` | 长距离开球 | 门将组 | `pas` | `str`, `dec` | normal |
| `gk_penalty_read` | 点球方向读取 | 门将组 | `ref`, `com` | `sav`, `dec` | light |

### 9.9 恢复与分析

| ID | 名称 | 推荐组 | 主要效果 | 成长 |
| --- | --- | --- | --- |
| `full_rest` | 完全休息 | 全队 | 大幅恢复体力并降低疲劳 | 无 |
| `mobility_session` | 活动度与拉伸 | 全队 | 小幅恢复体力并降低疲劳 | 极低 `bal` 成长 |
| `recovery_bike` | 低强度单车恢复 | 全队/指定球员 | 中幅恢复体力，轻度降低疲劳 | 极低 `sta` 成长 |
| `hydro_recovery` | 水疗恢复 | 全队/指定球员 | 中幅恢复体力并降低疲劳 | 无 |
| `individual_treatment` | 个人理疗 | 指定球员 | 高幅恢复体力并降低疲劳 | 无 |
| `match_review_unit` | 分组录像复盘 | 分组 | 提升认知类训练 | 少量 `dec/vis` |
| `opponent_clip_study` | 对手片段研究 | 全队/分组 | 后续接赛前策略 | 少量 `dec` |
| `role_meeting` | 位置职责会议 | 分组 | 提升战术理解 | 少量 `dec/com` |
| `captain_meeting` | 队长沟通会 | 全队 | 后续接士气 | 少量 `com` |

## 10. 训练套餐

套餐是对 7 天 × 3 时段的快速填充。玩家可以套用后再微调。

### 10.1 套餐列表

| 套餐 | 定位 |
| --- | --- |
| 标准微周期 | 新手默认，攻防、传控、身体和恢复都有覆盖。 |
| 禁区终结周 | 提升 `sho/com/fin/acc`，适合进球效率低的球队。 |
| 控球出球周 | 提升 `pas/con/vis/dec`，适合中后场控球和出球。 |
| 高压反抢周 | 提升 `sta/tkl/defe/dec/acc`，强度高。 |
| 低位防守周 | 提升 `defe/hea/pos/dec/tkl`，适合保守打法。 |
| 边路推进周 | 提升 `cro/dri/spd/acc/pas`。 |
| 定位球攻防周 | 围绕 `fk/hea/defe/pos/dec`。 |
| 点球与门将扑点周 | 围绕 `pk/com/sho/ref/sav`。 |
| 青年球员技术周 | 多个低中强度专项轮转，适合 18-23 岁高潜球员。 |
| 密集赛程恢复周 | 多恢复和低强度认知课，适合连续比赛后调整。 |

### 10.2 示例：点球与门将扑点周

| 日程 | 上午 | 下午 | 晚上 |
| --- | --- | --- | --- |
| Day 1 | 禁区一脚终结 | 点球助跑与角度 | 分组录像复盘 |
| Day 2 | 对抗下射门选择 | 压力点球模拟 | 活动度与拉伸 |
| Day 3 | 直接任意球脚法 | 点球助跑与角度 | 位置职责会议 |
| Day 4 | 完全休息 | 压力点球模拟 | 对手片段研究 |
| Day 5 | 倒三角接应射门 | 对抗下射门选择 | 活动度与拉伸 |
| Day 6 | 压力点球模拟 | 门将点球方向读取 | 完全休息 |
| Day 7 | 完全休息 | 分组录像复盘 | 完全休息 |

说明：

- 点球训练不应只练 `pk`。
- `com` 镇定和 `sho` 射门也应参与成长。
- 门将可通过门将组训练 `sav/ref/com`，形成攻守两侧收益。

## 11. 成长数值模型

### 11.1 小数能力

当前 `players` 能力字段是整数，建议升级为内部小数。

显示与比赛规则：

```
内部能力：12.94
前端展示：12
比赛使用：12

内部能力：13.00
前端展示：13
比赛使用：13
```

建议 DB 类型：

```
DECIMAL(5, 2)
```

原因：

- 能力范围小，`20.00` 足够。
- 小数训练成长可稳定累计。
- 避免浮点误差。

### 11.2 潜力上限

每名球员生成时有隐藏潜力上限：

| 字段 | 说明 |
| --- | --- |
| `potential_max` | 总体潜力上限，当前已有，范围建议 20-100。 |
| `attribute_caps` | 各属性隐藏上限，建议新增 JSON。 |

只用一个 `potential_max` 不够精细。一个球员可能总潜力高，但并不代表所有属性都能练到 20。

建议新增：

```json
{
  "sho": 17.4,
  "pas": 14.8,
  "dri": 16.2,
  "spd": 18.1,
  "sta": 15.5,
  "pk": 13.2
}
```

训练结算时：

```
新能力 = min(当前能力 + 成长值, 该属性上限, 20.00)
```

如果没有 `attribute_caps`，则用 `potential_max` 推导临时上限。

### 11.3 成长曲线

每名球员生成时拥有一条隐藏成长曲线，决定不同年龄段训练收益。

建议新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `growth_peak_age` | int | 巅峰年龄，例如 27-32。 |
| `growth_curve_type` | enum/string | 成长类型。 |
| `growth_speed` | DECIMAL | 成长速度系数。 |
| `growth_stability` | DECIMAL | 成长稳定性，影响随机波动。 |
| `late_bloom_factor` | DECIMAL | 晚熟系数。 |

成长曲线类型：

| 类型 | 说明 |
| --- | --- |
| `early_bloomer` 早熟 | 18-23 成长快，25 后明显放缓。 |
| `steady` 平稳 | 18-29 稳定成长，峰值普通。 |
| `late_bloomer` 晚熟 | 早期慢，26-32 成长更好。 |
| `explosive` 爆发型 | 成长高但波动大，可能阶段性突破。 |
| `plateau` 平台型 | 早期达到可用能力，后续成长慢。 |

### 11.4 年龄成长倍率

建议基础公式：

```
age_factor = exp(-((age - growth_peak_age) ^ 2) / (2 * curve_width ^ 2))
```

为了便于调参，实际实现可以不用直接暴露复杂公式，而是生成查表结果。

示例倍率：

| 年龄段 | 早熟 | 平稳 | 晚熟 |
| --- | --- | --- | --- |
| 16-18 | 1.40 | 1.10 | 0.80 |
| 19-21 | 1.55 | 1.30 | 1.00 |
| 22-24 | 1.25 | 1.35 | 1.15 |
| 25-27 | 0.70 | 1.00 | 1.10 |
| 28-30 | 0.20 | 0.35 | 0.55 |
| 31-32 | 0.03 | 0.08 | 0.20 |
| 33+ | 0.00 | 0.00 | 0.03 |

这能支持：

- 有些球员 29 岁巅峰。
- 有些球员 32 岁才迎来巅峰。
- 有些球员年轻时涨得很快。
- 有些球员整体发展平稳。

实际结算还会额外叠加一个 `development_stage_factor`，用于把训练收益更集中地给一线队培养期球员：

| 年龄段 | 阶段倍率 |
| --- | --- |
| 16-18 | 0.85 |
| 19-21 | 0.80 |
| 22-24 | 0.95 |
| 25-27 | 0.85 |
| 28 | 0.55 |
| 29 | 0.35 |
| 30 | 0.25 |
| 31-32 | 0.12 |
| 33+ | 0.03 |

高潜年轻球员有额外修正：

- `age <= 23` 且 `potential_max >= 70`：阶段倍率 `* 1.10`。
- `age <= 21` 且 `potential_max >= 80`：阶段倍率再 `* 1.08`。
- 晚熟球员且 `growth_peak_age >= 30`：28-30 岁阶段倍率最低按 `0.75`，31-32 岁最低按 `0.45`，避免误伤 32 岁才迎来巅峰的球员。

### 11.5 单次训练成长公式

建议单项属性成长：

```
gain =
  base_gain
  * attribute_weight
  * age_factor
  * growth_speed
  * development_stage_factor
  * potential_factor
  * position_fit
  * group_fit
  * diminishing_factor
  * random_factor
```

各项解释：

| 系数 | 建议范围 | 说明 |
| --- | --- | --- |
| `base_gain` | 0.04-0.10 | 训练内容基础收益。 |
| `attribute_weight` | 0.25-1.00 | 主属性高，副属性低。 |
| `age_factor` | 0.00-1.55 | 成长曲线决定。 |
| `growth_speed` | 0.70-1.40 | 球员隐藏成长速度。 |
| `development_stage_factor` | 0.03-1.60 | 年龄阶段与高潜年轻修正。 |
| `potential_factor` | 0.00-1.08 | 越接近上限越低；距离上限较远时略有加成。 |
| `position_fit` | 0.40-1.15 | 训练与位置匹配度。 |
| `group_fit` | 0.90-1.10 | 分组精度。 |
| `diminishing_factor` | 0.60-1.00 | 连续重复训练递减。 |
| `random_factor` | 0.85-1.15 | 小范围随机。 |

### 11.6 潜力接近衰减

球员越接近属性上限，成长越慢。

```
remaining = attribute_cap - current_attribute
if remaining >= 6:
  potential_factor = 1.08
elif remaining >= 4:
  potential_factor = 1.00
else:
  potential_factor = clamp(remaining / 4.0, 0.04, 1.00)
```

当只剩 `0.2` 上限空间时：

```
potential_factor = 0.04
```

训练仍可能有极小收益，但很难继续突破。达到上限后收益为 0。

### 11.7 重复训练递减

避免玩家无脑连续 21 格点同一个训练。

```
最近 7 天同一训练出现次数：
1-2 次：100%
3-4 次：85%
5-6 次：70%
7+ 次：60%
```

恢复训练、休息不参与递减。

### 11.8 示例：压力点球模拟

球员 A：

- 年龄 22。
- 成长类型：平稳。
- `growth_speed = 1.08`。
- 当前 `pk = 11.91`。
- `pk_cap = 16.40`。
- 压力点球模拟 `base_gain = 0.08`。
- `pk` 是主属性，`attribute_weight = 1.00`。
- 位置适配为前锋，`position_fit = 1.10`。
- 三组训练适配，`group_fit = 1.05`。
- 未重复递减，`diminishing_factor = 1.00`。
- 随机系数 `random_factor = 0.97`。

```
gain = 0.08 * 1.00 * 1.20 * 1.08 * 1.00 * 1.10 * 1.05 * 1.00 * 0.97
gain = 0.1075
```

结算：

```
pk 11.91 -> 12.02
```

展示与比赛使用从 11 变成 12。玩家会看到一次整数突破。

球员 B：

- 年龄 31。
- 成长类型：早熟。
- 当前 `pk = 14.85`。
- `pk_cap = 15.10`。

同样训练可能只得到：

```
gain = 0.01
pk 14.85 -> 14.86
```

玩家会感到老将仍能微调专项，但不适合长期培养。

## 12. 属性成长权重

每个训练内容定义属性权重。

示例：

```json
{
  "id": "penalty_pressure",
  "name": "压力点球模拟",
  "base_gain": 0.08,
  "intensity": "normal",
  "fitness_delta": -4,
  "fatigue_delta": 7,
  "load_points": 2,
  "attributes": {
    "pk": 1.0,
    "com": 0.45,
    "sho": 0.25
  },
  "position_fit": {
    "FW": 1.10,
    "MF": 1.00,
    "DF": 0.85,
    "GK": 0.60
  }
}
```

门将扑点可以是另一个训练：

```json
{
  "id": "gk_penalty_read",
  "name": "点球方向读取",
  "base_gain": 0.07,
  "intensity": "light",
  "fitness_delta": -2,
  "fatigue_delta": 3,
  "load_points": 1,
  "attributes": {
    "sav": 0.70,
    "ref": 0.60,
    "com": 0.50,
    "dec": 0.30
  },
  "position_fit": {
    "GK": 1.15,
    "DF": 0.30,
    "MF": 0.30,
    "FW": 0.30
  }
}
```

## 13. 训练结果展示

训练结算后，玩家不应该看到大量小数流水。建议只展示高价值反馈。

### 13.1 每日总结

每日训练完成后展示：

- 今日完成训练数。
- 全队成长总量。
- 发生整数突破的球员。
- 成长最快的 3 名球员。
- 低效率训练提示。

示例：

| 球员 | 变化 |
| --- | --- |
| 刘洋 | 点球 `11 -> 12` |
| 陈浩 | 射门进度 `13.72 -> 13.81` |
| 王强 | 扑救进度 `14.40 -> 14.47` |

### 13.2 球员详情

球员详情页建议展示：

- 当前整数能力。
- 小数进度条，例如 `12 + 62%`。
- 最近 7 天训练收益。
- 推荐训练方向。

不直接显示潜力上限的精确值，只显示大致提示：

| 状态 | 文案 |
| --- | --- |
| 上限空间大 | 仍有明显成长空间。 |
| 接近上限 | 该能力提升开始变慢。 |
| 已到上限 | 该能力已接近个人极限。 |

## 14. AI 训练规划

AI 球队每天自动生成训练计划。AI 不需要像玩家一样做复杂拖拽，但要有策略差异和随机性。

### 14.1 AI 决策输入

AI 训练规划参考：

| 输入 | 说明 |
| --- | --- |
| 球队平均年龄 | 年轻队更倾向高成长专项。 |
| 球队位置短板 | 某位置 OVR 或关键属性偏低时倾向补强。 |
| 最近战绩 | 连败时提高防守/基础训练权重。 |
| 近期赛程密度 | 密集赛程增加恢复训练。 |
| 球队风格 | 进攻型、防守型、均衡型。 |
| 随机扰动 | 避免全联盟训练完全一致。 |

### 14.2 AI 球队风格

每支 AI 队可生成一个隐藏训练偏好：

| 风格 | 倾向 |
| --- | --- |
| `attacking` | 射门、盘带、进攻套路。 |
| `defensive` | 防守站位、抢断、头球、定位球防守。 |
| `physical` | 体能、速度、力量。 |
| `technical` | 传球、控球、视野。 |
| `balanced` | 均衡训练。 |
| `youth_focus` | 给 18-23 岁高潜球员更多专项。 |

### 14.3 AI 每日生成规则

建议：

```
每日先判断是否需要恢复
  -> 根据球队短板选主训练
  -> 根据风格选副训练
  -> 晚上通常安排低强度训练或恢复
  -> 10%-20% 概率插入随机专项
```

训练概率示例：

| 条件 | 行为 |
| --- | --- |
| 平均 `fitness < 70` 或平均 `fatigue > 55` | 至少 1 个恢复训练。 |
| 未来 2 天有比赛 | 晚上更偏恢复/录像。 |
| 进球少 | 增加射门、进攻套路。 |
| 失球多 | 增加防守站位、抢断、定位球防守。 |
| 年轻高潜多 | 增加技术专项。 |
| 老将多 | 降低身体训练频率。 |

### 14.4 AI 分组

AI 默认使用三组训练：

- `FW` 进入进攻组。
- `DF` 进入防守组。
- `GK` 进入门将组。
- `MF` 根据队伍短板和随机权重进入进攻组或防守组。

AI 不需要逐人复杂优化，避免计算成本过高。

## 15. 数据模型建议

### 15.1 修改 `players`

建议把 23 项能力从整数升级为 `DECIMAL(5,2)`。

现有字段：

```
sho, pas, dri, spd, str, sta, acc, hea, bal,
defe, tkl, vis, cro, con, fin,
com, sav, ref, pos, rus, dec, fk, pk
```

新增字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `fitness` | int | 当前体力，保留现有字段，范围 0-100。 |
| `fatigue` | int | 长期疲劳，新增字段，范围 0-100。 |
| `fatigue_updated_at` | datetime nullable | 最近疲劳结算时间。 |
| `attribute_caps` | JSON nullable | 各属性隐藏上限。 |
| `growth_peak_age` | int nullable | 巅峰年龄。 |
| `growth_curve_type` | string nullable | 成长曲线类型。 |
| `growth_speed` | DECIMAL(5,2) | 成长速度系数。 |
| `growth_stability` | DECIMAL(5,2) | 成长稳定性。 |
| `training_focus_history` | JSON nullable | 最近训练摘要，或用独立表替代。 |

### 15.2 新表：`training_items`

训练内容配置表，也可以先用代码/JSON 配置。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | string | 训练内容 ID。 |
| `name` | string | 展示名。 |
| `category` | string | 技术/战术/身体/恢复/分析。 |
| `base_gain` | DECIMAL | 基础成长。 |
| `intensity` | string | 强度。 |
| `fitness_delta` | int | 对当前体力的影响。 |
| `fatigue_delta` | int | 对长期疲劳的影响。 |
| `load_points` | int | 训练负荷点，用于 3 日负荷状态分。 |
| `attribute_weights` | JSON | 属性权重。 |
| `position_fit` | JSON | 位置适配。 |
| `is_recovery` | bool | 是否恢复训练。 |
| `enabled` | bool | 是否启用。 |

### 15.3 新表：`team_training_plans`

保存未来 7 天计划。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | uuid/string | 主键。 |
| `team_id` | FK | 球队。 |
| `season_id` | FK | 赛季。 |
| `season_day` | int | 赛季第几天。 |
| `slot` | enum | 上午/下午/晚上。 |
| `mode` | enum | 全队/分组。 |
| `training_item_id` | string nullable | 全队训练内容。 |
| `groups` | JSON nullable | 分组训练配置。 |
| `status` | enum | planned/locked/completed/missed。 |
| `created_by` | enum | player/ai/default。 |

`groups` 示例：

```json
[
  {
    "group_id": "attack",
    "name": "进攻组",
    "training_item_id": "box_finish_one_touch",
    "player_ids": ["p1", "p2", "p3"]
  },
  {
    "group_id": "defense",
    "name": "防守组",
    "training_item_id": "defense_shape",
    "player_ids": ["p4", "p5", "p6"]
  },
  {
    "group_id": "gk",
    "name": "门将组",
    "training_item_id": "gk_low_save",
    "player_ids": ["p7"]
  }
]
```

### 15.4 新表：`training_results`

记录训练结算。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | uuid/string | 主键。 |
| `plan_id` | FK | 对应训练计划。 |
| `team_id` | FK | 球队。 |
| `player_id` | FK | 球员。 |
| `training_item_id` | string | 训练内容。 |
| `attribute_gains` | JSON | 各属性小数成长。 |
| `before_attributes` | JSON | 训练前快照。 |
| `after_attributes` | JSON | 训练后快照。 |
| `fitness_before` | int | 训练前体力。 |
| `fitness_after` | int | 训练后体力。 |
| `fatigue_before` | int | 训练前疲劳。 |
| `fatigue_after` | int | 训练后疲劳。 |
| `load_points` | int | 本次训练负荷点。 |
| `breakthroughs` | JSON | 整数突破记录。 |
| `efficiency` | DECIMAL | 本次训练效率。 |
| `created_at` | datetime | 结算时间。 |

### 15.5 新表：`team_training_ai_profiles`

可选。保存 AI 球队训练偏好。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `team_id` | FK | 球队。 |
| `style` | string | 训练风格。 |
| `risk_tolerance` | DECIMAL | 强度倾向，v1 可不用伤病。 |
| `youth_focus` | DECIMAL | 年轻球员培养倾向。 |
| `random_seed` | int | 稳定随机。 |

## 16. 后端服务建议

### 16.1 `TrainingService`

职责：

- 获取训练内容配置。
- 创建/更新未来 7 天计划。
- 校验训练时段是否可改。
- 结算训练计划。
- 写入 `training_results`。
- 更新球员小数能力。
- 更新球员 `fitness` 和 `fatigue`。
- 刷新 `state_training_load_score`。

核心方法：

```python
list_training_items()
get_team_training_plan(team_id, start_day, days=7)
save_training_plan(team_id, payload)
auto_group_players(team_id, mode)
apply_template(team_id, template_id, start_day)
complete_training_slot(team_id, season_day, slot)
calculate_player_training_gain(player, training_item, context)
apply_training_fatigue(player, training_item)
recalculate_training_load_score(player_id, days=3)
```

### 16.2 `TrainingGrowthService`

职责：

- 生成球员成长曲线。
- 生成属性上限。
- 计算年龄成长倍率。
- 计算单次训练收益。

可从 `PlayerGenerator` 调用，用于新球员生成。

### 16.3 `AITrainingPlanner`

职责：

- 为 AI 球队每天生成训练计划。
- 为未规划的人类玩家球队填默认计划。
- 根据球队风格、短板和赛程做轻量决策。

### 16.4 `PlayerFatigueService`

职责：

- 统一计算训练对 `fitness/fatigue` 的影响。
- 统一计算比赛后 `fitness/fatigue` 回写。
- 根据 `fitness`、`fatigue`、`STA`、位置计算赛前 `initial_stamina`。
- 为前端提供疲劳等级、训练建议和预计开场体力。

核心方法：

```python
apply_training_load(player, training_item, context)
apply_match_load(player, minutes, fixture_type, resolution)
apply_daily_recovery(player, day_context)
calculate_initial_stamina(player)
get_fatigue_band(player)
get_training_recommendation(player)
```

实现原则：

- `TrainingService` 调用它，不直接写死疲劳公式。
- `MatchSimulator._update_player_match_state` 调用它，不继续只扣 `fitness`。
- `PlayerStateService` 读取它的结果聚合状态分。

## 17. API 建议

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/api/v1/training/items` | 获取训练内容。 |
| `GET` | `/api/v1/teams/{team_id}/training/plan?days=7` | 获取未来训练计划。 |
| `PUT` | `/api/v1/teams/{team_id}/training/plan` | 保存训练计划。 |
| `POST` | `/api/v1/teams/{team_id}/training/templates/{template_id}/apply` | 套用训练套餐。 |
| `POST` | `/api/v1/teams/{team_id}/training/auto-group` | 一键按位置分组。 |
| `GET` | `/api/v1/teams/{team_id}/training/results` | 获取训练结果。 |
| `GET` | `/api/v1/players/{player_id}/training/progress` | 获取球员训练成长进度。 |
| `GET` | `/api/v1/players/{player_id}/fatigue` | 获取球员体力、疲劳、预计开场体力和负荷建议。 |

## 18. 前端页面改造

### 18.1 周计划页

现有 `/training/weekly` 保留 7×3 矩阵。

需要新增：

- 全队/两组/三组模式切换。
- 训练内容侧栏按类别筛选。
- 套餐应用后可编辑。
- 点击格子后可配置分组。
- 一键按位置分组。
- 球员拖拽进组。
- 保存计划按钮。
- 当前时段锁定态。

### 18.2 疲劳页

疲劳页需要替换 mock，并同时展示体力与疲劳：

- 使用真实 `fitness`。
- 使用新增 `fatigue`。
- 展示预计开场体力 `initial_stamina_preview`。
- 展示近 7 天训练次数和强度。
- 展示近 7 天比赛出场分钟造成的疲劳变化。
- 伤病风险先显示 TODO 或隐藏，不参与判断。

### 18.3 训练日历页

从 `training_results` 读取历史：

- 每日训练内容。
- 每日训练强度。
- 发生整数突破的球员。
- 全队成长总量。

### 18.4 训练历史页

从 `training_results` 聚合：

- 过去 4 周各训练类型次数。
- 属性成长总量。
- 球员成长排行。
- 套餐使用频率。

## 19. 事件接入

建议新增事件：

| 事件 | 时间 |
| --- | --- |
| `TRAINING_SLOT_COMPLETED` | 每天上午/下午/晚上。 |
| `AI_TRAINING_PLAN_GENERATED` | 每天凌晨或新一天开始。 |
| `TRAINING_WEEKLY_SUMMARY` | 每 7 天。 |

当前赛季为 42 天，可以按虚拟时间调度：

| 时段 | 建议结算时间 |
| --- | --- |
| 上午 | 10:00 |
| 下午 | 15:00 |
| 晚上 | 20:00 |

如果暂时不接真实时钟，可以在推进赛季日时一次性结算当天 3 个时段。

## 20. 数值调参目标

### 20.1 成长速度目标

建议一个高潜年轻球员在稳定专项培养下：

| 时间 | 预期 |
| --- | --- |
| 1 周 | 关键属性提升 0.3-0.8。 |
| 1 赛季 42 天 | 关键属性提升 2.0-4.0。 |
| 2-3 赛季 | 明显从替补成长为主力。 |
| 3-4 赛季 | 重点培养的一线队年轻球员应接近个人属性上限，但不保证所有属性练满。 |

普通球员：

| 时间 | 预期 |
| --- | --- |
| 1 周 | 关键属性提升 0.1-0.4。 |
| 1 赛季 | 关键属性提升 0.8-1.8。 |

老将：

| 时间 | 预期 |
| --- | --- |
| 1 周 | 大多数能力微小成长或无成长。 |
| 1 赛季 | 专项微调 0.2-0.8。 |

### 20.2 单次训练建议范围

| 情况 | 单次主属性成长 |
| --- | --- |
| 高潜年轻球员，适配训练 | 0.08-0.17 |
| 普通年轻球员，适配训练 | 0.04-0.09 |
| 成年主力，适配训练 | 0.02-0.06 |
| 老将或接近上限 | 0.00-0.03 |
| 不适配训练 | 0.00-0.03 |

## 21. 实施阶段

### Phase 1：设计落地与数据迁移

- 新增训练设计文档。
- 设计训练内容配置。
- 属性字段从整数迁移到 `DECIMAL(5,2)`。
- 新增成长曲线和属性上限字段。
- 新增 `players.fatigue` 和 `players.fatigue_updated_at`。
- 调整赛前初始体力公式，使 `fitness` 和 `fatigue` 同时参与。
- 球员生成时写入成长曲线。

### Phase 2：训练计划与结算

- 新增训练计划表。
- 新增训练结果表。
- 实现 `TrainingService`。
- 实现 7 天计划保存与读取。
- 实现训练结算和小数属性成长。
- 实现训练对 `fitness/fatigue` 的结算。
- 实现赛后 `fitness/fatigue` 双轨回写。

### Phase 3：前端替换 mock

- 周计划页接入真实 API。
- 支持套餐、分组、一键分组和拖拽。
- 疲劳/日历/历史页读取真实数据。

### Phase 4：AI 训练规划

- 实现 AI 球队训练偏好。
- 每日自动生成 AI 训练。
- 人类玩家未规划时套用默认训练。

### Phase 5：后续扩展

- 伤病风险。
- 教练组。
- 设施。
- 训练设施升级。
- 球员个人训练目标。
- 队内导师和老带新。

## 22. TODO

- 伤病系统：高强度训练、低体力、高疲劳、密集比赛共同影响伤病概率。
- 恢复系统：理疗、休息、轻训对伤病恢复和状态恢复的影响。
- 教练系统：不同教练提高不同训练类别效率。
- 青训联动：青训营球员是否使用简化训练模型，还是与一线队共享完整训练模型。
- 比赛表现反馈：高评分球员是否获得额外成长，低评分是否触发专项建议。
