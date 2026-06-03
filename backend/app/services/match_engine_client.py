"""
HTTP client and request adapter for the Go match engine.
"""
from __future__ import annotations

import hashlib
import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Any

from app.core.logging import get_logger

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.player import Player, PlayerPosition
from app.models.season import Fixture, FixtureType
from app.models.team import Team
from app.services.player_state_service import PlayerStateService

settings = get_settings()
logger = get_logger("app.match_engine")

FORMATION_REQUIREMENTS: dict[str, dict[PlayerPosition, int]] = {
    "F01": {PlayerPosition.DF: 2, PlayerPosition.MF: 3, PlayerPosition.FW: 2},  # Standard Balance
    "F02": {PlayerPosition.DF: 2, PlayerPosition.MF: 2, PlayerPosition.FW: 3},  # Front Press
    "F03": {PlayerPosition.DF: 1, PlayerPosition.MF: 3, PlayerPosition.FW: 3},  # Attack Storm
    "F04": {PlayerPosition.DF: 3, PlayerPosition.MF: 2, PlayerPosition.FW: 2},  # Iron Wall
    "F05": {PlayerPosition.DF: 1, PlayerPosition.MF: 2, PlayerPosition.FW: 4},  # All Out
    "F06": {PlayerPosition.DF: 3, PlayerPosition.MF: 3, PlayerPosition.FW: 1},  # Deep Defense
    "F07": {PlayerPosition.DF: 2, PlayerPosition.MF: 4, PlayerPosition.FW: 1},  # Diamond Control
    "F08": {PlayerPosition.DF: 1, PlayerPosition.MF: 4, PlayerPosition.FW: 2},  # Dual Wing
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
        "passing_style": 3, "attack_width": 4, "attack_tempo": 4,
        "defensive_line_height": 3, "crossing_strategy": 3, "shooting_mentality": 4,
        "playmaker_focus": 1, "pressing_intensity": 3, "defensive_compactness": 0,
        "marking_strategy": 1, "offside_trap": 1, "tackling_aggression": 2,
    },
}


class MatchEngineUnavailableError(RuntimeError):
    """Raised when the Go match engine cannot be reached."""


