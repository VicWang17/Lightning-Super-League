"""
Virtual-time simulation runner for development and long-flow tests.

The runner owns the test-time loop:
  1. advance the GameClock,
  2. process due persisted events through SeasonService,
  3. report basic invariants.

It deliberately avoids passing an arbitrary event timestamp as "now" unless the
clock has first been advanced to that timestamp.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Optional

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import GameClock, clock as default_clock
from app.core.events import EventStatus
from app.models.events import EventQueue as EventQueueModel
from app.models.match_result import MatchResult
from app.models.season import Fixture, FixtureStatus, Season, SeasonStatus
from app.services.game_clock_state import GameClockStateService
from app.services.season_service import SeasonService


@dataclass
class RunnerResult:
    processed: int = 0
    season_ends: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)
    stopped_reason: str = "completed"


class SimulationRunner:
    """Run the game world using virtual time as the authority."""

    def __init__(
        self,
        db: AsyncSession,
        game_clock: GameClock = default_clock,
        shared_clock: GameClockStateService | None = None,
    ):
        self.db = db
        self.clock = game_clock
        self.shared_clock = shared_clock
        self.service = SeasonService(db)

    async def current_now(self):
        if self.shared_clock:
            current = await self.shared_clock.now()
            self.clock.freeze_at(current)
            return current
        return self.clock.now()

    async def next_pending_event(self) -> Optional[EventQueueModel]:
        result = await self.db.execute(
            select(EventQueueModel)
            .where(EventQueueModel.status == EventStatus.PENDING.value)
            .order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def advance_to_next_event(self) -> Optional[EventQueueModel]:
        event = await self.next_pending_event()
        if event:
            if self.shared_clock:
                await self.shared_clock.advance_to(event.scheduled_at)
                await self.current_now()
            else:
                self.clock.advance_to(event.scheduled_at)
        return event

    async def process_due_events(self, max_events: int = 100) -> RunnerResult:
        result = RunnerResult()
        for _ in range(max_events):
            try:
                now = await self.current_now()
                item = await self.service.process_next_event(now=now)
            except Exception:
                await self.db.commit()
                raise
            if item is None:
                result.stopped_reason = "idle"
                break
            await self.db.commit()
            result.processed += 1
            result.results.append(item)
            if item.get("event") == "season_end":
                result.season_ends += 1
        else:
            result.stopped_reason = "max_events"
        return result

    async def run_next_event_time(self, max_events_at_time: int = 100) -> RunnerResult:
        event = await self.advance_to_next_event()
        if not event:
            return RunnerResult(stopped_reason="no_pending_events")
        return await self.process_due_events(max_events=max_events_at_time)

    async def run_for_virtual_days(
        self,
        days: int,
        step_hours: int = 24,
        max_events_per_step: int = 200,
    ) -> RunnerResult:
        if days <= 0:
            return RunnerResult(stopped_reason="invalid_days")
        if step_hours <= 0:
            raise ValueError("step_hours must be positive")

        total = RunnerResult()
        steps = max(1, (days * 24 + step_hours - 1) // step_hours)
        for _ in range(steps):
            if self.shared_clock:
                now = await self.shared_clock.now()
                await self.shared_clock.freeze_at(now + timedelta(hours=step_hours))
                await self.current_now()
            else:
                self.clock.tick(timedelta(hours=step_hours))
            batch = await self.process_due_events(max_events=max_events_per_step)
            total.processed += batch.processed
            total.season_ends += batch.season_ends
            total.results.extend(batch.results)
            if batch.stopped_reason == "max_events":
                total.stopped_reason = "max_events"
                return total
        total.stopped_reason = "completed"
        return total

    async def run_seasons(self, count: int, max_events: int = 10000) -> RunnerResult:
        total = RunnerResult()
        while total.season_ends < count and total.processed < max_events:
            event = await self.advance_to_next_event()
            if not event:
                total.stopped_reason = "no_pending_events"
                return total

            batch = await self.process_due_events(max_events=200)
            total.processed += batch.processed
            total.season_ends += batch.season_ends
            total.results.extend(batch.results)
            if batch.stopped_reason == "max_events":
                total.stopped_reason = "max_events_at_same_time"
                return total

        total.stopped_reason = "completed" if total.season_ends >= count else "max_events"
        return total

    async def status(self) -> dict[str, Any]:
        season_result = await self.db.execute(
            select(Season)
            .where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
            .order_by(desc(Season.season_number))
            .limit(1)
        )
        season = season_result.scalar_one_or_none()

        event_counts = await self.db.execute(
            select(EventQueueModel.status, func.count()).group_by(EventQueueModel.status)
        )
        fixture_counts = await self.db.execute(
            select(Fixture.status, func.count()).group_by(Fixture.status)
        )
        failed_events = await self.db.execute(
            select(func.count())
            .select_from(EventQueueModel)
            .where(EventQueueModel.status == EventStatus.FAILED.value)
        )
        latest_results = await self.db.execute(
            select(func.count()).select_from(MatchResult)
        )
        next_event = await self.next_pending_event()

        return {
            "clock": await self.shared_clock.status() if self.shared_clock else self.clock.status(),
            "season": {
                "number": season.season_number,
                "day": season.current_day,
                "total_days": season.total_days,
                "status": season.status.value,
            } if season else None,
            "events": {status: count for status, count in event_counts.all()},
            "fixtures": {
                getattr(status, "value", status): count
                for status, count in fixture_counts.all()
            },
            "match_results": latest_results.scalar_one(),
            "failed_events": failed_events.scalar_one(),
            "next_event": {
                "id": next_event.id,
                "type": next_event.event_type,
                "scheduled_at": next_event.scheduled_at.isoformat(),
                "payload": next_event.payload or {},
            } if next_event else None,
        }

    async def recent_results(self, limit: int = 10) -> list[dict[str, Any]]:
        rows = await self.db.execute(
            select(Fixture, MatchResult)
            .join(MatchResult, MatchResult.fixture_id == Fixture.id)
            .order_by(desc(Fixture.finished_at))
            .limit(limit)
        )
        return [
            {
                "day": fixture.season_day,
                "fixture_id": fixture.id,
                "home_team_id": fixture.home_team_id,
                "away_team_id": fixture.away_team_id,
                "home_score": fixture.home_score,
                "away_score": fixture.away_score,
                "type": fixture.fixture_type.value,
                "resolution": match_result.resolution,
            }
            for fixture, match_result in rows.all()
        ]

    async def assert_basic_invariants(self) -> list[str]:
        errors: list[str] = []

        failed = await self.db.execute(
            select(func.count())
            .select_from(EventQueueModel)
            .where(EventQueueModel.status == EventStatus.FAILED.value)
        )
        failed_count = failed.scalar_one()
        if failed_count:
            errors.append(f"failed events: {failed_count}")

        processing = await self.db.execute(
            select(func.count())
            .select_from(EventQueueModel)
            .where(EventQueueModel.status == EventStatus.PROCESSING.value)
        )
        processing_count = processing.scalar_one()
        if processing_count:
            errors.append(f"stuck processing events: {processing_count}")

        bad_finished = await self.db.execute(
            select(func.count())
            .select_from(Fixture)
            .where(Fixture.status == FixtureStatus.FINISHED)
            .where((Fixture.home_score.is_(None)) | (Fixture.away_score.is_(None)))
        )
        bad_finished_count = bad_finished.scalar_one()
        if bad_finished_count:
            errors.append(f"finished fixtures without score: {bad_finished_count}")

        return errors
