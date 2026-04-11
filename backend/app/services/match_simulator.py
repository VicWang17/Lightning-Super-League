"""
Match simulator interface - 比赛模拟接口
"""
import random
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.season import Fixture, FixtureStatus, FixtureType
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
