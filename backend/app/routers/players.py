"""
Player management API routes
"""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

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
    PlayerHistoryResponse,
    PlayerSeasonHistoryItem,
    PlayerCareerSummary,
    PlayerMilestone,
    SquadRole,
    PlayerContractResponse,
    ContractPreviewRequest,
    ContractPreviewResponse,
    ContractSignRequest,
    PlayerStateResponse,
    TeamPlayerStatesResponse,
)
from app.models import Player, PlayerSeasonStats, Season, Team
from app.services.contract_service import ContractService
from app.services.player_state_service import PlayerStateService

router = APIRouter(prefix="/players", tags=["球员"])


async def _get_career_stats(db: AsyncSession, player_id: str):
    """从赛季统计表聚合生涯统计。"""
    result = await db.execute(
        select(
            func.coalesce(func.sum(PlayerSeasonStats.matches_played), 0),
            func.coalesce(func.sum(PlayerSeasonStats.goals), 0),
            func.coalesce(func.sum(PlayerSeasonStats.assists), 0),
            func.coalesce(func.sum(PlayerSeasonStats.yellow_cards), 0),
            func.coalesce(func.sum(PlayerSeasonStats.red_cards), 0),
            func.coalesce(func.sum(PlayerSeasonStats.minutes_played), 0),
            func.coalesce(
                func.sum(PlayerSeasonStats.average_rating * PlayerSeasonStats.matches_played),
                0,
            ),
        ).where(PlayerSeasonStats.player_id == player_id)
    )
    (
        matches_played,
        goals,
        assists,
        yellow_cards,
        red_cards,
        minutes_played,
        rating_sum,
    ) = result.one()
    avg_rating = Decimal("6.0")
    if matches_played:
        avg_rating = (Decimal(str(rating_sum)) / Decimal(matches_played)).quantize(Decimal("0.1"))
    return {
        "matches_played": int(matches_played or 0),
        "goals": int(goals or 0),
        "assists": int(assists or 0),
        "yellow_cards": int(yellow_cards or 0),
        "red_cards": int(red_cards or 0),
        "average_rating": float(avg_rating),
        "minutes_played": int(minutes_played or 0),
    }


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
        pos=player.pos, rus=player.rus, dec=player.dec,
        fk=player.fk, pk=player.pk,
    )
    
    skills = [PlayerSkill(**s) for s in (player.skills or [])]
    
    career_stats = await _get_career_stats(db, player.id)
    stats = PlayerStats(**career_stats)
    
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
            matches_played=career_stats["matches_played"],
            goals=career_stats["goals"],
            assists=career_stats["assists"],
            yellow_cards=career_stats["yellow_cards"],
            red_cards=career_stats["red_cards"],
            average_rating=career_stats["average_rating"],
            minutes_played=career_stats["minutes_played"],
            team_id=player.team_id,
            created_at=player.created_at,
            updated_at=player.updated_at,
        ),
    )


