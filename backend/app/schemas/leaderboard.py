"""
Leaderboard schemas - 通用排行榜 Schema
"""
from enum import Enum
from typing import Optional, Any
from dataclasses import dataclass

from app.schemas.base import BaseSchema


class LeaderboardType(str, Enum):
    """排行榜类型枚举"""
    # 基础计数类
    GOALS = "goals"
    ASSISTS = "assists"
    CLEAN_SHEETS = "clean_sheets"
    SAVES = "saves"
    TACKLES = "tackles"
    INTERCEPTIONS = "interceptions"
    CLEARANCES = "clearances"
    BLOCKS = "blocks"
    SHOTS = "shots"
    SHOTS_ON_TARGET = "shots_on_target"
    KEY_PASSES = "key_passes"
    PASSES = "passes"
    CROSSES = "crosses"
    DRIBBLES = "dribbles"
    YELLOW_CARDS = "yellow_cards"
    RED_CARDS = "red_cards"
    FOULS = "fouls"
    OFFSIDES = "offsides"
    TOUCHES = "touches"
    FREE_KICK_GOALS = "free_kick_goals"
    PENALTY_GOALS = "penalty_goals"
    MINUTES = "minutes_played"
    APPEARANCES = "matches_played"
    RATING = "average_rating"

    # 比率/场均类
    SHOT_ACCURACY = "shot_accuracy"
    PASS_ACCURACY = "pass_accuracy"
    TACKLE_ACCURACY = "tackle_accuracy"
    DRIBBLE_ACCURACY = "dribble_accuracy"
    CROSS_ACCURACY = "cross_accuracy"
    HEADER_ACCURACY = "header_accuracy"
    GOALS_PER_GAME = "goals_per_game"
    ASSISTS_PER_GAME = "assists_per_game"


class LeaderboardItem(BaseSchema):
    """排行榜单项"""
    rank: int
    player_id: str
    player_name: str
    avatar_url: Optional[str] = None
    position: str
    team_name: str
    team_id: str
    value: float
    value_label: str
    matches: int
    # OVR 排名专用字段（兼容旧 TopPlayerItem 接口）
    age: Optional[int] = None
    ovr: Optional[int] = None


@dataclass
class LeaderboardConfig:
    """排行榜配置项"""
    type: LeaderboardType
    label: str
    value_label: str
    value_format: str  # "int" | "float1" | "percent"
    position_filter: Optional[str] = None  # "GK" / None
    min_matches_league: int = 0
    min_matches_world: int = 0
    is_rate: bool = False
    # 以下字段由服务层初始化时填充 SQLAlchemy column/expression
    order_expr: Any = None
    value_expr: Any = None
