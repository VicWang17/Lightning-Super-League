"""
Injury treatment schemas
"""
from typing import Optional
from pydantic import Field
from decimal import Decimal
from enum import Enum

from app.schemas.base import BaseSchema


class TreatmentPlanEnum(str, Enum):
    """医疗方案"""
    ENHANCED = "enhanced"
    SPECIALIST = "specialist"
    AGGRESSIVE = "aggressive"


class TreatmentOptionSchema(BaseSchema):
    """治疗选项"""
    plan: TreatmentPlanEnum
    plan_label: str = Field(..., description="方案显示名称")
    available: bool = Field(..., description="当前是否可选")
    days_reduced: int = Field(..., description="预计缩短天数")
    days_after: int = Field(..., description="治疗后剩余天数")
    cost: Decimal = Field(..., description="费用")
    residual_wear_penalty: int = Field(0, description="残余劳损惩罚")
    recurrence_risk_bonus: Decimal = Field(Decimal("0"), description="复发风险修正")
    side_effect: str = Field("", description="副作用说明")


class TreatmentApplyRequest(BaseSchema):
    """治疗请求"""
    plan: TreatmentPlanEnum


class TreatmentApplyResponse(BaseSchema):
    """治疗响应"""
    treatment_id: str
    player_id: str
    plan: TreatmentPlanEnum
    cost: Decimal
    reserve_paid: Decimal
    cash_paid: Decimal
    days_before: int
    days_reduced: int
    days_after: int
    reserve_available_after: Decimal


class ReserveStatusSchema(BaseSchema):
    """风险准备金状态"""
    team_id: str
    season_id: str
    reserve_budget: Decimal
    reserve_spent: Decimal
    reserve_available: Decimal
    reserve_usage_pct: float
    reserve_auto_used: Decimal
    reserve_medical_used: Decimal
    reserve_events_used: int
    risk_level: str = Field(..., description="风险等级: 激进/标准/稳健/保守")
