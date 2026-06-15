"""
Player Generator Service - 球员生成器

职责:
- 按种族/region生成姓名
- 按位置原型(Archetype)+风格(Style)生成23项属性
- 分配招牌技能、性格、头像
- 为球队生成完整阵容(squad)
"""
import json
import os
import random
from decimal import Decimal
from typing import Optional
from pathlib import Path

from app.models.player import (
    Player, PlayerPosition, PlayerFoot, PlayerRace, PlayerStatus,
    PotentialLetter, PlayerPersonality, ContractType, MatchForm, SquadRole,
    OriginType,
)
from app.services.player_number_service import generate_preferred_number
from app.services.training_growth_service import TrainingGrowthService


# ==================== 配置 ====================

# Race -> Region 概率分布
REGION_DISTRIBUTION = {
    "asian": {
        "ChineseSurname": 0.60,
        "Japanese": 0.15,
        "Korean": 0.15,
        "SoutheastAsia": 0.10,
    },
    "western": {
        "English": 0.25,
        "WesternEurope": 0.20,
        "Latin": 0.20,
        "Slavic": 0.15,
        "Nordic": 0.10,
        "Arabic": 0.10,
    }
}

# 位置 -> Archetype 列表与占比
ARCHETYPE_CONFIG = {
    PlayerPosition.FW: [
        ("射手型", 0.30),
        ("速度型", 0.25),
        ("支点型", 0.20),
        ("边锋型", 0.25),
    ],
    PlayerPosition.MF: [
        ("工兵型", 0.25),
        ("组织型", 0.25),
        ("攻击型", 0.20),
        ("全能型", 0.20),
        ("边翼型", 0.10),
    ],
    PlayerPosition.DF: [
        ("中卫型", 0.40),
        ("边卫型", 0.35),
        ("清道夫型", 0.25),
    ],
    PlayerPosition.GK: [
        ("传统型", 0.50),
        ("出击型", 0.30),
        ("出球型", 0.20),
    ],
}

# Style 分布
STYLE_DISTRIBUTION = [
    ("标准型", 0.72),
    ("天才型", 0.16),
    ("平均型", 0.12),
]

# 潜力分布 -> (letter, min_potential, max_potential, weight)
POTENTIAL_DISTRIBUTION = [
    (PotentialLetter.S, 95, 100, 0.006),
    (PotentialLetter.A, 85, 94, 0.054),
    (PotentialLetter.B, 75, 84, 0.23),
    (PotentialLetter.C, 65, 74, 0.39),
    (PotentialLetter.D, 50, 64, 0.32),
]

# 年龄分布 -> (min_age, max_age, weight)
AGE_DISTRIBUTION = [
    (17, 20, 0.18),
    (21, 25, 0.42),
    (26, 28, 0.22),
    (29, 31, 0.12),
    (32, 35, 0.06),
]

# Archetype -> 核心属性加成权重 (相对于位置基准的偏移)
ARCHETYPE_BIAS = {
    # FW
    "射手型": {"sho": 1.15, "hea": 1.10, "str_": 1.08, "fin": 1.10, "bal": 1.05, "pk": 1.10},
    "速度型": {"spd": 1.18, "acc": 1.15, "dri": 1.12, "sho": 1.05, "pk": 1.05},
    "支点型": {"str_": 1.15, "hea": 1.12, "pas": 1.08, "bal": 1.10, "pk": 1.05},
    "边锋型": {"spd": 1.15, "dri": 1.12, "cro": 1.12, "sta": 1.08, "fk": 1.08},
    # MF
    "工兵型": {"sta": 1.18, "defe": 1.15, "tkl": 1.12, "str_": 1.10},
    "组织型": {"pas": 1.18, "vis": 1.15, "con": 1.12, "sta": 1.10, "fk": 1.10},
    "攻击型": {"sho": 1.12, "pas": 1.12, "vis": 1.10, "fin": 1.10, "fk": 1.08},
    "全能型": {},  # 无加成，均衡
    "边翼型": {"spd": 1.12, "cro": 1.12, "dri": 1.10, "sta": 1.10, "fk": 1.10},
    # DF
    "中卫型": {"defe": 1.18, "hea": 1.15, "str_": 1.15, "bal": 1.10, "com": 1.08},
    "边卫型": {"spd": 1.15, "sta": 1.12, "cro": 1.10, "defe": 1.12, "fk": 1.05},
    "清道夫型": {"defe": 1.15, "vis": 1.12, "pas": 1.10, "tkl": 1.10, "com": 1.10},
    # GK
    "传统型": {"sav": 1.15, "ref": 1.12, "pos": 1.10, "com": 1.10, "dec": 1.08},
    "出击型": {"sav": 1.12, "ref": 1.10, "rus": 1.15, "spd": 1.05, "fk": 1.05, "dec": 1.05},
    "出球型": {"sav": 1.10, "ref": 1.10, "pos": 1.10, "pas": 1.12, "com": 1.05, "dec": 1.10},
}

# 位置 -> 非核心属性惩罚系数 (非核心属性 × 0.6~0.8)
POSITION_NON_CORE_ATTRS = {
    PlayerPosition.FW: {"sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal", "fin", "pk", "dec"},
    PlayerPosition.MF: {"pas", "dri", "spd", "str_", "sta", "defe", "vis", "tkl", "acc", "cro", "con", "fin", "fk", "dec"},
    PlayerPosition.DF: {"spd", "str_", "sta", "defe", "hea", "tkl", "vis", "cro", "bal", "com", "dec"},
    PlayerPosition.GK: {"com", "sav", "ref", "pos", "rus", "dec", "pas", "fk", "pk"},
}

