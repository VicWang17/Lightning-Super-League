"""
AI Tactics Advisor - AI 球队默认战术生成

V1 只负责在赛季初始化时为 AI 球队生成默认战术方案。
赛前微调、赛中情境规则放到后续迭代。
"""
import random
import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import TeamTactics, Player, PlayerPosition, PlayerStatus, Team, TeamTrainingAIProfile
from app.services.tactics_service import (
    TacticsService,
    FORMATION_REQUIREMENTS,
    TACTIC_PRESETS,
    _select_lineup as auto_select_lineup,
)
from app.schemas.tactics import (
    TacticsSetup,
    TeamInstructions,
    PlayerInstruction,
    InPossessionInstructions,
    TransitionInstructions,
    OutOfPossessionInstructions,
    GoalkeeperDistributionInstructions,
    SituationalRule,
    SituationalRuleCondition,
    SituationalRuleOverride,
)
from app.core.logging import get_logger

logger = get_logger("app.ai_tactics")


# 训练风格 -> 默认战术画像（V2 阶段化字段）
def _default_situational_rules(style: str) -> list[SituationalRule]:
    """根据 AI 风格生成默认落后/领先情境规则"""
    chase: dict[str, int | str] = {
        "tempo": 4,
        "shooting_frequency": 4,
        "defensive_line_height": 4,
        "pressing_intensity": 4,
    }
    protect: dict[str, int | str] = {
        "tempo": 1,
        "defensive_line_height": 1,
        "after_possession_won": "hold_shape",
    }

    if style == "attacking":
        chase["passing_risk"] = 4
        chase["crossing_frequency"] = 3
        protect["pressing_intensity"] = 2
    elif style == "defensive":
        chase["tempo"] = 3
        chase["pressing_intensity"] = 3
        protect["tempo"] = 0
        protect["pressing_intensity"] = 0
    elif style == "physical":
        chase["pressing_intensity"] = 4
        protect["pressing_intensity"] = 3
    elif style == "technical":
        chase["build_up_style"] = "short"
        chase["passing_risk"] = 3
        protect["build_up_style"] = "short"
        protect["chance_creation"] = "patient"
    elif style == "youth_focus":
        chase["tempo"] = 3
        protect["pressing_intensity"] = 1

    return [
        SituationalRule(
            id=str(uuid.uuid4()),
            name="落后追分",
            enabled=True,
            condition=SituationalRuleCondition(minute_gte=40, goal_diff_lte=-1),
            override=SituationalRuleOverride(**chase),  # type: ignore[arg-type]
        ),
        SituationalRule(
            id=str(uuid.uuid4()),
            name="领先稳守",
            enabled=True,
            condition=SituationalRuleCondition(minute_gte=40, goal_diff_gte=1),
            override=SituationalRuleOverride(**protect),  # type: ignore[arg-type]
        ),
    ]


