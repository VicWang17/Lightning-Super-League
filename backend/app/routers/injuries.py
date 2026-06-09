"""
Injury treatment API routes - 伤病医疗加速接口
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user
from app.schemas import (
    ResponseSchema,
    TreatmentOptionSchema,
    TreatmentApplyRequest,
    TreatmentApplyResponse,
)
from app.services.injury_treatment_service import InjuryTreatmentService
from app.core.logging import get_logger

router = APIRouter(prefix="/teams", tags=["伤病医疗"])
logger = get_logger("app.injuries")


@router.get(
    "/{team_id}/injuries/{injury_id}/treatment-options",
    response_model=ResponseSchema[List[TreatmentOptionSchema]],
    summary="获取治疗方案选项",
    description="获取某次伤病的可选医疗方案、费用和副作用",
)
async def get_treatment_options(
    team_id: str,
    injury_id: str,
    player_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取治疗方案选项"""
    service = InjuryTreatmentService(db)
    try:
        options = await service.list_treatment_options(team_id, player_id, injury_id)
        # 转换为 Pydantic schema
        schema_items = [TreatmentOptionSchema(**opt) for opt in options]
        return ResponseSchema(success=True, data=schema_items)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{team_id}/injuries/{injury_id}/treat",
    response_model=ResponseSchema[TreatmentApplyResponse],
    summary="执行治疗方案",
    description="对伤病执行选定的医疗方案，扣款并缩短恢复天数",
)
async def apply_treatment(
    team_id: str,
    injury_id: str,
    player_id: str,
    req: TreatmentApplyRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """执行治疗"""
    from app.models.injury_treatment import TreatmentPlan

    service = InjuryTreatmentService(db)
    try:
        plan = TreatmentPlan(req.plan.value)
        result = await service.apply_treatment(team_id, player_id, injury_id, plan)
        await db.commit()
        return ResponseSchema(
            success=True,
            data=TreatmentApplyResponse(**result),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
