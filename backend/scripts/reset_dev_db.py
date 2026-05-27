"""Reset the current development database."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings


async def reset_dev_db() -> None:
    settings = get_settings()
    url = make_url(settings.DATABASE_URL)
    database = url.database
    if not database:
        raise RuntimeError("DATABASE_URL must include a database name")

    root_url = url.set(
        username=os.getenv("MYSQL_ROOT_USER", "root"),
        password=os.getenv("MYSQL_ROOT_PASSWORD", "root_password"),
        database="mysql",
    )
    try:
        await _recreate_database(root_url, database)
        print(f"✅ 已重建开发数据库: {database}")
        return
    except SQLAlchemyError as exc:
        print(f"⚠️ root 重建数据库失败，改为清空当前 schema: {exc.__class__.__name__}")

    tables = await _drop_all_tables(url)
    print(f"✅ 已清空开发数据库表: {len(tables)}")


async def _recreate_database(server_url, database: str) -> None:
    engine = create_async_engine(server_url, echo=False, future=True, isolation_level="AUTOCOMMIT")
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS `{database}`"))
        await conn.execute(text(f"CREATE DATABASE `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    await engine.dispose()


async def _drop_all_tables(database_url) -> list[str]:
    engine = create_async_engine(database_url, echo=False, future=True)
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
        """))
        tables = [row[0] for row in result.fetchall()]

        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    await engine.dispose()
    return tables


def main() -> None:
    env = os.getenv("ENV", "").lower()
    if env != "dev":
        raise RuntimeError("reset_dev_db only runs with ENV=dev")
    asyncio.run(reset_dev_db())


if __name__ == "__main__":
    main()
