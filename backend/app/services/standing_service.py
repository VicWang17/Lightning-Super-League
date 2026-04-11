"""
Standing service - 积分榜服务
负责积分榜的更新、排名计算、升降级标记
"""
from typing import Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, asc

from app.models.league import LeagueStanding, League, LeagueSystem
from app.models.season import Season, Fixture, FixtureType
from app.models.team import Team


class StandingService:
    """积分榜服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_standing(
        self, 
        league_id: str, 
        season_id: str, 
        team_id: str
    ) -> LeagueStanding:
        """获取或创建积分榜记录"""
        result = await self.db.execute(
            select(LeagueStanding)
            .where(LeagueStanding.league_id == league_id)
            .where(LeagueStanding.season_id == season_id)
            .where(LeagueStanding.team_id == team_id)
        )
        standing = result.scalar_one_or_none()
        
        if not standing:
            standing = LeagueStanding(
                league_id=league_id,
                season_id=season_id,
                team_id=team_id,
                position=0,
                played=0,
                won=0,
                drawn=0,
                lost=0,
                goals_for=0,
                goals_against=0,
                goal_difference=0,
                points=0
            )
            self.db.add(standing)
            await self.db.flush()
        
        return standing
    
    async def update_from_fixture(self, fixture: Fixture) -> None:
        """根据比赛结果更新积分榜"""
        if fixture.fixture_type != FixtureType.LEAGUE:
            return  # 只更新联赛积分榜
        
        if fixture.home_score is None or fixture.away_score is None:
            return  # 比赛未结束
        
        # 获取主客场球队的积分榜记录
        home_standing = await self.get_or_create_standing(
            fixture.league_id, fixture.season_id, fixture.home_team_id
        )
        away_standing = await self.get_or_create_standing(
            fixture.league_id, fixture.season_id, fixture.away_team_id
        )
        
        # 更新比赛场次
        home_standing.played += 1
        away_standing.played += 1
        
        # 更新进球数
        home_standing.goals_for += fixture.home_score
        home_standing.goals_against += fixture.away_score
        away_standing.goals_for += fixture.away_score
        away_standing.goals_against += fixture.home_score
        
        # 计算胜负平
        if fixture.home_score > fixture.away_score:
            # 主场胜
            home_standing.won += 1
            home_standing.points += 3
            away_standing.lost += 1
        elif fixture.home_score < fixture.away_score:
            # 客场胜
            away_standing.won += 1
            away_standing.points += 3
            home_standing.lost += 1
        else:
            # 平局
            home_standing.drawn += 1
            home_standing.points += 1
            away_standing.drawn += 1
            away_standing.points += 1
        
        # 计算净胜球
        home_standing.goal_difference = home_standing.goals_for - home_standing.goals_against
        away_standing.goal_difference = away_standing.goals_for - away_standing.goals_against
        
        await self.db.flush()
    
    async def recalculate_positions(self, league_id: str, season_id: str) -> None:
        """重新计算排名"""
        # 获取该联赛该赛季的所有积分榜记录，按积分、净胜球、进球数排序
        result = await self.db.execute(
            select(LeagueStanding)
            .where(LeagueStanding.league_id == league_id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(
                desc(LeagueStanding.points),
                desc(LeagueStanding.goal_difference),
                desc(LeagueStanding.goals_for)
            )
        )
        standings = result.scalars().all()
        
        # 更新排名
        for i, standing in enumerate(standings, 1):
            standing.position = i
        
        await self.db.flush()
    
    async def get_standings(
        self, 
        league_id: str, 
        season_id: str
    ) -> List[LeagueStanding]:
        """获取积分榜（已排序）"""
        result = await self.db.execute(
            select(LeagueStanding)
            .where(LeagueStanding.league_id == league_id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(asc(LeagueStanding.position))
        )
        return list(result.scalars().all())
    
    async def get_league_standings_with_team_names(
        self, 
        league_id: str, 
        season_id: str
    ) -> List[dict]:
        """获取积分榜（包含球队名称）"""
        standings = await self.get_standings(league_id, season_id)
        
        # 获取球队名称
        team_ids = [s.team_id for s in standings]
        result = await self.db.execute(
            select(Team).where(Team.id.in_(team_ids))
        )
        teams = {t.id: t for t in result.scalars().all()}
        
        return [
            {
                "position": s.position,
                "team_id": s.team_id,
                "team_name": teams.get(s.team_id, Team(name="未知球队")).name,
                "played": s.played,
                "won": s.won,
                "drawn": s.drawn,
                "lost": s.lost,
                "goals_for": s.goals_for,
                "goals_against": s.goals_against,
                "goal_difference": s.goal_difference,
                "points": s.points
            }
            for s in standings
        ]
    
    async def get_all_leagues_standings(
        self, 
        season_id: str
    ) -> dict:
        """获取所有联赛的积分榜"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(League).options(selectinload(League.system))
        )
        leagues = result.scalars().all()
        
        all_standings = {}
        for league in leagues:
            standings = await self.get_league_standings_with_team_names(
                league.id, season_id
            )
            all_standings[league.name] = {
                "league_id": league.id,
                "level": league.level,
                "system": league.system.code if league.system else "未知",
                "standings": standings
            }
        
        return all_standings
    
    async def reset_standings_for_season(self, season_id: str) -> None:
        """重置赛季积分榜（用于新赛季）"""
        result = await self.db.execute(
            select(LeagueStanding).where(LeagueStanding.season_id == season_id)
        )
        standings = result.scalars().all()
        
        for standing in standings:
            standing.played = 0
            standing.won = 0
            standing.drawn = 0
            standing.lost = 0
            standing.goals_for = 0
            standing.goals_against = 0
            standing.goal_difference = 0
            standing.points = 0
            standing.position = 0
        
        await self.db.flush()
