"""
Pytest configuration
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()

# Use NullPool to avoid connection loop binding issues across tests
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True, poolclass=NullPool)
AsyncTestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    """Create test engine"""
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db(db_engine):
    """Create a fresh transaction for each test and rollback after"""
    async with db_engine.connect() as conn:
        trans = await conn.begin()
        async_session = AsyncTestSession(bind=conn)
        try:
            yield async_session
        finally:
            await trans.rollback()
            await async_session.close()


@pytest_asyncio.fixture(autouse=True)
async def _reset_cache_pool():
    """每个测试后断开缓存 Redis 连接池

    pytest-asyncio 每个测试一个 event loop，模块级 cache_redis 池中的连接
    绑定创建时的 loop，跨测试复用会报错；断开后下次使用时按当前 loop 重建。
    """
    yield
    try:
        from app.core.cache import cache_redis
        await cache_redis.connection_pool.disconnect()
    except Exception:
        pass
