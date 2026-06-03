"""
Training system models - 训练系统模型
按设计文档 TRAINING-SYSTEM-DESIGN.md 实现。
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, Enum, DECIMAL, JSON, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TrainingSlot(str, PyEnum):
    """训练时段"""
    MORNING = "morning"       # 上午
    AFTERNOON = "afternoon"   # 下午
    EVENING = "evening"       # 晚上


class TrainingMode(str, PyEnum):
    """训练分组模式"""
    TEAM = "team"         # 全队统一
    GROUPS_2 = "groups_2" # 两组训练
    GROUPS_3 = "groups_3" # 三组训练


class TrainingPlanStatus(str, PyEnum):
    """训练计划状态"""
    PLANNED = "planned"     # 已规划
    LOCKED = "locked"       # 已锁定（当前时段不可改）
    COMPLETED = "completed" # 已完成结算
    MISSED = "missed"       # 错过/未执行


class TrainingCreatedBy(str, PyEnum):
    """计划创建来源"""
    PLAYER = "player"   # 玩家手动
    AI = "ai"           # AI 生成
    DEFAULT = "default" # 系统默认


class TeamTrainingPlan(Base):
    """球队训练计划表
    
    说明：
    - 保存未来 7 天 × 3 时段的训练安排
    - 每个球队每天每时段一行
    """
    __tablename__ = "team_training_plans"
    
    # 联合唯一约束：每个球队每天每时段只能有一条计划
    __table_args__ = (
        UniqueConstraint('team_id', 'season_id', 'season_day', 'slot', name='uix_training_plan_slot'),
    )
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 赛季第几天
    slot: Mapped[TrainingSlot] = mapped_column(Enum(TrainingSlot), nullable=False)
    
    mode: Mapped[TrainingMode] = mapped_column(Enum(TrainingMode), default=TrainingMode.TEAM, nullable=False)
    
    # 全队统一训练时使用
    training_item_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # 分组训练配置 [{group_id, name, training_item_id, player_ids}]
    groups: Mapped[list | None] = mapped_column(JSON, nullable=True)
    
    status: Mapped[TrainingPlanStatus] = mapped_column(
        Enum(TrainingPlanStatus),
        default=TrainingPlanStatus.PLANNED,
        nullable=False,
    )
    created_by: Mapped[TrainingCreatedBy] = mapped_column(
        Enum(TrainingCreatedBy),
        default=TrainingCreatedBy.PLAYER,
        nullable=False,
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team")
    season: Mapped["Season"] = relationship("Season")
    
    def __repr__(self) -> str:
        return f"<TeamTrainingPlan(team={self.team_id}, day={self.season_day}, slot={self.slot.value})>"


class TrainingResult(Base):
    """训练结算结果表
    
    说明：
    - 记录每次训练结算的详细数据
    - 用于历史查询、成长追踪、整数突破展示
    """
    __tablename__ = "training_results"
    
    plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("team_training_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    season_day: Mapped[int] = mapped_column(Integer, nullable=False)
    slot: Mapped[TrainingSlot] = mapped_column(Enum(TrainingSlot), nullable=False)
    
    training_item_id: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # 成长数据
    attribute_gains: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # {sho: 0.08, ...}
    before_attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # 训练前快照
    after_attributes: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # 训练后快照
    
    # 体力与疲劳
    fitness_before: Mapped[int] = mapped_column(Integer, nullable=False)
    fitness_after: Mapped[int] = mapped_column(Integer, nullable=False)
    fatigue_before: Mapped[int] = mapped_column(Integer, nullable=False)
    fatigue_after: Mapped[int] = mapped_column(Integer, nullable=False)
    
    load_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # 整数突破记录 [{attribute: "sho", before: 11, after: 12}]
    breakthroughs: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    
    # 本次训练效率（综合倍率）
    efficiency: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=Decimal("1.00"), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<TrainingResult(player={self.player_id}, item={self.training_item_id}, day={self.season_day})>"


class TeamTrainingAIProfile(Base):
    """AI 球队训练偏好表
    
    说明：
    - 为 AI 球队生成训练策略差异
    """
    __tablename__ = "team_training_ai_profiles"
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    
    style: Mapped[str] = mapped_column(String(20), default="balanced", nullable=False)  # attacking/defensive/physical/technical/balanced/youth_focus
    risk_tolerance: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=Decimal("0.50"), nullable=False)  # 0-1
    youth_focus: Mapped[Decimal] = mapped_column(DECIMAL(3, 2), default=Decimal("0.30"), nullable=False)  # 0-1
    random_seed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    def __repr__(self) -> str:
        return f"<TeamTrainingAIProfile(team={self.team_id}, style={self.style})>"
