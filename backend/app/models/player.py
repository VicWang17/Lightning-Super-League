"""
Player model - 球员模型
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, DECIMAL, Date, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlayerPosition(str, PyEnum):
    """Player positions - 球员位置"""
    GK = "GK"    # 门将
    CB = "CB"    # 中后卫
    LB = "LB"    # 左后卫
    RB = "RB"    # 右后卫
    LWB = "LWB"  # 左翼卫
    RWB = "RWB"  # 右翼卫
    CDM = "CDM"  # 防守型中场
    CM = "CM"    # 中场
    CAM = "CAM"  # 进攻型中场
    LM = "LM"    # 左中场
    RM = "RM"    # 右中场
    LW = "LW"    # 左边锋
    RW = "RW"    # 右边锋
    LF = "LF"    # 左前锋
    RF = "RF"    # 右前锋
    ST = "ST"    # 前锋
    CF = "CF"    # 中锋


class PlayerFoot(str, PyEnum):
    """Preferred foot - 惯用脚"""
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"


class PlayerStatus(str, PyEnum):
    """Player status - 球员状态"""
    ACTIVE = "active"         # 正常
    INJURED = "injured"       # 受伤
    SUSPENDED = "suspended"   # 停赛
    RETIRED = "retired"       # 退役


class SquadRole(str, PyEnum):
    """Squad role - 阵容角色"""
    KEY_PLAYER = "key_player"     # 核心球员
    FIRST_TEAM = "first_team"     # 一线队
    ROTATION = "rotation"         # 轮换
    BACKUP = "backup"             # 替补
    HOT_PROSPECT = "hot_prospect" # 希望之星
    YOUNGSTER = "youngster"       # 青训
    NOT_NEEDED = "not_needed"     # 不需要


class Player(Base):
    """Player model - 球员表
    
    说明：
    - 球员属于某个球队
    - AI 球队的球员也是 AI 控制，玩家接管球队后继承这些球员
    - 包含详细的属性、能力值、合同等信息
    """
    __tablename__ = "players"
    
    # 基本信息
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 显示名称
    
    # 个人信息
    nationality: Mapped[str] = mapped_column(String(50), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)   # cm
    weight: Mapped[int | None] = mapped_column(Integer, nullable=True)   # kg
    preferred_foot: Mapped[PlayerFoot] = mapped_column(
        Enum(PlayerFoot),
        default=PlayerFoot.RIGHT,
        nullable=False
    )
    
    # 位置
    primary_position: Mapped[PlayerPosition] = mapped_column(
        Enum(PlayerPosition),
        nullable=False
    )
    secondary_position: Mapped[PlayerPosition | None] = mapped_column(
        Enum(PlayerPosition),
        nullable=True
    )
    
    # 属性值 (1-99)
    # 进攻能力
    shooting: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    finishing: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    long_shots: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 传球能力
    passing: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    vision: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    crossing: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 盘带能力
    dribbling: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    ball_control: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 防守能力
    defending: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    tackling: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    marking: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 身体素质
    pace: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    acceleration: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    strength: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    stamina: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 门将能力
    diving: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    handling: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    kicking: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    reflexes: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    positioning: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 精神属性
    aggression: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    composure: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    work_rate: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 总评和潜力
    overall_rating: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    potential: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    
    # 状态
    status: Mapped[PlayerStatus] = mapped_column(
        Enum(PlayerStatus),
        default=PlayerStatus.ACTIVE,
        nullable=False
    )
    fitness: Mapped[int] = mapped_column(Integer, default=100, nullable=False)   # 体能 0-100
    morale: Mapped[int] = mapped_column(Integer, default=50, nullable=False)     # 士气 1-99
    form: Mapped[int] = mapped_column(Integer, default=50, nullable=False)       # 状态 1-99
    
    # 合同信息
    wage: Mapped[Decimal] = mapped_column(DECIMAL(12, 2), default=Decimal("1000.00"), nullable=False)
    contract_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    release_clause: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2), nullable=True)
    squad_role: Mapped[SquadRole] = mapped_column(
        Enum(SquadRole),
        default=SquadRole.FIRST_TEAM,
        nullable=False
    )
    
    # 市场价值
    market_value: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("100000.00"),
        nullable=False
    )
    
    # 统计数据（当前赛季）
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    goals: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assists: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    red_cards: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_rating: Mapped[Decimal] = mapped_column(DECIMAL(3, 1), default=Decimal("6.0"), nullable=False)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 外键
    team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="players")
    
    @property
    def age(self) -> int:
        """Calculate player age"""
        today = date.today()
        born = self.birth_date
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        return f"<Player(id={self.id}, name={self.full_name}, team_id={self.team_id})>"
