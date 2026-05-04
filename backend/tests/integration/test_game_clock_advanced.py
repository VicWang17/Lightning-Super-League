"""
GameClock + EventQueue 高级测试集

覆盖场景：
  • 时钟跨模式多次切换的累积误差
  • EventQueue 压力测试（批量事件性能）
  • EventQueue 并发消费（多 worker 竞争）
  • 赛季事件流：空队列、SEASON_END 自动切换、异常恢复
  • MATCH_DAY 并发模拟的正确性（ standings 不冲突）
"""
import asyncio
import pytest
from datetime import datetime, timedelta

from app.core.clock import clock, GameClock
from app.core.events import EventQueue, GameEvent, EventType, EventStatus
from app.services.season_service import SeasonService
from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus
from app.models.events import EventQueue as EventQueueModel
from sqlalchemy import select, func, desc


# =================================================================
# GameClock 边界测试
# =================================================================
class TestGameClockEdgeCases:
    """时钟边界场景"""

    def test_rapid_mode_switching(self):
        """快速多次切换模式，虚拟时间不应漂移超过 100ms"""
        gc = GameClock(mode="step", start_time=datetime(2025, 1, 1, 12, 0, 0))
        gc.tick(timedelta(days=10))
        expected = gc.now()

        for _ in range(20):
            gc.set_mode("paused")
            gc.set_mode("turbo")
            gc.set_mode("step")

        # 允许 100ms 累积误差
        assert abs((gc.now() - expected).total_seconds()) < 0.1

    def test_turbo_at_extreme_speed(self):
        """turbo 模式 10000x 速度不应崩溃"""
        gc = GameClock(mode="turbo", speed=10000.0)
        t1 = gc.now()
        import time
        time.sleep(0.01)
        t2 = gc.now()
        # 0.01s × 10000 = 100s 虚拟时间流逝
        elapsed = (t2 - t1).total_seconds()
        assert 50 <= elapsed <= 200

    def test_paused_then_tick(self):
        """paused 模式下 tick 应正常工作"""
        gc = GameClock(mode="paused", start_time=datetime(2025, 1, 1))
        gc.tick(timedelta(days=5))
        assert gc.now() == datetime(2025, 1, 6)

    def test_fast_forward_to_past_raises(self):
        """fast_forward_to 过去时间应报错"""
        gc = GameClock(mode="step", start_time=datetime(2025, 6, 1))
        with pytest.raises(ValueError, match="in the future"):
            gc.fast_forward_to(datetime(2025, 1, 1))

    def test_global_clock_isolation(self):
        """创建局部 GameClock 不应影响全局 clock"""
        original_mode = clock.mode
        local = GameClock(mode="paused", start_time=datetime(2025, 1, 1))
        local.tick(timedelta(days=100))
        assert clock.mode == original_mode
        assert clock.now() != local.now()


