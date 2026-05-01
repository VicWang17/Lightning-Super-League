"""
Season schemas - 赛季相关Pydantic模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


# ============== 基础模型 ==============

class SeasonBase(BaseModel):
    """赛季基础模型"""
    season_number: int
    status: str
    current_day: int
    current_league_round: int
    current_cup_round: int


class FixtureBase(BaseModel):
    """赛程基础模型"""
    id: str
    fixture_type: str
    season_day: int
    round_number: int
    home_team_id: str
    away_team_id: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str
    cup_stage: Optional[str] = None
    cup_group: Optional[str] = None


# ============== 请求模型 ==============

class SeasonCreateRequest(BaseModel):
    """创建赛季请求"""
    start_date: Optional[datetime] = None
    zone_id: int = 1


# ============== 响应模型 ==============

class SeasonResponse(BaseModel):
    """赛季基本信息响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    season_number: int
    zone_id: int
    status: str
    start_date: datetime
    current_day: int
    current_league_round: int
    current_cup_round: int
    total_days: int
    
    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.id,
            season_number=obj.season_number,
            zone_id=obj.zone_id,
            status=obj.status.value,
            start_date=obj.start_date,
            current_day=obj.current_day,
            current_league_round=obj.current_league_round,
            current_cup_round=obj.current_cup_round,
            total_days=obj.total_days
        )


class SeasonDetailResponse(BaseModel):
    """赛季详情响应"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    season_number: int
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    current_day: int
    current_league_round: int
    current_cup_round: int
    total_days: int
    league_days: int
    cup_start_day: int
    cup_interval: int
    offseason_start: int
    
    # 今日信息
    is_match_day: bool = False
    today_fixture_count: int = 0
    
    @classmethod
    def from_orm(cls, obj):
        # 判断今天是否是比赛日
        is_match_day = obj.current_day > 0 and obj.current_day <= 30
        
        return cls(
            id=obj.id,
            season_number=obj.season_number,
            status=obj.status.value,
            start_date=obj.start_date,
            end_date=obj.end_date,
            current_day=obj.current_day,
            current_league_round=obj.current_league_round,
            current_cup_round=obj.current_cup_round,
            total_days=obj.total_days,
            league_days=obj.league_days,
            cup_start_day=obj.cup_start_day,
            cup_interval=obj.cup_interval,
            offseason_start=obj.offseason_start,
            is_match_day=is_match_day,
            today_fixture_count=0  # 需要查询计算
        )


class SeasonDayResponse(BaseModel):
    """赛季每日处理响应"""
    season_number: int
    current_day: int
    status: str
    fixtures_processed: int
    results: List[Dict[str, Any]]


class SeasonCalendarResponse(BaseModel):
    """赛季日历响应"""
    season_number: int
    team_id: Optional[str] = None
    calendar: List[Dict[str, Any]]


class TeamFixtureResponse(BaseModel):
    """球队赛程响应"""
    season_number: int
    team_id: str
    fixtures: List[Dict[str, Any]]


class TodayFixtureResponse(BaseModel):
    """今日比赛响应"""
    season_number: int
    current_day: int
    fixtures: List[Dict[str, Any]]


# ============== 前端显示专用 ==============

class SeasonStatusForDisplay(BaseModel):
    """前端显示的赛季状态"""
    season_number: int              # 第几赛季
    current_day: int                # 第几天
    total_days: int                 # 总天数
    progress_percent: float         # 进度百分比
    
    # 今日比赛信息
    has_league: bool                # 今天有联赛
    has_cup: bool                   # 今天有杯赛
    league_round: Optional[int]     # 联赛第几轮
    cup_round: Optional[int]        # 杯赛第几轮
    cup_stage: Optional[str]        # 杯赛阶段
    total_fixtures_today: int       # 今天该用户总比赛数
    
    # 显示文本
    display_text: str               # 用于右上角显示的文字
