"""
球员短词描述回填脚本

为数据库中所有缺少 short_description 的球员生成画像短语并写入数据库。
支持 --regenerate-all 强制重新生成所有球员描述。

运行方式:
    cd backend && python -m scripts.backfill_player_descriptions
    cd backend && python -m scripts.backfill_player_descriptions --regenerate-all
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.player import Player
from app.services.player_description_service import PlayerDescriptionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回填或重新生成球员短词描述")
    parser.add_argument(
        "--regenerate-all",
        action="store_true",
        help="强制为所有球员重新生成描述（不仅是空字段）",
    )
    return parser.parse_args()


async def backfill_descriptions(db: AsyncSession, regenerate_all: bool = False, batch_size: int = 200) -> int:
    """为所有缺少描述的球员生成 short_description。"""
    print("📝 开始回填球员短词描述...")

    service = PlayerDescriptionService()
    total_updated = 0

    if regenerate_all:
        result = await db.execute(select(Player))
    else:
        result = await db.execute(select(Player).where(Player.short_description.is_(None)))
    players = list(result.scalars().all())

    for i, player in enumerate(players):
        player.short_description = service.generate(player)
        total_updated += 1

        if (i + 1) % batch_size == 0:
            await db.commit()
            print(f"   已处理 {i + 1}/{len(players)} 名球员...")

    await db.commit()
    print(f"✅ 回填完成，共更新 {total_updated} 名球员")
    return total_updated


async def main():
    args = parse_args()
    db_gen = get_db()
    db = await anext(db_gen)

    try:
        await backfill_descriptions(db, regenerate_all=args.regenerate_all)
    except Exception as e:
        print(f"❌ 回填失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