class MatchEngineClient:
    """Go match engine HTTP client."""

    def __init__(self):
        self.base_url = settings.MATCH_ENGINE_URL.rstrip("/")
        self.api_key = settings.MATCH_ENGINE_API_KEY
        self.transport = settings.MATCH_ENGINE_TRANSPORT
        self.mode = settings.MATCH_ENGINE_MODE
        self.tick_interval_ms = settings.MATCH_ENGINE_TICK_INTERVAL_MS

    async def health_check(self) -> bool:
        if self.transport == "process":
            return self._engine_dir().exists()
        try:
            async with httpx.AsyncClient(timeout=3.0, trust_env=False) as client:
                response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def simulate_fixture(self, db: AsyncSession, fixture: Fixture) -> dict[str, Any]:
        """Build a frozen fixture snapshot, call Go, and return SimulateResult."""
        payload = await self._build_request(db, fixture)
        return await self.simulate_payload(fixture.id, payload)

    async def simulate_payload(self, fixture_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Call the configured engine with an already built immutable payload."""
        if self.transport == "process":
            return self._simulate_with_process(payload)

        headers = {}
        if self.api_key:
            headers["X-Match-Engine-Key"] = self.api_key

        url = f"{self.base_url}/api/v1/engine/matches/{fixture_id}/start"
        try:
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MatchEngineUnavailableError(str(exc)) from exc

        data = response.json()
        result = data.get("result")
        if not isinstance(result, dict):
            raise MatchEngineUnavailableError("match engine response missing result")
        return result

    async def simulate_fixtures(
        self,
        db: AsyncSession,
        fixtures: list[Fixture],
        concurrency: int = 16,
    ) -> list[dict[str, Any]]:
        """Simulate fixtures while keeping DB reads deterministic.

        SQLAlchemy sessions are not shared concurrently, so payload snapshots are
        built sequentially. HTTP engine calls are then fanned out with a bounded
        semaphore; process transport remains sequential to avoid spawning many Go
        compilers at once.
        """
        payloads = [(fixture.id, await self._build_request(db, fixture)) for fixture in fixtures]
        if self.transport == "process":
            return [self._simulate_with_process(payload) for _, payload in payloads]

        semaphore = asyncio.Semaphore(concurrency)

        async def run_one(fixture_id: str, payload: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                return await self.simulate_payload(fixture_id, payload)

        return await asyncio.gather(*(run_one(fixture_id, payload) for fixture_id, payload in payloads))

    def _simulate_with_process(self, payload: dict[str, Any]) -> dict[str, Any]:
        env = os.environ.copy()
        env.setdefault("GOCACHE", "/private/tmp/go-cache")
        engine_dir = self._engine_dir()
        configured_binary = os.environ.get("MATCH_ENGINE_PROCESS_BINARY")
        binary = Path(configured_binary) if configured_binary else engine_dir / "jsonsimulate"
        commands = [[str(binary)], ["go", "run", "./cmd/jsonsimulate"]] if binary.exists() else [["go", "run", "./cmd/jsonsimulate"]]
        last_error = ""
        completed: subprocess.CompletedProcess[str] | None = None
        for command in commands:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(engine_dir),
                    env=env,
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                last_error = str(exc)
                continue
            if completed.returncode == 0:
                break
            last_error = completed.stderr.strip() or "process engine failed"
            completed = None
        if completed is None:
            raise MatchEngineUnavailableError(last_error or "process engine failed")

        try:
            data = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise MatchEngineUnavailableError(f"invalid process engine JSON: {completed.stdout[:500]}") from exc
        result = data.get("result")
        if not isinstance(result, dict):
            raise MatchEngineUnavailableError("process engine response missing result")
        return result

    def _engine_dir(self) -> Path:
        return Path(__file__).resolve().parents[3] / "match-engine"

    async def _build_request(self, db: AsyncSession, fixture: Fixture) -> dict[str, Any]:
        home_team = await self._get_team(db, fixture.home_team_id)
        away_team = await self._get_team(db, fixture.away_team_id)
        home_players = await self._get_players(db, fixture.home_team_id)
        away_players = await self._get_players(db, fixture.away_team_id)

        requires_winner = fixture.fixture_type in {
            FixtureType.CUP_LIGHTNING_KNOCKOUT,
            FixtureType.CUP_JENNY,
            FixtureType.PLAYOFF,
        }

        return {
            "match_id": fixture.id,
            "home_team": await self._build_team_setup(home_team, home_players, db),
            "away_team": await self._build_team_setup(away_team, away_players, db),
            "home_advantage": True,
            "requires_winner": requires_winner,
            "mode": self.mode,
            "tick_interval_ms": self.tick_interval_ms,
            "seed": self._seed_for_fixture(fixture.id),
        }

    async def _get_team(self, db: AsyncSession, team_id: str) -> Team:
        result = await db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team:
            raise ValueError(f"Team not found: {team_id}")
        return team

    async def _get_players(self, db: AsyncSession, team_id: str) -> list[Player]:
        result = await db.execute(select(Player).where(Player.team_id == team_id))
        players = list(result.scalars().all())
        if len(players) < 8:
            raise ValueError(f"Team {team_id} has fewer than 8 players")
        return players

    async def _build_team_setup(self, team: Team, players: list[Player], db=None) -> dict[str, Any]:
        formation_id = self._choose_formation(players)
        starters, bench = self._select_lineup(players, formation_id)
        starter_setups = await asyncio.gather(*[self._player_setup(p, db) for p in starters])
        bench_setups = await asyncio.gather(*[self._player_setup(p, db) for p in bench])
        return {
            "team_id": team.id,
            "name": team.name,
            "formation_id": formation_id,
            "players": list(starter_setups),
            "bench": list(bench_setups),
            "tactics": self._choose_tactics(formation_id, starters),
        }

    def _select_lineup(self, players: list[Player], formation_id: str) -> tuple[list[Player], list[Player]]:
        active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
        pool = active if len(active) >= 8 else players
        gks = sorted([p for p in pool if p.position == PlayerPosition.GK], key=self._lineup_score, reverse=True)
        outfield = [p for p in pool if p.position != PlayerPosition.GK]

        starters: list[Player] = []
        if gks:
            starters.append(gks[0])

        requirements = FORMATION_REQUIREMENTS.get(formation_id, FORMATION_REQUIREMENTS["F01"])
        for position, required_count in requirements.items():
            candidates = sorted(
                [p for p in outfield if p.position == position and p not in starters],
                key=self._lineup_score,
                reverse=True,
            )
            starters.extend(candidates[:required_count])

        if len(starters) < 8:
            remaining = [p for p in pool if p not in starters]
            starters.extend(sorted(remaining, key=self._lineup_score, reverse=True)[: 8 - len(starters)])

        bench = [p for p in sorted(pool, key=self._lineup_score, reverse=True) if p not in starters][:5]
        return starters[:8], bench

    def _choose_formation(self, players: list[Player]) -> str:
        active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
        pool = active if len(active) >= 8 else players
        outfield = [p for p in pool if p.position != PlayerPosition.GK]
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
                    key=self._lineup_score,
                    reverse=True,
                )
                picked = candidates[:required_count]
                selected.extend(picked)
                score += sum(self._lineup_score(p) for p in picked)
                missing += max(0, required_count - len(picked))

            if len(selected) < 7:
                remaining = [p for p in outfield if p not in selected]
                fill = sorted(remaining, key=self._lineup_score, reverse=True)[: 7 - len(selected)]
                selected.extend(fill)
                score += sum(self._lineup_score(p) * 0.92 for p in fill)

            avg_fitness = self._avg([float(p.fitness or 100) for p in selected])
            avg_state = self._avg([float(p.state_score or 0) for p in selected])
            score -= missing * 18.0
            score += self._formation_style_bonus(formation_id, selected, avg_fitness, avg_state)

            if score > best_score:
                best_score = score
                best_formation = formation_id
        return best_formation

    def _formation_style_bonus(
        self,
        formation_id: str,
        players: list[Player],
        avg_fitness: float,
        avg_state: float,
    ) -> float:
        counts = {
            PlayerPosition.FW: sum(1 for p in players if p.position == PlayerPosition.FW),
            PlayerPosition.MF: sum(1 for p in players if p.position == PlayerPosition.MF),
            PlayerPosition.DF: sum(1 for p in players if p.position == PlayerPosition.DF),
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
        return bonus

    def _lineup_score(self, player: Player) -> float:
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

    async def _player_setup(self, player: Player, db=None) -> dict[str, Any]:
        # 基础属性
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
        stamina = float(player.fitness or 100)
        
        # 应用状态修正（需要 db session）。大规模闭环压测可关闭，避免为每个赛前 payload
        # 重复查询近期比赛状态；赛后状态更新仍由 MatchSimulator 负责。
        apply_player_state = os.environ.get("MATCH_ENGINE_APPLY_PLAYER_STATE", "true").lower()
        if db is not None and apply_player_state not in {"0", "false", "no"}:
            try:
                state_service = PlayerStateService(db)
                setup = await state_service.build_match_player_setup(player)
                # 保留 skills 和其他字段，build_match_player_setup 只返回基础结构
                setup["skills"] = self._skill_names(player.skills or [])
                return setup
            except Exception as exc:
                logger.warning(
                    f"State setup failed for player {player.id}, using raw stats: {exc}"
                )
        
        return {
            "player_id": player.id,
            "name": player.name,
            "position": getattr(player.position, "value", player.position),
            "attributes": base_attributes,
            "skills": self._skill_names(player.skills or []),
            "stamina": stamina,
            "height": player.height,
            "foot": self._foot(player.preferred_foot),
        }

    def _skill_names(self, skills: list[Any]) -> list[str]:
        names = []
        for skill in skills:
            if isinstance(skill, str):
                names.append(skill)
            elif isinstance(skill, dict):
                name = skill.get("skill_id") or skill.get("name") or ""
                quality = skill.get("quality") or skill.get("rarity")
                names.append(f"{name}|{quality}" if name and quality else name)
        return [s for s in names if s]

    def _foot(self, foot: Any) -> str:
        value = getattr(foot, "value", foot)
        mapping = {"LEFT": "left", "RIGHT": "right", "BOTH": "both"}
        return mapping.get(value, "right")

    def _choose_tactics(self, formation_id: str, starters: list[Player]) -> dict[str, int]:
        avg_fitness = self._avg([float(p.fitness or 100) for p in starters])
        avg_state = self._avg([float(p.state_score or 0) for p in starters])

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

    def _avg(self, values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def _seed_for_fixture(self, fixture_id: str) -> int:
        digest = hashlib.sha256(fixture_id.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)


match_engine_client: Optional[MatchEngineClient] = None


def get_match_engine_client() -> MatchEngineClient:
    global match_engine_client
    if match_engine_client is None:
        match_engine_client = MatchEngineClient()
    return match_engine_client
