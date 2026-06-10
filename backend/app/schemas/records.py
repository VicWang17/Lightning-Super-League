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
    CUP = "cup"


class RecordCategory(str, Enum):
    TEAM = "team"
    PLAYER = "player"
    MATCH = "match"


class RecordType(str, Enum):
    # --- 球员纪录 ---
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

    # 传球纪录
    CAREER_PASSES = "career_passes"
    CAREER_KEY_PASSES = "career_key_passes"
    SEASON_PASSES = "season_passes"
    SEASON_KEY_PASSES = "season_key_passes"
    MATCH_PASSES = "match_passes"
    MATCH_KEY_PASSES = "match_key_passes"

    # 防守纪录
    CAREER_TACKLES = "career_tackles"
    CAREER_INTERCEPTIONS = "career_interceptions"
    CAREER_CLEARANCES = "career_clearances"
    SEASON_TACKLES = "season_tackles"
    SEASON_INTERCEPTIONS = "season_interceptions"
    SEASON_CLEARANCES = "season_clearances"
    MATCH_TACKLES = "match_tackles"
    MATCH_INTERCEPTIONS = "match_interceptions"

    # 射门/进攻纪录
    CAREER_SHOTS = "career_shots"
    CAREER_SHOTS_ON_TARGET = "career_shots_on_target"
    SEASON_SHOTS = "season_shots"
    SEASON_SHOTS_ON_TARGET = "season_shots_on_target"
    MATCH_SHOTS = "match_shots"
    MATCH_SHOTS_ON_TARGET = "match_shots_on_target"

    # 门将纪录
    CAREER_SAVES = "career_saves"
    CAREER_CLEAN_SHEETS = "career_clean_sheets"
    SEASON_SAVES = "season_saves"
    SEASON_CLEAN_SHEETS = "season_clean_sheets"
    MATCH_SAVES = "match_saves"

    # 纪律纪录
    CAREER_FOULS = "career_fouls"
    CAREER_OFFSIDES = "career_offsides"
    SEASON_FOULS = "season_fouls"
    SEASON_OFFSIDES = "season_offsides"
    MATCH_FOULS = "match_fouls"
    MATCH_OFFSIDES = "match_offsides"

    # --- 球队纪录 ---
    SEASON_TEAM_GOALS = "season_team_goals"
    SEASON_TEAM_GOALS_AGAINST = "season_team_goals_against"
    SEASON_TEAM_POINTS = "season_team_points"
    SEASON_TEAM_WINS = "season_team_wins"
    SEASON_TEAM_CLEAN_SHEETS = "season_team_clean_sheets"
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

    # 进攻
    shots: int = 0
    shots_on_target: int = 0
    shot_accuracy: float = 0.0
    dribbles: int = 0
    dribbles_succ: int = 0
    dribble_accuracy: float = 0.0
    headers: int = 0
    headers_succ: int = 0
    header_accuracy: float = 0.0

    # 传球
    passes: int = 0
    passes_succ: int = 0
    pass_accuracy: float = 0.0
    key_passes: int = 0
    crosses: int = 0
    crosses_succ: int = 0
    cross_accuracy: float = 0.0

    # 防守
    tackles: int = 0
    tackles_succ: int = 0
    tackle_accuracy: float = 0.0
    interceptions: int = 0
    clearances: int = 0
    blocks: int = 0

    # 门将
    saves: int = 0

    # 纪律/其他
    fouls: int = 0
    fouls_drawn: int = 0
    offsides: int = 0
    turnovers: int = 0
    touches: int = 0
    free_kicks: int = 0
    free_kick_goals: int = 0
    penalties: int = 0
    penalty_goals: int = 0

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

    # 进攻
    total_shots: int = 0
    total_shots_on_target: int = 0
    total_dribbles: int = 0
    total_dribbles_succ: int = 0
    total_headers: int = 0
    total_headers_succ: int = 0

    # 传球
    total_passes: int = 0
    total_passes_succ: int = 0
    total_key_passes: int = 0
    total_crosses: int = 0
    total_crosses_succ: int = 0

    # 防守
    total_tackles: int = 0
    total_tackles_succ: int = 0
    total_interceptions: int = 0
    total_clearances: int = 0
    total_blocks: int = 0

    # 门将
    total_saves: int = 0
    total_clean_sheets: int = 0

    # 纪律/其他
    total_fouls: int = 0
    total_fouls_drawn: int = 0
    total_offsides: int = 0
    total_turnovers: int = 0
    total_touches: int = 0
    total_free_kicks: int = 0
    total_free_kick_goals: int = 0
    total_penalties: int = 0
    total_penalty_goals: int = 0


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


class TeamHonorItem(BaseSchema):
    """单条荣誉记录"""
    season_number: int
    honor_type: str = Field(..., description="league_champion 或 cup_champion")
    competition_name: str
    competition_level: Optional[int] = None


class TeamHonorsResponse(BaseSchema):
    """球队荣誉列表响应"""
    honors: List[TeamHonorItem] = Field(default_factory=list)
    total_league_titles: int = 0
    total_cup_titles: int = 0


class WorldRankingItem(BaseSchema):
    """世界排名单项"""
    rank: int
    team_id: str
    team_name: str
    total_score: float
    league_score: float
    cup_score: float
    cup_titles: int


class TopPlayerItem(BaseSchema):
    """球员OVR排行单项"""
    rank: int
    player_id: str
    player_name: str
    avatar_url: Optional[str] = None
    position: str
    age: int
    ovr: int
    team_name: str
    team_id: str


class TeamHistoryResponse(BaseSchema):
    """球队历史页完整响应"""
    seasons: List[TeamSeasonHistoryItem] = Field(default_factory=list)
    record_count: int = 0
    trophies: List[TeamHonorItem] = Field(default_factory=list)


class GrowthCurvePoint(BaseSchema):
    """成长曲线单点数据"""
    age: int
    ovr: int
    is_projected: bool = Field(..., description="是否为预测值")


class AttributeProgressItem(BaseSchema):
    """单属性成长进度"""
    attribute: str
    label: str
    current: int
    cap: float
    progress_pct: float = Field(..., description="当前值占上限的百分比")


class PlayerGrowthResponse(BaseSchema):
    """球员成长曲线页完整响应"""
    current_age: int
    current_ovr: int
    peak_age: int | None
    curve_type: str | None = Field(None, description="early_bloomer/steady/late_bloomer/explosive/plateau")
    curve_type_label: str = ""
    growth_speed: float
    stability: float
    late_bloom_factor: float
    projected_curve: List[GrowthCurvePoint] = Field(default_factory=list)
    attribute_progress: List[AttributeProgressItem] = Field(default_factory=list)
