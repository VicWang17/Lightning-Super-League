"""
Honor service - 荣誉系统业务逻辑
处理球队荣誉的授予、查询和世界排名计算
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from app.models.team_honor import TeamHonor, HonorType
from app.models.team import Team
from app.models.league import League, LeagueStanding
from app.models.season import Season, CupCompetition
from app.models.player import Player
from app.schemas.records import (
    TeamHonorItem,
    TeamHonorsResponse,
    WorldRankingItem,
    TopPlayerItem,
)


# 联赛级别权重映射
LEAGUE_LEVEL_WEIGHTS = {
    1: 10.0,   # 超级联赛
    2: 5.0,    # 甲级联赛
    3: 2.5,    # 乙级联赛
    4: 1.0,    # 丙级联赛
}

# 杯赛冠军积分
CUP_CHAMPION_POINTS = 500

# 近N个赛季计入排名
RANKING_SEASON_COUNT = 3


class HonorService:
    """荣誉服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def award_league_champion(
        self,
        team_id: str,
        season_id: str,
        league_id: str,
        league_name: str,
        league_level: int,
    ) -> TeamHonor:
        """授予联赛冠军荣誉"""
        honor = TeamHonor(
            team_id=team_id,
            season_id=season_id,
            honor_type=HonorType.LEAGUE_CHAMPION,
            competition_id=league_id,
            competition_name=league_name,
            competition_level=league_level,
        )
        self.db.add(honor)
        await self.db.flush()
        return honor

    async def award_cup_champion(
        self,
        team_id: str,
        season_id: str,
        cup_competition_id: str,
        cup_name: str,
    ) -> TeamHonor:
        """授予杯赛冠军荣誉"""
        honor = TeamHonor(
            team_id=team_id,
            season_id=season_id,
            honor_type=HonorType.CUP_CHAMPION,
            competition_id=cup_competition_id,
            competition_name=cup_name,
            competition_level=0,
        )
        self.db.add(honor)
        await self.db.flush()
        return honor

    async def get_team_honors(self, team_id: str) -> TeamHonorsResponse:
        """获取球队荣誉列表"""
        result = await self.db.execute(
            select(TeamHonor, Season)
            .join(Season, TeamHonor.season_id == Season.id)
            .where(TeamHonor.team_id == team_id)
            .order_by(desc(Season.season_number))
        )
        rows = result.all()

        honors: List[TeamHonorItem] = []
        league_titles = 0
        cup_titles = 0

        for honor, season in rows:
            if honor.honor_type == HonorType.LEAGUE_CHAMPION:
                league_titles += 1
            elif honor.honor_type == HonorType.CUP_CHAMPION:
                cup_titles += 1

            honors.append(TeamHonorItem(
                season_number=season.season_number,
                honor_type=honor.honor_type.value,
                competition_name=honor.competition_name or "",
                competition_level=honor.competition_level,
            ))

        return TeamHonorsResponse(
            honors=honors,
            total_league_titles=league_titles,
            total_cup_titles=cup_titles,
        )

    async def calculate_world_rankings(self) -> List[WorldRankingItem]:
        """计算世界排名

        算法：
        1. 查询最近3个已结束赛季，不足则补充进行中赛季
        2. 对每个球队，计算联赛加权积分 = sum(赛季积分 × 联赛级别权重)
        3. 加上杯赛冠军积分 = 杯赛冠军数 × 500
        4. 按总分降序排列
        """
        # 获取最近3个已结束赛季
        season_result = await self.db.execute(
            select(Season)
            .where(Season.status == "finished")
            .order_by(desc(Season.season_number))
            .limit(RANKING_SEASON_COUNT)
        )
        seasons = list(season_result.scalars().all())

        # 如果已结束赛季不足3个，补充进行中赛季（按赛季号降序）
        if len(seasons) < RANKING_SEASON_COUNT:
            needed = RANKING_SEASON_COUNT - len(seasons)
            existing_ids = {s.id for s in seasons}
            ongoing_result = await self.db.execute(
                select(Season)
                .where(Season.status.in_(["ongoing", "pending"]))
                .where(Season.id.notin_(existing_ids) if existing_ids else True)
                .order_by(desc(Season.season_number))
                .limit(needed)
            )
            seasons.extend(ongoing_result.scalars().all())

        season_ids = [s.id for s in seasons]

        if not season_ids:
            return []

        # 获取所有球队
        team_result = await self.db.execute(
            select(Team).order_by(Team.name)
        )
        teams = team_result.scalars().all()

        # 获取所有相关赛季的联赛积分和联赛级别
        standing_result = await self.db.execute(
            select(LeagueStanding, League)
            .join(League, LeagueStanding.league_id == League.id)
            .where(LeagueStanding.season_id.in_(season_ids))
        )
        standing_rows = standing_result.all()

        # 构建球队 -> [(points, level), ...] 映射
        team_league_scores: dict[str, List[tuple[int, int]]] = {}
        for standing, league in standing_rows:
            tid = standing.team_id
            if tid not in team_league_scores:
                team_league_scores[tid] = []
            team_league_scores[tid].append((standing.points, league.level))

        # 获取杯赛冠军数量
        cup_result = await self.db.execute(
            select(TeamHonor.team_id, func.count(TeamHonor.id))
            .where(TeamHonor.honor_type == HonorType.CUP_CHAMPION)
            .where(TeamHonor.season_id.in_(season_ids))
            .group_by(TeamHonor.team_id)
        )
        cup_counts = {tid: count for tid, count in cup_result.all()}

        # 计算排名
        rankings: List[WorldRankingItem] = []
        for team in teams:
            tid = team.id
            league_score = 0.0

            # 联赛加权积分
            for points, level in team_league_scores.get(tid, []):
                weight = LEAGUE_LEVEL_WEIGHTS.get(level, 1.0)
                league_score += points * weight

            # 杯赛积分
            cup_count = cup_counts.get(tid, 0)
            cup_score = cup_count * CUP_CHAMPION_POINTS

            total_score = league_score + cup_score

            rankings.append(WorldRankingItem(
                rank=0,  # 稍后填充
                team_id=tid,
                team_name=team.name,
                total_score=round(total_score, 2),
                league_score=round(league_score, 2),
                cup_score=round(cup_score, 2),
                cup_titles=cup_count,
            ))

        # 按总分降序排列
        rankings.sort(key=lambda x: x.total_score, reverse=True)

        # 填充排名
        for idx, item in enumerate(rankings):
            item.rank = idx + 1

        return rankings

    async def get_top_players(
        self,
        limit: int = 100,
        position: Optional[str] = None,
    ) -> List[TopPlayerItem]:
        """获取球员OVR排行"""
        query = select(Player, Team).outerjoin(
            Team, Player.team_id == Team.id
        )

        if position:
            query = query.where(Player.position == position)

        query = query.order_by(desc(Player.ovr)).limit(limit)

        result = await self.db.execute(query)
        rows = result.all()

        rankings: List[TopPlayerItem] = []
        for idx, (player, team) in enumerate(rows):
            rankings.append(TopPlayerItem(
                rank=idx + 1,
                player_id=player.id,
                player_name=player.name,
                avatar_url=player.avatar_url,
                position=player.position.value if hasattr(player.position, "value") else str(player.position),
                age=player.age,
                ovr=player.ovr,
                team_name=team.name if team else "自由球员",
                team_id=team.id if team else "",
            ))

        return rankings
