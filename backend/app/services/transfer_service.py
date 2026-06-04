"""
Transfer service - 转会市场核心服务
按 TRANSFER-MARKET-PRD.md v0.2 实现。
"""
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, asc, func, update

from app.models import (
    Player,
    PlayerStatus,
    ContractType,
    SquadRole,
    PotentialLetter,
    PlayerContract,
    ContractStatus,
    Team,
    TeamFinance,
    User,
    Season,
    SeasonStatus,
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus as FreeAgentListingStatus,
    Mail,
    MailCategory,
    MailPriority,
    FinanceTransaction,
    TransactionSourceType,
    TransactionDirection,
    OverspendLevel,
)
from app.models.transfer import (
    TransferListing,
    TransferListingStatus,
    TransferNegotiation,
    NegotiationStatus,
    TransferOffer,
    OfferKind,
    OfferStatus,
    TransferDailyQuota,
    TransferRecord,
    TransferType,
)
from app.core.events import EventType, EventQueue
from app.core.logging import get_logger
from app.services.contract_service import ContractService
from app.services.finance_service import FinanceService
from app.services.player_state_service import PlayerStateService
from app.services.game_clock_state import GameClockStateService

logger = get_logger("app.transfer")

# =====================================================================
# 估价常量
# =====================================================================
_OVR_BASE_PRICE = {
    30: Decimal("200000"),
    40: Decimal("600000"),
    50: Decimal("1500000"),
    60: Decimal("3500000"),
    70: Decimal("8000000"),
    80: Decimal("18000000"),
    90: Decimal("40000000"),
}

_AGE_FACTOR = {
    20: Decimal("1.20"),
    23: Decimal("1.10"),
    26: Decimal("1.00"),
    28: Decimal("0.85"),
    30: Decimal("0.65"),
    32: Decimal("0.45"),
}

_POTENTIAL_FACTOR = {
    PotentialLetter.S: Decimal("1.50"),
    PotentialLetter.A: Decimal("1.25"),
    PotentialLetter.B: Decimal("1.10"),
    PotentialLetter.C: Decimal("1.00"),
    PotentialLetter.D: Decimal("0.85"),
}

_FORM_FACTOR = {
    "HOT": Decimal("1.15"),
    "GOOD": Decimal("1.05"),
    "NEUTRAL": Decimal("1.00"),
    "LOW": Decimal("0.90"),
    "INJURED": Decimal("0.75"),
    "SUSPENDED": Decimal("0.75"),
}

_LEAGUE_FACTOR = {
    1: Decimal("1.25"),
    2: Decimal("1.10"),
    3: Decimal("1.00"),
    4: Decimal("0.85"),
}

# 报价链约束
MAX_DAILY_OFFERS = 2
AI_MAX_DAILY_OFFERS = 1
OFFER_EXPIRE_DAYS = 3
LISTING_INITIAL_DAYS = 3
COOLDOWN_DAYS = 3

# 违约金
RELEASE_BASE_RATE_NORMAL = Decimal("0.75")
RELEASE_BASE_RATE_ROOKIE = Decimal("0.50")
RELEASE_MIN_RATE_NORMAL = Decimal("0.10")
RELEASE_MIN_RATE_ROOKIE = Decimal("0.05")
SEASON_END_GRACE_DAYS = 7


