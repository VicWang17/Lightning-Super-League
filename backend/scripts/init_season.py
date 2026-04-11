"""
赛季初始化脚本 - Initialize Season

功能：
1. 创建新赛季（联赛+杯赛完整赛程）
2. 生成30轮联赛赛程（已随机打乱）
3. 生成闪电杯和杰尼杯赛程
4. 创建积分榜

用法:
    cd backend
    python -m scripts.init_season

注意:
    - 运行前需要先执行 init_system.py 初始化基础数据
    - 每个新赛季开始时都需要运行此脚本
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import get_settings
from app.models import (
    League, Team, Season, SeasonStatus,
    Fixture, FixtureType, FixtureStatus,
    CupCompetition, CupGroup, CupByeTeam,
    LeagueStanding
)
from app.services.scheduler import (
    LeagueScheduleGenerator, LightningCupGenerator,
    JennyCupGenerator, ScheduleMerger
)

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_next_season_number(db: AsyncSession) -> int:
    """获取下一个赛季编号"""
    result = await db.execute(
        select(Season).order_by(Season.season_number.desc())
    )
    last_season = result.scalar_one_or_none()
    return (last_season.season_number + 1) if last_season else 1


async def create_season(db: AsyncSession, season_number: int, start_date: datetime) -> Season:
    """创建赛季记录"""
    season = Season(
        season_number=season_number,
        start_date=start_date,
        status=SeasonStatus.PENDING,
        current_day=0,
        current_league_round=0,
        current_cup_round=0,
        total_days=42,
        league_days=30,
        cup_start_day=6,
        cup_interval=3,
        offseason_start=31
    )
    db.add(season)
    await db.flush()
    return season


async def create_cup_competitions(db: AsyncSession, season: Season) -> tuple:
    """创建杯赛定义"""
    # 闪电杯
    lightning_cup = CupCompetition(
        season_id=season.id,
        name="闪电杯",
        code="LIGHTNING_CUP",
        eligible_league_levels=[1],
        total_teams=64,
        has_group_stage=True,
        group_count=16,
        teams_per_group=4,
        group_rounds=3,
        current_round=0,
        status=SeasonStatus.PENDING,
        winner_team_id=None
    )
    db.add(lightning_cup)
    await db.flush()
    
    # 杰尼杯
    jenny_cup = CupCompetition(
        season_id=season.id,
        name="杰尼杯",
        code="JENNY_CUP",
        eligible_league_levels=[2, 3],
        total_teams=192,
        has_group_stage=False,
        group_count=0,
        teams_per_group=0,
        group_rounds=0,
        current_round=0,
        status=SeasonStatus.PENDING,
        winner_team_id=None
    )
    db.add(jenny_cup)
    await db.flush()
    
    return lightning_cup, jenny_cup


async def generate_league_schedules(db: AsyncSession, leagues: list) -> list:
    """生成联赛赛程"""
    print("\n🏆 生成联赛赛程（30轮，已随机打乱）...")
    
    league_schedules = []
    teams_by_league = {}
    
    for league in leagues:
        result = await db.execute(
            select(Team).where(Team.current_league_id == league.id)
        )
        teams = list(result.scalars().all())
        teams_by_league[league.id] = teams
        
        if len(teams) != 16:
            print(f"   ⚠️ 跳过 {league.name}: 只有{len(teams)}支球队")
            continue
        
        team_ids = [t.id for t in teams]
        schedule = LeagueScheduleGenerator.generate(team_ids, league.id)
        league_schedules.append(schedule)
        print(f"   ✅ {league.name}: 30轮")
    
    return league_schedules, teams_by_league


async def generate_cup_schedules(
    db: AsyncSession,
    lightning_cup: CupCompetition,
    jenny_cup: CupCompetition,
    leagues: list,
    teams_by_league: dict
) -> tuple:
    """生成杯赛赛程"""
    # 闪电杯
    print("\n⚡ 生成闪电杯赛程...")
    top_leagues = [l for l in leagues if l.level == 1]
    top_league_teams = [
        [t.id for t in teams_by_league.get(l.id, [])]
        for l in top_leagues
    ]
    top_league_teams = [teams for teams in top_league_teams if len(teams) == 16]
    
    lightning_schedule = None
    if len(top_league_teams) >= 4:
        lightning_schedule, cup_groups = LightningCupGenerator.generate(
            lightning_cup.id,
            top_league_teams[:4]
        )
        for group in cup_groups:
            db.add(group)
        print(f"   ✅ 16组小组赛 + 淘汰赛")
    else:
        print(f"   ⚠️ 只有{len(top_league_teams)}个完整顶级联赛，无法生成完整闪电杯")
    
    # 杰尼杯
    print("\n🏅 生成杰尼杯赛程...")
    tier2_leagues = [l for l in leagues if l.level == 2]
    tier3_leagues = [l for l in leagues if l.level == 3]
    tier2_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier2_leagues]
    tier3_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier3_leagues]
    tier2_teams = [teams for teams in tier2_teams if len(teams) == 16]
    tier3_teams = [teams for teams in tier3_teams if len(teams) == 16]
    
    jenny_schedule = None
    if len(tier2_teams) >= 4 and len(tier3_teams) >= 8:
        jenny_schedule = JennyCupGenerator.generate(
            jenny_cup.id,
            tier2_teams[:4],
            tier3_teams[:8]
        )
        for team_id in jenny_schedule.bye_team_ids:
            bye_team = CupByeTeam(
                competition_id=jenny_cup.id,
                team_id=team_id,
                round_number=2
            )
            db.add(bye_team)
        print(f"   ✅ 首轮64场 + {len(jenny_schedule.bye_team_ids)}支轮空")
    else:
        print(f"   ⚠️ 无法生成完整杰尼杯")
    
    return lightning_schedule, jenny_schedule


async def create_fixtures(
    db: AsyncSession,
    season: Season,
    start_date: datetime,
    league_schedules: list,
    lightning_schedule,
    jenny_schedule,
    lightning_cup: CupCompetition,
    jenny_cup: CupCompetition
) -> int:
    """创建比赛记录"""
    print("\n📝 创建比赛记录...")
    
    cup_ids = {"LIGHTNING": lightning_cup.id, "JENNY": jenny_cup.id}
    
    if not lightning_schedule:
        print("   ⚠️ 没有闪电杯赛程，无法创建比赛")
        return 0
    
    if not jenny_schedule:
        from app.services.scheduler import CupSchedule, RoundSchedule
        jenny_schedule = CupSchedule(jenny_cup.id, None, [RoundSchedule(i, []) for i in range(1, 9)])
    
    fixtures = ScheduleMerger.assign_dates(
        start_date,
        league_schedules,
        lightning_schedule,
        jenny_schedule,
        season.id,
        cup_ids
    )
    
    for fixture in fixtures:
        db.add(fixture)
    
    await db.flush()
    print(f"   ✅ 创建了 {len(fixtures)} 场比赛")
    return len(fixtures)


async def create_standings(db: AsyncSession, season: Season, leagues: list, teams_by_league: dict):
    """创建积分榜"""
    print("\n📊 创建积分榜...")
    
    standings_count = 0
    for league in leagues:
        teams = teams_by_league.get(league.id, [])
        for position, team in enumerate(teams, 1):
            standing = LeagueStanding(
                league_id=league.id,
                season_id=season.id,
                team_id=team.id,
                position=position,
                played=0,
                won=0,
                drawn=0,
                lost=0,
                goals_for=0,
                goals_against=0,
                goal_difference=0,
                points=0,
                form=None,
                is_promotion_zone=False,
                is_relegation_zone=False
            )
            db.add(standing)
            standings_count += 1
    
    await db.flush()
    print(f"   ✅ 创建了 {standings_count} 条积分榜记录")


async def init_season():
    """初始化赛季主函数"""
    async with AsyncSessionLocal() as db:
        # 检查是否已有进行中的赛季
        result = await db.execute(
            select(Season).where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"⚠️ 已有进行中的赛季: 第{existing.season_number}赛季")
            response = input("   是否继续创建新赛季? (y/N): ")
            if response.lower() != 'y':
                print("已取消")
                return None
        
        # 获取所有联赛
        result = await db.execute(select(League))
        leagues = list(result.scalars().all())
        
        if len(leagues) < 16:
            print(f"❌ 联赛数量不足: 只有{len(leagues)}个联赛，需要16个")
            print("   请先运行: python -m scripts.init_system")
            return None
        
        # 确定赛季编号和开始日期
        season_number = await get_next_season_number(db)
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"\n📅 创建第{season_number}赛季...")
        print(f"   开始日期: {start_date.strftime('%Y-%m-%d')}")
        
        # 1. 创建赛季
        season = await create_season(db, season_number, start_date)
        print(f"   ✅ 赛季记录创建成功")
        
        # 2. 创建杯赛
        lightning_cup, jenny_cup = await create_cup_competitions(db, season)
        print(f"   ✅ 闪电杯和杰尼杯创建成功")
        
        # 3. 生成联赛赛程
        league_schedules, teams_by_league = await generate_league_schedules(db, leagues)
        
        # 4. 生成杯赛赛程
        lightning_schedule, jenny_schedule = await generate_cup_schedules(
            db, lightning_cup, jenny_cup, leagues, teams_by_league
        )
        
        # 5. 创建比赛记录
        fixtures_count = await create_fixtures(
            db, season, start_date, league_schedules,
            lightning_schedule, jenny_schedule,
            lightning_cup, jenny_cup
        )
        
        # 6. 创建积分榜
        await create_standings(db, season, leagues, teams_by_league)
        
        # 7. 启动赛季
        season.status = SeasonStatus.ONGOING
        await db.commit()
        
        print(f"\n🚀 第{season_number}赛季已启动！")
        return season


async def show_season_info(season: Season):
    """显示赛季信息"""
    if not season:
        return
    
    print("\n" + "=" * 60)
    print("📊 赛季信息")
    print("=" * 60)
    print(f"赛季编号: 第{season.season_number}赛季")
    print(f"状态: {season.status.value}")
    print(f"开始日期: {season.start_date.strftime('%Y-%m-%d')}")
    print(f"当前天数: 第{season.current_day}天")
    print(f"联赛天数: {season.league_days}天")
    print(f"总天数: {season.total_days}天")
    print("=" * 60)


async def main():
    """主函数"""
    print("=" * 60)
    print("⚡ 闪电超级联赛 - 赛季初始化")
    print("=" * 60)
    
    try:
        season = await init_season()
        await show_season_info(season)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await engine.dispose()
    
    print("\n✅ 赛季初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
