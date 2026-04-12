"""
Cup routers - 杯赛管理API
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.dependencies import get_db, get_current_user
from app.schemas import ResponseSchema
from app.models.season import CupCompetition, CupGroup, Fixture, FixtureStatus, Season
from app.models.team import Team
from app.models.user import User

router = APIRouter(prefix="/cups", tags=["杯赛"])


@router.get("", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_cups(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取当前赛季的所有杯赛
    """
    # 获取当前赛季
    result = await db.execute(
        select(Season).where(Season.status == "ongoing").order_by(Season.season_number.desc())
    )
    season = result.scalar_one_or_none()
    
    if not season:
        # 如果没有进行中的赛季，获取最新的赛季
        result = await db.execute(
            select(Season).order_by(Season.season_number.desc())
        )
        season = result.scalar_one_or_none()
    
    if not season:
        return ResponseSchema(success=True, data=[], message="暂无赛季数据")
    
    # 获取该赛季的杯赛
    result = await db.execute(
        select(CupCompetition).where(CupCompetition.season_id == season.id)
    )
    cups = result.scalars().all()
    
    # 获取冠军球队名称
    cup_list = []
    for cup in cups:
        winner_name = None
        if cup.winner_team_id:
            team_result = await db.execute(
                select(Team).where(Team.id == cup.winner_team_id)
            )
            winner_team = team_result.scalar_one_or_none()
            if winner_team:
                winner_name = winner_team.name
        
        cup_list.append({
            "id": cup.id,
            "name": cup.name,
            "code": cup.code,
            "season_id": cup.season_id,
            "season_number": season.season_number,
            "status": cup.status.value if hasattr(cup.status, 'value') else cup.status,
            "current_round": cup.current_round,
            "total_teams": cup.total_teams,
            "has_group_stage": cup.has_group_stage,
            "group_count": cup.group_count,
            "teams_per_group": cup.teams_per_group,
            "group_rounds": cup.group_rounds,
            "eligible_league_levels": cup.eligible_league_levels,
            "winner_team_id": cup.winner_team_id,
            "winner_team_name": winner_name,
        })
    
    return ResponseSchema(success=True, data=cup_list)


