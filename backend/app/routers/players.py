"""
Player management API routes
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.schemas import (
    ResponseSchema,
    PaginatedResponse,
    PlayerCreate,
    PlayerUpdate,
    PlayerResponse,
    PlayerPosition,
    PlayerListItem,
    ErrorResponse,
)
from app.models import Player

router = APIRouter(prefix="/players", tags=["球员"])


@router.get(
    "/",
    response_model=ResponseSchema[PaginatedResponse[PlayerListItem]],
    summary="获取球员列表",
    description="获取所有球员的列表，支持分页和筛选",
)
async def list_players(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    team_id: Optional[str] = Query(None, description="球队ID筛选"),
    position: Optional[PlayerPosition] = Query(None, description="位置筛选"),
    min_ovr: Optional[int] = Query(None, ge=1, le=100, description="最低总评"),
    max_ovr: Optional[int] = Query(None, ge=1, le=100, description="最高总评"),
    search: Optional[str] = Query(None, description="搜索球员名称"),
    db: AsyncSession = Depends(get_db),
):
    """获取球员列表"""
    query = select(Player)
    
    if team_id:
        query = query.where(Player.team_id == team_id)
    if position:
        query = query.where(Player.position == position)
    if min_ovr:
        query = query.where(Player.ovr >= min_ovr)
    if max_ovr:
        query = query.where(Player.ovr <= max_ovr)
    if search:
        query = query.where(Player.name.contains(search))
    
    total_result = await db.execute(select(Player.id).where(query.whereclause) if query.whereclause else select(Player.id))
    total = len(total_result.scalars().all())
    
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    players = result.scalars().all()
    
    items = [
        PlayerListItem(
            id=p.id,
            name=p.name,
            race=p.race,
            avatar_url=p.avatar_url,
            age=abs(p.birth_offset),  # TODO: 加上当前赛季序号
            position=p.position,
            ovr=p.ovr,
            potential_letter=p.potential_letter,
            market_value=p.market_value,
            team_id=p.team_id,
        )
        for p in players
    ]
    
    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get(
    "/{player_id}",
    response_model=ResponseSchema[PlayerResponse],
    summary="获取球员详情",
    description="获取指定球员的详细信息",
    responses={
        200: {"description": "获取成功"},
        404: {"model": ErrorResponse, "description": "球员不存在"},
    },
)
async def get_player(player_id: str, db: AsyncSession = Depends(get_db)):
    """获取球员详情"""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    
    if not player:
        return ResponseSchema(success=False, message="球员不存在", code=404)
    
    from app.schemas.player import PlayerAbility, PlayerStats, PlayerSkill
    
    abilities = PlayerAbility(
        sho=player.sho, pas=player.pas, dri=player.dri,
        spd=player.spd, str_=player.str_, sta=player.sta,
        acc=player.acc, hea=player.hea, bal=player.bal,
        defe=player.defe, tkl=player.tkl, vis=player.vis,
        cro=player.cro, con=player.con, fin=player.fin,
        com=player.com, sav=player.sav, ref=player.ref,
        pos=player.pos,
    )
    
    skills = [PlayerSkill(**s) for s in (player.skills or [])]
    
    stats = PlayerStats(
        matches_played=player.matches_played,
        goals=player.goals,
        assists=player.assists,
        yellow_cards=player.yellow_cards,
        red_cards=player.red_cards,
        average_rating=float(player.average_rating),
        minutes_played=player.minutes_played,
    )
    
    return ResponseSchema(
        success=True,
        data=PlayerResponse(
            id=player.id,
            name=player.name,
            race=player.race,
            avatar_url=player.avatar_url,
            position=player.position,
            preferred_foot=player.preferred_foot,
            height=player.height,
            weight=player.weight,
            birth_offset=player.birth_offset,
            age=abs(player.birth_offset),
            abilities=abilities,
            ovr=player.ovr,
            potential_letter=player.potential_letter,
            skills=skills,
            status=player.status,
            match_form=player.match_form,
            fitness=player.fitness,
            contract_type=player.contract_type,
            contract_end_season=player.contract_end_season,
            wage=player.wage,
            release_clause=player.release_clause,
            squad_role=player.squad_role,
            market_value=player.market_value,
            stats=stats,
            team_id=player.team_id,
            created_at=player.created_at,
            updated_at=player.updated_at,
        ),
    )
