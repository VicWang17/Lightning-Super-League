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
