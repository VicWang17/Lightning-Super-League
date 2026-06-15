"""
Training growth service - 训练成长计算服务
按设计文档 TRAINING-SYSTEM-DESIGN.md 第 11 章实现。
"""
import random
import math
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.models.player import Player, PlayerPosition
from app.core.training_config import TrainingItem


# ==================== 成长曲线类型定义 ====================

GROWTH_CURVE_TYPES = {
    "early_bloomer": "早熟",
    "steady": "平稳",
    "late_bloomer": "晚熟",
    "explosive": "爆发型",
    "plateau": "平台型",
}

# 年龄成长倍率查表。
#
# 调参目标：
# - 18-23 岁高潜球员在稳定一线队训练下，3-4 个赛季可以接近个人上限。
# - 29+ 球员主要靠比赛保持状态，训练只做专项微调，不能继续大幅成长。
_AGE_FACTOR_TABLE = {
    # (min_age, max_age): {curve_type: factor}
    (16, 18): {"early_bloomer": 1.40, "steady": 1.10, "late_bloomer": 0.80},
    (19, 21): {"early_bloomer": 1.55, "steady": 1.30, "late_bloomer": 1.00},
    (22, 24): {"early_bloomer": 1.25, "steady": 1.35, "late_bloomer": 1.15},
    (25, 27): {"early_bloomer": 0.70, "steady": 1.00, "late_bloomer": 1.10},
    (28, 30): {"early_bloomer": 0.20, "steady": 0.35, "late_bloomer": 0.55},
    (31, 32): {"early_bloomer": 0.03, "steady": 0.08, "late_bloomer": 0.20},
    (33, 99): {"early_bloomer": 0.00, "steady": 0.00, "late_bloomer": 0.03},
}

_DEVELOPMENT_STAGE_FACTOR = [
    (16, 18, 1.40),
    (19, 21, 1.45),
    (22, 24, 1.25),
    (25, 27, 0.95),
    (28, 28, 0.55),
    (29, 29, 0.35),
    (30, 30, 0.25),
    (31, 32, 0.12),
    (33, 99, 0.03),
]

# 重复训练递减 (设计文档 11.7)
_DIMINISHING_TABLE = {
    (1, 2): 1.00,
    (3, 4): 0.85,
    (5, 6): 0.70,
    (7, 999): 0.60,
}

# 位置疲劳影响系数 (设计文档 5.2)
FATIGUE_IMPACT_BY_POSITION = {
    PlayerPosition.GK: 0.0012,
    PlayerPosition.DF: 0.0020,
    PlayerPosition.MF: 0.0026,
    PlayerPosition.FW: 0.0023,
}

# 疲劳区间与训练成长倍率 (设计文档 5.3)
_FATIGUE_BANDS = [
    (0, 15, 1.05),
    (16, 35, 1.00),
    (36, 55, 0.92),
    (56, 75, 0.78),
    (76, 90, 0.60),
    (91, 100, 0.40),
]

# 分组效率倍率 (设计文档 7.4)
_GROUP_FIT_MULTIPLIER = {
    "team": 1.00,
    "groups_2": 1.05,
    "groups_3": 1.10,
}

# 全部属性名列表
_ALL_ATTRIBUTES = [
    "sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
    "defe", "tkl", "vis", "cro", "con", "fin",
    "com", "sav", "ref", "pos", "rus", "dec", "fk", "pk"
]


