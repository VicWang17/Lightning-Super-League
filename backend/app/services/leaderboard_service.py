"""
Leaderboard service - 通用排行榜服务
支持联赛级和世界级的任意统计维度排行榜查询
"""
from typing import List, Optional, Any
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, cast, Float
from sqlalchemy.orm import selectinload

from app.models import PlayerSeasonStats, Player, Team, Season, League
from app.models.player import PlayerPosition
from app.models.season import SeasonStatus
from app.schemas.leaderboard import LeaderboardType, LeaderboardItem, LeaderboardConfig


# ==================== 排行榜配置表 ====================
# 计数类配置 (field_name: label, value_label, value_format, position_filter, min_matches_league, min_matches_world)
_COUNT_CONFIGS = {
    "goals": ("射手榜", "进球", "int", None, 0, 0),
    "assists": ("助攻榜", "助攻", "int", None, 0, 0),
    "clean_sheets": ("零封榜", "零封", "int", "GK", 0, 0),
    "saves": ("扑救榜", "扑救", "int", "GK", 0, 0),
    "tackles": ("抢断榜", "抢断", "int", None, 0, 0),
    "interceptions": ("拦截榜", "拦截", "int", None, 0, 0),
    "clearances": ("解围榜", "解围", "int", None, 0, 0),
    "blocks": ("封堵榜", "封堵", "int", None, 0, 0),
    "shots": ("射门榜", "射门", "int", None, 0, 0),
    "shots_on_target": ("射正榜", "射正", "int", None, 0, 0),
    "key_passes": ("关键传球榜", "关键传球", "int", None, 0, 0),
    "passes": ("传球榜", "传球", "int", None, 0, 0),
    "crosses": ("传中榜", "传中", "int", None, 0, 0),
    "dribbles": ("盘带榜", "盘带", "int", None, 0, 0),
    "yellow_cards": ("黄牌榜", "黄牌", "int", None, 0, 0),
    "red_cards": ("红牌榜", "红牌", "int", None, 0, 0),
    "fouls": ("犯规榜", "犯规", "int", None, 0, 0),
    "offsides": ("越位榜", "越位", "int", None, 0, 0),
    "touches": ("触球榜", "触球", "int", None, 0, 0),
    "free_kick_goals": ("任意球进球榜", "任意球进球", "int", None, 0, 0),
    "penalty_goals": ("点球进球榜", "点球进球", "int", None, 0, 0),
    "minutes_played": ("出场时间榜", "分钟", "int", None, 0, 0),
    "matches_played": ("出场榜", "场次", "int", None, 0, 0),
    "average_rating": ("场均评分榜", "评分", "float1", None, 3, 10),
}

# 率类配置 (type: numerator_field, denominator_field, label, value_label, value_format, position_filter, min_matches_league, min_matches_world)
_RATE_CONFIGS = {
    "shot_accuracy": ("shots_on_target", "shots", "射正率", "射正率", "percent", None, 3, 10),
    "pass_accuracy": ("passes_succ", "passes", "传球成功率", "传球成功率", "percent", None, 3, 10),
    "tackle_accuracy": ("tackles_succ", "tackles", "抢断成功率", "抢断成功率", "percent", None, 3, 10),
    "dribble_accuracy": ("dribbles_succ", "dribbles", "盘带成功率", "盘带成功率", "percent", None, 3, 10),
    "cross_accuracy": ("crosses_succ", "crosses", "传中成功率", "传中成功率", "percent", None, 3, 10),
    "header_accuracy": ("headers_succ", "headers", "头球成功率", "头球成功率", "percent", None, 3, 10),
    "goals_per_game": ("goals", "matches_played", "场均进球", "场均进球", "float1", None, 3, 10),
    "assists_per_game": ("assists", "matches_played", "场均助攻", "场均助攻", "float1", None, 3, 10),
}


def _build_configs() -> dict:
    """构建完整的配置字典，映射 type -> LeaderboardConfig"""
    configs = {}
    ps = PlayerSeasonStats
    
    # 计数类
    for field_name, (label, value_label, value_format, pos_filter, min_l, min_w) in _COUNT_CONFIGS.items():
        col = getattr(ps, field_name)
        lb_type = LeaderboardType(field_name)
        configs[lb_type] = LeaderboardConfig(
            type=lb_type,
            label=label,
            value_label=value_label,
            value_format=value_format,
            position_filter=pos_filter,
            min_matches_league=min_l,
            min_matches_world=min_w,
            is_rate=False,
            order_expr=col,
            value_expr=col,
        )
    
    # 率类
    for type_name, (num_field, den_field, label, value_label, value_format, pos_filter, min_l, min_w) in _RATE_CONFIGS.items():
        lb_type = LeaderboardType(type_name)
        configs[lb_type] = LeaderboardConfig(
            type=lb_type,
            label=label,
            value_label=value_label,
            value_format=value_format,
            position_filter=pos_filter,
            min_matches_league=min_l,
            min_matches_world=min_w,
            is_rate=True,
            order_expr=None,  # 由服务层动态构建
            value_expr=None,
        )
    
    return configs


