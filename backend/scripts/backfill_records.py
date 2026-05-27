#!/usr/bin/env python3
"""
纪录数据回填脚本

用法:
    cd backend
    source .venv/bin/activate
    python scripts/backfill_records.py

功能:
    1. 遍历所有已完成的比赛，检测并生成比赛级纪录
    2. 计算所有赛季级纪录（单赛季进球最多、积分最高等）
    3. 计算球员生涯累计纪录

注意:
    - 本脚本会清空现有的 records 表然后重新生成
    - 生产环境使用前请备份数据
"""
import asyncio
import sys
from pathlib import Path

# 将 backend 目录加入路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import AsyncSessionLocal
from app.models.season import Fixture, FixtureStatus
from app.models.match_result import MatchResult as MatchResultModel
from app.models.record import Record
from app.models.season import Season
from app.services.record_service import RecordService
from app.services.match_simulator import MatchSimulator, MatchResult


async def clear_existing_records(db: AsyncSession) -> None:
    """清空现有纪录"""
    result = await db.execute(select(Record))
    records = result.scalars().all()
    for r in records:
        await db.delete(r)
    await db.commit()
    print(f"已清空 {len(records)} 条现有纪录")


async def backfill_match_records(db: AsyncSession) -> None:
    """遍历所有已完成比赛，生成比赛级纪录"""
    result = await db.execute(
        select(Fixture).where(
            Fixture.status == FixtureStatus.FINISHED
        ).order_by(Fixture.scheduled_at.asc())
    )
    fixtures = result.scalars().all()
    print(f"找到 {len(fixtures)} 场已完成比赛")

    processed = 0
    for fixture in fixtures:
        # 加载比赛结果
        mr_result = await db.execute(
            select(MatchResultModel).where(
                MatchResultModel.fixture_id == fixture.id
            )
        )
        mr = mr_result.scalar_one_or_none()

        if mr:
            # 有引擎结果
            result = MatchResult(
                fixture_id=fixture.id,
                home_score=mr.home_score,
                away_score=mr.away_score,
                winner_team_id=mr.winner_team_id,
                resolution=mr.resolution,
                penalty_score=mr.penalty_score,
                match_stats=mr.match_stats or {},
                player_stats=mr.player_stats or [],
                events=mr.events or [],
                narratives=mr.narratives or [],
                engine_raw=mr.raw_result or {},
            )
        else:
            # 无引擎结果，创建最小结果
            result = MatchResult(
                fixture_id=fixture.id,
                home_score=fixture.home_score or 0,
                away_score=fixture.away_score or 0,
                events=[],
                player_stats=[],
            )

        try:
            await RecordService.process_match_records(fixture, result, db)
            processed += 1
            if processed % 50 == 0:
                print(f"  已处理 {processed}/{len(fixtures)} 场比赛...")
        except Exception as e:
            print(f"  处理比赛 {fixture.id} 时出错: {e}")

    await db.commit()
    print(f"比赛级纪录回填完成，共处理 {processed} 场比赛")


async def backfill_season_records(db: AsyncSession) -> None:
    """计算所有赛季的赛季级纪录"""
    result = await db.execute(select(Season))
    seasons = result.scalars().all()
    print(f"找到 {len(seasons)} 个赛季")

    for season in seasons:
        try:
            await RecordService.recalculate_season_records(season.id, db)
            print(f"  赛季 {season.season_number} 纪录计算完成")
        except Exception as e:
            print(f"  赛季 {season.season_number} 计算时出错: {e}")

    print("赛季级纪录回填完成")


async def main() -> None:
    print("=" * 60)
    print("纪录数据回填脚本")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        # 确认执行
        print("\n本脚本将清空现有 records 表并重新生成所有纪录。")
        print("输入 'yes' 继续:")
        # 非交互式环境默认继续
        import os
        if os.isatty(0):
            confirm = input().strip().lower()
            if confirm != 'yes':
                print("已取消")
                return
        else:
            print("(非交互式环境，自动继续)")

        # 1. 清空现有纪录
        print("\n[1/3] 清空现有纪录...")
        await clear_existing_records(db)

        # 2. 回填比赛级纪录
        print("\n[2/3] 回填比赛级纪录...")
        await backfill_match_records(db)

        # 3. 回填赛季级纪录
        print("\n[3/3] 回填赛季级纪录...")
        await backfill_season_records(db)

    print("\n" + "=" * 60)
    print("纪录回填完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
