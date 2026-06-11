"""
AwardService - 球员荣誉/奖项评选服务
"""
import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player_award import PlayerAward, AwardType, AwardLevel
from app.models.player_season_stats import PlayerSeasonStats
from app.models.player import Player, PlayerPosition
from app.models.team_honor import TeamHonor, HonorType
from app.models.team import Team
from app.models.season import Season
from app.models.match_result import MatchResult
from app.models.season import Fixture


class AwardService:
    """球员荣誉评选服务"""

    # ===== 评选触发接口 =====

    @staticmethod
    async def award_match_mvp(fixture_id: str, result: Any, db: AsyncSession) -> Optional[PlayerAward]:
        """评选单场 MVP 并入库

        result 可以是数据库 MatchResult 模型，也可以是 match_simulator 的 MatchResult dataclass。
        """
        stats = result.player_stats
        if not stats:
            return None

        # 提取评分和关键数据
        def _rating_key(s):
            rating = s.get("rating") or s.get("match_rating") or 0
            goals = s.get("goals", 0)
            assists = s.get("assists", 0)
            key_passes = s.get("key_passes", 0)
            tackles = s.get("tackles", 0)
            interceptions = s.get("interceptions", 0)
            saves = s.get("saves", 0)
            return (-float(rating), -goals, -assists, -(key_passes + tackles + interceptions + saves))

        sorted_stats = sorted(stats, key=_rating_key)
        winner = sorted_stats[0]
        winner_rating = winner.get("rating") or winner.get("match_rating") or 0

        if float(winner_rating) <= 0:
            return None

        player_id = winner.get("player_id")
        if not player_id:
            return None

        # 获取 fixture 和 season 信息
        fixture = await db.get(Fixture, fixture_id)
        if not fixture:
            return None
        season = await db.get(Season, fixture.season_id)
        if not season:
            return None

        # 确定球队名称（兼容 player_stats 中无 team_name 的情况）
        team_name = winner.get("team_name", "")
        opponent_name = ""
        if not team_name:
            winner_team_side = winner.get("team")
            if winner_team_side == "home":
                team_obj = await db.get(Team, fixture.home_team_id)
                opponent_obj = await db.get(Team, fixture.away_team_id)
            elif winner_team_side == "away":
                team_obj = await db.get(Team, fixture.away_team_id)
                opponent_obj = await db.get(Team, fixture.home_team_id)
            else:
                team_obj = None
                opponent_obj = None
            if team_obj:
                team_name = team_obj.name
            if opponent_obj:
                opponent_name = opponent_obj.name

        if not opponent_name:
            for s in stats:
                if s.get("player_id") != player_id:
                    other_name = s.get("team_name", "")
                    if other_name and other_name != team_name:
                        opponent_name = other_name
                        break

        description = f"第{season.season_number}赛季 第{fixture.season_day}天 {team_name} vs {opponent_name} 本场最佳"

        award = PlayerAward(
            id=str(uuid.uuid4()),
            player_id=player_id,
            season_id=fixture.season_id,
            season_number=season.season_number,
            award_type=AwardType.MATCH_MVP,
            award_level=AwardLevel.MATCH,
            fixture_id=fixture_id,
            award_metadata={
                "rating": float(winner_rating),
                "goals": winner.get("goals", 0),
                "assists": winner.get("assists", 0),
                "team": team_name,
                "opponent": opponent_name,
                "match_result": f"{result.home_score}:{result.away_score}",
            },
            description=description,
        )
        db.add(award)
        return award

    @staticmethod
    async def award_league_end_of_season(league_id: str, season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """联赛赛季结束后：评选最佳阵容 + 最佳位置球员 + 数据之王"""
        awards: List[PlayerAward] = []
        season = await db.get(Season, season_id)
        if not season:
            return awards

        # 1. 联赛最佳阵容 + 最佳位置
        team_awards, position_awards = await AwardService._award_league_team_and_positions(
            league_id, season_id, season.season_number, db
        )
        awards.extend(team_awards)
        awards.extend(position_awards)

        # 2. 联赛数据之王
        data_king_awards = await AwardService._award_league_data_kings(
            league_id, season_id, season.season_number, db
        )
        awards.extend(data_king_awards)

        return awards

    @staticmethod
    async def award_cup_end(cup_id: str, season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """杯赛结束后：评选杯赛数据之王"""
        awards: List[PlayerAward] = []
        season = await db.get(Season, season_id)
        if not season:
            return awards

        data_king_awards = await AwardService._award_cup_data_kings(
            cup_id, season_id, season.season_number, db
        )
        awards.extend(data_king_awards)

        return awards

    @staticmethod
    async def award_season_end(season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """整个赛季结束后：评选年度最佳球员 + 年度最佳位置 + 赛季数据之王"""
        awards: List[PlayerAward] = []
        season = await db.get(Season, season_id)
        if not season:
            return awards

        # 1. 年度最佳位置
        position_awards = await AwardService._award_season_best_positions(
            season_id, season.season_number, db
        )
        awards.extend(position_awards)

        # 2. 赛季数据之王
        data_king_awards = await AwardService._award_season_data_kings(
            season_id, season.season_number, db
        )
        awards.extend(data_king_awards)

        # 3. 年度最佳球员（闪电足球先生）
        best_player = await AwardService._award_season_best_player(
            season_id, season.season_number, db
        )
        if best_player:
            awards.append(best_player)

        return awards

    # ===== 查询接口 =====

    @staticmethod
    async def get_player_awards(player_id: str, db: AsyncSession) -> List[PlayerAward]:
        """获取某球员的全部荣誉"""
        result = await db.execute(
            select(PlayerAward)
            .where(PlayerAward.player_id == player_id)
            .order_by(PlayerAward.season_number.desc(), PlayerAward.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_player_award_summary(player_id: str, db: AsyncSession) -> Dict[str, int]:
        """获取球员荣誉统计摘要"""
        awards = await AwardService.get_player_awards(player_id, db)
        summary = {
            "total_awards": len(awards),
            "mvp_count": 0,
            "team_of_season_count": 0,
            "best_position_count": 0,
            "golden_boot_count": 0,
            "playmaker_count": 0,
            "golden_glove_count": 0,
            "golden_wall_count": 0,
            "season_best_player_count": 0,
        }
        for a in awards:
            t = a.award_type
            if t == AwardType.MATCH_MVP:
                summary["mvp_count"] += 1
            elif t == AwardType.LEAGUE_TEAM_OF_SEASON:
                summary["team_of_season_count"] += 1
            elif t in (AwardType.LEAGUE_BEST_FW, AwardType.LEAGUE_BEST_MF,
                       AwardType.LEAGUE_BEST_DF, AwardType.LEAGUE_BEST_GK,
                       AwardType.SEASON_BEST_FW, AwardType.SEASON_BEST_MF,
                       AwardType.SEASON_BEST_DF, AwardType.SEASON_BEST_GK):
                summary["best_position_count"] += 1
            elif t in (AwardType.LEAGUE_GOLDEN_BOOT, AwardType.CUP_GOLDEN_BOOT, AwardType.SEASON_GOLDEN_BOOT):
                summary["golden_boot_count"] += 1
            elif t in (AwardType.LEAGUE_PLAYMAKER, AwardType.CUP_PLAYMAKER, AwardType.SEASON_PLAYMAKER):
                summary["playmaker_count"] += 1
            elif t in (AwardType.LEAGUE_GOLDEN_GLOVE, AwardType.CUP_GOLDEN_GLOVE, AwardType.SEASON_GOLDEN_GLOVE):
                summary["golden_glove_count"] += 1
            elif t in (AwardType.LEAGUE_GOLDEN_WALL, AwardType.CUP_GOLDEN_WALL, AwardType.SEASON_GOLDEN_WALL):
                summary["golden_wall_count"] += 1
            elif t == AwardType.SEASON_BEST_PLAYER:
                summary["season_best_player_count"] += 1
        return summary

    @staticmethod
    async def get_season_awards(season_id: str, db: AsyncSession) -> Dict[AwardType, List[PlayerAward]]:
        """获取某赛季的全部奖项（按类型分组）"""
        result = await db.execute(
            select(PlayerAward)
            .where(PlayerAward.season_id == season_id)
            .order_by(PlayerAward.created_at.desc())
        )
        awards = result.scalars().all()
        grouped: Dict[AwardType, List[PlayerAward]] = {}
        for a in awards:
            grouped.setdefault(a.award_type, []).append(a)
        return grouped

    @staticmethod
    async def get_league_awards(league_id: str, season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """获取某联赛某赛季的全部奖项"""
        result = await db.execute(
            select(PlayerAward)
            .where(
                PlayerAward.league_id == league_id,
                PlayerAward.season_id == season_id,
            )
            .order_by(PlayerAward.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_cup_awards(cup_id: str, season_id: str, db: AsyncSession) -> List[PlayerAward]:
        """获取某杯赛某赛季的全部奖项"""
        result = await db.execute(
            select(PlayerAward)
            .where(
                PlayerAward.cup_id == cup_id,
                PlayerAward.season_id == season_id,
            )
            .order_by(PlayerAward.created_at.desc())
        )
        return result.scalars().all()

    # ===== 内部评选方法 =====

    @staticmethod
    async def _award_league_team_and_positions(
        league_id: str, season_id: str, season_number: int, db: AsyncSession
    ) -> tuple[List[PlayerAward], List[PlayerAward]]:
        """评选联赛最佳阵容和最佳位置球员"""
        team_awards: List[PlayerAward] = []
        position_awards: List[PlayerAward] = []

        query = (
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                PlayerSeasonStats.league_id == league_id,
                PlayerSeasonStats.season_id == season_id,
                PlayerSeasonStats.matches_played >= 10,
            )
        )
        result = await db.execute(query)
        rows = result.all()

        by_position: Dict[str, List[tuple[PlayerSeasonStats, Player]]] = {
            "FW": [], "MF": [], "DF": [], "GK": []
        }
        for stat, player in rows:
            pos = player.position.value if player.position else None
            if pos in by_position:
                by_position[pos].append((stat, player))

        # 按场均评分排序
        for pos in by_position:
            by_position[pos].sort(key=lambda x: -float(x[0].average_rating or 0))

        # 阵容配置
        slots = {
            "GK": 1,
            "DF": min(4, max(2, len(by_position["DF"]))),
            "MF": min(4, max(2, len(by_position["MF"]))),
            "FW": min(3, max(1, len(by_position["FW"]))),
        }

        for pos, count in slots.items():
            # 最佳位置（每个位置第一名）
            if by_position[pos]:
                stat, player = by_position[pos][0]
                award_type_map = {
                    "FW": AwardType.LEAGUE_BEST_FW,
                    "MF": AwardType.LEAGUE_BEST_MF,
                    "DF": AwardType.LEAGUE_BEST_DF,
                    "GK": AwardType.LEAGUE_BEST_GK,
                }
                position_awards.append(PlayerAward(
                    id=str(uuid.uuid4()),
                    player_id=player.id,
                    season_id=season_id,
                    season_number=season_number,
                    award_type=award_type_map[pos],
                    award_level=AwardLevel.LEAGUE,
                    league_id=league_id,
                    position=pos,
                    award_metadata={
                        "rating": float(stat.average_rating or 0),
                        "matches": stat.matches_played,
                        "goals": stat.goals,
                        "position": pos,
                    },
                    description=f"第{season_number}赛季 联赛最佳{pos}",
                ))

            # 最佳阵容
            for i in range(count):
                if i >= len(by_position[pos]):
                    break
                stat, player = by_position[pos][i]
                team_awards.append(PlayerAward(
                    id=str(uuid.uuid4()),
                    player_id=player.id,
                    season_id=season_id,
                    season_number=season_number,
                    award_type=AwardType.LEAGUE_TEAM_OF_SEASON,
                    award_level=AwardLevel.LEAGUE,
                    league_id=league_id,
                    position=pos,
                    award_metadata={
                        "rating": float(stat.average_rating or 0),
                        "matches": stat.matches_played,
                        "goals": stat.goals,
                        "position_rank": i + 1,
                    },
                    description=f"第{season_number}赛季 联赛最佳阵容",
                ))

        return team_awards, position_awards

    @staticmethod
    async def _award_league_data_kings(
        league_id: str, season_id: str, season_number: int, db: AsyncSession
    ) -> List[PlayerAward]:
        """评选联赛数据之王"""
        return await AwardService._award_data_kings(
            "league", league_id, season_id, season_number, db, min_matches=10
        )

    @staticmethod
    async def _award_cup_data_kings(
        cup_id: str, season_id: str, season_number: int, db: AsyncSession
    ) -> List[PlayerAward]:
        """评选杯赛数据之王"""
        return await AwardService._award_data_kings(
            "cup", cup_id, season_id, season_number, db, min_matches=3
        )

    @staticmethod
    async def _award_season_data_kings(
        season_id: str, season_number: int, db: AsyncSession
    ) -> List[PlayerAward]:
        """评选赛季数据之王（全服）"""
        return await AwardService._award_data_kings(
            "season", None, season_id, season_number, db, min_matches=10
        )

    @staticmethod
    async def _award_data_kings(
        scope_type: str,
        scope_id: Optional[str],
        season_id: str,
        season_number: int,
        db: AsyncSession,
        min_matches: int = 10,
    ) -> List[PlayerAward]:
        """通用数据之王评选"""
        ps = PlayerSeasonStats
        query = select(ps, Player).join(Player, ps.player_id == Player.id)

        if scope_type == "league":
            query = query.where(
                ps.league_id == scope_id,
                ps.season_id == season_id,
                ps.matches_played >= min_matches,
            )
        elif scope_type == "cup":
            query = query.where(
                ps.cup_competition_id == scope_id,
                ps.season_id == season_id,
                ps.matches_played >= min_matches,
            )
        else:  # season (全服)
            query = query.where(
                ps.season_id == season_id,
                ps.matches_played >= min_matches,
            )

        result = await db.execute(query)
        candidates = [(stat, player) for stat, player in result.all()]

        award_configs = [
            (
                AwardType.LEAGUE_GOLDEN_BOOT if scope_type == "league" else
                AwardType.CUP_GOLDEN_BOOT if scope_type == "cup" else
                AwardType.SEASON_GOLDEN_BOOT,
                lambda s: s.goals,
                "goals",
                lambda s: (-s.assists, -float(s.average_rating or 0)),
            ),
            (
                AwardType.LEAGUE_PLAYMAKER if scope_type == "league" else
                AwardType.CUP_PLAYMAKER if scope_type == "cup" else
                AwardType.SEASON_PLAYMAKER,
                lambda s: s.assists,
                "assists",
                lambda s: (-s.goals, -float(s.average_rating or 0)),
            ),
            (
                AwardType.LEAGUE_GOLDEN_GLOVE if scope_type == "league" else
                AwardType.CUP_GOLDEN_GLOVE if scope_type == "cup" else
                AwardType.SEASON_GOLDEN_GLOVE,
                lambda s: s.clean_sheets,
                "clean_sheets",
                lambda s: (-s.saves, -float(s.average_rating or 0)),
            ),
            (
                AwardType.LEAGUE_GOLDEN_WALL if scope_type == "league" else
                AwardType.CUP_GOLDEN_WALL if scope_type == "cup" else
                AwardType.SEASON_GOLDEN_WALL,
                lambda s: s.tackles + s.interceptions,
                "tackles_interceptions",
                lambda s: (-float(s.average_rating or 0), -s.clearances),
            ),
        ]

        awards: List[PlayerAward] = []
        for award_type, primary_key, meta_key, tie_breaker in award_configs:
            sorted_candidates = sorted(candidates, key=lambda x: (
                -primary_key(x[0]),
                *tie_breaker(x[0]),
            ))
            if not sorted_candidates:
                continue
            winner_stat, winner_player = sorted_candidates[0]
            primary_value = primary_key(winner_stat)
            if primary_value == 0:
                continue

            level = AwardLevel.LEAGUE if scope_type == "league" else AwardLevel.CUP if scope_type == "cup" else AwardLevel.SEASON

            metadata = {
                "primary_value": primary_value,
                "matches": winner_stat.matches_played,
                "goals": winner_stat.goals,
                "assists": winner_stat.assists,
                "rating": float(winner_stat.average_rating or 0),
            }

            kwargs: Dict[str, Any] = {
                "id": str(uuid.uuid4()),
                "player_id": winner_player.id,
                "season_id": season_id,
                "season_number": season_number,
                "award_type": award_type,
                "award_level": level,
                "metadata": metadata,
            }

            if scope_type == "league":
                kwargs["league_id"] = scope_id
            elif scope_type == "cup":
                kwargs["cup_id"] = scope_id

            awards.append(PlayerAward(**kwargs))

        return awards

    @staticmethod
    async def _award_season_best_positions(
        season_id: str, season_number: int, db: AsyncSession
    ) -> List[PlayerAward]:
        """评选年度最佳位置球员（全服）"""
        awards: List[PlayerAward] = []

        query = (
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                PlayerSeasonStats.season_id == season_id,
                PlayerSeasonStats.matches_played >= 10,
            )
        )
        result = await db.execute(query)
        rows = result.all()

        by_position: Dict[str, List[tuple[PlayerSeasonStats, Player]]] = {
            "FW": [], "MF": [], "DF": [], "GK": []
        }
        for stat, player in rows:
            pos = player.position.value if player.position else None
            if pos in by_position:
                by_position[pos].append((stat, player))

        award_type_map = {
            "FW": AwardType.SEASON_BEST_FW,
            "MF": AwardType.SEASON_BEST_MF,
            "DF": AwardType.SEASON_BEST_DF,
            "GK": AwardType.SEASON_BEST_GK,
        }

        for pos, items in by_position.items():
            if not items:
                continue
            # 按场均评分排序，取第一
            items.sort(key=lambda x: -float(x[0].average_rating or 0))
            stat, player = items[0]
            awards.append(PlayerAward(
                id=str(uuid.uuid4()),
                player_id=player.id,
                season_id=season_id,
                season_number=season_number,
                award_type=award_type_map[pos],
                award_level=AwardLevel.SEASON,
                position=pos,
                award_metadata={
                    "rating": float(stat.average_rating or 0),
                    "matches": stat.matches_played,
                    "goals": stat.goals,
                    "assists": stat.assists,
                },
                description=f"第{season_number}赛季 年度最佳{pos}",
            ))

        return awards

    @staticmethod
    async def _award_season_best_player(
        season_id: str, season_number: int, db: AsyncSession
    ) -> Optional[PlayerAward]:
        """评选年度最佳球员（闪电足球先生）"""
        # 1. 获取全服所有球员的赛季统计
        query = (
            select(PlayerSeasonStats, Player)
            .join(Player, PlayerSeasonStats.player_id == Player.id)
            .where(
                PlayerSeasonStats.season_id == season_id,
                PlayerSeasonStats.matches_played >= 10,
            )
        )
        result = await db.execute(query)
        rows = result.all()

        if not rows:
            return None

        # 2. 预加载该赛季所有奖项和球队荣誉
        award_result = await db.execute(
            select(PlayerAward).where(PlayerAward.season_id == season_id)
        )
        all_awards = award_result.scalars().all()

        honor_result = await db.execute(
            select(TeamHonor).where(TeamHonor.season_id == season_id)
        )
        all_honors = honor_result.scalars().all()

        # 3. 计算综合得分
        candidates = []
        for stat, player in rows:
            score = 0.0
            score += float(stat.average_rating or 0) * 15
            score += stat.matches_played * 0.2

            # MVP 次数
            mvp_count = sum(
                1 for a in all_awards
                if a.player_id == player.id and a.award_type == AwardType.MATCH_MVP
            )
            score += mvp_count * 3

            # 冠军数
            team_id = stat.team_id
            champ_count = sum(
                1 for h in all_honors
                if h.team_id == team_id and h.honor_type in (HonorType.LEAGUE_CHAMPION, HonorType.CUP_CHAMPION)
            )
            score += champ_count * 30

            # 联赛最佳阵容/最佳位置
            league_awards = [
                a for a in all_awards
                if a.player_id == player.id and a.award_level == AwardLevel.LEAGUE
            ]
            score += len([a for a in league_awards if a.award_type == AwardType.LEAGUE_TEAM_OF_SEASON]) * 10
            score += len([a for a in league_awards if AwardService._is_league_best_position(a.award_type)]) * 15

            candidates.append({
                "player": player,
                "stat": stat,
                "score": score,
                "metadata": {
                    "rating": float(stat.average_rating or 0),
                    "matches": stat.matches_played,
                    "goals": stat.goals,
                    "championships": champ_count,
                    "mvp_count": mvp_count,
                }
            })

        # 4. 取最高分
        candidates.sort(key=lambda x: -x["score"])
        winner = candidates[0]

        return PlayerAward(
            id=str(uuid.uuid4()),
            player_id=winner["player"].id,
            season_id=season_id,
            season_number=season_number,
            award_type=AwardType.SEASON_BEST_PLAYER,
            award_level=AwardLevel.SEASON,
            metadata=winner["metadata"],
            description=f"第{season_number}赛季 闪电足球先生",
        )

    @staticmethod
    def _is_league_best_position(award_type: AwardType) -> bool:
        return award_type in (
            AwardType.LEAGUE_BEST_FW,
            AwardType.LEAGUE_BEST_MF,
            AwardType.LEAGUE_BEST_DF,
            AwardType.LEAGUE_BEST_GK,
        )
