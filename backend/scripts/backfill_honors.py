"""
荣誉数据回填脚本
遍历所有已结束赛季，为联赛冠军和杯赛冠军补录荣誉记录

运行方式:
    cd backend && python -m scripts.backfill_honors
"""
import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Season, SeasonStatus, LeagueStanding, League, CupCompetition
from app.models.team_honor import TeamHonor, HonorType
from app.services.honor_service import HonorService


async def backfill_league_champions(db: AsyncSession):
    """回填联赛冠军荣誉"""
    print("🏆 开始回填联赛冠军荣誉...")

    # 获取所有已结束赛季
    result = await db.execute(
        select(Season).where(Season.status == SeasonStatus.FINISHED)
    )
    seasons = result.scalars().all()

    total = 0
    for season in seasons:
        # 查询该赛季所有联赛的冠军（position=1）
        champions_result = await db.execute(
            select(LeagueStanding, League)
            .join(League, LeagueStanding.league_id == League.id)
            .where(LeagueStanding.season_id == season.id)
            .where(LeagueStanding.position == 1)
        )

        for standing, league in champions_result.all():
            # 检查是否已存在
            existing = await db.execute(
                select(TeamHonor).where(
                    and_(
                        TeamHonor.team_id == standing.team_id,
                        TeamHonor.season_id == season.id,
                        TeamHonor.honor_type == HonorType.LEAGUE_CHAMPION,
                        TeamHonor.competition_id == league.id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            honor = TeamHonor(
                team_id=standing.team_id,
                season_id=season.id,
                honor_type=HonorType.LEAGUE_CHAMPION,
                competition_id=league.id,
                competition_name=league.name,
                competition_level=league.level,
            )
            db.add(honor)
            total += 1

    await db.commit()
    print(f"  ✅ 联赛冠军荣誉已回填: {total} 条")
    return total


async def backfill_cup_champions(db: AsyncSession):
    """回填杯赛冠军荣誉"""
    print("🏆 开始回填杯赛冠军荣誉...")

    # 获取所有有冠军的杯赛
    result = await db.execute(
        select(CupCompetition, Season)
        .join(Season, CupCompetition.season_id == Season.id)
        .where(CupCompetition.winner_team_id.isnot(None))
    )
    rows = result.all()

    total = 0
    for comp, season in rows:
        # 检查是否已存在
        existing = await db.execute(
            select(TeamHonor).where(
                and_(
                    TeamHonor.team_id == comp.winner_team_id,
                    TeamHonor.season_id == season.id,
                    TeamHonor.honor_type == HonorType.CUP_CHAMPION,
                    TeamHonor.competition_id == comp.id,
                )
            )
        )
        if existing.scalar_one_or_none():
            continue

        honor = TeamHonor(
            team_id=comp.winner_team_id,
            season_id=season.id,
            honor_type=HonorType.CUP_CHAMPION,
            competition_id=comp.id,
            competition_name=comp.name,
            competition_level=0,
        )
        db.add(honor)
        total += 1

    await db.commit()
    print(f"  ✅ 杯赛冠军荣誉已回填: {total} 条")
    return total


async def main():
    """主函数"""
    print("=" * 50)
    print("📝 球队荣誉数据回填工具")
    print("=" * 50)

    db_gen = get_db()
    db = await anext(db_gen)

    try:
        league_count = await backfill_league_champions(db)
        cup_count = await backfill_cup_champions(db)

        print("=" * 50)
        print(f"🎉 回填完成！总计: {league_count + cup_count} 条荣誉记录")
        print("=" * 50)

    except Exception as e:
        print(f"❌ 回填失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
