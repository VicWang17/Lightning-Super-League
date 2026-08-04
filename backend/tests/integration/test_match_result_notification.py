"""
MATCH_RESULT_NOTIFICATION 事件集成测试

测试覆盖：
  • push 事件 → process_next_event → 主客队结果邮件异步落库
  • 事件处理后标记为 COMPLETED
Redis 使用 settings.REDIS_URL 真实实例（与真实 MySQL 同一惯例）。
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta

from sqlalchemy import select, func

from app.core.cache import cache_redis
from app.core.events import EventQueue, EventType, EventStatus
from app.models.events import EventQueue as EventQueueModel
from app.models.mail import Mail, MailCategory
from app.models.season import Season, SeasonStatus
from app.models.team import Team
from app.models.user import User
from app.services.season_service import SeasonService


@pytest_asyncio.fixture
async def clean_test_keys():
    """测试后清理本测试产生的缓存 key，并断开连接池以跨 event loop 复用"""
    yield
    async for key in cache_redis.scan_iter(match="lsl:mail:unread:*", count=200):
        await cache_redis.delete(key)
    await cache_redis.connection_pool.disconnect()


async def _create_user_with_team(db, suffix: str) -> tuple[User, Team]:
    user = User(
        username=f"notify_user_{suffix}",
        email=f"notify_user_{suffix}@example.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    team = Team(name=f"Notify Team {suffix}", user_id=user.id)
    db.add(team)
    await db.flush()
    return user, team


@pytest.mark.asyncio
class TestMatchResultNotification:
    """比赛结果邮件异步通知事件"""

    async def test_push_then_process_sends_mails(self, db, clean_test_keys):
        """push → process_next_event → 主客各一封结果邮件落库"""
        home_user, home_team = await _create_user_with_team(db, "home")
        away_user, away_team = await _create_user_with_team(db, "away")
        season = Season(
            season_number=990002,
            zone_id=99,
            start_date=datetime(2025, 1, 1),
            status=SeasonStatus.ONGOING,
        )
        db.add(season)
        await db.flush()

        fixture_id = "fixture-notify-test"
        await EventQueue.push(
            db,
            EventType.MATCH_RESULT_NOTIFICATION,
            payload={
                "season_id": season.id,
                "fixture_id": fixture_id,
                "home_team_id": home_team.id,
                "away_team_id": away_team.id,
                "home_team_name": home_team.name,
                "away_team_name": away_team.name,
                "home_score": 2,
                "away_score": 1,
                "fixture_type": "league",
                "goals": [{"minute": 10, "player_name": "测试球员"}],
                "yellow_cards": 1,
                "red_cards": 0,
                "mvp_name": "测试球员",
                "injuries": [],
            },
            scheduled_at=datetime.utcnow() - timedelta(seconds=1),
        )

        service = SeasonService(db)
        result = await service.process_next_event()
        assert result is not None
        assert result["event"] == "match_result_notification"
        assert result["fixture_id"] == fixture_id

        # 主客各一封邮件落库
        mails_result = await db.execute(
            select(Mail).where(Mail.related_id == fixture_id)
        )
        mails = list(mails_result.scalars().all())
        assert len(mails) == 2
        assert {m.user_id for m in mails} == {home_user.id, away_user.id}
        assert all(m.category == MailCategory.MATCH_RESULT for m in mails)
        assert all("【比赛结果】" in m.subject for m in mails)

        # 事件已标记 COMPLETED
        evt_result = await db.execute(
            select(func.count(EventQueueModel.id)).where(
                EventQueueModel.event_type == EventType.MATCH_RESULT_NOTIFICATION.value,
                EventQueueModel.status == EventStatus.COMPLETED.value,
            )
        )
        assert evt_result.scalar() == 1
