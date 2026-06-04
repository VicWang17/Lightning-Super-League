# Lightning Super League 测试策略

## 背景

项目是在线实时 Web 游戏，测试目标不是验证单个事件处理函数，而是验证游戏世界能否在加速时间下长期稳定运行。核心流程包括：

- 赛季创建、启动、结算和切换。
- 比赛按虚拟时间开赛，并由比赛引擎推演和落库。
- 杯赛晋级、冠军写入。
- 升降级、附加赛和球队联赛归属变更。
- 未来白天会出现 AI 决策、训练、转会、随机伤病、新闻等大量系统交互。
- 本地应能运行多赛季流程压测，例如连续运行 100 个赛季。

## 当前问题

旧 console 和部分测试没有真正使用虚拟时钟。

典型问题：

- `scripts.dev_sim` 先查询最早的 pending event，再把 `now` 直接传成 `event.scheduled_at`，绕过了 `GameClock`。
- `/dev/clock/tick` 名义上是 tick，实际没有调用 `clock.tick()`。
- `SeasonService.fast_forward()` 推进的是赛季 day，不是虚拟时间。
- FastAPI 启动时没有后台 game loop，虚拟时钟流逝不会自动驱动游戏世界。
- 现有集成测试主要覆盖 EventQueue 生命周期和轻量分发，不覆盖完整赛季长流程。

这会导致测试结果失真：即使不开前端、不开后端服务，console 也能直接推动比赛。这本身不是错，因为流程测试可以不依赖前端，但错在它绕开了虚拟时钟这个权威时间源。

## 需求总结

测试系统必须满足以下要求：

1. 虚拟时间是权威输入。
   测试可以很快，但必须通过 `GameClock` 推进时间，而不是把事件时间伪装成当前时间。

2. 测试目标是完整游戏流程。
   重点不是单个 handler，而是整个世界连续运行后的状态正确性。

3. 不要求前端参与流程压测。
   前端只负责展示和玩家交互，不应成为游戏世界推进的必要条件。

4. 可以不追求极限速度。
   100 个赛季跑一天可以接受，前提是路径真实、结果可重复、能暴露长期状态问题。

5. pending event 不能承载所有未来交互。
   它适合可靠定时任务，不适合作为整个游戏世界唯一驱动方式。

## 架构原则

推荐采用混合模型：

```text
GameClock
  -> GameLoop / SimulationRunner
    -> due persisted events
    -> periodic game systems
      -> MatchSystem
      -> SeasonSystem
      -> TrainingSystem
      -> TransferSystem
      -> AISystem
      -> RandomInteractionSystem
```

### GameClock

只负责回答“游戏世界当前时间”。

支持：

- `realtime`：生产环境或真实演示。
- `turbo`：真实时间加速流逝。
- `step`：测试和调试中手动推进。
- `paused`：冻结观察。

### GameLoop / SimulationRunner

负责测试和开发模式下的世界推进：

- 推进虚拟时间到下一个关键时间点。
- 处理所有到期系统任务。
- 运行日 tick、小时 tick、比赛 tick 等周期系统。
- 收集结果和 invariant errors。

当前第一阶段先实现 persisted events 的虚拟时间驱动；后续新增白天系统时，应在 runner 中注册周期系统，而不是把所有交互写入 EventQueue。

### EventQueue

只用于必须可靠持久化的定时任务，例如：

- 赛季开始和结束。
- 比赛日触发。
- 杯赛晋级。
- 升降级处理。
- 转会挂牌到期。
- 转会报价过期。
- AI 每日转会市场扫描。
- AI 转会报价响应。
- 玩家操作产生的延迟任务。

不建议用于：

- 高频 AI 决策。低频且需要可审计的 AI 日常任务，例如每日转会扫描，可以作为 persisted event。
- 每小时随机交互。
- 普通训练、疲劳、状态波动。
- 新闻生成等可按周期批处理的系统。

这些应该由周期性 game systems 处理。

## 测试模式

### 1. 单元测试

目标：验证纯逻辑。

覆盖：

- `GameClock` 模式切换和 tick。
- `EventQueue` 状态机。
- 赛程生成。
- 比赛结果转换和基础落库逻辑。
- `PlayerFatigueService`：
  - `fitness` 和 `fatigue` 分别结算，不互相覆盖。
  - 同一疲劳值下，`GK` 的初始体力折扣小于 `DF/MF/FW`。
  - `fatigue >= 91` 时禁止高强度训练。
  - 休息、理疗、水疗降低 `fatigue`，高强度训练提高 `fatigue`。
  - 比赛出场分钟越高，`fitness` 降得越多，`fatigue` 升得越多。
- `TrainingGrowthService`：
  - 小数属性可以累计，展示和比赛使用向下取整。
  - 达到属性上限后训练收益为 0。
  - 疲劳越高，训练成长倍率越低。
  - 重复训练递减生效。
  - 年龄成长曲线对收益有影响。

### 2. 组件测试

目标：验证单个系统在真实数据库中的行为。

覆盖：

