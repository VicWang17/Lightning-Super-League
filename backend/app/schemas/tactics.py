"""
Tactics-related schemas
"""
from datetime import datetime
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator

from app.schemas.base import BaseSchema


class TacticsSetup(BaseSchema):
    """V1 12 字段战术滑条，向后兼容保留"""

    passing_style: int = Field(2, ge=0, le=4)
    attack_width: int = Field(2, ge=0, le=4)
    attack_tempo: int = Field(2, ge=0, le=4)
    defensive_line_height: int = Field(2, ge=0, le=4)
    crossing_strategy: int = Field(2, ge=0, le=4)
    shooting_mentality: int = Field(2, ge=0, le=4)
    playmaker_focus: int = Field(0, ge=0, le=4)
    pressing_intensity: int = Field(2, ge=0, le=4)
    defensive_compactness: int = Field(1, ge=0, le=2)
    marking_strategy: int = Field(0, ge=0, le=2)
    offside_trap: int = Field(0, ge=0, le=2)
    tackling_aggression: int = Field(1, ge=0, le=3)


class InPossessionInstructions(BaseSchema):
    """持球进攻阶段指令"""

    build_up_style: Literal["short", "balanced", "direct", "long_ball"] = "balanced"
    chance_creation: Literal["patient", "balanced", "early_shot", "work_into_box"] = "balanced"
    attack_route: Literal["left", "center", "right", "both_wings", "mixed"] = "mixed"
    width: int = Field(2, ge=0, le=4)
    tempo: int = Field(2, ge=0, le=4)
    passing_risk: int = Field(2, ge=0, le=4)
    crossing_frequency: int = Field(2, ge=0, le=4)
    dribble_frequency: int = Field(2, ge=0, le=4)
    shooting_frequency: int = Field(2, ge=0, le=4)


class TransitionInstructions(BaseSchema):
    """转换阶段指令"""

    after_possession_lost: Literal["counter_press", "balanced", "regroup"] = "balanced"
    after_possession_won: Literal["counter", "balanced", "hold_shape"] = "balanced"
    counter_directness: int = Field(2, ge=0, le=4)
    reset_under_pressure: int = Field(2, ge=0, le=4)


class OutOfPossessionInstructions(BaseSchema):
    """无球防守阶段指令"""

    defensive_line_height: int = Field(2, ge=0, le=4)
    pressing_intensity: int = Field(2, ge=0, le=4)
    pressing_trigger: Literal["passive", "bad_touch", "wide_trap", "center_trap", "always"] = "bad_touch"
    compactness: int = Field(1, ge=0, le=4)
    marking: Literal["zonal", "mixed", "man"] = "mixed"
    tackling_aggression: int = Field(1, ge=0, le=3)
    offside_trap: int = Field(0, ge=0, le=2)


class GoalkeeperDistributionInstructions(BaseSchema):
    """门将出球分配指令"""

    distribution_target: Literal["center_backs", "fullbacks", "midfield", "target_forward", "mixed"] = "mixed"
    distribution_length: Literal["short", "balanced", "long"] = "balanced"
    release_speed: Literal["slow", "balanced", "quick"] = "balanced"


class PlayerInstruction(BaseSchema):
    """球员个人指令"""

    player_id: str
    carry_ball: int = Field(2, ge=0, le=4)
    passing_risk: int = Field(2, ge=0, le=4)
    shooting_frequency: int = Field(2, ge=0, le=4)
    crossing_frequency: int = Field(2, ge=0, le=4)
    pressing_intensity: int = Field(2, ge=0, le=4)
    hold_position: int = Field(2, ge=0, le=4)
    forward_runs: int = Field(2, ge=0, le=4)


class SituationalRuleCondition(BaseSchema):
    """情境规则触发条件"""

    minute_gte: Optional[int] = Field(None, ge=0, le=120)
    minute_lt: Optional[int] = Field(None, ge=0, le=120)
    goal_diff_lte: Optional[int] = Field(None, ge=-20, le=20)
    goal_diff_gte: Optional[int] = Field(None, ge=-20, le=20)
    team_stamina_avg_lte: Optional[int] = Field(None, ge=0, le=100)


class SituationalRuleOverride(BaseSchema):
    """情境规则对团队指令的覆盖"""

    tempo: Optional[int] = Field(None, ge=0, le=4)
    shooting_frequency: Optional[int] = Field(None, ge=0, le=4)
    defensive_line_height: Optional[int] = Field(None, ge=0, le=4)
    pressing_intensity: Optional[int] = Field(None, ge=0, le=4)
    passing_risk: Optional[int] = Field(None, ge=0, le=4)
    crossing_frequency: Optional[int] = Field(None, ge=0, le=4)
    width: Optional[int] = Field(None, ge=0, le=4)
    after_possession_won: Optional[Literal["counter", "balanced", "hold_shape"]] = None
    after_possession_lost: Optional[Literal["counter_press", "balanced", "regroup"]] = None
    build_up_style: Optional[Literal["short", "balanced", "direct", "long_ball"]] = None
    chance_creation: Optional[Literal["patient", "balanced", "early_shot", "work_into_box"]] = None


