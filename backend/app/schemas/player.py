"""
Player-related schemas
"""
from typing import Optional, List
from pydantic import Field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from app.schemas.base import BaseSchema


class PlayerPosition(str, Enum):
    """Player positions"""
    GK = "GK"  # 门将
    CB = "CB"  # 中后卫
    LB = "LB"  # 左后卫
    RB = "RB"  # 右后卫
    LWB = "LWB"  # 左翼卫
    RWB = "RWB"  # 右翼卫
    CDM = "CDM"  # 防守型中场
    CM = "CM"  # 中场
    CAM = "CAM"  # 进攻型中场
    LM = "LM"  # 左中场
    RM = "RM"  # 右中场
    LW = "LW"  # 左边锋
    RW = "RW"  # 右边锋
    LF = "LF"  # 左前锋
    RF = "RF"  # 右前锋
    ST = "ST"  # 前锋
    CF = "CF"  # 中锋


class PlayerFoot(str, Enum):
    """Preferred foot"""
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


class PlayerStatus(str, Enum):
    """Player status"""
    ACTIVE = "active"  # 正常
    INJURED = "injured"  # 受伤
    SUSPENDED = "suspended"  # 停赛
    RETIRED = "retired"  # 退役


class PlayerAbility(BaseSchema):
    """Player ability attributes"""
    # 进攻能力
    shooting: int = Field(default=50, ge=1, le=99, description="射门")
    finishing: int = Field(default=50, ge=1, le=99, description="终结")
    long_shots: int = Field(default=50, ge=1, le=99, description="远射")
    
    # 传球能力
    passing: int = Field(default=50, ge=1, le=99, description="传球")
    vision: int = Field(default=50, ge=1, le=99, description="视野")
    crossing: int = Field(default=50, ge=1, le=99, description="传中")
    
    # 盘带能力
    dribbling: int = Field(default=50, ge=1, le=99, description="盘带")
    ball_control: int = Field(default=50, ge=1, le=99, description="控球")
    
    # 防守能力
    defending: int = Field(default=50, ge=1, le=99, description="防守")
    tackling: int = Field(default=50, ge=1, le=99, description="抢断")
    marking: int = Field(default=50, ge=1, le=99, description="盯人")
    
    # 身体素质
    pace: int = Field(default=50, ge=1, le=99, description="速度")
    acceleration: int = Field(default=50, ge=1, le=99, description="加速")
    strength: int = Field(default=50, ge=1, le=99, description="力量")
    stamina: int = Field(default=50, ge=1, le=99, description="体能")
    
    # 门将能力
    diving: int = Field(default=50, ge=1, le=99, description="扑救")
    handling: int = Field(default=50, ge=1, le=99, description="手型")
    kicking: int = Field(default=50, ge=1, le=99, description="开球")
    reflexes: int = Field(default=50, ge=1, le=99, description="反应")
    positioning: int = Field(default=50, ge=1, le=99, description="站位")


class PlayerStats(BaseSchema):
    """Player match statistics"""
    matches_played: int = 0
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    average_rating: float = Field(default=6.0, ge=1, le=10)
    minutes_played: int = 0


class PlayerBase(BaseSchema):
    """Base player schema"""
    first_name: str = Field(..., max_length=50, description="名")
    last_name: str = Field(..., max_length=50, description="姓")
    nationality: str = Field(..., max_length=50, description="国籍")
    birth_date: date = Field(..., description="出生日期")
    height: Optional[int] = Field(None, ge=150, le=220, description="身高(cm)")
    weight: Optional[int] = Field(None, ge=50, le=120, description="体重(kg)")
    preferred_foot: PlayerFoot = PlayerFoot.RIGHT
    primary_position: PlayerPosition = Field(..., description="主要位置")
    secondary_positions: Optional[List[PlayerPosition]] = Field(None, description="次要位置")


class PlayerCreate(PlayerBase):
    """Player creation schema"""
    abilities: PlayerAbility = Field(default_factory=PlayerAbility)
    potential: int = Field(default=50, ge=1, le=99, description="潜力")
    market_value: Decimal = Field(default=Decimal("100000.00"), description="市场价值")


class PlayerUpdate(BaseSchema):
    """Player update schema"""
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    primary_position: Optional[PlayerPosition] = None
    secondary_positions: Optional[List[PlayerPosition]] = None


class PlayerContract(BaseSchema):
    """Player contract information"""
    wage: Decimal = Field(default=Decimal("1000.00"), description="周薪")
    contract_end: Optional[date] = None
    release_clause: Optional[Decimal] = None
    squad_role: str = Field(default="squad", description=" squad/reserve/youth")


class PlayerResponse(PlayerBase):
    """Full player response schema"""
    id: int
    team_id: Optional[int] = None
    age: int = Field(..., description="年龄")
    
    # 能力值
    abilities: PlayerAbility
    overall_rating: int = Field(..., description="总评")
    potential: int = Field(..., description="潜力")
    
    # 状态
    status: PlayerStatus = PlayerStatus.ACTIVE
    fitness: int = Field(default=100, ge=0, le=100, description="体能")
    morale: int = Field(default=50, ge=1, le=99, description="士气")
    form: int = Field(default=50, ge=1, le=99, description="状态")
    
    # 经济和数据
    market_value: Decimal
    contract: Optional[PlayerContract] = None
    stats: Optional[PlayerStats] = None
    
    created_at: datetime
    updated_at: datetime


class PlayerListItem(BaseSchema):
    """Simplified player info for listings"""
    id: int
    name: str = Field(..., description="全名")
    age: int
    nationality: str
    position: PlayerPosition
    overall_rating: int
    market_value: Decimal
    team_id: Optional[int] = None
