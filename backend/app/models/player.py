"""
Player model - 球员模型 (PRD v5 简化版)
位置: FW/MF/DF/GK 四种
属性: 23项, 范围 1-20
年龄: birth_offset 相对偏移量
"""
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, JSON, case
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import func

from app.models.base import Base


class PlayerPosition(str, PyEnum):
    """Player positions - 球员大位置"""
    FW = "FW"   # 前锋
    MF = "MF"   # 中场
    DF = "DF"   # 后卫
    GK = "GK"   # 门将


class PlayerFoot(str, PyEnum):
    """Preferred foot - 惯用脚"""
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    BOTH = "BOTH"


class PlayerStatus(str, PyEnum):
    """Player status - 球员状态"""
    ACTIVE = "ACTIVE"
    INJURED = "INJURED"
    SUSPENDED = "SUSPENDED"
    RETIRED = "RETIRED"


class PlayerRace(str, PyEnum):
    """Player race - 种族(决定头像和名字风格)"""
    ASIAN = "asian"
    WESTERN = "western"


class PotentialLetter(str, PyEnum):
    """Potential letter - 潜力字母(前端可见)"""
    S = "S"
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class PlayerPersonality(str, PyEnum):
    """Player personality - 性格(完全隐藏,仅系统使用)"""
    MATERIALISTIC = "materialistic"   # 拜金型
    AMBITIOUS = "ambitious"           # 野心型
    PROFESSIONAL = "professional"     # 职业型
    PASSIONATE = "passionate"         # 激情型
    LOYAL = "loyal"                   # 忠诚型
    TEAM_ORIENTED = "team_oriented"   # 团队型


class ContractType(str, PyEnum):
    """Contract type - 合同类型"""
    NORMAL = "NORMAL"
    ROOKIE = "ROOKIE"
    FREE = "FREE"


class MatchForm(str, PyEnum):
    """Match form - 比赛表现状态(可见)"""
    HOT = "HOT"         # 火热
    GOOD = "GOOD"       # 良好
    NEUTRAL = "NEUTRAL" # 平淡
    LOW = "LOW"         # 低迷


class SquadRole(str, PyEnum):
    """Squad role - 阵容角色"""
    KEY_PLAYER = "key_player"
    FIRST_TEAM = "first_team"
    ROTATION = "rotation"
    BACKUP = "backup"
    HOT_PROSPECT = "hot_prospect"
    YOUNGSTER = "youngster"
    NOT_NEEDED = "not_needed"


