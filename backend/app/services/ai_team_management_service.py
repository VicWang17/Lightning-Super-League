"""
AI Team Management Service - AI 球队自主运营服务
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 第 14 节实现。

目标：保证全 AI 联赛可以持续运转，无需玩家干预。
"""
import random
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, asc

from app.models import (
    Player,
    PlayerPosition,
    PlayerStatus,
    ContractType,
    SquadRole,
    OriginType,
    YouthAcademyPlayer,
    AcademyPlayerStatus,
    GrowthSpeed,
    FreeAgentListing,
    ListingStatus,
    Season,
    SeasonStatus,
    Team,
    User,
)
from app.models.player_contract import PlayerContract, ContractStatus
from app.models.transfer import TransferRecord, TransferType
from app.models.league import League, LeagueStanding
from app.models.wage_config import WageConfig, WageConfigType
from app.services.contract_service import ContractService
from app.services.finance_service import FinanceService
from app.core.logging import get_logger

logger = get_logger("app.ai_team_management")


class AITeamManagementService:
    """AI 球队自主运营服务"""

    AI_TARGET_ROSTER = 16
    AI_SOFT_MAX_ROSTER = 17
    AI_FREE_MARKET_MAX_SIGNINGS_PER_PASS = 3
    AI_ACADEMY_MAX_SIGNINGS_PER_PASS = 2

    def __init__(self, db: AsyncSession):
        self.db = db
        self.contract_service = ContractService(db)

    # =====================================================================
    # 辅助：获取 AI 球队
    # =====================================================================

    async def _get_ai_teams(self) -> List[Team]:
        """获取所有 AI 球队"""
        result = await self.db.execute(
            select(Team)
            .join(User, Team.user_id == User.id)
            .where(User.is_ai == True)
        )
        return list(result.scalars().all())

    async def _get_team_players(self, team_id: str) -> List[Player]:
        """获取球队一线队球员"""
        result = await self.db.execute(
            select(Player)
            .where(
                and_(
                    Player.team_id == team_id,
                    Player.status == PlayerStatus.ACTIVE,
                )
            )
            .order_by(desc(Player.ovr))
        )
        return list(result.scalars().all())

    async def _get_team_injured_players(self, team_id: str) -> List[Player]:
        """获取球队当前伤病球员"""
        result = await self.db.execute(
            select(Player)
            .where(
                and_(
                    Player.team_id == team_id,
                    Player.status == PlayerStatus.INJURED,
                )
            )
            .order_by(desc(Player.ovr))
        )
        return list(result.scalars().all())

    async def _get_team_roster_count(self, team_id: str) -> int:
        """获取球队当前一线队人数。"""
        result = await self.db.execute(
            select(func.count(Player.id))
            .where(Player.team_id == team_id)
            .where(Player.status.in_([PlayerStatus.ACTIVE, PlayerStatus.INJURED, PlayerStatus.SUSPENDED]))
        )
        return result.scalar_one_or_none() or 0

    async def _get_current_season(self) -> Optional[Season]:
        result = await self.db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number)).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_team_academy_players(self, team_id: str, season_id: str) -> List:
        """获取球队青训营球员"""
        result = await self.db.execute(
            select(YouthAcademyPlayer, Player)
            .join(Player, YouthAcademyPlayer.player_id == Player.id)
            .where(
                and_(
                    YouthAcademyPlayer.team_id == team_id,
                    YouthAcademyPlayer.season_id == season_id,
                    YouthAcademyPlayer.status == AcademyPlayerStatus.IN_ACADEMY,
                )
            )
            .order_by(desc(Player.ovr))
        )
        return list(result.all())

    # =====================================================================
    # 伤病医疗决策 (EMERGENCY-FUND-INJURY-FINANCE-DESIGN.md §10)
    # =====================================================================

    async def run_injury_treatment_decisions(self, season_id: str) -> Dict[str, Any]:
        """AI 球队批量伤病治疗决策"""
        season = await self._get_current_season()
        if not season:
            return {"processed": 0, "treated": 0}

        ai_teams = await self._get_ai_teams()
        treated_count = 0

        from app.services.injury_treatment_service import InjuryTreatmentService
        treatment_service = InjuryTreatmentService(self.db)

        for team in ai_teams:
            try:
                injured_players = await self._get_team_injured_players(team.id)
                for player in injured_players:
                    result = await treatment_service.ai_evaluate_and_treat(
                        team_id=team.id,
                        player=player,
                        season_id=season_id,
                    )
                    if result:
                        treated_count += 1
            except Exception as e:
                logger.exception(f"AI injury treatment decision failed for team {team.id}")

        await self.db.commit()
        logger.info(f"AI 伤病治疗决策完成: treated={treated_count}, teams={len(ai_teams)}")
        return {"processed": len(ai_teams), "treated": treated_count}

    # =====================================================================
    # 1. 赛季开始规划
    # =====================================================================

    async def run_season_start_planning(self, season_id: str) -> Dict[str, Any]:
        """赛季开始：AI 球队检查名单结构、工资帽"""
        season = await self._get_current_season()
        if not season:
            return {"processed": 0}

        ai_teams = await self._get_ai_teams()
        processed = 0

        for team in ai_teams:
            try:
                await self._season_start_for_team(team, season)
                processed += 1
            except Exception as e:
                logger.exception(f"AI season start failed for team {team.id}")

        await self.db.commit()
        return {"processed": processed}

    async def _season_start_for_team(self, team: Team, season: Season) -> None:
        """单个 AI 球队的赛季开始检查"""
        players = await self._get_team_players(team.id)

        # 检查 roster 人数
        if len(players) < 10:
            # 赛季初人数不足，后续自由市场会补
            logger.info(f"AI team {team.id} roster low ({len(players)}), will supplement later")

    # =====================================================================
    # 2. 青训刷新后决策
    # =====================================================================

    async def run_midseason_academy_decisions(self, season_id: str, day: int) -> Dict[str, Any]:
        """青训刷新后：AI 判断是否签约青训球员"""
        season = await self._get_current_season()
        if not season:
            return {"signed": 0, "declined": 0}

        ai_teams = await self._get_ai_teams()
        signed_count = 0
        declined_count = 0
        blocked_full = 0
        below_threshold = 0
        sign_failed = 0
        candidates = 0

        for team in ai_teams:
            try:
                result = await _ai_academy_decisions_for_team(self.db, team, season)
                signed_count += result["signed"]
                declined_count += result["declined"]
                blocked_full += result["blocked_full"]
                below_threshold += result["below_threshold"]
                sign_failed += result["sign_failed"]
                candidates += result["candidates"]
            except Exception as e:
                logger.exception(f"AI academy decision failed for team {team.id}")

        await self.db.commit()
        return {
            "signed": signed_count,
            "declined": declined_count,
            "candidates": candidates,
            "blocked_full": blocked_full,
            "below_threshold": below_threshold,
            "sign_failed": sign_failed,
        }

    # =====================================================================
    # 3. 选秀志愿（已移除）
    # =====================================================================

    # 选秀系统已简化，不再使用志愿排序

    # _calculate_draft_value_score 已随选秀系统移除

    # =====================================================================
    # 4. 选秀签约决策（已移除）
    # =====================================================================

    # 选秀系统已简化

    # =====================================================================
    # 5. 赛季末续约与 roster 决策
    # =====================================================================

    async def run_season_end_roster_decisions(self, season_id: str) -> Dict[str, Any]:
        """赛季末合同到期前：AI 先续约关键球员。"""
        season = await self._get_current_season()
        if not season:
            return {"renewed": 0, "academy_signed": 0, "free_market_signed": 0}

        ai_teams = await self._get_ai_teams()
        renewed_count = 0

        for team in ai_teams:
            try:
                r = await self._ai_renew_contracts(team, season)
                renewed_count += r
            except Exception as e:
                logger.exception(f"AI season end failed for team {team.id}")

        await self.db.commit()
        return {
            "renewed": renewed_count,
            "academy_signed": 0,
            "free_market_signed": 0,
        }

    async def run_post_expiration_roster_decisions(self, season_id: str) -> Dict[str, Any]:
        """退役/合同过期释放名额后：AI 再尝试签青训和自由市场补人。"""
        season = await self._get_current_season()
        if not season:
            return {"academy_signed": 0, "free_market_signed": 0}

        ai_teams = await self._get_ai_teams()
        academy_signed_count = 0
        free_market_signed_count = 0
        academy_candidates = 0
        academy_blocked_full = 0
        academy_below_threshold = 0
        academy_sign_failed = 0

        for team in ai_teams:
            try:
                a = await self._ai_sign_academy_before_season_end(team, season)
                academy_signed_count += a["signed"]
                academy_candidates += a["candidates"]
                academy_blocked_full += a["blocked_full"]
                academy_below_threshold += a["below_threshold"]
                academy_sign_failed += a["sign_failed"]

                f = await self._ai_sign_free_market(team, season)
                free_market_signed_count += f
            except Exception:
                logger.exception(f"AI post-expiration roster decision failed for team {team.id}")

        await self.db.commit()
        return {
            "academy_signed": academy_signed_count,
            "free_market_signed": free_market_signed_count,
            "academy_candidates": academy_candidates,
            "academy_blocked_full": academy_blocked_full,
            "academy_below_threshold": academy_below_threshold,
            "academy_sign_failed": academy_sign_failed,
        }

    async def _ai_renew_contracts(self, team: Team, season: Season) -> int:
        """AI 续约合同即将到期的球员"""
        # 获取球队所有球员
        players = await self._get_team_players(team.id)

        # 计算 keep_score
        scored_players = []
        for idx, player in enumerate(players):
            score = await self._calculate_keep_score(team, player, idx, len(players), season)
            scored_players.append((player, score))

        # 按分数降序
        scored_players.sort(key=lambda x: -x[1])

        # 获取工资帽压力
        finance_service = FinanceService(self.db)
        season_finance = await finance_service._get_or_create_team_season_finance(team.id, season.id)
        total_wage = await finance_service._calculate_team_wage_bill(team.id)
        wage_cap = season_finance.wage_cap if season_finance.wage_cap > 0 else Decimal("1")
        pressure = float(total_wage / wage_cap) if wage_cap > 0 else 0.0

        renewed = 0
        max_renew = 6 if pressure > 0.95 else 8

        for renew_rank, (player, score) in enumerate(scored_players[:max_renew]):
            # 检查合同是否即将到期
            if player.contract_end_season is None:
                continue
            if player.contract_end_season < season.season_number:
                continue  # 已过期，不续约
            if player.contract_end_season > season.season_number + 1:
                continue  # 还有时间

            age = season.season_number + abs(player.birth_offset)
            if age >= 34 and score < 50:
                continue  # 34+ 且不是核心，不续约

            try:
                years = self._ai_determine_contract_years(age)
                role = self._ai_determine_role(player, renew_rank)
                renewal_contract_type = (
                    ContractType.NORMAL
                    if player.contract_type == ContractType.ROOKIE
                    else player.contract_type or ContractType.NORMAL
                )

                recommended = await self.contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=renewal_contract_type,
                    squad_role=role,
                )

                # AI 工资调整
                if score >= 70:
                    wage = recommended
                elif score >= 50:
                    wage = recommended * Decimal("0.95")
                else:
                    wage = recommended * Decimal("0.85")

                can_renew = await finance_service.can_sign_player(
                    team.id,
                    wage.quantize(Decimal("1")),
                    replaced_player_id=player.id,
                    season_id=season.id,
                )
                if not can_renew:
                    continue

                await self.contract_service.renew_contract(
                    player_id=player.id,
                    team_id=team.id,
                    years=years,
                    wage=wage.quantize(Decimal("1")),
                    squad_role=role,
                )
                renewed += 1
            except Exception as e:
                logger.warning(f"AI renew failed for player {player.id}: {e}")

        return renewed

    async def _calculate_keep_score(self, team: Team, player: Player, rank: int, total: int, season: Season) -> float:
        """计算球员留队分"""
        score = 0.0

        # OVR 分（前 8 名优先）
        if rank < 8:
            score += (8 - rank) * 5
        score += float(player.ovr) * 0.3

        # 潜力分
        potential_bonus = {"S": 15, "A": 10, "B": 5, "C": 2, "D": 0}
        score += potential_bonus.get(player.potential_letter.value if hasattr(player.potential_letter, "value") else str(player.potential_letter), 0)

        # 年龄分
        age = season.season_number + abs(player.birth_offset)
        if 18 <= age <= 23:
            score += 10
        elif 24 <= age <= 28:
            score += 5
        elif 29 <= age <= 33:
            score += 2
        elif age >= 34:
            score -= 10

        # 位置需求分
        position_need = await self._calculate_position_need(team.id)
        pos = player.position.value if hasattr(player.position, "value") else str(player.position)
        score += position_need.get(pos, 0) * 2

        # 状态分
        if player.match_form.value if hasattr(player.match_form, "value") else str(player.match_form) in ("HOT", "GOOD"):
            score += 3

        return score

    def _ai_determine_contract_years(self, age: int) -> int:
        """AI 根据年龄确定合同年限"""
        if 18 <= age <= 24:
            return random.choice([3, 4])
        elif 25 <= age <= 30:
            return random.choice([2, 3])
        elif 31 <= age <= 33:
            return random.choice([1, 2])
        else:
            return 1

    def _ai_determine_role(self, player: Player, rank: int) -> SquadRole:
        """AI 确定阵容角色"""
        if rank < 3:
            return SquadRole.KEY_PLAYER
        elif rank < 6:
            return SquadRole.FIRST_TEAM
        elif rank < 9:
            return SquadRole.ROTATION
        elif rank < 12:
            return SquadRole.BACKUP
        else:
            return SquadRole.YOUNGSTER

    async def _ai_sign_academy_before_season_end(self, team: Team, season: Season) -> Dict[str, Any]:
        """赛季末：AI 签约本队青训球员（进入新人市场前）"""
        result = {
            "signed": 0,
            "candidates": 0,
            "blocked_full": 0,
            "below_threshold": 0,
            "sign_failed": 0,
        }
        academy_players = await self._get_team_academy_players(team.id, season.id)
        if not academy_players:
            return result
        result["candidates"] = len(academy_players)

        roster_count = await self._get_team_roster_count(team.id)

        if roster_count >= self.AI_SOFT_MAX_ROSTER:
            result["blocked_full"] = len(academy_players)
            logger.info(
                f"[ai-academy] team={team.name} roster={roster_count} "
                f"soft_max={self.AI_SOFT_MAX_ROSTER} candidates={len(academy_players)} "
                f"signed=0 blocked_full={result['blocked_full']}"
            )
            return result

        # 计算 academy_score
        scored = []
        for academy_player, player in academy_players:
            score = self._calculate_academy_score(player, academy_player, roster_count)
            scored.append((academy_player, player, score))

        scored.sort(key=lambda x: -x[2])

        signed = 0
        max_sign = min(
            self.AI_ACADEMY_MAX_SIGNINGS_PER_PASS,
            self.AI_SOFT_MAX_ROSTER - roster_count,
        )

        for academy_player, player, score in scored[:max_sign]:
            threshold = 30 if roster_count < self.AI_TARGET_ROSTER else 38
            if score < threshold:
                result["below_threshold"] += 1
                continue
            try:
                recommended = await self.contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    squad_role=SquadRole.YOUNGSTER,
                )

                contract = await self.contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    years=2,
                    wage=recommended,
                    squad_role=SquadRole.YOUNGSTER,
                )

                academy_player.status = AcademyPlayerStatus.SIGNED
                academy_player.signed_at_season = season.season_number
                player.team_id = team.id
                player.joined_first_team_season = season.season_number
                signed += 1
                result["signed"] += 1
            except Exception as e:
                result["sign_failed"] += 1
                logger.warning(f"AI academy sign failed for player {player.id}: {e}")

        logger.info(
            f"[ai-academy] team={team.name} roster={roster_count} "
            f"target={self.AI_TARGET_ROSTER} soft_max={self.AI_SOFT_MAX_ROSTER} "
            f"candidates={result['candidates']} signed={result['signed']} "
            f"below_threshold={result['below_threshold']} failed={result['sign_failed']}"
        )
        return result

    def _calculate_academy_score(self, player: Player, academy_player, roster_count: int) -> float:
        """计算青训签约分"""
        score = 0.0

        # 潜力
        potential_bonus = {"S": 20, "A": 15, "B": 8, "C": 3, "D": 0}
        score += potential_bonus.get(player.potential_letter.value if hasattr(player.potential_letter, "value") else str(player.potential_letter), 0)

        # 成长速度
        speed_bonus = {GrowthSpeed.FAST: 10, GrowthSpeed.NORMAL: 5, GrowthSpeed.SLOW: 0}
        score += speed_bonus.get(academy_player.growth_speed, 0)

        # OVR
        score += float(player.ovr) * 0.3

        # roster 压力惩罚
        if roster_count >= self.AI_SOFT_MAX_ROSTER:
            score -= 30
        elif roster_count >= self.AI_TARGET_ROSTER:
            score -= 15
        elif roster_count >= 14:
            score -= 5

        return score

    async def _ai_sign_free_market(self, team: Team, season: Season) -> int:
        """AI 在自由市场签约补人"""
        roster_count = await self._get_team_roster_count(team.id)

        if roster_count >= self.AI_TARGET_ROSTER:
            return 0  # 人数足够，不主动签自由市场

        # 获取自由市场 listing
        listings_result = await self.db.execute(
            select(FreeAgentListing, Player)
            .join(Player, FreeAgentListing.player_id == Player.id)
            .where(
                and_(
                    FreeAgentListing.status == ListingStatus.ACTIVE,
                    FreeAgentListing.season_id == season.id,
                )
            )
            .order_by(desc(Player.ovr))
            .limit(10)
        )
        listings = listings_result.all()

        signed = 0
        max_needed = min(
            self.AI_TARGET_ROSTER - roster_count,
            self.AI_SOFT_MAX_ROSTER - roster_count,
            self.AI_FREE_MARKET_MAX_SIGNINGS_PER_PASS,
        )

        for listing, player in listings[:max_needed]:
            if roster_count + signed >= self.AI_TARGET_ROSTER:
                break
            try:
                recommended = await self.contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.NORMAL,
                    squad_role=SquadRole.BACKUP,
                )

                contract = await self.contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.NORMAL,
                    years=1,
                    wage=recommended,
                    squad_role=SquadRole.BACKUP,
                    source="free_market",
                )

                listing.status = ListingStatus.SIGNED
                listing.signed_team_id = team.id

                # 写入转会记录
                record = TransferRecord(
                    player_id=player.id,
                    from_team_id=None,
                    to_team_id=team.id,
                    season_id=season.id,
                    transfer_type=TransferType.FREE_MARKET_SIGNING,
                    amount=listing.signing_fee,
                    market_value_snapshot=player.market_value or Decimal("0"),
                    source_listing_id=listing.id,
                    completed_at=datetime.utcnow(),
                    is_public=True,
                )
                self.db.add(record)

                signed += 1
            except Exception as e:
                logger.warning(f"AI free market sign failed for player {player.id}: {e}")

        if signed or roster_count < self.AI_TARGET_ROSTER:
            logger.info(
                f"[ai-free-market] team={team.name} roster={roster_count} "
                f"target={self.AI_TARGET_ROSTER} soft_max={self.AI_SOFT_MAX_ROSTER} "
                f"candidates={len(listings)} signed={signed}"
            )
        return signed

    # =====================================================================
    # 位置需求计算
    # =====================================================================

    async def _calculate_position_need(self, team_id: str) -> Dict[str, int]:
        """计算球队各位置需求（人数缺口）"""
        result = await self.db.execute(
            select(Player.position, func.count(Player.id))
            .where(and_(Player.team_id == team_id, Player.status == PlayerStatus.ACTIVE))
            .group_by(Player.position)
        )
        counts = {pos.value if hasattr(pos, "value") else str(pos): cnt for pos, cnt in result.all()}

        # 目标人数
        targets = {"FW": 3, "MF": 5, "DF": 4, "GK": 2}
        need = {}
        for pos, target in targets.items():
            current = counts.get(pos, 0)
            need[pos] = max(0, target - current)

        return need



    # =====================================================================
    # 新人自由市场保护期
    # =====================================================================

    async def run_rookie_market_protection(self, season_id: str) -> Dict[str, Any]:
        """低排名 AI 球队先挑一轮保护池新人"""
        season = await self._get_current_season()
        if not season:
            return {"teams_processed": 0, "signed": 0}

        # 获取所有保护池 listing
        result = await self.db.execute(
            select(FreeAgentListing, Player, YouthAcademyPlayer)
            .join(Player, FreeAgentListing.player_id == Player.id)
            .join(YouthAcademyPlayer, YouthAcademyPlayer.player_id == Player.id)
            .where(
                and_(
                    FreeAgentListing.season_id == season_id,
                    FreeAgentListing.status == ListingStatus.ACTIVE,
                )
            )
        )
        all_listings = result.all()

        # 过滤出 rookie_protected 的
        protected = []
        for listing, player, academy_player in all_listings:
            extra = listing.extra_data or {}
            if extra.get("rookie_protected") and not extra.get("protection_processed"):
                protected.append((listing, player, academy_player))

        if not protected:
            logger.info(f"[rookie-market] no protected candidates for season {season_id}")
            return {"teams_processed": 0, "signed": 0, "candidates": 0}

        # 按联赛分组 listing
        by_league: Dict[str, List] = {}
        for listing, player, academy_player in protected:
            team = await self.db.execute(select(Team).where(Team.id == academy_player.team_id))
            team = team.scalar_one_or_none()
            league_id = team.current_league_id if team else None
            if league_id:
                by_league.setdefault(league_id, []).append((listing, player, academy_player))

        total_signed = 0
        total_teams = 0
        skipped_full = 0
        skipped_low_score = 0
        skipped_finance = 0

        for league_id, league_listings in by_league.items():
            # 获取联赛内 AI 球队，按上赛季排名倒序
            standings_result = await self.db.execute(
                select(LeagueStanding, Team)
                .join(Team, LeagueStanding.team_id == Team.id)
                .join(User, Team.user_id == User.id)
                .where(
                    and_(
                        LeagueStanding.league_id == league_id,
                        User.is_ai == True,
                    )
                )
                .order_by(desc(LeagueStanding.position))
            )
            ai_teams = [(s, t) for s, t in standings_result.all()]

            # 兜底：如果没有上赛季排名，获取当前联赛所有 AI 球队
            if not ai_teams:
                teams_result = await self.db.execute(
                    select(Team)
                    .join(User, Team.user_id == User.id)
                    .where(
                        and_(
                            Team.current_league_id == league_id,
                            User.is_ai == True,
                        )
                    )
                )
                ai_teams = [(None, t) for t in teams_result.scalars().all()]

            for standing, team in ai_teams:
                total_teams += 1
                roster_count = await self._get_team_roster_count(team.id)
                if roster_count >= self.AI_SOFT_MAX_ROSTER:
                    skipped_full += 1
                    continue

                # 获取球队余额
                from app.models.team import TeamFinance
                finance_result = await self.db.execute(
                    select(TeamFinance.balance).where(TeamFinance.team_id == team.id)
                )
                balance = finance_result.scalar_one_or_none() or Decimal("0")
                if balance < Decimal("-50000"):
                    skipped_finance += 1
                    continue

                # 计算工资压力
                finance_service = FinanceService(self.db)
                season_finance = await finance_service._get_or_create_team_season_finance(team.id, season_id)
                wage_pressure = 0.0
                if season_finance.wage_cap > 0:
                    wage_pressure = float(season_finance.wage_bill / season_finance.wage_cap)

                # 计算位置需求
                position_need = await self._calculate_position_need(team.id)

                # 评分并挑选最佳候选人
                best = None
                best_score = -999
                for listing, player, academy_player in league_listings:
                    # 检查球员是否已被签
                    if listing.status != ListingStatus.ACTIVE:
                        continue
                    if player.team_id is not None:
                        continue

                    score = self._calculate_rookie_score(
                        player, academy_player, position_need, roster_count, wage_pressure
                    )
                    if score > best_score:
                        best_score = score
                        best = (listing, player, academy_player)

                if not best:
                    continue

                listing, player, academy_player = best

                # 阈值判断
                if best_score < 25:
                    skipped_low_score += 1
                    continue
                if best_score < 35 and roster_count >= self.AI_TARGET_ROSTER:
                    skipped_low_score += 1
                    continue

                try:
                    recommended = await self.contract_service.calculate_recommended_wage(
                        player_id=player.id,
                        team_id=team.id,
                        contract_type=ContractType.ROOKIE,
                        squad_role=SquadRole.YOUNGSTER,
                    )

                    await self.contract_service.sign_contract(
                        player_id=player.id,
                        team_id=team.id,
                        contract_type=ContractType.ROOKIE,
                        years=2,
                        wage=recommended.quantize(Decimal("1")),
                        squad_role=SquadRole.YOUNGSTER,
                        source="rookie_market",
                    )

                    listing.status = ListingStatus.SIGNED
                    listing.signed_team_id = team.id

                    # 写入转会记录（青训签约也视为自由市场签约）
                    record = TransferRecord(
                        player_id=player.id,
                        from_team_id=None,
                        to_team_id=team.id,
                        season_id=season.id,
                        transfer_type=TransferType.FREE_MARKET_SIGNING,
                        amount=listing.signing_fee,
                        market_value_snapshot=player.market_value or Decimal("0"),
                        source_listing_id=listing.id,
                        completed_at=datetime.utcnow(),
                        is_public=True,
                    )
                    self.db.add(record)

                    extra = dict(listing.extra_data or {})
                    extra["protection_processed"] = True
                    extra["rookie_protected"] = False
                    listing.extra_data = extra

                    # 从 pool 移除，避免被其他球队重复签
                    league_listings.remove(best)

                    total_signed += 1
                except Exception as e:
                    logger.warning(f"AI rookie sign failed: {e}")
                    skipped_finance += 1

        logger.info(
            f"[rookie-market] protected candidates={len(protected)} "
            f"target={self.AI_TARGET_ROSTER} soft_max={self.AI_SOFT_MAX_ROSTER} "
            f"signed={total_signed} full={skipped_full} low_score={skipped_low_score} "
            f"finance={skipped_finance} released={len(protected) - total_signed}"
        )
        return {
            "teams_processed": total_teams,
            "rookie_candidates": len(protected),
            "signed": total_signed,
            "skipped_full": skipped_full,
            "skipped_low_score": skipped_low_score,
            "skipped_finance": skipped_finance,
        }

    def _calculate_rookie_score(
        self,
        player: Player,
        academy_player: YouthAcademyPlayer,
        position_need: Dict[str, int],
        roster_count: int,
        wage_pressure: float,
    ) -> float:
        """计算新人评分"""
        score = 0.0

        # 潜力分
        potential_bonus = {"S": 20, "A": 15, "B": 8, "C": 3, "D": 0}
        score += potential_bonus.get(
            player.potential_letter.value if hasattr(player.potential_letter, "value") else str(player.potential_letter),
            0
        )

        # 成长速度
        speed_bonus = {GrowthSpeed.FAST: 10, GrowthSpeed.NORMAL: 5, GrowthSpeed.SLOW: 0}
        score += speed_bonus.get(academy_player.growth_speed, 0)

        # 年龄分（Rookie 仅 17-18 岁，17 岁成长空间略大）
        age = abs(player.birth_offset)
        if age == 17:
            score += 3
        elif age == 18:
            score += 1

        # OVR 分
        score += float(player.ovr) * 0.3

        # 位置需求
        pos = player.position.value if hasattr(player.position, "value") else str(player.position)
        score += position_need.get(pos, 0) * 3

        # 阵容缺口
        if roster_count < 13:
            score += 10
        elif roster_count < self.AI_TARGET_ROSTER:
            score += 5
        elif roster_count >= self.AI_SOFT_MAX_ROSTER:
            score -= 12

        # 工资压力惩罚
        if wage_pressure > 1.0:
            score -= 15
        elif wage_pressure > 0.9:
            score -= 5

        return score

