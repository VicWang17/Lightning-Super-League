#!/usr/bin/env python3
"""
Backfill CUP-scoped records for historical cup fixtures.

Usage (from backend/):
    source .venv/bin/activate
    PYTHONPATH=. python scripts/backfill_cup_records.py
"""
import asyncio
import logging
import sys

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

sys.path.insert(0, ".")

from app.dependencies import AsyncSessionLocal
from app.models.season import Fixture, FixtureStatus
from app.models.match_result import MatchResult
from app.services.record_service import RecordService
from app.services.match_simulator import MatchResult as MatchResultObj

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BATCH_SIZE = 50


async def backfill() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Fixture)
            .where(
                and_(
                    Fixture.status == FixtureStatus.FINISHED,
                    Fixture.cup_competition_id.isnot(None),
                )
            )
            .order_by(Fixture.cup_competition_id, Fixture.scheduled_at)
            .options(selectinload(Fixture.home_team), selectinload(Fixture.away_team))
        )
        fixtures = result.scalars().all()
        logger.info("Found %d finished cup fixtures", len(fixtures))

        processed = 0
        for fixture in fixtures:
            mr_result = await db.execute(
                select(MatchResult).where(MatchResult.fixture_id == fixture.id)
            )
            mr = mr_result.scalar_one_or_none()
            if not mr:
                logger.warning("No match result for fixture %s, skipping", fixture.id)
                continue

            result_obj = MatchResultObj(
                fixture_id=mr.fixture_id,
                home_score=mr.home_score,
                away_score=mr.away_score,
                events=mr.events or [],
                player_stats=mr.player_stats or [],
            )

            # Only generate CUP-scoped records (and other scopes via shared helpers).
            # Career/season records are not re-evaluated because they were already
            # created when the match originally finished.
            await RecordService._check_match_level_records(fixture, db)
            if result_obj.events or result_obj.player_stats:
                await RecordService._check_player_match_records(fixture, result_obj, db)
            await RecordService._check_streak_records(fixture, db)
            if result_obj.player_stats:
                await RecordService._check_player_streaks(fixture, result_obj, db)

            processed += 1
            if processed % BATCH_SIZE == 0:
                await db.commit()
                logger.info("Committed %d/%d fixtures", processed, len(fixtures))

        await db.commit()
        logger.info("Backfill complete: %d fixtures processed", processed)


if __name__ == "__main__":
    asyncio.run(backfill())
