from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter()

class Team(BaseModel):
    id: int
    name: str
    manager_id: int
    reputation: int
    league_id: int

@router.get("/", response_model=List[Team])
async def get_teams():
    # 模拟返回球队列表
    return [
        Team(id=1, name="皇家马德里", manager_id=1, reputation=95, league_id=1),
        Team(id=2, name="巴塞罗那", manager_id=2, reputation=94, league_id=1),
    ]

@router.get("/{team_id}", response_model=Team)
async def get_team(team_id: int):
    # 模拟返回特定球队信息
    return Team(id=team_id, name="皇家马德里", manager_id=1, reputation=95, league_id=1) 