# =====================================================================
# 独立函数：青训刷新后决策（避免循环导入）
# =====================================================================

async def _ai_academy_decisions_for_team(db: AsyncSession, team: Team, season: Season) -> Dict[str, Any]:
    """单个 AI 球队的青训决策"""
    result = {
        "signed": 0,
        "declined": 0,
        "candidates": 0,
        "blocked_full": 0,
        "below_threshold": 0,
        "sign_failed": 0,
    }
    service = AITeamManagementService(db)
    academy_players = await service._get_team_academy_players(team.id, season.id)
    if not academy_players:
        return result
    result["candidates"] = len(academy_players)

    roster_count = await service._get_team_roster_count(team.id)

    if roster_count >= service.AI_SOFT_MAX_ROSTER:
        result["blocked_full"] = len(academy_players)
        logger.info(
            f"[ai-academy-midseason] team={team.name} roster={roster_count} "
            f"soft_max={service.AI_SOFT_MAX_ROSTER} candidates={len(academy_players)} "
            f"signed=0 blocked_full={result['blocked_full']}"
        )
        return result

    scored = []
    for academy_player, player in academy_players:
        score = service._calculate_academy_score(player, academy_player, roster_count)
        scored.append((academy_player, player, score))

    scored.sort(key=lambda x: -x[2])

    signed = 0
    declined = 0
    max_sign = min(
        service.AI_ACADEMY_MAX_SIGNINGS_PER_PASS,
        service.AI_SOFT_MAX_ROSTER - roster_count,
    )

    for academy_player, player, score in scored:
        if signed >= max_sign:
            break
        threshold = 30 if roster_count < service.AI_TARGET_ROSTER else 38
        if score >= threshold:
            try:
                contract_service = ContractService(db)
                recommended = await contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    squad_role=SquadRole.YOUNGSTER,
                )

                await contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    years=2,
                    wage=recommended,
                    squad_role=SquadRole.YOUNGSTER,
                )

                academy_player.status = AcademyPlayerStatus.SIGNED
                academy_player.signed_at_season = season.season_number
                player.team_id = team.id
                player.joined_first_team_season = season.season_number
                signed += 1
                result["signed"] += 1
            except Exception as e:
                result["sign_failed"] += 1
                logger.warning(f"AI midseason academy sign failed: {e}")
        else:
            # 低分球员本次不签，仍留在青训营，赛季末统一进入新人自由市场。
            declined += 1
            result["declined"] += 1
            result["below_threshold"] += 1

    logger.info(
        f"[ai-academy-midseason] team={team.name} roster={roster_count} "
        f"target={service.AI_TARGET_ROSTER} soft_max={service.AI_SOFT_MAX_ROSTER} "
        f"candidates={result['candidates']} signed={result['signed']} "
        f"declined={result['declined']} below_threshold={result['below_threshold']} "
        f"failed={result['sign_failed']}"
    )
    return result
