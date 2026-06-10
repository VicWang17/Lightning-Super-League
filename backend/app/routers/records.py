"""
Records API routes - 纪录中心接口
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.schemas import ResponseSchema
from app.schemas.records import (
    RecordItem,
    RecordsByCategory,
    RecordScope as RecordScopeEnum,
    RecordCategory as RecordCategoryEnum,
    RecordType as RecordTypeEnum,
)
from app.models import Record, Player, Team, Season
from app.models.record import RECORD_TYPE_LABELS, RecordScope, RecordCategory

router = APIRouter(prefix="/records", tags=["纪录"])


def _record_to_item(record: Record) -> RecordItem:
    """将 Record ORM 对象转换为 RecordItem schema"""
    holder_name = "未知"
    holder_id = ""
    holder_avatar_url = None
    holder_team_name = None
    holder_team_id = None
    
    if record.category == RecordCategory.PLAYER and record.holder_player:
        holder_name = record.holder_player.name
        holder_id = record.holder_player.id
        holder_avatar_url = record.holder_player.avatar_url
        holder_team_id = record.holder_player.team_id
        if record.holder_team:
            holder_team_name = record.holder_team.name
    elif record.category == RecordCategory.TEAM and record.holder_team:
        holder_name = record.holder_team.name
        holder_id = record.holder_team.id
        holder_team_id = record.holder_team.id
    elif record.category == RecordCategory.MATCH:
        # 比赛纪录的保持者可能是球队
        if record.holder_team:
            holder_name = record.holder_team.name
            holder_id = record.holder_team.id
            holder_team_id = record.holder_team.id
        elif record.holder_player:
            holder_name = record.holder_player.name
            holder_id = record.holder_player.id
            holder_avatar_url = record.holder_player.avatar_url
    
    season_number = None
    if record.season:
        season_number = getattr(record.season, 'season_number', None)
    
    return RecordItem(
        id=record.id,
        scope=RecordScopeEnum(record.scope.value),
        category=RecordCategoryEnum(record.category.value),
        record_type=RecordTypeEnum(record.record_type.value),
        record_type_label=RECORD_TYPE_LABELS.get(record.record_type, record.record_type.value),
        holder_name=holder_name,
        holder_id=holder_id,
        holder_avatar_url=holder_avatar_url,
        holder_team_name=holder_team_name,
        holder_team_id=holder_team_id,
        record_value=record.record_value,
        record_value_numeric=float(record.record_value_numeric),
        season_number=season_number,
        match_date=record.match_date,
        fixture_id=record.fixture_id,
        context=record.context or {},
        created_at=record.created_at.date() if record.created_at else None,
        updated_at=record.updated_at.date() if record.updated_at else None,
    )


@router.get(
    "/",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取纪录列表",
    description="获取纪录列表，支持按范围和分类筛选",
)
async def list_records(
    scope: RecordScopeEnum = Query(RecordScopeEnum.WORLD, description="纪录范围: world/league/team"),
    scope_target_id: Optional[str] = Query(None, description="联赛ID或球队ID，WORLD时可不传"),
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选: team/player/match"),
    db: AsyncSession = Depends(get_db),
):
    """获取纪录列表，按分类分组返回"""
    query = select(Record).options(
        selectinload(Record.holder_player),
        selectinload(Record.holder_team),
        selectinload(Record.season),
    )
    
    # scope 筛选
    scope_filter = Record.scope == RecordScope(scope.value)
    query = query.where(scope_filter)
    
    # scope_target_id 筛选
    if scope_target_id:
        query = query.where(Record.scope_target_id == scope_target_id)
    else:
        query = query.where(Record.scope_target_id.is_(None))
    
    # category 筛选
    if category:
        query = query.where(Record.category == RecordCategory(category.value))
    
    result = await db.execute(query)
    records = result.scalars().all()
    
    # 按分类分组
    by_category = RecordsByCategory()
    for record in records:
        item = _record_to_item(record)
        if record.category == RecordCategory.TEAM:
            by_category.team.append(item)
        elif record.category == RecordCategory.PLAYER:
            by_category.player.append(item)
        elif record.category == RecordCategory.MATCH:
            by_category.match.append(item)
    
    # 每组内按 record_type 固定顺序排序
    type_order = {t: i for i, t in enumerate(RecordTypeEnum)}
    by_category.team.sort(key=lambda x: type_order.get(x.record_type, 999))
    by_category.player.sort(key=lambda x: type_order.get(x.record_type, 999))
    by_category.match.sort(key=lambda x: type_order.get(x.record_type, 999))
    
    return ResponseSchema(success=True, data=by_category)


@router.get(
    "/world",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取世界纪录",
)
async def get_world_records(
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取所有世界纪录"""
    return await list_records(
        scope=RecordScopeEnum.WORLD,
        scope_target_id=None,
        category=category,
        db=db,
    )


@router.get(
    "/league/{league_id}",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取联赛纪录",
)
async def get_league_records(
    league_id: str,
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取指定联赛的所有纪录"""
    return await list_records(
        scope=RecordScopeEnum.LEAGUE,
        scope_target_id=league_id,
        category=category,
        db=db,
    )


@router.get(
    "/team/{team_id}",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取球队纪录",
)
async def get_team_records(
    team_id: str,
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取指定球队的所有纪录"""
    return await list_records(
        scope=RecordScopeEnum.TEAM,
        scope_target_id=team_id,
        category=category,
        db=db,
    )


@router.get(
    "/cup/{cup_id}",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取杯赛纪录",
)
async def get_cup_records(
    cup_id: str,
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取指定杯赛的所有纪录"""
    return await list_records(
        scope=RecordScopeEnum.CUP,
        scope_target_id=cup_id,
        category=category,
        db=db,
    )
