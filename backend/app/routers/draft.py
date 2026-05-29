"""
Draft API - 选秀系统路由
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 11.2 节实现。
"""
from typing import Optional, List
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas import BaseSchema, ResponseSchema, ErrorResponse
from app.models import SquadRole
from app.services.draft_service import DraftService
from app.core.logging import get_logger

router = APIRouter(prefix="/draft", tags=["选秀大会"])
logger = get_logger("app.draft_router")


# =====================================================================
# GET /leagues/{league_id}/draft
# =====================================================================

@router.get(
    "/leagues/{league_id}/draft",
    response_model=ResponseSchema[dict],
    summary="联赛选秀池",
)
async def get_draft_pool(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，默认当前赛季"),
    db: AsyncSession = Depends(get_db),
):
    """获取联赛选秀池及球员列表"""
    service = DraftService(db)
    data = await service.get_draft_pool(league_id, season_id)
    return ResponseSchema(success=True, data=data)


# =====================================================================
# GET /teams/{team_id}/draft/preferences
# =====================================================================

@router.get(
    "/teams/{team_id}/draft/preferences",
    response_model=ResponseSchema[list],
    summary="我的选秀志愿",
)
async def get_draft_preferences(
    team_id: str,
    draft_pool_id: str = Query(..., description="选秀池ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取球队选秀志愿排序"""
    service = DraftService(db)
    prefs = await service.get_team_preferences(draft_pool_id, team_id)
    return ResponseSchema(success=True, data=prefs)


# =====================================================================
# PUT /teams/{team_id}/draft/preferences
# =====================================================================

class PreferenceItem(BaseSchema):
    player_id: str
    priority: int
    excluded: bool = False


class SavePreferencesRequest(BaseSchema):
    draft_pool_id: str
    preferences: List[PreferenceItem]


@router.put(
    "/teams/{team_id}/draft/preferences",
    response_model=ResponseSchema[dict],
    summary="保存选秀志愿",
)
async def save_draft_preferences(
    team_id: str,
    req: SavePreferencesRequest,
    db: AsyncSession = Depends(get_db),
):
    """保存球队选秀志愿排序"""
    service = DraftService(db)
    prefs = [{"player_id": p.player_id, "priority": p.priority, "excluded": p.excluded} for p in req.preferences]
    result = await service.save_preferences(req.draft_pool_id, team_id, prefs)
    return ResponseSchema(success=True, data=result)


# =====================================================================
# GET /leagues/{league_id}/draft/results
# =====================================================================

@router.get(
    "/leagues/{league_id}/draft/results",
    response_model=ResponseSchema[dict],
    summary="选秀结果",
)
async def get_draft_results(
    league_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，默认当前赛季"),
    db: AsyncSession = Depends(get_db),
):
    """获取联赛选秀结果"""
    service = DraftService(db)
    data = await service.get_draft_results(league_id, season_id)
    return ResponseSchema(success=True, data=data)


# =====================================================================
# GET /teams/{team_id}/draft/selections
# =====================================================================

@router.get(
    "/teams/{team_id}/draft/selections",
    response_model=ResponseSchema[list],
    summary="本队待签约选秀结果",
)
async def get_team_draft_selections(
    team_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，默认当前赛季"),
    db: AsyncSession = Depends(get_db),
):
    """获取本队待签约的选秀球员"""
    service = DraftService(db)
    data = await service.get_team_selections(team_id, season_id)
    return ResponseSchema(success=True, data=data)


# =====================================================================
# POST /draft/selections/{selection_id}/preview-signing
# =====================================================================

class DraftPreviewRequest(BaseSchema):
    team_id: str
    years: int
    wage: Decimal
    squad_role: Optional[SquadRole] = SquadRole.YOUNGSTER


@router.post(
    "/selections/{selection_id}/preview-signing",
    response_model=ResponseSchema[dict],
    summary="选秀球员签约预览",
)
async def preview_draft_signing(
    selection_id: str,
    req: DraftPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """预览选秀球员签约"""
    service = DraftService(db)
    try:
        preview = await service.preview_signing(
            selection_id=selection_id,
            team_id=req.team_id,
            years=req.years,
            wage=req.wage,
            squad_role=req.squad_role or SquadRole.YOUNGSTER,
        )
        return ResponseSchema(success=True, data=preview)
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# POST /draft/selections/{selection_id}/sign
# =====================================================================

class DraftSignRequest(BaseSchema):
    team_id: str
    years: int
    wage: Decimal
    squad_role: Optional[SquadRole] = SquadRole.YOUNGSTER


@router.post(
    "/selections/{selection_id}/sign",
    response_model=ResponseSchema[dict],
    summary="签约选秀球员",
)
async def sign_draft_player(
    selection_id: str,
    req: DraftSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """签约选秀球员入一线队"""
    service = DraftService(db)
    try:
        result = await service.sign_selection(
            selection_id=selection_id,
            team_id=req.team_id,
            years=req.years,
            wage=req.wage,
            squad_role=req.squad_role or SquadRole.YOUNGSTER,
        )
        return ResponseSchema(success=True, data=result)
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# POST /draft/selections/{selection_id}/decline
# =====================================================================

@router.post(
    "/selections/{selection_id}/decline",
    response_model=ResponseSchema[dict],
    summary="放弃选秀球员",
)
async def decline_draft_player(
    selection_id: str,
    db: AsyncSession = Depends(get_db),
):
    """放弃选秀球员，使其进入自由市场"""
    service = DraftService(db)
    try:
        result = await service.decline_selection(selection_id)
        return ResponseSchema(success=True, data=result)
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# POST /internal/draft/selections/expire
# =====================================================================

@router.post(
    "/internal/draft/selections/expire",
    response_model=ResponseSchema[dict],
    summary="处理到期选秀签约（内部）",
)
async def expire_draft_selections(
    season_id: str = Query(..., description="赛季ID"),
    db: AsyncSession = Depends(get_db),
):
    """处理 24 小时到期的待签约选秀结果"""
    service = DraftService(db)
    result = await service.expire_pending_selections(season_id)
    return ResponseSchema(success=True, data=result)
