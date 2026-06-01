#!/usr/bin/env python3
"""
初始化工资配置表 (WageConfig)
按设计文档 CONTRACT-PLAYER-STATE-SYSTEM-DESIGN.md 第 5.2 / 5.3 节填充基准数据。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import AsyncSessionLocal
from app.models.wage_config import WageConfig, WageConfigType
from decimal import Decimal


async def init_wage_configs():
    """初始化工资配置数据"""
    db = AsyncSessionLocal()
    
    # 检查是否已初始化
    result = await db.execute(select(WageConfig).limit(1))
    if result.scalar_one_or_none():
        print("WageConfig 已存在，跳过初始化")
        return
    
    configs = []
    
    # === OVR 基础工资表 (设计文档 5.2) ===
    base_wages = [
        (30, Decimal("12000")),
        (40, Decimal("15000")),
        (50, Decimal("22000")),
        (55, Decimal("32000")),
        (60, Decimal("45000")),
        (65, Decimal("65000")),
        (70, Decimal("90000")),
        (75, Decimal("125000")),
        (80, Decimal("170000")),
        (85, Decimal("230000")),
        (90, Decimal("310000")),
        (95, Decimal("420000")),
    ]
    for ovr, wage in base_wages:
        configs.append(WageConfig(
            config_type=WageConfigType.BASE_WAGE,
            level_key=str(ovr),
            value=wage,
            sort_order=ovr,
            description=f"OVR {ovr} 基础赛季工资",
        ))
    
    # === 联赛系数 (设计文档 5.3) ===
    league_factors = [
        ("1", Decimal("1.00")),
        ("2", Decimal("0.95")),
        ("3", Decimal("1.00")),
        ("4", Decimal("0.90")),
    ]
    for level, factor in league_factors:
        configs.append(WageConfig(
            config_type=WageConfigType.LEAGUE_FACTOR,
            level_key=level,
            value=factor,
            sort_order=int(level),
            description=f"联赛级别 {level} 系数",
        ))
    
    # === 年龄系数 (设计文档 5.3) ===
    age_factors = [
        ("<=20", Decimal("0.60")),
        ("21-25", Decimal("1.00")),
        ("26-28", Decimal("1.10")),
        ("29-30", Decimal("0.90")),
        ("31-33", Decimal("0.70")),
        (">=34", Decimal("0.50")),
    ]
    for age_range, factor in age_factors:
        configs.append(WageConfig(
            config_type=WageConfigType.AGE_FACTOR,
            level_key=age_range,
            value=factor,
            sort_order=0,
            description=f"年龄范围 {age_range} 系数",
        ))
    
    # === 合同类型系数 (设计文档 5.3 / 闭环文档 5.2) ===
    # ROOKIE 系数按闭环文档调整为 0.70（青训/选秀签约折扣）
    contract_factors = [
        ("NORMAL", Decimal("1.00")),
        ("ROOKIE", Decimal("0.70")),
        ("FREE", Decimal("0.85")),
    ]
    for ctype, factor in contract_factors:
        configs.append(WageConfig(
            config_type=WageConfigType.CONTRACT_TYPE_FACTOR,
            level_key=ctype,
            value=factor,
            sort_order=0,
            description=f"合同类型 {ctype} 系数",
        ))
    
    # === 阵容角色系数 (设计文档 5.3) ===
    # NOTE: 当前游戏没有阵容角色判断机制，role_factor 暂不实现，
    # 建议工资计算中跳过此系数。
    
    db.add_all(configs)
    await db.commit()
    print(f"已初始化 {len(configs)} 条工资配置数据")
    await db.close()


if __name__ == "__main__":
    asyncio.run(init_wage_configs())
