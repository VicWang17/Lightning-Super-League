"""
Record Service - 纪录检测与更新服务

比赛结束时自动检测各类纪录，支持三级维度：
- WORLD: 全服纪录
- LEAGUE: 联赛纪录 (scope_target_id = league_id)
- TEAM: 球队纪录 (scope_target_id = team_id)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.models.record import (
    Record,
    RecordScope,
    RecordCategory,
    RecordType,
    RECORD_TYPE_LABELS,
    RECORD_TYPES_LOWER_IS_BETTER,
)
from app.models.season import Fixture, FixtureStatus, FixtureType
from app.models.player import Player, PlayerPosition
from app.models.match_result import MatchResult as MatchResultModel
from app.models.team import Team
from app.models.league import LeagueStanding
from app.models.player_season_stats import PlayerSeasonStats


class RecordService:
    """纪录检测服务"""

    # ------------------------------------------------------------------
    # 公共入口
    # ------------------------------------------------------------------

    @staticmethod
    async def process_match_records(
        fixture: Fixture,
        result: "MatchResult",  # type: ignore # forward ref to match_simulator.MatchResult
        db: AsyncSession,
    ) -> None:
        """比赛结束后主入口：检测并更新所有比赛级纪录"""
        # 确保 fixture 已刷新到最新状态（含比分）
        await db.refresh(fixture)

        # 1. 比赛级纪录（最大分差、单场总进球等）
        await RecordService._check_match_level_records(fixture, db)

        # 2. 球员单场纪录（单场进球最多、最快进球等）
        if result.events or result.player_stats:
            await RecordService._check_player_match_records(fixture, result, db)

        # 3. 连胜/连败 streak 纪录
        await RecordService._check_streak_records(fixture, db)

        # 4. 球员生涯累计纪录（在 player_stats 更新之后检测）
        if result.player_stats:
            await RecordService._check_career_records_from_engine(fixture, result, db)

        # 5. 赛季级纪录增量检测（单赛季最佳纪录）
        if fixture.season_id:
            await RecordService._check_season_records_incremental(fixture, db)

    # ------------------------------------------------------------------
    # 1. 比赛级纪录
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_match_level_records(fixture: Fixture, db: AsyncSession) -> None:
        """检测基于比分的比赛级纪录"""
        home_score = fixture.home_score or 0
        away_score = fixture.away_score or 0
        total_goals = home_score + away_score
        margin = abs(home_score - away_score)
        winner_team_id = fixture.home_team_id if home_score > away_score else (
            fixture.away_team_id if away_score > home_score else None
        )
        loser_team_id = fixture.away_team_id if home_score > away_score else (
            fixture.home_team_id if away_score > home_score else None
        )

        # 单场总进球最多
        if total_goals > 0:
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.MOST_GOALS_IN_MATCH,
                category=RecordCategory.MATCH,
                value_str=f"{total_goals}球",
                value_num=total_goals,
                holder_team_id=winner_team_id,
                fixture_id=fixture.id,
                season_id=fixture.season_id,
                match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                db=db,
            )
            if fixture.league_id:
                await RecordService._update_record(
                    scope=RecordScope.LEAGUE,
                    scope_target_id=fixture.league_id,
                    record_type=RecordType.MOST_GOALS_IN_MATCH,
                    category=RecordCategory.MATCH,
                    value_str=f"{total_goals}球",
                    value_num=total_goals,
                    holder_team_id=winner_team_id,
                    fixture_id=fixture.id,
                    season_id=fixture.season_id,
                    match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                    db=db,
                )

        # 最大比分胜利
        if margin > 0 and winner_team_id:
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.BIGGEST_WIN_MARGIN,
                category=RecordCategory.MATCH,
                value_str=f"{margin}球",
                value_num=margin,
                holder_team_id=winner_team_id,
                fixture_id=fixture.id,
                season_id=fixture.season_id,
                match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                db=db,
            )
            if fixture.league_id:
                await RecordService._update_record(
                    scope=RecordScope.LEAGUE,
                    scope_target_id=fixture.league_id,
                    record_type=RecordType.BIGGEST_WIN_MARGIN,
                    category=RecordCategory.MATCH,
                    value_str=f"{margin}球",
                    value_num=margin,
                    holder_team_id=winner_team_id,
                    fixture_id=fixture.id,
                    season_id=fixture.season_id,
                    match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                    db=db,
                )
            await RecordService._update_record(
                scope=RecordScope.TEAM,
                scope_target_id=winner_team_id,
                record_type=RecordType.BIGGEST_WIN_MARGIN,
                category=RecordCategory.MATCH,
                value_str=f"{margin}球",
                value_num=margin,
                holder_team_id=winner_team_id,
                fixture_id=fixture.id,
                season_id=fixture.season_id,
                match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                db=db,
            )

        # 最大比分失利
        if margin > 0 and loser_team_id:
            await RecordService._update_record(
                scope=RecordScope.TEAM,
                scope_target_id=loser_team_id,
                record_type=RecordType.BIGGEST_DEFEAT_MARGIN,
                category=RecordCategory.MATCH,
                value_str=f"{margin}球",
                value_num=margin,
                holder_team_id=loser_team_id,
                fixture_id=fixture.id,
                season_id=fixture.season_id,
                match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                db=db,
            )

    # ------------------------------------------------------------------
    # 2. 球员单场纪录
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_player_match_records(
        fixture: Fixture,
        result: "MatchResult",
        db: AsyncSession,
    ) -> None:
        """检测球员单场纪录：单场进球最多、单场助攻最多、最快进球"""
        events = result.events or []
        player_stats = result.player_stats or []

        # ---- 最快进球 ----
        goal_events = [e for e in events if e.get("type") == "GOAL"]
        if goal_events:
            # 按时间排序，找第一个
            sorted_goals = sorted(
                goal_events,
                key=lambda e: (e.get("minute", 99), e.get("second", 99))
            )
            first_goal = sorted_goals[0]
            minute = first_goal.get("minute", 0)
            second = first_goal.get("second", 0)
            total_seconds = minute * 60 + second
            player_id = first_goal.get("player_id")

            if player_id and total_seconds >= 0:
                # 越小越好，存负数用于统一比较
                value_num = -float(total_seconds)
                value_str = f"{minute}分{second}秒" if second else f"{minute}分"

                for scope, target_id in [
                    (RecordScope.WORLD, None),
                    (RecordScope.LEAGUE, fixture.league_id),
                ]:
                    if scope == RecordScope.LEAGUE and not target_id:
                        continue
                    await RecordService._update_record(
                        scope=scope,
                        scope_target_id=target_id,
                        record_type=RecordType.FASTEST_GOAL,
                        category=RecordCategory.PLAYER,
                        value_str=value_str,
                        value_num=value_num,
                        holder_player_id=player_id,
                        holder_team_id=first_goal.get("team_id"),
                        fixture_id=fixture.id,
                        season_id=fixture.season_id,
                        match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                        db=db,
                    )

        # ---- 单场进球最多 / 单场助攻最多 / 帽子戏法 ----
        # player_stats 中已经有聚合好的数据
        for ps in player_stats:
            player_id = ps.get("player_id")
            if not player_id:
                continue

            team_side = ps.get("team", "")
            team_id = fixture.home_team_id if team_side == "home" else fixture.away_team_id
            goals = int(ps.get("goals", 0))
            assists = int(ps.get("assists", 0))

            if goals >= 3:
                # 帽子戏法次数：每场比赛只计一次
                await RecordService._increment_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.HAT_TRICKS,
                    category=RecordCategory.PLAYER,
                    holder_player_id=player_id,
                    holder_team_id=team_id,
                    fixture_id=fixture.id,
                    season_id=fixture.season_id,
                    db=db,
                    increment=1,
                    unit="次",
                )
                if fixture.league_id:
                    await RecordService._increment_record(
                        scope=RecordScope.LEAGUE,
                        scope_target_id=fixture.league_id,
                        record_type=RecordType.HAT_TRICKS,
                        category=RecordCategory.PLAYER,
                        holder_player_id=player_id,
                        holder_team_id=team_id,
                        fixture_id=fixture.id,
                        season_id=fixture.season_id,
                        db=db,
                        increment=1,
                        unit="次",
                    )

            # 单场进球最多
            if goals > 0:
                for scope, target_id in [
                    (RecordScope.WORLD, None),
                    (RecordScope.LEAGUE, fixture.league_id),
                    (RecordScope.TEAM, team_id),
                ]:
                    if scope == RecordScope.LEAGUE and not target_id:
                        continue
                    await RecordService._update_record(
                        scope=scope,
                        scope_target_id=target_id,
                        record_type=RecordType.MATCH_GOALS,
                        category=RecordCategory.PLAYER,
                        value_str=f"{goals}球",
                        value_num=float(goals),
                        holder_player_id=player_id,
                        holder_team_id=team_id,
                        fixture_id=fixture.id,
                        season_id=fixture.season_id,
                        match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                        db=db,
                    )

            # 单场助攻最多
            if assists > 0:
                for scope, target_id in [
                    (RecordScope.WORLD, None),
                    (RecordScope.LEAGUE, fixture.league_id),
                    (RecordScope.TEAM, team_id),
                ]:
                    if scope == RecordScope.LEAGUE and not target_id:
                        continue
                    await RecordService._update_record(
                        scope=scope,
                        scope_target_id=target_id,
                        record_type=RecordType.MATCH_ASSISTS,
                        category=RecordCategory.PLAYER,
                        value_str=f"{assists}次",
                        value_num=float(assists),
                        holder_player_id=player_id,
                        holder_team_id=team_id,
                        fixture_id=fixture.id,
                        season_id=fixture.season_id,
                        match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                        db=db,
                    )

    # ------------------------------------------------------------------
    # 3. 连胜/连败 streak 纪录
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_streak_records(fixture: Fixture, db: AsyncSession) -> None:
        """检测球队连胜、不败、连败纪录
        
        逻辑：查询该球队最近所有已完成的联赛比赛，计算当前 streak，
        然后与历史纪录比较。
        """
        for team_id in [fixture.home_team_id, fixture.away_team_id]:
            if not team_id:
                continue

            # 获取该球队所有已完成的联赛比赛（按时间倒序）
            result = await db.execute(
                select(Fixture).where(
                    and_(
                        Fixture.status == FixtureStatus.FINISHED,
                        Fixture.fixture_type == FixtureType.LEAGUE,
                        or_(
                            Fixture.home_team_id == team_id,
                            Fixture.away_team_id == team_id,
                        ),
                    )
                ).order_by(Fixture.scheduled_at.desc())
            )
            fixtures = list(result.scalars().all())

            if not fixtures:
                continue

            # 计算 streaks
            win_streak = 0
            unbeaten_streak = 0
            losing_streak = 0

            for f in fixtures:
                is_home = f.home_team_id == team_id
                home_score = f.home_score or 0
                away_score = f.away_score or 0

                if is_home:
                    team_score, opp_score = home_score, away_score
                else:
                    team_score, opp_score = away_score, home_score

                if team_score > opp_score:
                    win_streak += 1
                    unbeaten_streak += 1
                    losing_streak = 0
                elif team_score == opp_score:
                    win_streak = 0
                    unbeaten_streak += 1
                    losing_streak = 0
                else:
                    win_streak = 0
                    unbeaten_streak = 0
                    losing_streak += 1

            # 注意：以上计算包含了当前这场比赛，所以 streak 是当前的连续值
            # 但我们只关心是否打破了"最长"纪录，所以还需要历史最长值
            # 简化处理：直接比较当前 streak 与纪录

            streaks = [
                (RecordType.LONGEST_WIN_STREAK, win_streak, "连胜"),
                (RecordType.LONGEST_UNBEATEN, unbeaten_streak, "场不败"),
                (RecordType.LONGEST_LOSING_STREAK, losing_streak, "连败"),
            ]

            for record_type, streak_length, suffix in streaks:
                if streak_length < 2:
                    continue

                value_str = f"{streak_length}{suffix}"

                # WORLD scope
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=record_type,
                    category=RecordCategory.TEAM,
                    value_str=value_str,
                    value_num=float(streak_length),
                    holder_team_id=team_id,
                    season_id=fixture.season_id,
                    match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                    db=db,
                    context={"streak_length": streak_length},
                )

                # LEAGUE scope
                if fixture.league_id:
                    await RecordService._update_record(
                        scope=RecordScope.LEAGUE,
                        scope_target_id=fixture.league_id,
                        record_type=record_type,
                        category=RecordCategory.TEAM,
                        value_str=value_str,
                        value_num=float(streak_length),
                        holder_team_id=team_id,
                        season_id=fixture.season_id,
                        match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                        db=db,
                        context={"streak_length": streak_length},
                    )

                # TEAM scope
                await RecordService._update_record(
                    scope=RecordScope.TEAM,
                    scope_target_id=team_id,
                    record_type=record_type,
                    category=RecordCategory.TEAM,
                    value_str=value_str,
                    value_num=float(streak_length),
                    holder_team_id=team_id,
                    season_id=fixture.season_id,
                    match_date=fixture.scheduled_at.date() if fixture.scheduled_at else None,
                    db=db,
                    context={"streak_length": streak_length},
                )

    # ------------------------------------------------------------------
    # 4. 生涯累计纪录（基于 engine player_stats）
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_career_records_from_engine(
        fixture: Fixture,
        result: "MatchResult",
        db: AsyncSession,
    ) -> None:
        """检测球员生涯累计纪录"""
        # 需要聚合每个球员的累计数据
        # 由于 player_stats 是单场比赛的，我们需要查询 Player 表获取最新累计值
        player_ids = [ps.get("player_id") for ps in (result.player_stats or []) if ps.get("player_id")]
        if not player_ids:
            return

        player_result = await db.execute(
            select(Player).where(Player.id.in_(player_ids))
        )
        players = player_result.scalars().all()

        for player in players:
            # 生涯总进球
            if player.goals > 0:
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.CAREER_GOALS,
                    category=RecordCategory.PLAYER,
                    value_str=f"{player.goals}球",
                    value_num=float(player.goals),
                    holder_player_id=player.id,
                    holder_team_id=player.team_id,
                    season_id=fixture.season_id,
                    db=db,
                )

            # 生涯总助攻
            if player.assists > 0:
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.CAREER_ASSISTS,
                    category=RecordCategory.PLAYER,
                    value_str=f"{player.assists}次",
                    value_num=float(player.assists),
                    holder_player_id=player.id,
                    holder_team_id=player.team_id,
                    season_id=fixture.season_id,
                    db=db,
                )

            # 生涯出场
            if player.matches_played > 0:
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.CAREER_APPEARANCES,
                    category=RecordCategory.PLAYER,
                    value_str=f"{player.matches_played}场",
                    value_num=float(player.matches_played),
                    holder_player_id=player.id,
                    holder_team_id=player.team_id,
                    season_id=fixture.season_id,
                    db=db,
                )

            # 生涯黄牌
            if player.yellow_cards > 0:
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.CAREER_YELLOW_CARDS,
                    category=RecordCategory.PLAYER,
                    value_str=f"{player.yellow_cards}张",
                    value_num=float(player.yellow_cards),
                    holder_player_id=player.id,
                    holder_team_id=player.team_id,
                    season_id=fixture.season_id,
                    db=db,
                )

            # 生涯红牌
            if player.red_cards > 0:
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.CAREER_RED_CARDS,
                    category=RecordCategory.PLAYER,
                    value_str=f"{player.red_cards}张",
                    value_num=float(player.red_cards),
                    holder_player_id=player.id,
                    holder_team_id=player.team_id,
                    season_id=fixture.season_id,
                    db=db,
                )

            # 生涯场均评分（至少50场）
            if player.matches_played >= 50:
                rating = float(player.average_rating)
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.CAREER_RATING,
                    category=RecordCategory.PLAYER,
                    value_str=f"{rating:.1f}分",
                    value_num=rating,
                    holder_player_id=player.id,
                    holder_team_id=player.team_id,
                    season_id=fixture.season_id,
                    db=db,
                    context={"matches_played": player.matches_played},
                )

    # ------------------------------------------------------------------
    # 5. 赛季级纪录增量检测（每场比赛后调用）
    # ------------------------------------------------------------------

    @staticmethod
    async def _check_season_records_incremental(fixture: Fixture, db: AsyncSession) -> None:
        """每场比赛后检测当前赛季最佳纪录是否被刷新
        
        检测内容：
        - 球员单赛季进球/助攻/评分
        - 球队单赛季进球/失球/积分/胜场/零封
        """
        if not fixture.season_id:
            return

        season_id = fixture.season_id

        # ---- 球员单赛季纪录 ----
        # 查询本场比赛涉及的球员本赛季统计
        player_ids = []
        if fixture.home_team_id:
            home_result = await db.execute(
                select(Player.id).where(Player.team_id == fixture.home_team_id)
            )
            player_ids.extend([r[0] for r in home_result.all()])
        if fixture.away_team_id:
            away_result = await db.execute(
                select(Player.id).where(Player.team_id == fixture.away_team_id)
            )
            player_ids.extend([r[0] for r in away_result.all()])

        if player_ids:
            # 查询这些球员的赛季统计
            stats_result = await db.execute(
                select(PlayerSeasonStats, Player)
                .join(Player, PlayerSeasonStats.player_id == Player.id)
                .where(
                    and_(
                        PlayerSeasonStats.season_id == season_id,
                        PlayerSeasonStats.player_id.in_(player_ids),
                    )
                )
            )

            for stats, player in stats_result.all():
                # 单赛季进球
                if stats.goals > 0:
                    await RecordService._update_record(
                        scope=RecordScope.WORLD,
                        scope_target_id=None,
                        record_type=RecordType.SEASON_GOALS,
                        category=RecordCategory.PLAYER,
                        value_str=f"{stats.goals}球",
                        value_num=float(stats.goals),
                        holder_player_id=player.id,
                        holder_team_id=player.team_id,
                        season_id=season_id,
                        db=db,
                    )
                    if fixture.league_id:
                        await RecordService._update_record(
                            scope=RecordScope.LEAGUE,
                            scope_target_id=fixture.league_id,
                            record_type=RecordType.SEASON_GOALS,
                            category=RecordCategory.PLAYER,
                            value_str=f"{stats.goals}球",
                            value_num=float(stats.goals),
                            holder_player_id=player.id,
                            holder_team_id=player.team_id,
                            season_id=season_id,
                            db=db,
                        )
                    await RecordService._update_record(
                        scope=RecordScope.TEAM,
                        scope_target_id=player.team_id,
                        record_type=RecordType.SEASON_GOALS,
                        category=RecordCategory.PLAYER,
                        value_str=f"{stats.goals}球",
                        value_num=float(stats.goals),
                        holder_player_id=player.id,
                        holder_team_id=player.team_id,
                        season_id=season_id,
                        db=db,
                    )

                # 单赛季助攻
                if stats.assists > 0:
                    await RecordService._update_record(
                        scope=RecordScope.WORLD,
                        scope_target_id=None,
                        record_type=RecordType.SEASON_ASSISTS,
                        category=RecordCategory.PLAYER,
                        value_str=f"{stats.assists}次",
                        value_num=float(stats.assists),
                        holder_player_id=player.id,
                        holder_team_id=player.team_id,
                        season_id=season_id,
                        db=db,
                    )
                    if fixture.league_id:
                        await RecordService._update_record(
                            scope=RecordScope.LEAGUE,
                            scope_target_id=fixture.league_id,
                            record_type=RecordType.SEASON_ASSISTS,
                            category=RecordCategory.PLAYER,
                            value_str=f"{stats.assists}次",
                            value_num=float(stats.assists),
                            holder_player_id=player.id,
                            holder_team_id=player.team_id,
                            season_id=season_id,
                            db=db,
                        )

                # 单赛季评分（至少10场）
                if stats.matches_played >= 10:
                    rating = float(stats.average_rating)
                    await RecordService._update_record(
                        scope=RecordScope.WORLD,
                        scope_target_id=None,
                        record_type=RecordType.SEASON_RATING,
                        category=RecordCategory.PLAYER,
                        value_str=f"{rating:.1f}分",
                        value_num=rating,
                        holder_player_id=player.id,
                        holder_team_id=player.team_id,
                        season_id=season_id,
                        db=db,
                        context={"matches_played": stats.matches_played},
                    )

        # ---- 球队单赛季纪录 ----
        # 查询本场比赛涉及的球队本赛季 LeagueStanding
        team_ids = []
        if fixture.home_team_id:
            team_ids.append(fixture.home_team_id)
        if fixture.away_team_id:
            team_ids.append(fixture.away_team_id)

        if team_ids and fixture.league_id:
            standing_result = await db.execute(
                select(LeagueStanding, Team)
                .join(Team, LeagueStanding.team_id == Team.id)
                .where(
                    and_(
                        LeagueStanding.season_id == season_id,
                        LeagueStanding.league_id == fixture.league_id,
                        LeagueStanding.team_id.in_(team_ids),
                    )
                )
            )

            for standing, team in standing_result.all():
                # 单赛季球队进球最多
                if standing.goals_for > 0:
                    await RecordService._update_record(
                        scope=RecordScope.WORLD,
                        scope_target_id=None,
                        record_type=RecordType.SEASON_TEAM_GOALS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.goals_for}球",
                        value_num=float(standing.goals_for),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )
                    await RecordService._update_record(
                        scope=RecordScope.LEAGUE,
                        scope_target_id=fixture.league_id,
                        record_type=RecordType.SEASON_TEAM_GOALS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.goals_for}球",
                        value_num=float(standing.goals_for),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )
                    await RecordService._update_record(
                        scope=RecordScope.TEAM,
                        scope_target_id=team.id,
                        record_type=RecordType.SEASON_TEAM_GOALS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.goals_for}球",
                        value_num=float(standing.goals_for),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )

                # 单赛季失球最少（越小越好，存负数）
                await RecordService._update_record(
                    scope=RecordScope.WORLD,
                    scope_target_id=None,
                    record_type=RecordType.SEASON_TEAM_GOALS_AGAINST,
                    category=RecordCategory.TEAM,
                    value_str=f"{standing.goals_against}球",
                    value_num=-float(standing.goals_against),
                    holder_team_id=team.id,
                    season_id=season_id,
                    db=db,
                )
                await RecordService._update_record(
                    scope=RecordScope.LEAGUE,
                    scope_target_id=fixture.league_id,
                    record_type=RecordType.SEASON_TEAM_GOALS_AGAINST,
                    category=RecordCategory.TEAM,
                    value_str=f"{standing.goals_against}球",
                    value_num=-float(standing.goals_against),
                    holder_team_id=team.id,
                    season_id=season_id,
                    db=db,
                )
                await RecordService._update_record(
                    scope=RecordScope.TEAM,
                    scope_target_id=team.id,
                    record_type=RecordType.SEASON_TEAM_GOALS_AGAINST,
                    category=RecordCategory.TEAM,
                    value_str=f"{standing.goals_against}球",
                    value_num=-float(standing.goals_against),
                    holder_team_id=team.id,
                    season_id=season_id,
                    db=db,
                )

                # 单赛季积分最高
                if standing.points > 0:
                    await RecordService._update_record(
                        scope=RecordScope.WORLD,
                        scope_target_id=None,
                        record_type=RecordType.SEASON_TEAM_POINTS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.points}分",
                        value_num=float(standing.points),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )
                    await RecordService._update_record(
                        scope=RecordScope.LEAGUE,
                        scope_target_id=fixture.league_id,
                        record_type=RecordType.SEASON_TEAM_POINTS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.points}分",
                        value_num=float(standing.points),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )
                    await RecordService._update_record(
                        scope=RecordScope.TEAM,
                        scope_target_id=team.id,
                        record_type=RecordType.SEASON_TEAM_POINTS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.points}分",
                        value_num=float(standing.points),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )

                # 单赛季胜场最多
                if standing.won > 0:
                    await RecordService._update_record(
                        scope=RecordScope.WORLD,
                        scope_target_id=None,
                        record_type=RecordType.SEASON_TEAM_WINS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.won}场",
                        value_num=float(standing.won),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )
                    await RecordService._update_record(
                        scope=RecordScope.LEAGUE,
                        scope_target_id=fixture.league_id,
                        record_type=RecordType.SEASON_TEAM_WINS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.won}场",
                        value_num=float(standing.won),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )
                    await RecordService._update_record(
                        scope=RecordScope.TEAM,
                        scope_target_id=team.id,
                        record_type=RecordType.SEASON_TEAM_WINS,
                        category=RecordCategory.TEAM,
                        value_str=f"{standing.won}场",
                        value_num=float(standing.won),
                        holder_team_id=team.id,
                        season_id=season_id,
                        db=db,
                    )

    # ------------------------------------------------------------------
    # 6. 赛季级纪录批量计算
    # ------------------------------------------------------------------

    @staticmethod
    async def recalculate_season_records(season_id: str, db: AsyncSession) -> None:
        """赛季结束时批量计算所有赛季级纪录"""
        # ---- 球员单赛季纪录 ----
        await RecordService._recalculate_player_season_records(season_id, db)

        # ---- 球队单赛季纪录 ----
        await RecordService._recalculate_team_season_records(season_id, db)

        await db.commit()

    @staticmethod
    async def _recalculate_player_season_records(season_id: str, db: AsyncSession) -> None:
        """计算球员单赛季纪录：进球、助攻、评分"""
        # 单赛季进球最多
        top_scorer_result = await db.execute(
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                and_(
                    PlayerSeasonStats.season_id == season_id,
                    PlayerSeasonStats.goals > 0,
                )
            )
            .order_by(PlayerSeasonStats.goals.desc())
            .limit(1)
        )
        row = top_scorer_result.first()
        if row:
            stats, player = row
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_GOALS,
                category=RecordCategory.PLAYER,
                value_str=f"{stats.goals}球",
                value_num=float(stats.goals),
                holder_player_id=player.id,
                holder_team_id=player.team_id,
                season_id=season_id,
                db=db,
            )

        # 单赛季助攻最多
        top_assist_result = await db.execute(
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                and_(
                    PlayerSeasonStats.season_id == season_id,
                    PlayerSeasonStats.assists > 0,
                )
            )
            .order_by(PlayerSeasonStats.assists.desc())
            .limit(1)
        )
        row = top_assist_result.first()
        if row:
            stats, player = row
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_ASSISTS,
                category=RecordCategory.PLAYER,
                value_str=f"{stats.assists}次",
                value_num=float(stats.assists),
                holder_player_id=player.id,
                holder_team_id=player.team_id,
                season_id=season_id,
                db=db,
            )

        # 单赛季最高场均评分（至少10场）
        top_rating_result = await db.execute(
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                and_(
                    PlayerSeasonStats.season_id == season_id,
                    PlayerSeasonStats.matches_played >= 10,
                )
            )
            .order_by(PlayerSeasonStats.average_rating.desc())
            .limit(1)
        )
        row = top_rating_result.first()
        if row:
            stats, player = row
            rating = float(stats.average_rating)
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_RATING,
                category=RecordCategory.PLAYER,
                value_str=f"{rating:.1f}分",
                value_num=rating,
                holder_player_id=player.id,
                holder_team_id=player.team_id,
                season_id=season_id,
                db=db,
                context={"matches_played": stats.matches_played},
            )

    @staticmethod
    async def _recalculate_team_season_records(season_id: str, db: AsyncSession) -> None:
        """计算球队单赛季纪录：进球、失球、积分、胜场、零封"""
        # 单赛季进球最多
        top_goals_result = await db.execute(
            select(LeagueStanding, Team)
            .join(Team, LeagueStanding.team_id == Team.id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(LeagueStanding.goals_for.desc())
            .limit(1)
        )
        row = top_goals_result.first()
        if row:
            standing, team = row
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_TEAM_GOALS,
                category=RecordCategory.TEAM,
                value_str=f"{standing.goals_for}球",
                value_num=float(standing.goals_for),
                holder_team_id=team.id,
                season_id=season_id,
                db=db,
            )

        # 单赛季失球最少
        top_ga_result = await db.execute(
            select(LeagueStanding, Team)
            .join(Team, LeagueStanding.team_id == Team.id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(LeagueStanding.goals_against.asc())
            .limit(1)
        )
        row = top_ga_result.first()
        if row:
            standing, team = row
            # 失球越少越好，存负数
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_TEAM_GOALS_AGAINST,
                category=RecordCategory.TEAM,
                value_str=f"{standing.goals_against}球",
                value_num=-float(standing.goals_against),
                holder_team_id=team.id,
                season_id=season_id,
                db=db,
            )

        # 单赛季积分最高
        top_points_result = await db.execute(
            select(LeagueStanding, Team)
            .join(Team, LeagueStanding.team_id == Team.id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(LeagueStanding.points.desc())
            .limit(1)
        )
        row = top_points_result.first()
        if row:
            standing, team = row
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_TEAM_POINTS,
                category=RecordCategory.TEAM,
                value_str=f"{standing.points}分",
                value_num=float(standing.points),
                holder_team_id=team.id,
                season_id=season_id,
                db=db,
            )

        # 单赛季胜场最多
        top_wins_result = await db.execute(
            select(LeagueStanding, Team)
            .join(Team, LeagueStanding.team_id == Team.id)
            .where(LeagueStanding.season_id == season_id)
            .order_by(LeagueStanding.won.desc())
            .limit(1)
        )
        row = top_wins_result.first()
        if row:
            standing, team = row
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_TEAM_WINS,
                category=RecordCategory.TEAM,
                value_str=f"{standing.won}场",
                value_num=float(standing.won),
                holder_team_id=team.id,
                season_id=season_id,
                db=db,
            )

        # 单赛季零封最多（GK）
        top_cs_result = await db.execute(
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                and_(
                    PlayerSeasonStats.season_id == season_id,
                    Player.position == PlayerPosition.GK,
                    PlayerSeasonStats.clean_sheets > 0,
                )
            )
            .order_by(PlayerSeasonStats.clean_sheets.desc())
            .limit(1)
        )
        row = top_cs_result.first()
        if row:
            stats, player = row
            await RecordService._update_record(
                scope=RecordScope.WORLD,
                scope_target_id=None,
                record_type=RecordType.SEASON_CLEAN_SHEETS,
                category=RecordCategory.TEAM,
                value_str=f"{stats.clean_sheets}场",
                value_num=float(stats.clean_sheets),
                holder_player_id=player.id,
                holder_team_id=player.team_id,
                season_id=season_id,
                db=db,
            )

    # ------------------------------------------------------------------
    # 底层工具方法
    # ------------------------------------------------------------------

    @staticmethod
    async def _update_record(
        scope: RecordScope,
        scope_target_id: Optional[str],
        record_type: RecordType,
        category: RecordCategory,
        value_str: str,
        value_num: float,
        holder_player_id: Optional[str] = None,
        holder_team_id: Optional[str] = None,
        fixture_id: Optional[str] = None,
        season_id: Optional[str] = None,
        match_date: Optional[date] = None,
        context: Optional[dict] = None,
        db: AsyncSession = None,
    ) -> bool:
        """通用更新逻辑：如果新数值打破纪录，则创建或更新纪录
        
        Returns: 是否更新了纪录
        """
        if not db:
            return False

        # 查询现有纪录
        result = await db.execute(
            select(Record).where(
                and_(
                    Record.scope == scope,
                    Record.record_type == record_type,
                    Record.scope_target_id == scope_target_id,
                )
            )
        )
        record = result.scalar_one_or_none()

        is_better = False
        if not record:
            is_better = True
        elif record_type in RECORD_TYPES_LOWER_IS_BETTER:
            is_better = value_num > record.record_value_numeric
        else:
            is_better = value_num > record.record_value_numeric

        if is_better:
            if not record:
                record = Record(
                    scope=scope,
                    scope_target_id=scope_target_id,
                    category=category,
                    record_type=record_type,
                    record_value=value_str,
                    record_value_numeric=Decimal(str(value_num)),
                    holder_player_id=holder_player_id,
                    holder_team_id=holder_team_id,
                    fixture_id=fixture_id,
                    season_id=season_id,
                    match_date=match_date,
                    context=context or {},
                )
                db.add(record)
            else:
                record.record_value = value_str
                record.record_value_numeric = Decimal(str(value_num))
                record.holder_player_id = holder_player_id
                record.holder_team_id = holder_team_id
                record.fixture_id = fixture_id
                record.season_id = season_id
                record.match_date = match_date
                record.context = context or {}
                record.updated_at = datetime.utcnow()

            await db.flush()
            return True

        return False

    @staticmethod
    async def _increment_record(
        scope: RecordScope,
        scope_target_id: Optional[str],
        record_type: RecordType,
        category: RecordCategory,
        holder_player_id: Optional[str] = None,
        holder_team_id: Optional[str] = None,
        fixture_id: Optional[str] = None,
        season_id: Optional[str] = None,
        db: AsyncSession = None,
        increment: int = 1,
        unit: str = "次",
    ) -> bool:
        """累加型纪录（如帽子戏法次数）：每次符合条件就 +1
        
        与 _update_record 不同，这里只要同一保持者就累加，
        如果保持者变了则取较大值。
        """
        if not db:
            return False

        result = await db.execute(
            select(Record).where(
                and_(
                    Record.scope == scope,
                    Record.record_type == record_type,
                    Record.scope_target_id == scope_target_id,
                )
            )
        )
        record = result.scalar_one_or_none()

        if not record:
            record = Record(
                scope=scope,
                scope_target_id=scope_target_id,
                category=category,
                record_type=record_type,
                record_value=f"{increment}{unit}",
                record_value_numeric=Decimal(str(increment)),
                holder_player_id=holder_player_id,
                holder_team_id=holder_team_id,
                fixture_id=fixture_id,
                season_id=season_id,
                context={},
            )
            db.add(record)
            await db.flush()
            return True

        # 如果是同一保持者，累加
        same_holder = (
            record.holder_player_id == holder_player_id
            and record.holder_team_id == holder_team_id
        )

        if same_holder:
            new_val = float(record.record_value_numeric) + increment
            record.record_value = f"{int(new_val)}{unit}"
            record.record_value_numeric = Decimal(str(new_val))
            record.updated_at = datetime.utcnow()
            await db.flush()
            return True
        else:
            # 不同保持者，只保留较大值（这里累加型通常不需要比较，因为不同人不会共享次数）
            # 简化：如果当前值 >= 新值（increment），保持原纪录
            # 如果新保持者已经有更高的累计值...这情况较复杂，暂时不处理
            return False
