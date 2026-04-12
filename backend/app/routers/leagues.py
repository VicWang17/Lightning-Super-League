"""
League API routes
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.schemas import ResponseSchema, ErrorResponse
from app.schemas.league import (
    LeagueResponse, LeagueDetailResponse, LeagueSystemResponse,
    LeagueStandingItem, StandingTeamInfo, MatchResponse, MatchTeamInfo,
    SeasonResponse, TopScorerItem, TopAssistItem, CleanSheetItem, PlayoffMatchItem
)
from app.models import LeagueSystem, League, Season, LeagueStanding, Fixture, FixtureStatus, Team, Player
from app.models.season import FixtureType
from app.dependencies import get_db

router = APIRouter(prefix="/leagues", tags=["联赛"])


@router.get(
    "/systems",
    response_model=ResponseSchema[List[LeagueSystemResponse]],
    summary="获取联赛体系列表",
    description="获取所有联赛体系（东区、西区、南区、北区）",
)
async def list_league_systems(db: AsyncSession = Depends(get_db)):
    """
    获取所有联赛体系列表
    """
    result = await db.execute(select(LeagueSystem))
    systems = result.scalars().all()
    
    return ResponseSchema(
        success=True,
        data=[
            LeagueSystemResponse(
                id=str(system.id),
                name=system.name,
                code=system.code,
                description=system.description,
                max_teams_per_league=system.max_teams_per_league
            )
            for system in systems
        ]
    )


@router.get(
    "/",
    response_model=ResponseSchema[List[LeagueResponse]],
    summary="获取联赛列表",
    description="获取所有联赛的列表，可按体系筛选",
)
async def list_leagues(
    system_id: Optional[str] = Query(None, description="联赛体系ID筛选"),
    system_code: Optional[str] = Query(None, description="联赛体系代码筛选（EAST/WEST/SOUTH/NORTH）"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有联赛列表
    
    - **system_id**: 按联赛体系ID筛选（可选）
    - **system_code**: 按联赛体系代码筛选（可选，EAST/WEST/SOUTH/NORTH）
    """
    query = select(League).options(selectinload(League.system))
    
    if system_code:
        # 通过 code 查找 system_id
        system_result = await db.execute(
            select(LeagueSystem).where(LeagueSystem.code == system_code.upper())
        )
        system = system_result.scalar_one_or_none()
        if system:
            query = query.where(League.system_id == system.id)
    elif system_id:
        query = query.where(League.system_id == system_id)
    
    result = await db.execute(query.order_by(League.system_id, League.level))
    leagues = result.scalars().all()
    
    # 获取所有联赛的球队数量
    league_ids = [league.id for league in leagues]
    teams_count_result = await db.execute(
        select(Team.current_league_id, func.count(Team.id))
        .where(Team.current_league_id.in_(league_ids))
        .group_by(Team.current_league_id)
    )
    teams_count_map = {league_id: count for league_id, count in teams_count_result.all()}
    
    return ResponseSchema(
        success=True,
        data=[
            LeagueResponse(
                id=str(league.id),
                name=league.name,
                level=league.level,
                system_id=str(league.system_id),
                system_code=league.system.code if league.system else "",
                system_name=league.system.name if league.system else "",
                max_teams=league.max_teams,
                promotion_spots=league.promotion_spots,
                relegation_spots=league.relegation_spots,
                has_promotion_playoff=league.has_promotion_playoff,
                has_relegation_playoff=league.has_relegation_playoff,
                teams_count=teams_count_map.get(league.id, 0)
            )
            for league in leagues
        ]
    )


