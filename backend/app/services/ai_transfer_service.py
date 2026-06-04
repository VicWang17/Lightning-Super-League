"""
AI Transfer service - AI 转会市场决策服务
按 TRANSFER-MARKET-PRD.md v0.2 第 11 节实现。
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.models import (
    Player,
    PlayerStatus,
    ContractType,
    Team,
    TeamFinance,
    Season,
    SeasonStatus,
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus as FreeAgentListingStatus,
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
from app.models.finance import TeamSeasonFinance, FinancialHealth, OverspendLevel
from app.core.logging import get_logger
from app.services.transfer_service import TransferService
from app.services.contract_service import ContractService
from app.services.game_clock_state import GameClockStateService

logger = get_logger("app.ai_transfer")

# AI 球队画像常量
AI_TARGET_ROSTER = 16
AI_SOFT_MAX_ROSTER = 17


class AITransferService:
    """AI 转会市场决策服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.transfer_service = TransferService(db)
        self.contract_service = ContractService(db)
        self.clock_service = GameClockStateService(db)

    # =====================================================================
    # 主入口
    # =====================================================================

    async def run_ai_transfer_market_scan(self) -> Dict:
        """每日 AI 转会市场扫描入口"""
        season = await self.transfer_service._get_current_season()
        if not season:
            return {"skipped": True, "reason": "no_season"}

        ai_teams = await self._get_ai_teams()
        stats = {"offers_handled": 0, "players_listed": 0, "offers_sent": 0, "releases": 0}

        for team in ai_teams:
            try:
                # 1. 处理收到的报价
                handled = await self._handle_received_offers(team.id)
                stats["offers_handled"] += handled

                # 2. 挂牌冗余球员
                listed = await self._list_surplus_players(team.id)
                stats["players_listed"] += listed

                # 3. 主动报价（限制每天最多1次）
                sent = await self._scan_market_for_targets(team.id)
                stats["offers_sent"] += sent

                # 4. 极端情况解约
                released = await self._consider_release(team.id)
                stats["releases"] += released
            except Exception as e:
                logger.error(f"AI transfer scan failed for team {team.id}: {e}")

        return stats

    async def run_ai_offer_response(self, negotiation_id: str) -> None:
        """AI 收到报价后快速响应"""
        negotiation = await self.transfer_service._get_negotiation(negotiation_id)
        if not negotiation or negotiation.status != NegotiationStatus.OPEN:
            return

        await self._evaluate_and_respond(negotiation)

    # =====================================================================
    # 辅助查询
    # =====================================================================

    async def _get_ai_teams(self) -> List[Team]:
        result = await self.db.execute(select(Team).where(Team.is_ai == True))
        return result.scalars().all()

    async def _get_team_finance_health(self, team_id: str) -> tuple[FinancialHealth, OverspendLevel]:
        season = await self.transfer_service._get_current_season()
        if not season:
            return FinancialHealth.B, OverspendLevel.NONE
        result = await self.db.execute(
            select(TeamSeasonFinance).where(
                and_(
                    TeamSeasonFinance.team_id == team_id,
                    TeamSeasonFinance.season_id == season.id,
                )
            )
        )
        tsf = result.scalar_one_or_none()
        if not tsf:
            return FinancialHealth.B, OverspendLevel.NONE
        return tsf.financial_health, tsf.overspend_level

    async def _get_team_players(self, team_id: str) -> List[Player]:
        result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.team_id == team_id,
                    Player.status != PlayerStatus.RETIRED,
                )
            )
        )
        return result.scalars().all()

    async def _get_position_counts(self, team_id: str) -> Dict[str, int]:
        players = await self._get_team_players(team_id)
        counts = {"FW": 0, "MF": 0, "DF": 0, "GK": 0}
        for p in players:
            if p.position.value in counts:
                counts[p.position.value] += 1
        return counts

    async def _get_active_listings(self, exclude_team_id: Optional[str] = None) -> List[TransferListing]:
        query = select(TransferListing).where(TransferListing.status == TransferListingStatus.ACTIVE)
        if exclude_team_id:
            query = query.where(TransferListing.seller_team_id != exclude_team_id)
        result = await self.db.execute(query)
        return result.scalars().all()

    # =====================================================================
    # 球员价值评估
    # =====================================================================

    async def _evaluate_player_for_ai(
        self,
        team_id: str,
        player_id: str,
        is_selling: bool = False,
    ) -> Decimal:
        """AI 内部价值评估 (PRD 11.2)"""
        market_value = await self.transfer_service.calculate_market_value(player_id, team_id)
        position_counts = await self._get_position_counts(team_id)
        players = await self._get_team_players(team_id)

        player = await self.transfer_service._get_player(player_id)
        if not player:
            return market_value

        # 位置需求系数
        pos = player.position.value
        target = {"FW": 3, "MF": 4, "DF": 3, "GK": 2}
        current = position_counts.get(pos, 0)
        if current < target.get(pos, 2):
            position_factor = Decimal("1.15") if not is_selling else Decimal("1.00")
        elif current > target.get(pos, 2) + 1:
            position_factor = Decimal("0.85") if is_selling else Decimal("1.00")
        else:
            position_factor = Decimal("1.00")

        # 队内保护系数
        sorted_by_ovr = sorted(players, key=lambda p: p.ovr, reverse=True)
        ovr_rank = next((i for i, p in enumerate(sorted_by_ovr) if p.id == player_id), len(players))

        if ovr_rank < 3:
            protect_factor = Decimal("1.30") if is_selling else Decimal("1.00")
        elif current <= target.get(pos, 2):
            protect_factor = Decimal("1.15") if is_selling else Decimal("1.00")
        elif ovr_rank >= len(players) * 0.7 and current > target.get(pos, 2) + 1:
            protect_factor = Decimal("0.85") if is_selling else Decimal("1.00")
        else:
            protect_factor = Decimal("1.00")

        # 财政压力系数
        health, overspend = await self._get_team_finance_health(team_id)
        if overspend in (OverspendLevel.RESTRICTED, OverspendLevel.CRISIS):
            finance_factor = Decimal("0.80") if is_selling else Decimal("1.00")
        elif health == FinancialHealth.D:
            finance_factor = Decimal("0.85") if is_selling else Decimal("1.00")
        elif health == FinancialHealth.C:
            finance_factor = Decimal("0.90") if is_selling else Decimal("1.00")
        else:
            finance_factor = Decimal("1.00")

        # 年龄规划系数
        age = (await self.transfer_service._get_current_season()).season_number + abs(player.birth_offset) if await self.transfer_service._get_current_season() else 25
        if age <= 21:
            age_plan_factor = Decimal("1.10") if not is_selling else Decimal("1.20")
        elif age >= 31:
            age_plan_factor = Decimal("0.90") if not is_selling else Decimal("0.80")
        else:
            age_plan_factor = Decimal("1.00")

        return _quantize(market_value * position_factor * protect_factor * finance_factor * age_plan_factor)

    # =====================================================================
    # 处理收到的报价
    # =====================================================================

    async def _handle_received_offers(self, team_id: str) -> int:
        """处理 AI 球队收到的所有待响应报价"""
        result = await self.db.execute(
            select(TransferOffer).where(
                and_(
                    TransferOffer.receiver_team_id == team_id,
                    TransferOffer.status == OfferStatus.PENDING_RESPONSE,
                )
            )
        )
        offers = result.scalars().all()
        count = 0
        for offer in offers:
            try:
                negotiation = await self.transfer_service._get_negotiation(offer.negotiation_id)
                if not negotiation or negotiation.status != NegotiationStatus.OPEN:
                    continue
                await self._evaluate_and_respond(negotiation)
                count += 1
            except Exception as e:
                logger.warning(f"AI handle offer failed: {e}")
        return count

    async def _evaluate_and_respond(self, negotiation: TransferNegotiation) -> None:
        """AI 评估单个报价链并做出决策"""
        team_id = negotiation.seller_team_id
        player_id = negotiation.player_id

        ai_value = await self._evaluate_player_for_ai(team_id, player_id, is_selling=True)
        current_offer = await self.transfer_service._get_offer(negotiation.current_offer_id)
        if not current_offer:
            return

        amount = current_offer.amount
        offer_kind = current_offer.offer_kind

        # 是否是挂牌球员
        listing = await self.transfer_service._get_listing(negotiation.listing_id) if negotiation.listing_id else None
        is_listed = listing is not None and listing.status == TransferListingStatus.ACTIVE

        if offer_kind == OfferKind.INITIAL:
            await self._respond_to_initial(team_id, negotiation, current_offer, ai_value, is_listed)
        elif offer_kind == OfferKind.FINAL:
            await self._respond_to_final(team_id, negotiation, current_offer, ai_value, is_listed)

    async def _respond_to_initial(
        self,
        team_id: str,
        negotiation: TransferNegotiation,
        offer: TransferOffer,
        ai_value: Decimal,
        is_listed: bool,
    ) -> None:
        """AI 对初始报价的决策"""
        amount = offer.amount
        roster_count = await self.transfer_service._get_team_roster_count(team_id)
        health, _ = await self._get_team_finance_health(team_id)

        # 高保护阈值调整
        accept_threshold = ai_value * Decimal("0.95") if is_listed else ai_value * Decimal("1.05")
        if health in (FinancialHealth.D,):
            accept_threshold = accept_threshold * Decimal("0.85")
        elif health == FinancialHealth.C:
            accept_threshold = accept_threshold * Decimal("0.90")

        # 如果报价 >= 阈值：接受
        if amount >= accept_threshold:
            await self.transfer_service.accept_offer(offer.id, team_id)
            return

        # 如果报价过低且未使用反报价：反报价
        if not negotiation.counter_used and amount >= ai_value * Decimal("0.60"):
            counter_amount = max(amount * Decimal("1.10"), ai_value * Decimal("1.05"))
            counter_amount = min(counter_amount, amount * Decimal("1.50"))
            try:
                await self.transfer_service.create_counter_offer(
                    offer.id, team_id, _quantize(counter_amount)
                )
            except ValueError:
                await self.transfer_service.reject_offer(offer.id, team_id)
            return

        # 否则拒绝
        await self.transfer_service.reject_offer(offer.id, team_id)

    async def _respond_to_final(
        self,
        team_id: str,
        negotiation: TransferNegotiation,
        offer: TransferOffer,
        ai_value: Decimal,
        is_listed: bool,
    ) -> None:
        """AI 对最终报价的决策"""
        amount = offer.amount
        accept_threshold = ai_value * Decimal("0.95") if is_listed else ai_value * Decimal("1.05")
        health, _ = await self._get_team_finance_health(team_id)
        if health in (FinancialHealth.D,):
            accept_threshold = accept_threshold * Decimal("0.85")
        elif health == FinancialHealth.C:
            accept_threshold = accept_threshold * Decimal("0.90")

        if amount >= accept_threshold:
            await self.transfer_service.accept_offer(offer.id, team_id)
        else:
            await self.transfer_service.reject_offer(offer.id, team_id)

    # =====================================================================
    # AI 主动挂牌
    # =====================================================================

    async def _list_surplus_players(self, team_id: str) -> int:
        """AI 挂牌冗余球员 (PRD 11.5)"""
        players = await self._get_team_players(team_id)
        position_counts = await self._get_position_counts(team_id)
        target = {"FW": 3, "MF": 4, "DF": 3, "GK": 2}
        count = 0

        for player in players:
            pos = player.position.value
            # 冗余判断
            is_redundant = position_counts.get(pos, 0) > target.get(pos, 2) + 1
            is_high_wage_low_value = False
            is_expiring = False

            contract = await self.transfer_service._get_active_contract(player.id)
            season = await self.transfer_service._get_current_season()
            if contract and season:
                if contract.end_season_number and contract.end_season_number <= season.season_number + 1:
                    is_expiring = True

            if is_redundant or is_expiring:
                # 检查是否已在挂牌
                existing = await self.db.execute(
                    select(TransferListing).where(
                        and_(
                            TransferListing.player_id == player.id,
                            TransferListing.status == TransferListingStatus.ACTIVE,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                market_value = await self.transfer_service.calculate_market_value(player.id, team_id)
                if is_expiring:
                    list_price = _quantize(market_value * Decimal(random.uniform("0.90", "1.00")))
                else:
                    list_price = _quantize(market_value * Decimal(random.uniform("1.00", "1.20")))

                try:
                    await self.transfer_service.list_player(player.id, team_id, list_price)
                    count += 1
                except ValueError:
                    pass

        return count

    # =====================================================================
    # AI 主动报价
    # =====================================================================

    async def _scan_market_for_targets(self, team_id: str) -> int:
        """AI 扫描市场并主动报价 (PRD 11.4)"""
        # 检查额度
        can_send, _ = await self.transfer_service._can_send_offer(team_id, is_ai=True)
        if not can_send:
            return 0

        roster_count = await self.transfer_service._get_team_roster_count(team_id)
        if roster_count >= AI_SOFT_MAX_ROSTER:
            return 0

        health, overspend = await self._get_team_finance_health(team_id)
        if overspend in (OverspendLevel.RESTRICTED, OverspendLevel.CRISIS):
            return 0

        position_counts = await self._get_position_counts(team_id)
        target = {"FW": 3, "MF": 4, "DF": 3, "GK": 2}
        shortages = {pos: max(0, target.get(pos, 2) - count) for pos, count in position_counts.items()}

        # 优先看挂牌市场
        listings = await self._get_active_listings(exclude_team_id=team_id)
        candidates = []

        for listing in listings:
            player = await self.transfer_service._get_player(listing.player_id)
            if not player:
                continue

            ai_value = await self._evaluate_player_for_ai(team_id, player.id, is_selling=False)
            if listing.list_price <= ai_value * Decimal("1.05"):
                score = ai_value - listing.list_price
                if shortages.get(player.position.value, 0) > 0:
                    score += Decimal("5000000")
                candidates.append((listing, player, score))

        if not candidates:
            return 0

        # 按分数排序，取最高
        candidates.sort(key=lambda x: x[2], reverse=True)
        best = candidates[0]
        listing, player, _ = best

        try:
            offer_amount = max(listing.list_price, _quantize(best[1].ovr * 10000 + 50000))
            await self.transfer_service.create_offer(
                player_id=player.id,
                buyer_team_id=team_id,
                amount=offer_amount,
                listing_id=listing.id,
            )
            return 1
        except ValueError as e:
            logger.debug(f"AI offer failed: {e}")
            return 0

    # =====================================================================
    # AI 解约
    # =====================================================================

    async def _consider_release(self, team_id: str) -> int:
        """AI 考虑解约 (PRD 11.6)"""
        players = await self._get_team_players(team_id)
        if len(players) <= ContractService.ROSTER_MIN:
            return 0

        health, overspend = await self._get_team_finance_health(team_id)
        if overspend != OverspendLevel.CRISIS:
            return 0

        # 找价值最低、工资最高的冗余球员
        candidates = []
        for player in players:
            market_value = await self.transfer_service.calculate_market_value(player.id, team_id)
            if player.wage > market_value * Decimal("0.10"):
                candidates.append((player, market_value))

        if not candidates:
            return 0

        candidates.sort(key=lambda x: x[0].wage - x[1], reverse=True)
        worst = candidates[0][0]

        try:
            preview = await self.transfer_service.preview_release_penalty(worst.id, team_id)
            if preview["can_release"]:
                await self.transfer_service.release_player_with_penalty(worst.id, team_id)
                return 1
        except ValueError:
            pass
        return 0


def _quantize(value: Decimal | int | float | str) -> Decimal:
    from decimal import ROUND_HALF_UP
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
