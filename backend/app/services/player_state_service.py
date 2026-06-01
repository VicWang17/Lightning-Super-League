"""
Player state service - 球员状态聚合服务
按设计文档 CONTRACT-PLAYER-STATE-SYSTEM-DESIGN.md 实现。
职责：计算所有状态来源分，更新球员可见状态，为比赛引擎构建有效属性。
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_

from app.models.player import (
    Player,
    PlayerPersonality,
    MatchForm,
    PlayerStatus,
)
from app.models.player_state_snapshot import PlayerStateSnapshot
from app.models.season import Fixture, FixtureStatus
from app.models.match_result import MatchResult as MatchResultModel
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
    (50, 0, -4),
    (30, -1, -10),
    (0, -2, -18),
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
    (180, -2),
    (120, -1),
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
        use_cached_match_data: bool = True,
        flush: bool = True,
        current_season_number: int | None = None,
    ) -> PlayerStateSnapshot:
        """重新计算球员状态并写入快照"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")

        return await self.recalculate_loaded_player_state(
            player,
            source_event=source_event,
            use_cached_match_data=use_cached_match_data,
            flush=flush,
            current_season_number=current_season_number,
        )

    async def recalculate_loaded_player_state(
        self,
        player: Player,
        source_event: str,
        use_cached_match_data: bool = True,
        flush: bool = True,
        current_season_number: int | None = None,
    ) -> PlayerStateSnapshot:
        """刷新已加载球员的状态缓存并写入快照，避免赛后批处理重复查询。"""
        components = await self.calculate_state_components(
            player,
            use_cached_match_data=use_cached_match_data,
            current_season_number=current_season_number,
        )
        
        # 写入快照
        snapshot = PlayerStateSnapshot(
            player_id=player.id,
            team_id=player.team_id,
            source_event=source_event,
            **components.to_dict(),
        )
        self.db.add(snapshot)
        
        self.apply_components_to_player(player, components)
        
        if flush:
            await self.db.flush()
        logger.info(
            f"State recalculated: player={player.id}, "
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
    
    async def calculate_state_components(
        self,
        player: Player,
        use_cached_match_data: bool = True,
        current_season_number: int | None = None,
    ) -> "PlayerStateComponents":
        """计算所有状态来源分并聚合"""
        # 查询当前赛季号（用于合同到期压力计算）
        if current_season_number is None:
            current_season_number = await self._get_current_season_number(player.team_id)
        
        contract_score = self._calc_contract_score(player, current_season_number)
        if use_cached_match_data:
            recent_match_score = self._calc_recent_match_score_from_ratings(player.recent_ratings or [])
            match_load_score = self._calc_match_load_score_from_minutes(player.recent_minutes or [])
        else:
            recent_match_score = await self._calc_recent_match_score(player.id, player.team_id)
            match_load_score = await self._calc_match_load_score(player.id, player.team_id)
        fitness_score, stamina_modifier = self._calc_fitness_score(player.fitness)
        match_rust_score = player.match_rust_score  # 持久化值，赛后维护
        training_load_score = 0  # 预留接口
        morale_score = 1  # 基础士气，避免常规轮换和体能扣分长期压低全联盟状态
        
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
    
    def components_from_cache(self, player: Player) -> "PlayerStateComponents":
        """从 players 表缓存读取状态，供赛前 payload 构建使用。"""
        total_score = max(-10, min(10, int(player.state_score or 0)))
        visible_form = player.match_form or self._map_to_visible_form(total_score)
        attribute_modifier_pct = player.state_attribute_modifier_pct or Decimal("0.0000")
        stamina_modifier = player.state_stamina_modifier or Decimal("0.00")
        return PlayerStateComponents(
            contract_score=player.state_contract_score or 0,
            recent_match_score=player.state_recent_match_score or 0,
            fitness_score=player.state_fitness_score or 0,
            match_load_score=player.state_match_load_score or 0,
            match_rust_score=player.match_rust_score or 0,
            training_load_score=player.state_training_load_score or 0,
            morale_score=player.state_morale_score or 0,
            total_score=total_score,
            visible_form=visible_form,
            attribute_modifier_pct=attribute_modifier_pct,
            stamina_modifier=stamina_modifier,
        )

    def apply_components_to_player(self, player: Player, components: "PlayerStateComponents") -> None:
        """把状态分解值写入 players 缓存字段。"""
        player.match_form = components.visible_form
        player.state_score = components.total_score
        player.state_contract_score = components.contract_score
        player.state_recent_match_score = components.recent_match_score
        player.state_fitness_score = components.fitness_score
        player.state_match_load_score = components.match_load_score
        player.state_training_load_score = components.training_load_score
        player.state_morale_score = components.morale_score
        player.state_attribute_modifier_pct = components.attribute_modifier_pct
        player.state_stamina_modifier = components.stamina_modifier
        player.state_updated_at = datetime.utcnow()

    async def audit_player_state_cache(self, player_id: str) -> dict:
        """完整历史重算并与缓存对比，用于压测/排错。"""
        player = await self._get_player(player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        cached = self.components_from_cache(player)
        recalculated = await self.calculate_state_components(player, use_cached_match_data=False)
        return {
            "player_id": player_id,
            "cached": cached.to_dict(),
            "recalculated": recalculated.to_dict(),
            "total_score_delta": recalculated.total_score - cached.total_score,
            "attribute_modifier_delta": float(recalculated.attribute_modifier_pct - cached.attribute_modifier_pct),
            "stamina_modifier_delta": float(recalculated.stamina_modifier - cached.stamina_modifier),
        }

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
            if seasons_remaining <= 0:
                expiry_modifier = -1
        
        return max(-4, min(4, base_score + expiry_modifier))
    
    def _calc_recent_match_score_from_ratings(self, ratings: list) -> int:
        """近期比赛来源分 (设计文档 6.1)"""
        if not ratings:
            return 0
        
        avg_rating = sum(float(r) for r in ratings) / len(ratings)
        for threshold, score in _RATING_SCORE_MAP:
            if avg_rating >= threshold:
                return score
        return -3

    async def _calc_recent_match_score(self, player_id: str, team_id: str | None = None) -> int:
        ratings = await self._get_recent_match_ratings(player_id, team_id, limit=3)
        return self._calc_recent_match_score_from_ratings(ratings)
    
    def _calc_fitness_score(self, fitness: int) -> tuple[int, int]:
        """体能来源分和 stamina 修正 (设计文档 6.1)"""
        for threshold, score, stamina_mod in _FITNESS_SCORE_MAP:
            if fitness >= threshold:
                return score, stamina_mod
        return -5, -30
    
    def _calc_match_load_score_from_minutes(self, minutes: list) -> int:
        """连续比赛劳累来源分 (设计文档 6.1)"""
        total_minutes = sum(int(m) for m in minutes)
        for threshold, score in _MATCH_LOAD_MAP:
            if total_minutes >= threshold:
                return score
        return 0

    async def _calc_match_load_score(self, player_id: str, team_id: str | None = None) -> int:
        minutes = await self._get_recent_match_minutes(player_id, team_id, limit=3)
        return self._calc_match_load_score_from_minutes(minutes)
    
    # =====================================================================
    # 比赛引擎集成
    # =====================================================================
    
    async def build_match_player_setup(self, player: Player) -> dict:
        """为比赛引擎构建带状态修正的球员数据"""
        components = self.components_from_cache(player)
        
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
    
    async def _get_recent_match_ratings(
        self, player_id: str, team_id: str | None = None, limit: int = 3
    ) -> list[float]:
        """从 MatchResult.player_stats 中提取最近比赛的评分"""
        query = (
            select(MatchResultModel.player_stats)
            .join(Fixture, MatchResultModel.fixture_id == Fixture.id)
            .where(Fixture.status == FixtureStatus.FINISHED)
            .order_by(desc(Fixture.season_day))
            .limit(limit * 2)  # 多取一些，过滤掉未出场的
        )
        if team_id:
            query = query.where(
                or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id)
            )
        result = await self.db.execute(query)
        match_results = result.scalars().all()
        
        ratings = []
        for player_stats in match_results:
            if not player_stats:
                continue
            for ps in player_stats:
                if ps.get("player_id") == player_id:
                    rating = ps.get("rating")
                    if rating is not None:
                        ratings.append(float(rating))
                    break
            if len(ratings) >= limit:
                break
        return ratings[:limit]
    
    async def _get_recent_match_minutes(
        self, player_id: str, team_id: str | None = None, limit: int = 3
    ) -> list[int]:
        """从 MatchResult.player_stats 中提取最近比赛的出场分钟数"""
        query = (
            select(MatchResultModel.player_stats, MatchResultModel.raw_result)
            .join(Fixture, MatchResultModel.fixture_id == Fixture.id)
            .where(Fixture.status == FixtureStatus.FINISHED)
            .order_by(desc(Fixture.season_day))
            .limit(limit * 2)
        )
        if team_id:
            query = query.where(
                or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id)
            )
        result = await self.db.execute(query)
        match_results = result.all()
        
        minutes = []
        for player_stats, raw_result in match_results:
            if not player_stats:
                continue
            for ps in player_stats:
                if ps.get("player_id") == player_id:
                    # 出场即计入，默认 50 或 70 分钟（与 match_simulator 一致）
                    # 如果 engine 返回了 minutes，使用实际值
                    mins = ps.get("minutes_played")
                    if mins is None:
                        # 根据 resolution 推断：常规时间 50，加时/点球 70
                        mins = 70 if (raw_result or {}).get("resolution") in {"extra_time", "penalties"} else 50
                    minutes.append(int(mins))
                    break
            if len(minutes) >= limit:
                break
        return minutes[:limit]
    
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
