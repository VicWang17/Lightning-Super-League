"""
Tactics service - 球队战术方案业务逻辑
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import TeamTactics, Player, PlayerPosition, PlayerStatus, Team
from app.schemas.tactics import TeamTacticsUpdate, TacticsSetup, TeamInstructions, SetPieceTakers
from app.core.logging import get_logger

logger = get_logger("app.tactics")

FORMATION_REQUIREMENTS: dict[str, dict[PlayerPosition, int]] = {
    "F01": {PlayerPosition.DF: 2, PlayerPosition.MF: 3, PlayerPosition.FW: 2},
    "F02": {PlayerPosition.DF: 2, PlayerPosition.MF: 2, PlayerPosition.FW: 3},
    "F03": {PlayerPosition.DF: 1, PlayerPosition.MF: 3, PlayerPosition.FW: 3},
    "F04": {PlayerPosition.DF: 3, PlayerPosition.MF: 2, PlayerPosition.FW: 2},
    "F05": {PlayerPosition.DF: 1, PlayerPosition.MF: 2, PlayerPosition.FW: 4},
    "F06": {PlayerPosition.DF: 3, PlayerPosition.MF: 3, PlayerPosition.FW: 1},
    "F07": {PlayerPosition.DF: 2, PlayerPosition.MF: 4, PlayerPosition.FW: 1},
    "F08": {PlayerPosition.DF: 1, PlayerPosition.MF: 4, PlayerPosition.FW: 2},
}

TACTIC_PRESETS: dict[str, dict[str, int]] = {
    "balanced": {
        "passing_style": 2, "attack_width": 2, "attack_tempo": 2,
        "defensive_line_height": 2, "crossing_strategy": 2, "shooting_mentality": 2,
        "playmaker_focus": 0, "pressing_intensity": 2, "defensive_compactness": 1,
        "marking_strategy": 0, "offside_trap": 0, "tackling_aggression": 1,
    },
    "high_press": {
        "passing_style": 2, "attack_width": 2, "attack_tempo": 3,
        "defensive_line_height": 4, "crossing_strategy": 2, "shooting_mentality": 3,
        "playmaker_focus": 0, "pressing_intensity": 4, "defensive_compactness": 1,
        "marking_strategy": 2, "offside_trap": 2, "tackling_aggression": 3,
    },
    "possession": {
        "passing_style": 4, "attack_width": 2, "attack_tempo": 1,
        "defensive_line_height": 3, "crossing_strategy": 1, "shooting_mentality": 1,
        "playmaker_focus": 2, "pressing_intensity": 2, "defensive_compactness": 2,
        "marking_strategy": 1, "offside_trap": 1, "tackling_aggression": 1,
    },
    "counter": {
        "passing_style": 1, "attack_width": 2, "attack_tempo": 4,
        "defensive_line_height": 1, "crossing_strategy": 2, "shooting_mentality": 2,
        "playmaker_focus": 0, "pressing_intensity": 1, "defensive_compactness": 2,
        "marking_strategy": 0, "offside_trap": 0, "tackling_aggression": 1,
    },
    "deep_defense": {
        "passing_style": 1, "attack_width": 1, "attack_tempo": 2,
        "defensive_line_height": 0, "crossing_strategy": 2, "shooting_mentality": 2,
        "playmaker_focus": 0, "pressing_intensity": 0, "defensive_compactness": 2,
        "marking_strategy": 0, "offside_trap": 0, "tackling_aggression": 0,
    },
    "wide_attack": {
        "passing_style": 2, "attack_width": 4, "attack_tempo": 2,
        "defensive_line_height": 2, "crossing_strategy": 4, "shooting_mentality": 2,
        "playmaker_focus": 0, "pressing_intensity": 2, "defensive_compactness": 1,
        "marking_strategy": 0, "offside_trap": 0, "tackling_aggression": 1,
    },
    "all_out": {
        "passing_style": 1, "attack_width": 3, "attack_tempo": 4,
        "defensive_line_height": 3, "crossing_strategy": 3, "shooting_mentality": 4,
        "playmaker_focus": 1, "pressing_intensity": 3, "defensive_compactness": 0,
        "marking_strategy": 1, "offside_trap": 1, "tackling_aggression": 2,
    },
}


def _lineup_score(player: Player) -> float:
    """与 MatchEngineClient 保持一致的阵容评分"""
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


def _select_lineup(players: list[Player], formation_id: str) -> tuple[list[Player], list[Player]]:
    """自动选择首发和替补，与 MatchEngineClient 逻辑保持一致"""
    active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
    pool = active
    gks = sorted([p for p in pool if p.position == PlayerPosition.GK], key=_lineup_score, reverse=True)
    outfield = [p for p in pool if p.position != PlayerPosition.GK]

    starters: list[Player] = []
    if gks:
        starters.append(gks[0])

    requirements = FORMATION_REQUIREMENTS.get(formation_id, FORMATION_REQUIREMENTS["F01"])
    for position, required_count in requirements.items():
        candidates = sorted(
            [p for p in outfield if p.position == position and p not in starters],
            key=_lineup_score,
            reverse=True,
        )
        starters.extend(candidates[:required_count])

    if len(starters) < 8:
        remaining = [p for p in pool if p not in starters]
        starters.extend(sorted(remaining, key=_lineup_score, reverse=True)[: 8 - len(starters)])

    bench = [p for p in sorted(pool, key=_lineup_score, reverse=True) if p not in starters][:5]
    return starters[:8], bench


def _choose_formation(players: list[Player]) -> str:
    """根据球员属性自动选择最佳阵型"""
    active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
    outfield = [p for p in active if p.position != PlayerPosition.GK]
    if len(outfield) < 7:
        return "F01"

    best_formation = "F01"
    best_score = float("-inf")

    for formation_id, requirements in FORMATION_REQUIREMENTS.items():
        selected: list[Player] = []
        score = 0.0
        missing = 0
        for position, required_count in requirements.items():
            candidates = sorted(
                [p for p in outfield if p.position == position and p not in selected],
                key=_lineup_score,
                reverse=True,
            )
            picked = candidates[:required_count]
            selected.extend(picked)
            score += sum(_lineup_score(p) for p in picked)
            missing += max(0, required_count - len(picked))

        if len(selected) < 7:
            remaining = [p for p in outfield if p not in selected]
            fill = sorted(remaining, key=_lineup_score, reverse=True)[: 7 - len(selected)]
            selected.extend(fill)
            score += sum(_lineup_score(p) * 0.92 for p in fill)

        avg_fitness = sum(float(p.fitness or 100) for p in selected) / len(selected) if selected else 0
        avg_state = sum(float(p.state_score or 0) for p in selected) / len(selected) if selected else 0
        score -= missing * 18.0

        counts = {
            PlayerPosition.FW: sum(1 for p in selected if p.position == PlayerPosition.FW),
            PlayerPosition.MF: sum(1 for p in selected if p.position == PlayerPosition.MF),
            PlayerPosition.DF: sum(1 for p in selected if p.position == PlayerPosition.DF),
        }
        bonus = 0.0
        if formation_id in {"F02", "F03", "F05", "F08"}:
            bonus += counts[PlayerPosition.FW] * 2.5 + max(avg_state, 0) * 1.5
        if formation_id in {"F04", "F06"}:
            bonus += counts[PlayerPosition.DF] * 2.5
            if avg_fitness < 76:
                bonus += 5.0
        if formation_id == "F07":
            bonus += counts[PlayerPosition.MF] * 2.7
        if formation_id == "F02" and avg_fitness >= 82:
            bonus += 5.0
        if formation_id in {"F03", "F05"} and avg_fitness < 78:
            bonus -= 8.0
        score += bonus

        if score > best_score:
            best_score = score
            best_formation = formation_id

    return best_formation


def _choose_tactics(formation_id: str, starters: list[Player]) -> dict[str, int]:
    """根据阵型和阵容状态选择战术预设"""
    avg_fitness = sum(float(p.fitness or 100) for p in starters) / len(starters) if starters else 100
    avg_state = sum(float(p.state_score or 0) for p in starters) / len(starters) if starters else 0

    if formation_id == "F02" and avg_fitness >= 80:
        preset = "high_press"
    elif formation_id in {"F03", "F05"} and avg_state >= -1:
        preset = "all_out" if formation_id == "F05" else "high_press"
    elif formation_id in {"F04", "F06"}:
        preset = "deep_defense" if avg_fitness < 80 else "counter"
    elif formation_id == "F07":
        preset = "possession"
    elif formation_id == "F08":
        preset = "wide_attack"
    else:
        preset = "balanced"

    tactics = dict(TACTIC_PRESETS[preset])
    if avg_fitness < 72:
        tactics["pressing_intensity"] = min(tactics["pressing_intensity"], 1)
        tactics["defensive_line_height"] = min(tactics["defensive_line_height"], 1)
        tactics["attack_tempo"] = min(tactics["attack_tempo"], 2)
        tactics["defensive_compactness"] = 2
    elif avg_state >= 3:
        tactics["shooting_mentality"] = min(4, tactics["shooting_mentality"] + 1)
        tactics["pressing_intensity"] = min(4, tactics["pressing_intensity"] + 1)
    elif avg_state <= -3:
        tactics["shooting_mentality"] = max(1, tactics["shooting_mentality"] - 1)
        tactics["defensive_compactness"] = min(2, tactics["defensive_compactness"] + 1)
    return tactics


def _set_piece_score(player: Player, kind: str) -> float:
    """根据场景计算球员定位球能力分。"""
    if kind == "penalty":
        return player.pk * 0.6 + player.com * 0.25 + player.sho * 0.15
    if kind == "free_kick":
        return player.fk * 0.6 + player.sho * 0.2 + player.pas * 0.15 + player.com * 0.05
    if kind == "corner":
        return player.cro * 0.5 + player.pas * 0.3 + player.fk * 0.1 + player.vis * 0.1
    return float(player.ovr)


def _build_default_set_piece_takers(players: list[Player]) -> dict:
    """为球队生成默认定位球主罚手排序，排除 GK。"""
    outfield = [p for p in players if p.position != PlayerPosition.GK]
    return {
        "penalty": [p.id for p in sorted(outfield, key=lambda p: _set_piece_score(p, "penalty"), reverse=True)[:3]],
        "free_kick": [p.id for p in sorted(outfield, key=lambda p: _set_piece_score(p, "free_kick"), reverse=True)[:3]],
        "corner": [p.id for p in sorted(outfield, key=lambda p: _set_piece_score(p, "corner"), reverse=True)[:3]],
    }


def _normalize_team_instructions(value: dict | None) -> dict:
    """将 V1 或空记录转换为 V2 TeamInstructions 字典；任何异常都回退到默认"""
    try:
        if not value:
            return TeamInstructions().model_dump()
        # V2 记录包含阶段化字段
        if "in_possession" in value:
            # 尝试反序列化以剔除损坏字段，失败则回退
            return TeamInstructions.model_validate(value).model_dump()
        # V1 记录只有 12 条 legacy sliders
        legacy = TacticsSetup.model_validate(value)
        return TeamInstructions.from_legacy(legacy).model_dump()
    except Exception:
        logger.warning("team_instructions 损坏或无法识别，回退到默认战术")
        return TeamInstructions().model_dump()


class TacticsService:
    """球队战术方案服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_team_id(self, team_id: str) -> Optional[TeamTactics]:
        """根据球队 ID 查询战术方案"""
        result = await self.db.execute(
            select(TeamTactics).where(TeamTactics.team_id == team_id)
        )
        record = result.scalar_one_or_none()
        if record is not None:
            record.team_instructions = _normalize_team_instructions(record.team_instructions)
            record.set_piece_takers = await self._ensure_set_piece_takers(record)
        return record

    async def _ensure_set_piece_takers(self, record: TeamTactics) -> dict:
        """确保 set_piece_takers 合法且有默认值；剔除离队/不可用/GK 球员。"""
        result = await self.db.execute(
            select(Player).where(
                Player.team_id == record.team_id,
                Player.status == PlayerStatus.ACTIVE,
            )
        )
        players = list(result.scalars().all())
        outfield = [p for p in players if p.position != PlayerPosition.GK]
        valid_ids = {p.id for p in players}

        raw = record.set_piece_takers or {}
        kinds = ["penalty", "free_kick", "corner"]
        cleaned: dict[str, list[str]] = {}
        changed = False

        for kind in kinds:
            ordered = [pid for pid in raw.get(kind, []) if pid in valid_ids]
            ordered = [pid for pid in ordered if next((p for p in players if p.id == pid), None).position != PlayerPosition.GK]
            # 补齐到 3 人
            for p in sorted(outfield, key=lambda p, k=kind: _set_piece_score(p, k), reverse=True):
                if p.id not in ordered and len(ordered) < 3:
                    ordered.append(p.id)
                    changed = True
            cleaned[kind] = ordered
            if ordered != raw.get(kind, []):
                changed = True

        if changed or not raw:
            record.set_piece_takers = cleaned
            await self.db.flush()
        return cleaned

    async def get_or_create_default(self, team_id: str) -> TeamTactics:
        """获取或创建默认战术方案"""
        record = await self.get_by_team_id(team_id)
        if record:
            return record

        # 获取球队球员
        result = await self.db.execute(
            select(Player).where(
                Player.team_id == team_id,
                Player.status == PlayerStatus.ACTIVE,
            )
        )
        players = list(result.scalars().all())

        if len(players) < 8:
            logger.warning(f"Team {team_id} has fewer than 8 active players, creating empty tactics")
            formation_id = "F01"
            starters_ids: list[str] = []
            bench_ids: list[str] = []
        else:
            formation_id = _choose_formation(players)
            starters, bench = _select_lineup(players, formation_id)
            starters_ids = [p.id for p in starters]
            bench_ids = [p.id for p in bench]

        legacy_tactics = _choose_tactics(formation_id, players[:8])
        team_instructions = TeamInstructions.from_legacy(TacticsSetup.model_validate(legacy_tactics))

        record = TeamTactics(
            team_id=team_id,
            formation_id=formation_id,
            lineup_player_ids=starters_ids,
            bench_player_ids=bench_ids,
            team_instructions=team_instructions.model_dump(),
            set_piece_takers=_build_default_set_piece_takers(players),
            set_piece_instructions={},
            substitution_rules={},
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def update(self, team_id: str, data: TeamTacticsUpdate) -> TeamTactics:
        """更新球队战术方案"""
        record = await self.get_by_team_id(team_id)
        if not record:
            record = TeamTactics(team_id=team_id)
            self.db.add(record)

        # 校验个人指令中的球员是否属于本队
        instruction_player_ids = [instr.player_id for instr in data.team_instructions.player_instructions]
        if instruction_player_ids:
            _, errors = await self.validate_players(team_id, instruction_player_ids)
            if errors:
                raise ValueError(f"个人指令校验失败: {'; '.join(errors)}")

        # 校验定位球主罚手
        takers_data = data.set_piece_takers.model_dump()
        cleaned_takers: dict[str, list[str]] = {}
        taker_player_ids: list[str] = []
        for kind in ("penalty", "free_kick", "corner"):
            ids = [pid for pid in takers_data.get(kind, []) if pid]
            cleaned_takers[kind] = ids[:3]
            taker_player_ids.extend(ids[:3])
        if taker_player_ids:
            valid_players, errors = await self.validate_players(team_id, taker_player_ids)
            if errors:
                raise ValueError(f"定位球主罚手校验失败: {'; '.join(errors)}")
            found = {p.id: p for p in valid_players}
            gk_ids = [pid for pid in taker_player_ids if found.get(pid) and found[pid].position == PlayerPosition.GK]
            if gk_ids:
                raise ValueError("门将不能担任定位球主罚手")

        record.formation_id = data.formation_id
        record.lineup_player_ids = list(data.lineup_player_ids)
        record.bench_player_ids = list(data.bench_player_ids)
        record.team_instructions = data.team_instructions.model_dump()
        record.set_piece_takers = cleaned_takers
        record.set_piece_instructions = dict(data.set_piece_instructions or {})
        record.substitution_rules = dict(data.substitution_rules or {})
        await self.db.flush()
        return record

    async def validate_players(
        self,
        team_id: str,
        player_ids: list[str],
    ) -> tuple[list[Player], list[str]]:
        """校验球员是否都属于指定球队且状态 ACTIVE

        返回：(合法球员列表, 错误信息列表)
        """
        errors: list[str] = []
        if not player_ids:
            return [], errors

        result = await self.db.execute(
            select(Player).where(
                Player.id.in_(player_ids),
                Player.team_id == team_id,
                Player.status == PlayerStatus.ACTIVE,
            )
        )
        found = {p.id: p for p in result.scalars().all()}

        valid_players: list[Player] = []
        for pid in player_ids:
            if pid not in found:
                errors.append(f"球员 {pid} 不存在、不属于本队或不可用")
            else:
                valid_players.append(found[pid])

        return valid_players, errors

    async def validate_formation(
        self,
        formation_id: str,
        lineup_players: list[Player],
    ) -> list[str]:
        """校验阵型：只检查是否存在以及有且仅有 1 名门将。

        游戏中位置只是模板，MF/DF/FW 可以互相客串，因此不再强制各位置人数。
        """
        errors: list[str] = []
        if formation_id not in FORMATION_REQUIREMENTS:
            errors.append(f"未知阵型: {formation_id}")
            return errors

        gk_count = sum(1 for p in lineup_players if p.position == PlayerPosition.GK)
        if gk_count != 1:
            errors.append(f"阵型 {formation_id} 需要 1 名门将，当前 {gk_count} 人")

        return errors
