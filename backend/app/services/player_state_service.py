"""
Player state service - 球员状态聚合服务
按设计文档 CONTRACT-PLAYER-STATE-SYSTEM-DESIGN.md 实现。
职责：计算所有状态来源分，更新球员可见状态，为比赛引擎构建有效属性。
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.player import (
    Player,
    PlayerPersonality,
    MatchForm,
    PlayerStatus,
)
from app.models.player_state_snapshot import PlayerStateSnapshot
from app.core.logging import get_logger

logger = get_logger("app.player_state")


# 性格对工资满意度的权重系数 (设计文档 5.5)
_PERSONALITY_MONEY_SENSITIVITY = {
    PlayerPersonality.MATERIALISTIC: Decimal("1.6"),
    PlayerPersonality.AMBITIOUS: Decimal("1.4"),
    PlayerPersonality.PROFESSIONAL: Decimal("1.0"),
    PlayerPersonality.PASSIONATE: Decimal("0.8"),
    PlayerPersonality.LOYAL: Decimal("0.6"),
    PlayerPersonality.TEAM_ORIENTED: Decimal("0.5"),
}

# 体能来源分映射 (设计文档 6.1)
_FITNESS_SCORE_MAP = [
    (90, 1, 3),
    (70, 0, 0),
    (50, -1, -8),
    (30, -3, -18),
    (0, -5, -30),
]

# 近期比赛评分映射 (设计文档 6.1)
_RATING_SCORE_MAP = [
    (8.0, 4),
    (7.2, 2),
    (6.5, 0),
    (6.0, -1),
    (0.0, -3),
]

# 连续比赛劳累映射 (设计文档 6.1)
_MATCH_LOAD_MAP = [
    (160, -3),
    (100, -2),
    (60, -1),
    (0, 0),
]


class PlayerStateService:
    """球员状态服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =====================================================================
    # 主入口
    # =====================================================================
    
    async def recalculate_player_state(
        self,
        player_id: str,
        source_event: str,
    ) -> PlayerStateSnapshot:
        """重新计算球员状态并写入快照"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        components = await self.calculate_state_components(player)
        
        # 写入快照
        snapshot = PlayerStateSnapshot(
            player_id=player_id,
            team_id=player.team_id,
            source_event=source_event,
            **components.to_dict(),
        )
        self.db.add(snapshot)
        
        # 更新玩家可见状态
        player.match_form = components.visible_form
        player.state_score = components.total_score
        player.state_updated_at = datetime.utcnow()
        
        await self.db.flush()
        logger.info(
            f"State recalculated: player={player_id}, "
            f"total={components.total_score}, form={components.visible_form.value}"
        )
        return snapshot
    
    async def recalculate_team_state(
        self,
        team_id: str,
        source_event: str,
    ) -> list[PlayerStateSnapshot]:
        """重新计算全队球员状态"""
        result = await self.db.execute(
            select(Player.id).where(Player.team_id == team_id)
        )
        player_ids = [r[0] for r in result.all()]
        
        snapshots = []
        for pid in player_ids:
            try:
                snap = await self.recalculate_player_state(pid, source_event)
                snapshots.append(snap)
            except Exception as exc:
                logger.warning(f"Failed to recalculate state for player {pid}: {exc}")
        return snapshots
    
    # =====================================================================
    # 状态来源计算
    # =====================================================================
    
    async def calculate_state_components(self, player: Player) -> "PlayerStateComponents":
        """计算所有状态来源分并聚合"""
        # 查询当前赛季号（用于合同到期压力计算）
        current_season_number = await self._get_current_season_number(player.team_id)
        
        contract_score = self._calc_contract_score(player, current_season_number)
        recent_match_score = self._calc_recent_match_score(player)
        fitness_score, stamina_modifier = self._calc_fitness_score(player.fitness)
        match_load_score = self._calc_match_load_score(player)
        match_rust_score = player.match_rust_score  # 持久化值，赛后维护
        training_load_score = 0  # 预留接口
        morale_score = 0  # 预留接口
        
        total_score = (
            contract_score
            + recent_match_score
            + fitness_score
            + match_load_score
            + match_rust_score
            + training_load_score
            + morale_score
        )
        total_score = max(-10, min(10, total_score))
        
        visible_form = self._map_to_visible_form(total_score)
        attribute_modifier_pct = Decimal(
            str(max(-0.04, min(0.04, total_score * 0.004)))
        ).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        
        return PlayerStateComponents(
            contract_score=contract_score,
            recent_match_score=recent_match_score,
            fitness_score=fitness_score,
            match_load_score=match_load_score,
            match_rust_score=match_rust_score,
            training_load_score=training_load_score,
            morale_score=morale_score,
            total_score=total_score,
            visible_form=visible_form,
            attribute_modifier_pct=attribute_modifier_pct,
            stamina_modifier=Decimal(str(stamina_modifier)),
        )
    
    def _calc_contract_score(self, player: Player, current_season_number: int | None = None) -> int:
        """合同来源分 (设计文档 6.1 / 5.6)"""
        if player.wage_satisfaction is None:
            return 0
        
        sensitivity = _PERSONALITY_MONEY_SENSITIVITY.get(
            player.personality, Decimal("1.0")
        )
        base_score = round(player.wage_satisfaction * float(sensitivity))
        
        # 合同到期压力 (设计文档 5.6)
        expiry_modifier = 0
        if current_season_number is not None and player.contract_end_season is not None:
            seasons_remaining = player.contract_end_season - current_season_number
            if seasons_remaining == 1:
                expiry_modifier = -1
            elif seasons_remaining <= 0:
                expiry_modifier = -2
        
        return max(-4, min(4, base_score + expiry_modifier))
    
    def _calc_recent_match_score(self, player: Player) -> int:
        """近期比赛来源分 (设计文档 6.1) — 从球员滑动窗口读取"""
        ratings = player.recent_ratings or []
        if not ratings:
            return 0
        avg_rating = sum(ratings) / len(ratings)
        for threshold, score in _RATING_SCORE_MAP:
            if avg_rating >= threshold:
                return score
        return -3

    def _calc_fitness_score(self, fitness: int) -> tuple[int, int]:
        """体能来源分和 stamina 修正 (设计文档 6.1)"""
        for threshold, score, stamina_mod in _FITNESS_SCORE_MAP:
            if fitness >= threshold:
                return score, stamina_mod
        return -5, -30

    def _calc_match_load_score(self, player: Player) -> int:
        """连续比赛劳累来源分 (设计文档 6.1) — 从球员滑动窗口读取"""
        minutes = player.recent_minutes or []
        total_minutes = sum(minutes)
        for threshold, score in _MATCH_LOAD_MAP:
            if total_minutes >= threshold:
                return score
        return 0
    
    # =====================================================================
    # 比赛引擎集成
    # =====================================================================
    
    async def build_match_player_setup(self, player: Player) -> dict:
        """为比赛引擎构建带状态修正的球员数据"""
        # 构建 payload 时只读不算写，避免触发 autoflush 导致
        # "Session is already flushing" 错误。
        with self.db.no_autoflush:
            components = await self.calculate_state_components(player)
        
        base_attributes = {
            "SHO": player.sho,
            "PAS": player.pas,
            "DRI": player.dri,
            "SPD": player.spd,
            "STR": player.str_,
            "STA": player.sta,
            "DEF": player.defe,
            "HEA": player.hea,
            "VIS": player.vis,
            "TKL": player.tkl,
            "ACC": player.acc,
            "CRO": player.cro,
            "CON": player.con,
            "FIN": player.fin,
            "BAL": player.bal,
            "COM": player.com,
            "SAV": player.sav,
            "REF": player.ref,
            "POS": player.pos,
            "SET": round((player.fk + player.pk) / 2),
            "DEC": player.dec,
        }
        
        effective_attributes = self.apply_state_to_attributes(
            base_attributes, components.attribute_modifier_pct
        )
        initial_stamina = max(
            30.0,
            min(100.0, player.fitness + float(components.stamina_modifier)),
        )
        
        return {
            "player_id": player.id,
            "name": player.name,
            "position": getattr(player.position, "value", player.position),
            "attributes": effective_attributes,
            "skills": [],  # 由调用方填充
            "stamina": float(initial_stamina),
            "height": player.height,
            "foot": self._foot(player.preferred_foot),
        }
    
    @staticmethod
    def apply_state_to_attributes(
        attributes: dict[str, int],
        modifier_pct: Decimal,
    ) -> dict[str, int]:
        """对属性应用状态修正 (设计文档 6.4 / 8.2)"""
        result = {}
        for key, base_val in attributes.items():
            effective = round(base_val * (1 + float(modifier_pct)))
            effective = max(1, min(20, effective))
            result[key] = effective
        return result
    
    def calculate_initial_stamina(
        self,
        player: Player,
        snapshot: Optional[PlayerStateSnapshot] = None,
    ) -> float:
        """计算初始 stamina (设计文档 6.5)"""
        if snapshot is None:
            _, stamina_mod = self._calc_fitness_score(player.fitness)
        else:
            stamina_mod = float(snapshot.stamina_modifier)
        
        initial = player.fitness + stamina_mod
        return max(30.0, min(100.0, initial))
    
    # =====================================================================
    # 内部辅助
    # =====================================================================
    
    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(
            select(Player).where(Player.id == player_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _map_to_visible_form(total_score: int) -> MatchForm:
        """综合状态分映射到可见状态 (设计文档 6.3)"""
        if total_score >= 6:
            return MatchForm.HOT
        if total_score >= 2:
            return MatchForm.GOOD
        if total_score >= -1:
            return MatchForm.NEUTRAL
        return MatchForm.LOW
    
    # TODO: 每日自然恢复（设计文档 9.4）
    # 训练系统完善后，将赛后回写中的 fitness 恢复逻辑迁移至此，
    # 并接入 season_service 的事件队列作为独立的 DAILY_PLAYER_STATE_TICK 事件。
    # 当前简化版：赛后回写直接处理出场扣 fitness / 未出场恢复 fitness。
    
    async def _get_current_season_number(self, team_id: str | None) -> int | None:
        """通过 team_id 查询当前赛季号"""
        if not team_id:
            return None
        from app.models.team import Team
        from app.models.season import Season
        
        result = await self.db.execute(
            select(Season.season_number)
            .join(Team, Team.current_season_id == Season.id)
            .where(Team.id == team_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _foot(foot) -> str:
        value = getattr(foot, "value", foot)
        mapping = {"LEFT": "left", "RIGHT": "right", "BOTH": "both"}
        return mapping.get(value, "right")


class PlayerStateComponents:
    """状态来源分解值（数据传输对象）"""
    
    def __init__(
        self,
        contract_score: int,
        recent_match_score: int,
        fitness_score: int,
        match_load_score: int,
        match_rust_score: int,
        training_load_score: int,
        morale_score: int,
        total_score: int,
        visible_form: MatchForm,
        attribute_modifier_pct: Decimal,
        stamina_modifier: Decimal,
    ):
        self.contract_score = contract_score
        self.recent_match_score = recent_match_score
        self.fitness_score = fitness_score
        self.match_load_score = match_load_score
        self.match_rust_score = match_rust_score
        self.training_load_score = training_load_score
        self.morale_score = morale_score
        self.total_score = total_score
        self.visible_form = visible_form
        self.attribute_modifier_pct = attribute_modifier_pct
        self.stamina_modifier = stamina_modifier
    
    def to_dict(self) -> dict:
        return {
            "contract_score": self.contract_score,
            "recent_match_score": self.recent_match_score,
            "fitness_score": self.fitness_score,
            "match_load_score": self.match_load_score,
            "match_rust_score": self.match_rust_score,
            "training_load_score": self.training_load_score,
            "morale_score": self.morale_score,
            "total_score": self.total_score,
            "visible_form": self.visible_form,
            "attribute_modifier_pct": self.attribute_modifier_pct,
            "stamina_modifier": self.stamina_modifier,
        }
