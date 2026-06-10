"""
Training system API routes
按设计文档 TRAINING-SYSTEM-DESIGN.md 第 17 章实现。
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.dependencies import get_db
from app.schemas import ResponseSchema, PaginatedResponse
from app.schemas.training import (
    TrainingItemSchema,
    TrainingPlanSlotSchema,
    TrainingPlanSaveRequest,
    TemplateApplyRequest,
    TrainingResultSchema,
    TrainingDailySummarySchema,
    PlayerFatigueSchema,
    PlayerTrainingProgressSchema,
    AutoGroupResponse,
    TrainingTemplateSchema,
    PlayerFatigueBatchResponse,
)
from app.models import (
    Player, Team, Season,
    TeamTrainingPlan, TrainingResult, TrainingSlot,
)
from app.services.training_service import TrainingService
from app.services.player_fatigue_service import PlayerFatigueService
from app.core.training_config import (
    list_training_items, list_templates, get_training_item,
)
from app.core.logging import get_logger

logger = get_logger("app.training_router")
router = APIRouter(prefix="/training", tags=["训练"])


# =====================================================================
# 训练内容
# =====================================================================

@router.get(
    "/items",
    response_model=ResponseSchema[List[TrainingItemSchema]],
    summary="获取训练内容列表",
)
async def get_training_items(
    category: Optional[str] = Query(None, description="分类筛选"),
):
    """获取所有训练内容"""
    items = list_training_items(category=category)
    return ResponseSchema(
        success=True,
        data=[
            TrainingItemSchema(
                id=i.id,
                name=i.name,
                category=i.category,
                recommended_group=i.recommended_group,
                base_gain=i.base_gain,
                intensity=i.intensity,
                fitness_delta=i.fitness_delta,
                fatigue_delta=i.fatigue_delta,
                load_points=i.load_points,
                attribute_weights=i.attribute_weights,
                position_fit=i.position_fit,
                is_recovery=i.is_recovery,
            )
            for i in items
        ],
    )


@router.get(
    "/templates",
    response_model=ResponseSchema[List[TrainingTemplateSchema]],
    summary="获取训练套餐列表",
)
async def get_training_templates():
    """获取所有训练套餐"""
    templates = list_templates()
    return ResponseSchema(
        success=True,
        data=[
            TrainingTemplateSchema(id=t.id, name=t.name, description=t.description)
            for t in templates
        ],
    )


# =====================================================================
# 训练计划
# =====================================================================

@router.get(
    "/teams/{team_id}/plan",
    response_model=ResponseSchema[List[TrainingPlanSlotSchema]],
    summary="获取球队训练计划",
)
async def get_team_training_plan(
    team_id: str,
    season_id: str = Query(..., description="赛季ID"),
    start_day: int = Query(..., description="开始天数"),
    days: int = Query(7, ge=1, le=14, description="天数"),
    db: AsyncSession = Depends(get_db),
):
    """获取球队未来训练计划"""
    service = TrainingService(db)
    plans = await service.get_team_training_plan(team_id, season_id, start_day, days)
    
    data = []
    for p in plans:
        item = get_training_item(p.training_item_id) if p.training_item_id else None
        data.append(TrainingPlanSlotSchema(
            id=p.id,
            team_id=p.team_id,
            season_id=p.season_id,
            season_day=p.season_day,
            slot=TrainingSlot(p.slot.value if hasattr(p.slot, 'value') else p.slot),
            mode=p.mode,
            training_item_id=p.training_item_id,
            groups=p.groups,
            status=p.status.value,
            created_by=p.created_by.value,
            training_item=TrainingItemSchema(
                id=item.id,
                name=item.name,
                category=item.category,
                recommended_group=item.recommended_group,
                base_gain=item.base_gain,
                intensity=item.intensity,
                fitness_delta=item.fitness_delta,
                fatigue_delta=item.fatigue_delta,
                load_points=item.load_points,
                attribute_weights=item.attribute_weights,
                position_fit=item.position_fit,
                is_recovery=item.is_recovery,
            ) if item else None,
        ))
    
    return ResponseSchema(success=True, data=data)


@router.put(
    "/teams/{team_id}/plan",
    response_model=ResponseSchema[List[TrainingPlanSlotSchema]],
    summary="保存训练计划",
)
async def save_team_training_plan(
    team_id: str,
    req: TrainingPlanSaveRequest,
    db: AsyncSession = Depends(get_db),
):
    """保存或更新训练计划"""
    service = TrainingService(db)
    plans = await service.save_training_plan(team_id, req.season_id, req.items)
    
    return ResponseSchema(
        success=True,
        data=[
            TrainingPlanSlotSchema(
                id=p.id,
                team_id=p.team_id,
                season_id=p.season_id,
                season_day=p.season_day,
                slot=TrainingSlot(p.slot.value if hasattr(p.slot, 'value') else p.slot),
                mode=p.mode,
                training_item_id=p.training_item_id,
                groups=p.groups,
                status=p.status.value,
                created_by=p.created_by.value,
            )
            for p in plans
        ],
    )


@router.post(
    "/teams/{team_id}/templates/{template_id}/apply",
    response_model=ResponseSchema[List[TrainingPlanSlotSchema]],
    summary="套用训练套餐",
)
async def apply_template(
    team_id: str,
    template_id: str,
    req: TemplateApplyRequest,
    db: AsyncSession = Depends(get_db),
):
    """套用训练套餐到指定日期范围"""
    service = TrainingService(db)
    plans = await service.apply_template(team_id, req.season_id, template_id, req.start_day)
    
    return ResponseSchema(
        success=True,
        data=[
            TrainingPlanSlotSchema(
                id=p.id,
                team_id=p.team_id,
                season_id=p.season_id,
                season_day=p.season_day,
                slot=TrainingSlot(p.slot.value if hasattr(p.slot, 'value') else p.slot),
                mode=p.mode,
                training_item_id=p.training_item_id,
                groups=p.groups,
                status=p.status.value,
                created_by=p.created_by.value,
            )
            for p in plans
        ],
    )


@router.post(
    "/teams/{team_id}/auto-group",
    response_model=ResponseSchema[AutoGroupResponse],
    summary="一键按位置分组",
)
async def auto_group_players(
    team_id: str,
    mode: str = Query("groups_3", description="分组模式: team/groups_2/groups_3"),
    db: AsyncSession = Depends(get_db),
):
    """一键按位置自动分组"""
    service = TrainingService(db)
    groups = await service.auto_group_players(team_id, mode)
    
    from app.schemas.training import TrainingGroupSchema
    return ResponseSchema(
        success=True,
        data=AutoGroupResponse(
            mode=mode,
            groups=[
                TrainingGroupSchema(
                    group_id=g["group_id"],
                    name=g["name"],
                    training_item_id=g.get("training_item_id", ""),
                    player_ids=g["player_ids"],
                )
                for g in groups
            ],
        ),
    )


# =====================================================================
# 训练结算与结果
# =====================================================================

@router.post(
    "/teams/{team_id}/plan/complete",
    response_model=ResponseSchema[TrainingDailySummarySchema],
    summary="结算训练时段",
)
async def complete_training_slot(
    team_id: str,
    season_id: str = Query(..., description="赛季ID"),
    season_day: int = Query(..., description="赛季第几天"),
    slot: TrainingSlot = Query(..., description="时段"),
    db: AsyncSession = Depends(get_db),
):
    """结算指定训练时段"""
    from app.models.training import TrainingSlot as TrainingSlotEnum
    
    service = TrainingService(db)
    
    # 获取当前赛季号
    season = await db.get(Season, season_id)
    current_season_number = season.season_number if season else 0
    
    slot_enum = TrainingSlotEnum(slot.value)
    summary = await service.complete_training_slot(
        team_id, season_id, season_day, slot_enum, current_season_number
    )
    
    if not summary.get("completed"):
        return ResponseSchema(
            success=False,
            message=f"结算失败: {summary.get('reason', 'unknown')}",
            data=None,
        )
    
    return ResponseSchema(
        success=True,
        data=TrainingDailySummarySchema(
            season_day=season_day,
            slot=slot,
            total_players=summary.get("total_players", 0),
            total_breakthroughs=summary.get("total_breakthroughs", 0),
            breakthrough_players=summary.get("breakthrough_players", []),
        ),
    )


@router.get(
    "/teams/{team_id}/results",
    response_model=ResponseSchema[List[TrainingResultSchema]],
    summary="获取训练结果",
)
async def get_training_results(
    team_id: str,
    season_id: str = Query(..., description="赛季ID"),
    player_id: Optional[str] = Query(None, description="球员ID筛选"),
    start_day: Optional[int] = Query(None, description="开始天数"),
    days: Optional[int] = Query(None, description="天数"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """获取训练结算记录"""
    service = TrainingService(db)
    results = await service.get_training_results(
        team_id, season_id, player_id, start_day, days, limit
    )
    
    # 预加载球员名称
    player_ids = [r.player_id for r in results]
    players_map = {}
    if player_ids:
        result = await db.execute(select(Player).where(Player.id.in_(player_ids)))
        players_map = {p.id: p for p in result.scalars().all()}
    
    data = []
    for r in results:
        player = players_map.get(r.player_id)
        item = get_training_item(r.training_item_id)
        data.append(TrainingResultSchema(
            id=r.id,
            player_id=r.player_id,
            player_name=player.name if player else None,
            season_day=r.season_day,
            slot=TrainingSlot(r.slot.value if hasattr(r.slot, 'value') else r.slot),
            training_item_id=r.training_item_id,
            training_item_name=item.name if item else None,
            attribute_gains=r.attribute_gains or {},
            fitness_before=r.fitness_before,
            fitness_after=r.fitness_after,
            fatigue_before=r.fatigue_before,
            fatigue_after=r.fatigue_after,
            breakthroughs=r.breakthroughs or [],
            efficiency=r.efficiency,
            created_at=r.created_at,
        ))
    
    return ResponseSchema(success=True, data=data)


# =====================================================================
# 球员疲劳与训练进度
# =====================================================================

@router.get(
    "/players/{player_id}/fatigue",
    response_model=ResponseSchema[PlayerFatigueSchema],
    summary="获取球员疲劳状态",
)
async def get_player_fatigue(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取球员体力、疲劳、预计开场体力和负荷建议"""
    player = await db.get(Player, player_id)
    if not player:
        return ResponseSchema(success=False, message="球员不存在", code=404)
    
    preview = PlayerFatigueService.get_stamina_preview(player)
    
    return ResponseSchema(
        success=True,
        data=PlayerFatigueSchema(
            player_id=player.id,
            player_name=player.name,
            fitness=preview["fitness"],
            fatigue=preview["fatigue"],
            stamina_preview=preview["stamina_preview"],
            fatigue_band=preview["fatigue_band"],
            stamina_multiplier=preview["stamina_multiplier"],
            recommendation=preview["recommendation"],
            can_high_intensity=preview["can_high_intensity"],
        ),
    )