@router.get("/my-team", response_model=ResponseSchema[Optional[Dict[str, Any]]])
async def get_my_team_cup(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户球队参加的杯赛
    """
    if not current_user.team_id:
        return ResponseSchema(success=True, data=None, message="用户没有球队")
    
    # 获取当前赛季
    result = await db.execute(
        select(Season).where(Season.status == "ongoing").order_by(Season.season_number.desc())
    )
    season = result.scalar_one_or_none()
    
    if not season:
        return ResponseSchema(success=True, data=None, message="暂无进行中的赛季")
    
    # 获取用户球队
    result = await db.execute(
        select(Team).where(Team.id == current_user.team_id)
    )
    team = result.scalar_one_or_none()
    
    if not team:
        return ResponseSchema(success=True, data=None, message="球队不存在")
    
    # 查找包含该球队的杯赛（通过检查比赛记录）
    result = await db.execute(
        select(Fixture).where(
            and_(
                Fixture.season_id == season.id,
                or_(
                    Fixture.home_team_id == team.id,
                    Fixture.away_team_id == team.id
                ),
                Fixture.fixture_type.in_(["cup_lightning_group", "cup_lightning_knockout", "cup_jenny"])
            )
        ).limit(1)
    )
    fixture = result.scalar_one_or_none()
    
    if not fixture or not fixture.cup_competition_id:
        return ResponseSchema(success=True, data=None, message="球队未参加任何杯赛")
    
    # 获取杯赛详情
    result = await db.execute(
        select(CupCompetition).where(CupCompetition.id == fixture.cup_competition_id)
    )
    cup = result.scalar_one_or_none()
    
    if not cup:
        return ResponseSchema(success=True, data=None, message="杯赛不存在")
    
    winner_name = None
    if cup.winner_team_id:
        team_result = await db.execute(
            select(Team).where(Team.id == cup.winner_team_id)
        )
        winner_team = team_result.scalar_one_or_none()
        if winner_team:
            winner_name = winner_team.name
    
    return ResponseSchema(success=True, data={
        "id": cup.id,
        "name": cup.name,
        "code": cup.code,
        "season_id": cup.season_id,
        "season_number": season.season_number,
        "status": cup.status.value if hasattr(cup.status, 'value') else cup.status,
        "current_round": cup.current_round,
        "total_teams": cup.total_teams,
        "has_group_stage": cup.has_group_stage,
        "group_count": cup.group_count,
        "teams_per_group": cup.teams_per_group,
        "group_rounds": cup.group_rounds,
        "eligible_league_levels": cup.eligible_league_levels,
        "winner_team_id": cup.winner_team_id,
        "winner_team_name": winner_name,
    })


@router.get("/{cup_id}", response_model=ResponseSchema[Dict[str, Any]])
async def get_cup_detail(
    cup_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取杯赛详情
    """
    result = await db.execute(
        select(CupCompetition).where(CupCompetition.id == cup_id)
    )
    cup = result.scalar_one_or_none()
    
    if not cup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="杯赛不存在"
        )
    
    # 获取赛季信息
    result = await db.execute(
        select(Season).where(Season.id == cup.season_id)
    )
    season = result.scalar_one_or_none()
    
    # 获取冠军球队名称
    winner_name = None
    if cup.winner_team_id:
        team_result = await db.execute(
            select(Team).where(Team.id == cup.winner_team_id)
        )
        winner_team = team_result.scalar_one_or_none()
        if winner_team:
            winner_name = winner_team.name
    
    return ResponseSchema(success=True, data={
        "id": cup.id,
        "name": cup.name,
        "code": cup.code,
        "season_id": cup.season_id,
        "season_number": season.season_number if season else 0,
        "status": cup.status.value if hasattr(cup.status, 'value') else cup.status,
        "current_round": cup.current_round,
        "total_teams": cup.total_teams,
        "has_group_stage": cup.has_group_stage,
        "group_count": cup.group_count,
        "teams_per_group": cup.teams_per_group,
        "group_rounds": cup.group_rounds,
        "eligible_league_levels": cup.eligible_league_levels,
        "winner_team_id": cup.winner_team_id,
        "winner_team_name": winner_name,
    })


