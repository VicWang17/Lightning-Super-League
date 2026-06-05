"""
RosterLifecycleService - 球队名单生命周期服务
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 第 6-7 节实现。

职责：
- 赛季末处理退役、合同到期、自动补员
- 生成自由市场 listing
- 维护 roster 人数在 8-15 人之间
"""
import random
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.models.player import (
    Player,
    PlayerStatus,
    ContractType,
    OriginType,
    SquadRole,
)
from app.models.player_contract import PlayerContract, ContractStatus
from app.models.team import Team
from app.models.season import Season
from app.models.league import League, LeagueStanding
from app.models.free_agent_listing import (
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus,
)
from app.models.finance import (
    TransactionSourceType,
    TransactionDirection,
)
from app.services.contract_service import ContractService
from app.services.finance_service import FinanceService
from app.services.player_generator import PlayerGenerator
from app.services.player_number_service import assign_squad_number
from app.core.logging import get_logger

logger = get_logger("app.roster_lifecycle")


# 34+ 退役概率表 (设计文档 6.2)
_RETIREMENT_PROBABILITY = {
    34: 0.08,
    35: 0.15,
    36: 0.25,
    37: 0.40,
    38: 0.60,
    39: 0.85,
}


class RosterLifecycleService:
    """球队名单生命周期服务"""

    ROSTER_MAX = 18
    ROSTER_MIN = 8

    def __init__(self, db: AsyncSession):
        self.db = db
        self.contract_service = ContractService(db)
        self.finance_service = FinanceService(db)
        self.player_generator = PlayerGenerator()

    async def close_season(self, season_id: str) -> dict:
        """赛季末名单闭环处理（设计文档 6.1）

        处理顺序：
        1. 关闭赛季财务（已由 SEASON_FINANCE_CLOSED 事件处理）
        2. 处理 34+ 球员退役
        3. 处理合同到期未续约 → 创建自由市场 listing
        4. 对低于 8 人球队执行自动补员

        Returns:
            处理结果统计
        """
        season = await self._get_season(season_id)
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        current_season_number = season.season_number

        logger.info(f"Starting roster lifecycle close for season {season_id} (number={current_season_number})")

        # 2. 处理退役
        retired = await self._process_retirements(current_season_number)

        # 3. 处理合同到期
        expired = await self._process_contract_expirations(current_season_number, season_id)

        # 4. 退役/到期释放名额后，AI 优先签本队青训，再考虑自由市场补人
        from app.services.ai_team_management_service import AITeamManagementService
        ai_service = AITeamManagementService(self.db)
        ai_post_expiration = await ai_service.run_post_expiration_roster_decisions(season_id)

        # 5. 未签青训进入新人自由市场保护池
        from app.services.youth_academy_service import YouthAcademyService
        youth_service = YouthAcademyService(self.db)
        rookie_released = await youth_service.release_unsigned_to_rookie_market(season_id)

        # 6. 低排名 AI 保护期先挑一轮
        from app.services.ai_team_management_service import AITeamManagementService
        ai_service = AITeamManagementService(self.db)
        rookie_protection = await ai_service.run_rookie_market_protection(season_id)

        # 7. 剩余新人转普通自由市场
        await self._release_remaining_rookies_to_normal_market(season_id)

        # 8. 自动补员
        filled = await self._process_auto_fill(current_season_number, season_id)

        await self.db.commit()

        result = {
            "season_id": season_id,
            "season_number": current_season_number,
            "retired_count": retired,
            "expired_count": expired["count"],
            "listings_created": expired["listings"],
            "ai_post_expiration": ai_post_expiration,
            "rookie_released": rookie_released.get("released", 0),
            "rookie_protection": rookie_protection,
            "auto_filled_count": filled,
        }
        logger.info(f"Roster lifecycle closed: {result}")
        return result

    # =====================================================================
    # 退役处理
    # =====================================================================

    async def _process_retirements(self, current_season_number: int) -> int:
        """处理 34+ 球员退役（设计文档 6.2）

        只对 status=ACTIVE 且未在青训营的球员判断。
        返回退役人数。
        """
        result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.status == PlayerStatus.ACTIVE,
                    Player.team_id.isnot(None),  # 有球队的球员
                )
            )
        )
        players = result.scalars().all()

        retired_count = 0
        for player in players:
            age = current_season_number + abs(player.birth_offset)
            if age < 34:
                continue

            # 获取概率
            prob = _RETIREMENT_PROBABILITY.get(min(age, 39), 0.85)

            if random.random() < prob:
                await self._retire_player(player, current_season_number)
                retired_count += 1

        await self.db.flush()
        logger.info(f"Retired {retired_count} players for season end")
        return retired_count

    async def _retire_player(self, player: Player, current_season_number: int) -> None:
        """退役单个球员"""
        # 终止活跃合同
        result = await self.db.execute(
            select(PlayerContract).where(
                and_(
                    PlayerContract.player_id == player.id,
                    PlayerContract.status == ContractStatus.ACTIVE,
                )
            )
        )
        contract = result.scalar_one_or_none()
        if contract:
            contract.status = ContractStatus.TERMINATED

        # 更新球员状态
        player.status = PlayerStatus.RETIRED
        player.team_id = None
        player.contract_type = ContractType.FREE
        player.contract_end_season = None
        player.wage = Decimal("0")
        player.retired_at_season = current_season_number

        # 更新相关 listing
        result = await self.db.execute(
            select(FreeAgentListing).where(
                and_(
                    FreeAgentListing.player_id == player.id,
                    FreeAgentListing.status == ListingStatus.ACTIVE,
                )
            )
        )
        listing = result.scalar_one_or_none()
        if listing:
            listing.status = ListingStatus.RETIRED

        logger.info(f"Player retired: {player.id} ({player.name}, age={current_season_number + abs(player.birth_offset)})")

    # =====================================================================
    # 合同到期处理
    # =====================================================================

    async def _process_contract_expirations(self, current_season_number: int, season_id: str) -> dict:
        """处理合同到期未续约球员（设计文档 6.3）

        将 end_season_number <= current_season_number 的活跃合同标记为过期，
        球员变为自由身，并创建自由市场 listing。

        Returns:
            {"count": 过期合同数, "listings": 创建的 listing 数}
        """
        result = await self.db.execute(
            select(PlayerContract)
            .where(PlayerContract.status == ContractStatus.ACTIVE)
            .where(PlayerContract.end_season_number.isnot(None))
        )
        contracts = result.scalars().all()

        expired_count = 0
        listings_created = 0

        for contract in contracts:
            if contract.end_season_number <= current_season_number:
                # 标记合同过期
                contract.status = ContractStatus.EXPIRED

                # 获取球员
                player = await self._get_player(contract.player_id)
                if not player:
                    continue

                # 球员变为自由身
                if player.team_id == contract.team_id:
                    player.team_id = None
                    player.contract_type = ContractType.FREE
                    player.contract_end_season = None
                    player.wage = Decimal("0")
                    player.squad_role = SquadRole.NOT_NEEDED

                # 创建自由市场 listing（仅对未退役球员）
                if player.status != PlayerStatus.RETIRED:
                    listing = await self._create_free_agent_listing(
                        player=player,
                        season_id=contract.season_id or season_id,
                        origin=FreeAgentOrigin.CONTRACT_EXPIRED,
                    )
                    if listing:
                        listings_created += 1

                expired_count += 1

        await self.db.flush()
        logger.info(f"Expired {expired_count} contracts, created {listings_created} listings")
        return {"count": expired_count, "listings": listings_created}

    async def _create_free_agent_listing(
        self,
        player: Player,
        season_id: str,
        origin: FreeAgentOrigin,
        origin_team_id: Optional[str] = None,
    ) -> Optional[FreeAgentListing]:
        """创建自由市场 listing"""
        # 检查是否已有活跃 listing
        result = await self.db.execute(
            select(FreeAgentListing).where(
                and_(
                    FreeAgentListing.player_id == player.id,
                    FreeAgentListing.status == ListingStatus.ACTIVE,
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return None

        # 计算签字费
        signing_fee = await self._calculate_signing_fee(player, origin)

        # 计算建议工资
        if origin_team_id:
            recommended_wage = await self.contract_service.calculate_recommended_wage(
                player.id, origin_team_id, ContractType.NORMAL, SquadRole.FIRST_TEAM
            )
        else:
            recommended_wage = player.recommended_wage or Decimal("1000.00")

        listing = FreeAgentListing(
            player_id=player.id,
            league_id=player.draft_league_id,
            season_id=season_id,
            origin=origin,
            signing_fee=signing_fee,
            recommended_wage=recommended_wage,
            listed_at_day=0,  # 赛季末，标记为 0
            status=ListingStatus.ACTIVE,
            extra_data={
                "origin_team_id": origin_team_id,
            },
        )
        self.db.add(listing)
        return listing

    async def _calculate_signing_fee(
        self,
        player: Player,
        origin: FreeAgentOrigin,
    ) -> Decimal:
        """计算签字费（设计文档 6.4）

        signing_fee = clamp(market_value * origin_factor * age_factor, min_fee, max_fee)
        """
        origin_factors = {
            FreeAgentOrigin.CONTRACT_EXPIRED: Decimal("0.08"),
            FreeAgentOrigin.RELEASED: Decimal("0.06"),
            FreeAgentOrigin.DRAFT_UNSELECTED: Decimal("0.04"),
            FreeAgentOrigin.DRAFT_DECLINED: Decimal("0.04"),
            FreeAgentOrigin.AUTO_GENERATED: Decimal("0.02"),
        }

        age = abs(player.birth_offset)  # 简化，使用相对年龄
        if age <= 20:
            age_factor = Decimal("1.15")
        elif age <= 28:
            age_factor = Decimal("1.00")
        elif age <= 33:
            age_factor = Decimal("0.75")
        else:
            age_factor = Decimal("0.45")

        base_fee = player.market_value * origin_factors.get(origin, Decimal("0.08")) * age_factor

        # min_fee = OVR 35 球员建议工资的 10%
        # max_fee = 该球员建议工资的 50%
        min_fee = Decimal("1500.00")  # 简化固定值
        max_fee = (player.recommended_wage or Decimal("30000.00")) * Decimal("0.50")

        fee = max(min_fee, min(base_fee, max_fee))
        return fee.quantize(Decimal("0.01"))

    # =====================================================================
    # 自动补员
    # =====================================================================

    async def _process_auto_fill(self, current_season_number: int, season_id: str) -> int:
        """对低于 8 人的球队执行自动补员（设计文档 7.2）

        返回补员总人数。
        """
        # 获取所有球队
        result = await self.db.execute(select(Team))
        teams = result.scalars().all()

        total_filled = 0
        for team in teams:
            roster_count = await self._get_team_roster_count(team.id)
            if roster_count >= self.ROSTER_MIN:
                continue

            needed = self.ROSTER_MIN - roster_count
            filled = await self._auto_fill_team(team, needed, current_season_number, season_id)
            total_filled += filled

        await self.db.flush()
        logger.info(f"Auto-filled {total_filled} players across all teams")
        return total_filled

    async def _auto_fill_team(
        self,
        team: Team,
        needed: int,
        current_season_number: int,
        season_id: str,
    ) -> int:
        """为单个球队自动补员

        顺序：
        1. 优先自动签约本队青训营剩余球员
        2. 若青训不足，从本联赛选秀未中/被放弃池签
        3. 若仍不足，生成低数值兜底球员
        """
        filled = 0

        # TODO: Phase 3/4 实现后补充青训和选秀补员逻辑
        # 现在直接生成兜底球员
        for _ in range(needed):
            player = self.player_generator.generate_auto_fill_player(
                team, current_season_number
            )
            self.db.add(player)
            await self.db.flush()

            # 分配队内号码
            await assign_squad_number(self.db, player, team.id)

            # 签 1 年合同
            try:
                await self.contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.NORMAL,
                    years=1,
                    wage=player.wage,
                    squad_role=SquadRole.BACKUP,
                    source="auto_fill",
                )
                filled += 1
            except Exception as exc:
                logger.warning(f"Auto-fill signing failed for team {team.id}: {exc}")

        if filled > 0:
            logger.info(f"Auto-filled {filled} players for team {team.id}")

        return filled

    # =====================================================================
    # 内部辅助
    # =====================================================================

    async def _get_season(self, season_id: str) -> Optional[Season]:
        result = await self.db.execute(select(Season).where(Season.id == season_id))
        return result.scalar_one_or_none()

    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()

    async def _get_team_roster_count(self, team_id: str) -> int:
        result = await self.db.execute(
            select(func.count(Player.id))
            .where(Player.team_id == team_id)
            .where(Player.status.in_([
                PlayerStatus.ACTIVE,
                PlayerStatus.INJURED,
                PlayerStatus.SUSPENDED,
            ]))
        )
        return result.scalar_one_or_none() or 0

    async def _release_remaining_rookies_to_normal_market(self, season_id: str) -> int:
        """保护期结束后，将剩余新人的 rookie_protected 标记清除"""
        from app.models.free_agent_listing import FreeAgentListing, ListingStatus

        result = await self.db.execute(
            select(FreeAgentListing).where(
                and_(
                    FreeAgentListing.status == ListingStatus.ACTIVE,
                )
            )
        )
        listings = result.scalars().all()

        released = 0
        for listing in listings:
            extra = dict(listing.extra_data or {})
            if extra.get("rookie_protected") and not extra.get("protection_processed"):
                extra["rookie_protected"] = False
                extra["protection_processed"] = True
                extra["protection_released_to_normal_market"] = True
                listing.extra_data = extra
                released += 1

        await self.db.flush()
        logger.info(f"Released {released} remaining rookies to normal market for season {season_id}")
        return released