class TrainingGrowthService:
    """训练成长计算服务"""
    
    @staticmethod
    def calculate_age_factor(age: int, curve_type: str, peak_age: int = 27) -> float:
        """根据年龄和成长曲线计算年龄倍率"""
        if not curve_type or curve_type not in GROWTH_CURVE_TYPES:
            curve_type = "steady"
        
        for (min_age, max_age), factors in _AGE_FACTOR_TABLE.items():
            if min_age <= age <= max_age:
                base = factors.get(curve_type, 1.0)
                # 根据 peak_age 微调
                if curve_type == "late_bloomer" and peak_age >= 30:
                    base *= 1.05
                elif curve_type == "early_bloomer" and age <= 20:
                    base *= 1.05
                return base
        return 0.0
    
    @staticmethod
    def calculate_potential_factor(current: float, cap: float) -> float:
        """潜力接近衰减。

        15+ 后采用指数式衰减：越接近 20，成长越困难；
        19->20 应该是历史级球员才可能长期冲击的区间。
        """
        remaining = cap - current
        if remaining <= 0:
            return 0.0
        cap_gap_factor = min(1.05, max(0.015, (remaining / 6.0) ** 2.10))
        high_attr_factor = TrainingGrowthService.calculate_high_attribute_factor(current)
        return round(cap_gap_factor * high_attr_factor, 4)

    @staticmethod
    def calculate_high_attribute_factor(current: float) -> float:
        """当前属性越高，成长越难。"""
        if current < 15:
            return 1.0
        return max(0.008, 0.62 ** (current - 14.0))

    @staticmethod
    def attribute_breakthrough_cost(current: float, cap: float | None = None) -> float:
        """从当前整数属性提升 1 点所需的成长进度成本。"""
        if cap is not None and math.floor(cap) <= current:
            return math.inf
        if current < 15:
            return 1.0
        base = 1.35 ** (current - 14.0)
        if current >= 18:
            base *= 1.8
        if current >= 19:
            base *= 3.0
        return round(base, 3)

    @staticmethod
    def calculate_development_stage_factor(
        age: int,
        potential_max: int | None = None,
        curve_type: str | None = None,
        peak_age: int | None = None,
    ) -> float:
        """年龄阶段倍率。

        年轻球员需要足够成长空间，才能支撑 3-4 个赛季培养到接近上限；
        老将训练收益必须快速衰减，避免 30+ 球员继续靠训练大幅涨点。
        """
        factor = 0.03
        for min_age, max_age, value in _DEVELOPMENT_STAGE_FACTOR:
            if min_age <= age <= max_age:
                factor = value
                break
        if curve_type == "late_bloomer" and (peak_age or 0) >= 30:
            if 28 <= age <= 30:
                factor = max(factor, 0.75)
            elif 31 <= age <= 32:
                factor = max(factor, 0.45)
        if age <= 23 and (potential_max or 0) >= 70:
            factor *= 1.10
        if age <= 21 and (potential_max or 0) >= 80:
            factor *= 1.08
        return factor
    
    @staticmethod
    def calculate_diminishing_factor(recent_count: int) -> float:
        """重复训练递减 (设计文档 11.7)"""
        if recent_count <= 0:
            return 1.00
        for (min_c, max_c), factor in _DIMINISHING_TABLE.items():
            if min_c <= recent_count <= max_c:
                return factor
        return 0.60
    
    @staticmethod
    def calculate_fatigue_factor(fatigue: int) -> float:
        """疲劳对训练成长的影响 (设计文档 5.3 / 11.5)"""
        for lo, hi, factor in _FATIGUE_BANDS:
            if lo <= fatigue <= hi:
                return factor
        return 0.40

    @staticmethod
    def calculate_decline_factor(age: int, curve_type: str, peak_age: int = 27) -> float:
        """年龄退步/进步偏移量。

        直接加到 gain 上的偏移值：
        - 年轻为正，促进成长
        - 巅峰期为 0
        - 年老为负，导致属性衰退
        """
        if not curve_type or curve_type not in GROWTH_CURVE_TYPES:
            curve_type = "steady"

        if age <= 18:
            base = 0.10
        elif age <= 21:
            base = 0.08
        elif age <= 24:
            base = 0.04
        elif age <= 27:
            base = 0.0
        elif age <= 30:
            base = -0.03
        elif age <= 32:
            base = -0.07
        elif age == 33:
            base = -0.11
        elif age == 34:
            base = -0.16
        elif age == 35:
            base = -0.22
        else:
            base = -0.25

        # 晚熟型在巅峰后期衰退更慢
        if curve_type == "late_bloomer" and (peak_age or 0) >= 30:
            if age <= 32:
                base = max(base, -0.01)
            elif age == 33:
                base = max(base, -0.08)
            elif age == 34:
                base = max(base, -0.12)
            else:
                base = max(base, -0.18)

        # 早发型衰退更早
        if curve_type == "early_bloomer" and age >= 26:
            base -= 0.02

        # 爆发型巅峰短，衰退更早更猛
        if curve_type == "explosive" and age >= 25:
            base -= 0.02

        return round(base, 2)
    
    @staticmethod
    def calculate_group_fit(mode: str) -> float:
        """分组效率倍率"""
        return _GROUP_FIT_MULTIPLIER.get(mode, 1.00)
    
    @staticmethod
    def calculate_single_attribute_gain(
        player: Player,
        training_item: TrainingItem,
        attribute: str,
        attribute_weight: float,
        age: int,
        recent_count: int,
        mode: str = "team",
    ) -> float:
        """计算单项属性的成长值 (设计文档 11.5)"""
        
        # 1. base_gain
        base_gain = training_item.base_gain
        
        # 2. attribute_weight
        weight = attribute_weight
        
        # 3. age_factor
        curve_type = player.growth_curve_type or "steady"
        peak_age = player.growth_peak_age or 27
        age_factor = TrainingGrowthService.calculate_age_factor(age, curve_type, peak_age)
        
        # 4. growth_speed
        growth_speed = float(player.growth_speed or Decimal("1.00"))

        # 4.5 development stage
        development_stage = TrainingGrowthService.calculate_development_stage_factor(
            age, player.potential_max or 50, curve_type, peak_age
        )
        
        # 5. potential_factor
        current_val = float(getattr(player, attribute, 10))
        progress = player.attribute_progress or {}
        current_decimal = float(progress.get(attribute, 0.0))
        current_total = current_val + current_decimal
        
        caps = player.attribute_caps or {}
        cap = caps.get(attribute)
        if cap is None:
            # 没有单独上限时，用 potential_max 推导临时上限
            cap = TrainingGrowthService._derive_cap_from_potential(player, attribute)
        cap = min(cap, 20.0)
        
        potential_factor = TrainingGrowthService.calculate_potential_factor(current_total, cap)
        if current_total >= cap or current_total >= 20.0:
            potential_factor = 0.0
        
        # 6. position_fit
        position_fit = training_item.position_fit.get(player.position.value, 1.0)
        
        # 7. group_fit
        group_fit = TrainingGrowthService.calculate_group_fit(mode)
        
        # 8. diminishing_factor
        diminishing = TrainingGrowthService.calculate_diminishing_factor(recent_count)
        if training_item.is_recovery:
            diminishing = 1.00
        
        # 9. fatigue_factor
        fatigue_factor = TrainingGrowthService.calculate_fatigue_factor(player.fatigue or 0)
        
        # 10. random_factor
        stability = float(player.growth_stability or Decimal("1.00"))
        random_range = 0.15 * min(stability, 1.5)
        random_factor = 1.0 + random.uniform(-random_range, random_range)
        
        # 计算最终成长
        gain = (
            base_gain
            * weight
            * age_factor
            * growth_speed
            * development_stage
            * potential_factor
            * position_fit
            * group_fit
            * diminishing
            * fatigue_factor
            * random_factor
        )
        
        # 11. decline_factor：年龄退步/进步偏移
        decline_factor = TrainingGrowthService.calculate_decline_factor(age, curve_type, peak_age)
        gain += decline_factor

        # 恢复训练不衰退，但上限很小
        if training_item.is_recovery:
            gain = max(gain, 0.0)
            gain = min(gain, 0.02)

        # 单次训练成长/衰退上限保护
        gain = max(gain, -0.25)

        return round(gain, 4)
    
    @staticmethod
    def _derive_cap_from_potential(player: Player, attribute: str) -> float:
        """根据 potential_max 推导属性临时上限"""
        potential = player.potential_max or 50
        # 基础：potential_max 映射到 1-20 区间
        base_cap = (potential / 100.0) * 18 + 1
        # 根据位置权重微调
        position = player.position
        from app.models.player import _OVR_WEIGHTS
        weights = _OVR_WEIGHTS.get(position, {})
        attr_weight = weights.get(attribute, 0)
        if attr_weight >= 10:
            base_cap *= 1.15
        elif attr_weight >= 5:
            base_cap *= 1.05
        else:
            base_cap *= 0.85
        return min(base_cap, 20.0)
    
    @staticmethod
    def generate_player_growth_profile(potential_max: int, position: PlayerPosition, actual_age: int) -> dict:
        """为新球员生成成长曲线和属性上限 (设计文档 11.2 / 11.3)"""
        
        # 成长曲线类型
        curve_weights = {
            "early_bloomer": 0.20,
            "steady": 0.35,
            "late_bloomer": 0.20,
            "explosive": 0.15,
            "plateau": 0.10,
        }
        curve_type = random.choices(
            list(curve_weights.keys()),
            weights=list(curve_weights.values()),
            k=1
        )[0]
        
        # 巅峰年龄
        if curve_type == "early_bloomer":
            peak_age = random.randint(24, 27)
        elif curve_type == "late_bloomer":
            peak_age = random.randint(28, 32)
        elif curve_type == "plateau":
            peak_age = random.randint(22, 26)
        else:
            peak_age = random.randint(26, 30)
        
        # 成长速度系数 (0.62 - 1.24)。高潜代表上限，不代表必然高速练满。
        base_speed = 0.74 + (potential_max / 100.0) * 0.34
        if curve_type == "explosive":
            base_speed += random.uniform(0.03, 0.10)
        elif curve_type == "plateau":
            base_speed -= random.uniform(0.05, 0.14)
        if actual_age <= 21 and potential_max >= 75:
            base_speed += 0.04
        growth_speed = round(max(0.62, min(1.24, base_speed)), 2)
        
        # 成长稳定性 (0.60 - 1.40)
        stability = round(random.uniform(0.80, 1.20), 2)
        if curve_type == "explosive":
            stability = round(random.uniform(0.60, 0.95), 2)
        
        # 晚熟系数
        late_bloom = round(random.uniform(0.90, 1.10), 2)
        if curve_type == "late_bloomer":
            late_bloom = round(random.uniform(1.05, 1.20), 2)
        
        # 属性上限 (设计文档 11.2)
        attribute_caps = TrainingGrowthService._generate_attribute_caps(potential_max, position)
        
        return {
            "growth_peak_age": peak_age,
            "growth_curve_type": curve_type,
            "growth_speed": Decimal(str(growth_speed)),
            "growth_stability": Decimal(str(stability)),
            "late_bloom_factor": Decimal(str(late_bloom)),
            "attribute_caps": attribute_caps,
        }
    
    @staticmethod
    def _generate_attribute_caps(potential_max: int, position: PlayerPosition) -> dict[str, float]:
        """生成各属性隐藏上限"""
        from app.models.player import _OVR_WEIGHTS
        weights = _OVR_WEIGHTS.get(position, {})
        
        # 总潜力映射到属性总和的参考值
        total_potential_units = potential_max * 2.3  # 经验系数
        
        caps = {}
        for attr in _ALL_ATTRIBUTES:
            w = weights.get(attr, 0)
            # 核心属性上限更高
            if w >= 10:
                base = 15.5 + (potential_max - 50) / 50.0 * 3.7
            elif w >= 5:
                base = 13.8 + (potential_max - 50) / 50.0 * 3.5
            elif w > 0:
                base = 11.8 + (potential_max - 50) / 50.0 * 3.2
            else:
                base = 12.4 + (potential_max - 50) / 50.0 * 3.8
            
            # 添加随机方差
            variance = random.uniform(-1.4, 1.0)
            raw_cap = base + variance
            hard_cap = 18.85
            if potential_max >= 99 and w >= 10 and raw_cap >= 19.4:
                hard_cap = 20.0
            elif potential_max >= 95 and w >= 10:
                hard_cap = 19.35
            elif potential_max >= 90 and w >= 10:
                hard_cap = 19.0
            elif potential_max >= 85 and w >= 5:
                hard_cap = 18.65
            cap = round(max(3.0, min(hard_cap, raw_cap)), 2)
            caps[attr] = cap
        
        return caps
    
    @staticmethod
    def apply_attribute_progress(player: Player, gains: dict[str, float]) -> list[dict]:
        """应用属性成长/衰退，处理小数进位，返回整数突破/衰退记录"""
        breakthroughs = []
        progress = dict(player.attribute_progress or {})

        for attr, gain in gains.items():
            if gain == 0:
                continue

            current_val = getattr(player, attr, 10)
            caps = player.attribute_caps or {}
            cap = float(caps.get(attr, TrainingGrowthService._derive_cap_from_potential(player, attr)))
            cap = min(cap, 20.0)
            current_progress = float(progress.get(attr, 0.0))
            new_progress = current_progress + gain

            # 处理整数进位（正数为突破，负数为衰退）
            if new_progress >= 0:
                int_gain = 0
                while new_progress >= TrainingGrowthService.attribute_breakthrough_cost(current_val, cap):
                    cost = TrainingGrowthService.attribute_breakthrough_cost(current_val, cap)
                    if cost == math.inf:
                        new_progress = 0.0
                        break
                    new_progress -= cost
                    int_gain += 1
                    current_val += 1
            else:
                int_gain = int(new_progress)

            if int_gain != 0:
                current_val = getattr(player, attr, 10)
                before_val = current_val
                after_val = max(1, min(20, int(math.floor(min(cap, current_val + int_gain)))))
                actual_change = after_val - before_val

                if actual_change != 0:
                    setattr(player, attr, after_val)
                    if actual_change > 0:
                        breakthroughs.append({
                            "attribute": attr,
                            "before": before_val,
                            "after": after_val,
                            "type": "breakthrough",
                        })
                    else:
                        breakthroughs.append({
                            "attribute": attr,
                            "before": before_val,
                            "after": after_val,
                            "type": "decline",
                        })

                if int_gain < 0:
                    new_progress -= int_gain

            progress[attr] = round(new_progress, 4)

        player.attribute_progress = progress
        return breakthroughs
