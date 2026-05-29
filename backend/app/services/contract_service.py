"""
Contract service - 合同服务
按设计文档 CONTRACT-PLAYER-STATE-SYSTEM-DESIGN.md 实现。
职责：计算建议工资、合同 preview/sign/renew/release、同步球员字段、刷新状态。
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.player import (
    Player,
    ContractType,
    SquadRole,
    PlayerPersonality,
    PlayerStatus,
)
from app.models.player_contract import PlayerContract, ContractStatus
from app.models.wage_config import WageConfig, WageConfigType
from app.models.team import Team
from app.models.season import Season
from app.services.player_state_service import PlayerStateService
from app.services.finance_service import FinanceService
from app.core.logging import get_logger

logger = get_logger("app.contract")


# 工资比例 -> 满意度映射 (设计文档 5.4)
_WAGE_SATISFACTION_MAP = [
    (Decimal("0.70"), -3),
    (Decimal("0.85"), -2),
    (Decimal("0.95"), -1),
    (Decimal("1.15"), 0),
    (Decimal("1.30"), 1),
    (Decimal("999.99"), 2),  # >= 1.30
]

# 合同到期压力修正 (设计文档 5.6)
# 注意：这里需要当前赛季号，由调用方传入或从数据库查询


class ContractService:
    """合同服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.state_service = PlayerStateService(db)
    
    # =====================================================================
    # 建议工资计算
    # =====================================================================
    
    async def calculate_recommended_wage(
        self,
        player_id: str,
        team_id: str,
        contract_type: ContractType,
        squad_role: SquadRole,
    ) -> Decimal:
        """计算建议工资 (设计文档 5.1)"""
        player = await self._get_player(player_id)
        team = await self._get_team(team_id)
        if not player or not team:
            raise ValueError("Player or team not found")
        
        # 1. 基础工资 (按 OVR 插值)
        base_wage = await self._get_base_wage_by_ovr(player.ovr)
        
        # 2. 联赛系数
        league_level = await self._get_team_league_level(team_id)
        league_factor = await self._get_wage_config(WageConfigType.LEAGUE_FACTOR, str(league_level))
        
        # 3. 年龄系数
        age = abs(player.birth_offset)  # 简化：当前赛季约等于 0 赛季起始
        age_key = self._age_range_key(age)
        age_factor = await self._get_wage_config(WageConfigType.AGE_FACTOR, age_key)
        
        # 4. 合同类型系数
        contract_factor = await self._get_wage_config(
            WageConfigType.CONTRACT_TYPE_FACTOR,
            contract_type.value,
        )
        
        # 5. 阵容角色系数 - 暂不实现（游戏目前没有角色判断机制）
        # role_factor = await self._get_wage_config(WageConfigType.ROLE_FACTOR, squad_role.value)
        role_factor = Decimal("1.0")
        
        recommended = (
            base_wage * league_factor * age_factor * contract_factor * role_factor
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        return recommended
    
    async def preview_contract_offer(
        self,
        player_id: str,
        team_id: str,
        contract_type: ContractType,
        years: int,
        wage: Decimal,
        squad_role: SquadRole,
    ) -> "ContractPreview":
        """预览合同 offer (设计文档 7.1)"""
        recommended = await self.calculate_recommended_wage(
            player_id, team_id, contract_type, squad_role
        )
        
        if recommended <= 0:
            recommended = Decimal("1000.00")
        
        wage_ratio = (wage / recommended).quantize(Decimal("0.01"))
        satisfaction = self._wage_ratio_to_satisfaction(wage_ratio)
        
        # 工资帽压力检查
        finance_service = FinanceService(self.db)
        team_season_finance = await finance_service._get_or_create_team_season_finance(
            team_id, await self._get_current_season_id(team_id)
        )
        wage_cap = team_season_finance.wage_cap if team_season_finance.wage_cap > 0 else Decimal("1")
        
        # 计算签约后的工资支出
        current_wage_bill = await finance_service._calculate_team_wage_bill(team_id)
        player = await self._get_player(player_id)
        old_wage = player.wage if player else Decimal("0")
        new_wage_bill = current_wage_bill - old_wage + wage
        wage_pressure_pct = int((new_wage_bill / wage_cap) * 100) if wage_cap > 0 else 0
        
        # 可见反应
        visible_reaction = self._satisfaction_to_reaction(satisfaction)
        
        # 能否提交
        can_submit = wage_pressure_pct <= 120  # 允许轻微超支
        warnings = []
        if wage_pressure_pct > 100:
            warnings.append("工资帽超限，可能导致财务惩罚")
        if satisfaction < -2:
            warnings.append("球员对工资非常不满")
        elif satisfaction < 0:
            warnings.append("球员对工资略有不满")
        
        return ContractPreview(
            recommended_wage=recommended,
            offered_wage=wage,
            wage_ratio=wage_ratio,
            visible_reaction=visible_reaction,
            hidden_wage_satisfaction=satisfaction,
            wage_cap_after_pct=wage_pressure_pct,
            can_submit=can_submit,
            warnings=warnings,
        )
    
    async def sign_contract(
        self,
        player_id: str,
        team_id: str,
        contract_type: ContractType,
        years: int,
        wage: Decimal,
        squad_role: SquadRole,
        release_clause: Optional[Decimal] = None,
    ) -> PlayerContract:
        """签约新合同"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        # 计算建议工资和满意度
        recommended = await self.calculate_recommended_wage(
            player_id, team_id, contract_type, squad_role
        )
        wage_ratio = (wage / recommended).quantize(Decimal("0.01")) if recommended > 0 else Decimal("1.0")
        satisfaction = self._wage_ratio_to_satisfaction(wage_ratio)
        
        # 当前赛季号
        current_season = await self._get_current_season_number(team_id)
        end_season = current_season + years if years > 0 else None
        season_id = await self._get_current_season_id(team_id)
        
        # 创建合同记录
        contract = PlayerContract(
            player_id=player_id,
            team_id=team_id,
            season_id=season_id,
            contract_type=contract_type,
            start_season_number=current_season,
            end_season_number=end_season,
            wage=wage,
            recommended_wage=recommended,
            wage_ratio=wage_ratio,
            wage_satisfaction=satisfaction,
            release_clause=release_clause,
            squad_role=squad_role,
            status=ContractStatus.ACTIVE,
        )
        self.db.add(contract)
        
        # 同步 players 表当前合同字段
        await self._sync_player_contract_fields(player, contract)
        
        # 刷新状态
        await self.state_service.recalculate_player_state(player_id, "contract_signed")
        
        await self.db.flush()
        logger.info(f"Contract signed: player={player_id}, team={team_id}, wage={wage}")
        return contract
    
    async def renew_contract(
        self,
        player_id: str,
        team_id: str,
        years: int,
        wage: Decimal,
        squad_role: Optional[SquadRole] = None,
        release_clause: Optional[Decimal] = None,
    ) -> PlayerContract:
        """续约合同"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        # 将旧合同标记为 expired
        old_contract = await self._get_active_contract(player_id)
        if old_contract:
            old_contract.status = ContractStatus.EXPIRED
        
        # 使用当前 squad_role 或传入的新 role
        role = squad_role if squad_role else player.squad_role
        contract_type = player.contract_type
        
        return await self.sign_contract(
            player_id=player_id,
            team_id=team_id,
            contract_type=contract_type,
            years=years,
            wage=wage,
            squad_role=role,
            release_clause=release_clause,
        )
    
    async def release_player(self, player_id: str, team_id: str) -> None:
        """解约球员"""
        contract = await self._get_active_contract(player_id)
        if contract and contract.team_id == team_id:
            contract.status = ContractStatus.TERMINATED
        
        player = await self._get_player(player_id)
        if player:
            player.team_id = None
            player.contract_type = ContractType.FREE
            player.contract_end_season = None
            player.wage = Decimal("0")
            player.release_clause = None
            player.wage_satisfaction = 0
            player.wage_ratio = None
            player.recommended_wage = None
        
        await self.db.flush()
        logger.info(f"Player released: player={player_id}, team={team_id}")
    
    async def expire_contracts(self, season_id: str) -> None:
        """赛季切换时处理到期合同"""
        result = await self.db.execute(
            select(PlayerContract)
            .where(PlayerContract.status == ContractStatus.ACTIVE)
            .where(PlayerContract.end_season_number.isnot(None))
        )
        contracts = result.scalars().all()
        
        season = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = season.scalar_one_or_none()
        if not season:
            return
        
        expired_count = 0
        for contract in contracts:
            if contract.end_season_number <= season.season_number:
                contract.status = ContractStatus.EXPIRED
                # 如果球员还在原球队，将其变为自由身
                player = await self._get_player(contract.player_id)
                if player and player.team_id == contract.team_id:
                    player.contract_type = ContractType.FREE
                    player.contract_end_season = None
                expired_count += 1
        
        await self.db.flush()
        logger.info(f"Expired {expired_count} contracts for season {season_id}")
    
    # =====================================================================
    # 内部辅助
    # =====================================================================
    
    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()
    
    async def _get_team(self, team_id: str) -> Optional[Team]:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()
    
    async def _get_active_contract(self, player_id: str) -> Optional[PlayerContract]:
        result = await self.db.execute(
            select(PlayerContract)
            .where(PlayerContract.player_id == player_id)
            .where(PlayerContract.status == ContractStatus.ACTIVE)
            .order_by(desc(PlayerContract.created_at))
        )
        return result.scalars().first()
    
    async def _get_team_league_level(self, team_id: str) -> int:
        result = await self.db.execute(
            select(Team.current_league_id).where(Team.id == team_id)
        )
        league_id = result.scalar_one_or_none()
        if not league_id:
            return 4
        from app.models.league import League
        result = await self.db.execute(select(League.level).where(League.id == league_id))
        level = result.scalar_one_or_none()
        return level or 4
    
    async def _get_current_season_id(self, team_id: str) -> Optional[str]:
        result = await self.db.execute(
            select(Team.current_season_id).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_current_season_number(self, team_id: str) -> int:
        season_id = await self._get_current_season_id(team_id)
        if season_id:
            result = await self.db.execute(
                select(Season.season_number).where(Season.id == season_id)
            )
            sn = result.scalar_one_or_none()
            if sn is not None:
                return sn
        return 1
    
    async def _get_base_wage_by_ovr(self, ovr: int) -> Decimal:
        """按 OVR 线性插值获取基础工资"""
        result = await self.db.execute(
            select(WageConfig)
            .where(WageConfig.config_type == WageConfigType.BASE_WAGE)
            .order_by(WageConfig.sort_order)
        )
        rows = result.scalars().all()
        
        if not rows:
            return Decimal("30000")
        
        # 转为 (ovr, wage) 列表
        points = [(int(r.level_key), r.value) for r in rows]
        points.sort(key=lambda x: x[0])
        
        # 边界检查
        if ovr <= points[0][0]:
            return points[0][1]
        if ovr >= points[-1][0]:
            return points[-1][1]
        
        # 线性插值
        for i in range(len(points) - 1):
            low_ovr, low_wage = points[i]
            high_ovr, high_wage = points[i + 1]
            if low_ovr <= ovr <= high_ovr:
                ratio = Decimal(str(ovr - low_ovr)) / Decimal(str(high_ovr - low_ovr))
                wage = low_wage + (high_wage - low_wage) * ratio
                return wage.quantize(Decimal("0.01"))
        
        return points[-1][1]
    
    async def _get_wage_config(self, config_type: WageConfigType, level_key: str) -> Decimal:
        """查询工资配置值"""
        result = await self.db.execute(
            select(WageConfig.value)
            .where(WageConfig.config_type == config_type)
            .where(WageConfig.level_key == level_key)
        )
        value = result.scalar_one_or_none()
        return value if value is not None else Decimal("1.0")
    
    @staticmethod
    def _age_range_key(age: int) -> str:
        """年龄映射到配置表 key"""
        if age <= 20:
            return "<=20"
        if age <= 25:
            return "21-25"
        if age <= 28:
            return "26-28"
        if age <= 30:
            return "29-30"
        if age <= 33:
            return "31-33"
        return ">=34"
    
    @staticmethod
    def _wage_ratio_to_satisfaction(wage_ratio: Decimal) -> int:
        """工资比例映射到满意度 (设计文档 5.4)"""
        for threshold, satisfaction in _WAGE_SATISFACTION_MAP:
            if wage_ratio < threshold:
                return satisfaction
        return 2
    
    @staticmethod
    def _satisfaction_to_reaction(satisfaction: int) -> str:
        """满意度映射到可见反应"""
        if satisfaction >= 2:
            return "非常满意"
        if satisfaction >= 1:
            return "满意"
        if satisfaction >= 0:
            return "平常"
        if satisfaction >= -2:
            return "不满"
        return "非常不满"
    
    async def _sync_player_contract_fields(
        self,
        player: Player,
        contract: PlayerContract,
    ) -> None:
        """同步当前合同字段到 players 表"""
        player.contract_type = contract.contract_type
        player.contract_end_season = contract.end_season_number
        player.wage = contract.wage
        player.release_clause = contract.release_clause
        player.squad_role = contract.squad_role
        player.recommended_wage = contract.recommended_wage
        player.wage_ratio = contract.wage_ratio
        player.wage_satisfaction = contract.wage_satisfaction
        player.team_id = contract.team_id


class ContractPreview:
    """合同预览结果"""
    
    def __init__(
        self,
        recommended_wage: Decimal,
        offered_wage: Decimal,
        wage_ratio: Decimal,
        visible_reaction: str,
        hidden_wage_satisfaction: int,
        wage_cap_after_pct: int,
        can_submit: bool,
        warnings: list[str],
    ):
        self.recommended_wage = recommended_wage
        self.offered_wage = offered_wage
        self.wage_ratio = wage_ratio
        self.visible_reaction = visible_reaction
        self.hidden_wage_satisfaction = hidden_wage_satisfaction
        self.wage_cap_after_pct = wage_cap_after_pct
        self.can_submit = can_submit
        self.warnings = warnings
    
    def to_dict(self) -> dict:
        return {
            "recommended_wage": float(self.recommended_wage),
            "offered_wage": float(self.offered_wage),
            "wage_ratio": float(self.wage_ratio),
            "visible_reaction": self.visible_reaction,
            "hidden_wage_satisfaction": self.hidden_wage_satisfaction,
            "wage_cap_after_pct": self.wage_cap_after_pct,
            "can_submit": self.can_submit,
            "warnings": self.warnings,
        }
