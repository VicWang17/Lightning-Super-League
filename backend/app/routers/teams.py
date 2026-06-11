"""
Team management API routes
"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.schemas import (
    ResponseSchema,
    PaginatedResponse,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamSummary,
    DashboardStats,
    ErrorResponse,
    PlayerListItem,
    TeamHistoryResponse,
    TeamSeasonHistoryItem,
    TeamFinancials,
    TeamStats,
    PlayerStateResponse,
    TeamPlayerStatesResponse,
)
from app.schemas.records import (
    TeamHonorItem,
    TeamHonorsResponse,
    RecordsByCategory,
    RecordCategory as RecordCategoryEnum,
)
from app.models.user import User
from app.dependencies import get_db, get_current_user
from app.models import Team, League, LeagueStanding, Fixture, FixtureStatus, Season, LeagueSystem, PlayerSeasonStats, Player, TeamHonor, HonorType
from app.core.logging import get_logger

router = APIRouter(prefix="/teams", tags=["球队"])
logger = get_logger("app.teams")


@router.get(
    "/my-team",
    response_model=ResponseSchema[dict],
    summary="获取我的球队",
    description="获取当前登录用户的球队信息",
)
async def get_my_team(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的球队
    """
    user_id = current_user.id
    logger.info(f"获取用户球队: user_id={user_id}")
    
    # 查询用户的球队
    result = await db.execute(
        select(Team, League).join(League, Team.current_league_id == League.id, isouter=True)
        .where(Team.user_id == user_id)
    )
    row = result.first()
    
    if not row:
        logger.warning(f"用户没有球队: user_id={user_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您还没有球队"
        )
    
    team, league = row
    logger.info(f"返回球队信息: team_id={team.id}, name={team.name}, current_league_id={team.current_league_id}")

    # 计算球队三线评分
    from app.models import Player as PlayerModel
    player_result = await db.execute(
        select(PlayerModel.position, PlayerModel.ovr)
        .where(PlayerModel.team_id == team.id)
        .order_by(PlayerModel.ovr.desc())
    )
    pos_ovrs: dict[str, list[int]] = {"GK": [], "DF": [], "MF": [], "FW": []}
    for pos, ovr in player_result.all():
        if pos in pos_ovrs:
            pos_ovrs[pos].append(ovr)

    def _avg_top(lst: list[int], n: int) -> int:
        if not lst:
            return 0
        return round(sum(lst[:n]) / min(len(lst), n))

    attack = _avg_top(pos_ovrs["FW"], 3)
    midfield = _avg_top(pos_ovrs["MF"], 4)
    defense = _avg_top(pos_ovrs["DF"], 4)
    
    return ResponseSchema(
        success=True,
        data={
            "id": team.id,
            "name": team.name,
            "short_name": team.short_name,
            "overall_rating": team.overall_rating,
            "attack": attack,
            "midfield": midfield,
            "defense": defense,
            "current_league_id": team.current_league_id,
            "league_id": team.current_league_id,
            "league_name": league.name if league else None,
        }
    )


@router.get(
    "/",
    response_model=ResponseSchema[PaginatedResponse[TeamSummary]],
    summary="获取球队列表",
    description="获取所有球队的列表，支持分页和筛选",
)
async def list_teams(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    league_id: Optional[int] = Query(None, description="联赛ID筛选"),
    zone_id: Optional[int] = Query(1, description="大区ID（默认1区）"),
    search: Optional[str] = Query(None, description="搜索关键词"),
):
    """
    获取球队列表
    
    - **page**: 页码
    - **page_size**: 每页数量
    - **league_id**: 按联赛筛选
    - **zone_id**: 按大区筛选
    - **search**: 搜索球队名称
    """
    # TODO: 实现球队列表查询
    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(
            items=[],
            total=0,
            page=page,
            page_size=page_size,
        ),
    )


@router.post(
    "/",
    response_model=ResponseSchema[TeamResponse],
    summary="创建球队",
    description="创建一支新球队",
    status_code=201,
)
async def create_team(team_data: TeamCreate):
    """
    创建新球队
    
    - **name**: 球队名称（2-50字符）
    - **short_name**: 球队简称（可选）
    - **logo_url**: 队徽URL（可选）
    - **stadium**: 主场球场（可选）
    - **city**: 所在城市（可选）
    - **founded_year**: 成立年份（可选）
    """
    # TODO: 实现球队创建逻辑
    return ResponseSchema(
        success=True,
        message="创建成功",
        data=TeamResponse(
            id=1,
            name=team_data.name,
            user_id=1,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        ),
    )