- 一个 MATCH_DAY 完整执行。
- 杯赛晋级后生成下一轮。
- 赛季结束后创建下一赛季。
- 升降级后球队数量和归属正确。
- 一个训练时段完整执行：
  - 训练计划从 `planned` 变为 `completed`。
  - `training_results` 写入属性成长、体力变化、疲劳变化。
  - 球员能力小数更新，整数突破被记录。
  - `state_training_load_score` 被刷新。
- 一个比赛后状态结算：
  - 出场球员 `fitness` 下降、`fatigue` 上升。
  - 未出场球员 `fitness` 恢复、`fatigue` 小幅下降。
  - `MatchResult.player_stats` 记录 `fitness_before/after`、`fatigue_before/after`、`initial_stamina`。
- 赛前 payload：
  - `initial_stamina` 使用 `fitness + fatigue + STA + position` 公式。
  - 高疲劳球员进入比赛时 stamina 明显低于低疲劳球员。
  - 门将高疲劳时仍有折扣，但折扣幅度小于外场球员。

### 3. 流程测试

目标：验证完整世界流程。

模式：

```bash
python backend/scripts/dev_console.py run-seasons 1
python backend/scripts/dev_console.py run-seasons 10
python backend/scripts/dev_console.py run-days 30
python backend/scripts/dev_console.py next
```

要求：

- 使用 `SimulationRunner`。
- 先推进 `GameClock`，再处理 due events。
- 不直接把 `now` 设为 event timestamp。
- 每轮输出处理事件数、赛季结算数、停止原因。

### 4. 长期压测

目标：暴露长期状态腐烂、数据膨胀、赛季切换错误。

建议命令：

```bash
python backend/scripts/dev_console.py bootstrap
python backend/scripts/dev_console.py run-seasons 100 --max-events 100000
python backend/scripts/dev_console.py check
```

压测可使用：

- `MATCH_ENGINE_TRANSPORT=http` + 长驻 Go engine server，更接近真实部署。
- `MATCH_ENGINE_TRANSPORT=process`，便于本地无服务运行，但每场 `go run` 较慢。
- `MATCH_ENGINE_MODE=instant`，用于快速回归。
- 后续可增加 `accelerated`，保留分钟级比赛事件但加速推演。

## Invariant 检查

每次流程测试后至少检查：

- 没有 `failed` events。
- 没有长期停留在 `processing` 的 events。
- `finished` fixtures 必须有比分。
- 当前赛季唯一且状态合理。
- 比赛结果数量随 finished fixtures 增长。

后续应扩展：

- 联赛积分榜 played 总数等于对应 finished league fixtures 的两倍。
- 杯赛每个已完成赛季都有冠军。
- 升降级后每个联赛球队数正确。
- 球队总数不丢失、不重复。
- 球员体力、疲劳、财政、训练等数值没有非法范围。
- `players.fitness` 始终在 `0-100`。
- `players.fatigue` 始终在 `0-100`。
- 高疲劳球员的 `initial_stamina` 均值低于低疲劳球员。
- 训练结果中的属性成长不为负，且不超过属性上限。
- 长期运行后没有大量球员在短期内全属性练满。
- 连续 N 个赛季后 pending events 数量不会异常膨胀。

## 训练与疲劳专项测试

训练系统上线后，必须新增专项测试，避免两个极端：

- 训练没有用：玩家安排训练后，球员长期没有可感知成长。
- 训练太强：全员很快练满，潜力和年龄曲线失去意义。

### 疲劳是否真实影响比赛

构造同一球员的不同疲劳状态：

| Case | fitness | fatigue | position | 预期 |
| --- | --- | --- | --- | --- |
| A | 95 | 5 | MF | `initial_stamina` 接近满值。 |
| B | 95 | 60 | MF | `initial_stamina` 明显低于 A。 |
| C | 95 | 60 | GK | `initial_stamina` 低于 A，但高于同疲劳外场球员。 |
| D | 70 | 60 | MF | 低于 B。 |

验收：

- B 比 A 至少低 10 点初始体力。
- C 比 B 至少高 5 点初始体力。
- D 比 B 更低。
- 比赛引擎 payload 中能看到差异，不只停留在数据库。

### 疲劳是否制约训练

构造同一球员、同一训练内容：

| Case | fatigue | 预期训练收益 |
| --- | --- | --- |
| A | 10 | 正常或略高。 |
| B | 50 | 明显低于 A。 |
| C | 85 | 大幅低于 A。 |
| D | 95 | 高强度训练不可安排，只能恢复/分析。 |

验收：

- B 的成长低于 A。
- C 的成长不超过 A 的 65%。
- D 保存训练计划时返回明确错误。

### 训练是否有效

构造一名 20-22 岁、高潜、成长曲线正常、属性未接近上限的球员。

连续 7 天安排适配专项训练，预期：

- 主属性小数成长累计明显大于副属性。
- 至少有可见小数进度变化。
- 若初始属性距离下一个整数很近，应发生整数突破。
- `training_results` 能解释成长来源。

