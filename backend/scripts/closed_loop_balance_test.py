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
    EventQueue,
    FinanceTransaction,
    FreeAgentListing,
    FreeAgentOrigin,
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
    GrowthSpeed,
    YouthAcademyPlayer,
    TrainingResult,
)
from app.core.events import EventStatus  # noqa: E402
from app.models.player_contract import ContractStatus  # noqa: E402
from app.services.simulation_runner import RunnerResult, SimulationRunner  # noqa: E402


ACTIVE_ROSTER_STATUSES = [
    PlayerStatus.ACTIVE,
    PlayerStatus.INJURED,
    PlayerStatus.SUSPENDED,
]
ROSTER_MIN = 8
ROSTER_MAX = 18


@dataclass
class SeasonSummary:
    season_number: int
    season_id: str
    event_status: str = "ok"
    processed_events: int = 0
    failed_events_total: int = 0
    teams_total: int = 0
    teams_below_8: int = 0
    teams_above_max: int = 0
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
    youth_released_to_rookie_market: int = 0
    youth_free_market: int = 0
    rookie_market_listings: int = 0
    rookie_market_active: int = 0
    rookie_market_signed: int = 0
    rookie_market_protected_active: int = 0
    auto_fill_players_joined: int = 0
    academy_players_joined: int = 0
    rookie_market_players_joined: int = 0
    free_market_players_joined: int = 0
    avg_wage_pressure_pct: float = 0.0
    max_wage_pressure_pct: float = 0.0
    teams_over_wage_cap: int = 0
    min_balance: float = 0.0
    avg_balance: float = 0.0
    avg_state_score: float = 0.0
    min_state_score: int = 0
    max_state_score: int = 0
    players_hot: int = 0
    players_good: int = 0
    players_neutral: int = 0
    players_low: int = 0
    avg_contract_score: float = 0.0
    avg_recent_match_score: float = 0.0
    avg_fitness_score: float = 0.0
    avg_match_load_score: float = 0.0
    avg_match_rust_score: float = 0.0
    training_sessions: int = 0
    training_breakthroughs: int = 0
    avg_fatigue: float = 0.0
    avg_fitness: float = 0.0
    players_fatigue_over_75: int = 0
    players_fitness_below_50: int = 0
    avg_attr_progress_total: float = 0.0
    invariants_failed: int = 0
    warnings: str = ""


