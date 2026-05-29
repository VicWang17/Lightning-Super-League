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
            async with httpx.AsyncClient(timeout=3.0) as client:
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
            async with httpx.AsyncClient(timeout=60.0) as client:
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
        try:
            completed = subprocess.run(
                ["go", "run", "./cmd/jsonsimulate"],
                cwd=str(self._engine_dir()),
                env=env,
                input=json.dumps(payload),
                text=True,
                capture_output=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise MatchEngineUnavailableError(str(exc)) from exc

        if completed.returncode != 0:
            raise MatchEngineUnavailableError(completed.stderr.strip() or "process engine failed")
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
            "home_team": self._build_team_setup(home_team, home_players, "F01", db),
            "away_team": self._build_team_setup(away_team, away_players, "F01", db),
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

    async def _build_team_setup(self, team: Team, players: list[Player], formation_id: str, db=None) -> dict[str, Any]:
        starters, bench = self._select_lineup(players)
        starter_setups = await asyncio.gather(*[self._player_setup(p, db) for p in starters])
        bench_setups = await asyncio.gather(*[self._player_setup(p, db) for p in bench])
        return {
            "team_id": team.id,
            "name": team.name,
            "formation_id": formation_id,
            "players": list(starter_setups),
            "bench": list(bench_setups),
            "tactics": self._default_tactics(),
        }

    def _select_lineup(self, players: list[Player]) -> tuple[list[Player], list[Player]]:
        active = [p for p in players if getattr(p.status, "value", p.status) == "ACTIVE"]
        pool = active or players
        gks = sorted([p for p in pool if p.position == PlayerPosition.GK], key=lambda p: p.ovr, reverse=True)
        outfield = sorted([p for p in pool if p.position != PlayerPosition.GK], key=lambda p: p.ovr, reverse=True)

        starters: list[Player] = []
        if gks:
            starters.append(gks[0])
        starters.extend(outfield[: 8 - len(starters)])

        if len(starters) < 8:
            remaining = [p for p in pool if p not in starters]
            starters.extend(sorted(remaining, key=lambda p: p.ovr, reverse=True)[: 8 - len(starters)])

        bench = [p for p in sorted(pool, key=lambda p: p.ovr, reverse=True) if p not in starters][:5]
        return starters[:8], bench

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
        
        # 应用状态修正（需要 db session）
        if db is not None:
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

    def _default_tactics(self) -> dict[str, int]:
        return {
            "passing_style": 2,
            "attack_width": 2,
            "attack_tempo": 2,
            "defensive_line_height": 2,
            "crossing_strategy": 2,
            "shooting_mentality": 2,
            "playmaker_focus": 1,
            "pressing_intensity": 2,
            "defensive_compactness": 1,
            "marking_strategy": 0,
            "offside_trap": 0,
            "tackling_aggression": 1,
        }

    def _seed_for_fixture(self, fixture_id: str) -> int:
        digest = hashlib.sha256(fixture_id.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)


match_engine_client: Optional[MatchEngineClient] = None


def get_match_engine_client() -> MatchEngineClient:
    global match_engine_client
    if match_engine_client is None:
        match_engine_client = MatchEngineClient()
    return match_engine_client
