"""
Youth Academy Service - 青训营服务
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 第 8 节实现。
"""
import random
from decimal import Decimal, ROUND_HALF_UP
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
)
from app.models.wage_config import WageConfig, WageConfigType
from app.models.league import League
from app.services.contract_service import ContractService
from app.services.player_generator import PlayerGenerator
from app.core.logging import get_logger

logger = get_logger("app.youth_academy")


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
        
        for team in teams:
            try:
                created = await self._refresh_team_academy(team, season, day)
                total_created += created
            except Exception as e:
                logger.exception(f"Failed to refresh academy for team {team.id}")
                errors.append(f"Team {team.id}: {e}")
        
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
                growth_score=Decimal("1.00"),
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
                growth_delta={"event": "refresh"},
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
        age = season.season_number + abs(player.birth_offset)
        
        # 成长系数
        speed_factors = {GrowthSpeed.FAST: 1.30, GrowthSpeed.NORMAL: 1.00, GrowthSpeed.SLOW: 0.70}
        age_factors = {15: 1.20, 16: 1.10, 17: 1.00, 18: 0.90}
        
        speed_factor = speed_factors.get(academy_player.growth_speed, 1.00)
        age_factor = age_factors.get(age, 0.80)
        random_factor = random.uniform(0.85, 1.15)
        
        base_growth = random.uniform(0.20, 0.45)
        growth_budget = base_growth * speed_factor * age_factor * random_factor
        
        # 应用属性增长
        attrs_gained = await self._apply_growth(player, growth_budget)
        
        # 更新快照
        snapshot = YouthAcademySnapshot(
            academy_player_id=academy_player.id,
            season_id=season.id,
            season_day=day,
            ovr=player.ovr,
            growth_delta={"growth_budget": round(growth_budget, 2), "attrs_gained": attrs_gained},
        )
        self.db.add(snapshot)
        
        academy_player.last_trained_day = day
        # 避免 float 精度污染 Decimal，先 round 再转换，最后 quantize 到 2 位小数
        growth_budget_decimal = Decimal(str(round(growth_budget, 4)))
        new_score = academy_player.growth_score + growth_budget_decimal
        new_score = new_score.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        academy_player.growth_score = min(new_score, Decimal("999.99"))
    
    async def _apply_growth(self, player: Player, growth_budget: float) -> Dict[str, int]:
        """应用属性增长，优先提升位置权重高的属性"""
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
        
        # 优先提升主要属性（无潜力上限限制，允许偏科）
        for attr in primary_attrs:
            if remaining_budget <= 0:
                break
            current_val = getattr(player, attr)
            
            gain = min(1, remaining_budget)
            if random.random() < 0.7:  # 70% 概率提升
                new_val = min(20, current_val + gain)  # 仅受硬顶20限制
                actual_gain = new_val - current_val
                if actual_gain > 0:
                    setattr(player, attr, int(new_val))
                    attrs_gained[attr] = actual_gain
                    remaining_budget -= actual_gain
        
        # 少量随机提升其他属性
        if remaining_budget > 0.3:
            secondary = [a for a in all_attrs if a not in primary_attrs]
            random.shuffle(secondary)
            for attr in secondary[:3]:
                if remaining_budget <= 0:
                    break
                current_val = getattr(player, attr)
                if random.random() < 0.3:  # 30% 概率
                    new_val = min(20, current_val + 1)  # 仅受硬顶20限制
                    actual_gain = new_val - current_val
                    if actual_gain > 0:
                        setattr(player, attr, int(new_val))
                        attrs_gained[attr] = attrs_gained.get(attr, 0) + actual_gain
                        remaining_budget -= actual_gain
        
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
        
        # 检查 roster 上限
        roster_count_result = await self.db.execute(
            select(func.count(Player.id)).where(Player.team_id == team_id)
        )
        roster_count = roster_count_result.scalar() or 0
        if roster_count >= 15:
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
        
        await self.db.commit()
        
        return {
            "contract_id": contract.id,
            "player_id": academy_player.player_id,
            "team_id": team_id,
            "signing_fee": 0,
        }
    
    async def release_to_draft(self, academy_player_id: str) -> Dict[str, Any]:
        """放弃青训球员，使其进入选秀候选"""
        academy_player = await self._get_academy_player(academy_player_id)
        if not academy_player:
            raise ValueError("青训球员不存在")
        if academy_player.status != AcademyPlayerStatus.IN_ACADEMY:
            raise ValueError("该球员不在青训营中")
        
        academy_player.status = AcademyPlayerStatus.RELEASED_TO_DRAFT
        await self.db.commit()
        
        return {
            "academy_player_id": academy_player_id,
            "status": AcademyPlayerStatus.RELEASED_TO_DRAFT.value,
        }
    
    async def release_unsigned_to_draft(self, season_id: str) -> Dict[str, Any]:
        """赛季末：将所有未签约青训球员标记为进入选秀池
        
        由 RosterLifecycleService.close_season 调用。
        """
        result = await self.db.execute(
            select(YouthAcademyPlayer)
            .where(
                and_(
                    YouthAcademyPlayer.season_id == season_id,
                    YouthAcademyPlayer.status == AcademyPlayerStatus.IN_ACADEMY,
                )
            )
        )
        players = result.scalars().all()
        
        count = 0
        for academy_player in players:
            academy_player.status = AcademyPlayerStatus.RELEASED_TO_DRAFT
            count += 1
        
        await self.db.commit()
        logger.info(f"Released {count} unsigned academy players to draft for season {season_id}")
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
                "growth_delta": s.growth_delta,
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
