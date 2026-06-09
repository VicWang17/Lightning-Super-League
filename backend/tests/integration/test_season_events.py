"""
赛季事件流集成测试 - Phase 5（轻量版）

避免完整创建赛季（256 支球队 × 多轮比赛，性能开销大）。
改为：
  1. 测试 EventQueue.build_season_events 生成正确事件序列
  2. 测试 SeasonService._dispatch_event 正确分发各类型事件
  3. 测试 process_next_event 的 peek-pop-complete 生命周期
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus
from app.models.events import EventQueue as EventQueueModel
from app.services.season_service import SeasonService
from app.core.formats import get_default_format
from app.core.events import EventQueue, EventType, EventStatus, GameEvent
from app.core.clock import clock


@pytest.mark.asyncio
class TestBuildSeasonEvents:
    """build_season_events 单元测试（同步，不需要 asyncio 标记）"""
    
    def test_generates_all_event_types(self):
        """应生成 SEASON_START + MATCH_DAY + CUP_PROGRESSION + PROMOTION_RELEGATION + SEASON_END"""
        start = datetime(2025, 1, 1)
        events = EventQueue.build_season_events(
            season_id="season-1",
            league_days=[1, 7, 14],
            cup_days=[10, 20],
            promotion_day=22,
            total_days=30,
            start_date=start,
        )
        
        types = [e.event_type for e in events]
        assert EventType.SEASON_START in types
        assert EventType.SEASON_END in types
        assert types.count(EventType.MATCH_DAY) == 30  # 每天一场
        assert types.count(EventType.CUP_PROGRESSION) == 2  # 每个杯赛日之后
        assert types.count(EventType.PROMOTION_RELEGATION) == 3
    
    def test_match_day_payload_contains_day_info(self):
        """MATCH_DAY 事件的 payload 应包含 day 和 league_round"""
        start = datetime(2025, 1, 1)
        events = EventQueue.build_season_events(
            season_id="season-1",
            league_days=[1, 7],
            cup_days=[10],
            promotion_day=22,
            total_days=15,
            start_date=start,
        )
        
        match_days = [e for e in events if e.event_type == EventType.MATCH_DAY]
        day1 = match_days[0]
        assert day1.payload["day"] == 1
        assert day1.payload.get("league_round") == 1
        
        day7 = match_days[6]
        assert day7.payload["day"] == 7
        assert day7.payload.get("league_round") == 2

    def test_events_use_hour_level_schedule(self):
        """关键事件应使用小时级 scheduled_at，而不是全挤在日期零点。"""
        start = datetime(2025, 1, 1)
        events = EventQueue.build_season_events(
            season_id="season-1",
            league_days=[1],
            cup_days=[1],
            promotion_day=2,
            total_days=2,
            start_date=start,
            wage_days=[1],
        )

        by_type = {}
        for event in events:
            by_type.setdefault(event.event_type, []).append(event)

        assert by_type[EventType.SEASON_START][0].scheduled_at.hour == 8
        assert by_type[EventType.SEASON_FINANCE_INITIALIZED][0].scheduled_at.hour == 9
        assert by_type[EventType.WAGES_PAID][0].scheduled_at.hour == 10
        assert by_type[EventType.MATCH_DAY][0].scheduled_at.hour == 20
        assert by_type[EventType.CUP_PROGRESSION][0].scheduled_at.hour == 23
    
    def test_events_are_ordered_by_scheduled_at(self):
        """事件应按 scheduled_at 升序排列"""
        start = datetime(2025, 1, 1)
        events = EventQueue.build_season_events(
            season_id="season-1",
            league_days=[],
            cup_days=[],
            promotion_day=-1,
            total_days=5,
            start_date=start,
        )
        
        for i in range(len(events) - 1):
            assert events[i].scheduled_at <= events[i + 1].scheduled_at


@pytest.mark.asyncio
class TestDispatchEvent:
    """_dispatch_event 分发测试（使用 mock 避免数据库操作）"""
    
    async def test_dispatch_season_start(self, db):
        service = SeasonService(db)
        event = GameEvent(event_type=EventType.SEASON_START, payload={"season_id": "s1"})
        result = await service._dispatch_event(event)
        assert result["event"] == "season_start"
    
    async def test_dispatch_match_day_with_no_fixtures(self, db):
        """MATCH_DAY 分发：如果没有 fixtures，应返回 0 场处理"""
        service = SeasonService(db)
        # 使用不存在的 season_id，查询不到 fixtures
        event = GameEvent(
            event_type=EventType.MATCH_DAY,
            payload={"season_id": "nonexistent", "day": 1}
        )
        with pytest.raises(ValueError, match="Season not found"):
            await service._dispatch_event(event)
    
    async def test_dispatch_season_end_with_no_season(self, db):
        """SEASON_END 分发：season 不存在时应报错"""
        service = SeasonService(db)
        event = GameEvent(
            event_type=EventType.SEASON_END,
            payload={"season_id": "nonexistent"}
        )
        with pytest.raises(ValueError, match="Season not found"):
            await service._dispatch_event(event)

    async def test_promotion_movement_recomputes_data_after_event_reload(self, db):
        """升降级应用日不能依赖前序事件挂在 Season 对象上的临时属性。"""
        service = SeasonService(db)
        season = Season(id="season-1", season_number=1, total_days=25)
        movement_day = get_default_format().season.promotion_day
        promotion_data = {
            "auto_promotions": [("team-up", "league-2", "league-1")],
            "auto_relegations": [("team-down", "league-1", "league-2")],
            "playoff_teams": {},
        }
        final_results = {
            "final_promotions": promotion_data["auto_promotions"],
            "final_relegations": promotion_data["auto_relegations"],
            "playoff_promotions": [],
            "playoff_relegations": [],
        }

        service.promotion_service.process_season_end = AsyncMock(return_value=promotion_data)
        service._process_playoff_results = AsyncMock(return_value=final_results)
        service.promotion_service.apply_team_movements = AsyncMock()

        result = await service._process_promotion_relegation(season, movement_day)

        service.promotion_service.process_season_end.assert_awaited_once_with(season)
        service._process_playoff_results.assert_awaited_once_with(season, promotion_data)
        service.promotion_service.apply_team_movements.assert_awaited_once_with(
            final_results["final_promotions"],
            final_results["final_relegations"],
        )
        assert result["final_promotions"] == 1
        assert result["final_relegations"] == 1


@pytest.mark.asyncio
class TestProcessNextEventLifecycle:
    """process_next_event 生命周期测试"""
    
    async def test_returns_none_when_queue_empty(self, db):
        """队列为空时应返回 None"""
        service = SeasonService(db)
        result = await service.process_next_event()
        assert result is None
    
    async def test_processes_pending_event(self, db):
        """应处理 PENDING 事件并标记为 COMPLETED"""
        service = SeasonService(db)
        # 手动插入一个 SEASON_START 事件
        evt = await EventQueue.push(
            db, EventType.SEASON_START,
            payload={"season_id": "test-season"},
            scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        )
        
        result = await service.process_next_event()
        assert result is not None
        assert result["event"] == "season_start"
        
        # 验证数据库状态
        result = await db.execute(
            __import__("sqlalchemy").select(EventQueueModel).where(EventQueueModel.id == evt.id)
        )
        obj = result.scalar_one()
        assert obj.status == EventStatus.COMPLETED.value
    
    async def test_marks_failed_on_exception(self, db):
        """处理异常时应标记为 FAILED"""
        service = SeasonService(db)
        # 插入一个 MATCH_DAY 事件，指向不存在的 season（会触发 ValueError）
        evt = await EventQueue.push(
            db, EventType.MATCH_DAY,
            payload={"season_id": "no-such-season", "day": 0},
            scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        )
        
        with pytest.raises(ValueError):
            await service.process_next_event()
        
        result = await db.execute(
            __import__("sqlalchemy").select(EventQueueModel).where(EventQueueModel.id == evt.id)
        )
        obj = result.scalar_one()
        # 默认 max_retries=3，第一次失败会回到 PENDING；等待重试
        assert obj.status == EventStatus.PENDING.value
        assert obj.retry_count == 1
        assert obj.error_msg == "Season not found: no-such-season"


@pytest.mark.asyncio
class TestClockIntegration:
    """GameClock 与 SeasonService 集成测试"""
    
    async def test_step_mode_does_not_auto_advance(self, db):
        """step 模式下，不调用 tick 时间不应前进"""
        base = datetime(2025, 6, 1, 12, 0, 0)
        # 使用新的 GameClock 实例避免污染全局 clock
        from app.core.clock import GameClock
        test_clock = GameClock(mode="step", start_time=base)
        
        t1 = test_clock.now()
        # 真实时间流逝但虚拟时间冻结
        import time
        time.sleep(0.05)
        t2 = test_clock.now()
        assert t1 == t2 == base