@router.get(
    "/{league_id}",
    response_model=ResponseSchema[LeagueDetailResponse],
    summary="获取联赛详情",
    description="获取指定联赛的详细信息，包含积分榜",
    responses={
        200: {"description": "获取成功"},
        404: {"model": ErrorResponse, "description": "联赛不存在"},
    },
)
async def get_league(league_id: str, db: AsyncSession = Depends(get_db)):
    """
    获取联赛详情
    
    - **league_id**: 联赛ID
    """
    # 获取联赛信息
    result = await db.execute(
        select(League)
        .options(selectinload(League.system))
        .where(League.id == league_id)
    )
    league = result.scalar_one_or_none()
    
    if not league:
        raise HTTPException(status_code=404, detail="联赛不存在")
    
    # 获取球队数量
    from app.models import Team
    teams_count_result = await db.execute(
        select(func.count(Team.id)).where(Team.current_league_id == league_id)
    )
    teams_count = teams_count_result.scalar() or 0
    
    # 获取当前赛季
    season_result = await db.execute(
        select(Season).where(Season.status.in_(["ongoing", "upcoming"])).order_by(Season.start_date)
    )
    current_season = season_result.scalar_one_or_none()
    
    # 获取积分榜
    standings_data = []
    if current_season:
        standings_result = await db.execute(
            select(LeagueStanding)
            .options(selectinload(LeagueStanding.team))
            .where(
                and_(
                    LeagueStanding.league_id == league_id,
                    LeagueStanding.season_id == current_season.id
                )
            )
            .order_by(LeagueStanding.position)
        )
        standings = standings_result.scalars().all()
        
        for standing in standings:
            standings_data.append(LeagueStandingItem(
                position=standing.position,
                team=StandingTeamInfo(
                    id=str(standing.team.id),
                    name=standing.team.name,
                    short_name=standing.team.short_name
                ),
                played=standing.played,
                won=standing.won,
                drawn=standing.drawn,
                lost=standing.lost,
                goals_for=standing.goals_for,
                goals_against=standing.goals_against,
                goal_difference=standing.goal_difference,
                points=standing.points,
                form=standing.form,
                is_promotion_zone=standing.is_promotion_zone,
                is_relegation_zone=standing.is_relegation_zone
            ))
    
    # 获取近期比赛
    recent_matches = []
    upcoming_matches = []
    if current_season:
        # 已完成的比赛
        recent_result = await db.execute(
            select(Fixture)
            .options(
                selectinload(Fixture.home_team),
                selectinload(Fixture.away_team)
            )
            .where(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == current_season.id,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
            .order_by(Fixture.scheduled_at.desc())
            .limit(5)
        )
        recent = recent_result.scalars().all()
        
        for match in recent:
            recent_matches.append(MatchResponse(
                id=str(match.id),
                matchday=match.round_number,
                home_team=MatchTeamInfo(
                    id=str(match.home_team.id),
                    name=match.home_team.name,
                    short_name=match.home_team.short_name
                ),
                away_team=MatchTeamInfo(
                    id=str(match.away_team.id),
                    name=match.away_team.name,
                    short_name=match.away_team.short_name
                ),
                home_score=match.home_score,
                away_score=match.away_score,
                status=match.status.value,
                scheduled_at=match.scheduled_at
            ))
        
        # 即将进行的比赛
        upcoming_result = await db.execute(
            select(Fixture)
            .options(
                selectinload(Fixture.home_team),
                selectinload(Fixture.away_team)
            )
            .where(
                and_(
                    Fixture.league_id == league_id,
                    Fixture.season_id == current_season.id,
                    Fixture.status.in_([FixtureStatus.SCHEDULED, FixtureStatus.ONGOING])
                )
            )
            .order_by(Fixture.scheduled_at)
            .limit(5)
        )
        upcoming = upcoming_result.scalars().all()
        
        for match in upcoming:
            upcoming_matches.append(MatchResponse(
                id=str(match.id),
                matchday=match.round_number,
                home_team=MatchTeamInfo(
                    id=str(match.home_team.id),
                    name=match.home_team.name,
                    short_name=match.home_team.short_name
                ),
                away_team=MatchTeamInfo(
                    id=str(match.away_team.id),
                    name=match.away_team.name,
                    short_name=match.away_team.short_name
                ),
                home_score=match.home_score,
                away_score=match.away_score,
                status=match.status.value,
                scheduled_at=match.scheduled_at
            ))
    
    # 获取附加赛信息
    # 当联赛第14轮（Day 20）打完后，显示附加赛信息
    playoffs_data = []
    if current_season:
        # 检查是否已经到了附加赛阶段（联赛第14轮结束后，即 season_day >= 20）
        # 或者当前赛季有正在进行的附加赛
        is_playoff_time = (
            current_season.current_league_round >= 14 or  # 联赛14轮全部结束
            current_season.current_day >= 20 or  # 或者已经到了Day 20
            current_season.status == "completed"  # 或者赛季已结束
        )
        
        if is_playoff_time:
            # 通过积分榜获取该联赛在该赛季的所有球队ID
            # 注意：使用 LeagueStanding 表获取赛季中的球队，而不是 Team.current_league_id
            # 因为赛季结束后球队可能已经被升降级
            standings_team_result = await db.execute(
                select(LeagueStanding.team_id).where(
                    and_(
                        LeagueStanding.league_id == league_id,
                        LeagueStanding.season_id == current_season.id
                    )
                )
            )
            league_team_ids = {str(t[0]) for t in standings_team_result.all()}
            
            # 查询该赛季的所有附加赛（Day 22, 23, 24）
            playoffs_result = await db.execute(
                select(Fixture)
                .options(
                    selectinload(Fixture.home_team),
                    selectinload(Fixture.away_team)
                )
                .where(
                    and_(
                        Fixture.season_id == current_season.id,
                        Fixture.fixture_type == FixtureType.PLAYOFF,
                        Fixture.season_day.in_([22, 23, 24])
                    )
                )
                .order_by(Fixture.season_day, Fixture.scheduled_at)
            )
            all_playoffs = playoffs_result.scalars().all()
            
            for playoff in all_playoffs:
                if not playoff.home_team or not playoff.away_team:
                    continue
                    
                home_team_id = str(playoff.home_team_id) if playoff.home_team_id else None
                away_team_id = str(playoff.away_team_id) if playoff.away_team_id else None
                stage_name = playoff.cup_stage or ""
                
                # 判断是否与该联赛相关：本联赛有球队参与这场比赛
                # 通过检查附加赛中的球队是否在该联赛的赛季积分榜中
                is_involved = (home_team_id in league_team_ids) or (away_team_id in league_team_ids)
                
                if is_involved:
                    # 生成对阵名称
                    if "P_" in stage_name or "预赛" in stage_name:
                        name = f"附加赛预选赛"
                    else:
                        name = f"附加赛决赛"
                    
                    playoffs_data.append(PlayoffMatchItem(
                        id=str(playoff.id),
                        name=name,
                        round=1 if playoff.season_day == 22 else 2,
                        home_team=MatchTeamInfo(
                            id=str(playoff.home_team.id),
                            name=playoff.home_team.name,
                            short_name=playoff.home_team.short_name
                        ),
                        away_team=MatchTeamInfo(
                            id=str(playoff.away_team.id),
                            name=playoff.away_team.name,
                            short_name=playoff.away_team.short_name
                        ),
                        home_score=playoff.home_score,
                        away_score=playoff.away_score,
                        status=playoff.status.value,
                        scheduled_at=playoff.scheduled_at
                    ))
    
    return ResponseSchema(
        success=True,
        data=LeagueDetailResponse(
            id=str(league.id),
            name=league.name,
            level=league.level,
            system_id=str(league.system_id),
            system_code=league.system.code if league.system else "",
            system_name=league.system.name if league.system else "",
            max_teams=league.max_teams,
            promotion_spots=league.promotion_spots,
            relegation_spots=league.relegation_spots,
            has_promotion_playoff=league.has_promotion_playoff,
            has_relegation_playoff=league.has_relegation_playoff,
            teams_count=teams_count,
            current_season=SeasonResponse(
                id=str(current_season.id),
                season_number=current_season.season_number,
                name=f"第{current_season.season_number}赛季",
                start_date=current_season.start_date,
                end_date=current_season.end_date,
                status=current_season.status
            ) if current_season else None,
            standings=standings_data,
            recent_matches=recent_matches,
            upcoming_matches=upcoming_matches,
            playoffs=playoffs_data
        )
    )


@router.get(
    "/{league_id}/table",
    response_model=ResponseSchema[List[LeagueStandingItem]],
    summary="获取积分榜",
    description="获取指定联赛的当前积分榜",
)
async def get_league_table(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID（默认当前赛季）"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取联赛积分榜
    
    - **league_id**: 联赛ID
    - **season_id**: 赛季ID（可选）
    """
    # 如果没有指定赛季，获取当前赛季
    if not season_id:
        season_result = await db.execute(
            select(Season).where(Season.status.in_(["ongoing", "upcoming"])).order_by(Season.start_date)
        )
        season = season_result.scalar_one_or_none()
        if season:
            season_id = str(season.id)
    
    if not season_id:
        return ResponseSchema(success=True, data=[])
    
    standings_result = await db.execute(
        select(LeagueStanding)
        .options(selectinload(LeagueStanding.team))
        .where(
            and_(
                LeagueStanding.league_id == league_id,
                LeagueStanding.season_id == season_id
            )
        )
        .order_by(LeagueStanding.position)
    )
    standings = standings_result.scalars().all()
    
    return ResponseSchema(
        success=True,
        data=[
            LeagueStandingItem(
                position=standing.position,
                team=StandingTeamInfo(
                    id=str(standing.team.id),
                    name=standing.team.name,
                    short_name=standing.team.short_name
                ),
                played=standing.played,
                won=standing.won,
                drawn=standing.drawn,
                lost=standing.lost,
                goals_for=standing.goals_for,
                goals_against=standing.goals_against,
                goal_difference=standing.goal_difference,
                points=standing.points,
                form=standing.form,
                is_promotion_zone=standing.is_promotion_zone,
                is_relegation_zone=standing.is_relegation_zone
            )
            for standing in standings
        ]
    )


@router.get(
    "/{league_id}/schedule",
    response_model=ResponseSchema[List[MatchResponse]],
    summary="获取赛程",
    description="获取指定联赛的赛程安排",
)
async def get_league_schedule(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID（默认当前赛季）"),
    round_number: Optional[int] = Query(None, description="轮次"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取联赛赛程
    
    - **league_id**: 联赛ID
    - **season_id**: 赛季ID（可选）
    - **round_number**: 轮次（可选）
    """
    # 如果没有指定赛季，获取当前赛季
    if not season_id:
        season_result = await db.execute(
            select(Season).where(Season.status.in_(["ongoing", "upcoming"])).order_by(Season.start_date)
        )
        season = season_result.scalar_one_or_none()
        if season:
            season_id = str(season.id)
    
    if not season_id:
        return ResponseSchema(success=True, data=[])
    
    query = select(Fixture).options(
        selectinload(Fixture.home_team),
        selectinload(Fixture.away_team)
    ).where(
        and_(
            Fixture.league_id == league_id,
            Fixture.season_id == season_id
        )
    )
    
    if round_number:
        query = query.where(Fixture.round_number == round_number)
    
    query = query.order_by(Fixture.round_number, Fixture.scheduled_at)
    
    result = await db.execute(query)
    matches = result.scalars().all()
    
    return ResponseSchema(
        success=True,
        data=[
            MatchResponse(
                id=str(match.id),
                matchday=match.round_number,
                home_team=MatchTeamInfo(
                    id=str(match.home_team.id),
                    name=match.home_team.name,
                    short_name=match.home_team.short_name
                ),
                away_team=MatchTeamInfo(
                    id=str(match.away_team.id),
                    name=match.away_team.name,
                    short_name=match.away_team.short_name
                ),
                home_score=match.home_score,
                away_score=match.away_score,
                status=match.status.value,
                scheduled_at=match.scheduled_at
            )
            for match in matches
        ]
    )


@router.get(
    "/{league_id}/top-scorers",
    response_model=ResponseSchema[List[TopScorerItem]],
    summary="获取射手榜",
    description="获取指定联赛的射手榜",
)
async def get_top_scorers(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID（默认当前赛季）"),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取联赛射手榜
    
    - **league_id**: 联赛ID
    - **season_id**: 赛季ID（可选）
    - **limit**: 返回数量
    """
    # 获取联赛中进球最多的球员
    result = await db.execute(
        select(Player, Team)
        .join(Team, Player.team_id == Team.id)
        .where(Team.current_league_id == league_id)
        .order_by(Player.goals.desc())
        .limit(limit)
    )
    players = result.all()
    
    return ResponseSchema(
        success=True,
        data=[
            TopScorerItem(
                rank=idx + 1,
                player_id=str(player.Player.id),
                player_name=player.Player.display_name or f"{player.Player.first_name} {player.Player.last_name}",
                team_name=player.Team.name,
                goals=player.Player.goals,
                matches=player.Player.matches_played
            )
            for idx, player in enumerate(players)
        ]
    )


@router.get(
    "/{league_id}/top-assists",
    response_model=ResponseSchema[List[TopAssistItem]],
    summary="获取助攻榜",
    description="获取指定联赛的助攻榜",
)
async def get_top_assists(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID（默认当前赛季）"),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取联赛助攻榜
    
    - **league_id**: 联赛ID
    - **season_id**: 赛季ID（可选）
    - **limit**: 返回数量
    """
    # 获取联赛中助攻最多的球员
    result = await db.execute(
        select(Player, Team)
        .join(Team, Player.team_id == Team.id)
        .where(Team.current_league_id == league_id)
        .order_by(Player.assists.desc())
        .limit(limit)
    )
    players = result.all()
    
    return ResponseSchema(
        success=True,
        data=[
            TopAssistItem(
                rank=idx + 1,
                player_id=str(player.Player.id),
                player_name=player.Player.display_name or f"{player.Player.first_name} {player.Player.last_name}",
                team_name=player.Team.name,
                assists=player.Player.assists,
                matches=player.Player.matches_played
            )
            for idx, player in enumerate(players)
        ]
    )


@router.get(
    "/{league_id}/clean-sheets",
    response_model=ResponseSchema[List[CleanSheetItem]],
    summary="获取零封榜",
    description="获取指定联赛的零封榜（门将）",
)
async def get_clean_sheets(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID（默认当前赛季）"),
    limit: int = Query(20, ge=1, le=50, description="返回数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取联赛零封榜
    
    - **league_id**: 联赛ID
    - **season_id**: 赛季ID（可选）
    - **limit**: 返回数量
    """
    # 获取联赛中零封最多的门将（简化实现，实际应该有专门的统计表）
    from app.models.player import PlayerPosition
    
    result = await db.execute(
        select(Player, Team)
        .join(Team, Player.team_id == Team.id)
        .where(
            and_(
                Team.current_league_id == league_id,
                Player.primary_position == PlayerPosition.GK
            )
        )
        .order_by(Player.matches_played.desc())  # 简化：按出场次数排序
        .limit(limit)
    )
    players = result.all()
    
    return ResponseSchema(
        success=True,
        data=[
            CleanSheetItem(
                rank=idx + 1,
                player_id=str(player.Player.id),
                player_name=player.Player.display_name or f"{player.Player.first_name} {player.Player.last_name}",
                team_name=player.Team.name,
                clean_sheets=player.Player.matches_played // 3,  # 模拟数据
                matches=player.Player.matches_played
            )
            for idx, player in enumerate(players)
        ]
    )
