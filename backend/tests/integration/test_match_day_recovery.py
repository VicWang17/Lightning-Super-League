"""
比赛日事务2崩溃后重试的自愈集成测试

场景：事务 1 已将 fixtures 持久化为 ONGOING，事务 2（apply_result 循环）中途异常。
重试时当天没有 SCHEDULED fixtures，若不自愈比赛日会空跑完成、
fixtures 永远卡在 ONGOING。修复后应重置回 SCHEDULED 并重新走模拟流程。
"""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from app.core.events import EventType, GameEvent
from app.models.season import Season, SeasonStatus, Fixture, FixtureType, FixtureStatus
from app.models.team import Team
from app.models.user import User
from app.services.season_service import SeasonService


async def _create_user_with_team(db, suffix: str) -> tuple[User, Team]:
    user = User(
        username=f"recovery_user_{suffix}",
        email=f"recovery_user_{suffix}@example.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    team = Team(name=f"Recovery Team {suffix}", user_id=user.id)
    db.add(team)
    await db.flush()
    return user, team


@pytest.mark.asyncio
class TestMatchDayRecovery:
    """ONGOING 残留 fixtures 的自愈重置"""

    async def test_stale_ongoing_fixtures_are_reset_and_re_simulated(self, db):
        """事务2崩溃残留 ONGOING → 重试应重置为 SCHEDULED 并重新模拟，而非空跑"""
        _, home_team = await _create_user_with_team(db, "home")
        _, away_team = await _create_user_with_team(db, "away")
        season = Season(
            season_number=990003,
            zone_id=99,
            start_date=datetime(2025, 1, 1),
            status=SeasonStatus.ONGOING,
        )
        db.add(season)
        await db.flush()
        fixture = Fixture(
            season_id=season.id,
            fixture_type=FixtureType.LEAGUE,
            season_day=1,
            scheduled_at=datetime(2025, 1, 1, 20, 0, 0),
            round_number=1,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=FixtureStatus.ONGOING,  # 模拟事务 1 commit 后事务 2 崩溃的残留
        )
        db.add(fixture)
        await db.flush()

        sim_result = MagicMock(
            player_stats=[], events=[], home_score=1, away_score=0, engine_raw={}
        )
        statuses_at_engine_call = []

        async def fake_simulate(fixtures):
            # 引擎调用发生在事务 1 的 ONGOING 更新之前，
            # 此时自愈逻辑应已把残留重置为 SCHEDULED
            statuses_at_engine_call.extend(f.status for f in fixtures)
            return [sim_result for _ in fixtures]

        service = SeasonService(db)
        service._simulate_fixtures_with_engine = AsyncMock(side_effect=fake_simulate)
        service.simulator.apply_result = AsyncMock()

        event = GameEvent(
            event_type=EventType.MATCH_DAY,
            payload={"season_id": season.id, "day": 1},
        )
        result = await service._process_match_day(event, season.id, 1)

        # 残留 fixture 被重置为 SCHEDULED 后重新进入模拟流程（不是空跑）
        assert statuses_at_engine_call == [FixtureStatus.SCHEDULED]
        service._simulate_fixtures_with_engine.assert_awaited_once()
        service.simulator.apply_result.assert_awaited_once()
        assert result["fixtures_processed"] == 1
        assert result["results"][0]["fixture_id"] == fixture.id
        assert result["results"][0]["home_score"] == 1

        # 事务 1 重新将其置为 ONGOING（apply_result 被 mock，故停留在此状态）
        assert fixture.status == FixtureStatus.ONGOING

    async def test_empty_day_without_stale_fixtures_completes_as_noop(self, db):
        """当天既没有 SCHEDULED 也没有 ONGOING 残留时，正常空跑完成"""
        season = Season(
            season_number=990004,
            zone_id=99,
            start_date=datetime(2025, 1, 1),
            status=SeasonStatus.ONGOING,
        )
        db.add(season)
        await db.flush()

        service = SeasonService(db)
        service._simulate_fixtures_with_engine = AsyncMock(return_value=[])

        event = GameEvent(
            event_type=EventType.MATCH_DAY,
            payload={"season_id": season.id, "day": 1},
        )
        result = await service._process_match_day(event, season.id, 1)
        assert result["fixtures_processed"] == 0
