"""
League-related schemas
"""
from typing import Optional, List
from pydantic import Field
from datetime import datetime
from enum import Enum
from app.schemas.base import BaseSchema


class SeasonStatus(str, Enum):
    """Season status enumeration"""
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"


class LeagueSystemResponse(BaseSchema):
    """League system response"""
    id: str
    name: str
    code: str
    description: Optional[str] = None
    max_teams_per_league: int = 16


class LeagueResponse(BaseSchema):
    """League response"""
    id: str
    name: str
    level: int
    system_id: str
    system_code: str
    system_name: str
    max_teams: int = 16
    promotion_spots: int
    relegation_spots: int
    has_promotion_playoff: bool
    has_relegation_playoff: bool
    teams_count: int = 0


class SeasonResponse(BaseSchema):
    """Season response"""
    id: str
    season_number: int
    name: str  # 从 season_number 生成，如 "第1赛季"
    start_date: datetime
    end_date: Optional[datetime]
    status: SeasonStatus


class StandingTeamInfo(BaseSchema):
    """Team info in standings"""
    id: str
    name: str
    short_name: Optional[str] = None


class LeagueStandingItem(BaseSchema):
    """League standing item"""
    position: int
    team: StandingTeamInfo
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: Optional[str] = None
    is_promotion_zone: bool = False
    is_relegation_zone: bool = False


class MatchTeamInfo(BaseSchema):
    """Team info in match"""
    id: str
    name: str
    short_name: Optional[str] = None


class MatchResponse(BaseSchema):
    """Match response"""
    id: str
    matchday: int
    home_team: MatchTeamInfo
    away_team: MatchTeamInfo
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    scheduled_at: datetime


class TopScorerItem(BaseSchema):
    """Top scorer item"""
    rank: int
    player_id: str
    player_name: str
    team_name: str
    goals: int
    matches: int


class TopAssistItem(BaseSchema):
    """Top assist item"""
    rank: int
    player_id: str
    player_name: str
    team_name: str
    assists: int
    matches: int


class CleanSheetItem(BaseSchema):
    """Clean sheet item"""
    rank: int
    player_id: str
    player_name: str
    team_name: str
    clean_sheets: int
    matches: int


class PlayoffMatchItem(BaseSchema):
    """Playoff match item"""
    id: str
    name: str  # 对阵名称，如 "东区超级-甲级附加赛"
    round: int  # 轮次：1=预选赛，2=决赛
    home_team: MatchTeamInfo
    away_team: MatchTeamInfo
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    scheduled_at: datetime


class LeagueDetailResponse(LeagueResponse):
    """League detail with standings"""
    current_season: Optional[SeasonResponse] = None
    standings: List[LeagueStandingItem] = []
    recent_matches: List[MatchResponse] = []
    upcoming_matches: List[MatchResponse] = []
    playoffs: List[PlayoffMatchItem] = []  # 附加赛信息
