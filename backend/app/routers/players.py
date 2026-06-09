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
    PlayerGrowthResponse,
    GrowthCurvePoint,
    AttributeProgressItem,
)
from app.models import Player, PlayerSeasonStats, Season, Team, SeasonStatus
from app.services.contract_service import ContractService
from app.services.player_state_service import PlayerStateService

router = APIRouter(prefix="/players", tags=["球员"])


def _calc_accuracy(total: int, succ: int) -> float:
    if not total:
        return 0.0
    return max(0.0, min(100.0, round((succ / total) * 100, 1)))


def _bounded_success(total: int, succ: int) -> int:
    return max(0, min(total, succ))


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
            # 进攻
            func.coalesce(func.sum(PlayerSeasonStats.shots), 0),
            func.coalesce(func.sum(PlayerSeasonStats.shots_on_target), 0),
            func.coalesce(func.sum(PlayerSeasonStats.dribbles), 0),
            func.coalesce(func.sum(PlayerSeasonStats.dribbles_succ), 0),
            func.coalesce(func.sum(PlayerSeasonStats.headers), 0),
            func.coalesce(func.sum(PlayerSeasonStats.headers_succ), 0),
            # 传球
            func.coalesce(func.sum(PlayerSeasonStats.passes), 0),
            func.coalesce(func.sum(PlayerSeasonStats.passes_succ), 0),
            func.coalesce(func.sum(PlayerSeasonStats.key_passes), 0),
            func.coalesce(func.sum(PlayerSeasonStats.crosses), 0),
            func.coalesce(func.sum(PlayerSeasonStats.crosses_succ), 0),
            # 防守
            func.coalesce(func.sum(PlayerSeasonStats.tackles), 0),
            func.coalesce(func.sum(PlayerSeasonStats.tackles_succ), 0),
            func.coalesce(func.sum(PlayerSeasonStats.interceptions), 0),
            func.coalesce(func.sum(PlayerSeasonStats.clearances), 0),
            func.coalesce(func.sum(PlayerSeasonStats.blocks), 0),
            # 门将
            func.coalesce(func.sum(PlayerSeasonStats.saves), 0),
            func.coalesce(func.sum(PlayerSeasonStats.clean_sheets), 0),
            # 纪律/其他
            func.coalesce(func.sum(PlayerSeasonStats.fouls), 0),
            func.coalesce(func.sum(PlayerSeasonStats.fouls_drawn), 0),
            func.coalesce(func.sum(PlayerSeasonStats.offsides), 0),
            func.coalesce(func.sum(PlayerSeasonStats.turnovers), 0),
            func.coalesce(func.sum(PlayerSeasonStats.touches), 0),
            func.coalesce(func.sum(PlayerSeasonStats.free_kicks), 0),
            func.coalesce(func.sum(PlayerSeasonStats.free_kick_goals), 0),
            func.coalesce(func.sum(PlayerSeasonStats.penalties), 0),
            func.coalesce(func.sum(PlayerSeasonStats.penalty_goals), 0),
        ).where(PlayerSeasonStats.player_id == player_id)
    )
    row = result.one()
    matches_played = int(row[0] or 0)
    goals = int(row[1] or 0)
    assists = int(row[2] or 0)
    yellow_cards = int(row[3] or 0)
    red_cards = int(row[4] or 0)
    minutes_played = int(row[5] or 0)
    rating_sum = row[6] or 0

    # 进攻
    shots = int(row[7] or 0)
    shots_on_target = int(row[8] or 0)
    dribbles = int(row[9] or 0)
    dribbles_succ = _bounded_success(dribbles, int(row[10] or 0))
    headers = int(row[11] or 0)
    headers_succ = _bounded_success(headers, int(row[12] or 0))
    # 传球
    passes = int(row[13] or 0)
    passes_succ = _bounded_success(passes, int(row[14] or 0))
    key_passes = int(row[15] or 0)
    crosses = int(row[16] or 0)
    crosses_succ = _bounded_success(crosses, int(row[17] or 0))
    # 防守
    tackles = int(row[18] or 0)
    tackles_succ = _bounded_success(tackles, int(row[19] or 0))
    interceptions = int(row[20] or 0)
    clearances = int(row[21] or 0)
    blocks = int(row[22] or 0)
    # 门将
    saves = int(row[23] or 0)
    clean_sheets = int(row[24] or 0)
    # 纪律/其他
    fouls = int(row[25] or 0)
    fouls_drawn = int(row[26] or 0)
    offsides = int(row[27] or 0)
    turnovers = int(row[28] or 0)
    touches = int(row[29] or 0)
    free_kicks = int(row[30] or 0)
    free_kick_goals = int(row[31] or 0)
    penalties = int(row[32] or 0)
    penalty_goals = int(row[33] or 0)

    avg_rating = Decimal("6.0")
    if matches_played:
        avg_rating = (Decimal(str(rating_sum)) / Decimal(matches_played)).quantize(Decimal("0.1"))

    return {
        "matches_played": matches_played,
        "goals": goals,
        "assists": assists,
        "yellow_cards": yellow_cards,
        "red_cards": red_cards,
        "average_rating": float(avg_rating),
        "minutes_played": minutes_played,
        # 进攻
        "shots": shots,
        "shots_on_target": shots_on_target,
        "shot_accuracy": _calc_accuracy(shots, shots_on_target),
        "dribbles": dribbles,
        "dribbles_succ": dribbles_succ,
        "dribble_accuracy": _calc_accuracy(dribbles, dribbles_succ),
        "headers": headers,
        "headers_succ": headers_succ,
        "header_accuracy": _calc_accuracy(headers, headers_succ),
        # 传球
        "passes": passes,
        "passes_succ": passes_succ,
        "pass_accuracy": _calc_accuracy(passes, passes_succ),
        "key_passes": key_passes,
        "crosses": crosses,
        "crosses_succ": crosses_succ,
        "cross_accuracy": _calc_accuracy(crosses, crosses_succ),
        # 防守
        "tackles": tackles,
        "tackles_succ": tackles_succ,
        "tackle_accuracy": _calc_accuracy(tackles, tackles_succ),
        "interceptions": interceptions,
        "clearances": clearances,
        "blocks": blocks,
        # 门将
        "saves": saves,
        "clean_sheets": clean_sheets,
        # 纪律/其他
        "fouls": fouls,
        "fouls_drawn": fouls_drawn,
        "offsides": offsides,
        "turnovers": turnovers,
        "touches": touches,
        "free_kicks": free_kicks,
        "free_kick_goals": free_kick_goals,
        "penalties": penalties,
        "penalty_goals": penalty_goals,
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

    player_ids = [p.id for p in players]
    stats_by_player: dict[str, dict] = {}
    if player_ids:
        stats_result = await db.execute(
            select(
                PlayerSeasonStats.player_id,
                func.coalesce(func.sum(PlayerSeasonStats.matches_played), 0).label("matches_played"),
                func.coalesce(func.sum(PlayerSeasonStats.goals), 0).label("goals"),
                func.coalesce(func.sum(PlayerSeasonStats.assists), 0).label("assists"),
                func.coalesce(
                    func.sum(PlayerSeasonStats.average_rating * PlayerSeasonStats.matches_played),
                    0,
                ).label("rating_sum"),
            )
            .where(PlayerSeasonStats.player_id.in_(player_ids))
            .group_by(PlayerSeasonStats.player_id)
        )
        for row in stats_result.all():
            matches_played = int(row.matches_played or 0)
            rating_sum = row.rating_sum or 0
            average_rating = round(float(rating_sum) / matches_played, 1) if matches_played else 0.0
            stats_by_player[row.player_id] = {
                "matches_played": matches_played,
                "goals": int(row.goals or 0),
                "assists": int(row.assists or 0),
                "average_rating": average_rating,
            }
    
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
            squad_number=p.squad_number,
            team_id=p.team_id,
            **stats_by_player.get(
                p.id,
                {
                    "matches_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "average_rating": 0.0,
                },
            ),
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
            current_suspension=player.current_suspension,
            contract_type=player.contract_type,
            contract_end_season=player.contract_end_season,
            wage=player.wage,
            release_clause=player.release_clause,
            squad_role=player.squad_role,
            preferred_number=player.preferred_number,
            squad_number=player.squad_number,
            market_value=player.market_value,
            stats=stats,
            team_id=player.team_id,
            created_at=player.created_at,
            updated_at=player.updated_at,
            **career_stats,
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
                # 进攻
                "shots": 0, "shots_on_target": 0,
                "dribbles": 0, "dribbles_succ": 0,
                "headers": 0, "headers_succ": 0,
                # 传球
                "passes": 0, "passes_succ": 0, "key_passes": 0,
                "crosses": 0, "crosses_succ": 0,
                # 防守
                "tackles": 0, "tackles_succ": 0,
                "interceptions": 0, "clearances": 0, "blocks": 0,
                # 门将
                "saves": 0,
                # 纪律/其他
                "fouls": 0, "fouls_drawn": 0, "offsides": 0,
                "turnovers": 0, "touches": 0,
                "free_kicks": 0, "free_kick_goals": 0,
                "penalties": 0, "penalty_goals": 0,
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

        # 进攻
        s["shots"] += stats.shots
        s["shots_on_target"] += stats.shots_on_target
        s["dribbles"] += stats.dribbles
        s["dribbles_succ"] += stats.dribbles_succ
        s["headers"] += stats.headers
        s["headers_succ"] += stats.headers_succ
        # 传球
        s["passes"] += stats.passes
        s["passes_succ"] += stats.passes_succ
        s["key_passes"] += stats.key_passes
        s["crosses"] += stats.crosses
        s["crosses_succ"] += stats.crosses_succ
        # 防守
        s["tackles"] += stats.tackles
        s["tackles_succ"] += stats.tackles_succ
        s["interceptions"] += stats.interceptions
        s["clearances"] += stats.clearances
        s["blocks"] += stats.blocks
        # 门将
        s["saves"] += stats.saves
        # 纪律/其他
        s["fouls"] += stats.fouls
        s["fouls_drawn"] += stats.fouls_drawn
        s["offsides"] += stats.offsides
        s["turnovers"] += stats.turnovers
        s["touches"] += stats.touches
        s["free_kicks"] += stats.free_kicks
        s["free_kick_goals"] += stats.free_kick_goals
        s["penalties"] += stats.penalties
        s["penalty_goals"] += stats.penalty_goals

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
        mp = s["matches_played"]
        seasons.append(PlayerSeasonHistoryItem(
            season_number=s["season_number"],
            team_name=s["team_name"],
            team_id=s["team_id"],
            matches_played=mp,
            minutes_played=s["minutes_played"],
            goals=s["goals"],
            assists=s["assists"],
            yellow_cards=s["yellow_cards"],
            red_cards=s["red_cards"],
            clean_sheets=s["clean_sheets"],
            average_rating=avg_rating,
            # 进攻
            shots=s["shots"],
            shots_on_target=s["shots_on_target"],
            shot_accuracy=_calc_accuracy(s["shots"], s["shots_on_target"]),
            dribbles=s["dribbles"],
            dribbles_succ=_bounded_success(s["dribbles"], s["dribbles_succ"]),
            dribble_accuracy=_calc_accuracy(s["dribbles"], _bounded_success(s["dribbles"], s["dribbles_succ"])),
            headers=s["headers"],
            headers_succ=_bounded_success(s["headers"], s["headers_succ"]),
            header_accuracy=_calc_accuracy(s["headers"], _bounded_success(s["headers"], s["headers_succ"])),
            # 传球
            passes=s["passes"],
            passes_succ=_bounded_success(s["passes"], s["passes_succ"]),
            pass_accuracy=_calc_accuracy(s["passes"], _bounded_success(s["passes"], s["passes_succ"])),
            key_passes=s["key_passes"],
            crosses=s["crosses"],
            crosses_succ=_bounded_success(s["crosses"], s["crosses_succ"]),
            cross_accuracy=_calc_accuracy(s["crosses"], _bounded_success(s["crosses"], s["crosses_succ"])),
            # 防守
            tackles=s["tackles"],
            tackles_succ=_bounded_success(s["tackles"], s["tackles_succ"]),
            tackle_accuracy=_calc_accuracy(s["tackles"], _bounded_success(s["tackles"], s["tackles_succ"])),
            interceptions=s["interceptions"],
            clearances=s["clearances"],
            blocks=s["blocks"],
            # 门将
            saves=s["saves"],
            # 纪律/其他
            fouls=s["fouls"],
            fouls_drawn=s["fouls_drawn"],
            offsides=s["offsides"],
            turnovers=s["turnovers"],
            touches=s["touches"],
            free_kicks=s["free_kicks"],
            free_kick_goals=s["free_kick_goals"],
            penalties=s["penalties"],
            penalty_goals=s["penalty_goals"],
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
        # 进攻
        total_shots=sum(s.shots for s in seasons),
        total_shots_on_target=sum(s.shots_on_target for s in seasons),
        total_dribbles=sum(s.dribbles for s in seasons),
        total_dribbles_succ=sum(s.dribbles_succ for s in seasons),
        total_headers=sum(s.headers for s in seasons),
        total_headers_succ=sum(s.headers_succ for s in seasons),
        # 传球
        total_passes=sum(s.passes for s in seasons),
        total_passes_succ=sum(s.passes_succ for s in seasons),
        total_key_passes=sum(s.key_passes for s in seasons),
        total_crosses=sum(s.crosses for s in seasons),
        total_crosses_succ=sum(s.crosses_succ for s in seasons),
        # 防守
        total_tackles=sum(s.tackles for s in seasons),
        total_tackles_succ=sum(s.tackles_succ for s in seasons),
        total_interceptions=sum(s.interceptions for s in seasons),
        total_clearances=sum(s.clearances for s in seasons),
        total_blocks=sum(s.blocks for s in seasons),
        # 门将
        total_saves=sum(s.saves for s in seasons),
        total_clean_sheets=sum(s.clean_sheets for s in seasons),
        # 纪律/其他
        total_fouls=sum(s.fouls for s in seasons),
        total_fouls_drawn=sum(s.fouls_drawn for s in seasons),
        total_offsides=sum(s.offsides for s in seasons),
        total_turnovers=sum(s.turnovers for s in seasons),
        total_touches=sum(s.touches for s in seasons),
        total_free_kicks=sum(s.free_kicks for s in seasons),
        total_free_kick_goals=sum(s.free_kick_goals for s in seasons),
        total_penalties=sum(s.penalties for s in seasons),
        total_penalty_goals=sum(s.penalty_goals for s in seasons),
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


# =====================================================================
# Player Growth Curve API
# =====================================================================

_ATTR_LABELS = {
    "sho": "射门", "pas": "传球", "dri": "盘带", "spd": "速度",
    "str_": "力量", "sta": "体能", "acc": "爆发力", "hea": "头球",
    "bal": "平衡", "defe": "防守意识", "tkl": "抢断", "vis": "视野",
    "cro": "传中", "con": "控球", "fin": "远射", "com": "镇定",
    "sav": "扑救", "ref": "反应", "pos": "站位", "rus": "出击",
    "dec": "球商", "fk": "任意球", "pk": "点球",
}

_CURVE_TYPE_LABELS = {
    "early_bloomer": "早熟型",
    "steady": "稳定型",
    "late_bloomer": "晚熟型",
    "explosive": "爆发型",
    "plateau": "平台型",
}


def _generate_projected_curve(
    current_age: int,
    current_ovr: int,
    peak_age: int,
    curve_type: str,
    speed: float,
) -> list[GrowthCurvePoint]:
    """基于球员成长参数生成预测曲线（15-35岁）。"""
    if peak_age <= 15:
        peak_age = 28

    # 估算巅峰 OVR
    if current_age < peak_age:
        years_to_peak = peak_age - current_age
        peak_ovr = current_ovr + years_to_peak * 2.0 * speed
    else:
        peak_ovr = current_ovr + (current_age - peak_age) * 1.5
    peak_ovr = min(99, peak_ovr)

    # 15 岁基础 OVR
    base_ovr = max(35, peak_ovr - (peak_age - 15) * 3.5)

    curve: list[GrowthCurvePoint] = []
    for age in range(15, 36):
        if age <= peak_age:
            t = (age - 15) / max(1, peak_age - 15)
            if curve_type == "early_bloomer":
                factor = 1 - (1 - t) ** 0.5
            elif curve_type == "late_bloomer":
                factor = t ** 2
            elif curve_type == "explosive":
                factor = 1 - (1 - t) ** 0.3
            elif curve_type == "plateau":
                factor = min(1.0, t / 0.6)
            else:  # steady
                factor = t
            ovr = base_ovr + (peak_ovr - base_ovr) * factor
        else:
            t = (age - peak_age) / max(1, 35 - peak_age)
            if curve_type == "early_bloomer":
                decline = t ** 0.8
            elif curve_type == "explosive":
                decline = t ** 0.5
            elif curve_type == "plateau":
                decline = max(0.0, (t - 0.3) / 0.7)
            elif curve_type == "late_bloomer":
                decline = t ** 1.2
            else:
                decline = t
            ovr = peak_ovr - (peak_ovr - 30) * decline

        ovr = int(max(30, min(99, ovr)))
        curve.append(GrowthCurvePoint(
            age=age,
            ovr=ovr,
            is_projected=(age != current_age),
        ))

    return curve


@router.get(
    "/{player_id}/growth",
    response_model=ResponseSchema[PlayerGrowthResponse],
    summary="获取球员成长曲线",
    description="获取球员成长曲线元数据、属性进度和预测曲线",
)
async def get_player_growth(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球员成长曲线数据"""
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        return ResponseSchema(success=False, message="球员不存在", code=404)

    # 获取当前赛季以计算年龄
    season_result = await db.execute(
        select(Season)
        .where(Season.status == SeasonStatus.ONGOING)
        .order_by(Season.season_number.desc())
        .limit(1)
    )
    season = season_result.scalar_one_or_none()
    current_age = abs(player.birth_offset)
    if season:
        current_age = season.season_number + abs(player.birth_offset)

    current_ovr = player.ovr
    peak_age = player.growth_peak_age or 28
    curve_type = player.growth_curve_type or "steady"
    speed = float(player.growth_speed) if player.growth_speed else 1.0
    stability = float(player.growth_stability) if player.growth_stability else 1.0
    late_bloom = float(player.late_bloom_factor) if player.late_bloom_factor else 1.0

    # 生成预测曲线
    projected_curve = _generate_projected_curve(
        current_age=current_age,
        current_ovr=current_ovr,
        peak_age=peak_age,
        curve_type=curve_type,
        speed=speed,
    )

    # 属性进度
    attribute_progress: list[AttributeProgressItem] = []
    caps = player.attribute_caps or {}
    progress = player.attribute_progress or {}
    for attr_key in _ATTR_LABELS:
        # 获取当前属性值
        current_val = getattr(player, attr_key, 10) or 10
        cap_val = caps.get(attr_key, 20.0) if isinstance(caps, dict) else 20.0
        if isinstance(cap_val, (int, float)):
            progress_pct = round((current_val / cap_val) * 100, 1) if cap_val > 0 else 0.0
        else:
            cap_val = 20.0
            progress_pct = 0.0

        attribute_progress.append(AttributeProgressItem(
            attribute=attr_key,
            label=_ATTR_LABELS[attr_key],
            current=current_val,
            cap=float(cap_val),
            progress_pct=progress_pct,
        ))

    # 按 progress_pct 排序，潜力空间最小的排前面（最接近上限）
    attribute_progress.sort(key=lambda x: x.progress_pct, reverse=True)

    return ResponseSchema(
        success=True,
        data=PlayerGrowthResponse(
            current_age=current_age,
            current_ovr=current_ovr,
            peak_age=peak_age,
            curve_type=curve_type,
            curve_type_label=_CURVE_TYPE_LABELS.get(curve_type, "未知"),
            growth_speed=speed,
            stability=stability,
            late_bloom_factor=late_bloom,
            projected_curve=projected_curve,
            attribute_progress=attribute_progress,
        ),
    )
