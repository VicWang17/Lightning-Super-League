"""
Match simulator interface - 比赛模拟接口

TODO: 当前为「临时占位实现」，未来由 Go 实时比赛引擎替代。
当前局限性：纯随机比分，无实时推演，不支持用户战术干预。
Phase 2 后本文件职责：接收 Go 引擎结果，写入数据库（apply_result 等）。
详见 services/match_engine_client.py 中的完整架构说明。
"""
import random
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import clock
from sqlalchemy import select, and_

from app.models.season import Fixture, FixtureStatus, FixtureType, CupGroup
from app.models.player import Player, PlayerPosition, PlayerStatus
from app.models.player_season_stats import PlayerSeasonStats
from app.models.team import Team
from app.services.standing_service import StandingService
from app.services.player_state_service import PlayerStateService
from app.core.logging import get_logger

logger = get_logger("app.match_simulator")


@dataclass
class MatchEvent:
    """比赛事件"""
    player_id: str
    event_type: str  # goal, assist, yellow_card, red_card, clean_sheet
    team_id: str


@dataclass
class MatchResult:
    """比赛结果"""
    fixture_id: str
    home_score: int
    away_score: int
    home_possession: Optional[int] = None
    away_possession: Optional[int] = None
    home_shots: Optional[int] = None
    away_shots: Optional[int] = None
    home_shots_on_target: Optional[int] = None
    away_shots_on_target: Optional[int] = None
    mvp_player_id: Optional[str] = None
    events: Optional[list] = None  # 比赛事件（进球、红黄牌等）
    winner_team_id: Optional[str] = None
    resolution: str = "regular"
    penalty_score: Optional[dict] = None
    match_stats: Optional[dict] = None
    player_stats: Optional[list] = None
    narratives: Optional[list] = None
    engine_raw: Optional[dict] = None


