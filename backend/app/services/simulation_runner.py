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
from app.models.league import LeagueStanding, League
from app.models.player_season_stats import PlayerSeasonStats
from app.models.player import Player
from app.models.team import Team
from app.models.record import Record, RecordScope, RecordCategory
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
        # 只选 MatchResult.resolution，避免拉取大 JSON 列导致 sort memory 不足
        rows = await self.db.execute(
            select(Fixture, MatchResult.resolution)
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
                "resolution": resolution,
            }
            for fixture, resolution in rows.all()
        ]

    # ------------------------------------------------------------------
    # 监控与数据查询
    # ------------------------------------------------------------------

    async def get_standings_snapshot(self, season_id: str | None = None) -> dict[str, Any]:
        """获取各联赛积分榜快照（默认取顶级联赛 level=1）"""
        if season_id is None:
            season = await self._current_season()
            if not season:
                return {}
            season_id = season.id

        # 取所有 level=1 的联赛
        league_result = await self.db.execute(
            select(League).where(League.level == 1).order_by(League.system_id)
        )
        leagues = league_result.scalars().all()

        snapshot: dict[str, Any] = {}
        for league in leagues:
            standing_result = await self.db.execute(
                select(LeagueStanding, Team)
                .join(Team, LeagueStanding.team_id == Team.id)
                .where(LeagueStanding.season_id == season_id)
                .where(LeagueStanding.league_id == league.id)
                .order_by(LeagueStanding.position)
            )
            rows = standing_result.all()
            snapshot[league.name] = [
                {
                    "position": s.position,
                    "team_name": t.name,
                    "played": s.played,
                    "won": s.won,
                    "drawn": s.drawn,
                    "lost": s.lost,
                    "goals_for": s.goals_for,
                    "goals_against": s.goals_against,
                    "goal_difference": s.goal_difference,
                    "points": s.points,
                }
                for s, t in rows
            ]
        return snapshot

    async def get_daily_scores(
        self, season_id: str | None = None, day: int | None = None
    ) -> list[dict[str, Any]]:
        """获取指定赛季某天的所有已完赛比分"""
        if season_id is None:
            season = await self._current_season()
            if not season:
                return []
            season_id = season.id
            if day is None:
                day = season.current_day

        if day is None:
            return []

        rows = await self.db.execute(
            select(Fixture, MatchResult)
            .join(MatchResult, MatchResult.fixture_id == Fixture.id, isouter=True)
            .where(Fixture.season_id == season_id)
            .where(Fixture.season_day == day)
            .where(Fixture.status == FixtureStatus.FINISHED)
            .order_by(Fixture.scheduled_at)
        )
        results = []
        for fixture, match_result in rows.all():
            results.append({
                "fixture_id": fixture.id,
                "fixture_type": fixture.fixture_type.value,
                "home_team_id": fixture.home_team_id,
                "away_team_id": fixture.away_team_id,
                "home_score": fixture.home_score,
                "away_score": fixture.away_score,
                "resolution": match_result.resolution if match_result else "unknown",
            })
        return results

    async def get_top_players(
        self, season_id: str | None = None, limit: int = 5
    ) -> dict[str, list[dict[str, Any]]]:
        """获取当前赛季射手榜、助攻榜、评分榜"""
        if season_id is None:
            season = await self._current_season()
            if not season:
                return {"goals": [], "assists": [], "rating": []}
            season_id = season.id

        # 射手榜（按联赛+杯赛合并）
        goals_result = await self.db.execute(
            select(PlayerSeasonStats.player_id, Player.name, func.sum(PlayerSeasonStats.goals).label("total_goals"))
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(PlayerSeasonStats.season_id == season_id)
            .group_by(PlayerSeasonStats.player_id)
            .order_by(desc("total_goals"))
            .limit(limit)
        )
        goals = [
            {"player_id": pid, "name": name, "goals": int(total) if total else 0}
            for pid, name, total in goals_result.all()
        ]

        assists_result = await self.db.execute(
            select(PlayerSeasonStats.player_id, Player.name, func.sum(PlayerSeasonStats.assists).label("total_assists"))
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(PlayerSeasonStats.season_id == season_id)
            .group_by(PlayerSeasonStats.player_id)
            .order_by(desc("total_assists"))
            .limit(limit)
        )
        assists = [
            {"player_id": pid, "name": name, "assists": int(total) if total else 0}
            for pid, name, total in assists_result.all()
        ]

        rating_result = await self.db.execute(
            select(
                PlayerSeasonStats.player_id,
                Player.name,
                func.sum(PlayerSeasonStats.matches_played).label("total_matches"),
                func.avg(PlayerSeasonStats.average_rating).label("avg_rating"),
            )
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(PlayerSeasonStats.season_id == season_id)
            .where(PlayerSeasonStats.matches_played >= 5)
            .group_by(PlayerSeasonStats.player_id)
            .order_by(desc("avg_rating"))
            .limit(limit)
        )
        ratings = [
            {
                "player_id": pid,
                "name": name,
                "matches": int(matches) if matches else 0,
                "rating": round(float(avg), 1) if avg else 0.0,
            }
            for pid, name, matches, avg in rating_result.all()
        ]

        return {"goals": goals, "assists": assists, "rating": ratings}

    async def get_records_snapshot(self, limit: int = 5) -> list[dict[str, Any]]:
        """获取最新世界纪录快照"""
        rows = await self.db.execute(
            select(Record, Player, Team)
            .outerjoin(Player, Record.holder_player_id == Player.id)
            .outerjoin(Team, Record.holder_team_id == Team.id)
            .where(Record.scope == RecordScope.WORLD)
            .order_by(Record.updated_at.desc())
            .limit(limit)
        )
        results = []
        for record, player, team in rows.all():
            holder = player.name if player else (team.name if team else "未知")
            results.append({
                "record_type": record.record_type.value,
                "record_value": record.record_value,
                "holder_name": holder,
                "category": record.category.value,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            })
        return results

    async def get_data_health_report(self) -> dict[str, Any]:
        """增强数据健康检查报告，供 AI 监看模式使用"""
        errors: list[str] = []
        warnings: list[str] = []

        # 1. 基础 invariant
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

        # 2. 数据一致性检查
        season = await self._current_season()
        if season:
            # 检查 SCHEDULED 比赛数量是否合理
            scheduled_count = await self.db.execute(
                select(func.count())
                .select_from(Fixture)
                .where(Fixture.season_id == season.id)
                .where(Fixture.status == FixtureStatus.SCHEDULED)
            )
            scheduled = scheduled_count.scalar_one()

            finished_count = await self.db.execute(
                select(func.count())
                .select_from(Fixture)
                .where(Fixture.season_id == season.id)
                .where(Fixture.status == FixtureStatus.FINISHED)
            )
            finished = finished_count.scalar_one()

            total = scheduled + finished
            if total > 0 and finished / total > 1.0:
                warnings.append("finished ratio abnormal")

            # 检查 match_results 与 finished fixtures 是否一一对应
            results_without_fixture = await self.db.execute(
                select(func.count())
                .select_from(MatchResult)
                .where(MatchResult.fixture_id.notin_(
                    select(Fixture.id).where(Fixture.status == FixtureStatus.FINISHED)
                ))
            )
            orphan_results = results_without_fixture.scalar_one()
            if orphan_results:
                warnings.append(f"orphan match_results: {orphan_results}")

            # 检查积分榜是否有负分或异常大数值
            bad_standings = await self.db.execute(
                select(func.count())
                .select_from(LeagueStanding)
                .where(LeagueStanding.season_id == season.id)
                .where(
                    (LeagueStanding.points < 0)
                    | (LeagueStanding.played < 0)
                    | (LeagueStanding.goals_for < 0)
                    | (LeagueStanding.goals_against < 0)
                )
            )
            if bad_standings.scalar_one():
                errors.append("negative values in standings")

            # 检查球员赛季统计是否有负值
            bad_stats = await self.db.execute(
                select(func.count())
                .select_from(PlayerSeasonStats)
                .where(PlayerSeasonStats.season_id == season.id)
                .where(
                    (PlayerSeasonStats.goals < 0)
                    | (PlayerSeasonStats.assists < 0)
                    | (PlayerSeasonStats.matches_played < 0)
                )
            )
            if bad_stats.scalar_one():
                errors.append("negative values in player stats")

        return {
            "ok": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "season_day": season.current_day if season else None,
            "season_number": season.season_number if season else None,
        }

    async def _current_season(self) -> Season | None:
        result = await self.db.execute(
            select(Season)
            .where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
            .order_by(desc(Season.season_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

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
