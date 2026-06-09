"""
World API routes - 世界排名与全球数据接口
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas import ResponseSchema
from app.schemas.records import (
    RecordsByCategory,
    RecordCategory as RecordCategoryEnum,
    RecordScope as RecordScopeEnum,
)
from app.services.honor_service import HonorService
from app.routers.records import list_records

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
    """获取球员OVR排行"""
    service = HonorService(db)
    players = await service.get_top_players(limit=limit, position=position)
    return ResponseSchema(success=True, data=players)


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
