"""
Economy configuration - 经济系统参数配置中心

所有经济数值集中在此，方便调优而无需修改业务逻辑。
"""
from dataclasses import dataclass, field
from typing import Dict, Tuple
from decimal import Decimal


@dataclass(frozen=True)
class BroadcastConfig:
    """转播收入配置"""
    # 联赛级别 -> 基础转播费
    base_by_level: Dict[int, Decimal] = field(default_factory=lambda: {
        1: Decimal("650000"),
        2: Decimal("520000"),
        3: Decimal("420000"),
        4: Decimal("340000"),
    })
    # 声望倍数范围
    reputation_min: Decimal = Decimal("0.8")
    reputation_max: Decimal = Decimal("1.2")
    reputation_default: Decimal = Decimal("1.0")


@dataclass(frozen=True)
class SponsorConfig:
    """赞助商配置"""
    # 联赛级别 -> 基础赞助费
    base_by_level: Dict[int, Decimal] = field(default_factory=lambda: {
        1: Decimal("1550000"),
        2: Decimal("1300000"),
        3: Decimal("1100000"),
        4: Decimal("950000"),
    })
    # 健康评级对赞助的修正
    health_modifier: Dict[str, Decimal] = field(default_factory=lambda: {
        "A": Decimal("1.05"),
        "B": Decimal("1.00"),
        "C": Decimal("0.90"),
        "D": Decimal("0.70"),
    })


@dataclass(frozen=True)
class WageConfig:
    """工资配置"""
    # 一个赛季发几次工资
    payments_per_season: int = 6
    # 默认赛季工资（球员 wage 字段为赛季工资）
    # 每次支付 = season_wage / payments_per_season


@dataclass(frozen=True)
class SeasonTicketConfig:
    """赛季套票收入配置"""
    # 联赛级别 -> 赛季初稳定门票收入
    base_by_level: Dict[int, Decimal] = field(default_factory=lambda: {
        1: Decimal("1100000"),
        2: Decimal("850000"),
        3: Decimal("680000"),
        4: Decimal("540000"),
    })
    # 声望倍数范围，和转播收入保持同样温和的强弱差异
    reputation_min: Decimal = Decimal("0.85")
    reputation_max: Decimal = Decimal("1.15")
    reputation_default: Decimal = Decimal("1.0")


@dataclass(frozen=True)
class WageCapConfig:
    """工资帽配置"""
    # 联赛级别 -> 基础赛季工资帽。工资帽是联盟公平规则，不随现金储备线性膨胀。
    base_by_level: Dict[int, Decimal] = field(default_factory=lambda: {
        1: Decimal("4200000"),
        2: Decimal("3100000"),
        3: Decimal("2250000"),
        4: Decimal("1600000"),
    })
    # 财务健康只做小幅修正，避免健康状态本身制造强队滚雪球。
    modifier_by_health: Dict[str, Decimal] = field(default_factory=lambda: {
        "A": Decimal("1.05"),
        "B": Decimal("1.00"),
        "C": Decimal("0.95"),
        "D": Decimal("0.90"),
    })


@dataclass(frozen=True)
class LeaguePrizeConfig:
    """联赛排名奖金配置"""
    # 联赛级别 -> 排名 -> 奖金
    # 只给前几名和保级相关名次发放，中间名次为0
    prize_by_level: Dict[int, Tuple[Decimal, ...]] = field(default_factory=lambda: {
        1: (
            Decimal("500000"),   # 1st
            Decimal("350000"),   # 2nd
            Decimal("250000"),   # 3rd
            Decimal("180000"),   # 4th
            Decimal("120000"),   # 5th
            Decimal("80000"),    # 6th
            Decimal("50000"),    # 7th
            Decimal("30000"),    # 8th
        ),
        2: (
            Decimal("350000"),
            Decimal("250000"),
            Decimal("180000"),
            Decimal("120000"),
            Decimal("80000"),
            Decimal("50000"),
            Decimal("30000"),
            Decimal("20000"),
        ),
        3: (
            Decimal("250000"),
            Decimal("180000"),
            Decimal("120000"),
            Decimal("80000"),
            Decimal("50000"),
            Decimal("30000"),
            Decimal("20000"),
            Decimal("10000"),
        ),
        4: (
            Decimal("180000"),
            Decimal("120000"),
            Decimal("80000"),
            Decimal("50000"),
            Decimal("30000"),
            Decimal("20000"),
            Decimal("10000"),
            Decimal("5000"),
        ),
    })


