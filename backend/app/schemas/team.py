"""
Team-related schemas
"""
from typing import Optional, List
from pydantic import Field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.schemas.base import BaseSchema


class TeamStatus(str, Enum):
    """Team status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class TeamBase(BaseSchema):
    """Base team schema"""
    name: str = Field(..., min_length=2, max_length=50, description="球队名称")
    short_name: Optional[str] = Field(None, max_length=10, description="球队简称")
    logo_url: Optional[str] = Field(None, description="队徽URL")
    stadium: Optional[str] = Field(None, max_length=100, description="主场球场")
    city: Optional[str] = Field(None, max_length=50, description="所在城市")
    founded_year: Optional[int] = Field(None, ge=1800, le=2100, description="成立年份")


class TeamCreate(TeamBase):
    """Team creation schema"""
    league_id: Optional[int] = Field(None, description="所属联赛ID")


class TeamUpdate(BaseSchema):
    """Team update schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    short_name: Optional[str] = Field(None, max_length=10)
    logo_url: Optional[str] = None
    stadium: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=50)


class TeamFinancials(BaseSchema):
    """Team financial information"""
    balance: Decimal = Field(default=Decimal("0.00"), description="当前资金")
    weekly_wages: Decimal = Field(default=Decimal("0.00"), description="周薪支出")
    stadium_capacity: int = Field(default=0, description="球场容量")
    ticket_price: Decimal = Field(default=Decimal("0.00"), description="门票价格")


class TeamStats(BaseSchema):
    """Team statistics"""
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    league_position: Optional[int] = None


class TeamResponse(TeamBase):
    """Full team response schema"""
    id: int
    user_id: int
    league_id: Optional[int] = None
    status: TeamStatus = TeamStatus.ACTIVE
    overall_rating: int = Field(default=50, description="总评")
    created_at: datetime
    updated_at: datetime
    
    # 关联数据
    financials: Optional[TeamFinancials] = None
    stats: Optional[TeamStats] = None


class TeamSummary(BaseSchema):
    """Simplified team info for listings"""
    id: int
    name: str
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    overall_rating: int
    league_position: Optional[int] = None


class DashboardStats(BaseSchema):
    """Dashboard statistics for a team"""
    # 联赛排名相关
    league_position: Optional[int] = None
    points: int = 0
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    goal_difference: int = 0
    
    # 近期状态 (例如: "WWDLW")
    recent_form: str = ""
    
    # 下场比赛
    next_match: Optional[dict] = None
