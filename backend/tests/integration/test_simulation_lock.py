"""
模拟幂等锁集成测试

测试覆盖：
  • simulate_match：锁被占用时返回 409，释放后可进入正常流程
  • _handle_match_day：比赛日锁被占用时直接 raise（走 EventQueue.fail 重试退避）
Redis 使用 settings.REDIS_URL 真实实例（与真实 MySQL 同一惯例）。
"""
import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.core.cache import KEY_PREFIX, acquire_lock, release_lock, cache_redis
from app.core.events import EventType, GameEvent
from app.routers.matches import simulate_match
from app.services.season_service import SeasonService


@pytest_asyncio.fixture
async def clean_locks():
    """测试前后清理锁 key，并断开连接池以跨 event loop 复用"""
    await _delete_locks()
    yield
    await _delete_locks()
    await cache_redis.connection_pool.disconnect()


async def _delete_locks():
    async for key in cache_redis.scan_iter(match=f"{KEY_PREFIX}lock:*", count=200):
        await cache_redis.delete(key)


@pytest.mark.asyncio
class TestSimulateMatchLock:
    """单场模拟幂等锁"""

    async def test_conflict_when_lock_held(self, db, clean_locks):
        """锁被占用时第二个请求应 409"""
        lock_key = f"{KEY_PREFIX}lock:fixture:fixture-lock-test"
        token = await acquire_lock(lock_key, ttl_sec=120)
        assert token is not None

        with pytest.raises(HTTPException) as exc_info:
            await simulate_match(match_id="fixture-lock-test", db=db)
        assert exc_info.value.status_code == 409

    async def test_proceeds_after_release(self, db, clean_locks):
        """释放锁后可再进入模拟流程（此处fixture不存在，应走到 404 而非 409）"""
        lock_key = f"{KEY_PREFIX}lock:fixture:fixture-lock-test"
        token = await acquire_lock(lock_key, ttl_sec=120)
        await release_lock(lock_key, token)

        with pytest.raises(HTTPException) as exc_info:
            await simulate_match(match_id="fixture-lock-test", db=db)
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestMatchDayLock:
    """比赛日级幂等锁"""

    async def test_raises_when_lock_held(self, db, clean_locks):
        """比赛日锁被占用时应直接 raise（由 EventQueue.fail 走重试退避）"""
        lock_key = f"{KEY_PREFIX}lock:matchday:season-lock-test:1"
        token = await acquire_lock(lock_key, ttl_sec=300)
        assert token is not None

        service = SeasonService(db)
        event = GameEvent(
            event_type=EventType.MATCH_DAY,
            payload={"season_id": "season-lock-test", "day": 1},
        )
        with pytest.raises(RuntimeError, match="比赛日正在处理中"):
            await service._handle_match_day(event)

    async def test_raises_season_not_found_after_release(self, db, clean_locks):
        """释放锁后应进入正常处理流程（此处赛季不存在，报 Season not found 而非锁冲突）"""
        service = SeasonService(db)
        event = GameEvent(
            event_type=EventType.MATCH_DAY,
            payload={"season_id": "season-lock-test", "day": 1},
        )
        with pytest.raises(ValueError, match="Season not found"):
            await service._handle_match_day(event)