@dataclass(frozen=True)
class BudgetConfig:
    """预算分配默认配置"""
    # 默认预算百分比
    default_transfer_pct: int = 25
    default_youth_pct: int = 10
    default_wage_pct: int = 55
    default_reserve_pct: int = 10
    # 极值限制
    youth_min_pct: int = 5
    youth_max_pct: int = 25
    wage_min_pct: int = 45
    wage_max_pct: int = 65
    reserve_min_pct: int = 5
    reserve_max_pct: int = 20


@dataclass(frozen=True)
class MedicalCostConfig:
    """医疗成本配置 (EMERGENCY-FUND-INJURY-FINANCE-DESIGN.md)"""
    market_value_pct: Decimal = Decimal("0.006")
    weekly_wage_multiplier: Decimal = Decimal("1.5")
    days_exponent: float = 1.15
    minimum_remaining_pct: Decimal = Decimal("0.35")
    
    # 部位倍率
    body_part_multiplier: Dict[str, Decimal] = field(default_factory=lambda: {
        "hamstring": Decimal("1.00"),
        "quadriceps": Decimal("1.00"),
        "calf": Decimal("1.00"),
        "groin": Decimal("1.00"),
        "ankle": Decimal("1.25"),
        "knee": Decimal("1.25"),
        "achilles": Decimal("1.25"),
        "foot": Decimal("1.00"),
        "back": Decimal("1.10"),
        "ribs": Decimal("1.10"),
        "shoulder": Decimal("1.10"),
        "fingers": Decimal("0.90"),
        "head": Decimal("1.30"),
    })
    
    # 门将额外倍率修正（对特定部位）
    gk_body_part_bonus: Decimal = Decimal("0.30")
    gk_sensitive_parts: Tuple[str, ...] = field(default_factory=lambda: ("fingers", "shoulder", "head"))
    
    # 联赛底价（按级别）
    league_floor: Dict[int, Decimal] = field(default_factory=lambda: {
        1: Decimal("50000"),
        2: Decimal("35000"),
        3: Decimal("25000"),
        4: Decimal("15000"),
    })
    
    # severity 倍率
    severity_multiplier: Dict[int, Decimal] = field(default_factory=lambda: {
        2: Decimal("1.0"),
        3: Decimal("1.6"),
    })


@dataclass(frozen=True)
class TreatmentPlanConfig:
    """医疗方案配置"""
    enhanced: Dict[str, object] = field(default_factory=lambda: {
        "reduction_pct": Decimal("0.25"),
        "max_days": 2,
        "cost_multiplier": Decimal("1.0"),
        "residual_wear_penalty": 0,
        "recurrence_risk_bonus": Decimal("0.00"),
    })
    specialist: Dict[str, object] = field(default_factory=lambda: {
        "reduction_pct": Decimal("0.40"),
        "max_days": 4,
        "cost_multiplier": Decimal("1.8"),
        "residual_wear_penalty": 5,
        "recurrence_risk_bonus": Decimal("0.15"),
    })
    aggressive: Dict[str, object] = field(default_factory=lambda: {
        "reduction_pct": Decimal("0.55"),
        "max_days": 6,
        "cost_multiplier": Decimal("3.0"),
        "residual_wear_penalty": 12,
        "recurrence_risk_bonus": Decimal("0.35"),
    })


@dataclass(frozen=True)
class ReserveCarryoverConfig:
    """准备金赛季末结转配置"""
    rate_by_health: Dict[str, Decimal] = field(default_factory=lambda: {
        "A": Decimal("0.70"),
        "B": Decimal("0.60"),
        "C": Decimal("0.50"),
        "D": Decimal("0.40"),
    })


@dataclass(frozen=True)
class EconomyConfig:
    """经济系统完整配置"""
    broadcast: BroadcastConfig = field(default_factory=BroadcastConfig)
    sponsor: SponsorConfig = field(default_factory=SponsorConfig)
    season_ticket: SeasonTicketConfig = field(default_factory=SeasonTicketConfig)
    wage: WageConfig = field(default_factory=WageConfig)
    wage_cap: WageCapConfig = field(default_factory=WageCapConfig)
    league_prize: LeaguePrizeConfig = field(default_factory=LeaguePrizeConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    medical_cost: MedicalCostConfig = field(default_factory=MedicalCostConfig)
    treatment_plan: TreatmentPlanConfig = field(default_factory=TreatmentPlanConfig)
    reserve_carryover: ReserveCarryoverConfig = field(default_factory=ReserveCarryoverConfig)


# 全局默认经济配置（可调优）
DEFAULT_ECONOMY = EconomyConfig()


def get_economy_config() -> EconomyConfig:
    """获取经济配置"""
    return DEFAULT_ECONOMY
