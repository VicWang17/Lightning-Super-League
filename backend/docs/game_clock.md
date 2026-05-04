# GameClock + EventQueue 开发文档

> Phase 1~6 实施总结 —— 虚拟时钟系统全面替换 day-by-day 赛季推进。

## 架构概览

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  GameClock  │────▶│  EventQueue  │────▶│ SeasonService   │
│ (虚拟时间源) │     │ (持久化队列)  │     │ (事件分发处理器) │
└─────────────┘     └──────────────┘     └─────────────────┘
       │                                            │
       ▼                                            ▼
  realtime / turbo                            MATCH_DAY (并发)
  step / paused                               CUP_PROGRESSION
                                              PROMOTION_RELEGATION
                                              SEASON_START / END
```

## GameClock

`app/core/clock.py` — 全局虚拟时钟单例。

### 模式

| 模式 | 行为 | 用途 |
|------|------|------|
| `realtime` | `now()` = `datetime.utcnow()` | 生产环境 |
| `turbo` | 虚拟时间 = 真实时间 × speed | 开发加速 |
| `step` | 时间不自动流逝，需手动 `tick()` | 调试/单步 |
| `paused` | 时间冻结 | 观察状态 |

### API

```python
from app.core.clock import clock

# 读取当前虚拟时间
now = clock.now()

# step 模式：手动推进 1 天
clock.tick(timedelta(days=1))

# 直接跳到目标时间
clock.fast_forward_to(datetime(2025, 6, 15))

# 切换模式
clock.set_mode("turbo", speed=100.0)
clock.set_mode("paused")
clock.set_mode("step")
```

### 环境变量

```bash
GAME_CLOCK_MODE=realtime      # realtime | turbo | step | paused
GAME_CLOCK_SPEED=100.0        # turbo 模式倍速
```

## EventQueue

`app/core/events.py` + `app/models/events.py` — 持久化事件队列。

### 事件类型

| 类型 | 触发时机 | 处理器 |
|------|----------|--------|
| `SEASON_START` | 赛季第一天 | `_handle_season_start` |
| `MATCH_DAY` | 每个比赛日 | `_handle_match_day` (并发模拟) |
| `CUP_PROGRESSION` | 杯赛日之后 | `_handle_cup_progression` |
| `PROMOTION_RELEGATION` | 升降级处理日 | `_handle_promotion_relegation` |
| `SEASON_END` | 赛季最后一天 | `_handle_season_end` |

### 状态机

```
PENDING ──pop()──▶ PROCESSING ──complete()──▶ COMPLETED
                           └─fail(retry<max)──▶ PENDING (延迟)
                           └─fail(retry>=max)──▶ FAILED
```

### 并发安全

`pop()` 使用 `SELECT ... FOR UPDATE SKIP LOCKED`，支持多 worker 并发消费而不重复处理。

## SeasonService 事件驱动入口

### 核心方法

```python
service = SeasonService(db)

# 处理下一个事件（通用）
result = await service.process_next_event()

# 处理下一天（兼容接口，内部调用 process_next_event）
result = await service.process_next_day(season)

# 连续运行直到下一个 MATCH_DAY / SEASON_END
results = await service.run_until_next_event(season)

# 快进 N 天（测试/调试）
results = await service.fast_forward(target_day=10, season=season)
```

### MATCH_DAY 并发执行

1. **并发 simulate**：所有 fixtures 的 `MatchSimulator.simulate()` 通过 `asyncio.gather()` 并发执行（纯计算，无 DB 写）
2. **串行 apply_result**：为避免 standings 共享状态竞争，`apply_result()` 串行执行
3. **统一 commit**：全部处理完后一次 `db.commit()`

未来 Go 引擎接入时，第 1 步改为并发调用 `match_engine_client.start_match()`，第 2 步由 `MATCH_ENGINE_COMPLETE` 事件触发。

## Dev Console API

`app/routers/dev.py` — 开发调试接口，前缀 `/api/v1/dev`。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/dev/clock` | 查看时钟状态 |
| POST | `/dev/clock/tick` | 单步推进 `{steps: 1}` |
| POST | `/dev/clock/fast-forward` | 快进 `{days: 5}` 或 `{events: 10}` |
| POST | `/dev/clock/set-mode` | 设置模式 `?mode=step` |
| GET | `/dev/events` | 查看事件队列（支持 status/event_type 筛选） |
| POST | `/dev/events/{id}/retry` | 重试失败事件 |
| DELETE | `/dev/events/{id}` | 取消事件 |
| POST | `/dev/season/advance` | 推进赛季 N 天 `{days: 1}` |

## 测试

```bash
cd backend
PYTHONPATH=$(pwd) pytest tests/unit/test_game_clock.py -v
PYTHONPATH=$(pwd) pytest tests/integration/test_event_queue.py -v
PYTHONPATH=$(pwd) pytest tests/integration/test_season_events.py -v
```

### 测试结构

- `tests/unit/test_game_clock.py` — GameClock 纯单元测试（8 个 case）
- `tests/integration/test_event_queue.py` — EventQueue CRUD + 重试 + 并发（9 个 case）
- `tests/integration/test_season_events.py` — 事件序列生成 + 分发 + 生命周期（10 个 case）

## 已替换的 `datetime.utcnow()`

以下 3 处赛季相关时间调用已替换为 `clock.now()`：

1. `services/season_service.py:68` — 赛季默认开始时间
2. `services/scheduler.py:675` — 赛季结束时间
3. `services/match_simulator.py:84` — 比赛完成时间

JWT、登录时间、软删除等非赛季时间保持系统时间不变。

## 数据库 Migration

```bash
alembic upgrade head   # 已应用：add_event_queue（event_queues 表）
```
