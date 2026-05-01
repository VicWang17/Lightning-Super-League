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
from sqlalchemy import select, and_

from app.models.season import Fixture, FixtureStatus, FixtureType, CupGroup
from app.models.player import Player, PlayerPosition
from app.models.player_season_stats import PlayerSeasonStats
from app.models.team import Team
from app.services.standing_service import StandingService


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


class MatchSimulator:
    """比赛模拟器"""
    
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
        fixture.finished_at = datetime.utcnow()
        
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
            await MatchSimulator._update_player_stats(fixture, db)
    
    @staticmethod
    async def _update_player_stats(fixture: Fixture, db: AsyncSession) -> None:
        """更新球员赛季统计"""
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
            
            # 同时更新 Player 表的累计数据
            player_result = await db.execute(
                select(Player).where(Player.id == player_id)
            )
            player = player_result.scalar_one_or_none()
            if player:
                player.goals += goals
                player.assists += assists
                player.yellow_cards += yellow_cards
                player.red_cards += red_cards
                player.matches_played += matches_played
                player.minutes_played += matches_played * 90
                if matches_played > 0:
                    total_mins = player.minutes_played
                    old_mins = total_mins - 90
                    if old_mins > 0:
                        old_avg = player.average_rating
                        new_avg = (
                            (old_avg * Decimal(old_mins / total_mins)) +
                            (new_rating * Decimal(90 / total_mins))
                        ).quantize(Decimal("0.1"))
                        player.average_rating = new_avg
                    else:
                        player.average_rating = new_rating
        
        await db.flush()
    
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
                if p.primary_position in (PlayerPosition.ST, PlayerPosition.CF, PlayerPosition.LF, PlayerPosition.RF):
                    weights.append(10)
                elif p.primary_position in (PlayerPosition.LW, PlayerPosition.RW, PlayerPosition.CAM, PlayerPosition.CM):
                    weights.append(6)
                elif p.primary_position == PlayerPosition.GK:
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
                            if p.primary_position in (PlayerPosition.CM, PlayerPosition.CAM, PlayerPosition.LM, PlayerPosition.RM, PlayerPosition.LW, PlayerPosition.RW):
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
                            if p.primary_position in (PlayerPosition.CM, PlayerPosition.CAM, PlayerPosition.LM, PlayerPosition.RM, PlayerPosition.LW, PlayerPosition.RW):
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
            gks = [p for p in home_players if p.primary_position == PlayerPosition.GK]
            if gks:
                keeper = random.choice(gks)
                events.append(MatchEvent(player_id=keeper.id, event_type="clean_sheet", team_id=fixture.home_team_id))
        
        if fixture.home_score == 0:
            gks = [p for p in away_players if p.primary_position == PlayerPosition.GK]
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