# OVR 权重 (4位置简化版, 总和100)
OVR_WEIGHTS = {
    PlayerPosition.FW: {
        "sho": 20, "pas": 3, "dri": 15, "spd": 18, "str_": 10, "sta": 3,
        "hea": 10, "acc": 10, "fin": 5, "bal": 3, "cro": 3, "dec": 4,
        "defe": 0, "vis": 0, "tkl": 0, "con": 0, "com": 0, "sav": 0, "ref": 0, "pos": 0,
        "fk": 0, "pk": 0, "rus": 0,
    },
    PlayerPosition.MF: {
        "pas": 16, "dri": 11, "spd": 7, "str_": 2, "sta": 14, "defe": 9,
        "vis": 13, "tkl": 6, "acc": 2, "cro": 7, "con": 7, "fin": 5, "dec": 10,
        "sho": 2, "hea": 0, "bal": 0, "com": 0, "sav": 0, "ref": 0, "pos": 0,
        "fk": 0, "pk": 0, "rus": 0,
    },
    PlayerPosition.DF: {
        "pas": 5, "spd": 11, "str_": 16, "sta": 11, "defe": 22, "hea": 11,
        "tkl": 7, "cro": 5, "bal": 4, "dec": 8,
        "dri": 0, "vis": 0, "acc": 0, "con": 0, "fin": 0, "sho": 0, "com": 0, "sav": 0, "ref": 0, "pos": 0,
        "fk": 0, "pk": 0, "rus": 0,
    },
    PlayerPosition.GK: {
        "pas": 5, "com": 8, "sav": 25, "ref": 18, "pos": 10, "rus": 8, "dec": 12,
        "sho": 0, "dri": 0, "spd": 0, "str_": 0, "sta": 0, "defe": 0, "hea": 0,
        "vis": 0, "tkl": 0, "acc": 0, "cro": 0, "con": 0, "fin": 0, "bal": 0,
        "fk": 0, "pk": 0,
    },
}

PLAYER_ATTRIBUTES = [
    "sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
    "defe", "tkl", "vis", "cro", "con", "fin", "com", "sav", "ref",
    "pos", "rus", "dec", "fk", "pk",
]

# Archetype-specific weaknesses create recognizable tradeoffs instead of
# simply boosting every relevant attribute together.
ARCHETYPE_WEAKNESS_BIAS = {
    "射手型": {"spd": 1.35, "acc": 1.25, "dri": 1.15, "sta": 1.10},
    "速度型": {"str_": 1.35, "hea": 1.20, "pas": 1.10, "dec": 1.10},
    "支点型": {"spd": 1.45, "acc": 1.35, "dri": 1.15},
    "边锋型": {"str_": 1.25, "hea": 1.20, "defe": 1.10},
    "工兵型": {"sho": 1.25, "fin": 1.20, "vis": 1.10, "fk": 1.10},
    "组织型": {"spd": 1.25, "str_": 1.20, "sho": 1.10, "hea": 1.10},
    "攻击型": {"defe": 1.30, "tkl": 1.25, "str_": 1.10},
    "全能型": {},
    "边翼型": {"str_": 1.20, "hea": 1.15, "defe": 1.10},
    "中卫型": {"spd": 1.25, "acc": 1.20, "dri": 1.15, "sho": 1.10},
    "边卫型": {"str_": 1.25, "hea": 1.20, "sho": 1.10},
    "清道夫型": {"sho": 1.25, "fin": 1.20, "acc": 1.10},
    "传统型": {"pas": 1.25, "spd": 1.15, "rus": 1.10},
    "出击型": {"pos": 1.20, "pas": 1.15, "pk": 1.10},
    "出球型": {"str_": 1.20, "rus": 1.15, "pk": 1.10},
}

ATTRIBUTE_PROFILE_DISTRIBUTION = {
    "标准型": [
        ("specialist", 0.36),
        ("flawed_starter", 0.28),
        ("balanced", 0.22),
        ("volatile", 0.10),
        ("all_rounder", 0.04),
    ],
    "天才型": [
        ("specialist", 0.40),
        ("volatile", 0.28),
        ("flawed_starter", 0.18),
        ("balanced", 0.09),
        ("all_rounder", 0.05),
    ],
    "平均型": [
        ("balanced", 0.52),
        ("flawed_starter", 0.22),
        ("specialist", 0.16),
        ("all_rounder", 0.08),
        ("volatile", 0.02),
    ],
}

ATTRIBUTE_PROFILE_CONFIG = {
    "specialist": {
        "strengths": (2, 3), "weaknesses": (2, 4),
        "strong_bonus": (2.4, 4.8), "weak_penalty": (2.2, 4.4),
        "variance": 1.4,
    },
    "flawed_starter": {
        "strengths": (1, 2), "weaknesses": (3, 5),
        "strong_bonus": (1.8, 3.6), "weak_penalty": (2.6, 5.0),
        "variance": 1.2,
    },
    "balanced": {
        "strengths": (1, 2), "weaknesses": (1, 2),
        "strong_bonus": (1.2, 2.6), "weak_penalty": (1.0, 2.4),
        "variance": 0.9,
    },
    "volatile": {
        "strengths": (3, 4), "weaknesses": (3, 5),
        "strong_bonus": (2.8, 5.2), "weak_penalty": (2.8, 5.4),
        "variance": 1.8,
    },
    "all_rounder": {
        "strengths": (3, 5), "weaknesses": (0, 1),
        "strong_bonus": (1.0, 2.2), "weak_penalty": (0.8, 1.6),
        "variance": 0.7,
    },
}

# 招牌技能池 (按位置)。技能名必须与 Go 引擎 skillHandlers 保持一致。
SKILL_POOL = {
    "通用": [
        ("铁人", "全场持续", "体能消耗降低，受伤概率降低"),
        ("领导力", "全队区域控制", "队友获得区域控制加成，仅取最高品质"),
        ("玻璃体质", "受伤触发时", "受伤概率提升，负面技能"),
        ("大场面先生", "比赛最后阶段", "全属性临时提升"),
        ("快速恢复", "体能衰减时", "周期性恢复额外体能"),
    ],
    "FW": [
        ("禁区幽灵", "禁区内射门时", "禁区内进攻加成"),
        ("抢点专家", "传中/角球争顶时", "抢点争顶加成"),
        ("远射重炮", "禁区外射门时", "远射进攻加成"),
        ("边路尖刀", "边路突破时", "边路事件权重提升"),
        ("盘带大师", "1v1突破时", "盘带突破加成"),
        ("致命直塞", "直塞球时", "直塞成功率和事件权重提升"),
        ("内切杀手", "边路内切射门时", "内切进攻加成"),
        ("点球专家", "主罚点球时", "点球进攻加成"),
        ("补射猎手", "门将脱手后", "补射事件权重提升"),
        ("花式魔术师", "盘带和摆脱时", "盘带类事件进攻加成"),
    ],
    "MF": [
        ("手术刀传球", "短传/直塞时", "关键传球进攻加成"),
        ("节拍器", "持球组织时", "区域控制加成"),
        ("全能中场", "攻防转换时", "攻防转换事件加成"),
        ("长传调度", "长传转移时", "长传事件加成"),
        ("拦截专家", "预判拦截时", "拦截事件加成"),
        ("组织核心", "进攻组织时", "组织事件权重提升"),
        ("定位球大师", "任意球/角球时", "定位球进攻加成"),
        ("绞肉机", "逼抢/铲球时", "对抗事件加成"),
    ],
    "DF": [
        ("铁壁", "1v1防守时", "防守对抗加成"),
        ("铲球专家", "铲球时", "铲球事件加成"),
        ("预判大师", "对方传球时", "预判防守加成"),
        ("盯人专家", "人盯人时", "降低对手事件权重"),
        ("空中堡垒", "争顶/解围时", "空中攻防加成"),
        ("边路屏障", "边路防守时", "边路防守加成"),
        ("清道夫", "补位防守时", "补位防守和控制加成"),
    ],
    "GK": [
        ("神反应", "近距离射门扑救时", "近距离扑救加成"),
        ("门线技术", "门线救险时", "门线防守加成"),
        ("出击果断", "单刀球出击时", "出击防守加成"),
        ("手抛球反击", "扑救后手抛球时", "反击发起加成"),
        ("点球克星", "扑点球时", "点球防守加成"),
    ],
}