@router.get(
    "/{player_id}/history",
    response_model=ResponseSchema[PlayerHistoryResponse],
    summary="获取球员生涯历史",
    description="获取球员每个赛季的表现数据和生涯总计",
)
async def get_player_history(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球员生涯历史"""
    # 验证球员存在
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()
    if not player:
        return ResponseSchema(success=False, message="球员不存在", code=404)

    # 获取所有赛季统计
    stats_result = await db.execute(
        select(PlayerSeasonStats, Season, Team)
        .join(Season, PlayerSeasonStats.season_id == Season.id)
        .outerjoin(Team, PlayerSeasonStats.team_id == Team.id)
        .where(PlayerSeasonStats.player_id == player_id)
        .order_by(Season.season_number.asc())
    )
    rows = stats_result.all()

    # 按赛季聚合（联赛+杯赛合并）
    season_map: dict[int, dict] = {}
    competition_details: dict[int, list[dict]] = {}

    for stats, season, team in rows:
        sn = season.season_number
        if sn not in season_map:
            season_map[sn] = {
                "season_number": sn,
                "team_name": team.name if team else "未知",
                "team_id": team.id if team else "",
                "matches_played": 0,
                "minutes_played": 0,
                "goals": 0,
                "assists": 0,
                "yellow_cards": 0,
                "red_cards": 0,
                "clean_sheets": 0,
                "total_rating_sum": 0.0,
                "total_rating_matches": 0,
            }
            competition_details[sn] = []

        s = season_map[sn]
        s["matches_played"] += stats.matches_played
        s["minutes_played"] += stats.minutes_played
        s["goals"] += stats.goals
        s["assists"] += stats.assists
        s["yellow_cards"] += stats.yellow_cards
        s["red_cards"] += stats.red_cards
        s["clean_sheets"] += stats.clean_sheets

        if stats.matches_played > 0:
            s["total_rating_sum"] += float(stats.average_rating) * stats.matches_played
            s["total_rating_matches"] += stats.matches_played

        comp_name = "联赛" if stats.league_id else ("杯赛" if stats.cup_competition_id else "其他")
        competition_details[sn].append({
            "competition": comp_name,
            "matches_played": stats.matches_played,
            "goals": stats.goals,
            "assists": stats.assists,
            "minutes_played": stats.minutes_played,
            "average_rating": float(stats.average_rating),
        })

    # 构建赛季历史项
    seasons: list[PlayerSeasonHistoryItem] = []
    for sn in sorted(season_map.keys()):
        s = season_map[sn]
        avg_rating = (
            round(s["total_rating_sum"] / s["total_rating_matches"], 1)
            if s["total_rating_matches"] > 0
            else 0.0
        )
        seasons.append(PlayerSeasonHistoryItem(
            season_number=s["season_number"],
            team_name=s["team_name"],
            team_id=s["team_id"],
            matches_played=s["matches_played"],
            minutes_played=s["minutes_played"],
            goals=s["goals"],
            assists=s["assists"],
            yellow_cards=s["yellow_cards"],
            red_cards=s["red_cards"],
            clean_sheets=s["clean_sheets"],
            average_rating=avg_rating,
            competition_breakdown=competition_details[sn],
        ))

    # 生涯汇总
    total_matches = sum(s.matches_played for s in seasons)
    total_goals = sum(s.goals for s in seasons)
    total_assists = sum(s.assists for s in seasons)
    total_minutes = sum(s.minutes_played for s in seasons)
    total_yellow = sum(s.yellow_cards for s in seasons)
    total_red = sum(s.red_cards for s in seasons)

    overall_rating = 0.0
    if total_matches > 0:
        rating_sum = sum(s.average_rating * s.matches_played for s in seasons)
        overall_rating = round(rating_sum / total_matches, 1)

    # 最佳赛季
    best_season = None
    if seasons:
        best = max(seasons, key=lambda s: s.goals * 3 + s.assists)
        best_season = {
            "season_number": best.season_number,
            "goals": best.goals,
            "assists": best.assists,
            "average_rating": best.average_rating,
        }

    summary = PlayerCareerSummary(
        total_seasons=len(seasons),
        total_matches=total_matches,
        total_goals=total_goals,
        total_assists=total_assists,
        total_minutes=total_minutes,
        total_yellow_cards=total_yellow,
        total_red_cards=total_red,
        overall_average_rating=overall_rating,
        best_season=best_season,
    )

    # 里程碑（简化版）
    milestones: list[PlayerMilestone] = []
    if seasons:
        first_season = min(seasons, key=lambda s: s.season_number)
        milestones.append(PlayerMilestone(
            milestone_type="debut",
            season_number=first_season.season_number,
            description=f"第 {first_season.season_number} 赛季首秀",
        ))
        if total_goals >= 1:
            milestones.append(PlayerMilestone(
                milestone_type="first_goal",
                season_number=first_season.season_number,
                description="攻入生涯首球",
            ))
        if total_goals >= 50:
            milestones.append(PlayerMilestone(
                milestone_type="50_goals",
                season_number=next((s.season_number for s in seasons if sum(x.goals for x in seasons[:seasons.index(s)+1]) >= 50), seasons[-1].season_number),
                description="达成 50 球里程碑",
            ))
        if total_goals >= 100:
            milestones.append(PlayerMilestone(
                milestone_type="100_goals",
                season_number=seasons[-1].season_number,
                description="达成 100 球里程碑",
            ))
        if total_matches >= 100:
            milestones.append(PlayerMilestone(
                milestone_type="100_appearances",
                season_number=seasons[-1].season_number,
                description="达成 100 场里程碑",
            ))

    return ResponseSchema(
        success=True,
        data=PlayerHistoryResponse(
            seasons=seasons,
            summary=summary,
            milestones=milestones,
        ),
    )


# =====================================================================
# Contract API (v1 新增)
# =====================================================================

@router.get(
    "/{player_id}/contract",
    response_model=ResponseSchema[PlayerContractResponse],
    summary="获取球员当前合同",
)
async def get_player_contract(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球员当前生效的合同详情"""
    contract_service = ContractService(db)
    contract = await contract_service._get_active_contract(player_id)
    if not contract:
        return ResponseSchema(success=False, message="球员没有生效的合同", code=404)
    
    return ResponseSchema(
        success=True,
        data=PlayerContractResponse(
            player_id=contract.player_id,
            team_id=contract.team_id,
            contract_type=contract.contract_type,
            start_season_number=contract.start_season_number,
            end_season_number=contract.end_season_number,
            wage=contract.wage,
            recommended_wage=contract.recommended_wage,
            wage_ratio=contract.wage_ratio,
            release_clause=contract.release_clause,
            squad_role=contract.squad_role,
            status=contract.status,
            created_at=contract.created_at,
        ),
    )


@router.post(
    "/{player_id}/contract/preview",
    response_model=ResponseSchema[ContractPreviewResponse],
    summary="预览合同 offer",
)
async def preview_contract(
    player_id: str,
    req: ContractPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """预览合同 offer，返回建议工资、满意度、工资帽压力等"""
    contract_service = ContractService(db)
    preview = await contract_service.preview_contract_offer(
        player_id=player_id,
        team_id=req.team_id,
        contract_type=req.contract_type,
        years=req.years,
        wage=req.wage,
        squad_role=req.squad_role,
    )
    return ResponseSchema(success=True, data=preview.to_dict())


@router.post(
    "/{player_id}/contract/sign",
    response_model=ResponseSchema[PlayerContractResponse],
    summary="签约",
)
async def sign_contract(
    player_id: str,
    req: ContractSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """与球员签订新合同"""
    contract_service = ContractService(db)
    contract = await contract_service.sign_contract(
        player_id=player_id,
        team_id=req.team_id,
        contract_type=req.contract_type,
        years=req.years,
        wage=req.wage,
        squad_role=req.squad_role,
        release_clause=req.release_clause,
    )
    return ResponseSchema(
        success=True,
        data=PlayerContractResponse(
            player_id=contract.player_id,
            team_id=contract.team_id,
            contract_type=contract.contract_type,
            start_season_number=contract.start_season_number,
            end_season_number=contract.end_season_number,
            wage=contract.wage,
            recommended_wage=contract.recommended_wage,
            wage_ratio=contract.wage_ratio,
            release_clause=contract.release_clause,
            squad_role=contract.squad_role,
            status=contract.status,
            created_at=contract.created_at,
        ),
    )


@router.post(
    "/{player_id}/contract/renew",
    response_model=ResponseSchema[PlayerContractResponse],
    summary="续约",
)
async def renew_contract(
    player_id: str,
    req: ContractSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """与球员续约"""
    contract_service = ContractService(db)
    contract = await contract_service.renew_contract(
        player_id=player_id,
        team_id=req.team_id,
        years=req.years,
        wage=req.wage,
        squad_role=req.squad_role,
        release_clause=req.release_clause,
    )
    return ResponseSchema(
        success=True,
        data=PlayerContractResponse(
            player_id=contract.player_id,
            team_id=contract.team_id,
            contract_type=contract.contract_type,
            start_season_number=contract.start_season_number,
            end_season_number=contract.end_season_number,
            wage=contract.wage,
            recommended_wage=contract.recommended_wage,
            wage_ratio=contract.wage_ratio,
            release_clause=contract.release_clause,
            squad_role=contract.squad_role,
            status=contract.status,
            created_at=contract.created_at,
        ),
    )


@router.post(
    "/{player_id}/contract/release",
    response_model=ResponseSchema[dict],
    summary="解约",
)
async def release_player(
    player_id: str,
    team_id: str = Query(..., description="球队ID"),
    db: AsyncSession = Depends(get_db),
):
    """解约球员"""
    contract_service = ContractService(db)
    await contract_service.release_player(player_id, team_id)
    return ResponseSchema(success=True, data={"released": True})


# =====================================================================
# Player State API (v1 新增)
# =====================================================================

@router.get(
    "/{player_id}/state",
    response_model=ResponseSchema[PlayerStateResponse],
    summary="获取球员状态",
)
async def get_player_state(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球员当前状态（玩家可见）"""
    player = await db.execute(select(Player).where(Player.id == player_id))
    player = player.scalar_one_or_none()
    if not player:
        return ResponseSchema(success=False, message="球员不存在", code=404)
    
    # 生成状态提示
    hints = []
    if player.match_form.value == "HOT":
        hints.append("近期状态火热")
    elif player.match_form.value == "LOW":
        hints.append("近期状态低迷")
    
    if player.fitness >= 90:
        hints.append("体能充沛")
    elif player.fitness < 50:
        hints.append("体能堪忧")
    
    if player.wage_satisfaction < 0:
        hints.append("合同问题可能影响他的投入程度")
    elif player.wage_satisfaction > 0:
        hints.append("对合同感到满意")
    
    if player.match_rust_score < -1:
        hints.append("久疏战阵，可能需要比赛找回节奏")
    
    # 趋势判断（简化：基于 state_score 与 0 的比较）
    trend = "stable"
    if player.state_score >= 3:
        trend = "up"
    elif player.state_score <= -2:
        trend = "down"
    
    return ResponseSchema(
        success=True,
        data=PlayerStateResponse(
            player_id=player.id,
            visible_form=player.match_form,
            fitness=player.fitness,
            availability=player.status,
            trend=trend,
            hints=hints,
            state_score=player.state_score,
            match_rust_score=player.match_rust_score,
        ),
    )


@router.get(
    "/teams/{team_id}/player-states",
    response_model=ResponseSchema[TeamPlayerStatesResponse],
    summary="获取全队球员状态",
)
async def get_team_player_states(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取全队所有球员的状态列表"""
    result = await db.execute(select(Player).where(Player.team_id == team_id))
    players = result.scalars().all()
    
    states = []
    for player in players:
        hints = []
        if player.match_form.value == "HOT":
            hints.append("近期状态火热")
        elif player.match_form.value == "LOW":
            hints.append("近期状态低迷")
        if player.fitness < 50:
            hints.append("体能堪忧")
        if player.match_rust_score < -1:
            hints.append("久疏战阵")
        
        trend = "stable"
        if player.state_score >= 3:
            trend = "up"
        elif player.state_score <= -2:
            trend = "down"
        
        states.append(PlayerStateResponse(
            player_id=player.id,
            visible_form=player.match_form,
            fitness=player.fitness,
            availability=player.status,
            trend=trend,
            hints=hints,
            state_score=player.state_score,
            match_rust_score=player.match_rust_score,
        ))
    
    return ResponseSchema(
        success=True,
        data=TeamPlayerStatesResponse(team_id=team_id, players=states),
    )
