"""
球员短词描述（球员画像）生成服务。

根据 23 项能力、位置、年龄、潜力生成一句由短词拼接而成的中文描述，
例如：边路爆破射手、中场组织专家、全能型传球大师。

设计要点：
- 使用能力分组（速度、射门、传球、盘带、防守、头球、身体、镇定、传中、门将）
  计算倾向分。
- 同义词池 + 随机权重，降低趋同率。
- 支持主次风格组合，可能出现“边路爆破组织专家”这类跨界描述。
- 守门员使用独立的词库与模板。
"""
from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.player import Player


# 能力分组与参与计算的属性
ABILITY_GROUPS = {
    "speed": ["spd", "acc"],
    "shoot": ["sho", "fin"],
    "pass": ["pas", "vis", "dec"],
    "dribble": ["dri", "con"],
    "defense": ["defe", "tkl", "pos"],
    "header": ["hea"],
    "physical": ["str_", "sta", "bal"],
    "calm": ["com"],
    "cross": ["cro"],
    "gk": ["sav", "ref", "pos", "rus", "com"],
}

# 每个分组的风格近义词池（同一属性可用多种说法）。
# 大部分词会和“型”搭配，如“盘带型中场”“重炮型前锋”。
STYLE_WORDS: dict[str, list[str]] = {
    "speed": ["极速", "闪电", "飞翼", "爆破"],
    "shoot": ["射门", "终结", "重炮", "得分"],
    "pass": ["组织", "传球", "调度", "发动机", "掌控"],
    "dribble": ["盘带", "突破", "控球", "魔术师", "灵动"],
    "defense": ["防守", "拦截", "抢断", "铁壁"],
    "header": ["头球", "空霸", "制空"],
    "physical": ["力量", "坦克", "硬汉", "绞肉机", "冲撞"],
    "calm": ["镇定", "冷静", "沉稳", "大心脏"],
    "cross": ["传中", "边路", "传中高手"],
    "gk": ["扑救", "反应", "出击", "镇定"],
}

# 按位置划分的区域词
ZONE_WORDS: dict[str, list[str]] = {
    "FW": ["禁区", "前场", "锋线", "中路", "两翼", "边路"],
    "MF": ["中场", "中路", "禁区前", "两翼", "边路"],
    "DF": ["后场", "禁区", "中路", "防线"],
    "GK": ["门前", "球门", "禁区"],
}

# 按位置划分的身份词（结尾名词）
ROLE_WORDS: dict[str, list[str]] = {
    "FW": ["前锋", "射手", "终结者", "杀手", "中锋", "快马", "妖人", "新星"],
    "MF": ["中场", "核心", "指挥官", "发动机", "大师", "妖人", "新星"],
    "DF": ["后卫", "铁闸", "防守大闸", "统帅", "大师", "妖人", "新星"],
    "GK": ["门将", "门神", "守护神", "门线专家", "定海神针"],
}

# 年轻高潜力球员可能出现的限定词
YOUNG_WORDS = ["天才型", "妖人", "新星", "超新星"]
VETERAN_WORDS = ["传奇", "老将", "定海神针"]


