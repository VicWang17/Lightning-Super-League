from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class Match(BaseModel):
    id: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    match_date: datetime
    status: str  # scheduled, in_progress, finished

@router.get("/", response_model=List[Match])
async def get_matches():
    # 模拟返回比赛列表
    return [
        Match(
            id=1,
            home_team_id=1,
            away_team_id=2,
            home_team_name="皇家马德里",
            away_team_name="巴塞罗那",
            home_score=2,
            away_score=1,
            match_date=datetime.now(),
            status="finished"
        ),
    ]

@router.get("/{match_id}", response_model=Match)
async def get_match(match_id: int):
    # 模拟返回特定比赛信息
    return Match(
        id=match_id,
        home_team_id=1,
        away_team_id=2,
        home_team_name="皇家马德里",
        away_team_name="巴塞罗那",
        home_score=2,
        away_score=1,
        match_date=datetime.now(),
        status="finished"
    ) 