def _interpolate_value(table: Dict[int, Decimal], key: int) -> Decimal:
    """线性插值"""
    keys = sorted(table.keys())
    if key <= keys[0]:
        return table[keys[0]]
    if key >= keys[-1]:
        return table[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= key <= keys[i + 1]:
            k1, k2 = keys[i], keys[i + 1]
            v1, v2 = table[k1], table[k2]
            ratio = Decimal(key - k1) / Decimal(k2 - k1)
            return v1 + (v2 - v1) * ratio
    return table[keys[-1]]


def _quantize(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class TransferService:
    """转会市场核心服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.contract_service = ContractService(db)
        self.finance_service = FinanceService(db)
        self.state_service = PlayerStateService(db)
        self.clock_service = GameClockStateService(db)

    # =====================================================================
    # 基础查询
    # =====================================================================

    async def _get_current_season(self) -> Optional[Season]:
        result = await self.db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number)).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_season_day(self) -> int:
        season = await self._get_current_season()
        return season.current_day if season else 1

    async def _get_current_season_id(self) -> Optional[str]:
        season = await self._get_current_season()
        return season.id if season else None

    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()

    async def _get_team(self, team_id: str) -> Optional[Team]:
        with self.db.no_autoflush:
            result = await self.db.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    async def _get_listing(self, listing_id: str) -> Optional[TransferListing]:
        result = await self.db.execute(select(TransferListing).where(TransferListing.id == listing_id))
        return result.scalar_one_or_none()

    async def _get_negotiation(self, negotiation_id: str) -> Optional[TransferNegotiation]:
        result = await self.db.execute(select(TransferNegotiation).where(TransferNegotiation.id == negotiation_id))
        return result.scalar_one_or_none()

    async def _get_offer(self, offer_id: str) -> Optional[TransferOffer]:
        result = await self.db.execute(select(TransferOffer).where(TransferOffer.id == offer_id))
        return result.scalar_one_or_none()

    async def _get_team_roster_count(self, team_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Player.id))
            .where(Player.team_id == team_id)
            .where(Player.status.in_([PlayerStatus.ACTIVE, PlayerStatus.INJURED, PlayerStatus.SUSPENDED]))
        )
        return result.scalar() or 0

    async def _get_active_contract(self, player_id: str) -> Optional[PlayerContract]:
        result = await self.db.execute(
            select(PlayerContract)
            .where(PlayerContract.player_id == player_id)
            .where(PlayerContract.status == ContractStatus.ACTIVE)
        )
        return result.scalar_one_or_none()

    async def _get_team_league_level(self, team_id: str) -> int:
        team = await self._get_team(team_id)
        if not team or not team.current_league_id:
            return 3
        from app.models.league import League
        result = await self.db.execute(select(League.level).where(League.id == team.current_league_id))
        level = result.scalar_one_or_none()
        return level or 3

    async def _is_ai_team(self, team_id: str) -> bool:
        with self.db.no_autoflush:
            result = await self.db.execute(
                select(User.is_ai)
                .join(Team, Team.user_id == User.id)
                .where(Team.id == team_id)
            )
        return bool(result.scalar_one_or_none())

    async def _schedule_ai_offer_response(
        self,
        receiver_team_id: str,
        negotiation_id: str,
        season_id: str,
        now: datetime,
    ) -> None:
        if not await self._is_ai_team(receiver_team_id):
            return
        EventQueue.add_pending(
            self.db,
            EventType.AI_TRANSFER_OFFER_RESPONSE,
            {"negotiation_id": negotiation_id, "season_id": season_id},
            scheduled_at=now + timedelta(minutes=30),
        )

    # =====================================================================
    # 市场估价
    # =====================================================================

    async def calculate_market_value(self, player_id: str, team_id: Optional[str] = None) -> Decimal:
        """计算球员市场估价 (PRD 5.1)"""
        player = await self._get_player(player_id)
        if not player:
            return Decimal("0")

        season = await self._get_current_season()
        current_season_number = season.season_number if season else 0
        age = current_season_number + abs(player.birth_offset)
        ovr = player.ovr

        # OVR 基础价（插值）
        base_price = _interpolate_value(_OVR_BASE_PRICE, ovr)

        # 年龄系数
        age_key = 20 if age <= 20 else 32 if age >= 32 else age
        age_factor = _interpolate_value(_AGE_FACTOR, age_key)

        # 潜力系数
        potential_factor = _POTENTIAL_FACTOR.get(player.potential_letter, Decimal("1.00"))

        # 状态系数
        form_key = "INJURED" if player.status in (PlayerStatus.INJURED, PlayerStatus.SUSPENDED) else player.match_form.value
        form_factor = _FORM_FACTOR.get(form_key, Decimal("1.00"))

        # 联赛级别系数
        level = await self._get_team_league_level(team_id) if team_id else 3
        league_factor = _LEAGUE_FACTOR.get(level, Decimal("1.00"))

        # 位置稀缺系数 v1 固定 1.00
        position_factor = Decimal("1.00")

        value = base_price * age_factor * potential_factor * form_factor * league_factor * position_factor
        return _quantize(value)

    # =====================================================================
    # 额度管理
    # =====================================================================

    async def _get_or_create_quota(self, team_id: str, season_id: str, season_day: int) -> TransferDailyQuota:
        result = await self.db.execute(
            select(TransferDailyQuota).where(
                and_(
                    TransferDailyQuota.team_id == team_id,
                    TransferDailyQuota.season_id == season_id,
                    TransferDailyQuota.season_day == season_day,
                )
            )
        )
        quota = result.scalar_one_or_none()
        if not quota:
            quota = TransferDailyQuota(
                team_id=team_id,
                season_id=season_id,
                season_day=season_day,
                sent_offer_count=0,
            )
            self.db.add(quota)
            await self.db.flush()
        return quota

    async def _can_send_offer(self, team_id: str, is_ai: bool = False) -> tuple[bool, str]:
        season = await self._get_current_season()
        if not season:
            return False, "没有进行中的赛季"
        quota = await self._get_or_create_quota(team_id, season.id, season.current_day)
        limit = AI_MAX_DAILY_OFFERS if is_ai else MAX_DAILY_OFFERS
        if quota.sent_offer_count >= limit:
            return False, f"今日主动报价额度已用完 ({quota.sent_offer_count}/{limit})"
        return True, ""

    async def _consume_offer_quota(self, team_id: str) -> None:
        season = await self._get_current_season()
        if not season:
            return
        quota = await self._get_or_create_quota(team_id, season.id, season.current_day)
        quota.sent_offer_count += 1
        await self.db.flush()

    # =====================================================================
    # 挂牌
    # =====================================================================

    async def list_player(self, player_id: str, seller_team_id: str, list_price: Decimal) -> TransferListing:
        """挂牌球员 (PRD 7)"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError("球员不存在")
        if player.team_id != seller_team_id:
            raise ValueError("该球员不属于你的球队")
        if player.status == PlayerStatus.RETIRED:
            raise ValueError("退役球员不能挂牌")

        season = await self._get_current_season()
        if not season:
            raise ValueError("没有进行中的赛季")

        # 检查是否已在待结算交易中
        existing = await self.db.execute(
            select(TransferNegotiation).where(
                and_(
                    TransferNegotiation.player_id == player_id,
                    TransferNegotiation.status.in_([NegotiationStatus.OPEN, NegotiationStatus.ACCEPTED]),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该球员已有进行中的报价链")

        # 检查 roster 下限
        roster_count = await self._get_team_roster_count(seller_team_id)
        if roster_count - 1 < ContractService.ROSTER_MIN:
            raise ValueError(f"挂牌后球队人数将低于下限 {ContractService.ROSTER_MIN}")

        # 估价检查
        market_value = await self.calculate_market_value(player_id, seller_team_id)
        min_price = _quantize(market_value * Decimal("0.80"))
        if list_price < min_price:
            raise ValueError(f"挂牌价不能低于市场估价的 80% ({float(min_price):.0f})")

        now = await self.clock_service.now()
        deadline = now + timedelta(days=LISTING_INITIAL_DAYS)

        listing = TransferListing(
            player_id=player_id,
            seller_team_id=seller_team_id,
            season_id=season.id,
            status=TransferListingStatus.ACTIVE,
            market_value_snapshot=market_value,
            list_price=list_price,
            min_price=min_price,
            listed_at_day=season.current_day,
            decision_deadline_at=deadline,
        )
        self.db.add(listing)
        await self.db.flush([listing])

        # 推送挂牌截止事件
        EventQueue.add_pending(
            self.db,
            EventType.TRANSFER_LISTING_DEADLINE,
            {"listing_id": listing.id, "season_id": season.id, "day": season.current_day},
            scheduled_at=deadline,
        )

        await self._notify_team(
            seller_team_id,
            season.id,
            "球员挂牌",
            f"你已将 {player.name} 挂牌出售，挂牌价 {float(list_price):.0f} 万。",
            MailPriority.NORMAL,
        )
        return listing

    async def cancel_listing(self, listing_id: str, seller_team_id: str) -> None:
        """撤牌"""
        listing = await self._get_listing(listing_id)
        if not listing:
            raise ValueError("挂牌不存在")
        if listing.seller_team_id != seller_team_id:
            raise ValueError("无权撤销此挂牌")
        if listing.status != TransferListingStatus.ACTIVE:
            raise ValueError("只能撤销活跃挂牌")

        listing.status = TransferListingStatus.CANCELLED
        await self.db.flush()

        # 关闭相关 open negotiation
        await self.db.execute(
            update(TransferNegotiation)
            .where(TransferNegotiation.listing_id == listing_id)
            .where(TransferNegotiation.status == NegotiationStatus.OPEN)
            .values(status=NegotiationStatus.REJECTED)
        )

        # 关闭相关 pending offer
        await self.db.execute(
            update(TransferOffer)
            .where(TransferOffer.listing_id == listing_id)
            .where(TransferOffer.status == OfferStatus.PENDING_RESPONSE)
            .values(status=OfferStatus.REJECTED)
        )

    # =====================================================================
    # 报价链
    # =====================================================================

    async def create_offer(
        self,
        player_id: str,
        buyer_team_id: str,
        amount: Decimal,
        listing_id: Optional[str] = None,
    ) -> TransferOffer:
        """创建初始报价 (PRD 6)"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError("球员不存在")
        if player.team_id == buyer_team_id:
            raise ValueError("不能向本队球员报价")
        if player.status == PlayerStatus.RETIRED:
            raise ValueError("退役球员不能报价")
        if not player.team_id:
            raise ValueError("自由球员请使用自由市场签约")

        seller_team_id = player.team_id
        season = await self._get_current_season()
        if not season:
            raise ValueError("没有进行中的赛季")

        # 额度检查
        can_send, reason = await self._can_send_offer(buyer_team_id, is_ai=False)
        if not can_send:
            raise ValueError(reason)

        # 买方财务检查
        can_bid, reason = await self.finance_service.can_place_transfer_bid(
            buyer_team_id, season.id, amount
        )
        if not can_bid:
            raise ValueError(reason)

        # roster 上限检查
        buyer_roster = await self._get_team_roster_count(buyer_team_id)
        if buyer_roster >= ContractService.ROSTER_MAX:
            raise ValueError(f"买方球队人数已达上限 {ContractService.ROSTER_MAX}")

        # 检查是否已有 open negotiation
        existing_neg = await self.db.execute(
            select(TransferNegotiation).where(
                and_(
                    TransferNegotiation.player_id == player_id,
                    TransferNegotiation.buyer_team_id == buyer_team_id,
                    TransferNegotiation.status == NegotiationStatus.OPEN,
                )
            )
        )
        if existing_neg.scalar_one_or_none():
            raise ValueError("你已对该球员有进行中的报价链")

        # 检查球员是否在其他已接受待结算交易中
        accepted = await self.db.execute(
            select(TransferNegotiation).where(
                and_(
                    TransferNegotiation.player_id == player_id,
                    TransferNegotiation.status == NegotiationStatus.ACCEPTED,
                )
            )
        )
        if accepted.scalar_one_or_none():
            raise ValueError("该球员已被其他交易接受，等待结算")

        market_value = await self.calculate_market_value(player_id, seller_team_id)

        # 挂牌报价检查
        listing = None
        is_listed = False
        if listing_id:
            listing = await self._get_listing(listing_id)
            if listing and listing.status == TransferListingStatus.ACTIVE and listing.player_id == player_id:
                is_listed = True
                if amount < listing.list_price:
                    raise ValueError(f"报价不能低于挂牌价 {float(listing.list_price):.0f}")
        else:
            # 非挂牌报价不得低于估价 80%
            min_offer = _quantize(market_value * Decimal("0.80"))
            if amount < min_offer:
                raise ValueError(f"非挂牌报价不得低于市场估价的 80% ({float(min_offer):.0f})")

        now = await self.clock_service.now()
        expires = now + timedelta(days=OFFER_EXPIRE_DAYS)

        # 创建 negotiation
        negotiation = TransferNegotiation(
            listing_id=listing_id if is_listed else None,
            player_id=player_id,
            buyer_team_id=buyer_team_id,
            seller_team_id=seller_team_id,
            season_id=season.id,
            status=NegotiationStatus.OPEN,
            counter_used=False,
            final_used=False,
            is_listed_snapshot=is_listed,
            expires_at=expires,
        )
        self.db.add(negotiation)
        await self.db.flush()

        # 创建 initial offer
        offer = TransferOffer(
            negotiation_id=negotiation.id,
            listing_id=listing_id if is_listed else None,
            player_id=player_id,
            buyer_team_id=buyer_team_id,
            seller_team_id=seller_team_id,
            sender_team_id=buyer_team_id,
            receiver_team_id=seller_team_id,
            season_id=season.id,
            amount=amount,
            market_value_snapshot=market_value,
            offer_kind=OfferKind.INITIAL,
            round_no=1,
            status=OfferStatus.PENDING_RESPONSE,
            is_public=True,
            expires_at=expires,
        )
        self.db.add(offer)
        await self.db.flush()

        negotiation.current_offer_id = offer.id
        negotiation.initial_offer_id = offer.id
        await self.db.flush()

        # 消耗额度
        await self._consume_offer_quota(buyer_team_id)

        # 挂牌等待期续期
        if is_listed and listing:
            listing.last_offer_at = now
            listing.decision_deadline_at = now + timedelta(days=LISTING_INITIAL_DAYS)
            EventQueue.add_pending(
                self.db,
                EventType.TRANSFER_LISTING_DEADLINE,
                {"listing_id": listing.id, "season_id": season.id, "day": season.current_day},
                scheduled_at=listing.decision_deadline_at,
            )

        # 推送报价过期事件
        EventQueue.add_pending(
            self.db,
            EventType.TRANSFER_OFFER_EXPIRES,
            {"offer_id": offer.id, "negotiation_id": negotiation.id, "season_id": season.id},
            scheduled_at=expires,
        )
        await self._schedule_ai_offer_response(seller_team_id, negotiation.id, season.id, now)

        # 通知
        await self._notify_team(
            seller_team_id,
            season.id,
            "收到转会报价",
            f"{player.name} 收到来自某球队的报价 {float(amount):.0f} 万。",
            MailPriority.NORMAL,
        )

        return offer

    async def create_counter_offer(
        self,
        offer_id: str,
        seller_team_id: str,
        amount: Decimal,
    ) -> TransferOffer:
        """卖方反报价 (PRD 6.4)"""
        initial_offer = await self._get_offer(offer_id)
        if not initial_offer:
            raise ValueError("报价不存在")
        if initial_offer.receiver_team_id != seller_team_id:
            raise ValueError("无权反报价")
        if initial_offer.status != OfferStatus.PENDING_RESPONSE:
            raise ValueError("该报价不再等待响应")
        if initial_offer.offer_kind != OfferKind.INITIAL:
            raise ValueError("只能对初始报价反报价")

        negotiation = await self._get_negotiation(initial_offer.negotiation_id)
        if not negotiation or negotiation.counter_used:
            raise ValueError("该报价链已使用过反报价")

        if amount <= initial_offer.amount:
            raise ValueError("反报价金额必须高于原报价")
        max_counter = _quantize(initial_offer.amount * Decimal("1.50"))
        if amount > max_counter:
            raise ValueError(f"反报价不能超过原报价的 150% ({float(max_counter):.0f})")

        season = await self._get_current_season()
        now = await self.clock_service.now()
        expires = now + timedelta(days=OFFER_EXPIRE_DAYS)
        player = await self._get_player(initial_offer.player_id)
        player_name = player.name if player else "某球员"

        # 原报价标记为 superseded
        initial_offer.status = OfferStatus.SUPERSEDED

        # 创建 counter offer
        counter = TransferOffer(
            negotiation_id=negotiation.id,
            listing_id=initial_offer.listing_id,
            player_id=initial_offer.player_id,
            buyer_team_id=initial_offer.buyer_team_id,
            seller_team_id=initial_offer.seller_team_id,
            sender_team_id=seller_team_id,
            receiver_team_id=initial_offer.buyer_team_id,
            season_id=initial_offer.season_id,
            amount=amount,
            market_value_snapshot=initial_offer.market_value_snapshot,
            offer_kind=OfferKind.COUNTER,
            round_no=2,
            status=OfferStatus.PENDING_RESPONSE,
            is_public=True,
            parent_offer_id=initial_offer.id,
            expires_at=expires,
        )
        self.db.add(counter)
        await self.db.flush()

        negotiation.current_offer_id = counter.id
        negotiation.counter_offer_id = counter.id
        negotiation.counter_used = True
        negotiation.expires_at = expires
        await self.db.flush()

        # 推送事件
        EventQueue.add_pending(
            self.db,
            EventType.TRANSFER_OFFER_EXPIRES,
            {"offer_id": counter.id, "negotiation_id": negotiation.id, "season_id": initial_offer.season_id},
            scheduled_at=expires,
        )
        await self._schedule_ai_offer_response(initial_offer.buyer_team_id, negotiation.id, initial_offer.season_id, now)

        await self._notify_team(
            initial_offer.buyer_team_id,
            initial_offer.season_id,
            "收到反报价",
            f"你对 {player_name} 的报价收到反报价 {float(amount):.0f} 万。",
            MailPriority.NORMAL,
        )

        return counter

    async def create_final_offer(
        self,
        negotiation_id: str,
        buyer_team_id: str,
        amount: Decimal,
    ) -> TransferOffer:
        """买方最终报价 (PRD 6.4)"""
        negotiation = await self._get_negotiation(negotiation_id)
        if not negotiation:
            raise ValueError("报价链不存在")
        if negotiation.buyer_team_id != buyer_team_id:
            raise ValueError("无权提交最终报价")
        if negotiation.final_used:
            raise ValueError("该报价链已使用过最终报价")
        if negotiation.status != NegotiationStatus.OPEN:
            raise ValueError("报价链不在开放状态")

        counter_offer = await self._get_offer(negotiation.counter_offer_id) if negotiation.counter_offer_id else None
        if not counter_offer or counter_offer.status != OfferStatus.PENDING_RESPONSE:
            raise ValueError("没有有效的反报价可回应")

        # 额度检查（最终报价消耗额度）
        can_send, reason = await self._can_send_offer(buyer_team_id, is_ai=False)
        if not can_send:
            raise ValueError(reason)

        initial_offer = await self._get_offer(negotiation.initial_offer_id) if negotiation.initial_offer_id else None
        if initial_offer and amount <= initial_offer.amount:
            raise ValueError("最终报价必须高于初始报价")
        if amount > counter_offer.amount:
            raise ValueError("最终报价不能高于卖方反报价；如愿意支付该金额，请直接接受反报价")

        season = await self._get_current_season()
        now = await self.clock_service.now()
        expires = now + timedelta(days=OFFER_EXPIRE_DAYS)
        player = await self._get_player(counter_offer.player_id)
        player_name = player.name if player else "某球员"

        # counter 标记为 superseded
        counter_offer.status = OfferStatus.SUPERSEDED

        final = TransferOffer(
            negotiation_id=negotiation.id,
            listing_id=counter_offer.listing_id,
            player_id=counter_offer.player_id,
            buyer_team_id=counter_offer.buyer_team_id,
            seller_team_id=counter_offer.seller_team_id,
            sender_team_id=buyer_team_id,
            receiver_team_id=counter_offer.seller_team_id,
            season_id=counter_offer.season_id,
            amount=amount,
            market_value_snapshot=counter_offer.market_value_snapshot,
            offer_kind=OfferKind.FINAL,
            round_no=3,
            status=OfferStatus.PENDING_RESPONSE,
            is_public=True,
            parent_offer_id=counter_offer.id,
            expires_at=expires,
        )
        self.db.add(final)
        await self.db.flush()

        negotiation.current_offer_id = final.id
        negotiation.final_offer_id = final.id
        negotiation.final_used = True
        negotiation.expires_at = expires
        await self.db.flush()

        # 消耗额度
        await self._consume_offer_quota(buyer_team_id)

        EventQueue.add_pending(
            self.db,
            EventType.TRANSFER_OFFER_EXPIRES,
            {"offer_id": final.id, "negotiation_id": negotiation.id, "season_id": counter_offer.season_id},
            scheduled_at=expires,
        )
        await self._schedule_ai_offer_response(counter_offer.seller_team_id, negotiation.id, counter_offer.season_id, now)

        await self._notify_team(
            counter_offer.seller_team_id,
            counter_offer.season_id,
            "收到最终报价",
            f"某球队对 {player_name} 提交最终报价 {float(amount):.0f} 万。",
            MailPriority.NORMAL,
        )

        return final

    # =====================================================================
    # 接受 / 拒绝
    # =====================================================================

    async def accept_offer(self, offer_id: str, actor_team_id: str) -> TransferRecord:
        """接受报价 (PRD 6.4, 9)"""
        offer = await self._get_offer(offer_id)
        if not offer:
            raise ValueError("报价不存在")
        if offer.receiver_team_id != actor_team_id:
            raise ValueError("无权接受此报价")
        if offer.status != OfferStatus.PENDING_RESPONSE:
            raise ValueError("该报价不再等待响应")

        negotiation = await self._get_negotiation(offer.negotiation_id)
        if not negotiation or negotiation.status != NegotiationStatus.OPEN:
            raise ValueError("报价链不在开放状态")

        # 标记为已接受
        offer.status = OfferStatus.ACCEPTED
        offer.responded_at = await self.clock_service.now()
        offer.response_actor_team_id = actor_team_id

        negotiation.status = NegotiationStatus.ACCEPTED
        await self.db.flush()

        # 进入结算
        return await self._settle_transfer(negotiation, offer)

    async def reject_offer(self, offer_id: str, actor_team_id: str) -> TransferOffer:
        """拒绝报价 (PRD 6.4)"""
        offer = await self._get_offer(offer_id)
        if not offer:
            raise ValueError("报价不存在")
        if offer.receiver_team_id != actor_team_id:
            raise ValueError("无权拒绝此报价")
        if offer.status != OfferStatus.PENDING_RESPONSE:
            raise ValueError("该报价不再等待响应")

        offer.status = OfferStatus.REJECTED
        offer.responded_at = await self.clock_service.now()
        offer.response_actor_team_id = actor_team_id

        negotiation = await self._get_negotiation(offer.negotiation_id)
        if negotiation:
            negotiation.status = NegotiationStatus.REJECTED

        await self.db.flush()
        return offer

    # =====================================================================
    # 成交结算
    # =====================================================================

    async def _settle_transfer(self, negotiation: TransferNegotiation, offer: TransferOffer) -> TransferRecord:
        """内部：执行转会成交结算 (PRD 9)"""
        season = await self._get_current_season()
        if not season:
            raise ValueError("没有进行中的赛季")

        buyer_team_id = negotiation.buyer_team_id
        seller_team_id = negotiation.seller_team_id
        player_id = negotiation.player_id
        amount = offer.amount

        # 二次校验 (PRD 9.1)
        player = await self._get_player(player_id)
        if not player or player.team_id != seller_team_id:
            raise ValueError("球员已不在卖方球队")
        if player.status == PlayerStatus.RETIRED:
            raise ValueError("球员已退役")

        # 买方余额
        team_finance = await self.db.execute(select(TeamFinance).where(TeamFinance.team_id == buyer_team_id))
        buyer_finance = team_finance.scalar_one_or_none()
        if not buyer_finance or buyer_finance.balance < amount:
            raise ValueError("买方余额不足")

        # roster 检查
        buyer_roster = await self._get_team_roster_count(buyer_team_id)
        if buyer_roster >= ContractService.ROSTER_MAX:
            raise ValueError(f"买方球队人数已达上限 {ContractService.ROSTER_MAX}")
        seller_roster = await self._get_team_roster_count(seller_team_id)
        if seller_roster - 1 < ContractService.ROSTER_MIN:
            raise ValueError(f"卖方出售后人数将低于下限 {ContractService.ROSTER_MIN}")

        # 检查是否有其他已接受的交易
        other_accepted = await self.db.execute(
            select(TransferNegotiation).where(
                and_(
                    TransferNegotiation.player_id == player_id,
                    TransferNegotiation.id != negotiation.id,
                    TransferNegotiation.status == NegotiationStatus.ACCEPTED,
                )
            )
        )
        if other_accepted.scalar_one_or_none():
            raise ValueError("该球员已被其他交易成交")

        market_value = await self.calculate_market_value(player_id, seller_team_id)
        tax = _quantize(amount * Decimal("0.05"))
        seller_income = _quantize(amount - tax)

        # 资金流
        await self.finance_service.apply_transaction(
            team_id=buyer_team_id,
            season_id=season.id,
            source_type=TransactionSourceType.TRANSFER,
            direction=TransactionDirection.EXPENSE,
            amount=amount,
            description=f"转会支出：购买 {player.name}",
            extra_data={"player_id": player_id, "negotiation_id": negotiation.id},
        )
        await self.finance_service.apply_transaction(
            team_id=seller_team_id,
            season_id=season.id,
            source_type=TransactionSourceType.TRANSFER,
            direction=TransactionDirection.INCOME,
            amount=seller_income,
            description=f"转会收入：出售 {player.name} (扣税 {float(tax):.0f})",
            extra_data={"player_id": player_id, "negotiation_id": negotiation.id},
        )

        # 球员转队 + 合同继承 (PRD 9.3, 16.3)
        player.team_id = buyer_team_id
        # 保留原合同字段
        # 同步 active player_contracts.team_id
        active_contract = await self._get_active_contract(player_id)
        if active_contract:
            active_contract.team_id = buyer_team_id
            # 阵容角色重置为 rotation
            active_contract.squad_role = SquadRole.ROTATION

        # 转会记录
        record = TransferRecord(
            player_id=player_id,
            from_team_id=seller_team_id,
            to_team_id=buyer_team_id,
            season_id=season.id,
            transfer_type=TransferType.CLUB_TRANSFER,
            amount=amount,
            market_value_snapshot=market_value,
            source_offer_id=offer.id,
            source_listing_id=negotiation.listing_id,
            completed_at=await self.clock_service.now(),
            is_public=True,
        )
        self.db.add(record)

        # 更新报价链和挂牌状态
        negotiation.status = NegotiationStatus.COMPLETED
        offer.status = OfferStatus.COMPLETED

        if negotiation.listing_id:
            listing = await self._get_listing(negotiation.listing_id)
            if listing:
                listing.status = TransferListingStatus.COMPLETED
                listing.accepted_offer_id = offer.id

        # 关闭该球员的其他 open negotiation -> outbid_closed
        other_open = await self.db.execute(
            select(TransferNegotiation).where(
                and_(
                    TransferNegotiation.player_id == player_id,
                    TransferNegotiation.id != negotiation.id,
                    TransferNegotiation.status == NegotiationStatus.OPEN,
                )
            )
        )
        for other in other_open.scalars().all():
            other.status = NegotiationStatus.REJECTED
            # 关闭它们的 pending offers
            other_offers = await self.db.execute(
                select(TransferOffer).where(
                    and_(
                        TransferOffer.negotiation_id == other.id,
                        TransferOffer.status == OfferStatus.PENDING_RESPONSE,
                    )
                )
            )
            for oo in other_offers.scalars().all():
                oo.status = OfferStatus.OUTBID_CLOSED

        await self.db.flush()

        # 刷新球员状态
        await self.state_service.recalculate_player_state(player_id, source_event="transfer_completed")

        # 通知
        await self._notify_team(
            buyer_team_id,
            season.id,
            "转会成交",
            f"你已成功签下 {player.name}，支出 {float(amount):.0f} 万。",
            MailPriority.HIGH,
        )
        await self._notify_team(
            seller_team_id,
            season.id,
            "转会成交",
            f"{player.name} 已出售，收入 {float(seller_income):.0f} 万 (扣税 {float(tax):.0f})。",
            MailPriority.HIGH,
        )

        return record

    # =====================================================================
    # 解约
    # =====================================================================

    async def preview_release_penalty(self, player_id: str, team_id: str) -> Dict:
        """预览解约违约金"""
        player = await self._get_player(player_id)
        if not player or player.team_id != team_id:
            raise ValueError("球员不属于该球队")

        season = await self._get_current_season()
        current_day = season.current_day if season else 1
        total_days = season.total_days if season else 42
        current_season_number = season.season_number if season else 0

        contract = await self._get_active_contract(player_id)
        contract_type = contract.contract_type if contract else ContractType.NORMAL
        end_season = contract.end_season_number if contract else current_season_number
        wage = player.wage if player.wage else Decimal("0")

        # 未发工资计算
        remaining_days = max(0, total_days - current_day)
        current_season_remaining = wage * Decimal(remaining_days) / Decimal(total_days)
        future_seasons = max(0, (end_season or current_season_number) - current_season_number)
        unpaid_wages = current_season_remaining + wage * Decimal(future_seasons)

        # 基础违约金
        is_rookie = contract_type == ContractType.ROOKIE
        base_rate = RELEASE_BASE_RATE_ROOKIE if is_rookie else RELEASE_BASE_RATE_NORMAL
        base_penalty = _quantize(unpaid_wages * base_rate)

        # 赛季末优惠
        if remaining_days <= SEASON_END_GRACE_DAYS and future_seasons == 0 and not is_rookie:
            base_penalty = _quantize(unpaid_wages * Decimal("0.50"))

        # 最低线
        market_value = await self.calculate_market_value(player_id, team_id)
        min_rate = RELEASE_MIN_RATE_ROOKIE if is_rookie else RELEASE_MIN_RATE_NORMAL
        min_penalty = _quantize(market_value * min_rate)

        final_penalty = max(base_penalty, min_penalty)

        team_finance = await self.db.execute(select(TeamFinance).where(TeamFinance.team_id == team_id))
        tf = team_finance.scalar_one_or_none()
        balance = tf.balance if tf else Decimal("0")

        # roster 下限检查
        roster_count = await self._get_team_roster_count(team_id)
        can_release = roster_count - 1 >= ContractService.ROSTER_MIN and balance >= final_penalty

        return {
            "player_id": player_id,
            "player_name": player.name,
            "unpaid_wages": float(unpaid_wages),
            "base_penalty": float(base_penalty),
            "min_penalty": float(min_penalty),
            "final_penalty": float(final_penalty),
            "balance": float(balance),
            "can_release": can_release,
            "reason": "" if can_release else (
                "球队人数将低于下限" if roster_count - 1 < ContractService.ROSTER_MIN else "余额不足支付违约金"
            ),
        }

    async def release_player_with_penalty(self, player_id: str, team_id: str) -> TransferRecord:
        """解约球员并支付违约金 (PRD 10)"""
        preview = await self.preview_release_penalty(player_id, team_id)
        if not preview["can_release"]:
            raise ValueError(preview["reason"])

        player = await self._get_player(player_id)
        season = await self._get_current_season()
        if not season:
            raise ValueError("没有进行中的赛季")

        penalty = Decimal(str(preview["final_penalty"]))

        # 扣违约金
        await self.finance_service.apply_transaction(
            team_id=team_id,
            season_id=season.id,
            source_type=TransactionSourceType.TRANSFER,
            direction=TransactionDirection.EXPENSE,
            amount=penalty,
            description=f"解约违约金：{player.name}",
            extra_data={"player_id": player_id, "type": "release_penalty"},
        )

        # 终止合同
        contract = await self._get_active_contract(player_id)
        if contract:
            contract.status = ContractStatus.TERMINATED

        # 球员变自由身
        player.team_id = None
        player.contract_type = ContractType.FREE
        player.contract_end_season = None
        player.wage = Decimal("0")
        player.release_clause = None
        player.wage_satisfaction = 0
        player.wage_ratio = None
        player.recommended_wage = None
        player.squad_role = SquadRole.NOT_NEEDED

        # 创建自由市场 listing
        market_value = await self.calculate_market_value(player_id, team_id)
        signing_fee = _quantize(market_value * Decimal("0.55"))
        listing = FreeAgentListing(
            player_id=player_id,
            league_id=None,
            season_id=season.id,
            origin=FreeAgentOrigin.RELEASED,
            signing_fee=signing_fee,
            recommended_wage=_quantize(market_value * Decimal("0.05")),
            listed_at_day=season.current_day,
            status=FreeAgentListingStatus.ACTIVE,
        )
        self.db.add(listing)

        # 转会记录
        record = TransferRecord(
            player_id=player_id,
            from_team_id=team_id,
            to_team_id=None,
            season_id=season.id,
            transfer_type=TransferType.RELEASE,
            amount=penalty,
            market_value_snapshot=market_value,
            completed_at=await self.clock_service.now(),
            is_public=True,
        )
        self.db.add(record)
        await self.db.flush()

        await self._notify_team(
            team_id,
            season.id,
            "球员解约",
            f"{player.name} 已解约，支付违约金 {float(penalty):.0f} 万。球员进入自由市场。",
            MailPriority.NORMAL,
        )

        return record

    # =====================================================================
    # 过期处理
    # =====================================================================

    async def process_expired_offers(self, now: Optional[datetime] = None) -> Dict:
        """处理过期报价 (PRD 6.5, 16.5)"""
        if not now:
            now = await self.clock_service.now()

        result = await self.db.execute(
            select(TransferOffer).where(
                and_(
                    TransferOffer.status == OfferStatus.PENDING_RESPONSE,
                    TransferOffer.expires_at <= now,
                )
            )
        )
        expired_offers = result.scalars().all()

        stats = {"auto_accepted": 0, "auto_rejected": 0, "settlement_failed": 0}

        for offer in expired_offers:
            negotiation = await self._get_negotiation(offer.negotiation_id)
            if not negotiation or negotiation.status != NegotiationStatus.OPEN:
                offer.status = OfferStatus.EXPIRED
                continue

            # 检查球员当前是否挂牌
            listing = await self._get_listing(negotiation.listing_id) if negotiation.listing_id else None
            is_listed = listing is not None and listing.status == TransferListingStatus.ACTIVE

            if is_listed:
                # 挂牌球员：自动接受最高有效买方报价
                # 获取所有该挂牌的 open 买方报价（initial/final）
                best_offer = await self._find_best_buyer_offer(negotiation.player_id)
                if best_offer and best_offer.id == offer.id:
                    # 这条就是最高报价
                    try:
                        await self._settle_transfer(negotiation, offer)
                        stats["auto_accepted"] += 1
                    except ValueError as e:
                        logger.warning(f"自动成交失败: {e}")
                        offer.status = OfferStatus.SETTLEMENT_FAILED
                        negotiation.status = NegotiationStatus.SETTLEMENT_FAILED
                        stats["settlement_failed"] += 1
                else:
                    offer.status = OfferStatus.EXPIRED
                    # 如果 best_offer 存在且属于另一个 negotiation，那条会在它自己的过期处理中成交
            else:
                # 非挂牌球员：自动拒绝
                offer.status = OfferStatus.EXPIRED
                negotiation.status = NegotiationStatus.EXPIRED
                stats["auto_rejected"] += 1

        await self.db.flush()
        return stats

    async def _find_best_buyer_offer(self, player_id: str) -> Optional[TransferOffer]:
        """找某挂牌球员当前最高的有效买方报价（initial/final, pending_response）"""
        result = await self.db.execute(
            select(TransferOffer).where(
                and_(
                    TransferOffer.player_id == player_id,
                    TransferOffer.offer_kind.in_([OfferKind.INITIAL, OfferKind.FINAL]),
                    TransferOffer.status == OfferStatus.PENDING_RESPONSE,
                )
            ).order_by(desc(TransferOffer.amount), asc(TransferOffer.created_at)).limit(1)
        )
        return result.scalar_one_or_none()

    async def process_listing_deadlines(self, now: Optional[datetime] = None) -> Dict:
        """处理挂牌等待期截止 (PRD 7.3)"""
        if not now:
            now = await self.clock_service.now()

        result = await self.db.execute(
            select(TransferListing).where(
                and_(
                    TransferListing.status == TransferListingStatus.ACTIVE,
                    TransferListing.decision_deadline_at <= now,
                )
            )
        )
        listings = result.scalars().all()

        stats = {"auto_accepted": 0, "expired": 0, "settlement_failed": 0}

        for listing in listings:
            best = await self._find_best_buyer_offer(listing.player_id)
            if best:
                negotiation = await self._get_negotiation(best.negotiation_id)
                if negotiation and negotiation.status == NegotiationStatus.OPEN:
                    try:
                        await self._settle_transfer(negotiation, best)
                        stats["auto_accepted"] += 1
                    except ValueError as e:
                        logger.warning(f"挂牌自动成交失败: {e}")
                        best.status = OfferStatus.SETTLEMENT_FAILED
                        if negotiation:
                            negotiation.status = NegotiationStatus.SETTLEMENT_FAILED
                        stats["settlement_failed"] += 1
            else:
                # 无报价：挂牌保持 active，但不再有自动倒计时
                listing.decision_deadline_at = None
                stats["expired"] += 1

        await self.db.flush()
        return stats

    # =====================================================================
    # 通知
    # =====================================================================

    async def _notify_team(
        self,
        team_id: str,
        season_id: str,
        subject: str,
        body: str,
        priority: MailPriority,
        related_id: Optional[str] = None,
        related_type: Optional[str] = None,
    ) -> None:
        team = await self._get_team(team_id)
        if not team or not team.user_id:
            return
        mail = Mail(
            user_id=team.user_id,
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.TRANSFER,
            priority=priority,
            sender_name="转会总监",
            subject=subject,
            body=body,
            is_read=False,
            has_action=False,
            related_id=related_id,
            related_type=related_type,
        )
        self.db.add(mail)