class PlayerDescriptionService:
    """生成球员短词画像。"""

    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def generate(self, player: Player) -> str:
        """根据球员属性生成一句短词描述。"""
        position = player.position.value if hasattr(player.position, "value") else str(player.position)
        scores = self._compute_group_scores(player)

        if position == "GK":
            return self._generate_gk(scores, player)

        # 普通 outfield 球员
        main_group, main_style, sub_group, sub_style = self._pick_styles(scores, position)
        zone = self._pick_zone(position, scores, exclude={main_style, sub_style} if sub_style else {main_style})
        role = self._pick_role(position, scores, player)

        # 全能型判定：多个分组都较高
        balanced = self._is_balanced(scores)

        templates: list[str] = []

        # 传中作为主导风格时，用“传中高手”这种更自然的说法，避免生硬的“传中型”
        if main_group == "cross":
            templates.append(f"{zone}{main_style}{role}")
            templates.append(f"{main_style}{role}")
            if sub_style:
                templates.append(f"{zone}{main_style}{sub_style}专家")
                templates.append(f"{main_style}{sub_style}专家")
                if main_style != "传中高手":
                    templates.append(f"{main_style}型{sub_style}{role}")
                    templates.append(f"{zone}{main_style}型{sub_style}{role}")
        else:
            # 基础模板
            templates.append(f"{zone}{main_style}{role}")
            if sub_style:
                templates.append(f"{zone}{main_style}{sub_style}{role}")
                templates.append(f"{main_style}型{sub_style}{role}")
                templates.append(f"{zone}{main_style}{sub_style}专家")
            templates.append(f"{main_style}型{zone}{role}")
            if balanced:
                templates.append(f"全能型{main_style}{role}")
                if sub_style:
                    templates.append(f"全能型{main_style}{sub_style}{role}")

        # 年轻/老将限定词偶尔前置
        prefix = self._maybe_prefix(player)
        if prefix:
            base = self._rng.choice(templates)
            # 避免重复：如果基础里已经有“妖人/新星”就不再加限定词
            if not any(w in base for w in YOUNG_WORDS + VETERAN_WORDS):
                templates.append(f"{prefix}{base}")

        return self._rng.choice(templates)

    def _generate_gk(self, scores: dict[str, float], player: Player) -> str:
        """守门员专用生成逻辑。"""
        # 门将只看 gk 分组，淡化 outfield 分组
        gk_score = scores.get("gk", 10.0)
        main_style = self._weighted_choice(STYLE_WORDS["gk"], gk_score)
        role = self._pick_role("GK", scores, player)

        templates = [
            f"{main_style}型{role}",
            f"{main_style}{role}",
        ]
        prefix = self._maybe_prefix(player)
        if prefix:
            base = self._rng.choice(templates)
            if not any(w in base for w in YOUNG_WORDS + VETERAN_WORDS):
                templates.append(f"{prefix}{base}")
        return self._rng.choice(templates)

    def batch_generate(self, players: list[Player]) -> dict[str, str]:
        """批量生成，返回 {player_id: description}。"""
        return {str(p.id): self.generate(p) for p in players}

    def _compute_group_scores(self, player: Player) -> dict[str, float]:
        """计算每个能力分组的平均分。"""
        scores: dict[str, float] = {}
        for group, attrs in ABILITY_GROUPS.items():
            total = 0.0
            for attr in attrs:
                value = getattr(player, attr, 10)
                total += float(value)
            scores[group] = total / len(attrs)
        return scores

    def _pick_styles(self, scores: dict[str, float], position: str) -> tuple[str, str, str | None, str | None]:
        """挑选主、副风格词及其所属分组。

        按分组得分排序，主风格取 Top1，副风格从 Top2-4 中按softmax加权选取。
        """
        # outfield 球员不直接用 gk 分组做主风格
        eligible = {k: v for k, v in scores.items() if k != "gk"}
        sorted_groups = sorted(eligible.items(), key=lambda x: x[1], reverse=True)

        main_group = sorted_groups[0][0]
        main_style = self._weighted_choice(STYLE_WORDS[main_group], sorted_groups[0][1])

        sub_group: str | None = None
        sub_style: str | None = None
        if len(sorted_groups) >= 2:
            # 从第二到第四中按得分加权选一个作为副风格
            candidates = sorted_groups[1:4]
            sub_group = self._weighted_choice_by_score([g for g, _ in candidates], [s for _, s in candidates])
            # 只有当副风格分数不太低时才使用
            if scores[sub_group] >= 10.5 and sub_group != main_group:
                sub_style = self._weighted_choice(STYLE_WORDS[sub_group], scores[sub_group])
        return main_group, main_style, sub_group, sub_style

    def _pick_zone(self, position: str, scores: dict[str, float], exclude: set[str] | None = None) -> str:
        """根据位置和速度/传中倾向选取区域词，避免与风格词重复。"""
        exclude = exclude or set()
        zones = [z for z in ZONE_WORDS.get(position, ZONE_WORDS["MF"]) if z not in exclude]
        if not zones:
            zones = ZONE_WORDS.get(position, ZONE_WORDS["MF"])
        # 速度或传中高时，更可能出现边路/两翼；所有权重保底 0.1
        weights = [1.0] * len(zones)
        for i, z in enumerate(zones):
            if z in ("边路", "两翼"):
                weights[i] += (scores.get("speed", 10) - 10) * 0.15
                weights[i] += (scores.get("cross", 10) - 10) * 0.15
            elif z in ("中路", "禁区", "中场"):
                weights[i] += (scores.get("pass", 10) - 10) * 0.1
            weights[i] = max(0.1, weights[i])
        return self._rng.choices(zones, weights=weights, k=1)[0]

    def _pick_role(self, position: str, scores: dict[str, float], player: Player) -> str:
        """挑选身份词。"""
        roles = ROLE_WORDS.get(position, ROLE_WORDS["MF"])
        weights = [1.0] * len(roles)

        age = abs(getattr(player, "birth_offset", -22))
        potential = getattr(player, "potential_max", 50) or 50

        for i, role in enumerate(roles):
            # 年轻高潜更容易出现妖人/新星
            if role in ("妖人", "新星", "超新星"):
                if age <= 21 and potential >= 75:
                    weights[i] += 3.0
                elif age <= 23 and potential >= 70:
                    weights[i] += 1.5
            # 老将更容易出现传奇/老将
            if role in ("传奇", "老将", "定海神针"):
                if age >= 30:
                    weights[i] += 2.0
                if age >= 28 and potential >= 80:
                    weights[i] += 1.0
            # 前锋射门高时更容易叫射手/终结者/杀手
            if position == "FW" and role in ("射手", "终结者", "杀手"):
                weights[i] += (scores.get("shoot", 10) - 10) * 0.2
            # 中场传球高时更容易叫核心/指挥官/发动机/大师
            if position == "MF" and role in ("核心", "指挥官", "发动机", "大师"):
                weights[i] += (scores.get("pass", 10) - 10) * 0.2
            # 后卫防守高时更容易叫铁闸/防守大闸/统帅
            if position == "DF" and role in ("铁闸", "防守大闸", "统帅"):
                weights[i] += (scores.get("defense", 10) - 10) * 0.2

            # 保底权重，避免极端属性导致 weights 全为非正数
            weights[i] = max(0.1, weights[i])

        if not roles or sum(weights) <= 0:
            return "球员"

        return self._rng.choices(roles, weights=weights, k=1)[0]

    def _maybe_prefix(self, player: Player) -> str:
        """根据年龄和潜力决定是否加前缀限定词。"""
        age = abs(getattr(player, "birth_offset", -22))
        potential = getattr(player, "potential_max", 50) or 50

        if age <= 21 and potential >= 75:
            return self._rng.choice(YOUNG_WORDS)
        if age >= 30 and potential >= 75:
            return self._rng.choice(VETERAN_WORDS)
        return ""

    def _is_balanced(self, scores: dict[str, float]) -> bool:
        """判断是否属于全能型：多个 outfield 分组都超过 12 分。"""
        outfield = {k: v for k, v in scores.items() if k not in ("gk", "calm")}
        high_groups = sum(1 for v in outfield.values() if v >= 12.0)
        return high_groups >= 4

    def _weighted_choice(self, options: list[str], score: float) -> str:
        """分数越高，越可能选到池中靠后的“高级”词。"""
        weights = [1.0 + max(0, score - 10) * (i / max(1, len(options) - 1)) for i in range(len(options))]
        return self._rng.choices(options, weights=weights, k=1)[0]

    def _weighted_choice_by_score(self, options: list[str], scores: list[float]) -> str:
        """按 raw score 加权选择。"""
        weights = [max(0.1, s - 8) for s in scores]
        return self._rng.choices(options, weights=weights, k=1)[0]
