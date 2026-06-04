# 闭环多赛季压测手册

本文档用于手动运行合同、青训、新人自由市场、财政、球员状态、AI 决策和升降级闭环压测。压测不涉及前端展示，目标是验证游戏世界能否连续运行多个赛季，并产出可分析的数据报告。

## 1. 压测目标

压测重点不是单个接口是否可用，而是连续多赛季后系统是否仍然健康。

重点观察：

- 完整性：赛季能否正常结束并进入下一季；事件队列是否失败；球队人数是否保持在 `8-18`；是否需要自动补员。
- 球员流动：退役、合同到期、续约、青训签约、新人市场签约、自由市场签约是否都有发生。
- 财政：球队余额是否持续塌陷；工资压力是否正常；是否频繁签不起人。
- AI 决策：AI 是否能续约、签青训、签新人、补自由市场。
- 游戏性：强球员是否转化为战绩；冠军次年是否过度随机；是否出现超级球队滚雪球。
- 状态系统：球员状态是否整体偏低或偏高；合同、近期表现、体能、负荷、久疏战阵是否有单项过度支配。

## 2. 前置条件

所有命令默认在 backend 目录执行：

```bash
cd /Users/bilibili/Code/Lightning-Super-League/backend
```

建议使用下面环境变量：

```bash
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
export MATCH_ENGINE_TRANSPORT=process
export MATCH_ENGINE_MODE=instant
```

说明：

- `PYTHONUNBUFFERED=1`：保证日志实时输出。
- `MATCH_ENGINE_TRANSPORT=process`：由 Python 直接拉起比赛引擎进程，适合本地压测。
- `MATCH_ENGINE_MODE=instant`：比赛快速出结果，适合多赛季回归。

## 3. 完全重置后从 S1 开始

如果本次数据已经被错误逻辑污染，推荐清空开发库重来。注意 `reset_dev_db` 必须带 `ENV=dev`。

```bash
cd /Users/bilibili/Code/Lightning-Super-League/backend

ENV=dev PYTHONPATH=. .venv/bin/python -m scripts.reset_dev_db
ENV=dev PYTHONPATH=. .venv/bin/python -m scripts.init_system
PYTHONPATH=. .venv/bin/alembic stamp head
PYTHONPATH=. .venv/bin/python -m scripts.init_season
```

然后运行 3 个赛季：

```bash
mkdir -p reports/closed_loop_fresh_3s

PYTHONPATH=. PYTHONUNBUFFERED=1 MATCH_ENGINE_TRANSPORT=process MATCH_ENGINE_MODE=instant \
.venv/bin/python -u -m scripts.closed_loop_balance_test \
  --seasons 3 \
  --max-events-per-season 14000 \
  --match-log-limit 8 \
  --out reports/closed_loop_fresh_3s \
  2>&1 | tee reports/closed_loop_fresh_3s/run.log
```

## 4. 从当前数据库继续跑

如果数据库状态是可信的，只想继续模拟后续赛季：

```bash
cd /Users/bilibili/Code/Lightning-Super-League/backend

mkdir -p reports/closed_loop_resume_3s

PYTHONPATH=. PYTHONUNBUFFERED=1 MATCH_ENGINE_TRANSPORT=process MATCH_ENGINE_MODE=instant \
.venv/bin/python -u -m scripts.closed_loop_balance_test \
  --seasons 3 \
  --max-events-per-season 14000 \
  --match-log-limit 8 \
  --out reports/closed_loop_resume_3s \
  2>&1 | tee reports/closed_loop_resume_3s/run.log
```

如果只想快速检查当前数据库，不推进赛季：

```bash
mkdir -p reports/closed_loop_collect_only

PYTHONPATH=. PYTHONUNBUFFERED=1 \
.venv/bin/python -u -m scripts.closed_loop_balance_test \
  --seasons 0 \
  --out reports/closed_loop_collect_only \
  2>&1 | tee reports/closed_loop_collect_only/run.log
```

## 5. 单赛季冒烟测试

用于刚修完 bug 后快速验证不会炸：