class Player(Base):
    """Player model - 球员表
    
    设计说明:
    - 位置简化为 FW/MF/DF/GK 四种
    - 属性 23 项, 范围 1-20
    - 年龄用 birth_offset(负数), 当前年龄 = current_season + |offset|
    - 性格完全隐藏, API 不暴露
    - 招牌技能以 JSON 存储
    """
    __tablename__ = "players"
    
    # ===== 基础档案 =====
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    race: Mapped[PlayerRace] = mapped_column(Enum(PlayerRace), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(200), nullable=True)
    
    position: Mapped[PlayerPosition] = mapped_column(Enum(PlayerPosition), nullable=False, index=True)
    preferred_foot: Mapped[PlayerFoot] = mapped_column(Enum(PlayerFoot), default=PlayerFoot.RIGHT, nullable=False)
    
    height: Mapped[int] = mapped_column(Integer, nullable=False)   # cm, 165-200
    weight: Mapped[int] = mapped_column(Integer, nullable=False)   # kg, 60-95
    
    # ===== 年龄系统 =====
    # birth_offset: 负数, 如 -22 表示第0赛季时22岁, 第1赛季时23岁
    birth_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # ===== 能力属性 (1-20) =====
    # 进攻
    sho: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 射门
    pas: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 传球
    dri: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 盘带
    # 身体
    spd: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 速度
    str_: Mapped[int] = mapped_column("str", Integer, default=10, nullable=False)  # 力量 (str是保留字,用str_映射到str列)
    sta: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 体能
    acc: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 爆发力
    hea: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 头球
    bal: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 平衡
    # 防守
    defe: Mapped[int] = mapped_column(Integer, default=10, nullable=False)  # 防守意识
    tkl: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 抢断
    # 技术/组织
    vis: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 视野
    cro: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 传中
    con: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 控球
    fin: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 远射
    # 门将专属
    com: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 镇定
    sav: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 扑救
    ref: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 反应
    pos: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 站位
    rus: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 出击
    dec: Mapped[int] = mapped_column(Integer, default=10, nullable=False)   # 球商
    fk: Mapped[int] = mapped_column(Integer, default=10, nullable=False)    # 任意球
    pk: Mapped[int] = mapped_column(Integer, default=10, nullable=False)    # 点球
    
    # ===== 综合能力 (计算属性, 不持久化) =====
    # ovr 由属性按位置权重实时计算
    
    # ===== 潜力系统 =====
    potential_max: Mapped[int] = mapped_column(Integer, default=50, nullable=False)      # 隐藏潜力上限(1-100)
    # potential_letter 由 potential_max 计算，不持久化。
    
    # ===== 招牌技能 (JSON) =====
    skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    # ===== 性格 (完全隐藏) =====
    personality: Mapped[PlayerPersonality] = mapped_column(Enum(PlayerPersonality), nullable=False)
    
    # ===== 状态 =====
    status: Mapped[PlayerStatus] = mapped_column(Enum(PlayerStatus), default=PlayerStatus.ACTIVE, nullable=False)
    match_form: Mapped[MatchForm] = mapped_column(Enum(MatchForm), default=MatchForm.NEUTRAL, nullable=False)
    fitness: Mapped[int] = mapped_column(Integer, default=100, nullable=False)   # 体能 0-100
    
    # ===== 合同 =====
    contract_type: Mapped[ContractType] = mapped_column(Enum(ContractType), default=ContractType.NORMAL, nullable=False)
    contract_end_season: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wage: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), default=Decimal("1000.00"), nullable=False)
    release_clause: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    squad_role: Mapped[SquadRole] = mapped_column(Enum(SquadRole), default=SquadRole.FIRST_TEAM, nullable=False)
    
    # market_value / recommended_wage / 生涯统计由服务实时计算，不持久化在 players。
    
    # ===== 外键 =====
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # ===== 关联关系 =====
    team: Mapped["Team"] = relationship("Team", back_populates="players")
    season_stats: Mapped[list["PlayerSeasonStats"]] = relationship("PlayerSeasonStats", back_populates="player")
    
    @property
    def age(self, current_season: int = 0) -> int:
        """计算当前年龄"""
        return current_season + abs(self.birth_offset)
    
    @property
    def potential_letter(self) -> PotentialLetter:
        """根据隐藏潜力上限计算前端展示档位。"""
        if self.potential_max >= 80:
            return PotentialLetter.S
        if self.potential_max >= 60:
            return PotentialLetter.A
        if self.potential_max >= 40:
            return PotentialLetter.B
        if self.potential_max >= 20:
            return PotentialLetter.C
        return PotentialLetter.D
    
    @property
    def market_value(self) -> Decimal:
        """实时估算市场价值，不落库。"""
        return Decimal(self.ovr * 10000 + self.potential_max * 500).quantize(Decimal("0.01"))
    
    @property
    def recommended_wage(self) -> Decimal:
        """实时估算建议工资，不落库。"""
        return Decimal(1000 + self.ovr * 800 + (self.potential_max - 50) * 50).quantize(Decimal("0.01"))
    
    @hybrid_property
    def ovr(self) -> int:
        """实时计算 OVR"""
        weights = _OVR_WEIGHTS.get(self.position, {})
        total = 0.0
        for attr, weight in weights.items():
            if weight > 0:
                val = getattr(self, attr, 10) or 10
                total += (val / 20.0) * weight
        return int(round(total))
    
    @ovr.expression
    def ovr(cls):
        """SQL 表达式版本 OVR"""
        whens = []
        for pos in (PlayerPosition.FW, PlayerPosition.MF, PlayerPosition.DF, PlayerPosition.GK):
            weights = _OVR_WEIGHTS.get(pos, {})
            total_expr = 0
            for attr, weight in weights.items():
                if weight > 0:
                    total_expr += getattr(cls, attr) * weight
            # total_expr / 20.0 得到加权平均值, 再用 ROUND
            expr = func.round(total_expr / 20.0)
            whens.append((cls.position == pos, expr))
        return case(*whens, else_=0)
    
    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name={self.name}, pos={self.position}, ovr={self.ovr})>"

# OVR 权重表 (4位置简化版, 总和100)
_OVR_WEIGHTS = {
    PlayerPosition.FW: {
        "sho": 20, "pas": 3, "dri": 15, "spd": 18, "str_": 10, "sta": 3,
        "hea": 10, "acc": 10, "fin": 5, "bal": 3, "cro": 3, "dec": 4,
        "defe": 0, "vis": 0, "tkl": 0, "con": 0, "com": 0, "sav": 0, "ref": 0, "pos": 0,
        "fk": 0, "pk": 0, "rus": 0,
    },
    PlayerPosition.MF: {
        "pas": 16, "dri": 11, "spd": 7, "str_": 2, "sta": 14, "defe": 9,
        "vis": 13, "tkl": 6, "acc": 2, "cro": 7, "con": 7, "fin": 5, "dec": 10,
        "sho": 2, "hea": 0, "bal": 0, "com": 0, "sav": 0, "ref": 0, "pos": 0,
        "fk": 0, "pk": 0, "rus": 0,
    },
    PlayerPosition.DF: {
        "pas": 5, "spd": 11, "str_": 16, "sta": 11, "defe": 22, "hea": 11,
        "tkl": 7, "cro": 5, "bal": 4, "dec": 8,
        "dri": 0, "vis": 0, "acc": 0, "con": 0, "fin": 0, "sho": 0, "com": 0, "sav": 0, "ref": 0, "pos": 0,
        "fk": 0, "pk": 0, "rus": 0,
    },
    PlayerPosition.GK: {
        "pas": 5, "com": 8, "sav": 25, "ref": 18, "pos": 10, "rus": 8, "dec": 12,
        "sho": 0, "dri": 0, "spd": 0, "str_": 0, "sta": 0, "defe": 0, "hea": 0,
        "vis": 0, "tkl": 0, "acc": 0, "cro": 0, "con": 0, "fin": 0, "bal": 0,
        "fk": 0, "pk": 0,
    },
}