STYLE_TACTICS_PROFILE: dict[str, dict] = {
    "attacking": {
        "formation": "F05",
        "fallback_formation": "F03",
        "preset": "all_out",
        "in_possession": {
            "build_up_style": "direct",
            "chance_creation": "early_shot",
            "attack_route": "center",
            "width": 2,
            "tempo": 4,
            "passing_risk": 3,
            "crossing_frequency": 2,
            "dribble_frequency": 3,
            "shooting_frequency": 4,
        },
        "transition": {
            "after_possession_lost": "counter_press",
            "after_possession_won": "counter",
            "counter_directness": 4,
            "reset_under_pressure": 2,
        },
        "out_of_possession": {
            "defensive_line_height": 3,
            "pressing_intensity": 4,
            "pressing_trigger": "always",
            "compactness": 1,
            "marking": "mixed",
            "tackling_aggression": 2,
            "offside_trap": 1,
        },
        "goalkeeper_distribution": {
            "distribution_target": "mixed",
            "distribution_length": "balanced",
            "release_speed": "quick",
        },
    },
    "defensive": {
        "formation": "F04",
        "fallback_formation": "F06",
        "preset": "deep_defense",
        "in_possession": {
            "build_up_style": "long_ball",
            "chance_creation": "patient",
            "attack_route": "mixed",
            "width": 1,
            "tempo": 2,
            "passing_risk": 1,
            "crossing_frequency": 2,
            "dribble_frequency": 1,
            "shooting_frequency": 2,
        },
        "transition": {
            "after_possession_lost": "regroup",
            "after_possession_won": "counter",
            "counter_directness": 3,
            "reset_under_pressure": 3,
        },
        "out_of_possession": {
            "defensive_line_height": 0,
            "pressing_intensity": 0,
            "pressing_trigger": "passive",
            "compactness": 2,
            "marking": "zonal",
            "tackling_aggression": 0,
            "offside_trap": 0,
        },
        "goalkeeper_distribution": {
            "distribution_target": "target_forward",
            "distribution_length": "long",
            "release_speed": "balanced",
        },
    },
    "physical": {
        "formation": "F08",
        "fallback_formation": "F02",
        "preset": "high_press",
        "in_possession": {
            "build_up_style": "direct",
            "chance_creation": "work_into_box",
            "attack_route": "both_wings",
            "width": 4,
            "tempo": 3,
            "passing_risk": 2,
            "crossing_frequency": 3,
            "dribble_frequency": 3,
            "shooting_frequency": 3,
        },
        "transition": {
            "after_possession_lost": "counter_press",
            "after_possession_won": "counter",
            "counter_directness": 3,
            "reset_under_pressure": 2,
        },
        "out_of_possession": {
            "defensive_line_height": 3,
            "pressing_intensity": 4,
            "pressing_trigger": "bad_touch",
            "compactness": 1,
            "marking": "mixed",
            "tackling_aggression": 3,
            "offside_trap": 1,
        },
        "goalkeeper_distribution": {
            "distribution_target": "fullbacks",
            "distribution_length": "balanced",
            "release_speed": "quick",
        },
    },
    "technical": {
        "formation": "F07",
        "fallback_formation": "F01",
        "preset": "possession",
        "in_possession": {
            "build_up_style": "short",
            "chance_creation": "work_into_box",
            "attack_route": "center",
            "width": 2,
            "tempo": 1,
            "passing_risk": 1,
            "crossing_frequency": 1,
            "dribble_frequency": 2,
            "shooting_frequency": 2,
        },
        "transition": {
            "after_possession_lost": "balanced",
            "after_possession_won": "hold_shape",
            "counter_directness": 2,
            "reset_under_pressure": 2,
        },
        "out_of_possession": {
            "defensive_line_height": 3,
            "pressing_intensity": 2,
            "pressing_trigger": "center_trap",
            "compactness": 2,
            "marking": "zonal",
            "tackling_aggression": 1,
            "offside_trap": 1,
        },
        "goalkeeper_distribution": {
            "distribution_target": "midfield",
            "distribution_length": "short",
            "release_speed": "slow",
        },
    },
    "balanced": {
        "formation": "F01",
        "fallback_formation": "F01",
        "preset": "balanced",
        "in_possession": {
            "build_up_style": "balanced",
            "chance_creation": "balanced",
            "attack_route": "mixed",
            "width": 2,
            "tempo": 2,
            "passing_risk": 2,
            "crossing_frequency": 2,
            "dribble_frequency": 2,
            "shooting_frequency": 2,
        },
        "transition": {
            "after_possession_lost": "balanced",
            "after_possession_won": "balanced",
            "counter_directness": 2,
            "reset_under_pressure": 2,
        },
        "out_of_possession": {
            "defensive_line_height": 2,
            "pressing_intensity": 2,
            "pressing_trigger": "bad_touch",
            "compactness": 1,
            "marking": "mixed",
            "tackling_aggression": 1,
            "offside_trap": 0,
        },
        "goalkeeper_distribution": {
            "distribution_target": "mixed",
            "distribution_length": "balanced",
            "release_speed": "balanced",
        },
    },
    "youth_focus": {
        "formation": "F01",
        "fallback_formation": "F07",
        "preset": "balanced",
        "in_possession": {
            "build_up_style": "balanced",
            "chance_creation": "patient",
            "attack_route": "mixed",
            "width": 2,
            "tempo": 2,
            "passing_risk": 2,
            "crossing_frequency": 2,
            "dribble_frequency": 2,
            "shooting_frequency": 2,
        },
        "transition": {
            "after_possession_lost": "balanced",
            "after_possession_won": "balanced",
            "counter_directness": 2,
            "reset_under_pressure": 3,
        },
        "out_of_possession": {
            "defensive_line_height": 2,
            "pressing_intensity": 2,
            "pressing_trigger": "bad_touch",
            "compactness": 2,
            "marking": "mixed",
            "tackling_aggression": 1,
            "offside_trap": 0,
        },
        "goalkeeper_distribution": {
            "distribution_target": "center_backs",
            "distribution_length": "short",
            "release_speed": "balanced",
        },
    },
}


