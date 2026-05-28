"""
Finance-related schemas
"""
from typing import Optional, List
from pydantic import Field
from datetime import datetime
from decimal import Decimal
from enum import Enum

from app.schemas.base import BaseSchema


class BudgetPolicy(str, Enum):
    """预算策略"""
    BALANCED = "balanced"
    YOUTH_FOCUS = "youth_focus"
    TRANSFER_PUSH = "transfer_push"
    WAGE_CONTROL = "wage_control"
    CUSTOM = "custom"


class SponsorPolicy(str, Enum):
    """赞助商策略"""
    STABLE = "stable"
    PERFORMANCE = "performance"


class TransactionSourceType(str, Enum):
    """交易来源类型"""
    BROADCAST = "broadcast"
    SPONSOR = "sponsor"
    MATCH_BONUS = "match_bonus"
    CUP_PRIZE = "cup_prize"
    LEAGUE_PRIZE = "league_prize"
    WAGE = "wage"
    TRANSFER = "transfer"
    YOUTH = "youth"
    PENALTY = "penalty"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class TransactionDirection(str, Enum):
    """交易方向"""
    INCOME = "income"
    EXPENSE = "expense"


class FinancialHealth(str, Enum):
    """财务健康评级"""
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class OverspendLevel(str, Enum):
    """超支等级"""
    NONE = "none"
    WARNING = "warning"
    RESTRICTED = "restricted"
    CRISIS = "crisis"


class FinanceTransactionItem(BaseSchema):
    """财务交易记录项"""
    id: str
    team_id: str
    season_id: str
    source_type: TransactionSourceType
    direction: TransactionDirection
    amount: Decimal = Field(..., description="交易金额")
    balance_after: Decimal = Field(..., description="交易后余额")
    description: str = Field(..., description="交易描述")
    extra_data: Optional[dict] = None
    created_at: datetime


class FinanceTransactionListParams(BaseSchema):
    """财务交易列表查询参数"""
    season_id: Optional[str] = None
    source_type: Optional[TransactionSourceType] = None
    direction: Optional[TransactionDirection] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class IncomeBreakdown(BaseSchema):
    """收入明细"""
    broadcast: Decimal = Decimal("0")
    sponsor: Decimal = Decimal("0")
    match_bonus: Decimal = Decimal("0")
    cup_prize: Decimal = Decimal("0")
    league_prize: Decimal = Decimal("0")
    other: Decimal = Decimal("0")


class ExpenseBreakdown(BaseSchema):
    """支出明细"""
    wage: Decimal = Decimal("0")
    youth: Decimal = Decimal("0")
    transfer: Decimal = Decimal("0")
    penalty: Decimal = Decimal("0")
    other: Decimal = Decimal("0")


class BudgetPlan(BaseSchema):
    """预算分配计划"""
    transfer_pct: int = Field(25, ge=0, le=100, description="转会预算百分比")
    youth_pct: int = Field(15, ge=0, le=100, description="青训预算百分比")
    wage_pct: int = Field(50, ge=0, le=100, description="工资预算百分比")
    reserve_pct: int = Field(10, ge=0, le=100, description="储备预算百分比")


class WageCapInfo(BaseSchema):
    """工资帽信息"""
    wage_cap: Decimal = Field(..., description="工资帽上限")
    wage_bill: Decimal = Field(..., description="当前工资总额")
    wage_pressure_pct: int = Field(..., ge=0, le=200, description="工资压力百分比")
    status: str = Field(..., description="状态: normal, warning, exceeded")


class BudgetPlanSchema(BaseSchema):
    """预算计划"""
    team_id: str
    target_season_id: str
    policy: BudgetPolicy = BudgetPolicy.BALANCED
    transfer_pct: int = Field(25, ge=0, le=100)
    youth_pct: int = Field(15, ge=0, le=100)
    wage_pct: int = Field(50, ge=0, le=100)
    reserve_pct: int = Field(10, ge=0, le=100)
    is_player_confirmed: bool = False
    locked_at: Optional[datetime] = None


class SponsorContractSchema(BaseSchema):
    """赞助合同"""
    team_id: str
    season_id: str
    policy: SponsorPolicy
    base_amount: Decimal = Field(..., description="基础金额")
    win_bonus: Decimal = Field(Decimal("0"), description="胜场奖金")
    draw_bonus: Decimal = Field(Decimal("0"), description="平局奖金")
    max_bonus: Decimal = Field(Decimal("0"), description="奖金上限")
    health_modifier_pct: int = Field(100, description="健康修正百分比")
    status: str = Field("pending", description="状态")


class SponsorOption(BaseSchema):
    """赞助商选项"""
    policy: SponsorPolicy
    label: str = Field(..., description="显示名称")
    base_amount: Decimal = Field(..., description="基础金额")
    win_bonus: Decimal = Field(Decimal("0"), description="胜场奖金")
    draw_bonus: Decimal = Field(Decimal("0"), description="平局奖金")
    max_bonus: Decimal = Field(Decimal("0"), description="奖金上限")
    description: str = Field("", description="说明")


class FinanceOverview(BaseSchema):
    """财务总览"""
    team_id: str
    season_id: str
    
    # 余额
    current_balance: Decimal = Field(..., description="当前余额")
    opening_balance: Decimal = Field(..., description="赛季初余额")
    
    # 预算
    projected_income: Decimal = Field(..., description="预计收入")
    projected_expense: Decimal = Field(..., description="预计支出")
    locked_budget_total: Decimal = Field(..., description="锁定预算总额")
    
    # 分类预算
    transfer_budget: Decimal = Field(..., description="转会预算")
    youth_budget: Decimal = Field(..., description="青训预算")
    wage_budget: Decimal = Field(..., description="工资预算")
    reserve_budget: Decimal = Field(..., description="储备预算")
    
    # 收入/支出统计（赛季累计）
    total_income: Decimal = Field(Decimal("0"), description="赛季总收入")
    total_expense: Decimal = Field(Decimal("0"), description="赛季总支出")
    income_breakdown: IncomeBreakdown = Field(default_factory=IncomeBreakdown)
    expense_breakdown: ExpenseBreakdown = Field(default_factory=ExpenseBreakdown)
    
    # 工资帽
    wage_cap_info: WageCapInfo
    
    # 健康评级
    financial_health: FinancialHealth = FinancialHealth.B
    overspend_level: OverspendLevel = OverspendLevel.NONE
    
    # 预算是否已锁定
    budget_locked: bool = False
    budget_locked_at: Optional[datetime] = None
    
    # Phase 3: 预算与赞助商
    budget_plan: Optional[BudgetPlanSchema] = None
    sponsor_contract: Optional[SponsorContractSchema] = None