```bash
mkdir -p reports/closed_loop_smoke_1s

PYTHONPATH=. PYTHONUNBUFFERED=1 MATCH_ENGINE_TRANSPORT=process MATCH_ENGINE_MODE=instant \
.venv/bin/python -u -m scripts.closed_loop_balance_test \
  --seasons 1 \
  --max-events-per-season 14000 \
  --match-log-limit 12 \
  --out reports/closed_loop_smoke_1s \
  2>&1 | tee reports/closed_loop_smoke_1s/run.log
```

如果希望遇到第一个错误就停止：

```bash
mkdir -p reports/closed_loop_smoke_stop

PYTHONPATH=. PYTHONUNBUFFERED=1 MATCH_ENGINE_TRANSPORT=process MATCH_ENGINE_MODE=instant \
.venv/bin/python -u -m scripts.closed_loop_balance_test \
  --seasons 1 \
  --stop-on-error \
  --max-events-per-season 14000 \
  --match-log-limit 12 \
  --out reports/closed_loop_smoke_stop \
  2>&1 | tee reports/closed_loop_smoke_stop/run.log
```

## 6. 日志和数据在哪里

每次压测的 `--out reports/<run_name>` 会生成以下文件：

```text
reports/<run_name>/
  run.log
  closed_loop_balance_report.md
  season_summary.csv
  team_season_metrics.csv
  player_season_metrics.csv
  youth_budget_metrics.csv
  event_results.jsonl
  invariants.csv
```

文件用途：

- `run.log`：终端完整日志。看异常、比赛结果、续约/签约事件、赛季结束摘要。
- `closed_loop_balance_report.md`：自动汇总报告。优先阅读。
- `season_summary.csv`：每季总览。看闭环、财政、状态、警告。
- `team_season_metrics.csv`：每队每季数据。看强弱队、财政差异、排名波动、滚雪球。
- `player_season_metrics.csv`：球员赛季数据。看 OVR、评分、状态分布。
- `youth_budget_metrics.csv`：每队每季青训预算和青训质量数据。看高青训预算是否真的产出更有用的新人。
- `event_results.jsonl`：每个事件的结构化结果。排查某类事件失败时使用。
- `invariants.csv`：系统不变量检查。任何 `error` 都优先处理。

注意：使用 `tee reports/<run_name>/run.log` 前必须先 `mkdir -p reports/<run_name>`，否则 `tee` 会提示目录不存在。

## 7. 终端日志怎么看

关键日志样式：

```text
[match] day=20 fixtures=128
[finance] wages_paid period=wage_20
[youth] refresh=...
[youth] trained=...
[season] end S7 -> S8
  ai renew=1448 academy=0 free_market=0
  post_expiration academy_signed=965 free_market=193 academy_candidates=2048 full=0 low_score=58 failed=0
[closed-loop] S7 events=61 roster=15/18 contracts=3066 youth=973 rookie_signed=452 auto_fill=0 errors=0 status=ok
```

优先关注：

- `status=ok`：该季是否正常结束。
- `errors=0`：是否没有 invariant error。
- `roster=15/18`：球队人数是否在合理范围。
- `auto_fill=0`：正常情况下应接近 0。
- `ai renew=...`：AI 是否在续约。
- `academy_signed/free_market/rookie_signed`：AI 是否能补人。
- `AI renew failed`、`Event processing failed`：出现后要先修代码，再重新跑。

## 8. AI 分析数据的流程

把以下文件交给 AI 或让 AI 读取：

```text
reports/<run_name>/closed_loop_balance_report.md
reports/<run_name>/season_summary.csv
reports/<run_name>/team_season_metrics.csv
reports/<run_name>/player_season_metrics.csv
reports/<run_name>/youth_budget_metrics.csv
reports/<run_name>/invariants.csv
reports/<run_name>/run.log
```

推荐让 AI 按下面顺序分析。

### 8.1 完整性

检查：

- `event_status` 是否全是 `ok`。
- `invariants_failed` 是否为 `0`。
- `failed_events_total` 是否为 `0`。
- `teams_below_8` 是否为 `0`。
- `teams_above_max` 是否为 `0`。
- `roster_min/roster_max` 是否在 `8-18`。
- `auto_fill_players_joined` 是否接近 `0`。

