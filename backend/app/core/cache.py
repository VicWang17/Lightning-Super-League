"""
Redis 缓存/锁基础设施

自建 Redis client（不复用 dependencies.py 的单例，保持 core 层自包含）。
所有操作均降级容错：Redis 不可用时按 cache miss / no-op 处理，
锁在 Redis 不可用时 fail-open（等价于无锁），绝不影响主流程。
key 统一前缀 lsl:。
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

KEY_PREFIX = "lsl:"

cache_redis: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# Lua 脚本：仅当锁值与 token 一致时才删除，防止误删他人持有的锁
_RELEASE_LOCK_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


async def close_cache() -> None:
    """关闭缓存 Redis 连接（供应用 lifespan shutdown 调用）"""
    try:
        await cache_redis.close()
    except Exception as exc:
        logger.warning(f"close cache redis failed: {exc}")


async def cache_get_json(key: str) -> Optional[Any]:
    """读取 JSON 缓存，未命中或 Redis 不可用返回 None"""
    try:
        raw = await cache_redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.warning(f"cache get failed: key={key}, error={exc}")
        return None


async def cache_set_json(key: str, obj: Any, ttl: int) -> None:
    """写入 JSON 缓存，失败仅记录日志"""
    try:
        await cache_redis.set(key, json.dumps(obj, ensure_ascii=False, default=str), ex=ttl)
    except Exception as exc:
        logger.warning(f"cache set failed: key={key}, error={exc}")


async def cache_delete(*keys: str) -> None:
    """删除指定缓存 key，失败仅记录日志"""
    if not keys:
        return
    try:
        await cache_redis.delete(*keys)
    except Exception as exc:
        logger.warning(f"cache delete failed: keys={keys}, error={exc}")


async def cache_delete_pattern(pattern: str) -> None:
    """按 pattern 删除缓存 key（SCAN + DEL，本规模够用），失败仅记录日志"""
    try:
        async for key in cache_redis.scan_iter(match=pattern, count=200):
            await cache_redis.delete(key)
    except Exception as exc:
        logger.warning(f"cache delete pattern failed: pattern={pattern}, error={exc}")


async def acquire_lock(key: str, ttl_sec: int) -> Optional[str]:
    """获取分布式锁，成功返回 token，被占用或 Redis 不可用返回 None（fail-open 由调用方决定）"""
    token = uuid.uuid4().hex
    try:
        ok = await cache_redis.set(key, token, nx=True, ex=ttl_sec)
        return token if ok else None
    except Exception as exc:
        logger.warning(f"acquire lock failed (fail-open): key={key}, error={exc}")
        # Redis 不可用时 fail-open：返回 token 视同持锁（等价于现状无锁）
        return token


async def release_lock(key: str, token: Optional[str]) -> None:
    """释放分布式锁（校验 token），失败仅记录日志"""
    if not token:
        return
    try:
        await cache_redis.eval(_RELEASE_LOCK_SCRIPT, 1, key, token)
    except Exception as exc:
        logger.warning(f"release lock failed: key={key}, error={exc}")
