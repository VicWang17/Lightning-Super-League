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


class PlayerSuspensionInfo(BaseSchema):
    """当前停赛信息"""
    reason: str = Field(..., description="停赛原因: red_card / yellow_card_accumulation")
    matches_remaining: int = Field(..., ge=0, description="剩余停赛场次")
    source_fixture_id: Optional[str] = None
    effective_from_day: int = 0


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
    rarity: str = Field(..., description="品质: 普通/优秀/精英/名人堂")
    quality: Optional[str] = Field(None, description="品质: 普通/优秀/精英/名人堂")
    color: Optional[str] = Field(None, description="品质颜色: white/blue/purple/red")
    type: Optional[str] = Field(None, description="技能类型，例如 negative")
    trigger: str = Field(..., description="触发条件")
    effect: str = Field(..., description="效果描述")


class PlayerAbility(BaseSchema):
    """23项能力属性 (1-20)"""
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
    defe: int = Field(default=10, ge=1, le=20, description="防守意识 DEF")
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

    # 进攻
    shots: int = 0
    shots_on_target: int = 0
    shot_accuracy: float = Field(default=0.0, ge=0, le=100)
    dribbles: int = 0
    dribbles_succ: int = 0
    dribble_accuracy: float = Field(default=0.0, ge=0, le=100)
    headers: int = 0
    headers_succ: int = 0
    header_accuracy: float = Field(default=0.0, ge=0, le=100)

    # 传球
    passes: int = 0
    passes_succ: int = 0
    pass_accuracy: float = Field(default=0.0, ge=0, le=100)
    key_passes: int = 0
    crosses: int = 0
    crosses_succ: int = 0
    cross_accuracy: float = Field(default=0.0, ge=0, le=100)

    # 防守
    tackles: int = 0
    tackles_succ: int = 0
    tackle_accuracy: float = Field(default=0.0, ge=0, le=100)
    interceptions: int = 0
    clearances: int = 0
    blocks: int = 0

    # 门将
    saves: int = 0
    clean_sheets: int = 0

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


class PlayerBase(BaseSchema):
    """Base player schema"""
    name: str = Field(..., max_length=50, description="姓名")
    race: PlayerRace = Field(..., description="种族")
    avatar_url: Optional[str] = Field(None, description="头像路径")
    position: PlayerPosition = Field(..., description="位置")
    preferred_foot: PlayerFoot = PlayerFoot.RIGHT
    preferred_number: int = Field(default=10, ge=1, le=99, description="号码偏好")
    squad_number: Optional[int] = Field(None, ge=1, le=99, description="队内号码")
    height: int = Field(..., ge=165, le=200, description="身高(cm)")
    weight: int = Field(..., ge=60, le=95, description="体重(kg)")
    birth_offset: int = Field(..., description="出生偏移量(负数)")