@router.get(
    "/my-team/dashboard",
    response_model=ResponseSchema[DashboardStats],
    summary="获取我的球队Dashboard数据",
    description="获取当前登录球队的Dashboard统计数据，包括联赛排名、战绩、近期状态和下场比赛",
)
async def get_my_team_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的球队Dashboard统计数据
    """
    user_id = current_user.id
    
    # 获取用户球队
    result = await db.execute(
        select(Team).where(Team.user_id == user_id)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="您还没有球队"
        )
    
    # 获取当前赛季（同大区）
    # 通过球队的联赛找到所属大区
    zone_id = 1
    if team.current_league_id:
        zone_result = await db.execute(
            select(LeagueSystem.zone_id)
            .join(League, League.system_id == LeagueSystem.id)
            .where(League.id == team.current_league_id)
        )
        zone_row = zone_result.first()
        if zone_row:
            zone_id = zone_row[0]
    
    result = await db.execute(
        select(Season)
        .where(Season.status == "ongoing")
        .where(Season.zone_id == zone_id)
    )
    current_season = result.scalar_one_or_none()
    
    if not current_season:
        # 没有进行中的赛季，返回空数据
        return ResponseSchema(
            success=True,
            data=DashboardStats()
        )
    
    # 获取联赛排名数据
    standing = None
    if team.current_league_id:
        result = await db.execute(
            select(LeagueStanding).where(
                and_(
                    LeagueStanding.team_id == team.id,
                    LeagueStanding.league_id == team.current_league_id,
                    LeagueStanding.season_id == current_season.id
                )
            )
        )
        standing = result.scalar_one_or_none()
    
    # 获取最近5场已完成的比赛结果
    result = await db.execute(
        select(Fixture).where(
            and_(
                Fixture.season_id == current_season.id,
                Fixture.status == FixtureStatus.FINISHED,
                (Fixture.home_team_id == team.id) | (Fixture.away_team_id == team.id)
            )
        ).order_by(desc(Fixture.season_day)).limit(5)
    )
    recent_fixtures = result.scalars().all()
    
    # 计算近期状态 (W/D/L)
    form_chars = []
    for fixture in reversed(recent_fixtures):  # 从旧到新
        if fixture.home_team_id == team.id:
            if fixture.home_score > fixture.away_score:
                form_chars.append("W")
            elif fixture.home_score < fixture.away_score:
                form_chars.append("L")
            else:
                form_chars.append("D")
        else:
            if fixture.away_score > fixture.home_score:
                form_chars.append("W")
            elif fixture.away_score < fixture.home_score:
                form_chars.append("L")
            else:
                form_chars.append("D")
    recent_form = "".join(form_chars)
    
    # 获取下场比赛
    result = await db.execute(
        select(Fixture).where(
            and_(
                Fixture.season_id == current_season.id,
                Fixture.status == FixtureStatus.SCHEDULED,
                (Fixture.home_team_id == team.id) | (Fixture.away_team_id == team.id)
            )
        ).order_by(Fixture.season_day).limit(1)
    )
    next_fixture = result.scalar_one_or_none()
    
    next_match = None
    if next_fixture:
        opponent_id = next_fixture.away_team_id if next_fixture.home_team_id == team.id else next_fixture.home_team_id
        is_home = next_fixture.home_team_id == team.id
        
        result = await db.execute(select(Team).where(Team.id == opponent_id))
        opponent = result.scalar_one_or_none()
        
        next_match = {
            "opponent_id": opponent_id,
            "opponent_name": opponent.name if opponent else "未知",
            "is_home": is_home,
            "day": next_fixture.season_day,
            "fixture_type": next_fixture.fixture_type.value if next_fixture.fixture_type else "league",
        }
    
    return ResponseSchema(
        success=True,
        data=DashboardStats(
            league_position=standing.position if standing else None,
            points=standing.points if standing else 0,
            played=standing.played if standing else 0,
            won=standing.won if standing else 0,
            drawn=standing.drawn if standing else 0,
            lost=standing.lost if standing else 0,
            goals_for=standing.goals_for if standing else 0,
            goals_against=standing.goals_against if standing else 0,
            goal_difference=standing.goal_difference if standing else 0,
            recent_form=recent_form,
            next_match=next_match
        )
    )


@router.get(
    "/{team_id}/players",
    response_model=ResponseSchema[PaginatedResponse[PlayerListItem]],
    summary="获取球队球员",
    description="获取指定球队的球员列表",
)
async def get_team_players(
    team_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    获取球队球员列表
    
    - **team_id**: 球队ID
    - **page**: 页码
    - **page_size**: 每页数量
    """
    from app.models import Player
    from app.schemas import PlayerListItem
    
    query = select(Player).where(Player.team_id == team_id)
    
    total_result = await db.execute(select(Player.id).where(Player.team_id == team_id))
    total = len(total_result.scalars().all())
    
    result = await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )
    players = result.scalars().all()
    players.sort(key=lambda p: p.ovr, reverse=True)

    player_ids = [p.id for p in players]
    stats_by_player: dict[str, dict] = {}
    if player_ids:
        stats_result = await db.execute(
            select(
                PlayerSeasonStats.player_id,
                func.coalesce(func.sum(PlayerSeasonStats.matches_played), 0).label("matches_played"),
                func.coalesce(func.sum(PlayerSeasonStats.minutes_played), 0).label("minutes_played"),
                func.coalesce(func.sum(PlayerSeasonStats.goals), 0).label("goals"),
                func.coalesce(func.sum(PlayerSeasonStats.assists), 0).label("assists"),
                func.coalesce(func.sum(PlayerSeasonStats.yellow_cards), 0).label("yellow_cards"),
                func.coalesce(func.sum(PlayerSeasonStats.red_cards), 0).label("red_cards"),
                func.coalesce(
                    func.sum(PlayerSeasonStats.average_rating * PlayerSeasonStats.matches_played),
                    0,
                ).label("rating_sum"),
                # 进攻
                func.coalesce(func.sum(PlayerSeasonStats.shots), 0).label("shots"),
                func.coalesce(func.sum(PlayerSeasonStats.shots_on_target), 0).label("shots_on_target"),
                func.coalesce(func.sum(PlayerSeasonStats.dribbles), 0).label("dribbles"),
                func.coalesce(func.sum(PlayerSeasonStats.dribbles_succ), 0).label("dribbles_succ"),
                func.coalesce(func.sum(PlayerSeasonStats.headers), 0).label("headers"),
                func.coalesce(func.sum(PlayerSeasonStats.headers_succ), 0).label("headers_succ"),
                # 传球
                func.coalesce(func.sum(PlayerSeasonStats.passes), 0).label("passes"),
                func.coalesce(func.sum(PlayerSeasonStats.passes_succ), 0).label("passes_succ"),
                func.coalesce(func.sum(PlayerSeasonStats.key_passes), 0).label("key_passes"),
                func.coalesce(func.sum(PlayerSeasonStats.crosses), 0).label("crosses"),
                func.coalesce(func.sum(PlayerSeasonStats.crosses_succ), 0).label("crosses_succ"),
                # 防守
                func.coalesce(func.sum(PlayerSeasonStats.tackles), 0).label("tackles"),
                func.coalesce(func.sum(PlayerSeasonStats.tackles_succ), 0).label("tackles_succ"),
                func.coalesce(func.sum(PlayerSeasonStats.interceptions), 0).label("interceptions"),
                func.coalesce(func.sum(PlayerSeasonStats.clearances), 0).label("clearances"),
                func.coalesce(func.sum(PlayerSeasonStats.blocks), 0).label("blocks"),
                # 门将
                func.coalesce(func.sum(PlayerSeasonStats.saves), 0).label("saves"),
                func.coalesce(func.sum(PlayerSeasonStats.clean_sheets), 0).label("clean_sheets"),
                # 纪律/其他
                func.coalesce(func.sum(PlayerSeasonStats.fouls), 0).label("fouls"),
                func.coalesce(func.sum(PlayerSeasonStats.fouls_drawn), 0).label("fouls_drawn"),
                func.coalesce(func.sum(PlayerSeasonStats.offsides), 0).label("offsides"),
                func.coalesce(func.sum(PlayerSeasonStats.turnovers), 0).label("turnovers"),
                func.coalesce(func.sum(PlayerSeasonStats.touches), 0).label("touches"),
                func.coalesce(func.sum(PlayerSeasonStats.free_kicks), 0).label("free_kicks"),
                func.coalesce(func.sum(PlayerSeasonStats.free_kick_goals), 0).label("free_kick_goals"),
                func.coalesce(func.sum(PlayerSeasonStats.penalties), 0).label("penalties"),
                func.coalesce(func.sum(PlayerSeasonStats.penalty_goals), 0).label("penalty_goals"),
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
                "minutes_played": int(row.minutes_played or 0),
                "goals": int(row.goals or 0),
                "assists": int(row.assists or 0),
                "yellow_cards": int(row.yellow_cards or 0),
                "red_cards": int(row.red_cards or 0),
                "average_rating": average_rating,
                # 进攻
                "shots": int(row.shots or 0),
                "shots_on_target": int(row.shots_on_target or 0),
                "dribbles": int(row.dribbles or 0),
                "dribbles_succ": int(row.dribbles_succ or 0),
                "headers": int(row.headers or 0),
                "headers_succ": int(row.headers_succ or 0),
                # 传球
                "passes": int(row.passes or 0),
                "passes_succ": int(row.passes_succ or 0),
                "key_passes": int(row.key_passes or 0),
                "crosses": int(row.crosses or 0),
                "crosses_succ": int(row.crosses_succ or 0),
                # 防守
                "tackles": int(row.tackles or 0),
                "tackles_succ": int(row.tackles_succ or 0),
                "interceptions": int(row.interceptions or 0),
                "clearances": int(row.clearances or 0),
                "blocks": int(row.blocks or 0),
                # 门将
                "saves": int(row.saves or 0),
                "clean_sheets": int(row.clean_sheets or 0),
                # 纪律/其他
                "fouls": int(row.fouls or 0),
                "fouls_drawn": int(row.fouls_drawn or 0),
                "offsides": int(row.offsides or 0),
                "turnovers": int(row.turnovers or 0),
                "touches": int(row.touches or 0),
                "free_kicks": int(row.free_kicks or 0),
                "free_kick_goals": int(row.free_kick_goals or 0),
                "penalties": int(row.penalties or 0),
                "penalty_goals": int(row.penalty_goals or 0),
            }
    
    items = [
        PlayerListItem(
            id=p.id,
            name=p.name,
            race=p.race,
            avatar_url=p.avatar_url,
            age=abs(p.birth_offset),
            position=p.position,
            ovr=p.ovr,
            potential_letter=p.potential_letter,
            market_value=p.market_value,
            squad_number=p.squad_number,
            team_id=p.team_id,
            status=p.status,
            current_suspension=p.current_suspension,
            **stats_by_player.get(
                p.id,
                {
                    "matches_played": 0,
                    "minutes_played": 0,
                    "goals": 0,
                    "assists": 0,
                    "yellow_cards": 0,
                    "red_cards": 0,
                    "average_rating": 0.0,
                    "shots": 0,
                    "shots_on_target": 0,
                    "dribbles": 0,
                    "dribbles_succ": 0,
                    "headers": 0,
                    "headers_succ": 0,
                    "passes": 0,
                    "passes_succ": 0,
                    "key_passes": 0,
                    "crosses": 0,
                    "crosses_succ": 0,
                    "tackles": 0,
                    "tackles_succ": 0,
                    "interceptions": 0,
                    "clearances": 0,
                    "blocks": 0,
                    "saves": 0,
                    "clean_sheets": 0,
                    "fouls": 0,
                    "fouls_drawn": 0,
                    "offsides": 0,
                    "turnovers": 0,
                    "touches": 0,
                    "free_kicks": 0,
                    "free_kick_goals": 0,
                    "penalties": 0,
                    "penalty_goals": 0,
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
    "/{team_id}/stats",
    response_model=ResponseSchema[dict],
    summary="获取球队统计",
    description="获取指定球队的赛季统计数据",
)
async def get_team_stats(team_id: int):
    """
    获取球队统计数据
    
    - **team_id**: 球队ID
    """
    # TODO: 实现球队统计查询
    return ResponseSchema(
        success=True,
        data={
            "matches_played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        },
    )


@router.get(
    "/{team_id}/finances",
    response_model=ResponseSchema[dict],
    summary="获取球队财务（兼容旧接口）",
    description="获取指定球队的财务基本信息",
)
async def get_team_finances(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取球队财务信息（兼容旧接口，返回基本信息）
    
    - **team_id**: 球队ID
    """
    from app.services.finance_service import FinanceService
    service = FinanceService(db)
    try:
        overview = await service.get_overview(team_id)
        return ResponseSchema(
            success=True,
            data={
                "balance": overview["current_balance"],
                "weekly_wages": overview["wage_cap_info"]["wage_bill"],
                "stadium_capacity": 30000,  # v1 暂不启用
                "ticket_price": 25.00,      # v1 暂不启用
            },
        )
    except ValueError:
        # 赛季未初始化，返回基础财务数据
        from app.models.team import TeamFinance
        from sqlalchemy import select
        result = await db.execute(select(TeamFinance).where(TeamFinance.team_id == team_id))
        tf = result.scalar_one_or_none()
        if tf:
            return ResponseSchema(
                success=True,
                data={
                    "balance": tf.balance,
                    "weekly_wages": tf.weekly_wage_bill,
                    "stadium_capacity": tf.stadium_capacity,
                    "ticket_price": tf.ticket_price,
                },
            )
        raise HTTPException(status_code=404, detail="球队财务未找到")




@router.get(
    "/{team_id}",
    response_model=ResponseSchema[TeamResponse],
    summary="获取球队详情",
    description="获取指定球队的详细信息",
    responses={
        200: {"description": "获取成功"},
        404: {"model": ErrorResponse, "description": "球队不存在"},
    },
)
async def get_team(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取球队详情

    - **team_id**: 球队ID
    """
    result = await db.execute(
        select(Team, League).join(League, Team.current_league_id == League.id, isouter=True)
        .where(Team.id == team_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="球队不存在",
        )
    team, league = row

    # 获取球队财务
    from app.models.team import TeamFinance
    finance_result = await db.execute(select(TeamFinance).where(TeamFinance.team_id == team_id))
    finance = finance_result.scalar_one_or_none()

    # 计算球队三线评分（取各位置 top N 球员的平均 OVR）
    from app.models import Player as PlayerModel
    player_result = await db.execute(
        select(PlayerModel.position, PlayerModel.ovr)
        .where(PlayerModel.team_id == team_id)
        .order_by(PlayerModel.ovr.desc())
    )
    pos_ovrs: dict[str, list[int]] = {"GK": [], "DF": [], "MF": [], "FW": []}
    for pos, ovr in player_result.all():
        if pos in pos_ovrs:
            pos_ovrs[pos].append(ovr)

    def _avg_top(lst: list[int], n: int) -> int:
        if not lst:
            return 0
        return round(sum(lst[:n]) / min(len(lst), n))

    attack = _avg_top(pos_ovrs["FW"], 3)
    midfield = _avg_top(pos_ovrs["MF"], 4)
    defense = _avg_top(pos_ovrs["DF"], 4)  # 包含 GK 影响小，取纯 DF

    # 获取当前赛季排名数据
    stats = None
    if team.current_league_id:
        season_result = await db.execute(
            select(Season).where(Season.status == "ongoing")
        )
        current_season = season_result.scalar_one_or_none()
        if current_season:
            standing_result = await db.execute(
                select(LeagueStanding).where(
                    and_(
                        LeagueStanding.team_id == team_id,
                        LeagueStanding.league_id == team.current_league_id,
                        LeagueStanding.season_id == current_season.id,
                    )
                )
            )
            standing = standing_result.scalar_one_or_none()
            if standing:
                stats = TeamStats(
                    matches_played=standing.played,
                    wins=standing.won,
                    draws=standing.drawn,
                    losses=standing.lost,
                    goals_for=standing.goals_for,
                    goals_against=standing.goals_against,
                    points=standing.points,
                    league_position=standing.position,
                )

    return ResponseSchema(
        success=True,
        data=TeamResponse(
            id=team.id,
            name=team.name,
            short_name=team.short_name,
            logo_url=team.logo_url,
            stadium=team.stadium,
            city=team.city,
            founded_year=team.founded_year,
            user_id=team.user_id,
            league_id=team.current_league_id,
            status=team.status,
            overall_rating=team.overall_rating,
            attack=attack,
            midfield=midfield,
            defense=defense,
            created_at=team.created_at if hasattr(team, "created_at") else datetime.now(),
            updated_at=team.updated_at if hasattr(team, "updated_at") else datetime.now(),
            financials=TeamFinancials(
                balance=finance.balance if finance else Decimal("0"),
                weekly_wages=finance.weekly_wage_bill if finance else Decimal("0"),
                stadium_capacity=finance.stadium_capacity if finance else 0,
                ticket_price=finance.ticket_price if finance else Decimal("0"),
            ) if finance else None,
            stats=stats,
        ),
    )


@router.put(
    "/{team_id}",
    response_model=ResponseSchema[TeamResponse],
    summary="更新球队信息",
    description="更新指定球队的信息",
)
async def update_team(team_id: str, team_data: TeamUpdate):
    """
    更新球队信息
    
    - **team_id**: 球队ID
    - **name**: 球队名称
    - **short_name**: 简称
    - **logo_url**: 队徽
    - **stadium**: 球场
    - **city**: 城市
    """
    # TODO: 实现球队更新逻辑
    return ResponseSchema(
        success=True,
        message="更新成功",
        data=TeamResponse(
            id=team_id,
            name=team_data.name or "示例球队",
            user_id=1,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        ),
    )


@router.get(
    "/{team_id}/history",
    response_model=ResponseSchema[TeamHistoryResponse],
    summary="获取球队历史",
    description="获取球队各赛季的联赛排名和战绩",
)
async def get_team_history(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球队历史赛季数据"""
    # 验证球队存在
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        return ResponseSchema(success=False, message="球队不存在", code=404)

    # 查询所有赛季的联赛排名
    standings_result = await db.execute(
        select(LeagueStanding, Season, League)
        .join(Season, LeagueStanding.season_id == Season.id)
        .join(League, LeagueStanding.league_id == League.id)
        .where(LeagueStanding.team_id == team_id)
        .order_by(Season.season_number.asc())
    )
    rows = standings_result.all()

    seasons: list[TeamSeasonHistoryItem] = []
    for standing, season, league in rows:
        # 查询该赛季队内射手王
        top_scorer_result = await db.execute(
            select(Player.name, PlayerSeasonStats.goals)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                PlayerSeasonStats.team_id == team_id,
                PlayerSeasonStats.season_id == season.id,
            )
            .order_by(PlayerSeasonStats.goals.desc())
            .limit(1)
        )
        top_scorer = top_scorer_result.first()

        seasons.append(TeamSeasonHistoryItem(
            season_number=season.season_number,
            league_name=league.name,
            league_level=league.level if league.level else 1,
            position=standing.position,
            played=standing.played,
            won=standing.won,
            drawn=standing.drawn,
            lost=standing.lost,
            goals_for=standing.goals_for,
            goals_against=standing.goals_against,
            goal_difference=standing.goal_difference,
            points=standing.points,
            top_scorer_name=top_scorer[0] if top_scorer else None,
            top_scorer_goals=top_scorer[1] if top_scorer else 0,
        ))

    # 查询球队荣誉
    honors_result = await db.execute(
        select(TeamHonor, Season)
        .join(Season, TeamHonor.season_id == Season.id)
        .where(TeamHonor.team_id == team_id)
        .order_by(desc(Season.season_number))
    )
    honor_rows = honors_result.all()
    trophies = [
        TeamHonorItem(
            season_number=season.season_number,
            honor_type=honor.honor_type.value,
            competition_name=honor.competition_name or "",
            competition_level=honor.competition_level,
        )
        for honor, season in honor_rows
    ]

    return ResponseSchema(
        success=True,
        data=TeamHistoryResponse(
            seasons=seasons,
            record_count=len(seasons),
            trophies=trophies,
        ),
    )


@router.get(
    "/{team_id}/honors",
    response_model=ResponseSchema[TeamHonorsResponse],
    summary="获取球队荣誉",
    description="获取球队获得的所有冠军荣誉（联赛冠军、杯赛冠军）",
)
async def get_team_honors(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球队荣誉列表"""
    from app.services.honor_service import HonorService

    # 验证球队存在
    team_result = await db.execute(select(Team).where(Team.id == team_id))
    team = team_result.scalar_one_or_none()
    if not team:
        return ResponseSchema(success=False, message="球队不存在", code=404)

    service = HonorService(db)
    honors = await service.get_team_honors(team_id)
    return ResponseSchema(success=True, data=honors)


@router.get(
    "/{team_id}/records",
    response_model=ResponseSchema[RecordsByCategory],
    summary="获取球队纪录",
    description="获取指定球队的所有纪录",
)
async def get_team_records(
    team_id: str,
    category: Optional[RecordCategoryEnum] = Query(None, description="分类筛选: team/player/match"),
    db: AsyncSession = Depends(get_db),
):
    """获取指定球队的所有纪录"""
    from app.routers.records import list_records
    from app.schemas.records import RecordScope as RecordScopeEnum

    return await list_records(
        scope=RecordScopeEnum.TEAM,
        scope_target_id=team_id,
        category=category,
        db=db,
    )


@router.get(
    "/{team_id}/player-states",
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