def _lineup_score(player: Player) -> float:
    """阵容评分，与 TacticsService 保持一致"""
    form_bonus = {
        "HOT": 4.0,
        "GOOD": 2.0,
        "NEUTRAL": 0.0,
        "LOW": -4.0,
    }.get(str(getattr(player.match_form, "value", player.match_form)), 0.0)
    fitness = float(player.fitness or 100)
    fitness_bonus = max(-8.0, min(3.0, (fitness - 82.0) * 0.18))
    state_bonus = float(player.state_score or 0) * 1.15
    rust_penalty = float(player.match_rust_score or 0) * 0.25
    return float(player.ovr) + form_bonus + fitness_bonus + state_bonus - rust_penalty


def _can_form_fulfill(players: list[Player], formation_id: str) -> bool:
    """检查阵容是否能满足阵型最低位置要求"""
    requirements = FORMATION_REQUIREMENTS.get(formation_id, FORMATION_REQUIREMENTS["F01"])
    counts = {
        PlayerPosition.GK: sum(1 for p in players if p.position == PlayerPosition.GK),
        PlayerPosition.DF: sum(1 for p in players if p.position == PlayerPosition.DF),
        PlayerPosition.MF: sum(1 for p in players if p.position == PlayerPosition.MF),
        PlayerPosition.FW: sum(1 for p in players if p.position == PlayerPosition.FW),
    }
    if counts[PlayerPosition.GK] < 1:
        return False
    for position, required in requirements.items():
        if counts[position] < required:
            return False
    return True


def _choose_ai_formation(players: list[Player], style: str) -> str:
    """根据 AI 风格和阵容选择可用阵型"""
    profile = STYLE_TACTICS_PROFILE.get(style, STYLE_TACTICS_PROFILE["balanced"])
    primary = profile["formation"]
    fallback = profile["fallback_formation"]

    if _can_form_fulfill(players, primary):
        return primary
    if _can_form_fulfill(players, fallback):
        return fallback

    # 兜底：选择第一个能满足的阵型
    for formation_id in FORMATION_REQUIREMENTS:
        if _can_form_fulfill(players, formation_id):
            return formation_id
    return "F01"


def _select_ai_lineup(
    players: list[Player],
    formation_id: str,
    style: str,
) -> tuple[list[Player], list[Player]]:
    """为 AI 球队选择首发，优先按风格偏好微调"""
    starters, bench = auto_select_lineup(players, formation_id)

    # 进攻型风格：优先把速度型球员放边路/前锋
    if style in {"attacking", "physical"}:
        fw_mf = [p for p in players if p.position in {PlayerPosition.FW, PlayerPosition.MF}]
        fast_players = sorted(
            fw_mf,
            key=lambda p: (p.spd + p.acc) / 2 + _lineup_score(p) * 0.5,
            reverse=True,
        )
        fast_ids = {p.id for p in fast_players[:3]}
        # 如果快马在替补，尝试和首发同位置较低分球员交换
        starter_by_pos: dict[PlayerPosition, list[Player]] = {
            PlayerPosition.FW: [],
            PlayerPosition.MF: [],
            PlayerPosition.DF: [],
            PlayerPosition.GK: [],
        }
        for p in starters:
            starter_by_pos[p.position].append(p)

        for fast in fast_players[:3]:
            if fast in starters:
                continue
            same_pos = starter_by_pos.get(fast.position, [])
            if same_pos and _lineup_score(same_pos[-1]) < _lineup_score(fast) + 2:
                # 简单交换：把同位置评分最低的换下来
                same_pos_sorted = sorted(same_pos, key=_lineup_score)
                to_replace = same_pos_sorted[0]
                if fast not in starters:
                    idx = starters.index(to_replace)
                    starters[idx] = fast
                    bench = [p for p in bench if p.id != fast.id]
                    bench.append(to_replace)
                    # 更新缓存
                    starter_by_pos[fast.position] = [p for p in starters if p.position == fast.position]

    return starters[:8], bench[:5]


