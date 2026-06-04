"""
Transfer Market API - 转会市场路由
按 TRANSFER-MARKET-PRD.md v0.2 实现。
"""
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, asc, func

from app.dependencies import get_db, get_current_user
from app.schemas import BaseSchema, ResponseSchema, PaginatedResponse
from app.models import (
    Player,
    PlayerPosition,
    PlayerStatus,
    Team,
    PotentialLetter,
)
from app.models.transfer import (
    TransferListing,
    TransferListingStatus,
    TransferNegotiation,
    NegotiationStatus,
    TransferOffer,
    OfferKind,
    OfferStatus,
    TransferRecord,
)
from app.services.transfer_service import TransferService
from app.services.ai_transfer_service import AITransferService
from app.core.logging import get_logger

router = APIRouter(prefix="/transfers", tags=["转会市场"])
logger = get_logger("app.transfers")


# =====================================================================
# Schemas
# =====================================================================

class ValuationResponse(BaseSchema):
    player_id: str
    market_value: float
    age: int
    ovr: int
    potential_letter: str


class ListPlayerRequest(BaseSchema):
    team_id: str
    list_price: Decimal


class CreateOfferRequest(BaseSchema):
    player_id: str
    buyer_team_id: str
    amount: Decimal
    listing_id: Optional[str] = None


class CounterOfferRequest(BaseSchema):
    seller_team_id: str
    amount: Decimal


class FinalOfferRequest(BaseSchema):
    buyer_team_id: str
    amount: Decimal


class ReleasePreviewResponse(BaseSchema):
    player_id: str
    player_name: str
    unpaid_wages: float
    base_penalty: float
    min_penalty: float
    final_penalty: float
    balance: float
    can_release: bool
    reason: str


# =====================================================================
# 市场浏览
# =====================================================================

