"""
Player fatigue service - 球员疲劳与体力服务
按设计文档 TRAINING-SYSTEM-DESIGN.md 第 5 章实现。
"""
from decimal import Decimal
from typing import Optional

from app.models.player import Player, PlayerPosition
from app.models.season import FixtureType
from app.core.training_config import TrainingItem, INTENSITY_LOAD_POINTS
from app.services.injury_service import InjuryService


# 位置疲劳影响系数 (设计文档 5.2)
_FATIGUE_IMPACT_BY_POSITION = {
    PlayerPosition.GK: 0.0012,
    PlayerPosition.DF: 0.0020,
    PlayerPosition.MF: 0.0026,
    PlayerPosition.FW: 0.0023,
}

# 疲劳区间与效果 (设计文档 5.3)
_FATIGUE_BANDS = [
    (0, 15, "清爽", 1.05),
    (16, 35, "正常", 1.00),
    (36, 55, "累积负荷", 0.92),
    (56, 75, "疲劳", 0.78),
    (76, 90, "重疲劳", 0.60),
    (91, 100, "透支", 0.40),
]

# 比赛对体力和疲劳的影响 (设计文档 5.5)
_MATCH_MINUTES_FITNESS_FATIGUE = {
    (0, 0): (8, -4),       # 未出场
    (1, 20): (-4, 5),
    (21, 40): (-7, 9),
    (41, 55): (-10, 13),
    (56, 70): (-14, 18),
    (71, 999): (-18, 24),
}

# 比赛强度修正
_FIXTURE_TYPE_MODIFIER = {
    FixtureType.LEAGUE: 1.00,
    FixtureType.CUP_LIGHTNING_GROUP: 1.00,
    FixtureType.CUP_LIGHTNING_KNOCKOUT: 1.10,
    FixtureType.CUP_JENNY: 1.05,
    FixtureType.PLAYOFF: 1.10,
}

# 位置比赛疲劳修正
_MATCH_POSITION_MODIFIER = {
    PlayerPosition.GK: 0.45,
    PlayerPosition.DF: 0.95,
    PlayerPosition.MF: 1.10,
    PlayerPosition.FW: 1.00,
}

# 3日训练负荷映射到 state_training_load_score (设计文档 5.8)
_3DAY_LOAD_SCORE_MAP = [
    (-999, 6, 1),    # 恢复/低负荷
    (7, 12, 0),      # 正常负荷
    (13, 18, -1),    # 偏高负荷
    (19, 24, -2),    # 高负荷
    (25, 999, -3),   # 极高负荷
]


def _clamp(val: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, int(round(val))))


