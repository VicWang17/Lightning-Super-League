"""
Finance models - 经济系统相关模型
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum, DECIMAL, JSON, Text, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TransactionSourceType(str, PyEnum):
    """交易来源类型"""
    BROADCAST = "broadcast"           # 转播收入
    SPONSOR = "sponsor"               # 赞助商收入
    MATCH_BONUS = "match_bonus"       # 比赛奖金
    CUP_PRIZE = "cup_prize"           # 杯赛奖金
    LEAGUE_PRIZE = "league_prize"     # 联赛奖金
    WAGE = "wage"                     # 工资支出
    TRANSFER = "transfer"             # 转会收支
    YOUTH = "youth"                   # 青训支出
    PENALTY = "penalty"               # 罚金
    MANUAL_ADJUSTMENT = "manual_adjustment"  # 手动调整
    MEDICAL = "medical"               # 主动医疗加速
    RESERVE_AUTO_COVER = "reserve_auto_cover"  # 自动缓冲事件
    RESERVE_SETTLEMENT = "reserve_settlement"  # 赛季末准备金结转


class TransactionDirection(str, PyEnum):
    """交易方向"""
    INCOME = "income"     # 收入
    EXPENSE = "expense"   # 支出


class FinancialHealth(str, PyEnum):
    """财务健康评级"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class OverspendLevel(str, PyEnum):
    """超支等级"""
    NONE = "none"
    WARNING = "warning"
    RESTRICTED = "restricted"
    CRISIS = "crisis"


class BudgetPolicy(str, PyEnum):
    """预算策略"""
    BALANCED = "balanced"           # 均衡
    YOUTH_FOCUS = "youth_focus"     # 青训侧重
    TRANSFER_PUSH = "transfer_push" # 转会侧重
    WAGE_CONTROL = "wage_control"   # 工资控制
    CUSTOM = "custom"               # 自定义


class SponsorPolicy(str, PyEnum):
    """赞助商策略"""
    STABLE = "stable"         # 稳定型
    PERFORMANCE = "performance"  # 绩效型


class SponsorContractStatus(str, PyEnum):
    """赞助合同状态"""
    PENDING = "pending"     # 待签署
    ACTIVE = "active"       # 生效中
    COMPLETED = "completed" # 已完成


class FinanceTransaction(Base):
    """FinanceTransaction model - 财务交易账本
    
    说明：
    - 所有改变球队余额的操作都必须在此留下记录
    - 不可修改，纠错使用补偿交易
    - 通过 (team_id, season_id, source_type, extra_data.idempotency_key) 保证幂等
    """
    __tablename__ = "finance_transactions"
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    event_queue_id: Mapped[str | None] = mapped_column(
        ForeignKey("event_queues.id", ondelete="SET NULL"),
        nullable=True
    )
    
    source_type: Mapped[TransactionSourceType] = mapped_column(
        Enum(TransactionSourceType),
        nullable=False
    )
    direction: Mapped[TransactionDirection] = mapped_column(
        Enum(TransactionDirection),
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False
    )
    balance_after: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False
    )
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=""
    )
    extra_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="finance_transactions")
    season: Mapped["Season"] = relationship("Season", back_populates="finance_transactions")
    
    def __repr__(self) -> str:
        return f"<FinanceTransaction(id={self.id}, team={self.team_id}, {self.direction.value}={self.amount})>"


class TeamSeasonFinance(Base):
    """TeamSeasonFinance model - 球队赛季财务快照
    
    说明：
    - 每个球队每个赛季只有一条记录
    - 记录赛季初预算、当前余额、健康评级等
    """
    __tablename__ = "team_season_finances"
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # 余额相关
    opening_balance: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    current_balance: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 预算规划
    projected_income: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    projected_expense: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    locked_budget_total: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 分类预算
    transfer_budget: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    youth_budget: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    wage_budget: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    reserve_budget: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 工资与约束
    wage_cap: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    wage_bill: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    
    # 评级
    financial_health: Mapped[FinancialHealth] = mapped_column(
        Enum(FinancialHealth),
        default=FinancialHealth.B,
        nullable=False
    )
    overspend_level: Mapped[OverspendLevel] = mapped_column(
        Enum(OverspendLevel),
        default=OverspendLevel.NONE,
        nullable=False
    )
    
    # 风险准备金使用追踪 (EMERGENCY-FUND-INJURY-FINANCE-DESIGN.md)
    reserve_spent: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    reserve_auto_used: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    reserve_medical_used: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    reserve_events_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )
    
    budget_locked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # 唯一约束：每个球队每个赛季只有一条记录
    __table_args__ = (
        UniqueConstraint("team_id", "season_id", name="uix_team_season_finance"),
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="season_finances")
    season: Mapped["Season"] = relationship("Season", back_populates="team_finances")
    
    def __repr__(self) -> str:
        return f"<TeamSeasonFinance(team={self.team_id}, season={self.season_id}, balance={self.current_balance})>"


class TeamBudgetPlan(Base):
    """TeamBudgetPlan model - 球队预算计划（下赛季决策）
    
    说明：
    - 在预算窗口期间创建，锁定后不再修改
    - 每个球队每个目标赛季只有一条记录
    """
    __tablename__ = "team_budget_plans"
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False
    )
    target_season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False
    )
    
    policy: Mapped[BudgetPolicy] = mapped_column(
        Enum(BudgetPolicy),
        default=BudgetPolicy.BALANCED,
        nullable=False
    )
    
    transfer_pct: Mapped[int] = mapped_column(
        Integer,
        default=25,
        nullable=False
    )
    youth_pct: Mapped[int] = mapped_column(
        Integer,
        default=15,
        nullable=False
    )
    wage_pct: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False
    )
    reserve_pct: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False
    )
    
    is_player_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # 唯一约束
    __table_args__ = (
        UniqueConstraint("team_id", "target_season_id", name="uix_team_budget_plan"),
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="budget_plans")
    target_season: Mapped["Season"] = relationship("Season", back_populates="budget_plans")
    
    def __repr__(self) -> str:
        return f"<TeamBudgetPlan(team={self.team_id}, policy={self.policy.value}, locked={self.locked_at is not None})>"


class SponsorContract(Base):
    """SponsorContract model - 赞助合同
    
    说明：
    - Phase 3 引入赞助商选择
    - stable: 固定基础收入，无比赛奖金
    - performance: 较低基础收入 + 比赛绩效奖金
    """
    __tablename__ = "sponsor_contracts"
    
    team_id: Mapped[str] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    season_id: Mapped[str] = mapped_column(
        ForeignKey("seasons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    policy: Mapped[SponsorPolicy] = mapped_column(
        Enum(SponsorPolicy),
        nullable=False
    )
    
    base_amount: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        nullable=False
    )
    win_bonus: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    draw_bonus: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    goal_bonus: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    max_bonus: Mapped[Decimal] = mapped_column(
        DECIMAL(15, 2),
        default=Decimal("0.00"),
        nullable=False
    )
    health_modifier_pct: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False
    )
    
    status: Mapped[SponsorContractStatus] = mapped_column(
        Enum(SponsorContractStatus),
        default=SponsorContractStatus.PENDING,
        nullable=False
    )
    
    # 关联关系
    team: Mapped["Team"] = relationship("Team", back_populates="sponsor_contracts")
    season: Mapped["Season"] = relationship("Season", back_populates="sponsor_contracts")
    
    def __repr__(self) -> str:
        return f"<SponsorContract(team={self.team_id}, policy={self.policy.value}, base={self.base_amount})>"