class PlayerCreate(PlayerBase):
    """Player creation schema"""
    abilities: PlayerAbility = Field(default_factory=PlayerAbility)
    ovr: int = Field(default=50, ge=1, le=100, description="总评")
    potential_max: int = Field(default=50, ge=1, le=100, description="隐藏潜力上限")
    skills: List[PlayerSkill] = Field(default_factory=list)
    personality: str = Field(default="professional")
    contract_type: ContractType = ContractType.NORMAL
    contract_end_season: Optional[int] = None
    wage: Decimal = Field(default=Decimal("1000.00"))


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
    current_suspension: Optional[PlayerSuspensionInfo] = None
    
    # 合同
    contract_type: ContractType = ContractType.NORMAL
    contract_end_season: Optional[int] = None
    wage: Decimal
    release_clause: Optional[Decimal] = None
    squad_role: str = Field(default="first_team")
    
    # 号码
    preferred_number: int = Field(default=10, ge=1, le=99)
    squad_number: Optional[int] = Field(None, ge=1, le=99)
    
    # 经济
    market_value: Decimal
    
    # 统计
    stats: Optional[PlayerStats] = None
    matches_played: int = 0
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    average_rating: float = Field(default=6.0, ge=1, le=10)
    minutes_played: int = 0

    # 进攻统计
    shots: int = 0
    shots_on_target: int = 0
    shot_accuracy: float = Field(default=0.0, ge=0, le=100)
    dribbles: int = 0
    dribbles_succ: int = 0
    dribble_accuracy: float = Field(default=0.0, ge=0, le=100)
    headers: int = 0
    headers_succ: int = 0
    header_accuracy: float = Field(default=0.0, ge=0, le=100)

    # 传球统计
    passes: int = 0
    passes_succ: int = 0
    pass_accuracy: float = Field(default=0.0, ge=0, le=100)
    key_passes: int = 0
    crosses: int = 0
    crosses_succ: int = 0
    cross_accuracy: float = Field(default=0.0, ge=0, le=100)

    # 防守统计
    tackles: int = 0
    tackles_succ: int = 0
    tackle_accuracy: float = Field(default=0.0, ge=0, le=100)
    interceptions: int = 0
    clearances: int = 0
    blocks: int = 0

    # 门将统计
    saves: int = 0
    clean_sheets: int = 0

    # 纪律/其他统计
    fouls: int = 0
    fouls_drawn: int = 0
    offsides: int = 0
    turnovers: int = 0
    touches: int = 0
    free_kicks: int = 0
    free_kick_goals: int = 0
    penalties: int = 0
    penalty_goals: int = 0

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
    squad_number: Optional[int] = None
    team_id: Optional[str] = None
    matches_played: int = 0
    goals: int = 0
    assists: int = 0
    average_rating: float = 0.0
    minutes_played: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    # 进攻
    shots: int = 0
    shots_on_target: int = 0
    dribbles: int = 0
    dribbles_succ: int = 0
    headers: int = 0
    headers_succ: int = 0
    # 传球
    passes: int = 0
    passes_succ: int = 0
    key_passes: int = 0
    crosses: int = 0
    crosses_succ: int = 0
    # 防守
    tackles: int = 0
    tackles_succ: int = 0
    interceptions: int = 0
    clearances: int = 0
    blocks: int = 0
    # 门将
    saves: int = 0
    clean_sheets: int = 0
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

    status: PlayerStatus = PlayerStatus.ACTIVE
    current_suspension: Optional[PlayerSuspensionInfo] = None


# =====================================================================
# Contract & State schemas (v1 新增)
# =====================================================================

class SquadRole(str, Enum):
    """Squad role"""
    KEY_PLAYER = "key_player"
    FIRST_TEAM = "first_team"
    ROTATION = "rotation"
    BACKUP = "backup"
    HOT_PROSPECT = "hot_prospect"
    YOUNGSTER = "youngster"
    NOT_NEEDED = "not_needed"


class PlayerContractResponse(BaseSchema):
    """球员合同详情"""
    player_id: str
    team_id: Optional[str]
    contract_type: ContractType
    start_season_number: int
    end_season_number: Optional[int]
    wage: Decimal
    recommended_wage: Decimal
    wage_ratio: Decimal
    release_clause: Optional[Decimal]
    squad_role: SquadRole
    status: str
    created_at: datetime


class ContractPreviewRequest(BaseSchema):
    """合同预览请求"""
    team_id: str
    contract_type: ContractType
    years: int = Field(..., ge=1, le=4)
    wage: Decimal
    squad_role: SquadRole


class ContractPreviewResponse(BaseSchema):
    """合同预览响应"""
    recommended_wage: Decimal
    offered_wage: Decimal
    wage_ratio: Decimal
    visible_reaction: str
    hidden_wage_satisfaction: int
    wage_cap_after_pct: int
    can_submit: bool
    warnings: List[str]


class ContractSignRequest(BaseSchema):
    """签约请求"""
    team_id: str
    contract_type: ContractType
    years: int = Field(..., ge=1, le=4)
    wage: Decimal
    squad_role: SquadRole
    release_clause: Optional[Decimal] = None


class PlayerStateResponse(BaseSchema):
    """球员状态响应（玩家可见）"""
    player_id: str
    visible_form: MatchForm
    fitness: int = Field(..., ge=0, le=100)
    availability: PlayerStatus
    trend: str = Field(default="stable", description="趋势: up/down/stable")
    hints: List[str] = Field(default_factory=list)
    # 管理/调试字段（开发环境可用）
    state_score: Optional[int] = Field(None, description="综合状态分")
    contract_score: Optional[int] = None
    recent_match_score: Optional[int] = None
    fitness_score: Optional[int] = None
    match_load_score: Optional[int] = None
    match_rust_score: Optional[int] = None


class TeamPlayerStatesResponse(BaseSchema):
    """全队球员状态列表"""
    team_id: str
    players: List[PlayerStateResponse]
