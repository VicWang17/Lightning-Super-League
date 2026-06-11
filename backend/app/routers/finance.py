"""
Finance API routes - 经济系统相关接口
"""
from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas import (
    ResponseSchema,
    PaginatedResponse,
    FinanceOverview,
    FinanceTransactionItem,
    FinanceTransactionListParams,
    TransactionSourceType,
    TransactionDirection,
    BudgetPolicy,
    SponsorPolicy,
    BudgetPlanSchema,
    SponsorContractSchema,
    SponsorOption,
    ReserveStatusSchema,
)
from app.dependencies import get_db, get_current_user
from app.services.finance_service import FinanceService
from app.core.logging import get_logger

router = APIRouter(prefix="/teams", tags=["财务"])
logger = get_logger("app.finance")


@router.get(
    "/{team_id}/finance/overview",
    response_model=ResponseSchema[FinanceOverview],
    summary="获取球队财务概览",
    description="获取指定球队的当前赛季财务概览，包括余额、预算、收入支出统计、工资帽等",
)
async def get_finance_overview(
    team_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，不传则使用当前赛季"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取球队财务概览"""
    user_id = current_user.id
    logger.info(f"获取财务概览: team_id={team_id}, user_id={user_id}")
    
    service = FinanceService(db)
    try:
        overview_data = await service.get_overview(team_id, season_id)
        return ResponseSchema(success=True, data=overview_data)
    except ValueError as e:
        logger.warning(f"获取财务概览失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{team_id}/finance/transactions",
    response_model=ResponseSchema[PaginatedResponse[FinanceTransactionItem]],
    summary="获取财务交易记录",
    description="获取指定球队的财务交易流水，支持按赛季、类型、方向筛选和分页",
)
async def get_finance_transactions(
    team_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID"),
    source_type: Optional[TransactionSourceType] = Query(None, description="交易来源类型"),
    direction: Optional[TransactionDirection] = Query(None, description="交易方向: income/expense"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取财务交易记录"""
    user_id = current_user.id
    logger.info(f"获取交易记录: team_id={team_id}, user_id={user_id}, season_id={season_id}")
    
    service = FinanceService(db)
    result = await service.get_transactions(
        team_id=team_id,
        season_id=season_id,
        source_type=source_type,
        direction=direction,
        page=page,
        page_size=page_size,
    )
    
    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(
            items=result["items"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        ),
    )


# =====================================================================
# Phase 3: 预算与赞助商 API
# =====================================================================

@router.get(
    "/{team_id}/finance/budget-plan",
    response_model=ResponseSchema[BudgetPlanSchema],
    summary="获取预算计划",
    description="获取指定球队的目标赛季预算计划",
)
async def get_budget_plan(
    team_id: str,
    target_season_id: str = Query(..., description="目标赛季ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取预算计划"""
    service = FinanceService(db)
    plan = await service.get_budget_plan(team_id, target_season_id)
    if not plan:
        raise HTTPException(status_code=404, detail="预算计划不存在")
    
    return ResponseSchema(
        success=True,
        data=BudgetPlanSchema(
            team_id=plan.team_id,
            target_season_id=plan.target_season_id,
            policy=plan.policy.value,
            transfer_pct=plan.transfer_pct,
            youth_pct=plan.youth_pct,
            wage_pct=plan.wage_pct,
            reserve_pct=plan.reserve_pct,
            is_player_confirmed=plan.is_player_confirmed,
            locked_at=plan.locked_at,
        )
    )


@router.post(
    "/{team_id}/finance/budget-plan",
    response_model=ResponseSchema[BudgetPlanSchema],
    summary="确认预算计划",
    description="球员确认或修改预算计划",
)
async def confirm_budget_plan(
    team_id: str,
    target_season_id: str = Query(..., description="目标赛季ID"),
    policy: BudgetPolicy = Query(..., description="预算策略"),
    transfer_pct: int = Query(..., ge=0, le=100, description="转会预算百分比"),
    youth_pct: int = Query(..., ge=0, le=100, description="青训预算百分比"),
    wage_pct: int = Query(..., ge=0, le=100, description="工资预算百分比"),
    reserve_pct: int = Query(..., ge=0, le=100, description="储备预算百分比"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """确认预算计划"""
    if transfer_pct + youth_pct + wage_pct + reserve_pct != 100:
        raise HTTPException(status_code=400, detail="预算分配百分比总和必须等于 100")
    
    service = FinanceService(db)
    try:
        plan = await service.confirm_budget_plan(
            team_id, target_season_id, policy,
            transfer_pct, youth_pct, wage_pct, reserve_pct
        )
        await db.commit()
        return ResponseSchema(
            success=True,
            data=BudgetPlanSchema(
                team_id=plan.team_id,
                target_season_id=plan.target_season_id,
                policy=plan.policy.value,
                transfer_pct=plan.transfer_pct,
                youth_pct=plan.youth_pct,
                wage_pct=plan.wage_pct,
                reserve_pct=plan.reserve_pct,
                is_player_confirmed=plan.is_player_confirmed,
                locked_at=plan.locked_at,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{team_id}/finance/sponsor-options",
    response_model=ResponseSchema[List[SponsorOption]],
    summary="获取赞助商选项",
    description="获取指定球队的赞助商选择方案（稳定型 vs 绩效型）",
)
async def get_sponsor_options(
    team_id: str,
    season_id: str = Query(..., description="赛季ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取赞助商选项"""
    service = FinanceService(db)
    options = await service.generate_sponsor_options(team_id, season_id)
    return ResponseSchema(success=True, data=options)


@router.post(
    "/{team_id}/finance/sponsor-contract",
    response_model=ResponseSchema[SponsorContractSchema],
    summary="签署赞助合同",
    description="选择并签署赞助商合同",
)
async def sign_sponsor_contract(
    team_id: str,
    season_id: str = Query(..., description="赛季ID"),
    policy: SponsorPolicy = Query(..., description="赞助商策略: stable/performance"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """签署赞助合同"""
    service = FinanceService(db)
    try:
        contract = await service.sign_sponsor_contract(team_id, season_id, policy)
        await db.commit()
        return ResponseSchema(
            success=True,
            data=SponsorContractSchema(
                team_id=contract.team_id,
                season_id=contract.season_id,
                policy=contract.policy.value,
                base_amount=contract.base_amount,
                win_bonus=contract.win_bonus,
                draw_bonus=contract.draw_bonus,
                max_bonus=contract.max_bonus,
                health_modifier_pct=contract.health_modifier_pct,
                status=contract.status.value,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{team_id}/finance/sponsor-contract",
    response_model=ResponseSchema[SponsorContractSchema],
    summary="获取当前赞助合同",
    description="获取指定球队当前赛季的赞助合同",
)
async def get_sponsor_contract(
    team_id: str,
    season_id: str = Query(..., description="赛季ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前赞助合同"""
    service = FinanceService(db)
    contract = await service._get_active_sponsor_contract(team_id, season_id)
    if not contract:
        raise HTTPException(status_code=404, detail="未找到赞助合同")
    
    return ResponseSchema(
        success=True,
        data=SponsorContractSchema(
            team_id=contract.team_id,
            season_id=contract.season_id,
            policy=contract.policy.value,
            base_amount=contract.base_amount,
            win_bonus=contract.win_bonus,
            draw_bonus=contract.draw_bonus,
            max_bonus=contract.max_bonus,
            health_modifier_pct=contract.health_modifier_pct,
            status=contract.status.value,
        )
    )


@router.get(
    "/{team_id}/finance/reserve",
    response_model=ResponseSchema[ReserveStatusSchema],
    summary="获取风险准备金状态",
    description="获取球队风险准备金的可用额、已用额、风险等级等",
)
async def get_reserve_status(
    team_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，不传则使用当前赛季"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取风险准备金状态"""
    from app.services.injury_treatment_service import InjuryTreatmentService
    
    service = InjuryTreatmentService(db)
    if not season_id:
        season_id = await service._get_current_season_id(team_id)
    if not season_id:
        raise HTTPException(status_code=404, detail="未找到赛季")
    
    status_data = await service.get_reserve_status(team_id, season_id)
    return ResponseSchema(success=True, data=ReserveStatusSchema(**status_data))


@router.post(
    "/{team_id}/finance/initialize",
    response_model=ResponseSchema[dict],
    summary="初始化赛季财务（开发/管理接口）",
    description="为指定球队初始化当前赛季财务快照",
    include_in_schema=False,
)
async def initialize_season_finance(
    team_id: str,
    season_id: Optional[str] = Query(None, description="赛季ID，不传则使用当前赛季"),
    db: AsyncSession = Depends(get_db),
):
    """初始化赛季财务（开发调试用）"""
    from app.models.season import Season
    from sqlalchemy import select, desc
    
    service = FinanceService(db)
    
    if not season_id:
        result = await db.execute(select(Season).order_by(desc(Season.season_number)).limit(1))
        season = result.scalar_one_or_none()
        if not season:
            raise HTTPException(status_code=404, detail="没有找到赛季")
        season_id = season.id
    
    season_finance = await service.initialize_season_finance(team_id, season_id)
    
    return ResponseSchema(
        success=True,
        message="赛季财务已初始化",
        data={
            "team_id": team_id,
            "season_id": season_id,
            "opening_balance": str(season_finance.opening_balance),
            "current_balance": str(season_finance.current_balance),
        },
    )
