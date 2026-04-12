"""
Match simulator interface - 比赛模拟接口
"""
import random
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.season import Fixture, FixtureStatus, FixtureType, CupGroup
from app.services.standing_service import StandingService


@dataclass
class MatchResult:
    """比赛结果"""
    fixture_id: str
    home_score: int
    away_score: int
    home_possession: Optional[int] = None
    away_possession: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    mvp_player_id: Optional[str] = None
    events: Optional[list] = None  # 比赛事件（进球、红黄牌等）


class MatchSimulator:
    """比赛模拟器"""
    
    @staticmethod
    async def simulate(fixture: Fixture) -> MatchResult:
        """模拟单场比赛 - 纯随机比分"""
        home_score = random.randint(0, 4)
        away_score = random.randint(0, 4)
        
        return MatchResult(
            fixture_id=fixture.id,
            home_score=home_score,
            away_score=away_score,
            home_possession=random.randint(40, 60),
            away_possession=100 - random.randint(40, 60),
            home_shots=random.randint(5, 20),
            away_shots=random.randint(5, 20),
            home_shots_on_target=random.randint(2, 10),
            away_shots_on_target=random.randint(2, 10),
            mvp_player_id=None,
            events=[]
        )
    
    @staticmethod
    async def apply_result(
        fixture: Fixture, 
        result: MatchResult, 
        db: AsyncSession = None
    ) -> None:
        """将比赛结果应用到Fixture并更新积分榜"""
        fixture.home_score = result.home_score
        fixture.away_score = result.away_score
        fixture.status = FixtureStatus.FINISHED
        fixture.finished_at = datetime.utcnow()
        
        # 更新积分榜（联赛比赛）
        if db and fixture.fixture_type == FixtureType.LEAGUE:
            standing_service = StandingService(db)
            await standing_service.update_from_fixture(fixture)
            # 重新计算排名
            await standing_service.recalculate_positions(
                fixture.league_id, fixture.season_id
            )
        
        # 更新杯赛小组赛积分榜
        if db and fixture.fixture_type == FixtureType.CUP_LIGHTNING_GROUP:
            await MatchSimulator._update_cup_group_standing(fixture, db)
    
    @staticmethod
    async def _update_cup_group_standing(fixture: Fixture, db: AsyncSession) -> None:
        """更新杯赛小组赛小组积分榜"""
        if not fixture.cup_competition_id or not fixture.cup_group_name:
            return
        
        # 获取小组信息
        result = await db.execute(
            select(CupGroup).where(
                and_(
                    CupGroup.competition_id == fixture.cup_competition_id,
                    CupGroup.name == fixture.cup_group_name
                )
            )
        )
        group = result.scalar_one_or_none()
        
        if not group:
            return
        
        # 初始化或获取现有积分榜
        standings = group.standings or {}
        
        # 确保每个球队都有积分榜记录
        for team_id in [fixture.home_team_id, fixture.away_team_id]:
            if team_id not in standings:
                standings[team_id] = {
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0
                }
        
        home_standing = standings[fixture.home_team_id]
        away_standing = standings[fixture.away_team_id]
        
        # 更新比赛场次
        home_standing["played"] += 1
        away_standing["played"] += 1
        
        # 更新进球数
        home_standing["goals_for"] += fixture.home_score
        home_standing["goals_against"] += fixture.away_score
        away_standing["goals_for"] += fixture.away_score
        away_standing["goals_against"] += fixture.home_score
        
        # 计算胜负平
        if fixture.home_score > fixture.away_score:
            home_standing["won"] += 1
            home_standing["points"] += 3
            away_standing["lost"] += 1
        elif fixture.home_score < fixture.away_score:
            away_standing["won"] += 1
            away_standing["points"] += 3
            home_standing["lost"] += 1
        else:
            home_standing["drawn"] += 1
            home_standing["points"] += 1
            away_standing["drawn"] += 1
            away_standing["points"] += 1
        
        # 保存更新后的积分榜
        group.standings = standings
        await db.flush()
