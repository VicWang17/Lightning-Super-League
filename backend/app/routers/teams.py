"""
Team management API routes
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.schemas import (
    ResponseSchema,
    PaginatedResponse,
    TeamCreate,
    TeamUpdate,
    TeamResponse,
    TeamSummary,
    DashboardStats,
    ErrorResponse,
)
from app.dependencies import get_db, get_current_user
from app.models import Team, League, LeagueStanding, Fixture, FixtureStatus, Season
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
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的球队
    """
    user_id = current_user.get("user_id")
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
    
    return ResponseSchema(
        success=True,
        data={
            "id": team.id,
            "name": team.name,
            "short_name": team.short_name,
            "overall_rating": team.overall_rating,
            "current_league_id": team.current_league_id,
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
    "/{team_id}",
    response_model=ResponseSchema[TeamResponse],
    summary="获取球队详情",
    description="获取指定球队的详细信息",
    responses={
        200: {"description": "获取成功"},
        404: {"model": ErrorResponse, "description": "球队不存在"},
    },
)
async def get_team(team_id: int):
    """
    获取球队详情
    
    - **team_id**: 球队ID
    """
    # TODO: 实现球队详情查询
    return ResponseSchema(
        success=True,
        data=TeamResponse(
            id=team_id,
            name="示例球队",
            user_id=1,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        ),
    )


@router.put(
    "/{team_id}",
    response_model=ResponseSchema[TeamResponse],
    summary="更新球队信息",
    description="更新指定球队的信息",
)
async def update_team(team_id: int, team_data: TeamUpdate):
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
    "/{team_id}/players",
    response_model=ResponseSchema[PaginatedResponse[dict]],  # 使用PlayerListItem
    summary="获取球队球员",
    description="获取指定球队的球员列表",
)
async def get_team_players(
    team_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    获取球队球员列表
    
    - **team_id**: 球队ID
    - **page**: 页码
    - **page_size**: 每页数量
    """
    # TODO: 实现球队球员查询
    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(
            items=[],
            total=0,
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
    summary="获取球队财务",
    description="获取指定球队的财务信息",
)
async def get_team_finances(team_id: int):
    """
    获取球队财务信息
    
    - **team_id**: 球队ID
    """
    # TODO: 实现球队财务查询
    return ResponseSchema(
        success=True,
        data={
            "balance": 10000000.00,
            "weekly_wages": 50000.00,
            "stadium_capacity": 30000,
            "ticket_price": 25.00,
        },
    )


@router.get(
    "/my-team/dashboard",
    response_model=ResponseSchema[DashboardStats],
    summary="获取我的球队Dashboard数据",
    description="获取当前登录球队的Dashboard统计数据，包括联赛排名、战绩、近期状态和下场比赛",
)
async def get_my_team_dashboard(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的球队Dashboard统计数据
    """
    user_id = current_user.get("user_id")
    
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
