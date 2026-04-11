"""
Create standings for existing season - 为现有赛季创建积分榜

用法:
    cd backend
    python -m scripts.create_standings
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.models import League, Team, Season, SeasonStatus, LeagueStanding


async def create_standings():
    """为现有赛季创建积分榜"""
    
    async with AsyncSessionLocal() as db:
        # 1. 获取当前赛季
        result = await db.execute(
            select(Season).where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
        )
        season = result.scalar_one_or_none()
        
        if not season:
            print("❌ 没有找到进行中的赛季")
            return
        
        print(f"📅 找到赛季: 第{season.season_number}赛季 (ID: {season.id})")
        
        # 2. 检查是否已有积分榜
        result = await db.execute(
            select(LeagueStanding).where(LeagueStanding.season_id == season.id)
        )
        existing = list(result.scalars().all())
        
        if existing:
            print(f"✅ 已有 {len(existing)} 条积分榜记录，无需创建")
            return
        
        # 3. 获取所有联赛
        result = await db.execute(select(League))
        leagues = list(result.scalars().all())
        print(f"📊 找到 {len(leagues)} 个联赛")
        
        # 4. 获取所有球队
        result = await db.execute(select(Team))
        teams = list(result.scalars().all())
        print(f"⚽ 找到 {len(teams)} 支球队")
        
        # 5. 按联赛分组球队
        teams_by_league = {}
        for team in teams:
            if team.current_league_id not in teams_by_league:
                teams_by_league[team.current_league_id] = []
            teams_by_league[team.current_league_id].append(team)
        
        # 6. 为每个联赛创建积分榜
        standings_count = 0
        for league in leagues:
            league_teams = teams_by_league.get(league.id, [])
            
            if not league_teams:
                print(f"  ⚠️  {league.name}: 没有球队")
                continue
            
            for position, team in enumerate(league_teams, 1):
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
            
            print(f"  ✅ {league.name}: {len(league_teams)} 支球队")
        
        # 7. 提交
        await db.commit()
        print(f"\n🎉 成功创建 {standings_count} 条积分榜记录！")


if __name__ == "__main__":
    print("=== 创建积分榜 ===\n")
    asyncio.run(create_standings())
    print("\n=== 完成 ===")