建议验收区间：

| 训练周期 | 主属性累计成长 |
| --- | --- |
| 7 天适配训练 | `0.25-0.90` |
| 42 天高质量培养 | `1.5-3.5` |

### 训练是否失控

跑 1 个完整赛季或 3 个赛季的闭环压测，统计：

- 全联盟球员平均 OVR 增长。
- 18-23 岁高潜球员平均成长。
- 29 岁以上球员平均成长。
- 到达属性上限的球员比例。
- 单属性突破次数分布。
- AI 球队和玩家默认训练球队的成长差距。

建议红线：

- 普通球员单赛季关键属性平均成长不应超过 `2.0`。
- 高潜年轻球员单赛季关键属性平均成长建议落在 `3.0-6.0`，低于区间说明培养反馈仍偏弱，高于区间说明可能过快练满。
- 29-32 岁球员单赛季关键属性平均成长不应超过 `0.5`。
- 33-34 岁球员应出现温和负成长。
- 35 岁以上高能力球员应出现明显负成长；90 OVR 级别球员持续到 35 岁时，目标综合能力通常应回落到 70 多到 80 出头区间。
- 连续 3 个赛季后，全联盟不应出现大量 20 满属性球员。
- 训练收益为 0 的球员比例不能过高，否则玩家会觉得训练无效。

### AI 训练规划是否合理

长期压测应记录 AI 训练分布：

- 恢复训练占比。
- 高强度训练占比。
- 不同球队风格的训练差异。
- 高疲劳时是否自动降低强度。
- 密集赛程是否增加恢复。

验收：

- AI 不应连续多日无脑高强度训练。
- 高疲劳球队恢复训练占比应高于低疲劳球队。
- 年轻队技术专项占比应高于老年队。
- 不同 AI 风格之间训练选择应有可见差异。

### 转会市场是否形成流动

长期压测应记录 `transfer_metrics.csv`：

- AI 是否产生 `initial_offers_sent`。
- AI 是否产生 `listings_created`。
- 是否出现 `counter_offers_sent` 和 `final_offers_sent`。
- 挂牌球员是否能成交，`club_transfers_bought` / `club_transfers_sold` 是否长期为 0。
- 解约球员是否通过 `players_released` 进入自由市场。
- 拒绝、过期、落选报价是否有合理分布。

健康预期：

- AI 至少能主动挂牌和主动报价。
- 有诚意但不足的报价应能触发反报价。
- 挂牌等待期结束应自动接受最高有效报价。
- 非挂牌报价超时应自动拒绝。
- 成交后 roster 和资金不变量不应被破坏。
- 解约应扣违约金，并创建 `FreeAgentListing(origin=RELEASED)`。

## Console 要求

新的 console 替代旧 console，支持：

- `bootstrap`：一键初始化基础设施、迁移、基础数据和首赛季。
- `status`：查看时钟、赛季、事件、比赛状态。
- `next`：推进虚拟时钟到下一个 pending event，并处理该时间点到期事件。
- `run-days`：按虚拟天数推进。
- `run-seasons`：连续运行 N 个赛季。
- `results`：查看近期比赛结果。
- `check`：运行基础 invariant 检查。
- 交互模式：无参数运行时显示菜单。

新增共享虚拟时钟后，观察模式应优先使用：

```bash
python backend/scripts/console.py
python backend/scripts/console.py watch --runtime core --speed 20
python backend/scripts/console.py watch --runtime api --speed 20
```

`watch --speed 20` 表示真实 1 秒约等于游戏世界 20 秒。该时间写入
`game_clock_states`，FastAPI `/api/v1/clock` 和 Dashboard 顶部时钟读取同一份状态。

Console 支持两种运行模式：

- Core：不启动 FastAPI，直接调用后端 service。用于长流程压测和快速定位后端业务问题。
- API：检查 FastAPI 和前端是否运行；未运行则后台启动，然后通过 HTTP 调 `/api/v1/dev/simulation/*` 推进世界。用于验证服务进程、API 路由和 Dashboard 时钟。

API 模式退出时，如果 console 自动启动了前端/后端，会询问是否结束这些进程。

比赛生命周期第一阶段只做分层：`scheduled -> ongoing -> finished`。当前 Go 引擎仍是同步最终结果，不是实时比赛。真实实时引擎的 TODO 是：

- Go engine 创建 match session。
- 引擎按 match speed tick 推进比赛分钟。
- WebSocket/SSE 推送当前分钟、比分、事件和统计。
- 用户通过 command API 提交临场战术、换人等指令。
- 引擎在后续 tick 中应用指令。
- 比赛结束后回调 Python 后端落库并触发结算。

## 关键约束

- 流程测试可以不依赖前端。
- 流程测试可以不启动 FastAPI，但必须复用后端 service、数据库、比赛引擎 client。
- 不允许再用“直接把 now 设置成 event.scheduled_at”的方式作为主测试路径。
- EventQueue 是可靠任务队列，不是未来所有游戏交互的唯一抽象。
