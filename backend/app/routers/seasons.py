"""
Season routers - 赛季管理API
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select

from app.dependencies import get_db
from app.services.season_service import SeasonService
from app.models.season import Season
from app.schemas import ResponseSchema
from app.schemas.season import (
    SeasonCreateRequest,
    SeasonResponse,
    SeasonDetailResponse,
    SeasonDayResponse,
    SeasonCalendarResponse,
    TeamFixtureResponse,
    TodayFixtureResponse,
)

router = APIRouter(prefix="/seasons", tags=["赛季"])


async def get_season_service(db: AsyncSession = Depends(get_db)) -> SeasonService:
    """依赖注入：获取赛季服务"""
    return SeasonService(db)


@router.get("", response_model=ResponseSchema[list[SeasonResponse]])
async def list_seasons(
    db: AsyncSession = Depends(get_db)
):
    """获取所有赛季列表（按赛季编号降序）"""
    result = await db.execute(
        select(Season).order_by(Season.season_number.desc())
    )
    seasons = result.scalars().all()
    return ResponseSchema(
        success=True,
        data=[SeasonResponse.from_orm(s) for s in seasons]
    )


@router.post("", response_model=ResponseSchema[SeasonResponse], status_code=status.HTTP_201_CREATED)
async def create_season(
    request: Optional[SeasonCreateRequest] = None,
    service: SeasonService = Depends(get_season_service)
):
    """
    创建新赛季
    
    - 自动生成所有联赛和杯赛的完整赛程
    - 联赛：30轮双循环
    - 闪电杯：64队，小组赛3轮+淘汰赛5轮
    - 杰尼杯：192队，首轮+淘汰赛7轮
    - 总时长：42天
    """
    start_date = request.start_date if request else None
    season = await service.create_new_season(start_date)
    return ResponseSchema(
        success=True,
        message="赛季创建成功",
        data=SeasonResponse.from_orm(season)
    )


@router.get("/current", response_model=ResponseSchema[SeasonDetailResponse])
async def get_current_season(
    service: SeasonService = Depends(get_season_service)
):
    """获取当前进行中的赛季详情"""
    season = await service.get_current_season()
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="当前没有进行中的赛季"
        )
    return ResponseSchema(
        success=True,
        data=SeasonDetailResponse.from_orm(season)
    )


@router.get("/{season_number}", response_model=ResponseSchema[SeasonDetailResponse])
async def get_season_by_number(
    season_number: int,
    service: SeasonService = Depends(get_season_service)
):
    """根据赛季编号获取赛季详情"""
    season = await service.get_season_by_number(season_number)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到第{season_number}赛季"
        )
    return ResponseSchema(
        success=True,
        data=SeasonDetailResponse.from_orm(season)
    )


@router.post("/{season_number}/start", response_model=ResponseSchema[SeasonResponse])
async def start_season(
    season_number: int,
    service: SeasonService = Depends(get_season_service)
):
    """启动赛季（将状态从PENDING改为ONGOING）"""
    season = await service.get_season_by_number(season_number)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到第{season_number}赛季"
        )
    
    await service.start_season(season)
    return ResponseSchema(
        success=True,
        message="赛季启动成功",
        data=SeasonResponse.from_orm(season)
    )


@router.post("/{season_number}/next-day", response_model=ResponseSchema[SeasonDayResponse])
async def process_next_day(
    season_number: int,
    service: SeasonService = Depends(get_season_service)
):
    """
    处理下一天的比赛（手动触发）
    
    - 推进赛季天数
    - 获取当天所有比赛
    - 模拟比赛并更新结果
    - 返回比赛结果汇总
    """
    season = await service.get_season_by_number(season_number)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到第{season_number}赛季"
        )
    
    result = await service.process_next_day(season)
    return ResponseSchema(
        success=True,
        message=f"已处理第{season.current_day}天比赛",
        data=SeasonDayResponse(
            season_number=season.season_number,
            current_day=season.current_day,
            status=season.status.value,
            fixtures_processed=result["fixtures_processed"],
            results=result["results"]
        )
    )


@router.get("/{season_number}/calendar", response_model=ResponseSchema[SeasonCalendarResponse])
async def get_season_calendar(
    season_number: int,
    team_id: Optional[str] = None,
    service: SeasonService = Depends(get_season_service)
):
    """获取赛季日历"""
    season = await service.get_season_by_number(season_number)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到第{season_number}赛季"
        )
    
    calendar = await service.get_season_calendar(season, team_id)
    return ResponseSchema(
        success=True,
        data=SeasonCalendarResponse(
            season_number=season.season_number,
            team_id=team_id,
            calendar=calendar
        )
    )


@router.get("/{season_number}/teams/{team_id}/fixtures", response_model=ResponseSchema[TeamFixtureResponse])
async def get_team_fixtures(
    season_number: int,
    team_id: str,
    fixture_type: Optional[str] = None,
    service: SeasonService = Depends(get_season_service)
):
    """获取某支球队在赛季中的所有比赛"""
    from app.models.season import FixtureType
    
    season = await service.get_season_by_number(season_number)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到第{season_number}赛季"
        )
    
    fixture_type_enum = None
    if fixture_type:
        try:
            fixture_type_enum = FixtureType(fixture_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的比赛类型: {fixture_type}"
            )
    
    fixtures = await service.get_team_fixtures(season, team_id, fixture_type_enum)
    
    return ResponseSchema(
        success=True,
        data=TeamFixtureResponse(
            season_number=season.season_number,
            team_id=team_id,
            fixtures=[
                {
                    "id": f.id,
                    "day": f.season_day,
                    "type": f.fixture_type.value,
                    "round": f.round_number,
                    "home_team_id": f.home_team_id,
                    "away_team_id": f.away_team_id,
                    "home_score": f.home_score,
                    "away_score": f.away_score,
                    "status": f.status.value,
                    "scheduled_at": f.scheduled_at.isoformat(),
                }
                for f in fixtures
            ]
        )
    )


@router.get("/{season_number}/today", response_model=ResponseSchema[TodayFixtureResponse])
async def get_today_fixtures(
    season_number: int,
    service: SeasonService = Depends(get_season_service)
):
    """获取今天的所有比赛"""
    season = await service.get_season_by_number(season_number)
    if not season:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到第{season_number}赛季"
        )
    
    fixtures = await service.get_today_fixtures(season)
    
    return ResponseSchema(
        success=True,
        data=TodayFixtureResponse(
            season_number=season.season_number,
            current_day=season.current_day,
            fixtures=[
                {
                    "id": f.id,
                    "type": f.fixture_type.value,
                    "round": f.round_number,
                    "home_team_id": f.home_team_id,
                    "away_team_id": f.away_team_id,
                    "home_score": f.home_score,
                    "away_score": f.away_score,
                    "status": f.status.value,
                    "cup_stage": f.cup_stage,
                    "cup_group": f.cup_group_name,
                }
                for f in fixtures
            ]
        )
    )