@router.get(
    "/teams/{team_id}/fatigue",
    response_model=ResponseSchema[PlayerFatigueBatchResponse],
    summary="获取全队疲劳状态",
)
async def get_team_fatigue(
    team_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取全队球员的体力、疲劳和预计开场体力"""
    result = await db.execute(
        select(Player).where(
            and_(
                Player.team_id == team_id,
                Player.status == "ACTIVE",
            )
        )
    )
    players = list(result.scalars().all())
    
    items = []
    total_fitness = 0
    total_fatigue = 0
    
    for player in players:
        preview = PlayerFatigueService.get_stamina_preview(player)
        items.append(PlayerFatigueSchema(
            player_id=player.id,
            player_name=player.name,
            fitness=preview["fitness"],
            fatigue=preview["fatigue"],
            stamina_preview=preview["stamina_preview"],
            fatigue_band=preview["fatigue_band"],
            stamina_multiplier=preview["stamina_multiplier"],
            recommendation=preview["recommendation"],
            can_high_intensity=preview["can_high_intensity"],
        ))
        total_fitness += preview["fitness"]
        total_fatigue += preview["fatigue"]
    
    avg_fitness = round(total_fitness / max(len(players), 1), 1)
    avg_fatigue = round(total_fatigue / max(len(players), 1), 1)
    
    return ResponseSchema(
        success=True,
        data=PlayerFatigueBatchResponse(
            team_id=team_id,
            players=items,
            avg_fitness=avg_fitness,
            avg_fatigue=avg_fatigue,
        ),
    )


@router.get(
    "/players/{player_id}/training/progress",
    response_model=ResponseSchema[PlayerTrainingProgressSchema],
    summary="获取球员训练成长进度",
)
async def get_player_training_progress(
    player_id: str,
    season_id: str = Query(..., description="赛季ID"),
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """获取球员训练成长进度和属性上限提示"""
    service = TrainingService(db)
    try:
        progress = await service.get_player_training_progress(player_id, season_id, days)
        return ResponseSchema(success=True, data=PlayerTrainingProgressSchema(**progress))
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=404)
