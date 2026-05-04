"""
赛季事件流集成测试 - Phase 5

测试覆盖：
  • create_new_season 自动生成 EventQueue 事件
  • 事件按 scheduled_at 顺序执行
  • MATCH_DAY 事件正确模拟当天比赛
  • SEASON_END 事件后赛季状态变为 FINISHED
  • process_next_day 兼容层正常工作
  • fast_forward 可跨越多天
"""
import pytest
from datetime import datetime, timedelta

from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus
from app.models.events import EventQueue as EventQueueModel
from app.services.season_service import SeasonService
from app.core.events import EventType, EventStatus
from app.core.clock import clock
from sqlalchemy import select, func


@pytest.mark.asyncio
class TestSeasonEventFlow:
    """赛季事件流端到端测试"""
    
    async def test_create_season_seeds_events(self, db):
        """创建赛季后应生成完整的事件队列"""
        service = SeasonService(db)
        start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        season = await service.create_new_season(start_date=start, zone_id=1)
        
        # 应写入事件
        result = await db.execute(
            select(EventQueueModel).where(
                EventQueueModel.payload.contains({"season_id": season.id})
            )
        )
        events = result.scalars().all()
        assert len(events) > 0
        
        types = {e.event_type for e in events}
        assert EventType.SEASON_START.value in types
        assert EventType.MATCH_DAY.value in types
        assert EventType.SEASON_END.value in types
    
    async def test_match_day_event_simulates_fixtures(self, db):
        """MATCH_DAY 事件应模拟当天所有比赛"""
        service = SeasonService(db)
        start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        season = await service.create_new_season(start_date=start, zone_id=1)
        await service.start_season(season)
        
        # 快进虚拟时间到赛季开始
        clock.set_mode("step")
        clock.fast_forward_to(start)
        
        # 处理 SEASON_START 事件
        result = await service.process_next_event(now=start)
        assert result["event"] == "season_start"
        
        # 处理第一个 MATCH_DAY
        result = await service.process_next_event(now=start)
        assert result["event"] == "match_day"
        assert result["fixtures_processed"] > 0
        
        # 验证比赛状态已更新
        day = result["season_day"]
        fixture_result = await db.execute(
            select(Fixture).where(
                Fixture.season_id == season.id,
                Fixture.season_day == day,
                Fixture.status == FixtureStatus.FINISHED,
            )
        )
        finished_fixtures = fixture_result.scalars().all()
        assert len(finished_fixtures) == result["fixtures_processed"]
    
    async def test_season_end_event_finishes_season(self, db):
        """SEASON_END 事件后赛季应变为 FINISHED"""
        service = SeasonService(db)
        start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        season = await service.create_new_season(start_date=start, zone_id=1)
        await service.start_season(season)
        
        # 快进虚拟时间到赛季结束
        end_date = start + timedelta(days=season.total_days)
        clock.set_mode("step")
        clock.fast_forward_to(end_date)
        
        # 处理所有事件直到结束
        processed = 0
        while processed < 200:  # 安全上限
            result = await service.process_next_event(now=end_date)
            if result is None:
                break
            processed += 1
            if result.get("event") == "season_end":
                break
        
        await db.refresh(season)
        assert season.status == SeasonStatus.FINISHED
        assert season.end_date is not None
    
    async def test_process_next_day_compatibility(self, db):
        """process_next_day 兼容层应正常工作"""
        service = SeasonService(db)
        start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        season = await service.create_new_season(start_date=start, zone_id=1)
        await service.start_season(season)
        
        clock.set_mode("step")
        clock.fast_forward_to(start)
        
        # 推进 3 天
        for _ in range(3):
            result = await service.process_next_day(season)
            assert result["fixtures_processed"] >= 0
            await db.refresh(season)
        
        assert season.current_day >= 3
    
    async def test_fast_forward_advances_multiple_days(self, db):
        """fast_forward 应能跨越多个比赛日"""
        service = SeasonService(db)
        start = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        season = await service.create_new_season(start_date=start, zone_id=1)
        await service.start_season(season)
        
        clock.set_mode("step")
        clock.fast_forward_to(start)
        
        target_day = 5
        results = await service.fast_forward(target_day, season)
        
        await db.refresh(season)
        assert season.current_day >= target_day
        assert len(results) > 0