@dataclass
class RunArtifacts:
    out_dir: Path
    season_rows: list[dict[str, Any]] = field(default_factory=list)
    team_rows: list[dict[str, Any]] = field(default_factory=list)
    player_rows: list[dict[str, Any]] = field(default_factory=list)
    youth_budget_rows: list[dict[str, Any]] = field(default_factory=list)
    event_rows: list[dict[str, Any]] = field(default_factory=list)
    invariant_rows: list[dict[str, Any]] = field(default_factory=list)
    training_rows: list[dict[str, Any]] = field(default_factory=list)
    fatigue_rows: list[dict[str, Any]] = field(default_factory=list)


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
    replaced_contract_player_ids = {
        contract.player_id
        for contract in contracts
        if enum_value(contract.status) in ("expired", "terminated")
    }

    youth_counts = await count_grouped(
        db, YouthAcademyPlayer.status, YouthAcademyPlayer, YouthAcademyPlayer.season_id == season.id
    )
    listing_counts = await count_grouped(
        db, FreeAgentListing.status, FreeAgentListing, FreeAgentListing.season_id == season.id
    )
    rookie_listing_counts = await count_grouped(
        db,
        FreeAgentListing.status,
        FreeAgentListing,
        FreeAgentListing.season_id == season.id,
        FreeAgentListing.origin == FreeAgentOrigin.ACADEMY_RELEASED,
    )
    rookie_protected_active = 0
    rookie_listings = (
        await db.execute(
            select(FreeAgentListing)
            .where(FreeAgentListing.season_id == season.id)
            .where(FreeAgentListing.origin == FreeAgentOrigin.ACADEMY_RELEASED)
        )
    ).scalars().all()
    for listing in rookie_listings:
        extra = listing.extra_data or {}
        if listing.status == ListingStatus.ACTIVE and extra.get("rookie_protected"):
            rookie_protected_active += 1

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
    active_players = (
        await db.execute(
            select(Player)
            .where(Player.status.in_(ACTIVE_ROSTER_STATUSES))
            .where(Player.team_id.isnot(None))
        )
    ).scalars().all()
    state_scores = [int(player.state_score or 0) for player in active_players]
    form_counts = Counter(enum_value(player.match_form).lower() for player in active_players)

    # 训练指标
    training_results = (
        await db.execute(select(TrainingResult).where(TrainingResult.season_id == season.id))
    ).scalars().all()
    training_sessions = len(training_results)
    training_breakthroughs = sum(
        len(r.breakthroughs or []) for r in training_results
    )

    # 疲劳与成长指标
    player_fatigues = [p.fatigue or 0 for p in active_players]
    player_fitnesses = [p.fitness or 100 for p in active_players]
    attr_progress_totals = [
        sum((p.attribute_progress or {}).values()) for p in active_players
    ]

    summary = SeasonSummary(
        season_number=season.season_number,
        season_id=season.id,
        event_status=event_status,
        processed_events=processed_events,
        failed_events_total=failed_events,
        teams_total=len(roster_values),
        teams_below_8=sum(1 for count in roster_values if count < ROSTER_MIN),
        teams_above_max=sum(1 for count in roster_values if count > ROSTER_MAX),
        roster_min=min(roster_values) if roster_values else 0,
        roster_max=max(roster_values) if roster_values else 0,
        roster_avg=round(avg(roster_values), 2),
        contracts_created=len(contracts),
        renewals_or_recontracts=sum(
            1
            for contract in contracts
            if enum_value(contract.status) == "active"
            and (
                previous_contract_counts[contract.player_id] > 0
                or contract.player_id in replaced_contract_player_ids
            )
        ),
        rookie_contracts_created=sum(1 for contract in contracts if enum_value(contract.contract_type) == "rookie"),
        contracts_expired_active_now=sum(1 for contract in contracts if enum_value(contract.status) == "expired"),
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
        youth_released_to_rookie_market=youth_counts.get("free_market", 0),
        youth_free_market=youth_counts.get("free_market", 0),
        rookie_market_listings=len(rookie_listings),
        rookie_market_active=rookie_listing_counts.get("active", 0),
        rookie_market_signed=rookie_listing_counts.get("signed", 0),
        rookie_market_protected_active=rookie_protected_active,
        auto_fill_players_joined=joined_counts.get("auto_fill", 0),
        academy_players_joined=joined_counts.get("academy", 0),
        rookie_market_players_joined=rookie_listing_counts.get("signed", 0),
        free_market_players_joined=joined_counts.get("free_market", 0),
        avg_wage_pressure_pct=round(avg(wage_pressures), 2),
        max_wage_pressure_pct=round(max(wage_pressures), 2) if wage_pressures else 0.0,
        teams_over_wage_cap=over_cap,
        min_balance=round(min(balances), 2) if balances else 0.0,
        avg_balance=round(avg(balances), 2),
        avg_state_score=round(avg(state_scores), 2),
        min_state_score=min(state_scores) if state_scores else 0,
        max_state_score=max(state_scores) if state_scores else 0,
        players_hot=form_counts.get("hot", 0),
        players_good=form_counts.get("good", 0),
        players_neutral=form_counts.get("neutral", 0),
        players_low=form_counts.get("low", 0),
        avg_contract_score=round(avg([player.state_contract_score or 0 for player in active_players]), 2),
        avg_recent_match_score=round(avg([player.state_recent_match_score or 0 for player in active_players]), 2),
        avg_fitness_score=round(avg([player.state_fitness_score or 0 for player in active_players]), 2),
        avg_match_load_score=round(avg([player.state_match_load_score or 0 for player in active_players]), 2),
        avg_match_rust_score=round(avg([player.match_rust_score or 0 for player in active_players]), 2),
        training_sessions=training_sessions,
        training_breakthroughs=training_breakthroughs,
        avg_fatigue=round(avg(player_fatigues), 2),
        avg_fitness=round(avg(player_fitnesses), 2),
        players_fatigue_over_75=sum(1 for f in player_fatigues if f > 75),
        players_fitness_below_50=sum(1 for f in player_fitnesses if f < 50),
        avg_attr_progress_total=round(avg(attr_progress_totals), 2),
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
        rookie_contracts = sum(1 for contract, _ in contracts if enum_value(contract.contract_type) == "rookie")
        rookie_market_signings = await count_rows(
            db,
            FreeAgentListing,
            FreeAgentListing.season_id == season.id,
            FreeAgentListing.origin == FreeAgentOrigin.ACADEMY_RELEASED,
            FreeAgentListing.status == ListingStatus.SIGNED,
            FreeAgentListing.signed_team_id == team.id,
        )

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
            "rookie_market_signings": rookie_market_signings,
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
                "match_form": enum_value(player.match_form),
                "state_score": player.state_score,
                "contract_score": player.state_contract_score,
                "recent_match_score": player.state_recent_match_score,
                "fitness_score": player.state_fitness_score,
                "match_load_score": player.state_match_load_score,
                "match_rust_score": player.match_rust_score,
                "attribute_modifier_pct": decimal_float(player.state_attribute_modifier_pct),
                "stamina_modifier": decimal_float(player.state_stamina_modifier),
                "fitness": player.fitness or 100,
                "fatigue": player.fatigue or 0,
                "attribute_progress_total": round(sum((player.attribute_progress or {}).values()), 2),
                "recent_ratings": player.recent_ratings or [],
                "recent_minutes": player.recent_minutes or [],
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


def youth_budget_tier(youth_pct: float) -> str:
    if youth_pct <= 10:
        return "low"
    if youth_pct <= 17:
        return "medium"
    return "high"


def academy_player_age(player: Player, season: Season) -> int:
    return season.season_number + abs(player.birth_offset)


def academy_prospect_score(player: Player, academy_player: YouthAcademyPlayer, season: Season) -> float:
    """压测用青训价值分：综合即时 OVR、潜力、年龄和成长速度。"""
    age = academy_player_age(player, season)
    growth_bonus = {
        GrowthSpeed.FAST: 6.0,
        GrowthSpeed.NORMAL: 2.0,
        GrowthSpeed.SLOW: -2.0,
    }.get(academy_player.growth_speed, 0.0)
    age_bonus = max(0, 18 - age) * 2.0
    future_gap = max(0, int(player.potential_max or 0) - int(player.ovr or 0))
    return round(float(player.ovr) + future_gap * 0.45 + growth_bonus + age_bonus, 2)


def academy_player_is_useful(
    player: Player,
    academy_player: YouthAcademyPlayer,
    season: Season,
    roster_avg_ovr: float,
    team_top8_ovr: float,
) -> bool:
    """判断该青训是否对本队有即时或未来价值。"""
    score = academy_prospect_score(player, academy_player, season)
    immediate_help = float(player.ovr) >= max(0.0, roster_avg_ovr - 1.0)
    future_core = float(player.potential_max or 0) >= team_top8_ovr + 5.0
    young_fast_upside = (
        academy_player_age(player, season) <= 16
        and academy_player.growth_speed == GrowthSpeed.FAST
        and float(player.potential_max or 0) >= team_top8_ovr
    )
    score_help = score >= team_top8_ovr + 2.0
    return immediate_help or future_core or young_fast_upside or score_help


async def collect_youth_budget_rows(db, season: Season) -> list[dict[str, Any]]:
    finance_rows = (
        await db.execute(select(TeamSeasonFinance).where(TeamSeasonFinance.season_id == season.id))
    ).scalars().all()
    finance_by_team = {finance.team_id: finance for finance in finance_rows}

    teams = (
        await db.execute(select(Team, User).join(User, Team.user_id == User.id))
    ).all()

    rows: list[dict[str, Any]] = []
    for team, user in teams:
        roster_players = (
            await db.execute(
                select(Player)
                .where(Player.team_id == team.id)
                .where(Player.status.in_(ACTIVE_ROSTER_STATUSES))
            )
        ).scalars().all()
        roster_ovrs = sorted([player.ovr for player in roster_players], reverse=True)
        roster_avg_ovr = avg(roster_ovrs)
        team_top8_ovr = avg(roster_ovrs[:8])

        academy_rows = (
            await db.execute(
                select(YouthAcademyPlayer, Player)
                .join(Player, YouthAcademyPlayer.player_id == Player.id)
                .where(YouthAcademyPlayer.season_id == season.id)
                .where(YouthAcademyPlayer.team_id == team.id)
            )
        ).all()

        finance = finance_by_team.get(team.id)
        youth_budget = decimal_float(finance.youth_budget) if finance else 0.0
        locked_budget_total = decimal_float(finance.locked_budget_total) if finance else 0.0
        youth_pct = youth_budget / locked_budget_total * 100 if locked_budget_total > 0 else 0.0

        generated = len(academy_rows)
        ages = [academy_player_age(player, season) for academy_player, player in academy_rows]
        ovrs = [float(player.ovr) for academy_player, player in academy_rows]
        potentials = [float(player.potential_max or 0) for academy_player, player in academy_rows]
        prospect_scores = [
            academy_prospect_score(player, academy_player, season)
            for academy_player, player in academy_rows
        ]
        useful_flags = [
            academy_player_is_useful(player, academy_player, season, roster_avg_ovr, team_top8_ovr)
            for academy_player, player in academy_rows
        ]
        speed_counts = Counter(enum_value(academy_player.growth_speed) for academy_player, _ in academy_rows)
        potential_letters = Counter(enum_value(player.potential_letter) for _, player in academy_rows)
        status_counts = Counter(enum_value(academy_player.status) for academy_player, _ in academy_rows)

        rows.append({
            "season_number": season.season_number,
            "season_id": season.id,
            "team_id": team.id,
            "team_name": team.name,
            "is_ai": bool(user.is_ai),
            "league_id": team.current_league_id,
            "roster_count": len(roster_players),
            "roster_avg_ovr": round(roster_avg_ovr, 2),
            "team_top8_ovr": round(team_top8_ovr, 2),
            "youth_budget": round(youth_budget, 2),
            "locked_budget_total": round(locked_budget_total, 2),
            "youth_budget_pct": round(youth_pct, 2),
            "budget_tier": youth_budget_tier(youth_pct),
            "academy_generated": generated,
            "academy_signed": status_counts.get("signed", 0),
            "academy_in_academy": status_counts.get("in_academy", 0),
            "academy_free_market": status_counts.get("free_market", 0),
            "avg_youth_age": round(avg(ages), 2),
            "avg_youth_ovr": round(avg(ovrs), 2),
            "max_youth_ovr": round(max(ovrs), 2) if ovrs else 0.0,
            "avg_potential_max": round(avg(potentials), 2),
            "max_potential_max": round(max(potentials), 2) if potentials else 0.0,
            "avg_prospect_score": round(avg(prospect_scores), 2),
            "best_prospect_score": round(max(prospect_scores), 2) if prospect_scores else 0.0,
            "useful_prospect_count": sum(1 for flag in useful_flags if flag),
            "useful_prospect_rate": round(sum(1 for flag in useful_flags if flag) / generated * 100, 2) if generated else 0.0,
            "unusable_prospect_count": generated - sum(1 for flag in useful_flags if flag),
            "fast_growth_count": speed_counts.get("fast", 0),
            "normal_growth_count": speed_counts.get("normal", 0),
            "slow_growth_count": speed_counts.get("slow", 0),
            "potential_s_count": potential_letters.get("S", 0),
            "potential_a_count": potential_letters.get("A", 0),
            "potential_b_or_lower_count": generated - potential_letters.get("S", 0) - potential_letters.get("A", 0),
        })
    return rows


async def collect_training_rows(db, season: Season) -> list[dict[str, Any]]:
    """按球队汇总训练结算数据"""
    teams = (
        await db.execute(select(Team, User).join(User, Team.user_id == User.id))
    ).all()

    rows: list[dict[str, Any]] = []
    for team, user in teams:
        results = (
            await db.execute(
                select(TrainingResult)
                .where(TrainingResult.season_id == season.id)
                .where(TrainingResult.team_id == team.id)
            )
        ).scalars().all()

        if not results:
            continue

        efficiencies = [decimal_float(r.efficiency) for r in results if r.efficiency is not None]
        load_points = [r.load_points or 0 for r in results]
        breakthroughs = sum(len(r.breakthroughs or []) for r in results)

        rows.append({
            "season_number": season.season_number,
            "season_id": season.id,
            "team_id": team.id,
            "team_name": team.name,
            "is_ai": bool(user.is_ai),
            "total_sessions": len(results),
            "total_breakthroughs": breakthroughs,
            "avg_efficiency": round(avg(efficiencies), 2) if efficiencies else 0.0,
            "total_load_points": sum(load_points),
        })
    return rows


async def collect_fatigue_rows(db, season: Season) -> list[dict[str, Any]]:
    """按球队汇总球员疲劳与成长数据"""
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

        if not players:
            continue

        fatigues = [p.fatigue or 0 for p in players]
        fitnesses = [p.fitness or 100 for p in players]
        attr_progress = [sum((p.attribute_progress or {}).values()) for p in players]
        ages = [season.season_number + abs(p.birth_offset) for p in players]
        young = [p for p in players if season.season_number + abs(p.birth_offset) <= 21]
        old = [p for p in players if season.season_number + abs(p.birth_offset) >= 30]

        rows.append({
            "season_number": season.season_number,
            "season_id": season.id,
            "team_id": team.id,
            "team_name": team.name,
            "is_ai": bool(user.is_ai),
            "roster_count": len(players),
            "avg_fatigue": round(avg(fatigues), 2),
            "avg_fitness": round(avg(fitnesses), 2),
            "players_fatigue_over_75": sum(1 for f in fatigues if f > 75),
            "players_fitness_below_50": sum(1 for f in fitnesses if f < 50),
            "avg_attr_progress_total": round(avg(attr_progress), 2),
            "avg_age": round(avg(ages), 2),
            "young_players_count": len(young),
            "old_players_count": len(old),
            "young_avg_attr_progress": round(avg([sum((p.attribute_progress or {}).values()) for p in young]), 2) if young else 0.0,
            "old_avg_attr_progress": round(avg([sum((p.attribute_progress or {}).values()) for p in old]), 2) if old else 0.0,
        })
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
    add("teams_below_8", "error", sum(1 for c in roster_counts.values() if c < ROSTER_MIN), "team active roster below minimum")
    add("teams_above_max", "error", sum(1 for c in roster_counts.values() if c > ROSTER_MAX), "team active roster above maximum")

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

    active_rookie_listings = (
        await db.execute(
            select(FreeAgentListing)
            .where(FreeAgentListing.status == ListingStatus.ACTIVE)
            .where(FreeAgentListing.origin == FreeAgentOrigin.ACADEMY_RELEASED)
        )
    ).scalars().all()
    protected_rookies = sum(
        1 for listing in active_rookie_listings
        if (listing.extra_data or {}).get("rookie_protected")
    )
    add(
        "protected_rookies_still_active",
        "warning",
        int(protected_rookies),
        "rookie market listings still active after protection processing",
    )

    duplicate_active_contracts = await db.execute(
        select(PlayerContract.player_id, func.count())
        .where(PlayerContract.status == ContractStatus.ACTIVE)
        .group_by(PlayerContract.player_id)
        .having(func.count() > 1)
    )
    duplicate_count = len(duplicate_active_contracts.all())
    add("duplicate_active_contracts", "error", duplicate_count, "player has more than one active contract")

    missing_state_cache = await count_rows(
        db,
        Player,
        Player.team_id.isnot(None),
        Player.status.in_(ACTIVE_ROSTER_STATUSES),
        Player.state_updated_at.is_(None),
    )
    add("missing_player_state_cache", "warning", missing_state_cache, "active roster player has not been state-recalculated")

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


async def run_one_season(
    runner: SimulationRunner,
    db,
    args: argparse.Namespace,
    artifacts: RunArtifacts,
    season_loop_index: int,
) -> RunnerResult:
    total = RunnerResult()
    team_name_cache: dict[str, str] = {}

    while total.season_ends < 1 and total.processed < args.max_events_per_season:
        batch = await runner.run_next_event_time(max_events_at_time=200)
        total.processed += batch.processed
        total.season_ends += batch.season_ends
        total.results.extend(batch.results)
        add_event_rows(artifacts, season_loop_index, batch.results)

        if not args.quiet_events:
            for item in batch.results:
                for line in await format_event_log_lines(db, item, args.match_log_limit, team_name_cache):
                    print(line, flush=True)

        if batch.stopped_reason == "no_pending_events":
            total.stopped_reason = batch.stopped_reason
            return total
        if batch.stopped_reason == "idle" and batch.processed == 0:
            total.stopped_reason = batch.stopped_reason
            return total
        if batch.stopped_reason == "max_events_at_same_time":
            total.stopped_reason = batch.stopped_reason
            return total
        if batch.stopped_reason == "max_events":
            total.stopped_reason = "max_events_at_same_time"
            return total

    total.stopped_reason = "completed" if total.season_ends >= 1 else "max_events"
    return total


async def format_event_log_lines(
    db,
    item: dict[str, Any],
    match_log_limit: int,
    team_name_cache: dict[str, str],
) -> list[str]:
    event = item.get("event", "unknown")

    if event == "match_day":
        lines = [
            f"[match] day={item.get('season_day')} fixtures={item.get('fixtures_processed', 0)}"
        ]
        results = item.get("results") or []
        for match in results[:match_log_limit]:
            home = await get_team_name(db, match.get("home_team"), team_name_cache)
            away = await get_team_name(db, match.get("away_team"), team_name_cache)
            lines.append(
                "  {home} {hs}-{as_} {away} ({type})".format(
                    home=home,
                    hs=match.get("home_score"),
                    as_=match.get("away_score"),
                    away=away,
                    type=match.get("type"),
                )
            )
        remaining = len(results) - match_log_limit
        if remaining > 0:
            lines.append(f"  ... {remaining} more matches")
        return lines

    if event == "youth_refresh":
        refresh = item.get("refresh") or {}
        ai = item.get("ai") or {}
        return [
            "[youth] refresh={refresh} ai_signed={signed} ai_declined={declined} "
            "candidates={candidates} full={full} low_score={low} failed={failed}".format(
                refresh=refresh.get("refreshed", 0),
                signed=ai.get("signed", 0),
                declined=ai.get("declined", 0),
                candidates=ai.get("candidates", 0),
                full=ai.get("blocked_full", 0),
                low=ai.get("below_threshold", 0),
                failed=ai.get("sign_failed", 0),
            )
        ]

    if event == "youth_training":
        return [f"[youth] trained={item.get('trained', 0)}"]

    if event == "training_day":
        return [
            "[training] day={day} teams={teams} sessions={sessions} breakthroughs={bt}".format(
                day=item.get("season_day"),
                teams=item.get("teams_processed", 0),
                sessions=item.get("sessions_completed", 0),
                bt=item.get("total_breakthroughs", 0),
            )
        ]

    if event == "draft_preferences_open":
        ai = item.get("ai") or {}
        return [
            "[draft] preferences_open pools={pools} ai_processed={processed}".format(
                pools=item.get("pools", 0),
                processed=ai.get("processed", 0),
            )
        ]

    if event == "draft_run":
        draft = item.get("draft") or {}
        ai = item.get("ai") or {}
        return [
            "[draft] selections={selections} ai_signed={signed} ai_declined={declined}".format(
                selections=draft.get("selections", 0),
                signed=ai.get("signed", 0),
                declined=ai.get("declined", 0),
            )
        ]

    if event == "draft_signing_expire":
        return [f"[draft] signing_expire signed={item.get('signed', 0)} expired={item.get('expired', 0)}"]

    if event == "season_end":
        lifecycle = item.get("roster_lifecycle") or {}
        ai = item.get("ai") or item.get("ai_roster") or {}
        lines = [
            "[season] end S{season} -> S{next_season}".format(
                season=item.get("season_number"),
                next_season=item.get("next_season_number"),
            )
        ]
        if ai:
            lines.append(
                "  ai renew={renewed} academy={academy} free_market={free_market}".format(
                    renewed=ai.get("renewed", 0),
                    academy=ai.get("academy_signed", 0),
                    free_market=ai.get("free_market_signed", 0),
                )
            )
        if lifecycle:
            ai_post = lifecycle.get("ai_post_expiration") or {}
            if ai_post:
                lines.append(
                    "  post_expiration academy_signed={academy} free_market={free_market} "
                    "academy_candidates={candidates} full={full} low_score={low} failed={failed}".format(
                        academy=ai_post.get("academy_signed", 0),
                        free_market=ai_post.get("free_market_signed", 0),
                        candidates=ai_post.get("academy_candidates", 0),
                        full=ai_post.get("academy_blocked_full", 0),
                        low=ai_post.get("academy_below_threshold", 0),
                        failed=ai_post.get("academy_sign_failed", 0),
                    )
                )
            lines.append(f"  lifecycle={compact_dict(lifecycle)}")
        return lines

    if event == "season_finance_initialized":
        return [f"[finance] season initialized teams={item.get('teams_initialized', 0)}"]

    if event == "wages_paid":
        return [f"[finance] wages_paid period={item.get('period_key')}"]

    if event == "season_finance_closed":
        return [f"[finance] season closed season_id={short_id(item.get('season_id'))}"]

    if event == "budget_window_opened":
        return [f"[budget] opened {compact_dict(item)}"]

    if event == "budget_window_closed":
        return [f"[budget] closed {compact_dict(item)}"]

    if event == "cup_progression":
        results = item.get("results") or {}
        return [f"[cup] progression day={item.get('after_day')} {compact_dict(results)}"]

    if event == "promotion_relegation":
        results = item.get("results") or {}
        return [f"[league] promotion_relegation day={item.get('day')} {compact_dict(results)}"]

    if event == "season_start":
        return [f"[season] start season_id={short_id(item.get('season_id'))}"]

    return [f"[event] {event}: {compact_dict(item)}"]


async def get_team_name(db, team_id: str | None, cache: dict[str, str]) -> str:
    if not team_id:
        return "unknown"
    if team_id in cache:
        return cache[team_id]
    result = await db.execute(select(Team.name).where(Team.id == team_id))
    name = result.scalar_one_or_none() or short_id(team_id)
    cache[team_id] = name
    return name


def compact_dict(value: Any, limit: int = 220) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def short_id(value: Any) -> str:
    text = "" if value is None else str(value)
    return text[:8]


def build_report(artifacts: RunArtifacts) -> str:
    season_rows = artifacts.season_rows
    team_rows = artifacts.team_rows
    player_rows = artifacts.player_rows
    youth_budget_rows = artifacts.youth_budget_rows
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
    youth_rows_with_generated = [row for row in youth_budget_rows if int(row.get("academy_generated") or 0) > 0]
    corr_youth_budget_best = pearson(
        [float(row["youth_budget_pct"]) for row in youth_rows_with_generated],
        [float(row["best_prospect_score"]) for row in youth_rows_with_generated],
    )
    corr_youth_budget_useful = pearson(
        [float(row["youth_budget_pct"]) for row in youth_rows_with_generated],
        [float(row["useful_prospect_rate"]) for row in youth_rows_with_generated],
    )
    corr_youth_budget_potential = pearson(
        [float(row["youth_budget_pct"]) for row in youth_rows_with_generated],
        [float(row["avg_potential_max"]) for row in youth_rows_with_generated],
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
            "rookie_market_listings",
            "rookie_market_signed",
            "auto_fill_players_joined",
            "training_sessions",
            "training_breakthroughs",
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
        f"- Rookie-market listings: {total['rookie_market_listings']}",
        f"- Rookie-market signed: {total['rookie_market_signed']}",
        f"- Free-agent listings created: {total['free_agent_listings_created']}",
        f"- Auto-fill players joined: {total['auto_fill_players_joined']}",
        f"- Training sessions: {total['training_sessions']}",
        f"- Training breakthroughs: {total['training_breakthroughs']}",
        "",
        "## Player State Signals",
        "",
        f"- Latest avg state score: {season_rows[-1].get('avg_state_score', 'n/a') if season_rows else 'n/a'}",
        f"- Latest state score range: {season_rows[-1].get('min_state_score', 'n/a') if season_rows else 'n/a'} / {season_rows[-1].get('max_state_score', 'n/a') if season_rows else 'n/a'}",
        f"- Latest forms HOT/GOOD/NEUTRAL/LOW: "
        f"{season_rows[-1].get('players_hot', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('players_good', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('players_neutral', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('players_low', 'n/a') if season_rows else 'n/a'}",
        f"- Latest component avg contract/recent/fitness/load/rust: "
        f"{season_rows[-1].get('avg_contract_score', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('avg_recent_match_score', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('avg_fitness_score', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('avg_match_load_score', 'n/a') if season_rows else 'n/a'} / "
        f"{season_rows[-1].get('avg_match_rust_score', 'n/a') if season_rows else 'n/a'}",
        "",
        "## Training & Fatigue Signals",
        "",
        f"- Latest avg fatigue / fitness: {season_rows[-1].get('avg_fatigue', 'n/a') if season_rows else 'n/a'} / {season_rows[-1].get('avg_fitness', 'n/a') if season_rows else 'n/a'}",
        f"- Latest players fatigue>75 / fitness<50: {season_rows[-1].get('players_fatigue_over_75', 'n/a') if season_rows else 'n/a'} / {season_rows[-1].get('players_fitness_below_50', 'n/a') if season_rows else 'n/a'}",
        f"- Latest avg attr progress total: {season_rows[-1].get('avg_attr_progress_total', 'n/a') if season_rows else 'n/a'}",
        f"- Training sessions S1..Sn: {' / '.join(str(row.get('training_sessions', 0)) for row in season_rows)}",
        f"- Breakthroughs S1..Sn: {' / '.join(str(row.get('training_breakthroughs', 0)) for row in season_rows)}",
        "",
        "## Correlations",
        "",
        f"- Team top8 OVR vs points: {fmt_corr(corr_top8_points)}",
        f"- Team wage bill vs points: {fmt_corr(corr_wage_points)}",
        f"- Team max OVR vs points: {fmt_corr(corr_max_points)}",
        f"- Player OVR vs average rating: {fmt_corr(corr_ovr_rating)}",
        f"- Youth budget pct vs best prospect score: {fmt_corr(corr_youth_budget_best)}",
        f"- Youth budget pct vs useful prospect rate: {fmt_corr(corr_youth_budget_useful)}",
        f"- Youth budget pct vs avg potential max: {fmt_corr(corr_youth_budget_potential)}",
        "",
        "## Youth Budget Signals",
        "",
        "| Budget Tier | Teams | Avg Budget % | Avg Youth OVR | Avg Potential | Best Prospect | Useful Rate | Fast Growth/Team | A+S/Team |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    tier_order = ["low", "medium", "high"]
    rows_by_tier: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in youth_rows_with_generated:
        rows_by_tier[str(row.get("budget_tier") or "")].append(row)
    for tier in tier_order:
        rows = rows_by_tier.get(tier, [])
        lines.append(
            "| {tier} | {teams} | {budget:.1f}% | {ovr:.1f} | {potential:.1f} | {best:.1f} | {useful:.1f}% | {fast:.2f} | {aplus:.2f} |".format(
                tier=tier,
                teams=len(rows),
                budget=avg([float(row["youth_budget_pct"]) for row in rows]),
                ovr=avg([float(row["avg_youth_ovr"]) for row in rows]),
                potential=avg([float(row["avg_potential_max"]) for row in rows]),
                best=avg([float(row["best_prospect_score"]) for row in rows]),
                useful=avg([float(row["useful_prospect_rate"]) for row in rows]),
                fast=avg([float(row["fast_growth_count"]) for row in rows]),
                aplus=avg([float(row["potential_s_count"]) + float(row["potential_a_count"]) for row in rows]),
            )
        )

    lines.extend([
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
        "| Season | Contracts | Renew/Recontract | Retired | Youth Gen | Youth Signed | Rookie Listings | Rookie Signed | FA Listings | Auto Fill | Training | Breakthroughs | Roster Min/Max | Wage Avg/Max | State Avg/Range | Fatigue | Fitness | Errors |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: |",
    ])
    for row in season_rows:
        lines.append(
            "| {season_number} | {contracts_created} | {renewals_or_recontracts} | {retired_players} | "
            "{youth_generated} | {youth_signed} | {rookie_market_listings} | {rookie_market_signed} | {free_agent_listings_created} | "
            "{auto_fill_players_joined} | {training_sessions} | {training_breakthroughs} | {roster_min}/{roster_max} | "
            "{avg_wage_pressure_pct:.1f}%/{max_wage_pressure_pct:.1f}% | {avg_state_score:.1f}/{min_state_score}..{max_state_score} | "
            "{avg_fatigue:.1f} | {avg_fitness:.1f} | {invariants_failed} |".format(**row)
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
        "- If most players are LOW or HOT, inspect component averages to find the state factor dominating the system.",
        "- If avg fatigue stays >70 or fitness <60, training load or match recovery may be too harsh.",
        "- If young_avg_attr_progress >3.5/season or old_avg_attr_progress >1.0/season, growth speed is unhealthy.",
        "- If training breakthroughs are near zero, check whether training plans are being generated and completed.",
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
            artifacts.youth_budget_rows.extend(await collect_youth_budget_rows(db, season))
            artifacts.training_rows.extend(await collect_training_rows(db, season))
            artifacts.fatigue_rows.extend(await collect_fatigue_rows(db, season))
            artifacts.invariant_rows.extend(invariants)
        else:
            for index in range(1, args.seasons + 1):
                print(f"[closed-loop] running season {index}/{args.seasons} ...", flush=True)
                event_status = "ok"
                processed = 0
                try:
                    if args.debug_events > 0:
                        result = await runner.run_next_event_time(max_events_at_time=args.debug_events)
                        add_event_rows(artifacts, index, result.results)
                        if not args.quiet_events:
                            team_name_cache: dict[str, str] = {}
                            for item in result.results:
                                for line in await format_event_log_lines(db, item, args.match_log_limit, team_name_cache):
                                    print(line, flush=True)
                    elif args.quiet_events:
                        result = await runner.run_seasons(count=1, max_events=args.max_events_per_season)
                        add_event_rows(artifacts, index, result.results)
                    else:
                        result = await run_one_season(runner, db, args, artifacts, index)
                    processed = result.processed
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
                artifacts.youth_budget_rows.extend(await collect_youth_budget_rows(db, season))
                artifacts.training_rows.extend(await collect_training_rows(db, season))
                artifacts.fatigue_rows.extend(await collect_fatigue_rows(db, season))
                artifacts.invariant_rows.extend(invariants)

                message = (
                    "[closed-loop] S{season} events={events} roster={rmin}/{rmax} "
                    "contracts={contracts} youth={youth} rookie_signed={rookie} "
                    "training={training}/{breakthroughs} fatigue={avg_fatigue} fitness={avg_fitness} "
                    "auto_fill={auto_fill} errors={errors} status={status}"
                ).format(
                    season=summary.season_number,
                    events=processed,
                    rmin=summary.roster_min,
                    rmax=summary.roster_max,
                    contracts=summary.contracts_created,
                    youth=summary.youth_signed,
                    rookie=summary.rookie_market_signed,
                    training=summary.training_sessions,
                    breakthroughs=summary.training_breakthroughs,
                    avg_fatigue=summary.avg_fatigue,
                    avg_fitness=summary.avg_fitness,
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
    write_csv(artifacts.out_dir / "youth_budget_metrics.csv", artifacts.youth_budget_rows)
    write_csv(artifacts.out_dir / "training_metrics.csv", artifacts.training_rows)
    write_csv(artifacts.out_dir / "player_fatigue_metrics.csv", artifacts.fatigue_rows)
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
    parser.add_argument("--quiet-events", action="store_true", help="Do not print per-event progress logs while simulating.")
    parser.add_argument("--match-log-limit", type=int, default=8, help="Number of match results to print per match day.")
    parser.add_argument("--stop-on-error", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
