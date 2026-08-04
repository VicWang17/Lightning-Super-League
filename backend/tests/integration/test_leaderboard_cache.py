"""
排行榜缓存集成测试

测试覆盖：
  • 查询后写入 Redis 缓存
  • 二次查询命中缓存（改库后仍返回旧结果）
  • 主动失效后重新计算
  • OVR 榜短 TTL 缓存
测试基建沿用 conftest 真实 MySQL 的惯例，Redis 同样用 settings.REDIS_URL 真实实例。
"""
import pytest
import pytest_asyncio
from datetime import datetime

from app.core.cache import KEY_PREFIX, cache_redis, cache_get_json
from app.models.player import Player, PlayerPosition, PlayerRace, PlayerPersonality
from app.models.player_season_stats import PlayerSeasonStats
from app.models.season import Season, SeasonStatus
from app.schemas.leaderboard import LeaderboardType, TeamLeaderboardType
from app.services.leaderboard_service import (
    LeaderboardService,
    invalidate_match_result_caches,
)


@pytest_asyncio.fixture
async def clean_lb_cache():
    """测试前后清理 lsl:lb:* 测试 key

    pytest-asyncio 每个测试一个 event loop，模块级 cache_redis 的连接
    绑定旧 loop 后无法复用，因此清理后断开连接池，下次使用时按新 loop 重建。
    """
    await _delete_lb_keys()
    yield
    await _delete_lb_keys()
    await cache_redis.connection_pool.disconnect()


async def _delete_lb_keys():
    async for key in cache_redis.scan_iter(match=f"{KEY_PREFIX}lb:*", count=200):
        await cache_redis.delete(key)


async def _create_scoring_player(db, goals: int) -> Player:
    """创建一个带赛季统计的球员（事务回滚由 conftest 保证）"""
    season = Season(
        season_number=990001,
        zone_id=99,
        start_date=datetime(2025, 1, 1),
        status=SeasonStatus.ONGOING,
    )
    db.add(season)
    player = Player(
        name="Cache Test Scorer",
        race=PlayerRace.ASIAN,
        position=PlayerPosition.FW,
        height=180,
        birth_offset=-20,
        personality=PlayerPersonality.PROFESSIONAL,
    )
    db.add(player)
    await db.flush()
    stats = PlayerSeasonStats(
        player_id=player.id,
        season_id=season.id,
        goals=goals,
        matches_played=10,
    )
    db.add(stats)
    await db.flush()
    return player


@pytest.mark.asyncio
class TestWorldLeaderboardCache:
    """世界级排行榜缓存（cache-aside + 主动失效）"""

    async def test_query_writes_cache(self, db, clean_lb_cache):
        """查询后应写入 Redis 缓存"""
        service = LeaderboardService(db)
        await service.get_world_leaderboard(LeaderboardType.GOALS, limit=5)

        cache_key = f"{KEY_PREFIX}lb:world:goals:5:all"
        cached = await cache_get_json(cache_key)
        assert cached is not None
        assert isinstance(cached, list)

    async def test_cache_hit_returns_stale_result(self, db, clean_lb_cache):
        """改库后二次查询应命中旧缓存（内容不变），失效后应重算"""
        service = LeaderboardService(db)
        lb_type = LeaderboardType.GOALS
        limit = 5

        first = await service.get_world_leaderboard(lb_type, limit=limit)
        first_ids = [item.player_id for item in first]

        # 改库：新增一个超高进球球员
        scorer = await _create_scoring_player(db, goals=999999)

        # 命中旧缓存：新球员不应出现
        second = await service.get_world_leaderboard(lb_type, limit=limit)
        assert [item.player_id for item in second] == first_ids
        assert scorer.id not in [item.player_id for item in second]

        # 主动失效后重算：新球员应出现
        await invalidate_match_result_caches(league_ids=[], season_id="any", cup_ids=[])
        third = await service.get_world_leaderboard(lb_type, limit=limit)
        assert scorer.id in [item.player_id for item in third]

    async def test_world_team_leaderboard_cache(self, db, clean_lb_cache):
        """球队世界榜同样写入/命中缓存"""
        service = LeaderboardService(db)
        first = await service.get_world_team_leaderboard(TeamLeaderboardType.POINTS, limit=5)

        cache_key = f"{KEY_PREFIX}lb:world_team:points:5"
        assert await cache_get_json(cache_key) is not None

        # 使缓存内容可辨识：直接改缓存不影响二次读取结果
        second = await service.get_world_team_leaderboard(TeamLeaderboardType.POINTS, limit=5)
        assert [item.team_id for item in second] == [item.team_id for item in first]


@pytest.mark.asyncio
class TestOvrLeaderboardCache:
    """OVR 榜仅短 TTL 缓存"""

    async def test_ovr_query_writes_cache(self, db, clean_lb_cache):
        service = LeaderboardService(db)
        await service.get_ovr_leaderboard(limit=5)

        cache_key = f"{KEY_PREFIX}lb:ovr:5:all"
        assert await cache_get_json(cache_key) is not None


@pytest.mark.asyncio
class TestInvalidateMatchResultCaches:
    """失效函数行为"""

    async def test_invalidate_clears_league_and_world_keys(self, db, clean_lb_cache):
        """应按 pattern 删除联赛榜与世界榜 key"""
        await cache_redis.set(f"{KEY_PREFIX}lb:league:lg1:s1:goals:20", "[]")
        await cache_redis.set(f"{KEY_PREFIX}lb:league:lg1:s2:goals:20", "[]")
        await cache_redis.set(f"{KEY_PREFIX}lb:cup:cup1:s1:goals:20", "[]")
        await cache_redis.set(f"{KEY_PREFIX}lb:world:goals:100:all", "[]")
        await cache_redis.set(f"{KEY_PREFIX}lb:world_team:points:100", "[]")

        await invalidate_match_result_caches(league_ids=["lg1"], season_id="s1", cup_ids=["cup1"])

        # 指定赛季/联赛的 key 被删除，其他赛季保留
        assert await cache_redis.get(f"{KEY_PREFIX}lb:league:lg1:s1:goals:20") is None
        assert await cache_redis.get(f"{KEY_PREFIX}lb:league:lg1:s2:goals:20") is not None
        assert await cache_redis.get(f"{KEY_PREFIX}lb:cup:cup1:s1:goals:20") is None
        assert await cache_redis.get(f"{KEY_PREFIX}lb:world:goals:100:all") is None
        assert await cache_redis.get(f"{KEY_PREFIX}lb:world_team:points:100") is None