结论口径：

- 有任何 `error`，先不做平衡分析，优先修完整性。
- `auto_fill` 长期大于 0，说明续约、青训、自由市场补人不够。

### 8.2 球员流动

检查 `season_summary.csv`：

- `contracts_created`
- `renewals_or_recontracts`
- `retired_players`
- `contracts_expired_active_now`
- `youth_generated`
- `youth_signed`
- `rookie_market_listings`
- `rookie_market_signed`
- `free_agent_active`
- `free_agent_signed`

健康预期：

- 每季应该有退役和合同到期。
- 每季应该有大量续约。
- 青训签约和新人市场签约都应该有发生。
- `rookie_market_active` 可以存在，但保护标记不应长期残留。
- 自由市场 active 太多说明供给过剩；太少说明新人流入不足。

### 8.3 财政

检查：

- `avg_balance`
- `min_balance`
- `avg_wage_pressure_pct`
- `max_wage_pressure_pct`
- `teams_over_wage_cap`
- `team_season_metrics.csv` 中不同联赛等级的余额分布。

健康预期：

- `avg_balance` 不应连续快速下跌。
- `min_balance` 不应逼近 0 或负数。
- `avg_wage_pressure_pct` 建议大致在 `35%-70%`。
- `max_wage_pressure_pct` 不应长期超过 `100%`。
- 余额 Gini 不宜快速超过 `0.25`。

判断：

- 平均余额下降且工资压力下降：收入仍偏低或青训/运营支出偏高。
- 平均余额上升且 Gini 快速上升：可能强队滚雪球。
- 很多 AI 签不起人：财政过紧或签约策略过激。

### 8.4 青训预算质量

检查 `closed_loop_balance_report.md` 里的 `Youth Budget Signals`，以及 `youth_budget_metrics.csv`。

关键字段：

- `youth_budget_pct`：青训预算占锁定预算总额的比例。
- `budget_tier`：按预算比例分为 `low`、`medium`、`high`。
- `avg_youth_ovr` / `max_youth_ovr`：本季该队青训即时能力。
- `avg_potential_max` / `max_potential_max`：本季该队青训潜力。
- `avg_prospect_score` / `best_prospect_score`：压测用青训价值分，综合 OVR、潜力、年龄、成长速度。
- `useful_prospect_rate`：对本队有即时或未来价值的新人比例。
- `fast_growth_count`：快速成长青训人数。
- `potential_s_count` / `potential_a_count`：高潜力青训人数。

健康预期：

- `high` 档的 `best_prospect_score`、`avg_potential_max`、`useful_prospect_rate` 应该明显高于 `low` 档。
- `low` 档可以偶尔刷出好球员，但多数应落在 `unusable_prospect_count`，不能稳定补强球队。
- `medium` 档应介于两者之间，不应和 `high` 完全一样。
- 报告里的 `Youth budget pct vs best prospect score` 和 `Youth budget pct vs avg potential max` 应该为正；单次 1-3 季样本可能波动，但长期不应接近 0 或负数。

判断：

- 高预算和低预算指标几乎一样：青训生成参数没有真正吃到预算。
- 高预算只提高数量、不提高 `best_prospect_score` 或潜力：预算影响太浅，玩家投入缺少反馈。
- 低预算也经常高 `useful_prospect_rate`：青训过于慷慨，会削弱预算选择。

### 8.5 强弱队和滚雪球

用 `team_season_metrics.csv` 分析：

- `top8_ovr` vs `points` 相关性。
- `wage_bill` vs `points` 相关性。
- `balance` Gini。
- `top8_ovr` Gini。
- 冠军次年排名。
- 前二名次年是否频繁跌到第 7/8。
- 高余额球队是否越来越集中在高排名。

健康预期：

- `top8_ovr vs points` 建议在 `0.25-0.45`。太低表示强队不明显，太高表示强队太稳定。
- `Player OVR vs average rating` 建议大于 `0.55`。
- `Champion relegations next season` 应接近 `0`。
- 冠军次年掉到倒数可以偶发，但不应常态化。
- `top8 OVR Gini` 不应持续上升。

### 8.6 球员状态

