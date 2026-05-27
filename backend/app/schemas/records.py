"""
Record-related schemas for API request/response validation
"""
from typing import Optional, List
from datetime import date
from pydantic import Field
from enum import Enum

from app.schemas.base import BaseSchema


class RecordScope(str, Enum):
    WORLD = "world"
    LEAGUE = "league"
    TEAM = "team"


class RecordCategory(str, Enum):
    TEAM = "team"
    PLAYER = "player"
    MATCH = "match"


class RecordType(str, Enum):
    CAREER_GOALS = "career_goals"
    CAREER_ASSISTS = "career_assists"
    CAREER_APPEARANCES = "career_appearances"
    CAREER_YELLOW_CARDS = "career_yellow_cards"
    CAREER_RED_CARDS = "career_red_cards"
    CAREER_RATING = "career_rating"
    SEASON_GOALS = "season_goals"
    SEASON_ASSISTS = "season_assists"
    SEASON_RATING = "season_rating"
    MATCH_GOALS = "match_goals"
    MATCH_ASSISTS = "match_assists"
    FASTEST_GOAL = "fastest_goal"
    YOUNGEST_SCORER = "youngest_scorer"
    OLDEST_SCORER = "oldest_scorer"
    HAT_TRICKS = "hat_tricks"
    SCORING_STREAK = "scoring_streak"
    ASSIST_STREAK = "assist_streak"
    SEASON_TEAM_GOALS = "season_team_goals"
    SEASON_TEAM_GOALS_AGAINST = "season_team_goals_against"
    SEASON_TEAM_POINTS = "season_team_points"
    SEASON_TEAM_WINS = "season_team_wins"
    SEASON_CLEAN_SHEETS = "season_clean_sheets"
    BIGGEST_WIN_MARGIN = "biggest_win_margin"
    BIGGEST_DEFEAT_MARGIN = "biggest_defeat_margin"
    MOST_GOALS_IN_MATCH = "most_goals_in_match"
    LONGEST_WIN_STREAK = "longest_win_streak"
    LONGEST_UNBEATEN = "longest_unbeaten"
    LONGEST_LOSING_STREAK = "longest_losing_streak"


class RecordItem(BaseSchema):
    """单条纪录响应"""
    id: str
    scope: RecordScope
    category: RecordCategory
    record_type: RecordType
    record_type_label: str = Field(..., description="中文标签，如 '单赛季进球最多'")
    
    # 保持者信息
    holder_name: str = Field(..., description="球员名或球队名")
    holder_id: str
    holder_avatar_url: Optional[str] = None
    holder_team_name: Optional[str] = None
    holder_team_id: Optional[str] = None
    
    # 纪录数值
    record_value: str = Field(..., description="展示值，如 '34球'")
    record_value_numeric: float
    
    # 创造背景
    season_number: Optional[int] = None
    match_date: Optional[date] = None
    fixture_id: Optional[str] = None
    
    # 额外上下文
    context: dict = Field(default_factory=dict)
    
    created_at: Optional[date] = None
    updated_at: Optional[date] = None


class RecordsByCategory(BaseSchema):
    """按分类分组的纪录列表"""
    team: List[RecordItem] = Field(default_factory=list)
    player: List[RecordItem] = Field(default_factory=list)
    match: List[RecordItem] = Field(default_factory=list)


class PlayerSeasonHistoryItem(BaseSchema):
    """球员单赛季历史数据"""
    season_number: int
    team_name: str
    team_id: str
    matches_played: int = 0
    minutes_played: int = 0
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    clean_sheets: int = 0
    average_rating: float = 0.0
    # 联赛+杯赛细分
    competition_breakdown: List[dict] = Field(default_factory=list)


class PlayerCareerSummary(BaseSchema):
    """球员生涯汇总"""
    total_seasons: int = 0
    total_matches: int = 0
    total_goals: int = 0
    total_assists: int = 0
    total_minutes: int = 0
    total_yellow_cards: int = 0
    total_red_cards: int = 0
    overall_average_rating: float = 0.0
    best_season: Optional[dict] = None


class PlayerMilestone(BaseSchema):
    """球员生涯里程碑"""
    milestone_type: str = Field(..., description="类型: debut, first_goal, 100_goals, transfer, award...")
    season_number: int
    match_date: Optional[date] = None
    description: str
    fixture_id: Optional[str] = None


class PlayerHistoryResponse(BaseSchema):
    """球员历史页完整响应"""
    seasons: List[PlayerSeasonHistoryItem] = Field(default_factory=list)
    summary: PlayerCareerSummary = Field(default_factory=PlayerCareerSummary)
    milestones: List[PlayerMilestone] = Field(default_factory=list)


class TeamSeasonHistoryItem(BaseSchema):
    """球队单赛季历史数据"""
    season_number: int
    league_name: str
    league_level: int
    position: int
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    top_scorer_name: Optional[str] = None
    top_scorer_goals: int = 0


class TeamHistoryResponse(BaseSchema):
    """球队历史页完整响应"""
    seasons: List[TeamSeasonHistoryItem] = Field(default_factory=list)
    record_count: int = 0
    trophies: List[dict] = Field(default_factory=list)