def _apply_roster_corrections(tactics: dict[str, int], players: list[Player]) -> dict[str, int]:
    """根据阵容短板修正 legacy sliders"""
    corrected = dict(tactics)

    active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
    if not active:
        return corrected

    df_count = sum(1 for p in active if p.position == PlayerPosition.DF)
    fw_count = sum(1 for p in active if p.position == PlayerPosition.FW)
    avg_def = sum(p.defe for p in active) / len(active)
    avg_sta = sum(p.sta for p in active) / len(active)

    # 后卫少或防守弱 -> 降低防线高度和逼抢
    if df_count < 3 or avg_def < 10:
        corrected["defensive_line_height"] = min(corrected["defensive_line_height"], 1)
        corrected["pressing_intensity"] = min(corrected["pressing_intensity"], 2)

    # 前锋少 -> 降低射门心态，避免浪射
    if fw_count < 2:
        corrected["shooting_mentality"] = min(corrected["shooting_mentality"], 2)

    # 体能差 -> 降低高压和节奏
    if avg_sta < 12:
        corrected["pressing_intensity"] = min(corrected["pressing_intensity"], 1)
        corrected["attack_tempo"] = min(corrected["attack_tempo"], 2)

    return corrected


def _apply_team_instructions_corrections(instr: TeamInstructions, players: list[Player]) -> None:
    """根据阵容短板修正阶段化战术指令"""
    active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
    if not active:
        return

    df_count = sum(1 for p in active if p.position == PlayerPosition.DF)
    fw_count = sum(1 for p in active if p.position == PlayerPosition.FW)
    avg_def = sum(p.defe for p in active) / len(active)
    avg_sta = sum(p.sta for p in active) / len(active)

    if df_count < 3 or avg_def < 10:
        instr.out_of_possession.defensive_line_height = min(instr.out_of_possession.defensive_line_height, 1)
        instr.out_of_possession.pressing_intensity = min(instr.out_of_possession.pressing_intensity, 2)
        instr.transition.after_possession_lost = "regroup" if instr.transition.after_possession_lost == "counter_press" else instr.transition.after_possession_lost

    if fw_count < 2:
        instr.in_possession.shooting_frequency = min(instr.in_possession.shooting_frequency, 2)

    if avg_sta < 12:
        instr.out_of_possession.pressing_intensity = min(instr.out_of_possession.pressing_intensity, 1)
        instr.in_possession.tempo = min(instr.in_possession.tempo, 2)
        if instr.transition.after_possession_lost == "counter_press":
            instr.transition.after_possession_lost = "balanced"


def _generate_player_instructions(starters: list[Player]) -> list[PlayerInstruction]:
    """为 AI 首发球员生成默认个人指令"""
    instructions: list[PlayerInstruction] = []
    if not starters:
        return instructions

    # 按位置分组并排序，找出各位置关键球员
    by_position: dict[PlayerPosition, list[Player]] = {}
    for p in starters:
        by_position.setdefault(p.position, []).append(p)

    def avg_attr(player: Player, attrs: list[str]) -> float:
        return sum(getattr(player, a, 10) for a in attrs) / len(attrs)

    for p in starters:
        instr = PlayerInstruction(player_id=p.id)
        pos = p.position

        if pos == PlayerPosition.GK:
            instr.passing_risk = 1
            instr.hold_position = 3
        elif pos == PlayerPosition.FW:
            sho = avg_attr(p, ["sho", "fin", "com"])
            spd = avg_attr(p, ["spd", "acc", "dri"])
            if spd >= 12:
                instr.carry_ball = 3
                instr.forward_runs = 3
            if sho >= 12:
                instr.shooting_frequency = 3
            if p.hea >= 12:
                instr.crossing_frequency = 2
        elif pos == PlayerPosition.MF:
            pas = avg_attr(p, ["pas", "vis", "con", "dec"])
            defe = avg_attr(p, ["defe", "tkl", "pos", "sta"])
            if pas >= 12:
                instr.passing_risk = 1
            if defe >= 12:
                instr.pressing_intensity = 3
                instr.hold_position = 3
            if p.cro >= 12:
                instr.crossing_frequency = 3
        elif pos == PlayerPosition.DF:
            spd = avg_attr(p, ["spd", "acc"])
            defe = avg_attr(p, ["defe", "tkl", "pos", "hea"])
            if spd >= 12:
                instr.carry_ball = 2
                instr.forward_runs = 2
            if defe >= 12:
                instr.pressing_intensity = 3
                instr.hold_position = 3

        # 只保留偏离默认值的指令，减少 payload 体积
        if any(getattr(instr, k) != 2 for k in [
            "carry_ball", "passing_risk", "shooting_frequency", "crossing_frequency",
            "pressing_intensity", "hold_position", "forward_runs"
        ]):
            instructions.append(instr)

    return instructions[:13]