@router.get("/market", response_model=ResponseSchema[PaginatedResponse[dict]], summary="转会市场球员列表")
async def get_transfer_market(
    position: Optional[PlayerPosition] = Query(None, description="位置筛选"),
    min_ovr: Optional[int] = Query(None, ge=1, le=100),
    max_ovr: Optional[int] = Query(None, ge=1, le=100),
    min_age: Optional[int] = Query(None, ge=15, le=50),
    max_age: Optional[int] = Query(None, ge=15, le=50),
    is_listed: Optional[bool] = Query(None, description="是否挂牌"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取可交易球员列表（含挂牌状态）"""
    season_result = await db.execute(select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number)).limit(1))
    season = season_result.scalar_one_or_none()
    current_season_number = season.season_number if season else 0

    # 查询所有有队非退役球员
    query = select(Player, Team).join(Team, Player.team_id == Team.id).where(
        and_(
            Player.team_id.isnot(None),
            Player.status != PlayerStatus.RETIRED,
        )
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

    # 计数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(Player.ovr)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    transfer_service = TransferService(db)
    items = []
    for player, team in rows:
        age = current_season_number + abs(player.birth_offset)
        market_value = await transfer_service.calculate_market_value(player.id, team.id)

        # 查询是否挂牌
        listing_result = await db.execute(
            select(TransferListing).where(
                and_(
                    TransferListing.player_id == player.id,
                    TransferListing.status == TransferListingStatus.ACTIVE,
                )
            )
        )
        listing = listing_result.scalar_one_or_none()

        if is_listed is not None:
            if is_listed and not listing:
                continue
            if not is_listed and listing:
                continue

        item = {
            "player_id": player.id,
            "name": player.name,
            "position": player.position.value,
            "age": age,
            "ovr": player.ovr,
            "potential_letter": player.potential_letter.value,
            "market_value": float(market_value),
            "team_id": team.id,
            "team_name": team.name,
            "is_listed": listing is not None,
            "list_price": float(listing.list_price) if listing else None,
            "listing_id": listing.id if listing else None,
        }
        items.append(item)

    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
    )


@router.get("/listings", response_model=ResponseSchema[PaginatedResponse[dict]], summary="挂牌列表")
async def get_listings(
    seller_team_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取活跃挂牌列表"""
    query = select(TransferListing, Player).join(Player, TransferListing.player_id == Player.id).where(
        TransferListing.status == TransferListingStatus.ACTIVE
    )
    if seller_team_id:
        query = query.where(TransferListing.seller_team_id == seller_team_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(TransferListing.list_price)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for listing, player in rows:
        items.append({
            "listing_id": listing.id,
            "player_id": player.id,
            "name": player.name,
            "position": player.position.value,
            "ovr": player.ovr,
            "age": abs(player.birth_offset),
            "list_price": float(listing.list_price),
            "market_value": float(listing.market_value_snapshot),
            "seller_team_id": listing.seller_team_id,
            "deadline": listing.decision_deadline_at.isoformat() if listing.decision_deadline_at else None,
        })

    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
    )


# =====================================================================
# 报价
# =====================================================================

@router.get("/offers/public", response_model=ResponseSchema[PaginatedResponse[dict]], summary="公开报价")
async def get_public_offers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取全服公开报价"""
    query = select(TransferOffer, Player).join(Player, TransferOffer.player_id == Player.id).where(
        TransferOffer.is_public == True
    ).order_by(desc(TransferOffer.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.all()

    items = []
    for offer, player in rows:
        items.append({
            "offer_id": offer.id,
            "player_id": player.id,
            "player_name": player.name,
            "position": player.position.value,
            "ovr": player.ovr,
            "buyer_team_id": offer.buyer_team_id,
            "seller_team_id": offer.seller_team_id,
            "amount": float(offer.amount),
            "market_value": float(offer.market_value_snapshot),
            "offer_kind": offer.offer_kind.value,
            "status": offer.status.value,
            "created_at": offer.created_at.isoformat(),
            "expires_at": offer.expires_at.isoformat(),
        })

    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
    )


@router.get("/offers/received", response_model=ResponseSchema[PaginatedResponse[dict]], summary="收到的报价")
async def get_received_offers(
    team_id: str = Query(..., description="球队ID"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取某球队收到的报价"""
    query = select(TransferOffer, Player).join(Player, TransferOffer.player_id == Player.id).where(
        TransferOffer.receiver_team_id == team_id
    )
    if status:
        query = query.where(TransferOffer.status == status)
    query = query.order_by(desc(TransferOffer.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()

    items = []
    for offer, player in rows:
        negotiation = await db.execute(select(TransferNegotiation).where(TransferNegotiation.id == offer.negotiation_id))
        neg = negotiation.scalar_one_or_none()
        items.append({
            "offer_id": offer.id,
            "negotiation_id": offer.negotiation_id,
            "player_id": player.id,
            "player_name": player.name,
            "amount": float(offer.amount),
            "offer_kind": offer.offer_kind.value,
            "status": offer.status.value,
            "buyer_team_id": offer.buyer_team_id,
            "expires_at": offer.expires_at.isoformat(),
            "can_counter": neg.counter_used if neg else False,
        })

    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
    )


@router.get("/offers/sent", response_model=ResponseSchema[PaginatedResponse[dict]], summary="发出的报价")
async def get_sent_offers(
    team_id: str = Query(..., description="球队ID"),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取某球队发出的报价"""
    query = select(TransferOffer, Player).join(Player, TransferOffer.player_id == Player.id).where(
        TransferOffer.sender_team_id == team_id
    )
    if status:
        query = query.where(TransferOffer.status == status)
    query = query.order_by(desc(TransferOffer.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()

    items = []
    for offer, player in rows:
        items.append({
            "offer_id": offer.id,
            "negotiation_id": offer.negotiation_id,
            "player_id": player.id,
            "player_name": player.name,
            "amount": float(offer.amount),
            "offer_kind": offer.offer_kind.value,
            "status": offer.status.value,
            "seller_team_id": offer.seller_team_id,
            "expires_at": offer.expires_at.isoformat(),
        })

    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
    )


# =====================================================================
# 操作
# =====================================================================

@router.post("/players/{player_id}/valuation", response_model=ResponseSchema[ValuationResponse], summary="球员估价")
async def get_player_valuation(
    player_id: str,
    team_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """获取球员市场估价"""
    transfer_service = TransferService(db)
    player = await transfer_service._get_player(player_id)
    if not player:
        return ResponseSchema(success=False, message="球员不存在", code=404)

    season = await transfer_service._get_current_season()
    age = (season.season_number if season else 0) + abs(player.birth_offset)
    market_value = await transfer_service.calculate_market_value(player_id, team_id)

    return ResponseSchema(
        success=True,
        data=ValuationResponse(
            player_id=player_id,
            market_value=float(market_value),
            age=age,
            ovr=player.ovr,
            potential_letter=player.potential_letter.value,
        ),
    )


@router.post("/players/{player_id}/list", response_model=ResponseSchema[dict], summary="挂牌球员")
async def list_player_for_sale(
    player_id: str,
    req: ListPlayerRequest,
    db: AsyncSession = Depends(get_db),
):
    """将球员挂牌出售"""
    transfer_service = TransferService(db)
    try:
        listing = await transfer_service.list_player(player_id, req.team_id, req.list_price)
        return ResponseSchema(
            success=True,
            data={
                "listing_id": listing.id,
                "player_id": player_id,
                "list_price": float(listing.list_price),
                "deadline": listing.decision_deadline_at.isoformat() if listing.decision_deadline_at else None,
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/listings/{listing_id}/cancel", response_model=ResponseSchema[dict], summary="撤销挂牌")
async def cancel_player_listing(
    listing_id: str,
    team_id: str = Query(..., description="球队ID"),
    db: AsyncSession = Depends(get_db),
):
    """撤销球员挂牌"""
    transfer_service = TransferService(db)
    try:
        await transfer_service.cancel_listing(listing_id, team_id)
        return ResponseSchema(success=True, data={"listing_id": listing_id, "status": "cancelled"})
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/offers", response_model=ResponseSchema[dict], summary="发送报价")
async def create_transfer_offer(
    req: CreateOfferRequest,
    db: AsyncSession = Depends(get_db),
):
    """向其他球队球员发送转会报价"""
    transfer_service = TransferService(db)
    try:
        offer = await transfer_service.create_offer(
            player_id=req.player_id,
            buyer_team_id=req.buyer_team_id,
            amount=req.amount,
            listing_id=req.listing_id,
        )
        return ResponseSchema(
            success=True,
            data={
                "offer_id": offer.id,
                "negotiation_id": offer.negotiation_id,
                "amount": float(offer.amount),
                "expires_at": offer.expires_at.isoformat(),
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/offers/{offer_id}/accept", response_model=ResponseSchema[dict], summary="接受报价")
async def accept_transfer_offer(
    offer_id: str,
    actor_team_id: str = Query(..., description="操作方球队ID"),
    db: AsyncSession = Depends(get_db),
):
    """接受转会报价"""
    transfer_service = TransferService(db)
    try:
        record = await transfer_service.accept_offer(offer_id, actor_team_id)
        return ResponseSchema(
            success=True,
            data={
                "record_id": record.id,
                "transfer_type": record.transfer_type.value,
                "amount": float(record.amount),
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/offers/{offer_id}/reject", response_model=ResponseSchema[dict], summary="拒绝报价")
async def reject_transfer_offer(
    offer_id: str,
    actor_team_id: str = Query(..., description="操作方球队ID"),
    db: AsyncSession = Depends(get_db),
):
    """拒绝转会报价"""
    transfer_service = TransferService(db)
    try:
        offer = await transfer_service.reject_offer(offer_id, actor_team_id)
        return ResponseSchema(success=True, data={"offer_id": offer.id, "status": offer.status.value})
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/offers/{offer_id}/counter", response_model=ResponseSchema[dict], summary="反报价")
async def counter_transfer_offer(
    offer_id: str,
    req: CounterOfferRequest,
    db: AsyncSession = Depends(get_db),
):
    """对初始报价发起反报价"""
    transfer_service = TransferService(db)
    try:
        counter = await transfer_service.create_counter_offer(offer_id, req.seller_team_id, req.amount)
        return ResponseSchema(
            success=True,
            data={
                "offer_id": counter.id,
                "negotiation_id": counter.negotiation_id,
                "amount": float(counter.amount),
                "expires_at": counter.expires_at.isoformat(),
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/negotiations/{negotiation_id}/final-offer", response_model=ResponseSchema[dict], summary="最终报价")
async def create_final_transfer_offer(
    negotiation_id: str,
    req: FinalOfferRequest,
    db: AsyncSession = Depends(get_db),
):
    """对反报价提交最终报价"""
    transfer_service = TransferService(db)
    try:
        final = await transfer_service.create_final_offer(negotiation_id, req.buyer_team_id, req.amount)
        return ResponseSchema(
            success=True,
            data={
                "offer_id": final.id,
                "negotiation_id": final.negotiation_id,
                "amount": float(final.amount),
                "expires_at": final.expires_at.isoformat(),
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# 解约
# =====================================================================

@router.post("/players/{player_id}/release/preview", response_model=ResponseSchema[ReleasePreviewResponse], summary="解约预览")
async def preview_release(
    player_id: str,
    team_id: str = Query(..., description="球队ID"),
    db: AsyncSession = Depends(get_db),
):
    """预览解约违约金"""
    transfer_service = TransferService(db)
    try:
        preview = await transfer_service.preview_release_penalty(player_id, team_id)
        return ResponseSchema(success=True, data=ReleasePreviewResponse(**preview))
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


@router.post("/players/{player_id}/release", response_model=ResponseSchema[dict], summary="解约球员")
async def release_player(
    player_id: str,
    team_id: str = Query(..., description="球队ID"),
    db: AsyncSession = Depends(get_db),
):
    """解约球员并支付违约金"""
    transfer_service = TransferService(db)
    try:
        record = await transfer_service.release_player_with_penalty(player_id, team_id)
        return ResponseSchema(
            success=True,
            data={
                "record_id": record.id,
                "transfer_type": record.transfer_type.value,
                "amount": float(record.amount),
            },
        )
    except ValueError as e:
        return ResponseSchema(success=False, message=str(e), code=400)


# =====================================================================
# 历史
# =====================================================================

@router.get("/history", response_model=ResponseSchema[PaginatedResponse[dict]], summary="转会历史")
async def get_transfer_history(
    team_id: Optional[str] = Query(None),
    player_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取转会历史记录"""
    query = select(TransferRecord, Player).join(Player, TransferRecord.player_id == Player.id).where(
        TransferRecord.is_public == True
    )
    if team_id:
        query = query.where(
            or_(
                TransferRecord.from_team_id == team_id,
                TransferRecord.to_team_id == team_id,
            )
        )
    if player_id:
        query = query.where(TransferRecord.player_id == player_id)

    query = query.order_by(desc(TransferRecord.completed_at))

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).all()

    items = []
    for record, player in rows:
        items.append({
            "record_id": record.id,
            "player_id": player.id,
            "player_name": player.name,
            "from_team_id": record.from_team_id,
            "to_team_id": record.to_team_id,
            "transfer_type": record.transfer_type.value,
            "amount": float(record.amount),
            "market_value": float(record.market_value_snapshot),
            "completed_at": record.completed_at.isoformat(),
        })

    return ResponseSchema(
        success=True,
        data=PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size),
    )


# =====================================================================
# AI 触发（内部/管理用）
# =====================================================================

@router.post("/admin/ai-scan", response_model=ResponseSchema[dict], summary="触发AI转会扫描")
async def trigger_ai_transfer_scan(
    db: AsyncSession = Depends(get_db),
):
    """手动触发 AI 转会市场扫描（开发/测试用）"""
    ai_service = AITransferService(db)
    stats = await ai_service.run_ai_transfer_market_scan()
    return ResponseSchema(success=True, data=stats)
