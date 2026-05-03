"""
Player-related schemas (PRD v5 简化版)
"""
from typing import Optional, List
from pydantic import Field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from app.schemas.base import BaseSchema


class PlayerPosition(str, Enum):
    """Player positions - 4种大位置"""
    FW = "FW"
    MF = "MF"
    DF = "DF"
    GK = "GK"


class PlayerFoot(str, Enum):
    """Preferred foot"""
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BOTH = "BOTH"


class PlayerStatus(str, Enum):
    """Player status"""
    ACTIVE = "ACTIVE"
    INJURED = "INJURED"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class PlayerRace(str, Enum):
    """Player race"""
    ASIAN = "asian"
    WESTERN = "western"


class PotentialLetter(str, Enum):
    """Potential letter"""
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class ContractType(str, Enum):
    """Contract type"""
    NORMAL = "NORMAL"
    ROOKIE = "ROOKIE"
    FREE = "FREE"


class MatchForm(str, Enum):
    """Match form"""
    HOT = "HOT"
    GOOD = "GOOD"
    NEUTRAL = "NEUTRAL"
    LOW = "LOW"


class PlayerSkill(BaseSchema):
    """招牌技能"""
    skill_id: str = Field(..., description="技能ID/名称")
    rarity: str = Field(..., description="稀有度: 普通/稀有/传奇/负面")
    trigger: str = Field(..., description="触发条件")
    effect: str = Field(..., description="效果描述")


class PlayerAbility(BaseSchema):
    """21项能力属性 (1-20)"""
    # 进攻
    sho: int = Field(default=10, ge=1, le=20, description="射门 SHO")
    pas: int = Field(default=10, ge=1, le=20, description="传球 PAS")
    dri: int = Field(default=10, ge=1, le=20, description="盘带 DRI")
    # 身体
    spd: int = Field(default=10, ge=1, le=20, description="速度 SPD")
    str_: int = Field(default=10, ge=1, le=20, description="力量 STR", alias="str", serialization_alias="str")
    sta: int = Field(default=10, ge=1, le=20, description="体能 STA")
    acc: int = Field(default=10, ge=1, le=20, description="爆发力 ACC")
    hea: int = Field(default=10, ge=1, le=20, description="头球 HEA")
    bal: int = Field(default=10, ge=1, le=20, description="平衡 BAL")
    # 防守
    defe: int = Field(default=10, ge=1, le=20, description="防守 DEF")
    tkl: int = Field(default=10, ge=1, le=20, description="抢断 TKL")
    # 技术/组织
    vis: int = Field(default=10, ge=1, le=20, description="视野 VIS")
    cro: int = Field(default=10, ge=1, le=20, description="传中 CRO")
    con: int = Field(default=10, ge=1, le=20, description="控球 CON")
    fin: int = Field(default=10, ge=1, le=20, description="远射 FIN")
    # 门将专属
    com: int = Field(default=10, ge=1, le=20, description="镇定 COM")
    sav: int = Field(default=10, ge=1, le=20, description="扑救 SAV")
    ref: int = Field(default=10, ge=1, le=20, description="反应 REF")
    pos: int = Field(default=10, ge=1, le=20, description="站位 POS")
    rus: int = Field(default=10, ge=1, le=20, description="出击 RUS")
    dec: int = Field(default=10, ge=1, le=20, description="球商 DEC")
    # 定位球
    fk: int = Field(default=10, ge=1, le=20, description="任意球 FK")
    pk: int = Field(default=10, ge=1, le=20, description="点球 PK")

    class Config:
        populate_by_name = True


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
    name: str = Field(..., max_length=50, description="姓名")
    race: PlayerRace = Field(..., description="种族")
    avatar_url: Optional[str] = Field(None, description="头像路径")
    position: PlayerPosition = Field(..., description="位置")
    preferred_foot: PlayerFoot = PlayerFoot.RIGHT
    height: int = Field(..., ge=165, le=200, description="身高(cm)")
    weight: int = Field(..., ge=60, le=95, description="体重(kg)")
    birth_offset: int = Field(..., description="出生偏移量(负数)")


class PlayerCreate(PlayerBase):
    """Player creation schema"""
    abilities: PlayerAbility = Field(default_factory=PlayerAbility)
    ovr: int = Field(default=50, ge=1, le=100, description="总评")
    potential_letter: PotentialLetter = PotentialLetter.C
    skills: List[PlayerSkill] = Field(default_factory=list)
    personality: str = Field(default="professional")
    contract_type: ContractType = ContractType.NORMAL
    contract_end_season: Optional[int] = None
    wage: Decimal = Field(default=Decimal("1000.00"))
    market_value: Decimal = Field(default=Decimal("100000.00"))


class PlayerUpdate(BaseSchema):
    """Player update schema"""
    name: Optional[str] = Field(None, max_length=50)
    position: Optional[PlayerPosition] = None
    status: Optional[PlayerStatus] = None
    squad_role: Optional[str] = None


class PlayerResponse(PlayerBase):
    """Full player response schema"""
    id: str
    team_id: Optional[str] = None
    age: int = Field(..., description="当前年龄(由 birth_offset 计算)")
    
    # 能力值
    abilities: PlayerAbility
    ovr: int = Field(..., description="总评 OVR")
    potential_letter: PotentialLetter = Field(..., description="潜力字母")
    
    # 招牌技能
    skills: List[PlayerSkill] = Field(default_factory=list)
    
    # 状态
    status: PlayerStatus = PlayerStatus.ACTIVE
    match_form: MatchForm = MatchForm.NEUTRAL
    fitness: int = Field(default=100, ge=0, le=100, description="体能")
    
    # 合同
    contract_type: ContractType = ContractType.NORMAL
    contract_end_season: Optional[int] = None
    wage: Decimal
    release_clause: Optional[Decimal] = None
    squad_role: str = Field(default="first_team")
    
    # 经济
    market_value: Decimal
    
    # 统计
    stats: Optional[PlayerStats] = None
    
    created_at: datetime
    updated_at: datetime


class PlayerListItem(BaseSchema):
    """Simplified player info for listings"""
    id: str
    name: str
    race: PlayerRace
    avatar_url: Optional[str]
    age: int
    position: PlayerPosition
    ovr: int
    potential_letter: PotentialLetter
    market_value: Decimal
    team_id: Optional[str] = None