SKILL_QUALITY_COLORS = {
    "普通": "white",
    "优秀": "blue",
    "精英": "purple",
    "名人堂": "red",
}

SKILL_QUALITY_WEIGHTS = [
    ("普通", 62),
    ("优秀", 27),
    ("精英", 9),
    ("名人堂", 2),
]

PERSONALITIES = list(PlayerPersonality)

INITIAL_WAGE_TABLE = (
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
)


def estimate_initial_wage(ovr: int, potential_max: int, age: int) -> Decimal:
    """Estimate season wage for generated players using the same scale as contracts."""
    if ovr <= INITIAL_WAGE_TABLE[0][0]:
        base = INITIAL_WAGE_TABLE[0][1]
    elif ovr >= INITIAL_WAGE_TABLE[-1][0]:
        base = INITIAL_WAGE_TABLE[-1][1]
    else:
        base = INITIAL_WAGE_TABLE[0][1]
        for (low_ovr, low_wage), (high_ovr, high_wage) in zip(INITIAL_WAGE_TABLE, INITIAL_WAGE_TABLE[1:]):
            if low_ovr <= ovr <= high_ovr:
                ratio = Decimal(ovr - low_ovr) / Decimal(high_ovr - low_ovr)
                base = low_wage + (high_wage - low_wage) * ratio
                break

    potential_gap = max(potential_max - ovr, 0)
    potential_modifier = Decimal("1") + Decimal(min(potential_gap, 20)) * Decimal("0.006")
    if age <= 20:
        age_modifier = Decimal("0.70")
    elif age <= 23:
        age_modifier = Decimal("0.88")
    elif age <= 30:
        age_modifier = Decimal("1.00")
    elif age <= 34:
        age_modifier = Decimal("0.90")
    else:
        age_modifier = Decimal("0.75")
    return (base * potential_modifier * age_modifier).quantize(Decimal("100"))

# Squad 配比: 位置 -> 人数
SQUAD_COMPOSITION = [
    (PlayerPosition.GK, 2),
    (PlayerPosition.DF, 5),
    (PlayerPosition.MF, 5),
    (PlayerPosition.FW, 3),
]

INITIAL_TEAM_OVR_BY_LEVEL = {
    1: (78, 82),
    2: (68, 73),
    3: (58, 64),
    4: (48, 55),
}

INITIAL_SQUAD_OVR_TIERS = {
    1: [(86, 88, 2), (82, 85, 4), (76, 81, 6), (68, 75, 3)],
    2: [(84, 86, 1), (76, 83, 3), (66, 75, 6), (58, 65, 6)],
    3: [(70, 76, 1), (63, 69, 4), (56, 62, 6), (48, 55, 5)],
    4: [(62, 68, 1), (53, 61, 4), (45, 52, 6), (38, 47, 5)],
}
INITIAL_LEVEL_ONE_ELITE_PROBABILITY = 0.40
INITIAL_LEVEL_ONE_ELITE_OVR_RANGE = (90, 94)

HIGH_ATTRIBUTE_VALUE_WEIGHTS = {
    16: 1.00,
    17: 0.68,
    18: 0.38,
    19: 0.18,
    20: 0.07,
}
HIGH_ATTRIBUTE_STEP_WEIGHTS = {
    16: 1.00,
    17: 0.72,
    18: 0.46,
    19: 0.24,
    20: 0.10,
}


# ==================== 工具函数 ====================

def _weighted_choice(items: list) -> any:
    """按权重随机选择"""
    weights = [w for _, w in items]
    choices = [c for c, _ in items]
    return random.choices(choices, weights=weights, k=1)[0]


def _clamp(val: int, lo: int = 1, hi: int = 20) -> int:
    return max(lo, min(hi, int(round(val))))


def _shape_high_attribute_value(val: float, *, is_strength: bool = False, is_elite: bool = False) -> int:
    rounded = _clamp(val)
    if rounded < 16:
        return rounded

    max_value = rounded
    weights = []
    candidates = list(range(16, max_value + 1))
    for candidate in candidates:
        weight = HIGH_ATTRIBUTE_VALUE_WEIGHTS[candidate]
        if is_strength:
            weight *= 1.0 + (candidate - 16) * 0.16
        if is_elite:
            weight *= 1.0 + (candidate - 16) * 0.12
        weights.append(weight)
    return random.choices(candidates, weights=weights, k=1)[0]


