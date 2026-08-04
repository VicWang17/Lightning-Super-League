"""
Shared virtual world clock service.

This service is the cross-process clock authority. The old in-memory
``app.core.clock.clock`` remains useful inside a single process, but the API,
console runner, and future workers must read/write this persisted state when
they need to agree on world time.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import KEY_PREFIX, cache_get_json, cache_set_json
from app.models.clock import GameClockState


ClockMode = Literal["realtime", "turbo", "step", "paused"]
GLOBAL_CLOCK_ID = "global"

_CLOCK_CACHE_KEY = f"{KEY_PREFIX}clock:global"
# Cache TTL is a safety net; write methods write through on every mutation.
_CLOCK_CACHE_TTL = 3600


def _serialize_state(state: GameClockState) -> dict:
    return {
        "mode": state.mode,
        "speed": state.speed,
        "virtual_anchor": state.virtual_anchor.isoformat(),
        "real_anchor": state.real_anchor.isoformat(),
    }


def _deserialize_state(data: dict) -> GameClockState:
    """Build a detached (session-free) GameClockState from cached fields.

    compute_now only reads these four fields, so no ORM session is needed.
    """
    return GameClockState(
        id=GLOBAL_CLOCK_ID,
        mode=data["mode"],
        speed=data["speed"],
        virtual_anchor=datetime.fromisoformat(data["virtual_anchor"]),
        real_anchor=datetime.fromisoformat(data["real_anchor"]),
    )


class GameClockStateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_from_db(self) -> GameClockState:
        """Load (or create) the persisted clock state attached to this session."""
        result = await self.db.execute(
            select(GameClockState).where(GameClockState.id == GLOBAL_CLOCK_ID)
        )
        state = result.scalar_one_or_none()
        if state:
            return state

        now = datetime.utcnow()
        state = GameClockState(
            id=GLOBAL_CLOCK_ID,
            mode="realtime",
            speed=1.0,
            virtual_anchor=now,
            real_anchor=now,
        )
        self.db.add(state)
        await self.db.flush()
        return state

    async def get_or_create(self) -> GameClockState:
        """Read-through cache: cached state is returned detached from the session."""
        cached = await cache_get_json(_CLOCK_CACHE_KEY)
        if cached is not None:
            try:
                return _deserialize_state(cached)
            except (KeyError, TypeError, ValueError):
                pass  # fall through to DB on malformed cache

        state = await self._load_from_db()
        await cache_set_json(_CLOCK_CACHE_KEY, _serialize_state(state), _CLOCK_CACHE_TTL)
        return state

    def compute_now(self, state: GameClockState) -> datetime:
        if state.mode == "realtime":
            return datetime.utcnow()
        if state.mode == "turbo":
            elapsed = datetime.utcnow() - state.real_anchor
            return state.virtual_anchor + elapsed * state.speed
        return state.virtual_anchor

    async def now(self) -> datetime:
        return self.compute_now(await self.get_or_create())

    async def status(self) -> dict:
        state = await self.get_or_create()
        return {
            "mode": state.mode,
            "speed": state.speed,
            "virtual_now": self.compute_now(state).isoformat(),
            "virtual_anchor": state.virtual_anchor.isoformat(),
            "real_anchor": state.real_anchor.isoformat(),
        }

    async def set_mode(self, mode: ClockMode, speed: Optional[float] = None) -> GameClockState:
        if mode not in ("realtime", "turbo", "step", "paused"):
            raise ValueError(f"invalid clock mode: {mode}")
        # Write path must use the session-attached state: flushing a detached
        # (cache-built) object would silently skip persisting the mutation.
        state = await self._load_from_db()
        current = self.compute_now(state)
        state.mode = mode
        if speed is not None:
            state.speed = max(0.0, speed)
        state.virtual_anchor = current
        state.real_anchor = datetime.utcnow()
        await self.db.flush()
        await cache_set_json(_CLOCK_CACHE_KEY, _serialize_state(state), _CLOCK_CACHE_TTL)
        return state

    async def advance_to(self, target: datetime) -> GameClockState:
        state = await self._load_from_db()
        current = self.compute_now(state)
        if target < current:
            return state
        state.virtual_anchor = target
        state.real_anchor = datetime.utcnow()
        await self.db.flush()
        await cache_set_json(_CLOCK_CACHE_KEY, _serialize_state(state), _CLOCK_CACHE_TTL)
        return state

    async def freeze_at(self, target: datetime) -> GameClockState:
        state = await self._load_from_db()
        state.mode = "step"
        state.virtual_anchor = target
        state.real_anchor = datetime.utcnow()
        await self.db.flush()
        await cache_set_json(_CLOCK_CACHE_KEY, _serialize_state(state), _CLOCK_CACHE_TTL)
        return state