class PlayerFatigueService:
    """球员疲劳与体力服务"""
    
    @staticmethod
    def apply_training_load(player: Player, training_item: TrainingItem) -> None:
        """应用训练对体力和疲劳的影响 (设计文档 5.4)"""
        player.fitness = _clamp(player.fitness + training_item.fitness_delta)
        player.fatigue = _clamp(player.fatigue + training_item.fatigue_delta)
    
    @staticmethod
    def apply_match_load(
        player: Player,
        minutes: int,
        fixture_type: FixtureType = FixtureType.LEAGUE,
        resolution: str = "regular",
        red_card_event: bool = False,
    ) -> None:
        """应用比赛对体力和疲劳的影响 (设计文档 5.5)"""
        # 基础变化
        base_fitness_delta = 0
        base_fatigue_delta = 0
        for (min_m, max_m), (f_delta, fat_delta) in _MATCH_MINUTES_FITNESS_FATIGUE.items():
            if min_m <= minutes <= max_m:
                base_fitness_delta = f_delta
                base_fatigue_delta = fat_delta
                break
        
        # 未出场
        if minutes == 0:
            player.fitness = _clamp(player.fitness + base_fitness_delta)
            player.fatigue = _clamp(player.fatigue + base_fatigue_delta)
            return
        
        # 强度修正
        type_mod = _FIXTURE_TYPE_MODIFIER.get(fixture_type, 1.00)
        
        # 加时修正
        if resolution in ("extra_time", "penalties"):
            type_mod *= 1.20
        elif resolution == "penalties_only":
            type_mod *= 1.05
        
        # 红牌少打一人修正
        if red_card_event:
            type_mod *= 1.10
        
        # 位置修正
        pos_mod = _MATCH_POSITION_MODIFIER.get(player.position, 1.00)
        
        # 最终变化
        fatigue_delta = round(base_fatigue_delta * type_mod * pos_mod)
        fitness_delta = base_fitness_delta  # fitness 不受强度修正
        
        player.fitness = _clamp(player.fitness + fitness_delta)
        player.fatigue = _clamp(player.fatigue + fatigue_delta)
    
    @staticmethod
    def apply_daily_recovery(player: Player, had_match: bool = False, had_high_intensity_training: bool = False, activity_type: str = "normal_training") -> dict:
        """自然恢复 (设计文档 5.6)
        
        activity_type: full_rest / recovery_training / light_training / normal_training / high_intensity_training
        返回恢复摘要。
        """
        summary = {}
        
        if had_match:
            # 比赛日只处理伤病恢复，不处理体力和劳损
            recovered = InjuryService.tick_injury_recovery(player)
            if recovered:
                summary["injury_recovered"] = True
            return summary
        
        # 默认恢复体力和疲劳
        if not had_high_intensity_training:
            player.fitness = _clamp(player.fitness + 10)
            player.fatigue = _clamp(player.fatigue - 8)
        
        # 伤病恢复倒计时
        recovered = InjuryService.tick_injury_recovery(player)
        if recovered:
            summary["injury_recovered"] = True
        
        # BodyWear 自然恢复 (伤病系统 v2)
        wear_recovery = InjuryService.apply_daily_recovery(player, activity_type=activity_type)
        if wear_recovery:
            summary["wear_recovery"] = wear_recovery
        
        return summary
    
    @staticmethod
    def calculate_initial_stamina(player: Player) -> float:
        """计算赛前初始 stamina (设计文档 5.2)"""
        sta = getattr(player, 'sta', 10) or 10
        fitness = player.fitness or 100
        base_match_stamina = fitness + (sta - 10) * 1.2
        
        impact = _FATIGUE_IMPACT_BY_POSITION.get(player.position, 0.0023)
        fatigue = player.fatigue or 0
        multiplier = max(0.5, 1 - fatigue * impact)
        
        initial = base_match_stamina * multiplier
        return round(max(35.0, min(100.0, initial)), 1)
    
    @staticmethod
    def get_fatigue_band(player: Player) -> dict:
        """获取疲劳区间信息 (设计文档 5.3)"""
        fatigue = player.fatigue or 0
        for lo, hi, label, growth_factor in _FATIGUE_BANDS:
            if lo <= fatigue <= hi:
                return {
                    "fatigue": fatigue,
                    "band": label,
                    "min": lo,
                    "max": hi,
                    "training_growth_factor": growth_factor,
                    "stamina_multiplier": max(0.5, 1 - fatigue * _FATIGUE_IMPACT_BY_POSITION.get(player.position, 0.0023)),
                }
        return {
            "fatigue": fatigue,
            "band": "透支",
            "min": 91,
            "max": 100,
            "training_growth_factor": 0.40,
            "stamina_multiplier": max(0.5, 1 - fatigue * _FATIGUE_IMPACT_BY_POSITION.get(player.position, 0.0023)),
        }
    
    @staticmethod
    def get_training_recommendation(player: Player) -> str:
        """根据疲劳状态给出训练建议"""
        band = PlayerFatigueService.get_fatigue_band(player)
        fatigue = band["fatigue"]
        
        if fatigue >= 91:
            return "球员严重透支，只能安排恢复或分析训练"
        elif fatigue >= 76:
            return "球员处于重疲劳状态，不建议高强度训练"
        elif fatigue >= 56:
            return "球员疲劳明显，优先恢复或低强度训练"
        elif fatigue >= 36:
            return "球员有一定负荷，控制高强度训练频次"
        elif fatigue >= 16:
            return "球员状态正常，可安排常规训练"
        else:
            return "球员状态清爽，适合专项质量课"
    
    @staticmethod
    def can_do_high_intensity_training(player: Player) -> bool:
        """判断球员是否可以进行高强度训练"""
        return (player.fatigue or 0) < 91
    
    @staticmethod
    def calculate_3day_load_score(load_points_total: int) -> int:
        """根据最近3天训练负荷计算状态分 (设计文档 5.8)"""
        for lo, hi, score in _3DAY_LOAD_SCORE_MAP:
            if lo <= load_points_total <= hi:
                return score
        return -3
    
    @staticmethod
    def recalculate_training_load_score(player: Player, recent_plan_items: list) -> int:
        """重新计算球员的 training_load_score"""
        total_load = sum(
            INTENSITY_LOAD_POINTS.get(getattr(item, 'intensity', 'normal'), 2)
            for item in recent_plan_items
        )
        score = PlayerFatigueService.calculate_3day_load_score(total_load)
        player.state_training_load_score = score
        return score
    
    @staticmethod
    def get_stamina_preview(player: Player) -> dict:
        """获取预计开场体力的预览信息"""
        initial = PlayerFatigueService.calculate_initial_stamina(player)
        band = PlayerFatigueService.get_fatigue_band(player)
        return {
            "fitness": player.fitness,
            "fatigue": player.fatigue,
            "stamina_preview": initial,
            "fatigue_band": band["band"],
            "stamina_multiplier": round(band["stamina_multiplier"], 3),
            "recommendation": PlayerFatigueService.get_training_recommendation(player),
            "can_high_intensity": PlayerFatigueService.can_do_high_intensity_training(player),
        }