检查：

- `avg_state_score`
- `min_state_score`
- `max_state_score`
- `players_hot`
- `players_good`
- `players_neutral`
- `players_low`
- `avg_contract_score`
- `avg_recent_match_score`
- `avg_fitness_score`
- `avg_match_load_score`
- `avg_match_rust_score`

健康预期：

- `avg_state_score` 接近 `-1 到 +1`。
- 不应大部分球员都是 `LOW`。
- 不应大部分球员都是 `HOT/GOOD`。
- 单个状态组件不应长期压倒其他组件。

判断：

- `avg_contract_score` 太低：工资满意度或合同到期压力过重。
- `avg_fitness_score` 太低：体能恢复不足或比赛消耗过高。
- `avg_match_load_score` 太低：负荷惩罚过重。
- `avg_match_rust_score` 太低：未出场惩罚过重或轮换不足。

### 8.7 训练与疲劳

训练系统上线后，闭环报告需要新增训练与疲劳指标。建议输出到 `training_metrics.csv` 和 `player_fatigue_metrics.csv`。

训练检查：

- `training_sessions_total`
- `training_sessions_by_category`
- `high_intensity_sessions_pct`
- `recovery_sessions_pct`
- `avg_attribute_gain_per_session`
- `avg_main_attribute_gain_per_season`
- `breakthroughs_per_season`
- `players_at_attribute_cap`
- `avg_growth_by_age_band`
- `avg_growth_by_potential_letter`

疲劳检查：

- `avg_fitness`
- `min_fitness`
- `avg_fatigue`
- `max_fatigue`
- `players_fatigue_75_plus`
- `players_fatigue_91_plus`
- `avg_initial_stamina`
- `avg_initial_stamina_by_position`
- `gk_fatigue_stamina_penalty_avg`
- `outfield_fatigue_stamina_penalty_avg`

健康预期：

- `fitness` 和 `fatigue` 都必须始终在 `0-100`。
- 高疲劳球员的 `initial_stamina` 应明显低于低疲劳球员。
- 同疲劳下，门将的体力折扣应小于外场球员。
- 高强度训练不能长期占比过高，否则 AI 会把球队练崩。
- 恢复训练占比不能过低，否则疲劳会长期堆满。
- 普通球员单赛季关键属性平均成长不应超过 `2.0`。
- 高潜年轻球员单赛季关键属性平均成长建议落在 `3.0-6.0`，否则 3-4 个赛季接近练满的培养目标无法成立。
- 29-32 岁球员单赛季关键属性平均成长不应超过 `0.5`。
- 33-34 岁球员应出现温和负成长。
- 35 岁以上高能力球员应出现明显负成长；90 OVR 级别球员持续到 35 岁时，目标综合能力通常应回落到 70 多到 80 出头区间。
- 连续 3 个赛季后，不应出现大量球员快速练满多个属性。

判断：

- `avg_fatigue` 持续上升：比赛/训练疲劳过重，或恢复不足。
- `avg_initial_stamina` 长期偏低：疲劳折扣过强，比赛质量会被系统性压低。
- `avg_attribute_gain_per_session` 接近 0：训练无效，玩家缺少反馈。
- `avg_attribute_gain_per_session` 过高：训练过强，潜力和年龄曲线失去意义。
- `players_at_attribute_cap` 快速上升：属性上限或成长衰减没有有效限制。
- AI 高强度训练占比过高：AI 训练规划需要更强的疲劳约束。

### 8.8 转会市场

转会系统上线后，闭环报告需要新增 `transfer_metrics.csv`，并在 `closed_loop_balance_report.md` 中输出 `Transfer Market Signals`。

必须记录：

- `listings_created`：球队主动挂牌人数。
- `initial_offers_sent`：主动初始报价数，用于判断 AI 是否会自己发起转会。
- `counter_offers_sent`：反报价数，用于判断讨价还价是否发生。
- `final_offers_sent`：最终报价数，用于判断买方是否会回应反报价。
- `club_transfers_bought` / `club_transfers_sold`：队间成交买入/卖出。
- `transfer_spend` / `transfer_sales_gross`：转会支出与卖出总额。
- `players_released`：解约人数。
- `release_penalties`：解约违约金支出。
- `offers_rejected` / `offers_expired` / `offers_outbid_closed`：拒绝、过期和多报价落选情况。