def calculate_initial_team_overall(league_level: int, team_index: int = 1) -> int:
    """Return the public team OVR used by initial data generation."""
    low, high = INITIAL_TEAM_OVR_BY_LEVEL.get(league_level, INITIAL_TEAM_OVR_BY_LEVEL[3])
    span = max(high - low, 0)
    rank_bonus = max(0, (8 - team_index) // 2)
    return min(high, low + rank_bonus + random.randint(0, max(span - rank_bonus, 0)))


# ==================== 名字生成器 ====================

class NameGenerator:
    def __init__(self, data_path: str = None):
        if data_path is None:
            # 相对路径: 从 backend/app/services/ 到 design/name_generator.json
            base = Path(__file__).resolve().parents[3]
            data_path = base / "design" / "name_generator.json"
        with open(data_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        self._build_pools()
    
    def _build_pools(self):
        """预构建按region分组的池子"""
        # Chinese
        self.chinese_surnames = self.data["chinese_surnames"]
        self.chinese_single = self.data["chinese_single_names"]
        self.chinese_double = self.data["chinese_double_names"]
        
        # Foreign names by region
        self.foreign_names_by_region = {}
        for item in self.data["foreign_names"]:
            r = item["region"]
            self.foreign_names_by_region.setdefault(r, []).append(item)
        
        # Foreign surnames by region
        self.foreign_surnames_by_region = self.data["foreign_surnames"]
    
    def _weighted_pick(self, pool: list, key: str = "freq") -> str:
        weights = [item.get(key, 1) for item in pool]
        names = [item["name"] for item in pool]
        return random.choices(names, weights=weights, k=1)[0]
    
    def generate(self, race: str) -> tuple[str, str]:
        """
        返回 (name, region)
        name: 生成的全名
        region: 使用的region
        """
        region = _weighted_choice(list(REGION_DISTRIBUTION[race].items()))
        
        if region == "ChineseSurname":
            surname = self._weighted_pick(self.chinese_surnames)
            # 70% 双字名, 30% 单字名
            if random.random() < 0.7:
                given = self._weighted_pick(self.chinese_double)
            else:
                given = self._weighted_pick(self.chinese_single)
            return f"{surname}{given}", region
        else:
            surname_pool = self.foreign_surnames_by_region.get(region, [])
            name_pool = self.foreign_names_by_region.get(region, [])
            if not surname_pool or not name_pool:
                # fallback to English
                surname_pool = self.foreign_surnames_by_region.get("English", [])
                name_pool = self.foreign_names_by_region.get("English", [])
            surname = self._weighted_pick(surname_pool)
            given = self._weighted_pick(name_pool)
            return f"{given} {surname}", region


# ==================== 头像池 ====================

class AvatarPool:
    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = Path(__file__).resolve().parents[3] / "frontend" / "public" / "avatars"
        self.base_path = Path(base_path)
        self.asian_field = self._load_pool("asian_field")
        self.asian_gk = self._load_pool("asian_gk")
        self.western_field = self._load_pool("western_field")
        self.western_gk = self._load_pool("western_gk")

        # Fallback for older workspaces before the v2 avatar split is installed.
        self.asian = self._load_pool("asian")
        self.western = self._load_pool("western")
        if not (self.asian_field or self.asian) or not (self.western_field or self.western):
            raise RuntimeError("Avatar pool empty! Check frontend/public/avatars/")

    def _load_pool(self, dirname: str) -> list[str]:
        directory = self.base_path / dirname
        return sorted([f"avatars/{dirname}/{f.name}" for f in directory.glob("*.png")])

    def pick(self, race: str, position: PlayerPosition | None = None) -> str:
        is_gk = position == PlayerPosition.GK
        if race == "asian":
            pool = self.asian_gk if is_gk and self.asian_gk else self.asian_field
            if not pool:
                pool = self.asian
        else:
            pool = self.western_gk if is_gk and self.western_gk else self.western_field
            if not pool:
                pool = self.western
        return random.choice(pool)


# ==================== 属性生成器 ====================

class AttributeGenerator:
    @staticmethod
    def calculate_ovr(position: PlayerPosition, attrs: dict) -> int:
        weights = OVR_WEIGHTS[position]
        weight_total = sum(weight for weight in weights.values() if weight > 0)
        if weight_total <= 0:
            return 0
        total = sum((attrs.get(k, 10) / 20.0) * w for k, w in weights.items())
        return int(round((total / weight_total) * 100))

    @staticmethod
    def _pick_attribute_profile(style: str, base_ovr: int) -> str:
        distribution = list(ATTRIBUTE_PROFILE_DISTRIBUTION.get(style, ATTRIBUTE_PROFILE_DISTRIBUTION["标准型"]))
        if base_ovr < 72:
            distribution = [
                (name, weight * 0.35 if name == "all_rounder" else weight)
                for name, weight in distribution
            ]
        elif base_ovr >= 82:
            distribution = [
                (name, weight * 1.8 if name == "all_rounder" else weight)
                for name, weight in distribution
            ]
        return _weighted_choice(distribution)

    @staticmethod
    def _weighted_sample_attrs(candidates: list[str], weights: dict[str, float], count: int) -> set[str]:
        picked: set[str] = set()
        pool = list(dict.fromkeys(candidates))
        while pool and len(picked) < count:
            choice = random.choices(pool, weights=[weights.get(attr, 1.0) for attr in pool], k=1)[0]
            picked.add(choice)
            pool.remove(choice)
        return picked

    @staticmethod
    def _calibrate_ovr(
        position: PlayerPosition,
        attrs: dict,
        target_ovr: int,
        strengths: set[str],
        weaknesses: set[str],
        core_floor: int = 1,
    ) -> dict:
        weights = OVR_WEIGHTS[position]
        relevant_attrs = [attr for attr, weight in weights.items() if weight > 0]

        for _ in range(90):
            current_ovr = AttributeGenerator.calculate_ovr(position, attrs)
            diff = target_ovr - current_ovr
            if abs(diff) <= 1:
                break

            if diff > 0:
                candidates = [attr for attr in relevant_attrs if attrs.get(attr, 10) < 20]
                if not candidates:
                    break
                step_weights = {
                    attr: (
                        weights[attr]
                        * (1.8 if attr in strengths else 0.55 if attr in weaknesses else 1.0)
                        * HIGH_ATTRIBUTE_STEP_WEIGHTS.get(attrs.get(attr, 10) + 1, 1.0)
                    )
                    for attr in candidates
                }
                attr = random.choices(candidates, weights=[step_weights[a] for a in candidates], k=1)[0]
                attrs[attr] += 1
            else:
                candidates = [
                    attr for attr in relevant_attrs
                    if attrs.get(attr, 10) > max(1, core_floor if attr in POSITION_NON_CORE_ATTRS[position] else 1)
                ]
                if not candidates:
                    break
                step_weights = {
                    attr: weights[attr] * (1.8 if attr in weaknesses else 0.45 if attr in strengths else 1.0)
                    for attr in candidates
                }
                attr = random.choices(candidates, weights=[step_weights[a] for a in candidates], k=1)[0]
                attrs[attr] -= 1
        return attrs
    
    @staticmethod
    def generate(position: PlayerPosition, archetype: str, style: str,
                 age: int, potential_max: int, team_ovr: int,
                 target_ovr: int | None = None) -> dict:
        """
        生成23项属性,返回属性字典 + 计算后的OVR
        """
        # 1. 确定基准OVR (由年龄、潜力、球队水平共同决定)
        age_factor = 1.0 if 21 <= age <= 28 else (0.85 if age <= 20 else 0.90 if age <= 31 else 0.75)
        potential_factor = potential_max / 100.0
        # 基准在 team_ovr ± 5 浮动, 受潜力修正
        if target_ovr is None:
            base_ovr = team_ovr + random.randint(-5, 5)
            base_ovr = int(base_ovr * age_factor * (0.8 + 0.4 * potential_factor))
        else:
            base_ovr = target_ovr + random.randint(-1, 1)
        base_ovr = _clamp(base_ovr, 20, 99)
        
        # 2. 核心属性组 (该位置看重的属性)
        core_attrs = POSITION_NON_CORE_ATTRS[position]
        
        # 3. Archetype 加成
        bias = ARCHETYPE_BIAS.get(archetype, {})
        weakness_bias = ARCHETYPE_WEAKNESS_BIAS.get(archetype, {})
        
        # 4. 选择属性画像：大多数球员会有明确强项和短板，少数才是全能型。
        profile = AttributeGenerator._pick_attribute_profile(style, base_ovr)
        profile_config = ATTRIBUTE_PROFILE_CONFIG[profile]
        strength_count = random.randint(*profile_config["strengths"])
        weakness_count = random.randint(*profile_config["weaknesses"])

        core_candidates = [attr for attr in PLAYER_ATTRIBUTES if attr in core_attrs]
        strength_weights = {attr: bias.get(attr, 1.0) for attr in core_candidates}
        strengths = AttributeGenerator._weighted_sample_attrs(core_candidates, strength_weights, strength_count)

        relevant_weights = OVR_WEIGHTS[position]
        weakness_candidates = [
            attr for attr in core_candidates
            if attr not in strengths and relevant_weights.get(attr, 0) > 0
        ]
        if len(weakness_candidates) < weakness_count:
            weakness_candidates.extend([attr for attr in core_candidates if attr not in strengths])
        weakness_weights = {
            attr: weakness_bias.get(attr, 1.0) * (1.0 + relevant_weights.get(attr, 0) / 20.0)
            for attr in weakness_candidates
        }
        weaknesses = AttributeGenerator._weighted_sample_attrs(weakness_candidates, weakness_weights, weakness_count)

        variance = profile_config["variance"]
        if style == "天才型":
            variance *= 1.15
        elif style == "平均型":
            variance *= 0.75
        
        # 5. 逐项生成
        attrs = {}
        for attr in PLAYER_ATTRIBUTES:
            is_core = attr in core_attrs
            
            # 基础值: OVR 映射到 1-20 区间
            base_attr = (base_ovr / 100.0) * 18 + 1  # 映射到 1-19
            
            # 核心属性略高，非核心属性明显拉低，避免所有位置都全能。
            if is_core:
                base_attr *= 1.02
            else:
                base_attr *= 0.68
            
            # Archetype 只提供倾向，真正的强弱项由画像决定。
            bias_factor = bias.get(attr, 1.0)
            base_attr *= 1.0 + (bias_factor - 1.0) * 0.55

            if attr in strengths:
                base_attr += random.uniform(*profile_config["strong_bonus"])
            elif attr in weaknesses:
                base_attr -= random.uniform(*profile_config["weak_penalty"])
            elif is_core and profile in {"specialist", "volatile", "flawed_starter"}:
                base_attr += random.uniform(-0.9, 0.6)
            
            # 随机方差
            noise = random.gauss(0, variance)
            val = base_attr + noise
            
            attrs[attr] = _shape_high_attribute_value(
                val,
                is_strength=attr in strengths,
                is_elite=base_ovr >= 90,
            )
        
        # 5b. 生成 FK 和 PK (基于相关属性)
        attrs["fk"] = _shape_high_attribute_value(
            attrs.get("cro", 10) * 0.4 + attrs.get("pas", 10) * 0.3 +
            attrs.get("vis", 10) * 0.2 + attrs.get("fin", 10) * 0.1 +
            random.gauss(0, variance),
            is_strength="fk" in strengths,
            is_elite=base_ovr >= 90,
        )
        attrs["pk"] = _shape_high_attribute_value(
            attrs.get("sho", 10) * 0.4 + attrs.get("fin", 10) * 0.3 +
            attrs.get("con", 10) * 0.2 + attrs.get("str_", 10) * 0.1 +
            random.gauss(0, variance),
            is_strength="pk" in strengths,
            is_elite=base_ovr >= 90,
        )

        # 6. 校准实际OVR，尽量保持球队强度分布，同时保留强弱项轮廓。
        if base_ovr >= 85:
            core_floor = 12
        elif base_ovr >= 75:
            core_floor = 11
        elif base_ovr >= 65:
            core_floor = 10
        elif base_ovr >= 55:
            core_floor = 9
        else:
            core_floor = 8
        for attr in core_candidates:
            if relevant_weights.get(attr, 0) > 0:
                attrs[attr] = max(attrs[attr], core_floor)

        attrs = AttributeGenerator._calibrate_ovr(position, attrs, base_ovr, strengths, weaknesses, core_floor)
        actual_ovr = AttributeGenerator.calculate_ovr(position, attrs)
        attrs["ovr"] = actual_ovr
        return attrs


# ==================== 技能生成器 ====================

class SkillGenerator:
    @staticmethod
    def generate(position: PlayerPosition, ovr: int) -> list:
        skills = []
        
        # 通用池 + 位置池
        pool = SKILL_POOL["通用"] + SKILL_POOL.get(position.value, [])
        
        # 70% 概率获得1个技能, 30% 概率0个
        if random.random() > 0.3:
            candidates = []
            for name, trigger, effect in pool:
                if name == "玻璃体质":
                    continue
                if name in {"禁区幽灵", "致命直塞", "组织核心", "铁壁", "神反应", "点球克星"} and ovr < 65:
                    continue
                candidates.append((name, trigger, effect, 1))
            
            if candidates:
                weights = [c[3] for c in candidates]
                choice = random.choices(candidates, weights=weights, k=1)[0]
                quality = SkillGenerator._quality_for_ovr(ovr)
                skills.append({
                    "skill_id": choice[0],
                    "rarity": quality,
                    "quality": quality,
                    "color": SKILL_QUALITY_COLORS[quality],
                    "trigger": choice[1],
                    "effect": choice[2],
                })
        
        # 15% 概率附加负面技能 (与主技能独立)
        if random.random() < 0.15:
            skills.append({
                "skill_id": "玻璃体质",
                "rarity": "普通",
                "quality": "普通",
                "color": SKILL_QUALITY_COLORS["普通"],
                "type": "negative",
                "trigger": "受伤触发时",
                "effect": "受伤概率提升，负面技能",
            })
        
        return skills

    @staticmethod
    def _quality_for_ovr(ovr: int) -> str:
        weights = list(SKILL_QUALITY_WEIGHTS)
        if ovr >= 80:
            weights = [("普通", 40), ("优秀", 35), ("精英", 18), ("名人堂", 7)]
        elif ovr >= 70:
            weights = [("普通", 50), ("优秀", 32), ("精英", 15), ("名人堂", 3)]
        return random.choices([q for q, _ in weights], weights=[w for _, w in weights], k=1)[0]


def potential_letter_from_value(potential_max: int) -> PotentialLetter:
    if potential_max >= 95:
        return PotentialLetter.S
    if potential_max >= 85:
        return PotentialLetter.A
    if potential_max >= 75:
        return PotentialLetter.B
    if potential_max >= 65:
        return PotentialLetter.C
    return PotentialLetter.D


# ==================== 主生成器 ====================

class PlayerGenerator:
    def __init__(self, name_data_path: str = None, avatar_base_path: str = None):
        self.name_gen = NameGenerator(name_data_path)
        self.avatar_pool = AvatarPool(avatar_base_path)
    
    def _generate_age_and_potential(self, team_level: int = 4) -> tuple:
        """返回 (birth_offset, potential_letter, potential_max, actual_age)"""
        # 年龄
        age_item = random.choices(AGE_DISTRIBUTION, weights=[w for _, _, w in AGE_DISTRIBUTION], k=1)[0]
        age_min, age_max, _ = age_item
        actual_age = random.randint(age_min, age_max)
        birth_offset = -actual_age  # 负数
        
        # 潜力
        pot_item = random.choices(POTENTIAL_DISTRIBUTION, weights=[w for _, _, _, w in POTENTIAL_DISTRIBUTION], k=1)[0]
        letter, pmin, pmax, _ = pot_item
        potential_max = random.randint(pmin, pmax)
        
        return birth_offset, letter, potential_max, actual_age
    
    def _generate_height_weight(self, position: PlayerPosition) -> tuple:
        if position == PlayerPosition.GK:
            h = random.randint(182, 198)
        elif position == PlayerPosition.DF:
            h = random.randint(178, 195)
        elif position == PlayerPosition.FW:
            h = random.randint(170, 190)
        else:  # MF
            h = random.randint(168, 188)
        
        # 体重与身高正相关
        base_w = h - 115
        w = random.randint(base_w - 5, base_w + 8)
        w = max(60, min(95, w))
        return h, w
    
    def generate_player(self, team, position: PlayerPosition = None,
                       team_ovr: int = 50, team_level: int = 4,
                       target_ovr: int | None = None) -> Player:
        """生成单个球员"""
        # Race
        race_str = random.choice(["asian", "western"])
        race = PlayerRace.ASIAN if race_str == "asian" else PlayerRace.WESTERN
        
        # Name
        name, region = self.name_gen.generate(race_str)
        
        # Position (如果未指定)
        if position is None:
            position = random.choice(list(PlayerPosition))

        # Avatar
        avatar_url = self.avatar_pool.pick(race_str, position)
        
        # Archetype
        archetype = _weighted_choice(ARCHETYPE_CONFIG[position])
        
        # Style
        style = _weighted_choice(STYLE_DISTRIBUTION)
        
        # Age & Potential
        birth_offset, _potential_letter, potential_max, actual_age = self._generate_age_and_potential(team_level)
        
        # Height & Weight
        height, weight = self._generate_height_weight(position)
        
        # Foot
        foot_roll = random.random()
        if foot_roll < 0.70:
            foot = PlayerFoot.RIGHT
        elif foot_roll < 0.95:
            foot = PlayerFoot.LEFT
        else:
            foot = PlayerFoot.BOTH
        
        # Attributes
        attr_result = AttributeGenerator.generate(
            position, archetype, style, actual_age, potential_max, team_ovr, target_ovr=target_ovr
        )
        ovr = attr_result.pop("ovr", 50)  # 不持久化, 由模型 hybrid_property 计算
        while ovr >= 100 and any(value > 1 for value in attr_result.values()):
            for attr, value in attr_result.items():
                attr_result[attr] = max(1, value - 1)
            ovr = AttributeGenerator.calculate_ovr(position, attr_result)
        if potential_max <= ovr:
            growth_margin = random.randint(1, 8) if actual_age <= 24 else random.randint(0, 3)
            potential_max = min(100, ovr + max(growth_margin, 1))
        
        # Skills
        skills = SkillGenerator.generate(position, ovr)
        
        # Personality
        personality = random.choice(PERSONALITIES)
        
        # Contract
        contract_end = random.randint(1, 4)  # 1-4个赛季后到期
        wage = estimate_initial_wage(ovr, potential_max, actual_age)
        release_clause = Decimal(str(wage * 20))
        
        # Squad role by age/OVR
        if actual_age <= 20:
            role = SquadRole.YOUNGSTER
        elif ovr >= team_ovr + 5:
            role = SquadRole.KEY_PLAYER
        elif ovr >= team_ovr:
            role = SquadRole.FIRST_TEAM
        elif ovr >= team_ovr - 5:
            role = SquadRole.ROTATION
        else:
            role = SquadRole.BACKUP
        
        # 生成成长曲线和属性上限
        growth_profile = TrainingGrowthService.generate_player_growth_profile(
            potential_max, position, actual_age
        )
        
        preferred_number = generate_preferred_number(position)
        
        return Player(
            name=name,
            race=race,
            avatar_url=avatar_url,
            position=position,
            preferred_foot=foot,
            preferred_number=preferred_number,
            height=height,
            weight=weight,
            birth_offset=birth_offset,
            # 23 attrs
            sho=attr_result["sho"], pas=attr_result["pas"], dri=attr_result["dri"],
            spd=attr_result["spd"], str_=attr_result["str_"], sta=attr_result["sta"],
            acc=attr_result["acc"], hea=attr_result["hea"], bal=attr_result["bal"],
            defe=attr_result["defe"], tkl=attr_result["tkl"], vis=attr_result["vis"],
            cro=attr_result["cro"], con=attr_result["con"], fin=attr_result["fin"],
            com=attr_result["com"], sav=attr_result["sav"], ref=attr_result["ref"],
            pos=attr_result["pos"], rus=attr_result["rus"], dec=attr_result["dec"],
            fk=attr_result["fk"], pk=attr_result["pk"],
            potential_max=potential_max,
            # skills & personality
            skills=skills,
            personality=personality,
            # status
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fitness=100,
            fatigue=0,
            # growth
            attribute_caps=growth_profile["attribute_caps"],
            attribute_progress={},
            growth_peak_age=growth_profile["growth_peak_age"],
            growth_curve_type=growth_profile["growth_curve_type"],
            growth_speed=growth_profile["growth_speed"],
            growth_stability=growth_profile["growth_stability"],
            late_bloom_factor=growth_profile["late_bloom_factor"],
            # contract
            contract_type=ContractType.NORMAL,
            contract_end_season=contract_end,
            wage=wage,
            release_clause=release_clause,
            squad_role=role,
            team_id=team.id,
        )
    
    def generate_auto_fill_player(self, team, season_number: int = 1) -> Player:
        """生成自动补员兜底球员（设计文档 7.2）
        
        - 年龄 20-28
        - OVR 35-45
        - 潜力 C/D
        - 合同 NORMAL，1 年
        - origin_type = auto_fill
        """
        race_str = random.choice(["asian", "western"])
        race = PlayerRace.ASIAN if race_str == "asian" else PlayerRace.WESTERN
        name, region = self.name_gen.generate(race_str)
        
        position = random.choice(list(PlayerPosition))
        avatar_url = self.avatar_pool.pick(race_str, position)
        archetype = _weighted_choice(ARCHETYPE_CONFIG[position])
        style = _weighted_choice(STYLE_DISTRIBUTION)
        
        # 年龄 20-28
        actual_age = random.randint(20, 28)
        birth_offset = -actual_age
        
        # 潜力 C/D
        potential_max = random.randint(50, 74)
        if potential_max >= 65:
            potential_letter = PotentialLetter.C
        else:
            potential_letter = PotentialLetter.D
        
        # 初始 OVR 35-45
        base_ovr = random.randint(35, 45)
        
        height, weight = self._generate_height_weight(position)
        
        foot_roll = random.random()
        if foot_roll < 0.70:
            foot = PlayerFoot.RIGHT
        elif foot_roll < 0.95:
            foot = PlayerFoot.LEFT
        else:
            foot = PlayerFoot.BOTH
        
        # 生成属性
        attr_result = AttributeGenerator.generate(
            position, archetype, style, actual_age, potential_max, base_ovr
        )
        attr_result["ovr"] = base_ovr  # 强制设定 OVR
        
        # 技能
        skills = SkillGenerator.generate(position, base_ovr)
        
        # 性格
        personality = random.choice(PERSONALITIES)
        
        wage = estimate_initial_wage(base_ovr, potential_max, actual_age)
        
        preferred_number = generate_preferred_number(position)
        
        return Player(
            name=name,
            race=race,
            avatar_url=avatar_url,
            position=position,
            preferred_foot=foot,
            preferred_number=preferred_number,
            height=height,
            weight=weight,
            birth_offset=birth_offset,
            sho=attr_result["sho"], pas=attr_result["pas"], dri=attr_result["dri"],
            spd=attr_result["spd"], str_=attr_result["str_"], sta=attr_result["sta"],
            acc=attr_result["acc"], hea=attr_result["hea"], bal=attr_result["bal"],
            defe=attr_result["defe"], tkl=attr_result["tkl"], vis=attr_result["vis"],
            cro=attr_result["cro"], con=attr_result["con"], fin=attr_result["fin"],
            com=attr_result["com"], sav=attr_result["sav"], ref=attr_result["ref"],
            pos=attr_result["pos"], rus=attr_result["rus"], dec=attr_result["dec"],
            fk=attr_result["fk"], pk=attr_result["pk"],
            potential_max=potential_max,
            skills=skills,
            personality=personality,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fitness=100,
            contract_type=ContractType.NORMAL,
            contract_end_season=season_number,  # 1 年合同，当前赛季末到期
            wage=wage,
            squad_role=SquadRole.BACKUP,
            origin_type=OriginType.AUTO_FILL,
        )
    
    def generate_youth_player(
        self,
        team,
        season_number: int = 1,
        investment_level: str = "medium",
        league_level: int = 3,
    ) -> Player:
        """生成青训球员（设计文档 8.2-8.3）
        
        - 年龄 15-18
        - 投入等级影响潜力、OVR、年龄倾向
        - 联赛级别修正
        - origin_type = academy, team_id = null
        """
        # 投入等级基础配置
        investment_config = {
            "low": {
                "age_weights": [(17, 0.35), (18, 0.35), (16, 0.20), (15, 0.10)],
                "potential_weights": [
                    (PotentialLetter.S, 0.002), (PotentialLetter.A, 0.045),
                    (PotentialLetter.B, 0.22), (PotentialLetter.C, 0.41), (PotentialLetter.D, 0.323)
                ],
                "ovr_range": (30, 44),
            },
            "medium": {
                "age_weights": [(15, 0.20), (16, 0.25), (17, 0.30), (18, 0.25)],
                "potential_weights": [
                    (PotentialLetter.S, 0.007), (PotentialLetter.A, 0.09),
                    (PotentialLetter.B, 0.34), (PotentialLetter.C, 0.40), (PotentialLetter.D, 0.163)
                ],
                "ovr_range": (32, 47),
            },
            "high": {
                "age_weights": [(15, 0.35), (16, 0.30), (17, 0.25), (18, 0.10)],
                "potential_weights": [
                    (PotentialLetter.S, 0.02), (PotentialLetter.A, 0.17),
                    (PotentialLetter.B, 0.41), (PotentialLetter.C, 0.31), (PotentialLetter.D, 0.09)
                ],
                "ovr_range": (34, 50),
            },
        }
        config = investment_config.get(investment_level, investment_config["medium"])
        
        # 联赛级别修正
        league_modifier = {
            1: {"potential_bonus": 0.20, "ovr_bonus": (3, 6)},
            2: {"potential_bonus": 0.10, "ovr_bonus": (1, 3)},
            3: {"potential_bonus": 0.00, "ovr_bonus": (0, 0)},
            4: {"potential_bonus": -0.10, "ovr_bonus": (-3, -1)},
        }.get(league_level, {"potential_bonus": 0.00, "ovr_bonus": (0, 0)})
        
        # 年龄
        age_weights = config["age_weights"]
        actual_age = _weighted_choice([(a, w) for a, w in age_weights])
        birth_offset = -actual_age
        
        # 年龄修正
        age_ovr_modifier = {15: (-10, -6), 16: (-6, -3), 17: (-3, -1), 18: (1, 2)}.get(actual_age, (0, 0))
        
        # 潜力（应用联赛修正）
        potential_weights = list(config["potential_weights"])
        bonus = league_modifier["potential_bonus"]
        if bonus != 0:
            # 提升高潜概率，降低低潜概率
            adjusted = []
            for letter, weight in potential_weights:
                if letter in (PotentialLetter.S, PotentialLetter.A, PotentialLetter.B):
                    new_w = weight * (1 + bonus)
                else:
                    new_w = weight * (1 - bonus)
                adjusted.append((letter, new_w))
            potential_weights = adjusted
        
        potential_letter = _weighted_choice(potential_weights)
        # potential_max 映射
        potential_ranges = {
            PotentialLetter.S: (95, 100), PotentialLetter.A: (85, 94),
            PotentialLetter.B: (75, 84), PotentialLetter.C: (65, 74), PotentialLetter.D: (50, 64)
        }
        p_min, p_max = potential_ranges[potential_letter]
        potential_max = random.randint(p_min, p_max)
        
        # OVR
        ovr_min, ovr_max = config["ovr_range"]
        ovr_bonus_min, ovr_bonus_max = league_modifier["ovr_bonus"]
        age_ovr_min, age_ovr_max = age_ovr_modifier
        base_ovr = random.randint(ovr_min, ovr_max)
        base_ovr += random.randint(ovr_bonus_min, ovr_bonus_max)
        base_ovr += random.randint(age_ovr_min, age_ovr_max)
        base_ovr = max(20, min(62, base_ovr))
        
        # Race / Name / Avatar
        race_str = random.choice(["asian", "western"])
        race = PlayerRace.ASIAN if race_str == "asian" else PlayerRace.WESTERN
        name, region = self.name_gen.generate(race_str)
        
        # Position
        position = random.choice(list(PlayerPosition))
        avatar_url = self.avatar_pool.pick(race_str, position)
        archetype = _weighted_choice(ARCHETYPE_CONFIG[position])
        style = _weighted_choice(STYLE_DISTRIBUTION)
        
        # Height / Weight
        height, weight = self._generate_height_weight(position)
        
        # Foot
        foot_roll = random.random()
        if foot_roll < 0.70:
            foot = PlayerFoot.RIGHT
        elif foot_roll < 0.95:
            foot = PlayerFoot.LEFT
        else:
            foot = PlayerFoot.BOTH
        
        # Attributes
        attr_result = AttributeGenerator.generate(
            position, archetype, style, actual_age, potential_max, base_ovr
        )
        attr_result["ovr"] = base_ovr
        
        # Skills
        skills = SkillGenerator.generate(position, base_ovr)
        
        # Personality
        personality = random.choice(PERSONALITIES)
        
        # 生成成长曲线和属性上限
        growth_profile = TrainingGrowthService.generate_player_growth_profile(
            potential_max, position, actual_age
        )
        
        preferred_number = generate_preferred_number(position)
        
        return Player(
            name=name,
            race=race,
            avatar_url=avatar_url,
            position=position,
            preferred_foot=foot,
            preferred_number=preferred_number,
            height=height,
            weight=weight,
            birth_offset=birth_offset,
            sho=attr_result["sho"], pas=attr_result["pas"], dri=attr_result["dri"],
            spd=attr_result["spd"], str_=attr_result["str_"], sta=attr_result["sta"],
            acc=attr_result["acc"], hea=attr_result["hea"], bal=attr_result["bal"],
            defe=attr_result["defe"], tkl=attr_result["tkl"], vis=attr_result["vis"],
            cro=attr_result["cro"], con=attr_result["con"], fin=attr_result["fin"],
            com=attr_result["com"], sav=attr_result["sav"], ref=attr_result["ref"],
            pos=attr_result["pos"], rus=attr_result["rus"], dec=attr_result["dec"],
            fk=attr_result["fk"], pk=attr_result["pk"],
            potential_max=potential_max,
            skills=skills,
            personality=personality,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fitness=100,
            fatigue=0,
            attribute_caps=growth_profile["attribute_caps"],
            attribute_progress={},
            growth_peak_age=growth_profile["growth_peak_age"],
            growth_curve_type=growth_profile["growth_curve_type"],
            growth_speed=growth_profile["growth_speed"],
            growth_stability=growth_profile["growth_stability"],
            late_bloom_factor=growth_profile["late_bloom_factor"],
            contract_type=ContractType.FREE,
            contract_end_season=None,
            wage=Decimal("0"),
            squad_role=SquadRole.YOUNGSTER,
            team_id=None,
            origin_type=OriginType.ACADEMY,
            academy_team_id=team.id,
        )
    
    def _generate_initial_squad_targets(self, league_level: int, size: int) -> list[int]:
        tiers = INITIAL_SQUAD_OVR_TIERS.get(league_level, INITIAL_SQUAD_OVR_TIERS[3])
        targets: list[int] = []
        for low, high, count in tiers:
            targets.extend(random.randint(low, high) for _ in range(count))
        while len(targets) < size:
            low, high, _ = tiers[-1]
            targets.append(random.randint(low, high))
        if league_level == 1 and targets and random.random() < INITIAL_LEVEL_ONE_ELITE_PROBABILITY:
            low, high = INITIAL_LEVEL_ONE_ELITE_OVR_RANGE
            strongest_idx = max(range(len(targets)), key=lambda idx: targets[idx])
            targets[strongest_idx] = random.randint(low, high)
        random.shuffle(targets)
        return targets[:size]

    def generate_squad(self, team, size: int = 15, league_level: int | None = None) -> list:
        """为球队生成完整阵容"""
        players = []
        team_ovr = getattr(team, 'overall_rating', 50)
        team_level = league_level or 4
        targets = self._generate_initial_squad_targets(team_level, size)
        target_idx = 0
        
        for pos, count in SQUAD_COMPOSITION:
            for _ in range(count):
                target_ovr = targets[target_idx] if target_idx < len(targets) else None
                target_idx += 1
                p = self.generate_player(
                    team,
                    position=pos,
                    team_ovr=team_ovr,
                    team_level=team_level,
                    target_ovr=target_ovr,
                )
                players.append(p)
        
        return players