class MatchSimulator:
    """比赛模拟器"""
    
    @staticmethod
    def from_engine_result(fixture: Fixture, engine_result: dict[str, Any]) -> MatchResult:
        """Convert Go engine SimulateResult into the backend result shape."""
        score = engine_result.get("score") or {}
        stats = engine_result.get("stats") or {}
        return MatchResult(
            fixture_id=fixture.id,
            home_score=int(score.get("home", 0)),
            away_score=int(score.get("away", 0)),
            home_possession=round(stats.get("possession_home", 0)) if stats else None,
            away_possession=round(stats.get("possession_away", 0)) if stats else None,
            home_shots=stats.get("shots_home"),
            away_shots=stats.get("shots_away"),
            home_shots_on_target=stats.get("shots_on_target_home"),
            away_shots_on_target=stats.get("shots_on_target_away"),
            events=engine_result.get("events") or [],
            winner_team_id=engine_result.get("winner_team_id") or None,
            resolution=engine_result.get("resolution") or "regular",
            penalty_score=engine_result.get("penalty_score"),
            match_stats=stats,
            player_stats=engine_result.get("player_stats") or [],
            narratives=engine_result.get("narratives") or [],
            engine_raw=engine_result,
        )
    
    @staticmethod
    async def simulate(fixture: Fixture) -> MatchResult:
        """模拟单场比赛 - 纯随机比分"""
        home_score = random.randint(0, 4)
        away_score = random.randint(0, 4)
        
        return MatchResult(
            fixture_id=fixture.id,
            home_score=home_score,
            away_score=away_score,
            home_possession=random.randint(40, 60),
            away_possession=100 - random.randint(40, 60),
            home_shots=random.randint(5, 20),
            away_shots=random.randint(5, 20),
            home_shots_on_target=random.randint(2, 10),
            away_shots_on_target=random.randint(2, 10),
            mvp_player_id=None,
            events=[]
        )
    
    @staticmethod
    async def apply_result(
        fixture: Fixture, 
        result: MatchResult, 
        db: AsyncSession = None
    ) -> None:
        """将比赛结果应用到Fixture并更新积分榜、球员统计"""
        fixture.home_score = result.home_score
        fixture.away_score = result.away_score
        fixture.status = FixtureStatus.FINISHED
        fixture.finished_at = clock.now()
        
        # 更新积分榜（联赛比赛）
        if db and fixture.fixture_type == FixtureType.LEAGUE:
            standing_service = StandingService(db)
            await standing_service.update_from_fixture(fixture)
            # 重新计算排名
            await standing_service.recalculate_positions(
                fixture.league_id, fixture.season_id
            )
        
        # 更新杯赛小组赛积分榜
        if db and fixture.fixture_type == FixtureType.CUP_LIGHTNING_GROUP:
            await MatchSimulator._update_cup_group_standing(fixture, db)
        
        # 更新球员赛季统计
        if db and fixture.season_id:
            if result.engine_raw:
                await MatchSimulator._persist_engine_result(fixture, result, db)
                await MatchSimulator._update_player_stats_from_engine(fixture, result, db)
                await MatchSimulator._update_player_match_state(fixture, result, db)
            else:
                await MatchSimulator._update_player_stats(fixture, db, result)
                await MatchSimulator._update_player_match_state(fixture, result, db)
        
        # 检测并更新纪录
        if db:
            from app.services.record_service import RecordService
            await RecordService.process_match_records(fixture, result, db)
    
    @staticmethod
    async def _update_player_stats(fixture: Fixture, db: AsyncSession, result: Optional[MatchResult] = None) -> None:
        """更新球员赛季统计
        
        Args:
            result: 如果传入，会将生成的 player_stats 写回 result，供纪录检测使用
        """
        # 获取双方球队球员
        home_players = await MatchSimulator._get_team_players(db, fixture.home_team_id)
        away_players = await MatchSimulator._get_team_players(db, fixture.away_team_id)
        
        if not home_players or not away_players:
            return
        
        # 生成比赛事件
        events = MatchSimulator._generate_match_events(
            fixture, home_players, away_players
        )
        
        # 获取球员对应的 team_id 和 league_id
        team_map = {
            fixture.home_team_id: fixture.home_team_id,
            fixture.away_team_id: fixture.away_team_id,
        }
        league_id = fixture.league_id
        cup_competition_id = fixture.cup_competition_id
        
        # 按球员聚合事件
        player_events: Dict[str, list[MatchEvent]] = {}
        for event in events:
            if event.player_id not in player_events:
                player_events[event.player_id] = []
            player_events[event.player_id].append(event)
        
        # 构建 player_stats 列表（供纪录检测使用）
        player_stats_for_records: list[dict] = []
        
        # 更新每个球员的赛季统计
        for player_id, player_event_list in player_events.items():
            stats = await MatchSimulator._get_or_create_player_season_stats(
                db, player_id, fixture.season_id, league_id=league_id, cup_competition_id=cup_competition_id
            )
            
            # 更新球队和联赛/杯赛信息（取最新）
            for event in player_event_list:
                stats.team_id = event.team_id
            if league_id:
                stats.league_id = league_id
            if cup_competition_id:
                stats.cup_competition_id = cup_competition_id
            
            goals = sum(1 for e in player_event_list if e.event_type == "goal")
            assists = sum(1 for e in player_event_list if e.event_type == "assist")
            yellow_cards = sum(1 for e in player_event_list if e.event_type == "yellow_card")
            red_cards = sum(1 for e in player_event_list if e.event_type == "red_card")
            clean_sheets = sum(1 for e in player_event_list if e.event_type == "clean_sheet")
            matches_played = 1 if any(e.event_type == "match_played" for e in player_event_list) else 0
            
            stats.goals += goals
            stats.assists += assists
            stats.yellow_cards += yellow_cards
            stats.red_cards += red_cards
            stats.clean_sheets += clean_sheets
            stats.matches_played += matches_played
            stats.minutes_played += matches_played * 90
            
            # 更新平均评分（简化：随机 5.5-8.5）
            new_rating = Decimal("6.0")
            if matches_played > 0:
                new_rating = Decimal(str(round(random.uniform(5.5, 8.5), 1)))
                # 加权移动平均
                total_minutes = stats.minutes_played
                old_minutes = total_minutes - 90
                if old_minutes > 0:
                    old_rating = stats.average_rating
                    stats.average_rating = (
                        (old_rating * Decimal(old_minutes / total_minutes)) +
                        (new_rating * Decimal(90 / total_minutes))
                    ).quantize(Decimal("0.1"))
                else:
                    stats.average_rating = new_rating
            
            # 收集 player_stats 供纪录检测使用
            # 确定球队 side
            team_id_for_player = player_event_list[0].team_id if player_event_list else None
            side = "home" if team_id_for_player == fixture.home_team_id else "away"
            player_stats_for_records.append({
                "player_id": player_id,
                "team": side,
                "goals": goals,
                "assists": assists,
                "yellow_cards": yellow_cards,
                "red_cards": red_cards,
                "rating": float(new_rating) if matches_played > 0 else 6.0,
            })
        
        await db.flush()
        
        # 将生成的 player_stats 写回 result，供纪录检测使用
        if result:
            result.player_stats = player_stats_for_records
            # 同时生成 events 供最快进球等纪录检测
            # 随机分配进球时间
            goal_events_for_records: list[dict] = []
            minute_counter = 1
            for ps in player_stats_for_records:
                for _ in range(ps.get("goals", 0)):
                    goal_events_for_records.append({
                        "type": "GOAL",
                        "player_id": ps["player_id"],
                        "team_id": fixture.home_team_id if ps["team"] == "home" else fixture.away_team_id,
                        "minute": minute_counter,
                        "second": random.randint(0, 59),
                    })
                    minute_counter += random.randint(5, 20)
            if goal_events_for_records:
                result.events = goal_events_for_records
    
    @staticmethod
    async def _get_team_players(db: AsyncSession, team_id: str) -> list[Player]:
        """获取球队所有球员"""
        result = await db.execute(
            select(Player).where(Player.team_id == team_id)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def _get_or_create_player_season_stats(
        db: AsyncSession, player_id: str, season_id: str,
        league_id: Optional[str] = None, cup_competition_id: Optional[str] = None
    ) -> PlayerSeasonStats:
        """获取或创建球员赛季统计记录
        
        支持联赛和杯赛独立统计：
        - 联赛比赛：league_id 有值，cup_competition_id 为 None
        - 杯赛比赛：cup_competition_id 有值，league_id 为 None
        """
        conditions = [
            PlayerSeasonStats.player_id == player_id,
            PlayerSeasonStats.season_id == season_id,
        ]
        
        if league_id:
            conditions.append(PlayerSeasonStats.league_id == league_id)
            conditions.append(PlayerSeasonStats.cup_competition_id.is_(None))
        elif cup_competition_id:
            conditions.append(PlayerSeasonStats.cup_competition_id == cup_competition_id)
            conditions.append(PlayerSeasonStats.league_id.is_(None))
        else:
            # 兼容旧数据，如果没有指定 league_id 或 cup_competition_id
            conditions.append(PlayerSeasonStats.league_id.is_(None))
            conditions.append(PlayerSeasonStats.cup_competition_id.is_(None))
        
        result = await db.execute(
            select(PlayerSeasonStats).where(and_(*conditions))
        )
        stats = result.scalar_one_or_none()
        if not stats:
            stats = PlayerSeasonStats(
                player_id=player_id,
                season_id=season_id,
                league_id=league_id,
                cup_competition_id=cup_competition_id,
                goals=0,
                assists=0,
                yellow_cards=0,
                red_cards=0,
                clean_sheets=0,
                matches_played=0,
                minutes_played=0,
                average_rating=Decimal("6.0")
            )
            db.add(stats)
            await db.flush()
        return stats
    
    @staticmethod
    def _generate_match_events(
        fixture: Fixture,
        home_players: list[Player],
        away_players: list[Player]
    ) -> list[MatchEvent]:
        """生成比赛事件"""
        events: list[MatchEvent] = []
        
        # 1. 选择上场球员（每队11人，不足则全部上场）
        home_starters = random.sample(home_players, min(11, len(home_players))) if home_players else []
        away_starters = random.sample(away_players, min(11, len(away_players))) if away_players else []
        
        for p in home_starters:
            events.append(MatchEvent(player_id=p.id, event_type="match_played", team_id=fixture.home_team_id))
        for p in away_starters:
            events.append(MatchEvent(player_id=p.id, event_type="match_played", team_id=fixture.away_team_id))
        
        # 2. 分配进球
        def _get_scorer_candidates(players: list[Player]) -> list[Player]:
            # 前锋/边锋/中场进球概率高，后卫/门将低
            weights = []
            for p in players:
                if p.position == PlayerPosition.FW:
                    weights.append(10)
                elif p.position == PlayerPosition.MF:
                    weights.append(6)
                elif p.position == PlayerPosition.GK:
                    weights.append(0.5)
                else:
                    weights.append(2)
            return players, weights
        
        if home_players:
            candidates, weights = _get_scorer_candidates(home_players)
            for _ in range(fixture.home_score or 0):
                scorer = random.choices(candidates, weights=weights, k=1)[0]
                events.append(MatchEvent(player_id=scorer.id, event_type="goal", team_id=fixture.home_team_id))
                
                # 助攻（70%概率）
                if random.random() < 0.7:
                    assist_candidates = [p for p in home_players if p.id != scorer.id]
                    if assist_candidates:
                        assist_weights = []
                        for p in assist_candidates:
                            if p.position == PlayerPosition.MF:
                                assist_weights.append(8)
                            else:
                                assist_weights.append(3)
                        assister = random.choices(assist_candidates, weights=assist_weights, k=1)[0]
                        events.append(MatchEvent(player_id=assister.id, event_type="assist", team_id=fixture.home_team_id))
        
        if away_players:
            candidates, weights = _get_scorer_candidates(away_players)
            for _ in range(fixture.away_score or 0):
                scorer = random.choices(candidates, weights=weights, k=1)[0]
                events.append(MatchEvent(player_id=scorer.id, event_type="goal", team_id=fixture.away_team_id))
                
                if random.random() < 0.7:
                    assist_candidates = [p for p in away_players if p.id != scorer.id]
                    if assist_candidates:
                        assist_weights = []
                        for p in assist_candidates:
                            if p.position == PlayerPosition.MF:
                                assist_weights.append(8)
                            else:
                                assist_weights.append(3)
                        assister = random.choices(assist_candidates, weights=assist_weights, k=1)[0]
                        events.append(MatchEvent(player_id=assister.id, event_type="assist", team_id=fixture.away_team_id))
        
        # 3. 黄牌/红牌（小概率）
        for p in home_starters + away_starters:
            if random.random() < 0.05:
                events.append(MatchEvent(player_id=p.id, event_type="yellow_card", team_id=p.team_id or ""))
            if random.random() < 0.01:
                events.append(MatchEvent(player_id=p.id, event_type="red_card", team_id=p.team_id or ""))
        
        # 4. 零封
        if fixture.away_score == 0:
            gks = [p for p in home_players if p.position == PlayerPosition.GK]
            if gks:
                keeper = random.choice(gks)
                events.append(MatchEvent(player_id=keeper.id, event_type="clean_sheet", team_id=fixture.home_team_id))
        
        if fixture.home_score == 0:
            gks = [p for p in away_players if p.position == PlayerPosition.GK]
            if gks:
                keeper = random.choice(gks)
                events.append(MatchEvent(player_id=keeper.id, event_type="clean_sheet", team_id=fixture.away_team_id))
        
        return events
    
    @staticmethod
    async def _update_cup_group_standing(fixture: Fixture, db: AsyncSession) -> None:
        """更新杯赛小组赛小组积分榜"""
        if not fixture.cup_competition_id or not fixture.cup_group_name:
            return
        
        # 获取小组信息
        result = await db.execute(
            select(CupGroup).where(
                and_(
                    CupGroup.competition_id == fixture.cup_competition_id,
                    CupGroup.name == fixture.cup_group_name
                )
            )
        )
        group = result.scalar_one_or_none()
        
        if not group:
            return
        
        # 初始化或获取现有积分榜
        standings = group.standings or {}
        
        # 确保每个球队都有积分榜记录
        for team_id in [fixture.home_team_id, fixture.away_team_id]:
            if team_id not in standings:
                standings[team_id] = {
                    "played": 0,
                    "won": 0,
                    "drawn": 0,
                    "lost": 0,
                    "goals_for": 0,
                    "goals_against": 0,
                    "points": 0
                }
        
        home_standing = standings[fixture.home_team_id]
        away_standing = standings[fixture.away_team_id]
        
        # 更新比赛场次
        home_standing["played"] += 1
        away_standing["played"] += 1
        
        # 更新进球数
        home_standing["goals_for"] += fixture.home_score
        home_standing["goals_against"] += fixture.away_score
        away_standing["goals_for"] += fixture.away_score
        away_standing["goals_against"] += fixture.home_score
        
        # 计算胜负平
        if fixture.home_score > fixture.away_score:
            home_standing["won"] += 1
            home_standing["points"] += 3
            away_standing["lost"] += 1
        elif fixture.home_score < fixture.away_score:
            away_standing["won"] += 1
            away_standing["points"] += 3
            home_standing["lost"] += 1
        else:
            home_standing["drawn"] += 1
            home_standing["points"] += 1
            away_standing["drawn"] += 1
            away_standing["points"] += 1
        
        # 保存更新后的积分榜
        group.standings = standings
        await db.flush()

    @staticmethod
    async def _persist_engine_result(fixture: Fixture, result: MatchResult, db: AsyncSession) -> None:
        """Persist raw Go engine output for replay and post-match pages."""
        from app.models.match_result import MatchResult as MatchResultModel

        existing = await db.execute(
            select(MatchResultModel).where(MatchResultModel.fixture_id == fixture.id)
        )
        obj = existing.scalar_one_or_none()
        payload = {
            "fixture_id": fixture.id,
            "engine_match_id": result.engine_raw.get("match_id", fixture.id),
            "home_score": result.home_score,
            "away_score": result.away_score,
            "winner_team_id": result.winner_team_id,
            "resolution": result.resolution,
            "penalty_score": result.penalty_score,
            "match_stats": result.match_stats or {},
            "player_stats": result.player_stats or [],
            "events": result.events or [],
            "narratives": result.narratives or [],
            "raw_result": result.engine_raw or {},
        }
        if obj:
            for key, value in payload.items():
                setattr(obj, key, value)
        else:
            db.add(MatchResultModel(**payload))
        await db.flush()

    @staticmethod
    async def _update_player_stats_from_engine(
        fixture: Fixture,
        result: MatchResult,
        db: AsyncSession,
    ) -> None:
        """Apply authoritative per-player stats returned by the Go engine."""
        if not result.player_stats:
            return

        team_for_side = {
            "home": fixture.home_team_id,
            "away": fixture.away_team_id,
        }
        minutes = 70 if result.resolution in {"extra_time", "penalties"} else 50

        for ps in result.player_stats:
            player_id = ps.get("player_id")
            if not player_id:
                continue

            team_id = team_for_side.get(ps.get("team"))
            stats = await MatchSimulator._get_or_create_player_season_stats(
                db,
                player_id,
                fixture.season_id,
                league_id=fixture.league_id,
                cup_competition_id=fixture.cup_competition_id,
            )
            stats.team_id = team_id
            stats.goals += int(ps.get("goals", 0))
            stats.assists += int(ps.get("assists", 0))
            stats.yellow_cards += int(ps.get("yellow_cards", 0))
            stats.red_cards += int(ps.get("red_cards", 0))
            if ps.get("position") == "GK":
                conceded = result.away_score if ps.get("team") == "home" else result.home_score
                if conceded == 0:
                    stats.clean_sheets += 1
            stats.matches_played += 1
            stats.minutes_played += minutes

            rating = Decimal(str(round(float(ps.get("rating", 6.0)), 1)))
            old_matches = max(stats.matches_played - 1, 0)
            if old_matches:
                stats.average_rating = (
                    (stats.average_rating * Decimal(old_matches) + rating)
                    / Decimal(stats.matches_played)
                ).quantize(Decimal("0.1"))
            else:
                stats.average_rating = rating

        await db.flush()

    @staticmethod
    async def _update_player_match_state(
        fixture: Fixture,
        result: MatchResult,
        db: AsyncSession,
    ) -> None:
        """赛后更新球员 fitness、match_rust_score 并触发状态重算"""
        if not result.player_stats:
            return
        
        # 获取双方球队所有球员
        home_players = await MatchSimulator._get_team_players(db, fixture.home_team_id)
        away_players = await MatchSimulator._get_team_players(db, fixture.away_team_id)
        all_players = {p.id: p for p in home_players + away_players}
        
        # 找出出场的球员
        played_player_ids = set()
        for ps in result.player_stats:
            player_id = ps.get("player_id")
            if player_id:
                played_player_ids.add(player_id)
        
        state_service = PlayerStateService(db)
        
        # 构建 player_stats 查找表
        stats_by_player = {
            ps.get("player_id"): ps
            for ps in result.player_stats
            if ps.get("player_id")
        }

        # 处理出场的球员
        for player_id in played_player_ids:
            player = all_players.get(player_id)
            if not player:
                continue
            
            ps = stats_by_player.get(player_id, {})
            
            # fitness 下降（设计文档 8.3）
            minutes = ps.get("minutes_played")
            if minutes is None:
                minutes = 70 if result.resolution in {"extra_time", "penalties"} else 50
            fitness_drop = 18 if minutes >= 70 else 12
            player.fitness = max(0, player.fitness - fitness_drop)
            
            # match_rust_score 恢复（栈式弹出）
            player.match_rust_score = min(player.match_rust_score + 1, 0)
            
            # 更新近期比赛滑动窗口
            rating = ps.get("rating")
            if rating is not None:
                ratings = player.recent_ratings or []
                ratings.append(float(rating))
                player.recent_ratings = ratings[-3:]
            
            minutes_list = player.recent_minutes or []
            minutes_list.append(int(minutes))
            player.recent_minutes = minutes_list[-3:]
            
            # 触发状态重算
            try:
                await state_service.recalculate_player_state(player_id, "match_finished")
            except Exception as exc:
                logger.warning(f"Failed to recalculate state for player {player_id}: {exc}")
        
        # 处理未出场的球员（非伤停/停赛）
        for player_id, player in all_players.items():
            if player_id in played_player_ids:
                continue
            if player.status in (PlayerStatus.INJURED, PlayerStatus.SUSPENDED):
                continue
            
            # fitness 恢复（设计文档 8.3 / 9.4）
            player.fitness = min(100, player.fitness + 5)
            
            # match_rust_score 下降（栈式压入）
            player.match_rust_score = max(player.match_rust_score - 1, -4)
            
            # 触发状态重算
            try:
                await state_service.recalculate_player_state(player_id, "match_finished")
            except Exception as exc:
                logger.warning(f"Failed to recalculate state for player {player_id}: {exc}")
        
        await db.flush()