事件日志应记录：

- `[transfer-ai] handled=... listed=... sent=... releases=...`
- `[transfer-expire] auto_accept=... auto_reject=... failed=...`
- `[transfer-listing] auto_accept=... expired=... failed=...`

健康预期：

- AI 每赛季应出现非零 `initial_offers_sent`，否则 AI 没有主动买人。
- AI 每赛季应出现一定 `listings_created`，否则冗余/到期球员不会进入市场。
- 至少部分有诚意报价会产生 `counter_offers_sent` 或成交；如果全是拒绝，AI 卖方阈值可能过高。
- 挂牌球员有报价时，等待期结束应能自动接受最高有效报价。
- 非挂牌报价超时应自动拒绝，不应悄悄成交。
- 解约球员应创建 `FreeAgentListing(origin=RELEASED)`，并在 `transfer_records` 中记录 `RELEASE`。
- 成交后买方 roster 不应超过上限，卖方 roster 不应低于下限。
- 转会资金流应体现为买方 `TRANSFER/EXPENSE`、卖方 `TRANSFER/INCOME`，卖方收入应扣除 5% 交易税。

判断：

- `initial_offers_sent = 0`：检查 `AI_TRANSFER_MARKET_SCAN` 是否排入赛季事件、AI 球队识别是否正确、挂牌市场是否过少。
- `counter_offers_sent = 0`：检查 AI 估值阈值是否过于极端，或报价区间是否只触发接受/拒绝。
- `club_transfers_bought = 0` 且报价很多：检查成交前 roster/余额/工资压力校验是否过严。
- `players_released = 0`：可能正常，只有 `CRISIS` 财政下 AI 才会解约；若手动制造危机仍为 0，需要检查 AI 解约条件。
- `offers_expired` 很高：检查 AI 快速响应事件是否正常触发。

## 9. 建议 AI 输出格式

分析完成后，AI 应按这个结构汇报：

```text
结论：
- 闭环是否跑通
- 是否存在阻塞性 bug
- 是否存在财政风险
- 是否存在滚雪球或随机性过强

关键数据：
- Sx-Sy roster、contracts、youth、rookie、auto_fill
- avg/min balance
- wage pressure
- state score
- training growth / fatigue signals
- transfer listings / offers / counters / completed / releases
- OVR/points correlation
- champion relegation/repeat champion

问题分级：
- P0：流程中断、事件失败、数据不变量错误
- P1：长期会毁档的平衡问题，例如财政持续归零
- P2：游戏性调优，例如强弱队区分度不足

建议修复：
- 每个建议说明原因、预期影响、需要再压测验证的指标
```

## 10. 常见问题

### reset_dev_db 报 ENV 错误

必须带 `ENV=dev`：

```bash
ENV=dev PYTHONPATH=. .venv/bin/python -m scripts.reset_dev_db
```

### alembic 提示表已存在

通常是 reset 没成功，或不是 dev 环境。不要继续在半重置状态压测，先确认 `reset_dev_db` 成功。

### tee 提示 No such file or directory

先创建目录：

```bash
mkdir -p reports/<run_name>
```

### 某赛季因为 bug 跑坏了

如果没有快照回滚工具，不建议手工删除合同、球员、事件数据。最稳方式是：

1. 修 bug。
2. 清库重建。
3. 从 S1 重新跑。

如果只是想看修复后是否继续能跑，也可以从当前库继续跑，但这份数据不能用于严肃平衡结论。

### 日志太多

降低比赛日志数量：

```bash
--match-log-limit 3
```

完全关闭事件细节：

```bash
--quiet-events
```

## 11. 推荐回归节奏

每次改闭环或数值后：

1. 跑单季冒烟：`--seasons 1 --stop-on-error`
2. 看 `errors=0` 后跑三季：`--seasons 3`
3. AI 分析报表。
4. 若发现财政、状态、流动性问题，调整数值。
5. 重大规则改动后清库从 S1 重跑，避免历史数据污染结论。
