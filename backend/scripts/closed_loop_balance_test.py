#!/usr/bin/env python3
"""
Closed-loop multi-season balance test.

This script is intentionally backend-only. It advances the virtual world through
SimulationRunner, captures roster/economy/youth/draft/free-market metrics, and
exports machine-readable logs plus a compact markdown report.

Usage:
    PYTHONPATH=. MATCH_ENGINE_TRANSPORT=process MATCH_ENGINE_MODE=instant \
      python -m scripts.closed_loop_balance_test --seasons 3

    PYTHONPATH=. python -m scripts.closed_loop_balance_test --seasons 0 --out reports/audit
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import and_, desc, func, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.dependencies import AsyncSessionLocal, engine  # noqa: E402
from app.models import (  # noqa: E402
    AcademyPlayerStatus,
    DraftPool,
    DraftPoolPlayer,
    DraftPoolPlayerStatus,
    DraftSelection,
    DraftSelectionStatus,
    EventQueue,
    FinanceTransaction,
    FreeAgentListing,
    League,
    LeagueStanding,
    ListingStatus,
    OriginType,
    Player,
    PlayerContract,
    PlayerSeasonStats,
    PlayerStatus,
    Season,
    SeasonStatus,
    Team,
    TeamSeasonFinance,
    User,
    YouthAcademyPlayer,
)
from app.core.events import EventStatus  # noqa: E402
from app.models.player_contract import ContractStatus  # noqa: E402
from app.services.simulation_runner import SimulationRunner  # noqa: E402


ACTIVE_ROSTER_STATUSES = [
    PlayerStatus.ACTIVE,
    PlayerStatus.INJURED,
    PlayerStatus.SUSPENDED,
]


@dataclass
class SeasonSummary:
    season_number: int
    season_id: str
    event_status: str = "ok"
    processed_events: int = 0
    failed_events_total: int = 0
    teams_total: int = 0
    teams_below_8: int = 0
    teams_above_15: int = 0
    roster_min: int = 0
    roster_max: int = 0
    roster_avg: float = 0.0
    contracts_created: int = 0
    renewals_or_recontracts: int = 0
    rookie_contracts_created: int = 0
    contracts_expired_active_now: int = 0
    retired_players: int = 0
    free_agent_listings_created: int = 0
    free_agent_active: int = 0
    free_agent_signed: int = 0
    youth_generated: int = 0
    youth_in_academy: int = 0
    youth_signed: int = 0
    youth_released_to_draft: int = 0
    youth_drafted: int = 0
    youth_free_market: int = 0
    draft_pools: int = 0
    draft_pool_players: int = 0
    draft_selections_pending: int = 0
    draft_selections_signed: int = 0
    draft_selections_declined: int = 0
    draft_selections_expired: int = 0
    draft_selections_skipped_roster_full: int = 0
    auto_fill_players_joined: int = 0
    academy_players_joined: int = 0
    draft_players_joined: int = 0
    free_market_players_joined: int = 0
    avg_wage_pressure_pct: float = 0.0
    max_wage_pressure_pct: float = 0.0
    teams_over_wage_cap: int = 0
    min_balance: float = 0.0
    avg_balance: float = 0.0
    invariants_failed: int = 0
    warnings: str = ""


@dataclass
class RunArtifacts:
    out_dir: Path
    season_rows: list[dict[str, Any]] = field(default_factory=list)
    team_rows: list[dict[str, Any]] = field(default_factory=list)
    player_rows: list[dict[str, Any]] = field(default_factory=list)
    event_rows: list[dict[str, Any]] = field(default_factory=list)
    invariant_rows: list[dict[str, Any]] = field(default_factory=list)


def enum_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def decimal_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def avg(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    mx = avg(xs)
    my = avg(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if dx == 0 or dy == 0:
        return None
    return numerator / (dx * dy)


def gini(values: list[float]) -> float | None:
    values = sorted(v for v in values if v >= 0)
    if not values:
        return None
    total = sum(values)
    if total == 0:
        return 0.0
    weighted = sum((idx + 1) * value for idx, value in enumerate(values))
    return (2 * weighted) / (len(values) * total) - (len(values) + 1) / len(values)


async def latest_finished_season(db) -> Season | None:
    result = await db.execute(
        select(Season)
        .where(Season.status == SeasonStatus.FINISHED)
        .order_by(desc(Season.season_number))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def current_or_latest_season(db) -> Season | None:
    result = await db.execute(
        select(Season)
        .where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
        .order_by(desc(Season.season_number))
        .limit(1)
    )
    season = result.scalar_one_or_none()
    if season:
        return season
    return await latest_finished_season(db)


async def count_rows(db, model, *criteria) -> int:
    result = await db.execute(select(func.count()).select_from(model).where(*criteria))
    return int(result.scalar_one() or 0)


async def count_grouped(db, field, model, *criteria) -> dict[str, int]:
    result = await db.execute(
        select(field, func.count()).select_from(model).where(*criteria).group_by(field)
    )
    return {enum_value(key): int(count) for key, count in result.all()}


async def collect_roster_counts(db) -> dict[str, int]:
    teams = (await db.execute(select(Team.id))).scalars().all()
    counts: dict[str, int] = {}
    for team_id in teams:
        counts[team_id] = await count_rows(
            db,
            Player,
            Player.team_id == team_id,
            Player.status.in_(ACTIVE_ROSTER_STATUSES),
        )
    return counts


async def collect_season_summary(db, season: Season, processed_events: int, event_status: str) -> SeasonSummary:
    roster_counts = await collect_roster_counts(db)
    roster_values = list(roster_counts.values())

    contracts = (
        await db.execute(select(PlayerContract).where(PlayerContract.season_id == season.id))
    ).scalars().all()
    previous_contract_counts: Counter[str] = Counter()
    if contracts:
        player_ids = [contract.player_id for contract in contracts]
        previous = await db.execute(
            select(PlayerContract.player_id, func.count())
            .where(PlayerContract.player_id.in_(player_ids))
            .where(PlayerContract.start_season_number < season.season_number)
            .group_by(PlayerContract.player_id)
        )
        previous_contract_counts.update({pid: int(count) for pid, count in previous.all()})

    youth_counts = await count_grouped(
        db, YouthAcademyPlayer.status, YouthAcademyPlayer, YouthAcademyPlayer.season_id == season.id
    )
    selection_counts = await count_grouped(
        db, DraftSelection.status, DraftSelection, DraftSelection.season_id == season.id
    )
    listing_counts = await count_grouped(
        db, FreeAgentListing.status, FreeAgentListing, FreeAgentListing.season_id == season.id
    )

    joined_counts = await count_grouped(
        db,
        Player.origin_type,
        Player,
        Player.joined_first_team_season == season.season_number,
    )

    finances = (
        await db.execute(select(TeamSeasonFinance).where(TeamSeasonFinance.season_id == season.id))
    ).scalars().all()
    wage_pressures = []
    balances = []
    over_cap = 0
    for finance in finances:
        cap = decimal_float(finance.wage_cap)
        bill = decimal_float(finance.wage_bill)
        if cap > 0:
            pressure = bill / cap * 100
            wage_pressures.append(pressure)
            if bill > cap:
                over_cap += 1
        balances.append(decimal_float(finance.current_balance))

    failed_events = await count_rows(
        db, EventQueue, EventQueue.status == EventStatus.FAILED.value
    )

    summary = SeasonSummary(
        season_number=season.season_number,
        season_id=season.id,
        event_status=event_status,
        processed_events=processed_events,
        failed_events_total=failed_events,
        teams_total=len(roster_values),
        teams_below_8=sum(1 for count in roster_values if count < 8),
        teams_above_15=sum(1 for count in roster_values if count > 15),
        roster_min=min(roster_values) if roster_values else 0,
        roster_max=max(roster_values) if roster_values else 0,
        roster_avg=round(avg(roster_values), 2),
        contracts_created=len(contracts),
        renewals_or_recontracts=sum(1 for contract in contracts if previous_contract_counts[contract.player_id] > 0),
        rookie_contracts_created=sum(1 for contract in contracts if enum_value(contract.contract_type) == "ROOKIE"),
        contracts_expired_active_now=sum(1 for contract in contracts if contract.status == ContractStatus.EXPIRED),
        retired_players=await count_rows(
            db, Player, Player.status == PlayerStatus.RETIRED, Player.retired_at_season == season.season_number
        ),
        free_agent_listings_created=await count_rows(
            db, FreeAgentListing, FreeAgentListing.season_id == season.id
        ),
        free_agent_active=listing_counts.get("active", 0),
        free_agent_signed=listing_counts.get("signed", 0),
        youth_generated=await count_rows(
            db, YouthAcademyPlayer, YouthAcademyPlayer.season_id == season.id
        ),
        youth_in_academy=youth_counts.get("in_academy", 0),
        youth_signed=youth_counts.get("signed", 0),
        youth_released_to_draft=youth_counts.get("released_to_draft", 0),
        youth_drafted=youth_counts.get("drafted", 0),
        youth_free_market=youth_counts.get("free_market", 0),
        draft_pools=await count_rows(db, DraftPool, DraftPool.season_id == season.id),
        draft_pool_players=await count_rows(db, DraftPoolPlayer, DraftPoolPlayer.draft_pool_id.in_(
            select(DraftPool.id).where(DraftPool.season_id == season.id)
        )),
        draft_selections_pending=selection_counts.get("pending", 0),
        draft_selections_signed=selection_counts.get("signed", 0),
        draft_selections_declined=selection_counts.get("declined", 0),
        draft_selections_expired=selection_counts.get("expired", 0),
        draft_selections_skipped_roster_full=selection_counts.get("skipped_roster_full", 0),
        auto_fill_players_joined=joined_counts.get("auto_fill", 0),
        academy_players_joined=joined_counts.get("academy", 0),
        draft_players_joined=joined_counts.get("draft", 0),
        free_market_players_joined=joined_counts.get("free_market", 0),
        avg_wage_pressure_pct=round(avg(wage_pressures), 2),
        max_wage_pressure_pct=round(max(wage_pressures), 2) if wage_pressures else 0.0,
        teams_over_wage_cap=over_cap,
        min_balance=round(min(balances), 2) if balances else 0.0,
        avg_balance=round(avg(balances), 2),
    )
    return summary


async def collect_team_rows(db, season: Season) -> list[dict[str, Any]]:
    standings = await db.execute(
        select(LeagueStanding, League)
        .join(League, LeagueStanding.league_id == League.id)
        .where(LeagueStanding.season_id == season.id)
    )
    standing_by_team = {standing.team_id: (standing, league) for standing, league in standings.all()}

    finance_rows = (
        await db.execute(select(TeamSeasonFinance).where(TeamSeasonFinance.season_id == season.id))
    ).scalars().all()
    finance_by_team = {finance.team_id: finance for finance in finance_rows}

    teams = (
        await db.execute(select(Team, User).join(User, Team.user_id == User.id))
    ).all()

    rows: list[dict[str, Any]] = []
    for team, user in teams:
        players = (
            await db.execute(
                select(Player)
                .where(Player.team_id == team.id)
                .where(Player.status.in_(ACTIVE_ROSTER_STATUSES))
            )
        ).scalars().all()
        ovrs = sorted([player.ovr for player in players], reverse=True)

        contracts = (
            await db.execute(
                select(PlayerContract, Player)
                .join(Player, PlayerContract.player_id == Player.id)
                .where(PlayerContract.season_id == season.id)
                .where(PlayerContract.team_id == team.id)
            )
        ).all()
        origin_counts = Counter(enum_value(player.origin_type) for _, player in contracts)
        rookie_contracts = sum(1 for contract, _ in contracts if enum_value(contract.contract_type) == "ROOKIE")

        standing, league = standing_by_team.get(team.id, (None, None))
        finance = finance_by_team.get(team.id)
        cap = decimal_float(finance.wage_cap) if finance else 0.0
        bill = decimal_float(finance.wage_bill) if finance else 0.0

        rows.append({
            "season_number": season.season_number,
            "season_id": season.id,
            "team_id": team.id,
            "team_name": team.name,
            "is_ai": bool(user.is_ai),
            "league_id": standing.league_id if standing else team.current_league_id,
            "league_level": league.level if league else "",
            "position": standing.position if standing else "",
            "points": standing.points if standing else "",
            "played": standing.played if standing else "",
            "won": standing.won if standing else "",
            "drawn": standing.drawn if standing else "",
            "lost": standing.lost if standing else "",
            "goals_for": standing.goals_for if standing else "",
            "goals_against": standing.goals_against if standing else "",
            "goal_difference": standing.goal_difference if standing else "",
            "roster_count": len(players),
            "avg_ovr": round(avg(ovrs), 2),
            "top8_ovr": round(avg(ovrs[:8]), 2),
            "max_ovr": max(ovrs) if ovrs else 0,
            "contracts_signed": len(contracts),
            "rookie_contracts": rookie_contracts,
            "academy_signings": origin_counts.get("academy", 0),
            "draft_signings": origin_counts.get("draft", 0),
            "free_market_signings": origin_counts.get("free_market", 0),
            "auto_fill_signings": origin_counts.get("auto_fill", 0),
            "wage_cap": round(cap, 2),
            "wage_bill": round(bill, 2),
            "wage_pressure_pct": round(bill / cap * 100, 2) if cap > 0 else 0.0,
            "balance": round(decimal_float(finance.current_balance), 2) if finance else 0.0,
            "financial_health": enum_value(finance.financial_health) if finance else "",
            "overspend_level": enum_value(finance.overspend_level) if finance else "",
        })
    return rows


async def collect_player_rows(db, season: Season) -> list[dict[str, Any]]:
    stats = (
        await db.execute(
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(PlayerSeasonStats.season_id == season.id)
        )
    ).all()
    aggregate: dict[str, dict[str, Any]] = {}
    for row, player in stats:
        item = aggregate.setdefault(
            player.id,
            {
                "season_number": season.season_number,
                "season_id": season.id,
                "player_id": player.id,
                "player_name": player.name,
                "team_id": row.team_id,
                "position": enum_value(player.position),
                "age": season.season_number + abs(player.birth_offset),
                "ovr": player.ovr,
                "potential": enum_value(player.potential_letter),
                "origin_type": enum_value(player.origin_type),
                "wage": decimal_float(player.wage),
                "matches": 0,
                "goals": 0,
                "assists": 0,
                "rating_weighted": 0.0,
            },
        )
        matches = int(row.matches_played or 0)
        item["matches"] += matches
        item["goals"] += int(row.goals or 0)
        item["assists"] += int(row.assists or 0)
        item["rating_weighted"] += decimal_float(row.average_rating) * max(matches, 1)

    rows = []
    for item in aggregate.values():
        denominator = max(int(item["matches"]), 1)
        item["average_rating"] = round(item.pop("rating_weighted") / denominator, 2)
        rows.append(item)
    return rows


async def collect_invariants(db, season: Season | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(name: str, severity: str, count: int, detail: str) -> None:
        if count:
            rows.append({
                "season_number": season.season_number if season else "",
                "season_id": season.id if season else "",
                "severity": severity,
                "name": name,
                "count": count,
                "detail": detail,
            })

    roster_counts = await collect_roster_counts(db)
    add("teams_below_8", "error", sum(1 for c in roster_counts.values() if c < 8), "team active roster below minimum")
    add("teams_above_15", "error", sum(1 for c in roster_counts.values() if c > 15), "team active roster above maximum")

    failed = await count_rows(db, EventQueue, EventQueue.status == EventStatus.FAILED.value)
    add("failed_events", "error", failed, "event queue has failed events")

    stuck = await count_rows(db, EventQueue, EventQueue.status == EventStatus.PROCESSING.value)
    add("processing_events", "error", stuck, "event queue has stuck processing events")

    retired_on_roster = await count_rows(
        db, Player, Player.status == PlayerStatus.RETIRED, Player.team_id.isnot(None)
    )
    add("retired_players_on_roster", "error", retired_on_roster, "retired player still belongs to a team")

    active_listing_bad_player = await db.execute(
        select(func.count())
        .select_from(FreeAgentListing)
        .join(Player, FreeAgentListing.player_id == Player.id)
        .where(FreeAgentListing.status == ListingStatus.ACTIVE)
        .where((Player.team_id.isnot(None)) | (Player.status == PlayerStatus.RETIRED))
    )
    add("bad_active_free_agent_listing", "error", int(active_listing_bad_player.scalar_one() or 0), "active listing points to signed or retired player")

    old_pending = await count_rows(
        db,
        DraftSelection,
        DraftSelection.status == DraftSelectionStatus.PENDING,
        DraftSelection.expires_at.isnot(None),
        DraftSelection.expires_at < datetime.utcnow(),
    )
    add("expired_pending_draft_selections", "warning", old_pending, "draft selection pending after 24h window")

    duplicate_active_contracts = await db.execute(
        select(PlayerContract.player_id, func.count())
        .where(PlayerContract.status == ContractStatus.ACTIVE)
        .group_by(PlayerContract.player_id)
        .having(func.count() > 1)
    )
    duplicate_count = len(duplicate_active_contracts.all())
    add("duplicate_active_contracts", "error", duplicate_count, "player has more than one active contract")

    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def add_event_rows(artifacts: RunArtifacts, season_loop_index: int, event_results: list[dict[str, Any]]) -> None:
    for index, item in enumerate(event_results, 1):
        artifacts.event_rows.append({
            "loop_index": season_loop_index,
            "event_index": index,
            "event": item.get("event"),
            "season_id": item.get("season_id"),
            "payload": item,
        })


def build_report(artifacts: RunArtifacts) -> str:
    season_rows = artifacts.season_rows
    team_rows = artifacts.team_rows
    player_rows = artifacts.player_rows
    invariant_rows = artifacts.invariant_rows

    top_level_team_rows = [
        row for row in team_rows
        if row.get("league_level") not in ("", None)
    ]
    points_rows = [row for row in top_level_team_rows if row.get("points") not in ("", None)]

    corr_top8_points = pearson(
        [float(row["top8_ovr"]) for row in points_rows],
        [float(row["points"]) for row in points_rows],
    )
    corr_wage_points = pearson(
        [float(row["wage_bill"]) for row in points_rows],
        [float(row["points"]) for row in points_rows],
    )
    corr_max_points = pearson(
        [float(row["max_ovr"]) for row in points_rows],
        [float(row["points"]) for row in points_rows],
    )
    rated_players = [row for row in player_rows if int(row.get("matches") or 0) >= 5]
    corr_ovr_rating = pearson(
        [float(row["ovr"]) for row in rated_players],
        [float(row["average_rating"]) for row in rated_players],
    )

    latest_season_number = max((int(row["season_number"]) for row in season_rows), default=0)
    latest_team_rows = [row for row in team_rows if int(row["season_number"]) == latest_season_number]
    balance_gini = gini([float(row["balance"]) for row in latest_team_rows])
    top8_gini = gini([float(row["top8_ovr"]) for row in latest_team_rows])

    champion_relegations = count_champion_relegations(team_rows)
    repeat_champions = count_repeat_champions(team_rows)

    errors = [row for row in invariant_rows if row.get("severity") == "error"]
    warnings = [row for row in invariant_rows if row.get("severity") == "warning"]

    def fmt_corr(value: float | None) -> str:
        return "n/a" if value is None else f"{value:.3f}"

    total = Counter()
    for row in season_rows:
        for key in [
            "contracts_created",
            "renewals_or_recontracts",
            "retired_players",
            "free_agent_listings_created",
            "youth_generated",
            "youth_signed",
            "draft_selections_signed",
            "draft_selections_declined",
            "draft_selections_expired",
            "auto_fill_players_joined",
        ]:
            total[key] += int(row.get(key) or 0)

    lines = [
        "# Closed Loop Balance Test Report",
        "",
        f"Generated at: `{datetime.utcnow().isoformat()}Z`",
        "",
        "## Run Summary",
        "",
        f"- Seasons captured: {len(season_rows)}",
        f"- Invariant errors: {len(errors)}",
        f"- Invariant warnings: {len(warnings)}",
        f"- Contracts created: {total['contracts_created']}",
        f"- Renewals/recontracts: {total['renewals_or_recontracts']}",
        f"- Retired players: {total['retired_players']}",
        f"- Youth generated: {total['youth_generated']}",
        f"- Youth signed: {total['youth_signed']}",
        f"- Draft signed: {total['draft_selections_signed']}",
        f"- Draft declined/expired: {total['draft_selections_declined'] + total['draft_selections_expired']}",
        f"- Free-agent listings created: {total['free_agent_listings_created']}",
        f"- Auto-fill players joined: {total['auto_fill_players_joined']}",
        "",
        "## Correlations",
        "",
        f"- Team top8 OVR vs points: {fmt_corr(corr_top8_points)}",
        f"- Team wage bill vs points: {fmt_corr(corr_wage_points)}",
        f"- Team max OVR vs points: {fmt_corr(corr_max_points)}",
        f"- Player OVR vs average rating: {fmt_corr(corr_ovr_rating)}",
        "",
        "## Long-Term Balance Signals",
        "",
        f"- Latest balance Gini: {'n/a' if balance_gini is None else f'{balance_gini:.3f}'}",
        f"- Latest top8 OVR Gini: {'n/a' if top8_gini is None else f'{top8_gini:.3f}'}",
        f"- Champion relegations next season: {champion_relegations}",
        f"- Repeat champions in same league: {repeat_champions}",
        "",
        "## Season Table",
        "",
        "| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Draft Signed | FA Listings | Auto Fill | Roster Min/Max | Wage Avg/Max | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    for row in season_rows:
        lines.append(
            "| {season_number} | {contracts_created} | {renewals_or_recontracts} | {retired_players} | "
            "{youth_generated} | {youth_signed} | {draft_selections_signed} | {free_agent_listings_created} | "
            "{auto_fill_players_joined} | {roster_min}/{roster_max} | {avg_wage_pressure_pct:.1f}%/{max_wage_pressure_pct:.1f}% | {invariants_failed} |".format(**row)
        )

    if invariant_rows:
        lines.extend(["", "## Invariants", ""])
        for row in invariant_rows[:100]:
            lines.append(f"- [{row['severity']}] S{row['season_number']} {row['name']}: {row['count']} ({row['detail']})")
        if len(invariant_rows) > 100:
            lines.append(f"- ... {len(invariant_rows) - 100} more")

    lines.extend([
        "",
        "## Suggested Interpretation",
        "",
        "- If `Auto Fill` remains high after several seasons, contracts/youth/free market supply is not doing enough work.",
        "- If roster errors appear, the closed-loop lifecycle is not enforcing hard squad bounds.",
        "- If OVR-to-points correlation is near zero, strong players are not translating into team strength.",
        "- If wage-to-points correlation is too high and balance Gini rises quickly, the economy may be enabling runaway strong teams.",
        "- If champion relegations are frequent, promotion/relegation or match variance is too chaotic.",
    ])

    return "\n".join(lines) + "\n"


def count_champion_relegations(team_rows: list[dict[str, Any]]) -> int:
    by_team_season = {(row["team_id"], int(row["season_number"])): row for row in team_rows}
    count = 0
    for row in team_rows:
        if row.get("position") == 1 and row.get("league_level") == 1:
            next_row = by_team_season.get((row["team_id"], int(row["season_number"]) + 1))
            if next_row and next_row.get("league_level") not in ("", 1):
                count += 1
    return count


def count_repeat_champions(team_rows: list[dict[str, Any]]) -> int:
    champions = defaultdict(dict)
    for row in team_rows:
        if row.get("position") == 1 and row.get("league_id"):
            champions[row["league_id"]][int(row["season_number"])] = row["team_id"]
    repeat = 0
    for by_season in champions.values():
        for season_number, team_id in by_season.items():
            if by_season.get(season_number + 1) == team_id:
                repeat += 1
    return repeat


async def run(args: argparse.Namespace) -> int:
    random.seed(args.seed)
    out_dir = Path(args.out) if args.out else REPO_ROOT / "reports" / "closed_loop" / datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    artifacts = RunArtifacts(out_dir=out_dir)

    async with AsyncSessionLocal() as db:
        runner = SimulationRunner(db)
        if not runner.shared_clock:
            runner.clock.set_mode("step")
        if args.seasons == 0:
            season = await current_or_latest_season(db)
            if not season:
                print("No season found. Run bootstrap/init_season first.")
                return 1
            summary = await collect_season_summary(db, season, processed_events=0, event_status="collect_only")
            invariants = await collect_invariants(db, season)
            summary.invariants_failed = len([row for row in invariants if row["severity"] == "error"])
            summary.warnings = "; ".join(row["name"] for row in invariants)
            artifacts.season_rows.append(asdict(summary))
            artifacts.team_rows.extend(await collect_team_rows(db, season))
            artifacts.player_rows.extend(await collect_player_rows(db, season))
            artifacts.invariant_rows.extend(invariants)
        else:
            for index in range(1, args.seasons + 1):
                print(f"[closed-loop] running season {index}/{args.seasons} ...", flush=True)
                event_status = "ok"
                processed = 0
                try:
                    if args.debug_events > 0:
                        result = await runner.run_next_event_time(max_events_at_time=args.debug_events)
                    else:
                        result = await runner.run_seasons(count=1, max_events=args.max_events_per_season)
                    processed = result.processed
                    add_event_rows(artifacts, index, result.results)
                    if result.stopped_reason != "completed":
                        event_status = result.stopped_reason
                except Exception as exc:
                    event_status = f"exception:{type(exc).__name__}:{exc}"
                    await db.rollback()
                    print(f"[closed-loop] season run failed: {event_status}", flush=True)

                season = await latest_finished_season(db)
                if not season:
                    print("[closed-loop] no finished season available after run", flush=True)
                    break

                invariants = await collect_invariants(db, season)
                summary = await collect_season_summary(db, season, processed_events=processed, event_status=event_status)
                summary.invariants_failed = len([row for row in invariants if row["severity"] == "error"])
                summary.warnings = "; ".join(row["name"] for row in invariants)
                artifacts.season_rows.append(asdict(summary))
                artifacts.team_rows.extend(await collect_team_rows(db, season))
                artifacts.player_rows.extend(await collect_player_rows(db, season))
                artifacts.invariant_rows.extend(invariants)

                message = (
                    "[closed-loop] S{season} events={events} roster={rmin}/{rmax} "
                    "contracts={contracts} youth={youth} draft_signed={draft} "
                    "auto_fill={auto_fill} errors={errors} status={status}"
                ).format(
                    season=summary.season_number,
                    events=processed,
                    rmin=summary.roster_min,
                    rmax=summary.roster_max,
                    contracts=summary.contracts_created,
                    youth=summary.youth_signed,
                    draft=summary.draft_selections_signed,
                    auto_fill=summary.auto_fill_players_joined,
                    errors=summary.invariants_failed,
                    status=event_status,
                )
                print(message, flush=True)

                if args.stop_on_error and (summary.invariants_failed or event_status != "ok"):
                    print("[closed-loop] stopping because --stop-on-error is enabled", flush=True)
                    break

    artifacts.out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(artifacts.out_dir / "season_summary.csv", artifacts.season_rows)
    write_csv(artifacts.out_dir / "team_season_metrics.csv", artifacts.team_rows)
    write_csv(artifacts.out_dir / "player_season_metrics.csv", artifacts.player_rows)
    write_jsonl(artifacts.out_dir / "event_results.jsonl", artifacts.event_rows)
    write_csv(artifacts.out_dir / "invariants.csv", artifacts.invariant_rows)
    (artifacts.out_dir / "closed_loop_balance_report.md").write_text(build_report(artifacts), encoding="utf-8")

    print(f"[closed-loop] report written to: {artifacts.out_dir}", flush=True)
    await engine.dispose()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run closed-loop balance simulation and export metrics.")
    parser.add_argument("--seasons", type=int, default=1, help="Number of seasons to advance. Use 0 to only collect current DB state.")
    parser.add_argument("--max-events-per-season", type=int, default=12000)
    parser.add_argument("--debug-events", type=int, default=0, help="Advance to the next event timestamp, process at most this many events, then collect.")
    parser.add_argument("--seed", type=int, default=20260529)
    parser.add_argument("--out", type=str, default="")
    parser.add_argument("--stop-on-error", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
