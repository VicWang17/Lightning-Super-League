"""
Award schemas - 球员荣誉/奖项相关 schema
"""
from typing import Optional, List, Dict, Any
from pydantic import Field
from datetime import datetime
from enum import Enum
from app.schemas.base import BaseSchema


class AwardType(str, Enum):
    """奖项类型"""
    MATCH_MVP = "match_mvp"
    LEAGUE_TEAM_OF_SEASON = "league_team_of_season"
    LEAGUE_BEST_FW = "league_best_fw"
    LEAGUE_BEST_MF = "league_best_mf"
    LEAGUE_BEST_DF = "league_best_df"
    LEAGUE_BEST_GK = "league_best_gk"
    LEAGUE_GOLDEN_BOOT = "league_golden_boot"
    LEAGUE_PLAYMAKER = "league_playmaker"
    LEAGUE_GOLDEN_GLOVE = "league_golden_glove"
    LEAGUE_GOLDEN_WALL = "league_golden_wall"
    CUP_GOLDEN_BOOT = "cup_golden_boot"
    CUP_PLAYMAKER = "cup_playmaker"
    CUP_GOLDEN_GLOVE = "cup_golden_glove"
    CUP_GOLDEN_WALL = "cup_golden_wall"
    SEASON_BEST_PLAYER = "season_best_player"
    SEASON_BEST_FW = "season_best_fw"
    SEASON_BEST_MF = "season_best_mf"
    SEASON_BEST_DF = "season_best_df"
    SEASON_BEST_GK = "season_best_gk"
    SEASON_GOLDEN_BOOT = "season_golden_boot"
    SEASON_PLAYMAKER = "season_playmaker"
    SEASON_GOLDEN_GLOVE = "season_golden_glove"
    SEASON_GOLDEN_WALL = "season_golden_wall"


class AwardLevel(str, Enum):
    """奖项级别"""
    MATCH = "match"
    LEAGUE = "league"
    CUP = "cup"
    SEASON = "season"


class AwardMetadata(BaseSchema):
    """奖项评选依据"""
    rating: Optional[float] = None
    matches: Optional[int] = None
    goals: Optional[int] = None
    assists: Optional[int] = None
    clean_sheets: Optional[int] = None
    tackles: Optional[int] = None
    interceptions: Optional[int] = None
    saves: Optional[int] = None
    championships: Optional[int] = None
    mvp_count: Optional[int] = None
    primary_value: Optional[int] = None
    position_rank: Optional[int] = None
    team: Optional[str] = None
    opponent: Optional[str] = None
    match_result: Optional[str] = None
    cup_name: Optional[str] = None


class PlayerAwardBase(BaseSchema):
    """球员荣誉基础 schema"""
    player_id: str
    season_id: str
    season_number: int
    award_type: AwardType
    award_level: AwardLevel
    league_id: Optional[str] = None
    cup_id: Optional[str] = None
    fixture_id: Optional[str] = None
    position: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    description: Optional[str] = None


class PlayerAwardResponse(PlayerAwardBase):
    """球员荣誉响应 schema（含关联信息）"""
    id: str
    player_name: Optional[str] = None
    player_avatar_url: Optional[str] = None
    player_position: Optional[str] = None
    league_name: Optional[str] = None
    cup_name: Optional[str] = None
    created_at: datetime


class PlayerAwardSummary(BaseSchema):
    """球员荣誉统计摘要"""
    total_awards: int = 0
    mvp_count: int = 0
    team_of_season_count: int = 0
    best_position_count: int = 0
    golden_boot_count: int = 0
    playmaker_count: int = 0
    golden_glove_count: int = 0
    golden_wall_count: int = 0
    season_best_player_count: int = 0


class AwardsByCategory(BaseSchema):
    """按类别分组的奖项"""
    match_mvp: List[PlayerAwardResponse] = []
    league_team_of_season: List[PlayerAwardResponse] = []
    league_best_fw: List[PlayerAwardResponse] = []
    league_best_mf: List[PlayerAwardResponse] = []
    league_best_df: List[PlayerAwardResponse] = []
    league_best_gk: List[PlayerAwardResponse] = []
    league_golden_boot: List[PlayerAwardResponse] = []
    league_playmaker: List[PlayerAwardResponse] = []
    league_golden_glove: List[PlayerAwardResponse] = []
    league_golden_wall: List[PlayerAwardResponse] = []
    cup_golden_boot: List[PlayerAwardResponse] = []
    cup_playmaker: List[PlayerAwardResponse] = []
    cup_golden_glove: List[PlayerAwardResponse] = []
    cup_golden_wall: List[PlayerAwardResponse] = []
    season_best_player: List[PlayerAwardResponse] = []
    season_best_fw: List[PlayerAwardResponse] = []
    season_best_mf: List[PlayerAwardResponse] = []
    season_best_df: List[PlayerAwardResponse] = []
    season_best_gk: List[PlayerAwardResponse] = []
    season_golden_boot: List[PlayerAwardResponse] = []
    season_playmaker: List[PlayerAwardResponse] = []
    season_golden_glove: List[PlayerAwardResponse] = []
    season_golden_wall: List[PlayerAwardResponse] = []


class SeasonAwardsResponse(BaseSchema):
    """赛季奖项响应"""
    season_id: str
    season_number: int
    best_player: Optional[PlayerAwardResponse] = None
    best_fw: Optional[PlayerAwardResponse] = None
    best_mf: Optional[PlayerAwardResponse] = None
    best_df: Optional[PlayerAwardResponse] = None
    best_gk: Optional[PlayerAwardResponse] = None
    golden_boot: Optional[PlayerAwardResponse] = None
    playmaker: Optional[PlayerAwardResponse] = None
    golden_glove: Optional[PlayerAwardResponse] = None
    golden_wall: Optional[PlayerAwardResponse] = None


class LeagueAwardsResponse(BaseSchema):
    """联赛奖项响应"""
    league_id: str
    season_id: str
    season_number: int
    team_of_season: List[PlayerAwardResponse] = []
    best_fw: Optional[PlayerAwardResponse] = None
    best_mf: Optional[PlayerAwardResponse] = None
    best_df: Optional[PlayerAwardResponse] = None
    best_gk: Optional[PlayerAwardResponse] = None
    golden_boot: Optional[PlayerAwardResponse] = None
    playmaker: Optional[PlayerAwardResponse] = None
    golden_glove: Optional[PlayerAwardResponse] = None
    golden_wall: Optional[PlayerAwardResponse] = None


class CupAwardsResponse(BaseSchema):
    """杯赛奖项响应"""
    cup_id: str
    season_id: str
    season_number: int
    golden_boot: Optional[PlayerAwardResponse] = None
    playmaker: Optional[PlayerAwardResponse] = None
    golden_glove: Optional[PlayerAwardResponse] = None
    golden_wall: Optional[PlayerAwardResponse] = None
