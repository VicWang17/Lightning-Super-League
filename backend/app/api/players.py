from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class Player(BaseModel):
    id: int
    name: str
    age: int
    position: str
    nationality: str
    team_id: Optional[int] = None
    overall_rating: int
    market_value: int

@router.get("/", response_model=List[Player])
async def get_players():
    # 模拟返回球员列表
    return [
        Player(id=1, name="莱昂内尔·梅西", age=36, position="RW", nationality="阿根廷", team_id=1, overall_rating=93, market_value=50000000),
        Player(id=2, name="克里斯蒂亚诺·罗纳尔多", age=38, position="ST", nationality="葡萄牙", team_id=2, overall_rating=91, market_value=45000000),
    ]

@router.get("/{player_id}", response_model=Player)
async def get_player(player_id: int):
    # 模拟返回特定球员信息
    return Player(id=player_id, name="莱昂内尔·梅西", age=36, position="RW", nationality="阿根廷", team_id=1, overall_rating=93, market_value=50000000) 