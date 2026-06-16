"""
World API routes - 世界排名与全球数据接口
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import ResponseSchema
from app.schemas.records import (
    RecordsByCategory,
    RecordCategory as RecordCategoryEnum,
    RecordScope as RecordScopeEnum,
)
from app.services.honor_service import HonorService
from app.services.leaderboard_service import LeaderboardService
from app.routers.records import list_records
from app.schemas.leaderboard import (
    LeaderboardType,
    LeaderboardItem,
    TeamLeaderboardType,
    TeamLeaderboardItem,
)

router = APIRouter(prefix="/world", tags=["世界"])


@router.get(
    "/rankings",
    response_model=ResponseSchema[list],
    summary="获取世界排名",
    description="获取所有球队的世界排名，基于近3个赛季联赛加权积分 + 杯赛冠军积分",
)
async def get_world_rankings(
    db: AsyncSession = Depends(get_db),
):
    """获取世界排名列表"""
    service = HonorService(db)
    rankings = await service.calculate_world_rankings()
    return ResponseSchema(success=True, data=rankings)


@router.get(
    "/top-players",
    response_model=ResponseSchema[list],
    summary="获取球员OVR排名",
    description="获取球员按OVR降序排列的排行榜",
)
async def get_top_players(
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    position: Optional[str] = Query(None, description="位置筛选: GK/DF/MF/FW"),
    db: AsyncSession = Depends(get_db),
):
    """获取球员OVR排行（兼容旧接口，内部调用通用排行榜）"""
    service = LeaderboardService(db)
    players = await service.get_ovr_leaderboard(limit=limit, position=position)
    return ResponseSchema(success=True, data=players)


@router.get(
    "/leaderboard",
    response_model=ResponseSchema[List[LeaderboardItem]],
    summary="获取世界排行榜",
    description="获取全球球员排行榜，支持进球、助攻、评分、抢断等30+维度",
)
async def get_world_leaderboard(
    type: LeaderboardType = Query(LeaderboardType.GOALS, description="排行榜类型"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    position: Optional[str] = Query(None, description="位置筛选: GK/DF/MF/FW"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取世界通用排行榜
    
    - **type**: 排行榜类型，如 goals/assists/tackles/rating/shot_accuracy 等
    - **limit**: 返回数量
    - **position**: 位置筛选（可选）
    """
    service = LeaderboardService(db)
    items = await service.get_world_leaderboard(
        lb_type=type,
        limit=limit,
        position=position,
    )
    return ResponseSchema(success=True, data=items)


@router.get(
    "/team-leaderboard",
    response_model=ResponseSchema[List[TeamLeaderboardItem]],
    summary="获取球队世界排行榜",
    description="获取全球球队排行榜，支持积分、胜场、进球、失球、胜率、场均进球等维度",
)
async def get_world_team_leaderboard(
    type: TeamLeaderboardType = Query(TeamLeaderboardType.POINTS, description="排行榜类型"),
    limit: int = Query(100, ge=1, le=500, description="返回数量限制"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取球队世界通用排行榜

    - **type**: 排行榜类型，如 points/wins/goals_for/goals_against/win_rate/goals_per_game 等
    - **limit**: 返回数量
    """
    service = LeaderboardService(db)
    items = await service.get_world_team_leaderboard(
        lb_type=type,
        limit=limit,
    )
    return ResponseSchema(success=True, data=items)


@router.get(
    "/records",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取世界纪录",
    description="获取所有世界纪录，按分类分组返回",
)
async def get_world_records(
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选: team/player/match"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有世界纪录"""
    return await list_records(
        scope=RecordScopeEnum.WORLD,
        scope_target_id=None,
        category=category,
        db=db,
    )