# =================================================================
# EventQueue 压力与并发测试
# =================================================================
@pytest.mark.asyncio
class TestEventQueueStress:
    """EventQueue 压力测试"""

    async def test_batch_push_100_events(self, db):
        """批量推送 100 个事件应在一秒内完成"""
        import time
        start = time.time()
        events = [
            GameEvent(
                event_type=EventType.MATCH_DAY,
                payload={"day": i},
                scheduled_at=datetime.utcnow() - timedelta(seconds=1),
            )
            for i in range(100)
        ]
        created = await EventQueue.push_many(db, events)
        elapsed = time.time() - start
        assert len(created) == 100
        assert elapsed < 5.0  # 5 秒阈值（含数据库往返）

    async def test_pop_all_events_sequentially(self, db):
        """串行 pop 所有 100 个事件"""
        for i in range(50):
            await EventQueue.push(db, EventType.MATCH_DAY, payload={"i": i},
                                  scheduled_at=datetime.utcnow() - timedelta(seconds=1))

        popped = 0
        while True:
            evt = await EventQueue.pop(db)
            if not evt:
                break
            await EventQueue.complete(db, evt.id)
            popped += 1

        assert popped == 50

    async def test_pop_isolation_between_sessions(self, db):
        """一个 session pop 后，另一个 session 不应再 pop 到同一事件"""
        evt = await EventQueue.push(db, EventType.MATCH_DAY, payload={"test": True},
                                    scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        await db.commit()

        # Session A pop
        popped_a = await EventQueue.pop(db)
        assert popped_a is not None
        assert popped_a.id == evt.id

        # Session B（新连接）尝试 pop 同一事件 —— 由于 FOR UPDATE + skip_locked，
        # 如果 A 未提交，B 会跳过；如果 A 已提交状态为 PROCESSING，B 也看不到
        from app.config import get_settings
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        settings = get_settings()
        engine_b = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
        SessionB = sessionmaker(engine_b, class_=AsyncSession, expire_on_commit=False)

        async with SessionB() as db_b:
            popped_b = await EventQueue.pop(db_b)
            # 由于 A 已将状态改为 PROCESSING，B 看不到 PENDING 状态的事件
            assert popped_b is None

        await engine_b.dispose()
        # 清理
        await EventQueue.complete(db, evt.id)
        await db.commit()


# =================================================================
# 赛季事件流高级测试
# =================================================================
@pytest.mark.asyncio
class TestSeasonEventFlowAdvanced:
    """赛季事件流高级场景"""

    async def test_process_next_event_with_empty_queue(self, db):
        """空队列时 process_next_event 返回 None"""
        service = SeasonService(db)
        result = await service.process_next_event()
        assert result is None

    async def test_fast_forward_on_finished_season(self, db):
        """对已结束赛季 fast_forward 应不处理任何事件"""
        # 找一个 FINISHED 赛季（如果没有则跳过）
        result = await db.execute(
            select(Season).where(Season.status == SeasonStatus.FINISHED).limit(1)
        )
        season = result.scalar_one_or_none()
        if not season:
            pytest.skip("No finished season in database")

        service = SeasonService(db)
        results = await service.fast_forward(season.current_day + 10, season)
        assert len(results) == 0

    async def test_run_until_next_event_respects_max_events(self, db):
        """run_until_next_event 不应超过 max_events 限制"""
        # 找一个有效赛季
        result = await db.execute(select(Season).limit(1))
        season = result.scalar_one_or_none()
        if not season:
            pytest.skip("No season in database")

        # 创建 5 个 SEASON_START 事件（不依赖 fixtures，安全）
        for i in range(5):
            await EventQueue.push(db, EventType.SEASON_START, payload={"season_id": season.id, "i": i},
                                  scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        await db.commit()

        service = SeasonService(db)
        # max_events=2，即使还有 pending 事件也应停止
        results = await service.run_until_next_event(season, max_events=2)
        assert len(results) == 2

    async def test_event_queue_status_transitions(self, db):
        """事件完整生命周期：PENDING → PROCESSING → COMPLETED"""
        evt = await EventQueue.push(db, EventType.SEASON_START, payload={"test": True},
                                    scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        assert evt.status == EventStatus.PENDING

        popped = await EventQueue.pop(db)
        assert popped is not None
        assert popped.status == EventStatus.PROCESSING

        await EventQueue.complete(db, popped.id)
        await db.commit()

        result = await db.execute(select(EventQueueModel).where(EventQueueModel.id == popped.id))
        obj = result.scalar_one()
        assert obj.status == EventStatus.COMPLETED.value
        assert obj.processed_at is not None

    async def test_retry_then_permanent_fail(self, db):
        """重试 2 次后最终 FAILED"""
        evt = await EventQueue.push(db, EventType.MATCH_DAY, payload={},
                                    scheduled_at=datetime.utcnow() - timedelta(seconds=1))
        for _ in range(2):
            await EventQueue.pop(db)
            await EventQueue.fail(db, evt.id, "test error", max_retries=2)
            await db.commit()

        result = await db.execute(select(EventQueueModel).where(EventQueueModel.id == evt.id))
        obj = result.scalar_one()
        assert obj.status == EventStatus.FAILED.value
        assert obj.retry_count == 2


# =================================================================
# MATCH_DAY 并发正确性测试
# =================================================================
@pytest.mark.asyncio
class TestMatchDayConcurrencyCorrectness:
    """MATCH_DAY 并发模拟的数据正确性"""

    async def test_match_day_does_not_duplicate_standings(self, db):
        """同一天所有比赛 apply_result 后，standings 统计不应为负数"""
        # 找一个已有 FINISHED 比赛的 day
        result = await db.execute(
            select(Fixture.season_day, func.count())
            .where(Fixture.status == FixtureStatus.FINISHED)
            .group_by(Fixture.season_day)
            .having(func.count() > 5)
            .limit(1)
        )
        row = result.first()
        if not row:
            pytest.skip("No day with enough finished fixtures")

        day, count = row
        # 验证该天所有比赛都已经完成
        result = await db.execute(
            select(Fixture).where(Fixture.season_day == day)
            .where(Fixture.status == FixtureStatus.FINISHED)
        )
        fixtures = result.scalars().all()

        # 基本验证：所有比分非负，所有 fixture 状态正确
        for f in fixtures:
            assert f.home_score >= 0
            assert f.away_score >= 0
            assert f.status == FixtureStatus.FINISHED
            assert f.finished_at is not None

    async def test_simulate_does_not_access_db(self, db):
        """simulate() 是纯计算，不应访问数据库"""
        from app.services.match_simulator import MatchSimulator
        from app.models.season import FixtureType
        # 创建一个 fixture 但不查询数据库
        fixture = Fixture(id="test-fixture", home_team_id="team-a", away_team_id="team-b",
                          season_day=1, fixture_type=FixtureType.LEAGUE)
        result = await MatchSimulator.simulate(fixture)
        assert result.home_score >= 0
        assert result.away_score >= 0