@router.get("/{cup_id}/groups", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_cup_groups(
    cup_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取杯赛小组赛分组
    """
    result = await db.execute(
        select(CupCompetition).where(CupCompetition.id == cup_id)
    )
    cup = result.scalar_one_or_none()
    
    if not cup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="杯赛不存在"
        )
    
    # 获取所有小组
    result = await db.execute(
        select(CupGroup).where(CupGroup.competition_id == cup_id)
    )
    groups = result.scalars().all()
    
    group_list = []
    for group in groups:
        # 获取球队信息
        teams = []
        for team_id in group.team_ids:
            team_result = await db.execute(
                select(Team).where(Team.id == team_id)
            )
            team = team_result.scalar_one_or_none()
            if team:
                teams.append({"id": team.id, "name": team.name})
        
        group_list.append({
            "id": group.id,
            "competition_id": group.competition_id,
            "name": group.name,
            "team_ids": group.team_ids,
            "teams": teams,
            "standings": group.standings,
            "qualified_team_ids": group.qualified_team_ids,
        })
    
    return ResponseSchema(success=True, data=group_list)


@router.get("/{cup_id}/fixtures", response_model=ResponseSchema[List[Dict[str, Any]]])
async def get_cup_fixtures(
    cup_id: str,
    stage: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取杯赛赛程
    """
    result = await db.execute(
        select(CupCompetition).where(CupCompetition.id == cup_id)
    )
    cup = result.scalar_one_or_none()
    
    if not cup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="杯赛不存在"
        )
    
    # 构建查询
    query = select(Fixture).where(Fixture.cup_competition_id == cup_id)
    if stage:
        query = query.where(Fixture.cup_stage == stage)
    
    query = query.order_by(Fixture.season_day, Fixture.id)
    
    result = await db.execute(query)
    fixtures = result.scalars().all()
    
    fixture_list = []
    for fixture in fixtures:
        # 获取球队名称
        home_team_result = await db.execute(
            select(Team).where(Team.id == fixture.home_team_id)
        )
        home_team = home_team_result.scalar_one_or_none()
        
        away_team_result = await db.execute(
            select(Team).where(Team.id == fixture.away_team_id)
        )
        away_team = away_team_result.scalar_one_or_none()
        
        fixture_list.append({
            "id": fixture.id,
            "season_day": fixture.season_day,
            "round_number": fixture.round_number,
            "fixture_type": fixture.fixture_type.value if hasattr(fixture.fixture_type, 'value') else fixture.fixture_type,
            "home_team": {
                "id": fixture.home_team_id,
                "name": home_team.name if home_team else "未知球队"
            },
            "away_team": {
                "id": fixture.away_team_id,
                "name": away_team.name if away_team else "未知球队"
            },
            "home_score": fixture.home_score,
            "away_score": fixture.away_score,
            "status": fixture.status.value if hasattr(fixture.status, 'value') else fixture.status,
            "cup_stage": fixture.cup_stage,
            "cup_group_name": fixture.cup_group_name,
            "scheduled_at": fixture.scheduled_at.isoformat() if fixture.scheduled_at else None,
        })
    
    return ResponseSchema(success=True, data=fixture_list)


@router.get("/{cup_id}/bracket", response_model=ResponseSchema[Dict[str, List[Dict[str, Any]]]])
async def get_cup_bracket(
    cup_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    获取杯赛淘汰赛对阵表
    """
    result = await db.execute(
        select(CupCompetition).where(CupCompetition.id == cup_id)
    )
    cup = result.scalar_one_or_none()
    
    if not cup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="杯赛不存在"
        )
    
    # 获取所有淘汰赛比赛（包含杰尼杯的预选赛 ROUND_48）
    stages = ["ROUND_48", "ROUND_32", "ROUND_16", "QUARTER", "SEMI", "FINAL"]
    bracket = {stage.lower(): [] for stage in stages}
    
    for stage in stages:
        result = await db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_competition_id == cup_id,
                    Fixture.cup_stage == stage
                )
            ).order_by(Fixture.id)
        )
        fixtures = result.scalars().all()
        
        for fixture in fixtures:
            # 获取球队名称
            home_team_result = await db.execute(
                select(Team).where(Team.id == fixture.home_team_id)
            )
            home_team = home_team_result.scalar_one_or_none()
            
            away_team_result = await db.execute(
                select(Team).where(Team.id == fixture.away_team_id)
            )
            away_team = away_team_result.scalar_one_or_none()
            
            bracket[stage.lower()].append({
                "id": fixture.id,
                "season_day": fixture.season_day,
                "round_number": fixture.round_number,
                "fixture_type": fixture.fixture_type.value if hasattr(fixture.fixture_type, 'value') else fixture.fixture_type,
                "home_team": {
                    "id": fixture.home_team_id,
                    "name": home_team.name if home_team else "未知球队"
                },
                "away_team": {
                    "id": fixture.away_team_id,
                    "name": away_team.name if away_team else "未知球队"
                },
                "home_score": fixture.home_score,
                "away_score": fixture.away_score,
                "status": fixture.status.value if hasattr(fixture.status, 'value') else fixture.status,
                "cup_stage": fixture.cup_stage,
                "scheduled_at": fixture.scheduled_at.isoformat() if fixture.scheduled_at else None,
            })
    
    return ResponseSchema(success=True, data=bracket)
