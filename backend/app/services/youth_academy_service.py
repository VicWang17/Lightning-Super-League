"""
Youth Academy Service - 青训营服务
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 第 8 节实现。
"""
import random
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
    YouthAcademySnapshot,
    AcademyPlayerStatus,
    GrowthSpeed,
    Team,
    TeamSeasonFinance,
    Season,
    SeasonStatus,
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus,
)
from app.models.wage_config import WageConfig, WageConfigType
from app.models.league import League
from app.services.contract_service import ContractService
from app.services.player_generator import PlayerGenerator
from app.services.player_number_service import assign_squad_number
from app.services.notification_service import NotificationService
from app.services.training_growth_service import TrainingGrowthService
from app.core.logging import get_logger

logger = get_logger("app.youth_academy")

_GROWTH_SCORE_MAX = Decimal("999.99")


def _quantize_growth_score(value: Decimal | float) -> Decimal:
    value = Decimal(str(value)).quantize(Decimal("0.01"))
    return min(value, _GROWTH_SCORE_MAX)


class YouthAcademyService:
    """青训营服务"""

    YOUTH_CAPACITY = 8

    def __init__(self, db: AsyncSession):
        self.db = db
        self.generator = PlayerGenerator()

    # =====================================================================
    # 青训刷新
    # =====================================================================

    async def refresh_academy_players(self, season_id: str, day: int) -> Dict[str, Any]:
        """青训刷新：为每支球队补满青训营空位

        赛季第 4、8 天自动触发。
        """
        season = await self._get_season(season_id)
        if not season:
            logger.error(f"Season {season_id} not found for youth refresh")
            return {"refreshed": 0, "errors": ["Season not found"]}

        teams_result = await self.db.execute(select(Team))
        teams = teams_result.scalars().all()

        total_created = 0
        errors = []
        team_new_counts: Dict[str, int] = {}

        for team in teams:
            try:
                created = await self._refresh_team_academy(team, season, day)
                total_created += created
                if created > 0:
                    team_new_counts[team.id] = created
            except Exception as e:
                logger.exception(f"Failed to refresh academy for team {team.id}")
                errors.append(f"Team {team.id}: {e}")

        # 发送青训刷新通知
        notify = NotificationService(self.db)
        for team_id, new_count in team_new_counts.items():
            await notify.send_youth_refresh(
                team_id=team_id,
                season_id=season_id,
                day=day,
                new_count=new_count,
            )

        await self.db.commit()
        logger.info(f"Youth refresh completed: {total_created} players created for season {season_id} day {day}")
        return {"refreshed": total_created, "errors": errors}

    async def _refresh_team_academy(self, team: Team, season: Season, day: int) -> int:
        """为单个球队刷新青训营"""
        # 计算当前在营人数
        count_result = await self.db.execute(
            select(func.count(YouthAcademyPlayer.id))
            .where(
                and_(
                    YouthAcademyPlayer.team_id == team.id,
                    YouthAcademyPlayer.season_id == season.id,
                    YouthAcademyPlayer.status == AcademyPlayerStatus.IN_ACADEMY,
                )
            )
        )
        in_academy_count = count_result.scalar() or 0

        empty_slots = self.YOUTH_CAPACITY - in_academy_count
        if empty_slots <= 0:
            return 0

        # 获取投入等级和联赛级别
        investment_level, league_level = await self._get_team_investment_level(team, season.id)

        created = 0
        for _ in range(empty_slots):
            player = self.generator.generate_youth_player(
                team=team,
                season_number=season.season_number,
                investment_level=investment_level,
                league_level=league_level,
            )
            self.db.add(player)
            await self.db.flush()  # 获取 player.id

            # 创建青训记录
            academy_player = YouthAcademyPlayer(
                player_id=player.id,
                team_id=team.id,
                season_id=season.id,
                joined_season_number=season.season_number,
                joined_day=day,
                status=AcademyPlayerStatus.IN_ACADEMY,
                growth_speed=self._determine_growth_speed(abs(player.birth_offset)),
                growth_score=_quantize_growth_score(Decimal("1.00")),
                last_trained_day=None,
            )
            self.db.add(academy_player)
            await self.db.flush()

            # 创建初始快照
            snapshot = YouthAcademySnapshot(
                academy_player_id=academy_player.id,
                season_id=season.id,
                season_day=day,
                ovr=player.ovr,
                extra_data={"event": "refresh"},
            )
            self.db.add(snapshot)
            created += 1

        return created

    async def _get_team_investment_level(self, team: Team, season_id: str) -> tuple:
        """获取球队青训投入等级和联赛级别"""
        # 默认中等投入
        investment_level = "medium"
        league_level = 3

        # 尝试从 TeamSeasonFinance 获取 youth_budget
        finance_result = await self.db.execute(
            select(TeamSeasonFinance).where(
                and_(
                    TeamSeasonFinance.team_id == team.id,
                    TeamSeasonFinance.season_id == season_id,
                )
            )
        )
        finance = finance_result.scalar_one_or_none()
        if finance and finance.locked_budget_total > 0:
            youth_pct = float(finance.youth_budget / finance.locked_budget_total * 100)
            if youth_pct <= 10:
                investment_level = "low"
            elif youth_pct <= 17:
                investment_level = "medium"
            else:
                investment_level = "high"

        # 联赛级别
        if team.current_league_id:
            league_result = await self.db.execute(
                select(League.level).where(League.id == team.current_league_id)
            )
            level = league_result.scalar_one_or_none()
            if level:
                league_level = level

        return investment_level, league_level

    def _determine_growth_speed(self, age: int) -> GrowthSpeed:
        """根据年龄确定成长速度"""
        if age <= 15:
            return _weighted_choice([(GrowthSpeed.FAST, 0.60), (GrowthSpeed.NORMAL, 0.35), (GrowthSpeed.SLOW, 0.05)])
        elif age == 16:
            return _weighted_choice([(GrowthSpeed.FAST, 0.35), (GrowthSpeed.NORMAL, 0.50), (GrowthSpeed.SLOW, 0.15)])
        elif age == 17:
            return _weighted_choice([(GrowthSpeed.FAST, 0.15), (GrowthSpeed.NORMAL, 0.60), (GrowthSpeed.SLOW, 0.25)])
        else:
            return _weighted_choice([(GrowthSpeed.FAST, 0.05), (GrowthSpeed.NORMAL, 0.50), (GrowthSpeed.SLOW, 0.45)])

    # =====================================================================
    # 青训训练
    # =====================================================================

    async def train_academy_players(self, season_id: str, day: int) -> Dict[str, Any]:
        """青训训练：为所有在营球员执行一次训练

        每 youth_training_interval_days 天自动触发。
        """
        season = await self._get_season(season_id)
        if not season:
            return {"trained": 0, "errors": ["Season not found"]}

        result = await self.db.execute(
            select(YouthAcademyPlayer, Player)
            .join(Player, YouthAcademyPlayer.player_id == Player.id)
            .where(
                and_(
                    YouthAcademyPlayer.season_id == season_id,
                    YouthAcademyPlayer.status == AcademyPlayerStatus.IN_ACADEMY,
                )
            )
        )
        rows = result.all()

        trained_count = 0
        for academy_player, player in rows:
            try:
                await self._train_single_player(academy_player, player, season, day)
                trained_count += 1
            except Exception as e:
                logger.exception(f"Failed to train player {player.id}")

        await self.db.commit()
        logger.info(f"Youth training completed: {trained_count} players trained for season {season_id} day {day}")
        return {"trained": trained_count, "errors": []}

    async def _train_single_player(
        self,
        academy_player: YouthAcademyPlayer,
        player: Player,
        season: Season,
        day: int,
    ) -> None:
        """训练单个青训球员"""
        old_ovr = player.ovr
        age = season.season_number + abs(player.birth_offset)

        # 成长系数
        speed_factors = {GrowthSpeed.FAST: 1.30, GrowthSpeed.NORMAL: 1.00, GrowthSpeed.SLOW: 0.70}
        age_factors = {15: 1.20, 16: 1.10, 17: 1.00, 18: 0.90}

        speed_factor = speed_factors.get(academy_player.growth_speed, 1.00)
        age_factor = age_factors.get(age, 0.80)
        random_factor = random.uniform(0.85, 1.15)

        base_growth = random.uniform(0.12, 0.28)
        growth_budget = base_growth * speed_factor * age_factor * random_factor

        # 应用属性增长
        attrs_gained = await self._apply_growth(player, growth_budget)

        # 检查 OVR 整数突破
        if player.ovr > old_ovr:
            notify = NotificationService(self.db)
            await notify.send_youth_breakthrough(
                team_id=academy_player.team_id,
                season_id=season.id,
                player_name=player.name,
                player_id=player.id,
                old_ovr=old_ovr,
                new_ovr=player.ovr,
            )

        # 更新快照
        snapshot = YouthAcademySnapshot(
            academy_player_id=academy_player.id,
            season_id=season.id,
            season_day=day,
            ovr=player.ovr,
            extra_data={"growth_budget": round(growth_budget, 2), "attrs_gained": attrs_gained},
        )
        self.db.add(snapshot)

        academy_player.last_trained_day = day
        academy_player.growth_score = _quantize_growth_score(
            Decimal(str(academy_player.growth_score)) + Decimal(str(growth_budget))
        )

    async def _apply_growth(self, player: Player, growth_budget: float) -> Dict[str, int]:
        """应用属性增长，优先提升位置权重高的属性。

        青训成长也必须遵守属性上限和高属性指数成本，避免 18/19 轻易冲 20。
        """
        # 位置权重定义
        position_weights = {
            PlayerPosition.FW: ["sho", "hea", "fin", "spd", "acc", "dri", "str_", "bal", "pk"],
            PlayerPosition.MF: ["pas", "vis", "dri", "con", "sta", "spd", "acc", "cro", "fk"],
            PlayerPosition.DF: ["defe", "tkl", "hea", "str_", "bal", "pos", "sta", "spd", "com"],
            PlayerPosition.GK: ["sav", "ref", "pos", "com", "rus", "dec", "sta", "bal", "str_"],
        }

        primary_attrs = position_weights.get(player.position, [])
        all_attrs = ["sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
                     "defe", "tkl", "vis", "cro", "con", "fin", "com", "sav", "ref",
                     "pos", "rus", "dec", "fk", "pk"]

        attrs_gained = {}
        remaining_budget = growth_budget
        progress = dict(player.attribute_progress or {})

        def try_grow(attr: str, chance: float, budget_share: float) -> None:
            nonlocal remaining_budget
            if remaining_budget <= 0 or random.random() >= chance:
                return

            current_val = float(getattr(player, attr))
            caps = player.attribute_caps or {}
            cap = float(caps.get(attr, TrainingGrowthService._derive_cap_from_potential(player, attr)))
            cap = min(cap, 20.0)
            if current_val >= 20 or int(cap) <= int(current_val):
                return

            high_attr_factor = TrainingGrowthService.calculate_high_attribute_factor(
                current_val + float(progress.get(attr, 0.0))
            )
            gain = min(remaining_budget, budget_share) * high_attr_factor
            if gain <= 0:
                return

            before = int(getattr(player, attr))
            breakthroughs = TrainingGrowthService.apply_attribute_progress(player, {attr: gain})
            after = int(getattr(player, attr))
            progress.update(player.attribute_progress or {})
            if after > before:
                attrs_gained[attr] = attrs_gained.get(attr, 0) + (after - before)
            remaining_budget -= min(remaining_budget, budget_share)

        # 优先提升主要属性
        for attr in primary_attrs:
            if remaining_budget <= 0:
                break
            try_grow(attr, chance=0.62, budget_share=0.18)

        # 少量随机提升其他属性
        if remaining_budget > 0.12:
            secondary = [a for a in all_attrs if a not in primary_attrs]
            random.shuffle(secondary)
            for attr in secondary[:3]:
                if remaining_budget <= 0:
                    break
                try_grow(attr, chance=0.20, budget_share=0.08)

        return attrs_gained

    # =====================================================================
    # 青训签约
    # =====================================================================

    async def list_academy(self, team_id: str, season_id: Optional[str] = None) -> Dict[str, Any]:
        """获取球队青训营列表"""
        # 如果未指定赛季，使用当前赛季
        if not season_id:
            season = await self._get_current_season()
            season_id = season.id if season else None

        if not season_id:
            return {"team_id": team_id, "players": [], "capacity": self.YOUTH_CAPACITY, "count": 0}

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
        rows = result.all()

        players = []
        for academy_player, player in rows:
            players.append({
                "academy_player_id": academy_player.id,
                "player_id": player.id,
                "name": player.name,
                "race": player.race.value,
                "avatar_url": player.avatar_url,
                "position": player.position.value,
                "age": abs(player.birth_offset),
                "ovr": player.ovr,
                "potential_letter": player.potential_letter.value,
                "growth_speed": academy_player.growth_speed.value,
                "joined_day": academy_player.joined_day,
                "last_trained_day": academy_player.last_trained_day,
            })

        return {
            "team_id": team_id,
            "season_id": season_id,
            "players": players,
            "capacity": self.YOUTH_CAPACITY,
            "count": len(players),
        }

    async def preview_signing(
        self,
        academy_player_id: str,
        team_id: str,
        years: int,
        wage: Decimal,
        squad_role: SquadRole = SquadRole.YOUNGSTER,
    ) -> Dict[str, Any]:
        """青训签约预览"""
        academy_player = await self._get_academy_player(academy_player_id)
        if not academy_player:
            raise ValueError("青训球员不存在")
        if academy_player.status != AcademyPlayerStatus.IN_ACADEMY:
            raise ValueError("该球员不在青训营中")
        if not (1 <= years <= 2):
            raise ValueError("青训合同年限必须在 1-2 个赛季之间")

        contract_service = ContractService(self.db)
        preview = await contract_service.preview_contract_offer(
            player_id=academy_player.player_id,
            team_id=team_id,
            contract_type=ContractType.ROOKIE,
            years=years,
            wage=wage,
            squad_role=squad_role,
        )

        preview_dict = preview.to_dict()
        # 青训签约无签字费
        preview_dict["signing_fee"] = 0
        preview_dict["balance_after_fee"] = float(
            (await self._get_team_balance(team_id)) - Decimal("0")
        )
        preview_dict["can_pay_signing_fee"] = True

        return preview_dict

    async def sign_player(
        self,
        academy_player_id: str,
        team_id: str,
        years: int,
        wage: Decimal,
        squad_role: SquadRole = SquadRole.YOUNGSTER,
    ) -> Dict[str, Any]:
        """签约青训球员入一线队"""
        academy_player = await self._get_academy_player(academy_player_id)
        if not academy_player:
            raise ValueError("青训球员不存在")
        if academy_player.status != AcademyPlayerStatus.IN_ACADEMY:
            raise ValueError("该球员不在青训营中或已被处理")
        if not (1 <= years <= 2):
            raise ValueError("青训合同年限必须在 1-2 个赛季之间")

        # 检查 roster 上限
        roster_count_result = await self.db.execute(
            select(func.count(Player.id)).where(Player.team_id == team_id)
        )
        roster_count = roster_count_result.scalar() or 0
        if roster_count >= 18:
            raise ValueError("一线队已满 15 人，无法签约")

        contract_service = ContractService(self.db)
        contract = await contract_service.sign_contract(
            player_id=academy_player.player_id,
            team_id=team_id,
            contract_type=ContractType.ROOKIE,
            years=years,
            wage=wage,
            squad_role=squad_role,
        )

        # 更新青训记录
        academy_player.status = AcademyPlayerStatus.SIGNED
        academy_player.signed_at_season = (await self._get_current_season()).season_number

        # 更新球员归属
        player = await self._get_player(academy_player.player_id)
        if player:
            player.team_id = team_id
            player.joined_first_team_season = (await self._get_current_season()).season_number
            # 分配队内号码
            await assign_squad_number(self.db, player, team_id)

        # 发送青训签约通知
        current_season = await self._get_current_season()
        season_id_for_notify = current_season.id if current_season else None
        notify = NotificationService(self.db)
        await notify.send_youth_signed(
            team_id=team_id,
            season_id=season_id_for_notify,
            player_name=player.name if player else "未知球员",
            player_id=academy_player.player_id,
            years=years,
            wage=float(wage),
        )

        await self.db.commit()

        return {
            "contract_id": contract.id,
            "player_id": academy_player.player_id,
            "team_id": team_id,
            "signing_fee": 0,
        }

    async def release_to_market(self, academy_player_id: str) -> Dict[str, Any]:
        """放弃青训球员，使其进入自由市场"""
        academy_player = await self._get_academy_player(academy_player_id)
        if not academy_player:
            raise ValueError("青训球员不存在")
        if academy_player.status != AcademyPlayerStatus.IN_ACADEMY:
            raise ValueError("该球员不在青训营中")

        academy_player.status = AcademyPlayerStatus.FREE_MARKET
        await self.db.commit()

        return {
            "academy_player_id": academy_player_id,
            "status": AcademyPlayerStatus.FREE_MARKET.value,
        }

    async def release_unsigned_to_rookie_market(self, season_id: str) -> Dict[str, Any]:
        """赛季末：将未签约青训球员释放到新人自由市场保护池

        由 RosterLifecycleService.close_season 调用。
        创建 FreeAgentListing，标记 rookie_protected=true。
        """
        from app.services.player_generator import estimate_initial_wage

        result = await self.db.execute(
            select(YouthAcademyPlayer, Player)
            .join(Player, YouthAcademyPlayer.player_id == Player.id)
            .where(
                and_(
                    YouthAcademyPlayer.season_id == season_id,
                    YouthAcademyPlayer.status.in_(
                        [AcademyPlayerStatus.IN_ACADEMY, AcademyPlayerStatus.FREE_MARKET]
                    ),
                )
            )
        )
        rows = result.all()

        season = await self.db.execute(select(Season).where(Season.id == season_id))
        season = season.scalar_one_or_none()
        season_number = season.season_number if season else 1

        count = 0
        for academy_player, player in rows:
            existing_listing = await self.db.execute(
                select(FreeAgentListing.id).where(
                    and_(
                        FreeAgentListing.player_id == player.id,
                        FreeAgentListing.season_id == season_id,
                    )
                ).limit(1)
            )
            if existing_listing.scalar_one_or_none():
                academy_player.status = AcademyPlayerStatus.FREE_MARKET
                continue

            # 创建自由市场 listing
            signing_fee = Decimal(3000.00)  # 青训流出签字费较低
            recommended_wage = (
                estimate_initial_wage(
                    player.ovr, player.potential_max, abs(player.birth_offset)
                ) * Decimal("0.55")
            ).quantize(Decimal("100"))

            listing = FreeAgentListing(
                player_id=player.id,
                season_id=season_id,
                origin=FreeAgentOrigin.ACADEMY_RELEASED,
                signing_fee=signing_fee,
                recommended_wage=recommended_wage,
                status=ListingStatus.ACTIVE,
                listed_at_day=season_number,
                extra_data={
                    "rookie_protected": True,
                    "source_team_id": academy_player.team_id,
                    "source_academy_player_id": academy_player.id,
                    "protection_season_number": season_number,
                    "protection_processed": False,
                },
            )
            self.db.add(listing)

            # 更新青训状态
            academy_player.status = AcademyPlayerStatus.FREE_MARKET
            count += 1

        await self.db.commit()
        logger.info(f"[youth] released {count} unsigned academy players to rookie market for season {season_id}")
        return {"released": count}

    # =====================================================================
    # 成长曲线
    # =====================================================================

    async def get_growth_curve(self, academy_player_id: str) -> List[Dict[str, Any]]:
        """获取青训球员成长曲线"""
        result = await self.db.execute(
            select(YouthAcademySnapshot)
            .where(YouthAcademySnapshot.academy_player_id == academy_player_id)
            .order_by(asc(YouthAcademySnapshot.season_day))
        )
        snapshots = result.scalars().all()

        return [
            {
                "season_day": s.season_day,
                "ovr": s.ovr,
                "extra_data": s.extra_data,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ]

    # =====================================================================
    # 内部辅助
    # =====================================================================

    async def _get_season(self, season_id: str) -> Optional[Season]:
        result = await self.db.execute(select(Season).where(Season.id == season_id))
        return result.scalar_one_or_none()

    async def _get_current_season(self) -> Optional[Season]:
        result = await self.db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number)).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_academy_player(self, academy_player_id: str) -> Optional[YouthAcademyPlayer]:
        result = await self.db.execute(
            select(YouthAcademyPlayer).where(YouthAcademyPlayer.id == academy_player_id)
        )
        return result.scalar_one_or_none()

    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()

    async def _get_team_balance(self, team_id: str) -> Decimal:
        from app.models.team import TeamFinance
        result = await self.db.execute(
            select(TeamFinance.balance).where(TeamFinance.team_id == team_id)
        )
        balance = result.scalar_one_or_none()
        return balance or Decimal("0")


def _weighted_choice(choices):
    """按权重随机选择"""
    total = sum(w for _, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for item, w in choices:
        upto += w
        if upto >= r:
            return item
    return choices[-1][0]
