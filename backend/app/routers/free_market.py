"""
Free Market API - 自由市场路由
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 11.3 节实现。
"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.dependencies import get_db, get_current_user
from app.schemas import BaseSchema, ResponseSchema, PaginatedResponse, ErrorResponse
from app.models import (
    Player,
    PlayerPosition,
    PlayerStatus,
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus,
    SquadRole,
    ContractType,
)
from app.services.contract_service import ContractService
from app.core.logging import get_logger

router = APIRouter(prefix="/free-market", tags=["自由市场"])
logger = get_logger("app.free_market")


@router.get(
    "/",
    response_model=ResponseSchema[PaginatedResponse[dict]],
    summary="自由市场球员列表",
)
async def list_free_market(
    position: Optional[PlayerPosition] = Query(None, description="位置筛选"),
    min_ovr: Optional[int] = Query(None, ge=1, le=100, description="最低OVR"),
    max_ovr: Optional[int] = Query(None, ge=1, le=100, description="最高OVR"),
    min_age: Optional[int] = Query(None, ge=15, le=50, description="最低年龄"),
    max_age: Optional[int] = Query(None, ge=15, le=50, description="最高年龄"),
    origin: Optional[str] = Query(None, description="来源筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取自由市场活跃 listing 列表"""
    # 构建查询：join players 和 free_agent_listings
    from sqlalchemy import func
    
    query = (
        select(FreeAgentListing, Player)
        .join(Player, FreeAgentListing.player_id == Player.id)
        .where(FreeAgentListing.status == ListingStatus.ACTIVE)
        .where(Player.status != PlayerStatus.RETIRED)
    )
    
    if position:
        query = query.where(Player.position == position)
    if min_ovr:
        query = query.where(Player.ovr >= min_ovr)
    if max_ovr:
        query = query.where(Player.ovr <= max_ovr)
    if min_age:
        query = query.where(Player.birth_offset <= -min_age)
    if max_age:
        query = query.where(Player.birth_offset >= -max_age)
    if origin:
        query = query.where(FreeAgentListing.origin == origin)
    
    # 计数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # 分页
    query = query.order_by(desc(Player.ovr))
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    rows = result.all()
    
    items = []
    for listing, player in rows:
        extra = listing.extra_data or {}
        item = {
            "listing_id": listing.id,
            "player_id": player.id,
            "name": player.name,
            "race": player.race.value,
            "avatar_url": player.avatar_url,
            "position": player.position.value,
            "age": abs(player.birth_offset),
            "ovr": player.ovr,
            "potential_letter": player.potential_letter.value,
            "origin": listing.origin.value,
            "signing_fee": float(listing.signing_fee),
            "recommended_wage": float(listing.recommended_wage),
            "listed_at_day": listing.listed_at_day,
            "is_rookie_protected": extra.get("rookie_protected", False),
        }
        items.append(item)
    
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
    "/{listing_id}",
    response_model=ResponseSchema[dict],
    summary="自由市场球员详情",
)
async def get_free_market_detail(
    listing_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取单个自由市场 listing 详情"""
    result = await db.execute(
        select(FreeAgentListing, Player)
        .join(Player, FreeAgentListing.player_id == Player.id)
        .where(FreeAgentListing.id == listing_id)
    )
    row = result.first()
    
    if not row:
        return ResponseSchema(success=False, message="Listing 不存在", code=404)
    
    listing, player = row
    
    return ResponseSchema(
        success=True,
        data={
            "listing_id": listing.id,
            "player": {
                "id": player.id,
                "name": player.name,
                "race": player.race.value,
                "avatar_url": player.avatar_url,
                "position": player.position.value,
                "age": abs(player.birth_offset),
                "ovr": player.ovr,
                "potential_letter": player.potential_letter.value,
                "abilities": {
                    "sho": player.sho, "pas": player.pas, "dri": player.dri,
                    "spd": player.spd, "str": player.str_, "sta": player.sta,
                    "acc": player.acc, "hea": player.hea, "bal": player.bal,
                    "defe": player.defe, "tkl": player.tkl, "vis": player.vis,
                    "cro": player.cro, "con": player.con, "fin": player.fin,
                    "com": player.com, "sav": player.sav, "ref": player.ref,
                    "pos": player.pos, "rus": player.rus, "dec": player.dec,
                    "fk": player.fk, "pk": player.pk,
                },
                "skills": player.skills,
            },
            "origin": listing.origin.value,
            "signing_fee": float(listing.signing_fee),
            "recommended_wage": float(listing.recommended_wage),
            "listed_at_day": listing.listed_at_day,
        },
    )


class FreeMarketSignRequest(BaseSchema):
    """自由市场签约请求"""
    team_id: str
    years: int
    wage: Decimal
    squad_role: SquadRole


@router.post(
    "/{listing_id}/preview",
    response_model=ResponseSchema[dict],
    summary="自由市场签约预览",
)
async def preview_free_market_signing(
    listing_id: str,
    req: FreeMarketSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """预览自由市场签约（含签字费）"""
    result = await db.execute(
        select(FreeAgentListing).where(
            and_(
                FreeAgentListing.id == listing_id,
                FreeAgentListing.status == ListingStatus.ACTIVE,
            )
        )
    )
    listing = result.scalar_one_or_none()
    if not listing:
        return ResponseSchema(success=False, message="Listing 不存在或已失效", code=404)
    
    contract_service = ContractService(db)
    contract_type = (
        ContractType.ROOKIE
        if listing.origin == FreeAgentOrigin.ACADEMY_RELEASED
        else ContractType.NORMAL
    )
    preview = await contract_service.preview_contract_offer(
        player_id=listing.player_id,
        team_id=req.team_id,
        contract_type=contract_type,
        years=req.years,
        wage=req.wage,
        squad_role=req.squad_role,
    )
    
    # 获取球队余额
    from app.models.team import TeamFinance
    finance_result = await db.execute(
        select(TeamFinance.balance).where(TeamFinance.team_id == req.team_id)
    )
    balance = finance_result.scalar_one_or_none() or Decimal("0")
    
    preview_dict = preview.to_dict()
    preview_dict["signing_fee"] = float(listing.signing_fee)
    preview_dict["balance_after_fee"] = float(balance - listing.signing_fee)
    preview_dict["can_pay_signing_fee"] = balance >= listing.signing_fee
    
    return ResponseSchema(success=True, data=preview_dict)


@router.post(
    "/{listing_id}/sign",
    response_model=ResponseSchema[dict],
    summary="自由市场签约",
)
async def sign_free_market_player(
    listing_id: str,
    req: FreeMarketSignRequest,
    db: AsyncSession = Depends(get_db),
):
    """签约自由市场球员"""
    result = await db.execute(
        select(FreeAgentListing).where(
            and_(
                FreeAgentListing.id == listing_id,
                FreeAgentListing.status == ListingStatus.ACTIVE,
            )
        )
    )
    listing = result.scalar_one_or_none()
    if not listing:
        return ResponseSchema(success=False, message="Listing 不存在或已失效", code=404)
    
    contract_service = ContractService(db)
    contract_type = (
        ContractType.ROOKIE
        if listing.origin == FreeAgentOrigin.ACADEMY_RELEASED
        else ContractType.NORMAL
    )
    source = "rookie_market" if listing.origin == FreeAgentOrigin.ACADEMY_RELEASED else "free_market"
    
    try:
        contract = await contract_service.sign_free_agent(
            player_id=listing.player_id,
            team_id=req.team_id,
            years=req.years,
            wage=req.wage,
            squad_role=req.squad_role,
            signing_fee=listing.signing_fee,
            contract_type=contract_type,
            source=source,
        )
        
        # 更新 listing
        listing.status = ListingStatus.SIGNED
        listing.signed_team_id = req.team_id
        
        await db.commit()
        
        return ResponseSchema(
            success=True,
            data={
                "contract_id": contract.id,
                "player_id": listing.player_id,
                "team_id": req.team_id,
                "signing_fee": float(listing.signing_fee),
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)