class SituationalRule(BaseSchema):
    """单条情境规则"""

    id: str
    name: str = ""
    enabled: bool = True
    condition: SituationalRuleCondition = Field(default_factory=SituationalRuleCondition)
    override: SituationalRuleOverride = Field(default_factory=SituationalRuleOverride)


class TeamInstructions(BaseSchema):
    """V2 阶段化团队战术指令

    内部同时保留 V1 的 legacy_team_sliders，确保旧记录可加载。
    """

    legacy_team_sliders: TacticsSetup = Field(default_factory=TacticsSetup)
    in_possession: InPossessionInstructions = Field(default_factory=InPossessionInstructions)
    transition: TransitionInstructions = Field(default_factory=TransitionInstructions)
    out_of_possession: OutOfPossessionInstructions = Field(default_factory=OutOfPossessionInstructions)
    goalkeeper_distribution: GoalkeeperDistributionInstructions = Field(
        default_factory=GoalkeeperDistributionInstructions
    )
    player_instructions: List[PlayerInstruction] = Field(default_factory=list)
    situational_rules: List[SituationalRule] = Field(default_factory=list)

    def get_player_instruction(self, player_id: str) -> PlayerInstruction:
        """获取指定球员的个人指令，未配置则返回默认值"""
        for instr in self.player_instructions:
            if instr.player_id == player_id:
                return instr
        return PlayerInstruction(player_id=player_id)

    @model_validator(mode="after")
    def _limit_player_instructions(self) -> "TeamInstructions":
        """最多保存 13 条个人指令（8 首发 + 5 替补）"""
        if len(self.player_instructions) > 13:
            self.player_instructions = self.player_instructions[:13]
        return self

    @model_validator(mode="after")
    def _limit_situational_rules(self) -> "TeamInstructions":
        """最多保存 10 条情境规则，防止规则爆炸"""
        if len(self.situational_rules) > 10:
            self.situational_rules = self.situational_rules[:10]
        return self

    @classmethod
    def from_legacy(cls, legacy: TacticsSetup) -> "TeamInstructions":
        """从 V1 的 12 条滑条推导出 V2 阶段化指令默认值"""
        return cls(
            legacy_team_sliders=legacy,
            in_possession=InPossessionInstructions(
                build_up_style="short" if legacy.passing_style >= 3 else "direct" if legacy.passing_style <= 1 else "balanced",
                attack_route="both_wings" if legacy.attack_width >= 3 else "center" if legacy.attack_width <= 1 else "mixed",
                width=legacy.attack_width,
                tempo=legacy.attack_tempo,
                passing_risk=2,
                crossing_frequency=legacy.crossing_strategy,
                dribble_frequency=2,
                shooting_frequency=legacy.shooting_mentality,
            ),
            transition=TransitionInstructions(
                after_possession_lost="counter_press" if legacy.pressing_intensity >= 3 else "balanced",
                after_possession_won="counter" if legacy.attack_tempo >= 3 else "hold_shape" if legacy.attack_tempo <= 1 else "balanced",
                counter_directness=legacy.attack_tempo,
                reset_under_pressure=2,
            ),
            out_of_possession=OutOfPossessionInstructions(
                defensive_line_height=legacy.defensive_line_height,
                pressing_intensity=legacy.pressing_intensity,
                compactness=legacy.defensive_compactness,
                marking="man" if legacy.marking_strategy >= 2 else "zonal" if legacy.marking_strategy == 0 else "mixed",
                tackling_aggression=legacy.tackling_aggression,
                offside_trap=legacy.offside_trap,
            ),
            goalkeeper_distribution=GoalkeeperDistributionInstructions(
                distribution_target="mixed",
                distribution_length="balanced",
                release_speed="balanced",
            ),
        )


class TeamTacticsResponse(BaseSchema):
    """球队战术方案响应"""

    team_id: str
    formation_id: str
    lineup_player_ids: List[str]
    bench_player_ids: List[str]
    team_instructions: TeamInstructions
    set_piece_instructions: dict
    substitution_rules: dict
    ai_profile: dict | None = None
    created_at: datetime
    updated_at: datetime


class TeamTacticsUpdate(BaseSchema):
    """更新球队战术方案请求"""

    formation_id: str = Field(..., pattern=r"^F0[1-8]$")
    lineup_player_ids: List[str]
    bench_player_ids: List[str]
    team_instructions: TeamInstructions
    set_piece_instructions: dict = Field(default_factory=dict)
    substitution_rules: dict = Field(default_factory=dict)

    @field_validator("lineup_player_ids")
    @classmethod
    def validate_lineup_length(cls, v: List[str]) -> List[str]:
        if len(v) != 8:
            raise ValueError("首发阵容必须为 8 人")
        return v

    @field_validator("bench_player_ids")
    @classmethod
    def validate_bench_length(cls, v: List[str]) -> List[str]:
        if len(v) > 5:
            raise ValueError("替补席最多 5 人")
        return v
