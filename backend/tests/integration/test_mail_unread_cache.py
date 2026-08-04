"""
邮件未读数缓存集成测试

测试覆盖：
  • 查询后写入缓存，命中时返回一致结果
  • 发邮件（send_mail / send_mail_to_human_teams）后未读数缓存失效重算
  • 已读（详情自动已读 / 批量已读 / 全部已读）后缓存失效
Redis 使用 settings.REDIS_URL 真实实例（与真实 MySQL 同一惯例）。
"""
import pytest
import pytest_asyncio

from app.core.cache import cache_redis, cache_get_json
from app.models.mail import MailCategory, MailPriority
from app.models.team import Team
from app.models.user import User
from app.routers.mail import get_mail, get_unread_count, mark_all_read, mark_read
from app.schemas.mail import MarkReadRequest
from app.services.notification_service import (
    NotificationService,
    mail_unread_cache_key,
)


@pytest_asyncio.fixture
async def clean_mail_cache():
    """测试前后清理邮件缓存 key，并断开连接池以跨 event loop 复用"""
    await _delete_mail_keys()
    yield
    await _delete_mail_keys()
    await cache_redis.connection_pool.disconnect()


async def _delete_mail_keys():
    async for key in cache_redis.scan_iter(match="lsl:mail:*", count=200):
        await cache_redis.delete(key)


async def _create_user_with_team(db, suffix: str) -> tuple[User, Team]:
    user = User(
        username=f"cache_user_{suffix}",
        email=f"cache_user_{suffix}@example.com",
        hashed_password="x",
    )
    db.add(user)
    await db.flush()
    team = Team(name=f"Cache Team {suffix}", user_id=user.id)
    db.add(team)
    await db.flush()
    return user, team


@pytest.mark.asyncio
class TestMailUnreadCache:
    """未读数缓存（查询结果缓存 + 写路径主动失效）"""

    async def test_query_writes_cache_and_hit_is_consistent(self, db, clean_mail_cache):
        """查询后写入缓存；缓存命中时返回一致结果"""
        user, team = await _create_user_with_team(db, "hit")
        notify = NotificationService(db)
        await notify.send_mail(
            team_id=team.id,
            season_id=None,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="系统",
            subject="测试邮件",
            body="正文",
        )
        await db.flush()

        first = await get_unread_count(current_user=user, db=db)
        assert first.data.total == 1
        assert first.data.by_category == {"system": 1}
        assert await cache_get_json(mail_unread_cache_key(user.id)) is not None

        # 直接改库（绕过失效），命中缓存应返回一致的旧结果
        from app.models.mail import Mail
        db.add(Mail(user_id=user.id, team_id=team.id, category=MailCategory.SYSTEM,
                    subject="绕过缓存的邮件", body="x"))
        await db.flush()

        second = await get_unread_count(current_user=user, db=db)
        assert second.data.total == first.data.total
        assert second.data.by_category == first.data.by_category

    async def test_send_mail_invalidates_cache(self, db, clean_mail_cache):
        """发邮件后未读数缓存失效并重算"""
        user, team = await _create_user_with_team(db, "send")
        notify = NotificationService(db)

        first = await get_unread_count(current_user=user, db=db)
        assert first.data.total == 0

        await notify.send_mail(
            team_id=team.id,
            season_id=None,
            category=MailCategory.FINANCE,
            priority=MailPriority.NORMAL,
            sender_name="财务官",
            subject="工资单",
            body="正文",
        )
        await db.flush()

        # send_mail 已失效缓存，重新查询应看到新邮件
        assert await cache_get_json(mail_unread_cache_key(user.id)) is None
        second = await get_unread_count(current_user=user, db=db)
        assert second.data.total == 1
        assert second.data.by_category == {"finance": 1}

    async def test_send_mail_to_human_teams_invalidates_cache(self, db, clean_mail_cache):
        """批量发邮件按收件人失效缓存"""
        user, team = await _create_user_with_team(db, "batch")
        notify = NotificationService(db)

        await get_unread_count(current_user=user, db=db)
        assert await cache_get_json(mail_unread_cache_key(user.id)) is not None

        sent = await notify.send_mail_to_human_teams(
            team_ids=[team.id],
            season_id=None,
            category=MailCategory.SPONSOR,
            priority=MailPriority.NORMAL,
            sender_name="赞助商",
            subject="合同",
            body="正文",
        )
        assert sent == 1
        assert await cache_get_json(mail_unread_cache_key(user.id)) is None

    async def test_read_paths_invalidate_cache(self, db, clean_mail_cache):
        """详情自动已读 / 批量已读 / 全部已读均失效缓存"""
        user, team = await _create_user_with_team(db, "read")
        notify = NotificationService(db)
        mails = []
        for i in range(3):
            mail = await notify.send_mail(
                team_id=team.id,
                season_id=None,
                category=MailCategory.SYSTEM,
                priority=MailPriority.NORMAL,
                sender_name="系统",
                subject=f"邮件{i}",
                body="正文",
            )
            mails.append(mail)
        await db.flush()

        # 1) 详情自动已读
        await get_unread_count(current_user=user, db=db)
        await get_mail(mail_id=mails[0].id, current_user=user, db=db)
        assert await cache_get_json(mail_unread_cache_key(user.id)) is None
        resp = await get_unread_count(current_user=user, db=db)
        assert resp.data.total == 2

        # 2) 批量已读
        await mark_read(request=MarkReadRequest(mail_ids=[mails[1].id]), current_user=user, db=db)
        assert await cache_get_json(mail_unread_cache_key(user.id)) is None
        resp = await get_unread_count(current_user=user, db=db)
        assert resp.data.total == 1

        # 3) 全部已读
        await mark_all_read(category=None, current_user=user, db=db)
        assert await cache_get_json(mail_unread_cache_key(user.id)) is None
        resp = await get_unread_count(current_user=user, db=db)
        assert resp.data.total == 0
