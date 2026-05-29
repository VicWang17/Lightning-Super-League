"""
Wage configuration model - 工资配置表
按设计文档 5.2 / 5.3 节实现，支持运行时调参而不需要改代码。
"""
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, Integer, Enum, DECIMAL, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WageConfigType(str, PyEnum):
    """Wage config type - 工资配置类型"""
    BASE_WAGE = "base_wage"               # OVR 基础工资
    LEAGUE_FACTOR = "league_factor"       # 联赛系数
    AGE_FACTOR = "age_factor"             # 年龄系数
    CONTRACT_TYPE_FACTOR = "contract_type_factor"  # 合同类型系数
    ROLE_FACTOR = "role_factor"           # 阵容角色系数


class WageConfig(Base):
    """Wage configuration model - 工资配置表
    
    说明：
    - 所有工资相关参数集中在此，方便运营调优
    - base_wage 用 sort_order 排序后做线性插值
    - 其他系数直接查表匹配
    """
    __tablename__ = "wage_configs"
    
    config_type: Mapped[WageConfigType] = mapped_column(
        Enum(WageConfigType),
        nullable=False,
        index=True,
    )
    level_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    value: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 4),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )
    
    # 唯一约束：同类型同 level_key 只能有一条
    __table_args__ = (
        UniqueConstraint("config_type", "level_key", name="uix_wage_config_type_level"),
    )
    
    def __repr__(self) -> str:
        return f"<WageConfig(type={self.config_type.value}, level={self.level_key}, value={self.value})>"
