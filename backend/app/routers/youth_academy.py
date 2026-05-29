"""
Youth Academy API - 青训营路由
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 11.1 节实现。
"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas import BaseSchema, ResponseSchema, PaginatedResponse, ErrorResponse
from app.models import SquadRole
from app.services.youth_academy_service import YouthAcademyService
from app.core.logging import get_logger

router = APIRouter(prefix="/youth", tags=["青训营"])
logger = get_logger("app.youth_academy_router")


# =====================================================================
# GET /teams/{team_id}/youth/academy
# =====================================================================

@router.get(
    "/teams/{team_id}/youth/academy",
    response_model=ResponseSchema[dict],
    summary="青训营列表",
)
async def list_academy(
    team_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，默认当前赛季"),
    db: AsyncSession = Depends(get_db),
):
    """获取球队青训营列表、在营人数、预算信息"""
    service = YouthAcademyService(db)
    data = await service.list_academy(team_id, season_id)
    return ResponseSchema(success=True, data=data)


# =====================================================================
# POST /youth/academy/{academy_player_id}/preview-signing
# =====================================================================

class YouthPreviewRequest(BaseSchema):
    """青训签约预览请求"""
    team_id: str
    years: int
    wage: Decimal
    squad_role: Optional[SquadRole] = SquadRole.YOUNGSTER


@router.post(
    "/academy/{academy_player_id}/preview-signing",
    response_model=ResponseSchema[dict],
    summary="青训签约预览",
)
async def preview_youth_signing(
    academy_player_id: str,
    req: YouthPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """预览青训球员签约入一线队（含 ROOKIE 折扣）"""
    service = YouthAcademyService(db)
    try:
        preview = await service.preview_signing(
            academy_player_id=academy_player_id,
            team_id=req.team_id,
            years=req.years,
            wage=req.wage,
            squad_role=req.squad_role or SquadRole.YOUNGSTER,
        )
        return ResponseSchema(success=True, data=preview)
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# POST /youth/academy/{academy_player_id}/sign
# =====================================================================

class YouthSignRequest(BaseSchema):
    """青训签约请求"""
    team_id: str
    years: int
    wage: Decimal
    squad_role: Optional[SquadRole] = SquadRole.YOUNGSTER


@router.post(
    "/academy/{academy_player_id}/sign",
    response_model=ResponseSchema[dict],
    summary="青训签约",
)
async def sign_youth_player(
    academy_player_id: str,
    req: YouthSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """签约青训球员入一线队"""
    service = YouthAcademyService(db)
    try:
        result = await service.sign_player(
            academy_player_id=academy_player_id,
            team_id=req.team_id,
            years=req.years,
            wage=req.wage,
            squad_role=req.squad_role or SquadRole.YOUNGSTER,
        )
        return ResponseSchema(success=True, data=result)
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# POST /youth/academy/{academy_player_id}/release
# =====================================================================

@router.post(
    "/academy/{academy_player_id}/release",
    response_model=ResponseSchema[dict],
    summary="放弃青训球员",
)
async def release_youth_player(
    academy_player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """放弃青训球员，使其进入选秀候选"""
    service = YouthAcademyService(db)
    try:
        result = await service.release_to_draft(academy_player_id)
        return ResponseSchema(success=True, data=result)
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# GET /youth/academy/{academy_player_id}/growth
# =====================================================================

@router.get(
    "/academy/{academy_player_id}/growth",
    response_model=ResponseSchema[list],
    summary="成长曲线",
)
async def get_youth_growth(
    academy_player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取青训球员的成长曲线"""
    service = YouthAcademyService(db)
    curve = await service.get_growth_curve(academy_player_id)
    return ResponseSchema(success=True, data=curve)