class AITacticsAdvisor:
    """AI 战术顾问"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create_ai_profile(self, team_id: str) -> TeamTrainingAIProfile:
        """获取或创建 AI 训练/战术风格画像"""
        result = await self.db.execute(
            select(TeamTrainingAIProfile).where(TeamTrainingAIProfile.team_id == team_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            styles = list(STYLE_TACTICS_PROFILE.keys())
            style = random.choice(styles)
            profile = TeamTrainingAIProfile(
                team_id=team_id,
                style=style,
                risk_tolerance=round(random.uniform(0.3, 0.7), 2),
                youth_focus=round(random.uniform(0.2, 0.5), 2),
                random_seed=random.randint(0, 10000),
            )
            self.db.add(profile)
            await self.db.flush()
        return profile

    async def generate_default_tactics(self, team_id: str) -> TeamTactics:
        """为 AI 球队生成默认战术方案"""
        # 校验球队存在
        team_result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = team_result.scalar_one_or_none()
        if not team:
            raise ValueError(f"Team not found: {team_id}")

        # 获取或创建 AI 风格画像
        profile = await self._get_or_create_ai_profile(team_id)
        style = profile.style or "balanced"
        style_profile = STYLE_TACTICS_PROFILE.get(style, STYLE_TACTICS_PROFILE["balanced"])

        # 获取可用球员
        result = await self.db.execute(
            select(Player).where(
                Player.team_id == team_id,
                Player.status == PlayerStatus.ACTIVE,
            )
        )
        players = list(result.scalars().all())

        if len(players) < 8:
            logger.warning(f"AI team {team_id} has fewer than 8 active players, creating minimal tactics")
            formation_id = "F01"
            starters_ids: list[str] = []
            bench_ids: list[str] = []
            instructions = TeamInstructions()
        else:
            formation_id = _choose_ai_formation(players, style)
            starters, bench = _select_ai_lineup(players, formation_id, style)
            starters_ids = [p.id for p in starters]
            bench_ids = [p.id for p in bench]

            preset_name = style_profile["preset"]
            legacy = dict(TACTIC_PRESETS.get(preset_name, TACTIC_PRESETS["balanced"]))
            legacy = _apply_roster_corrections(legacy, players)
            instructions = TeamInstructions.from_legacy(TacticsSetup(**legacy))

            # 应用风格画像的阶段化覆盖
            if "in_possession" in style_profile:
                instructions.in_possession = InPossessionInstructions(**style_profile["in_possession"])
            if "transition" in style_profile:
                instructions.transition = TransitionInstructions(**style_profile["transition"])
            if "out_of_possession" in style_profile:
                instructions.out_of_possession = OutOfPossessionInstructions(**style_profile["out_of_possession"])
            if "goalkeeper_distribution" in style_profile:
                instructions.goalkeeper_distribution = GoalkeeperDistributionInstructions(**style_profile["goalkeeper_distribution"])

            _apply_team_instructions_corrections(instructions, players)
            instructions.player_instructions = _generate_player_instructions(starters)
            instructions.situational_rules = _default_situational_rules(style)

        # 创建或更新 team_tactics
        tactics_service = TacticsService(self.db)
        record = await tactics_service.get_by_team_id(team_id)
        if not record:
            record = TeamTactics(team_id=team_id)
            self.db.add(record)

        record.formation_id = formation_id
        record.lineup_player_ids = starters_ids
        record.bench_player_ids = bench_ids
        record.team_instructions = instructions.model_dump()
        record.ai_profile = {
            "style": style,
            "preset": style_profile.get("preset"),
            "attack_route": style_profile.get("in_possession", {}).get("attack_route"),
            "source": "ai_default",
        }
        await self.db.flush()

        logger.info(
            f"[ai-tactics] team={team_id} style={style} formation={formation_id} "
            f"starters={len(starters_ids)} bench={len(bench_ids)}"
        )
        return record

    async def generate_for_all_ai_teams(self) -> dict[str, int]:
        """为所有 AI 球队生成默认战术"""
        from app.models.user import User

        result = await self.db.execute(
            select(Team).join(User, Team.user_id == User.id).where(User.is_ai == True)
        )
        ai_teams = list(result.scalars().all())

        created = 0
        updated = 0
        for team in ai_teams:
            try:
                existing = await self.db.execute(
                    select(TeamTactics).where(TeamTactics.team_id == team.id)
                )
                had_existing = existing.scalar_one_or_none() is not None
                await self.generate_default_tactics(team.id)
                if had_existing:
                    updated += 1
                else:
                    created += 1
            except Exception as exc:
                logger.exception(f"AI tactics generation failed for team {team.id}: {exc}")

        return {"created": created, "updated": updated, "total": len(ai_teams)}
