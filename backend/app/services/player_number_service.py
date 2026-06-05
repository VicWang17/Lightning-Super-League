"""
Player Number Service - 球员号码系统

职责:
- 按位置生成号码偏好
- 球员入队时分配实际队内号码
"""
import random
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.player import Player, PlayerPosition


# 位置 -> 偏好号码概率分布
_NUMBER_PREFERENCE = {
    PlayerPosition.FW: [
        (9, 0.25),
        (10, 0.25),
        (11, 0.20),
        (7, 0.10),
        (14, 0.05),
        (17, 0.05),
        (19, 0.05),
        (20, 0.05),
    ],
    PlayerPosition.MF: [
        (6, 0.15),
        (7, 0.15),
        (8, 0.15),
        (10, 0.20),
        (4, 0.10),
        (14, 0.10),
        (16, 0.08),
        (18, 0.07),
    ],
    PlayerPosition.DF: [
        (2, 0.15),
        (3, 0.15),
        (4, 0.15),
        (5, 0.15),
        (6, 0.15),
        (13, 0.10),
        (15, 0.08),
        (22, 0.07),
    ],
    PlayerPosition.GK: [
        (1, 0.80),
        (12, 0.08),
        (13, 0.07),
        (22, 0.03),
        (25, 0.02),
    ],
}

# 备选号码池 (12-35，用于偏好冲突时)
_FALLBACK_NUMBERS = list(range(12, 36))


def generate_preferred_number(position: PlayerPosition) -> int:
    """按位置生成号码偏好
    
    分布模拟真实足球号码选择习惯:
    - FW: 偏好 9-11, 也有 7, 14, 17, 19, 20 等
    - MF: 偏好 6-8, 10, 也有 4, 14, 16, 18 等
    - DF: 偏好 2-6, 也有 13, 15, 22 等
    - GK: 80% 选 1, 也有 12, 13, 22, 25 等
    """
    choices = _NUMBER_PREFERENCE.get(position, [(10, 1.0)])
    numbers = [n for n, _ in choices]
    weights = [w for _, w in choices]
    return random.choices(numbers, weights=weights, k=1)[0]


async def get_team_squad_numbers(db: AsyncSession, team_id: str) -> set[int]:
    """获取球队当前已使用的号码集合"""
    result = await db.execute(
        select(Player.squad_number)
        .where(Player.team_id == team_id)
        .where(Player.squad_number.isnot(None))
    )
    return {n for n in result.scalars().all() if n is not None}


async def assign_squad_number(
    db: AsyncSession,
    player: Player,
    team_id: str,
) -> int:
    """为入队球员分配实际队内号码
    
    规则:
    1. 优先使用偏好号码，若无人占用
    2. 若偏好号码被占用，在 12-35 中随机选一个未被占用的
    3. 若 12-35 全满，返回偏好号码（极端情况）
    """
    used_numbers = await get_team_squad_numbers(db, team_id)
    preferred = player.preferred_number
    
    if preferred not in used_numbers:
        player.squad_number = preferred
        return preferred
    
    # 偏好被占用，在 12-35 中选一个随机的可用号码
    available = [n for n in _FALLBACK_NUMBERS if n not in used_numbers]
    if available:
        number = random.choice(available)
        player.squad_number = number
        return number
    
    # 极端情况：全满了，返回偏好号码
    player.squad_number = preferred
    return preferred
