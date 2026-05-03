"""
Player Generator Service - 球员生成器

职责:
- 按种族/region生成姓名
- 按位置原型(Archetype)+风格(Style)生成19项属性
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
    PotentialLetter, PlayerPersonality, ContractType, MatchForm, SquadRole
)


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
    ("标准型", 0.70),
    ("天才型", 0.15),
    ("平均型", 0.15),
]

# 潜力分布 -> (letter, min_potential, max_potential, weight)
POTENTIAL_DISTRIBUTION = [
    (PotentialLetter.S, 80, 100, 0.02),
    (PotentialLetter.A, 60, 79, 0.08),
    (PotentialLetter.B, 40, 59, 0.25),
    (PotentialLetter.C, 20, 39, 0.35),
    (PotentialLetter.D, 1, 19, 0.30),
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
        "pas": 5, "com": 8, "sav": 30, "ref": 22, "pos": 12, "rus": 8, "dec": 12,
        "sho": 0, "dri": 0, "spd": 0, "str_": 0, "sta": 0, "defe": 0, "hea": 0,
        "vis": 0, "tkl": 0, "acc": 0, "cro": 0, "con": 0, "fin": 0, "bal": 0,
        "fk": 0, "pk": 0,
    },
}

# 招牌技能池 (按位置)
SKILL_POOL = {
    "通用": [
        ("铁人", "稀有", "全场持续", "体能消耗-15%,受伤概率-20%"),
        ("大赛型选手", "稀有", "杯赛/关键战", "全属性+5%(杯赛/淘汰赛生效)"),
        ("领导力", "稀有", "全场持续", "队友全属性+2%(仅1人生效,队长优先)"),
        ("青训之星", "普通", "全场持续", "年龄≤21岁时,全属性+3%"),
        ("万金油", "普通", "被安排非首选位置时", "在非首选位置属性惩罚减半"),
        ("玻璃体质", "负面", "受伤触发时", "受伤概率+30%,恢复时间+50%"),
        ("大场面先生", "传奇", "比赛最后10分钟", "全属性+8%(80分钟后生效)"),
        ("快速恢复", "稀有", "体能衰减时", "每5分钟额外恢复1%体能"),
    ],
    "FW": [
        ("禁区幽灵", "传奇", "禁区内射门时", "禁区射门命中率+10%"),
        ("抢点专家", "稀有", "传中/角球争顶时", "头球争顶成功率+8%"),
        ("远射重炮", "稀有", "禁区外射门时", "远射命中率和力量+7%"),
        ("速度之魔", "传奇", "冲刺跑时", "速度突破成功率+10%,反击触发率+5%"),
        ("盘带大师", "稀有", "1v1突破时", "盘带过人成功率+8%"),
        ("致命直塞", "传奇", "直塞球时", "直塞成功率+10%,形成单刀概率+5%"),
        ("内切杀手", "稀有", "从边路内切射门时", "内切射门命中率+8%"),
        ("空中霸主", "普通", "争顶时", "头球属性临时+5%"),
        ("点球专家", "稀有", "主罚点球时", "点球命中率+10%"),
        ("补射猎手", "普通", "门将脱手后", "补射抢到概率+15%"),
    ],
    "MF": [
        ("手术刀传球", "传奇", "短传/直塞时", "传球成功率+10%,关键传球概率+5%"),
        ("节拍器", "稀有", "持球组织时", "球队该区域控制度+5%"),
        ("全能中场", "稀有", "参与进攻/防守事件时", "攻防转换效率+8%"),
        ("长传调度", "普通", "长传转移时", "长传成功率+7%"),
        ("拦截专家", "稀有", "预判拦截时", "拦截成功率+8%"),
        ("组织核心", "传奇", "全队进攻事件时", "进攻事件成功率+5%(光环效果)"),
        ("定位球大师", "稀有", "任意球/角球时", "定位球直接进球率+8%"),
        ("绞肉机", "普通", "逼抢/铲球时", "逼抢成功率+5%,犯规率-10%"),
    ],
    "DF": [
        ("铁壁", "传奇", "1v1防守时", "防守成功率+10%,被过概率-15%"),
        ("铲球专家", "稀有", "铲球时", "铲球成功率+8%,铲空犯规率-10%"),
        ("预判大师", "稀有", "对方传球时", "拦截/断球成功率+8%"),
        ("盯人专家", "普通", "人盯人时", "被盯防对象接球成功率-5%"),
        ("空中堡垒", "稀有", "争顶/解围时", "头球争顶成功率+8%,解围距离+10%"),
        ("边路屏障", "普通", "边路防守时", "边路防守成功率+7%"),
        ("清道夫", "稀有", "补位防守时", "补位成功率+8%,区域控制度+3%"),
        ("造越位专家", "普通", "防线联动时", "造越位成功率+10%"),
    ],
    "GK": [
        ("神反应", "传奇", "近距离射门扑救时", "近距离扑救成功率+12%"),
        ("门线技术", "稀有", "门线救险时", "门线解围成功率+10%"),
        ("出击果断", "普通", "单刀球出击时", "出击成功率+7%,失误率-5%"),
        ("手抛球反击", "稀有", "扑救后手抛球时", "手抛球精准度+10%,反击启动率+5%"),
        ("点球克星", "传奇", "扑点球时", "点球扑救率+15%"),
    ],
}

PERSONALITIES = list(PlayerPersonality)

# Squad 配比: 位置 -> 人数
SQUAD_COMPOSITION = [
    (PlayerPosition.GK, 2),
    (PlayerPosition.DF, 5),
    (PlayerPosition.MF, 5),
    (PlayerPosition.FW, 3),
]


# ==================== 工具函数 ====================

def _weighted_choice(items: list) -> any:
    """按权重随机选择"""
    weights = [w for _, w in items]
    choices = [c for c, _ in items]
    return random.choices(choices, weights=weights, k=1)[0]


def _clamp(val: int, lo: int = 1, hi: int = 20) -> int:
    return max(lo, min(hi, int(round(val))))


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
        self.asian = sorted([f"avatars/asian/{f.name}" for f in (self.base_path / "asian").glob("*.png")])
        self.western = sorted([f"avatars/western/{f.name}" for f in (self.base_path / "western").glob("*.png")])
        if not self.asian or not self.western:
            raise RuntimeError("Avatar pool empty! Check frontend/public/avatars/")
    
    def pick(self, race: str) -> str:
        pool = self.asian if race == "asian" else self.western
        return random.choice(pool)


# ==================== 属性生成器 ====================

class AttributeGenerator:
    @staticmethod
    def calculate_ovr(position: PlayerPosition, attrs: dict) -> int:
        weights = OVR_WEIGHTS[position]
        total = sum((attrs.get(k, 10) / 20.0) * w for k, w in weights.items())
        return int(round(total))
    
    @staticmethod
    def generate(position: PlayerPosition, archetype: str, style: str,
                 age: int, potential_max: int, team_ovr: int) -> dict:
        """
        生成19项属性,返回属性字典 + 计算后的OVR
        """
        # 1. 确定基准OVR (由年龄、潜力、球队水平共同决定)
        age_factor = 1.0 if 21 <= age <= 28 else (0.85 if age <= 20 else 0.90 if age <= 31 else 0.75)
        potential_factor = potential_max / 100.0
        # 基准在 team_ovr ± 5 浮动, 受潜力修正
        base_ovr = team_ovr + random.randint(-5, 5)
        base_ovr = int(base_ovr * age_factor * (0.8 + 0.4 * potential_factor))
        base_ovr = _clamp(base_ovr, 20, 95)
        
        # 2. 核心属性组 (该位置看重的属性)
        core_attrs = POSITION_NON_CORE_ATTRS[position]
        
        # 3. Archetype 加成
        bias = ARCHETYPE_BIAS.get(archetype, {})
        
        # 4. Style 修正
        if style == "天才型":
            style_core_boost = 1.15
            style_non_core_penalty = 0.85
            variance = 1.5
        elif style == "平均型":
            style_core_boost = 1.0
            style_non_core_penalty = 1.0
            variance = 0.5
        else:  # 标准型
            style_core_boost = 1.0
            style_non_core_penalty = 1.0
            variance = 1.0
        
        # 5. 逐项生成
        all_attrs = ["sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
                     "defe", "tkl", "vis", "cro", "con", "fin", "com", "sav", "ref", "pos", "rus", "dec", "fk", "pk"]
        
        attrs = {}
        for attr in all_attrs:
            is_core = attr in core_attrs
            
            # 基础值: OVR 映射到 1-20 区间
            base_attr = (base_ovr / 100.0) * 18 + 1  # 映射到 1-19
            
            # 核心属性略高
            if is_core:
                base_attr *= 1.05
            else:
                base_attr *= 0.85
            
            # Archetype 加成
            bias_factor = bias.get(attr, 1.0)
            base_attr *= bias_factor
            
            # Style 修正
            if is_core:
                base_attr *= style_core_boost
            else:
                base_attr *= style_non_core_penalty
            
            # 随机方差
            noise = random.gauss(0, variance * 1.5)
            val = base_attr + noise
            
            attrs[attr] = _clamp(val)
        
        # 5b. 生成 FK 和 PK (基于相关属性)
        attrs["fk"] = _clamp(
            attrs.get("cro", 10) * 0.4 + attrs.get("pas", 10) * 0.3 +
            attrs.get("vis", 10) * 0.2 + attrs.get("fin", 10) * 0.1 +
            random.gauss(0, variance)
        )
        attrs["pk"] = _clamp(
            attrs.get("sho", 10) * 0.4 + attrs.get("fin", 10) * 0.3 +
            attrs.get("con", 10) * 0.2 + attrs.get("str_", 10) * 0.1 +
            random.gauss(0, variance)
        )

        # 6. 计算实际OVR (可能因分布与base_ovr不同)
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
            # 按稀有度筛选
            candidates = []
            for name, rarity, trigger, effect in pool:
                if rarity == "传奇" and ovr < 75:
                    continue
                weight = {"普通": 6, "稀有": 3, "传奇": 1, "负面": 2}.get(rarity, 1)
                candidates.append((name, rarity, trigger, effect, weight))
            
            if candidates:
                weights = [c[4] for c in candidates]
                choice = random.choices(candidates, weights=weights, k=1)[0]
                skills.append({
                    "skill_id": choice[0],
                    "rarity": choice[1],
                    "trigger": choice[2],
                    "effect": choice[3],
                })
        
        # 15% 概率附加负面技能 (与主技能独立)
        if random.random() < 0.15:
            neg_pool = [s for s in SKILL_POOL["通用"] if s[1] == "负面"]
            if neg_pool:
                s = random.choice(neg_pool)
                skills.append({
                    "skill_id": s[0],
                    "rarity": s[1],
                    "trigger": s[2],
                    "effect": s[3],
                })
        
        return skills


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
                       team_ovr: int = 50, team_level: int = 4) -> Player:
        """生成单个球员"""
        # Race
        race_str = random.choice(["asian", "western"])
        race = PlayerRace.ASIAN if race_str == "asian" else PlayerRace.WESTERN
        
        # Name
        name, region = self.name_gen.generate(race_str)
        
        # Avatar
        avatar_url = self.avatar_pool.pick(race_str)
        
        # Position (如果未指定)
        if position is None:
            position = random.choice(list(PlayerPosition))
        
        # Archetype
        archetype = _weighted_choice(ARCHETYPE_CONFIG[position])
        
        # Style
        style = _weighted_choice(STYLE_DISTRIBUTION)
        
        # Age & Potential
        birth_offset, potential_letter, potential_max, actual_age = self._generate_age_and_potential(team_level)
        
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
            position, archetype, style, actual_age, potential_max, team_ovr
        )
        ovr = attr_result.pop("ovr", 50)  # 不持久化, 由模型 hybrid_property 计算
        
        # Skills
        skills = SkillGenerator.generate(position, ovr)
        
        # Personality
        personality = random.choice(PERSONALITIES)
        
        # Contract
        contract_end = random.randint(1, 4)  # 1-4个赛季后到期
        wage = Decimal(str(1000 + ovr * 800 + (potential_max - 50) * 50))
        release_clause = Decimal(str(wage * 20))
        market_value = Decimal(str(ovr * 10000 + potential_max * 500))
        
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
        
        return Player(
            name=name,
            race=race,
            avatar_url=avatar_url,
            position=position,
            preferred_foot=foot,
            height=height,
            weight=weight,
            birth_offset=birth_offset,
            # 21 attrs
            sho=attr_result["sho"], pas=attr_result["pas"], dri=attr_result["dri"],
            spd=attr_result["spd"], str_=attr_result["str_"], sta=attr_result["sta"],
            acc=attr_result["acc"], hea=attr_result["hea"], bal=attr_result["bal"],
            defe=attr_result["defe"], tkl=attr_result["tkl"], vis=attr_result["vis"],
            cro=attr_result["cro"], con=attr_result["con"], fin=attr_result["fin"],
            com=attr_result["com"], sav=attr_result["sav"], ref=attr_result["ref"],
            pos=attr_result["pos"], fk=attr_result["fk"], pk=attr_result["pk"],
            potential_max=potential_max,
            potential_letter=potential_letter,
            # skills & personality
            skills=skills,
            personality=personality,
            # status
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fitness=100,
            # contract
            contract_type=ContractType.NORMAL,
            contract_end_season=contract_end,
            wage=wage,
            release_clause=release_clause,
            squad_role=role,
            market_value=market_value,
            team_id=team.id,
        )
    
    def generate_squad(self, team, size: int = 15) -> list:
        """为球队生成完整阵容"""
        players = []
        team_ovr = getattr(team, 'overall_rating', 50)
        team_level = 4  # TODO: 从联赛级别推算
        
        for pos, count in SQUAD_COMPOSITION:
            for _ in range(count):
                p = self.generate_player(team, position=pos, team_ovr=team_ovr, team_level=team_level)
                players.append(p)
        
        return players
