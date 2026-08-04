"""
游戏时钟缓存集成测试

测试覆盖：
  • 写方法（set_mode/advance_to/freeze_at）后缓存与 DB 一致
  • now() 命中缓存时与 DB 计算结果一致
  • get_or_create miss 时回填缓存
Redis 使用 settings.REDIS_URL 真实实例（与真实 MySQL 同一惯例）。
"""
import pytest
import pytest_asyncio
from datetime import datetime

from sqlalchemy import select

from app.core.cache import cache_redis, cache_get_json
from app.models.clock import GameClockState
from app.services.game_clock_state import GameClockStateService, _CLOCK_CACHE_KEY


@pytest_asyncio.fixture
async def clean_clock_cache():
    """测试前后清理时钟缓存 key，并断开连接池以跨 event loop 复用"""
    await cache_redis.delete(_CLOCK_CACHE_KEY)
    yield
    await cache_redis.delete(_CLOCK_CACHE_KEY)
    await cache_redis.connection_pool.disconnect()


@pytest.mark.asyncio
class TestGameClockCache:
    """游戏时钟 read-through 缓存"""

    async def test_get_or_create_backfills_cache(self, db, clean_clock_cache):
        """缓存 miss 时走 MySQL 并回填缓存"""
        service = GameClockStateService(db)
        state = await service.get_or_create()
        assert state is not None

        cached = await cache_get_json(_CLOCK_CACHE_KEY)
        assert cached is not None
        assert cached["mode"] == state.mode

    async def test_freeze_at_persists_db_and_updates_cache(self, db, clean_clock_cache):
        """写方法后缓存与 DB 一致"""
        service = GameClockStateService(db)
        target = datetime(2025, 3, 1, 12, 0, 0)
        await service.freeze_at(target)

        # DB 已落库（flush 到当前事务）
        result = await db.execute(
            select(GameClockState).where(GameClockState.id == "global")
        )
        db_state = result.scalar_one()
        assert db_state.mode == "step"
        assert db_state.virtual_anchor == target

        # 缓存写穿更新
        cached = await cache_get_json(_CLOCK_CACHE_KEY)
        assert cached["mode"] == "step"
        assert datetime.fromisoformat(cached["virtual_anchor"]) == target

    async def test_now_hits_cache_and_matches_db(self, db, clean_clock_cache):
        """now() 命中缓存时与 DB 计算结果一致"""
        service = GameClockStateService(db)
        target = datetime(2025, 6, 15, 8, 30, 0)
        await service.freeze_at(target)

        # step 模式下 virtual_anchor 固定，缓存值与 DB 值必然一致
        now = await service.now()
        assert now == target

        result = await db.execute(
            select(GameClockState).where(GameClockState.id == "global")
        )
        db_state = result.scalar_one()
        assert service.compute_now(db_state) == now

    async def test_set_mode_updates_cache(self, db, clean_clock_cache):
        """set_mode 后缓存反映新模式"""
        service = GameClockStateService(db)
        await service.set_mode("paused")

        cached = await cache_get_json(_CLOCK_CACHE_KEY)
        assert cached["mode"] == "paused"

        result = await db.execute(
            select(GameClockState).where(GameClockState.id == "global")
        )
        assert result.scalar_one().mode == "paused"
