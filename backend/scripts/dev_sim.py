#!/usr/bin/env python3
"""
Developer simulation CLI.

Examples:
    PYTHONPATH=. python -m scripts.dev_sim status
    PYTHONPATH=. python -m scripts.dev_sim next-event
    PYTHONPATH=. python -m scripts.dev_sim matchday
    PYTHONPATH=. python -m scripts.dev_sim season
    PYTHONPATH=. python -m scripts.dev_sim results --limit 10
"""
import argparse
import asyncio
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import asc, desc, select, func

from app.dependencies import AsyncSessionLocal
from app.core.events import EventStatus
from app.models.events import EventQueue as EventQueueModel
from app.models.match_result import MatchResult
from app.models.season import Fixture, Season, SeasonStatus
from app.models.team import Team
from app.services.match_engine_client import get_match_engine_client
from app.services.season_service import SeasonService


async def main() -> None:
    parser = argparse.ArgumentParser(description="Lightning Super League dev simulation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show engine, season, event, and fixture status")
    next_event = sub.add_parser("next-event", help="Process the next pending event")
    next_event.add_argument("--count", type=int, default=1)
    sub.add_parser("matchday", help="Process events until the next match day finishes")
    season = sub.add_parser("season", help="Process events until season end")
    season.add_argument("--max-events", type=int, default=500)
    results = sub.add_parser("results", help="Show recent finished fixtures")
    results.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    async with AsyncSessionLocal() as db:
        if args.command == "status":
            await show_status(db)
        elif args.command == "next-event":
            for _ in range(args.count):
                result = await process_next_pending(db)
                if result is None:
                    print("No pending events.")
                    break
                await print_event_result(db, result)
        elif args.command == "matchday":
            if not await get_match_engine_client().health_check():
                print("Match engine is not available. Use MATCH_ENGINE_TRANSPORT=process or start it with: make match-engine")
                return
            await run_until(db, stop_events={"match_day"})
        elif args.command == "season":
            if not await get_match_engine_client().health_check():
                print("Match engine is not available. Use MATCH_ENGINE_TRANSPORT=process or start it with: make match-engine")
                return
            await run_until(db, stop_events={"season_end"}, max_events=args.max_events)
        elif args.command == "results":
            await show_results(db, args.limit)


async def show_status(db) -> None:
    engine_ok = await get_match_engine_client().health_check()
    print(f"Match engine: {'OK' if engine_ok else 'DOWN'}")

    result = await db.execute(
        select(Season)
        .where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
        .order_by(desc(Season.season_number))
        .limit(1)
    )
    season = result.scalar_one_or_none()
    if season:
        print(f"Season: #{season.season_number} day {season.current_day}/{season.total_days} ({season.status.value})")
    else:
        print("Season: none ongoing")

    counts = await db.execute(
        select(EventQueueModel.status, func.count()).group_by(EventQueueModel.status)
    )
    print("Events:", " ".join(f"{status}={count}" for status, count in counts.all()) or "none")

    fixture_counts = await db.execute(
        select(Fixture.status, func.count()).group_by(Fixture.status)
    )
    print("Fixtures:", " ".join(f"{status.value if hasattr(status, 'value') else status}={count}" for status, count in fixture_counts.all()) or "none")

    next_event = await peek_next_event(db)
    if next_event:
        print(f"Next event: #{next_event.id} {next_event.event_type} at {next_event.scheduled_at} payload={next_event.payload}")


async def run_until(db, stop_events: set[str], max_events: int = 200) -> None:
    processed = 0
    while processed < max_events:
        result = await process_next_pending(db)
        if result is None:
            print("No pending events.")
            return
        processed += 1
        await print_event_result(db, result)
        if result.get("event") in stop_events:
            return
    print(f"Stopped after {processed} events without reaching {', '.join(stop_events)}.")


async def process_next_pending(db) -> Optional[dict]:
    event = await peek_next_event(db)
    if not event:
        return None
    service = SeasonService(db)
    return await service.process_next_event(now=event.scheduled_at)


async def peek_next_event(db) -> Optional[EventQueueModel]:
    result = await db.execute(
        select(EventQueueModel)
        .where(EventQueueModel.status == EventStatus.PENDING.value)
        .order_by(asc(EventQueueModel.scheduled_at), asc(EventQueueModel.id))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def print_event_result(db, result: dict) -> None:
    event = result.get("event", "unknown")
    if event == "match_day":
        print(f"match_day day={result.get('season_day')} fixtures={result.get('fixtures_processed')}")
        for item in result.get("results", [])[:8]:
            home = await team_name(db, item["home_team"])
            away = await team_name(db, item["away_team"])
            print(f"  {home} {item['home_score']} - {item['away_score']} {away} ({item['type']})")
        if len(result.get("results", [])) > 8:
            print(f"  ... {len(result['results']) - 8} more")
    elif event == "cup_progression":
        print(f"cup_progression after_day={result.get('after_day')} results={result.get('results')}")
    elif event == "season_end":
        print(
            f"season_end season=#{result.get('season_number')} "
            f"-> next season=#{result.get('next_season_number')}"
        )
    else:
        print(f"{event}: {result}")


async def show_results(db, limit: int) -> None:
    result = await db.execute(
        select(Fixture, MatchResult)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .order_by(desc(Fixture.finished_at))
        .limit(limit)
    )
    rows = result.all()
    if not rows:
        print("No finished engine results yet.")
        return
    for fixture, match_result in rows:
        home = await team_name(db, fixture.home_team_id)
        away = await team_name(db, fixture.away_team_id)
        suffix = f" [{match_result.resolution}]"
        if match_result.penalty_score:
            suffix += f" pens {match_result.penalty_score.get('home')}-{match_result.penalty_score.get('away')}"
        print(f"Day {fixture.season_day:>2} {home} {fixture.home_score} - {fixture.away_score} {away}{suffix}")


async def team_name(db, team_id: str) -> str:
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    return team.name if team else team_id[:8]


if __name__ == "__main__":
    asyncio.run(main())