LEADERBOARD_CONFIGS = _build_configs()


class LeaderboardService:
    """通用排行榜服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 赛季解析 ====================

    async def _resolve_season_for_league(self, league_id: str, season_id: Optional[str] = None) -> Optional[str]:
        """解析联赛对应的当前赛季ID"""
        if season_id:
            return season_id
        
        # 获取联赛所在 zone
        result = await self.db.execute(
            select(League).where(League.id == league_id)
        )
        league = result.scalar_one_or_none()
        if not league:
            return None
        
        zone_id = league.system.zone_id if league.system else 1
        
        season_result = await self.db.execute(
            select(Season)
            .where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
            .where(Season.zone_id == zone_id)
            .order_by(Season.start_date)
        )
        season = season_result.scalar_one_or_none()
        return str(season.id) if season else None

    async def _resolve_current_season_ids(self) -> List[str]:
        """解析当前全局赛季ID列表（跨 zone）"""
        # 先找 zone=1 的最新 ONGOING 赛季
        result = await self.db.execute(
            select(Season)
            .where(Season.status == SeasonStatus.ONGOING)
            .where(Season.zone_id == 1)
            .order_by(Season.start_date.desc())
            .limit(1)
        )
        season = result.scalar_one_or_none()
        
        if not season:
            # 没有 ONGOING，取最近 FINISHED
            result = await self.db.execute(
                select(Season)
                .where(Season.status == SeasonStatus.FINISHED)
                .order_by(Season.start_date.desc())
                .limit(1)
            )
            season = result.scalar_one_or_none()
        
        if not season:
            return []
        
        # 取同 season_number 的所有 zone 的赛季
        result = await self.db.execute(
            select(Season.id)
            .where(Season.season_number == season.season_number)
        )
        return [str(r[0]) for r in result.all()]

    # ==================== 杯赛级排行榜 ====================

    async def get_cup_leaderboard(
        self,
        cup_id: str,
        season_id: str,
        lb_type: LeaderboardType,
        limit: int = 20,
    ) -> List[LeaderboardItem]:
        """获取杯赛级排行榜"""
        config = LEADERBOARD_CONFIGS.get(lb_type)
        if not config:
            return []
        
        ps = PlayerSeasonStats
        player = Player
        team = Team
        
        # 构建排序表达式
        if config.is_rate:
            order_expr = self._build_league_rate_expr(lb_type)
            value_expr = order_expr
        else:
            order_expr = config.order_expr
            value_expr = config.value_expr
        
        # 基础查询：按 cup_competition_id 过滤
        query = (
            select(
                player,
                team,
                value_expr.label("stat_value"),
                ps.matches_played.label("matches"),
            )
            .join(ps, player.id == ps.player_id)
            .outerjoin(team, ps.team_id == team.id)
            .where(
                and_(
                    ps.cup_competition_id == cup_id,
                    ps.season_id == season_id,
                )
            )
        )
        
        # 位置过滤
        if config.position_filter:
            query = query.where(player.position == PlayerPosition(config.position_filter))
        
        # 场次门槛（杯赛使用联赛级门槛）
        min_matches = config.min_matches_league
        if min_matches > 0:
            query = query.where(ps.matches_played >= min_matches)
        
        # 对于率类，需要额外过滤分母 > 0
        if config.is_rate:
            den_field = self._get_rate_denominator_field(lb_type)
            if den_field:
                query = query.where(den_field > 0)
        
        # 排序
        query = query.order_by(desc(order_expr)).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        items = []
        for idx, (p, t, stat_value, matches) in enumerate(rows):
            items.append(LeaderboardItem(
                rank=idx + 1,
                player_id=str(p.id),
                player_name=p.name,
                avatar_url=p.avatar_url,
                position=p.position.value if hasattr(p.position, "value") else str(p.position),
                team_name=t.name if t else "未知球队",
                team_id=str(t.id) if t else "",
                value=self._format_value(stat_value, config.value_format),
                value_label=config.value_label,
                matches=matches or 0,
            ))
        
        return items

    # ==================== 联赛级排行榜 ====================

    async def get_league_leaderboard(
        self,
        league_id: str,
        season_id: Optional[str],
        lb_type: LeaderboardType,
        limit: int = 20,
    ) -> List[LeaderboardItem]:
        """获取联赛级排行榜"""
        config = LEADERBOARD_CONFIGS.get(lb_type)
        if not config:
            return []
        
        resolved_season_id = await self._resolve_season_for_league(league_id, season_id)
        if not resolved_season_id:
            return []
        
        ps = PlayerSeasonStats
        player = Player
        team = Team
        
        # 构建排序表达式
        if config.is_rate:
            order_expr = self._build_league_rate_expr(lb_type)
            value_expr = order_expr
        else:
            order_expr = config.order_expr
            value_expr = config.value_expr
        
        # 基础查询
        query = (
            select(
                player,
                team,
                value_expr.label("stat_value"),
                ps.matches_played.label("matches"),
            )
            .join(ps, player.id == ps.player_id)
            .outerjoin(team, ps.team_id == team.id)
            .where(
                and_(
                    ps.league_id == league_id,
                    ps.season_id == resolved_season_id,
                )
            )
        )
        
        # 位置过滤
        if config.position_filter:
            query = query.where(player.position == PlayerPosition(config.position_filter))
        
        # 场次门槛
        min_matches = config.min_matches_league
        if min_matches > 0:
            query = query.where(ps.matches_played >= min_matches)
        
        # 对于率类，需要额外过滤分母 > 0
        if config.is_rate:
            den_field = self._get_rate_denominator_field(lb_type)
            if den_field:
                query = query.where(den_field > 0)
        
        # 排序
        query = query.order_by(desc(order_expr)).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        items = []
        for idx, (p, t, stat_value, matches) in enumerate(rows):
            items.append(LeaderboardItem(
                rank=idx + 1,
                player_id=str(p.id),
                player_name=p.name,
                avatar_url=p.avatar_url,
                position=p.position.value if hasattr(p.position, "value") else str(p.position),
                team_name=t.name if t else "未知球队",
                team_id=str(t.id) if t else "",
                value=self._format_value(stat_value, config.value_format),
                value_label=config.value_label,
                matches=matches or 0,
            ))
        
        return items

    # ==================== 世界级排行榜 ====================

    async def get_world_leaderboard(
        self,
        lb_type: LeaderboardType,
        limit: int = 100,
        position: Optional[str] = None,
    ) -> List[LeaderboardItem]:
        """获取世界级排行榜（ career 累计，跨赛季、跨赛事）"""
        config = LEADERBOARD_CONFIGS.get(lb_type)
        if not config:
            return []
        
        ps = PlayerSeasonStats
        player = Player
        team = Team
        
        # 构建聚合表达式
        if config.is_rate:
            value_expr = self._build_world_rate_expr(lb_type)
            order_expr = value_expr
            matches_expr = func.coalesce(func.sum(ps.matches_played), 0).label("matches")
        else:
            value_expr = func.coalesce(func.sum(config.order_expr), 0).label("stat_value")
            order_expr = value_expr
            matches_expr = func.coalesce(func.sum(ps.matches_played), 0).label("matches")
        
        # 基础聚合查询：世界榜统计所有赛季、所有赛事的 career 累计
        query = (
            select(
                player,
                team,
                value_expr,
                matches_expr,
            )
            .outerjoin(team, player.team_id == team.id)
            .join(ps, player.id == ps.player_id)
            .group_by(player.id, team.id)
        )
        
        # 位置过滤（优先用传入参数，其次用配置）
        pos_filter = position or config.position_filter
        if pos_filter:
            query = query.where(player.position == PlayerPosition(pos_filter))
        
        # 场次门槛
        min_matches = config.min_matches_world
        if min_matches > 0:
            query = query.having(func.coalesce(func.sum(ps.matches_played), 0) >= min_matches)
        
        # 对于率类，过滤分母总和 > 0
        if config.is_rate:
            den_field = self._get_rate_denominator_field(lb_type)
            if den_field:
                query = query.having(func.coalesce(func.sum(den_field), 0) > 0)
        
        # 排序
        query = query.order_by(desc(order_expr)).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        items = []
        for idx, (p, t, stat_value, matches) in enumerate(rows):
            items.append(LeaderboardItem(
                rank=idx + 1,
                player_id=str(p.id),
                player_name=p.name,
                avatar_url=p.avatar_url,
                position=p.position.value if hasattr(p.position, "value") else str(p.position),
                team_name=t.name if t else "未知球队",
                team_id=str(t.id) if t else "",
                value=self._format_value(stat_value, config.value_format),
                value_label=config.value_label,
                matches=matches or 0,
            ))
        
        return items

    # ==================== OVR 排名（世界页专用） ====================

    async def get_ovr_leaderboard(
        self,
        limit: int = 100,
        position: Optional[str] = None,
    ) -> List[LeaderboardItem]:
        """获取球员 OVR 排名（从 Player 表直接查询）"""
        player = Player
        team = Team
        
        query = (
            select(player, team)
            .outerjoin(team, player.team_id == team.id)
        )
        
        if position:
            query = query.where(player.position == PlayerPosition(position))
        
        query = query.order_by(desc(player.ovr)).limit(limit)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        items = []
        for idx, (p, t) in enumerate(rows):
            items.append(LeaderboardItem(
                rank=idx + 1,
                player_id=str(p.id),
                player_name=p.name,
                avatar_url=p.avatar_url,
                position=p.position.value if hasattr(p.position, "value") else str(p.position),
                team_name=t.name if t else "未知球队",
                team_id=str(t.id) if t else "",
                value=float(p.ovr),
                value_label="OVR",
                matches=0,
                age=p.age,
                ovr=int(p.ovr),
            ))
        
        return items

    # ==================== 辅助方法 ====================

    def _build_league_rate_expr(self, lb_type: LeaderboardType) -> Any:
        """构建联赛级率类排序表达式"""
        ps = PlayerSeasonStats
        type_name = lb_type.value
        
        if type_name == "shot_accuracy":
            return cast(ps.shots_on_target, Float) / func.nullif(cast(ps.shots, Float), 0)
        elif type_name == "pass_accuracy":
            return cast(ps.passes_succ, Float) / func.nullif(cast(ps.passes, Float), 0)
        elif type_name == "tackle_accuracy":
            return cast(ps.tackles_succ, Float) / func.nullif(cast(ps.tackles, Float), 0)
        elif type_name == "dribble_accuracy":
            return cast(ps.dribbles_succ, Float) / func.nullif(cast(ps.dribbles, Float), 0)
        elif type_name == "cross_accuracy":
            return cast(ps.crosses_succ, Float) / func.nullif(cast(ps.crosses, Float), 0)
        elif type_name == "header_accuracy":
            return cast(ps.headers_succ, Float) / func.nullif(cast(ps.headers, Float), 0)
        elif type_name == "goals_per_game":
            return cast(ps.goals, Float) / func.nullif(cast(ps.matches_played, Float), 0)
        elif type_name == "assists_per_game":
            return cast(ps.assists, Float) / func.nullif(cast(ps.matches_played, Float), 0)
        
        return ps.goals  # fallback

    def _build_world_rate_expr(self, lb_type: LeaderboardType) -> Any:
        """构建世界级率类聚合排序表达式"""
        ps = PlayerSeasonStats
        type_name = lb_type.value
        
        if type_name == "shot_accuracy":
            return (
                cast(func.coalesce(func.sum(ps.shots_on_target), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.shots), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "pass_accuracy":
            return (
                cast(func.coalesce(func.sum(ps.passes_succ), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.passes), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "tackle_accuracy":
            return (
                cast(func.coalesce(func.sum(ps.tackles_succ), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.tackles), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "dribble_accuracy":
            return (
                cast(func.coalesce(func.sum(ps.dribbles_succ), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.dribbles), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "cross_accuracy":
            return (
                cast(func.coalesce(func.sum(ps.crosses_succ), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.crosses), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "header_accuracy":
            return (
                cast(func.coalesce(func.sum(ps.headers_succ), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.headers), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "goals_per_game":
            return (
                cast(func.coalesce(func.sum(ps.goals), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.matches_played), 0), Float), 0)
            ).label("stat_value")
        elif type_name == "assists_per_game":
            return (
                cast(func.coalesce(func.sum(ps.assists), 0), Float)
                / func.nullif(cast(func.coalesce(func.sum(ps.matches_played), 0), Float), 0)
            ).label("stat_value")
        
        return func.coalesce(func.sum(ps.goals), 0).label("stat_value")

    def _get_rate_denominator_field(self, lb_type: LeaderboardType) -> Any:
        """获取率类的分母字段"""
        ps = PlayerSeasonStats
        type_name = lb_type.value
        
        mapping = {
            "shot_accuracy": ps.shots,
            "pass_accuracy": ps.passes,
            "tackle_accuracy": ps.tackles,
            "dribble_accuracy": ps.dribbles,
            "cross_accuracy": ps.crosses,
            "header_accuracy": ps.headers,
            "goals_per_game": ps.matches_played,
            "assists_per_game": ps.matches_played,
        }
        return mapping.get(type_name)

    def _format_value(self, raw_value: Any, value_format: str) -> float:
        """格式化数值"""
        if raw_value is None:
            return 0.0
        
        if isinstance(raw_value, Decimal):
            raw_value = float(raw_value)
        elif not isinstance(raw_value, (int, float)):
            raw_value = float(raw_value)
        
        if value_format == "int":
            return float(int(raw_value))
        elif value_format == "float1":
            return round(raw_value, 1)
        elif value_format == "percent":
            return round(raw_value * 100, 1)
        
        return float(raw_value)
