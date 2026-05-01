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
    CupCompetition, CupGroup,
    LeagueStanding
)
from app.services.scheduler import (
    LeagueScheduleGenerator, LightningCupGenerator,
    JennyCupGenerator, ScheduleMerger
)
from app.core.formats import get_default_format

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
    fmt = get_default_format()
    template = fmt.season
    
    season = Season(
        season_number=season_number,
        start_date=start_date,
        status=SeasonStatus.PENDING,
        current_day=0,
        current_league_round=0,
        current_cup_round=0,
        total_days=template.total_days,
        league_days=len(template.league_days),
        cup_start_day=template.lightning_cup_days[0] if template.lightning_cup_days else 4,
        cup_interval=2,
        offseason_start=template.playoff_days[0] if template.playoff_days else 22
    )
    db.add(season)
    await db.flush()
    return season


async def create_cup_competitions(db: AsyncSession, season: Season) -> tuple:
    """创建杯赛定义"""
    fmt = get_default_format()
    cup_config = fmt.cup
    
    # 闪电杯
    lightning_cup = CupCompetition(
        season_id=season.id,
        name="闪电杯",
        code="LIGHTNING_CUP",
        eligible_league_levels=list(cup_config.lightning_eligible_levels),
        total_teams=cup_config.lightning_total_teams,
        has_group_stage=cup_config.lightning_has_group_stage,
        group_count=cup_config.lightning_group_count,
        teams_per_group=cup_config.lightning_teams_per_group,
        group_rounds=cup_config.lightning_group_rounds,
        current_round=0,
        status=SeasonStatus.PENDING,
        winner_team_id=None
    )
    db.add(lightning_cup)
    await db.flush()
    
    # 杰尼杯（各体系独立）
    jenny_cups = []
    systems = fmt.structure.system_codes
    for system_code in systems:
        jenny_cup = CupCompetition(
            season_id=season.id,
            name=f"杰尼杯-{system_code}",
            code=f"JENNY_CUP_{system_code}",
            eligible_league_levels=list(cup_config.jenny_eligible_levels),
            total_teams=cup_config.jenny_preliminary_teams + cup_config.jenny_seed_teams,
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
        jenny_cups.append((system_code, jenny_cup))
    
    return lightning_cup, jenny_cups


async def generate_league_schedules(db: AsyncSession, leagues: list) -> list:
    """生成联赛赛程"""
    fmt = get_default_format()
    league_config = fmt.league
    
    print(f"\n🏆 生成联赛赛程（{league_config.total_rounds}轮{league_config.round_robin_type}循环，已随机打乱）...")
    
    league_schedules = []
    teams_by_league = {}
    
    for league in leagues:
        result = await db.execute(
            select(Team).where(Team.current_league_id == league.id)
        )
        teams = list(result.scalars().all())
        teams_by_league[league.id] = teams
        
        if len(teams) != league_config.teams_per_league:
            print(f"   ⚠️ 跳过 {league.name}: 只有{len(teams)}支球队")
            continue
        
        team_ids = [t.id for t in teams]
        schedule = LeagueScheduleGenerator.generate(team_ids, league.id, league_config)
        league_schedules.append(schedule)
        print(f"   ✅ {league.name}: {league_config.total_rounds}轮")
    
    return league_schedules, teams_by_league


async def generate_cup_schedules(
    db: AsyncSession,
    lightning_cup: CupCompetition,
    jenny_cups: list,
    leagues: list,
    teams_by_league: dict
) -> tuple:
    """生成杯赛赛程"""
    fmt = get_default_format()
    cup_config = fmt.cup
    league_config = fmt.league
    structure = fmt.structure
    
    # 闪电杯
    print("\n⚡ 生成闪电杯赛程...")
    top_leagues = [l for l in leagues if l.level in cup_config.lightning_eligible_levels]
    top_league_teams = [
        [t.id for t in teams_by_league.get(l.id, [])]
        for l in top_leagues
    ]
    top_league_teams = [teams for teams in top_league_teams if len(teams) == league_config.teams_per_league]
    
    lightning_schedule = None
    cup_groups = []
    num_systems = len(structure.system_codes)
    if len(top_league_teams) >= num_systems:
        lightning_schedule, cup_groups = LightningCupGenerator.generate(
            lightning_cup.id,
            top_league_teams[:num_systems],
            cup_config
        )
        for group in cup_groups:
            db.add(group)
        total_rounds = cup_config.lightning_group_rounds + cup_config.lightning_knockout_rounds
        print(f"   ✅ {cup_config.lightning_group_count}组小组赛 + 淘汰赛，共{total_rounds}轮")
    else:
        print(f"   ⚠️ 只有{len(top_league_teams)}个完整顶级联赛，无法生成完整闪电杯")
    
    # 杰尼杯（各体系独立）
    print(f"\n🏅 生成杰尼杯赛程（{num_systems}个体系）...")
    jenny_cup_schedules = []
    
    expected_tier3 = league_config.teams_per_league * structure.levels[2]
    expected_tier4 = league_config.teams_per_league * structure.levels[3]
    
    for system_code, jenny_cup in jenny_cups:
        system_name = structure.system_names.get(system_code, system_code)
        system_leagues = [l for l in leagues if system_name in l.name]
        
        tier2 = [l for l in system_leagues if l.level == cup_config.jenny_seed_level]
        tier3 = [l for l in system_leagues if l.level in cup_config.jenny_eligible_levels and l.level == 3]
        tier4 = [l for l in system_leagues if l.level in cup_config.jenny_eligible_levels and l.level == 4]
        
        tier2_teams = []
        for l in tier2:
            tier2_teams.extend([t.id for t in teams_by_league.get(l.id, [])])
        
        tier3_teams = []
        for l in tier3:
            tier3_teams.extend([t.id for t in teams_by_league.get(l.id, [])])
        
        tier4_teams = []
        for l in tier4:
            tier4_teams.extend([t.id for t in teams_by_league.get(l.id, [])])
        
        if (len(tier2_teams) == cup_config.jenny_seed_teams and
            len(tier3_teams) == expected_tier3 and
            len(tier4_teams) == expected_tier4):
            
            tier3_sublists = [
                tier3_teams[i * league_config.teams_per_league:(i + 1) * league_config.teams_per_league]
                for i in range(structure.levels[2])
            ]
            tier4_sublists = [
                tier4_teams[i * league_config.teams_per_league:(i + 1) * league_config.teams_per_league]
                for i in range(structure.levels[3])
            ]
            
            jenny_schedule = JennyCupGenerator.generate(
                jenny_cup.id,
                system_code,
                tier2_teams,
                tier3_sublists,
                tier4_sublists,
                cup_config
            )
            jenny_cup_schedules.append(jenny_schedule)
            total_jenny = cup_config.jenny_preliminary_teams + cup_config.jenny_seed_teams
            print(f"   ✅ {system_code}: 预选赛{cup_config.jenny_preliminary_teams}队 + {cup_config.jenny_seed_teams}种子，共{cup_config.jenny_total_rounds}轮")
        else:
            print(f"   ⚠️ {system_code}: 球队数量不足，跳过")
    
    return lightning_schedule, jenny_cup_schedules


async def create_fixtures(
    db: AsyncSession,
    season: Season,
    start_date: datetime,
    league_schedules: list,
    lightning_schedule,
    jenny_cup_schedules: list,
    lightning_cup: CupCompetition,
    jenny_cups: list
) -> int:
    """创建比赛记录"""
    print("\n📝 创建比赛记录...")
    
    cup_ids = {"LIGHTNING": lightning_cup.id}
    for system_code, jenny_cup in jenny_cups:
        cup_ids[f"JENNY_{system_code}"] = jenny_cup.id
    
    if not lightning_schedule:
        print("   ⚠️ 没有闪电杯赛程，无法创建比赛")
        return 0
    
    fixtures = ScheduleMerger.assign_dates(
        start_date,
        league_schedules,
        lightning_schedule,
        jenny_cup_schedules,
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
        
        if len(leagues) < 32:
            print(f"❌ 联赛数量不足: 只有{len(leagues)}个联赛，需要32个")
            print("   请先运行: python -m scripts.init_system")
            return None
        
        # 确定赛季编号和开始日期
        season_number = await get_next_season_number(db)
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"\n📅 创建第{season_number}赛季...")
        print(f"   开始日期: {start_date.strftime('%Y-%m-%d')}")
        print(f"   赛季时长: 26天（14轮联赛 + 杯赛 + 附加赛）")
        
        # 1. 创建赛季
        season = await create_season(db, season_number, start_date)
        print(f"   ✅ 赛季记录创建成功")
        
        # 2. 创建杯赛
        lightning_cup, jenny_cups = await create_cup_competitions(db, season)
        print(f"   ✅ 闪电杯（全服）+ 4个杰尼杯（体系内）创建成功")
        
        # 3. 生成联赛赛程
        league_schedules, teams_by_league = await generate_league_schedules(db, leagues)
        
        # 4. 生成杯赛赛程
        lightning_schedule, jenny_cup_schedules = await generate_cup_schedules(
            db, lightning_cup, jenny_cups, leagues, teams_by_league
        )
        
        # 5. 创建比赛记录
        fixtures_count = await create_fixtures(
            db, season, start_date, league_schedules,
            lightning_schedule, jenny_cup_schedules,
            lightning_cup, jenny_cups
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
    print(f"联赛: 14轮双循环")
    print(f"闪电杯: 8组小组赛 + 淘汰赛（7轮）")
    print(f"杰尼杯: 4个体系各自进行（预选赛+5轮）")
    print(f"升降级附加赛: 赛季结束后2天")
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
