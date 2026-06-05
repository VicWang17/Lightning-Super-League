"""
Injury service - 伤病系统服务
按设计文档 INJURY-SYSTEM-DESIGN.md 实现。
负责：训练/比赛后的劳损累积、伤病检定、恢复结算、伤愈残余劳损。
"""
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.orm.attributes import flag_modified

from app.models.player import Player, PlayerStatus
from app.core.training_config import TrainingItem


# ============================================================================
# 身体部位常量 (与 match-engine 对应)
# ============================================================================

BODY_PARTS = [
    "hamstring", "quadriceps", "calf", "groin", "ankle",
    "knee", "achilles", "foot", "back", "ribs",
    "shoulder", "fingers", "head",
]

# ============================================================================
# 恢复区间表 [severity][part] = (min_days, max_days)
# severity: 1=minor, 2=medium, 3=major
# ============================================================================

RECOVERY_RANGES = {
    "hamstring":  {1: (1, 2), 2: (4, 6), 3: (7, 12)},
    "quadriceps": {1: (1, 2), 2: (4, 6), 3: (7, 12)},
    "calf":       {1: (1, 2), 2: (4, 6), 3: (7, 12)},
    "groin":      {1: (1, 2), 2: (5, 7), 3: (7, 12)},
    "ankle":      {1: (1, 2), 2: (5, 8), 3: (7, 12)},
    "knee":       {1: (1, 2), 2: (5, 8), 3: (7, 12)},
    "achilles":   {1: (1, 2), 2: (5, 8), 3: (8, 12)},
    "foot":       {1: (1, 1), 2: (5, 8), 3: (7, 12)},
    "back":       {1: (1, 2), 2: (5, 8), 3: (7, 12)},
    "ribs":       {1: (1, 2), 2: (6, 9), 3: (8, 12)},
    "shoulder":   {1: (1, 2), 2: (5, 8), 3: (7, 12)},
    "fingers":    {1: (1, 1), 2: (4, 6), 3: (7, 12)},
    "head":       {1: (1, 1), 2: (5, 8), 3: (7, 12)},
}

# ============================================================================
# 伤病名称映射
# ============================================================================

INJURY_NAMES = {
    "hamstring":  {1: "腿筋肌肉紧绷", 2: "腿筋轻度拉伤", 3: "腿筋中度拉伤"},
    "quadriceps": {1: "股四头肌酸痛", 2: "股四头肌轻度拉伤", 3: "股四头肌中度拉伤"},
    "calf":       {1: "小腿肌肉紧绷", 2: "小腿轻度拉伤", 3: "小腿中度拉伤"},
    "groin":      {1: "腹股沟紧绷", 2: "腹股沟轻度拉伤", 3: "腹股沟中度拉伤"},
    "ankle":      {1: "脚踝轻度扭伤", 2: "脚踝中度扭伤", 3: "脚踝严重扭伤"},
    "knee":       {1: "膝盖不适", 2: "膝盖挫伤", 3: "膝盖内侧副韧带扭伤"},
    "achilles":   {1: "跟腱紧绷", 2: "跟腱轻度炎症", 3: "跟腱中度炎症"},
    "foot":       {1: "脚趾不适", 2: "足部瘀伤", 3: "脚趾骨折"},
    "back":       {1: "腰背僵硬", 2: "腰部肌肉痉挛", 3: "下背部拉伤"},
    "ribs":       {1: "肋部不适", 2: "肋骨挫伤", 3: "单根肋骨骨折"},
    "shoulder":   {1: "肩部僵硬", 2: "肩袖轻度拉伤", 3: "肩关节扭伤"},
    "fingers":    {1: "手指不适", 2: "手指挫伤", 3: "手指骨折"},
    "head":       {1: "面部擦伤", 2: "面部淤肿", 3: "鼻骨骨折"},
}

# ============================================================================
# 训练伤病基础概率 (比比赛更低)
# ============================================================================

TRAINING_INJURY_RATES = {
    # intensity: (light_prob, medium_prob, severe_prob)
    "light":  (0.0006, 0.00004, 0.000002),  # 0.06%, 0.004%, 0.0002%
    "normal": (0.0018, 0.00012, 0.000006),  # 0.18%, 0.012%, 0.0006%
    "hard":   (0.0048, 0.00035, 0.00002),   # 0.48%, 0.035%, 0.002%
}

# ============================================================================
# 自然恢复配置
# ============================================================================

DAILY_BASE_RECOVERY = {
    "sleep": 1.5,  # 每天睡眠基础恢复
    "full_rest": 8.0,
    "recovery_training": 5.0,
    "light_training": 2.0,
    "normal_training": 1.5,
    "high_intensity_training": 0.0,
}

# 特质修正
TRAIT_RECOVERY_MODIFIERS = {
    "铁人": 1.30,
    "年轻气盛": 1.20,
    "老将": 0.80,
    "玻璃体质": 0.85,
}

TRAIT_WEAR_MODIFIERS = {
    "铁人": 0.70,
    "玻璃体质": 1.50,
    "老将": 1.20,
}


def _clamp(val: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, val))


def _flag_json_modified(player: Player, field: str) -> None:
    try:
        flag_modified(player, field)
    except Exception:
        pass


def _player_age(player: Player) -> int:
    explicit_age = getattr(player, "age", None)
    if explicit_age is not None:
        try:
            return int(explicit_age)
        except (TypeError, ValueError):
            pass
    return int(abs(getattr(player, "birth_offset", 24) or 24))


class InjuryService:
    """伤病系统服务"""

    # ========================================================================
    # Body Wear 读写
    # ========================================================================

    @staticmethod
    def get_body_wear(player: Player, part: str) -> float:
        """获取指定部位的劳损值"""
        if player.body_wear is None:
            player.body_wear = {}
        return float(player.body_wear.get(part, 0.0))

    @staticmethod
    def set_body_wear(player: Player, part: str, value: float) -> None:
        """设置指定部位的劳损值"""
        if player.body_wear is None:
            player.body_wear = {}
        player.body_wear[part] = _clamp(value)
        _flag_json_modified(player, "body_wear")

    @staticmethod
    def add_body_wear(player: Player, part: str, delta: float) -> None:
        """增加指定部位的劳损值"""
        current = InjuryService.get_body_wear(player, part)
        InjuryService.set_body_wear(player, part, current + delta)

    # ========================================================================
    # 训练劳损累积
    # ========================================================================

    @staticmethod
    def apply_training_wear(player: Player, training_item: TrainingItem) -> None:
        """应用训练对 body_wear 的影响"""
        if not training_item.wear_impact:
            return

        # 特质修正
        trait_mod = 1.0
        for trait in player.traits or []:
            trait_mod *= TRAIT_WEAR_MODIFIERS.get(trait, 1.0)
        if _player_age(player) > 32:
            trait_mod *= 1.20

        for part, value in training_item.wear_impact.items():
            InjuryService.add_body_wear(player, part, value * trait_mod)

    # ========================================================================
    # 训练后伤病检定
    # ========================================================================

    @staticmethod
    def check_training_injury(player: Player, training_item: TrainingItem) -> Optional[dict]:
        """
        训练后伤病检定。
        返回伤病信息 dict 或 None。
        """
        # 已有伤病则跳过
        if player.current_injury is not None:
            return None

        rates = TRAINING_INJURY_RATES.get(training_item.intensity, TRAINING_INJURY_RATES["normal"])
        light_rate, medium_rate, severe_rate = rates

        # 获取最高劳损部位
        max_wear = 0.0
        max_part = ""
        for part in BODY_PARTS:
            wear = InjuryService.get_body_wear(player, part)
            if wear > max_wear:
                max_wear = wear
                max_part = part

        if not max_part:
            return None

        # 劳损系数: (1 + wear/50)^2
        wear_factor = (1.0 + max_wear / 50.0) ** 2

        # 特质修正
        trait_mod = 1.0
        for trait in player.traits or []:
            if trait == "铁人":
                trait_mod *= 0.60
            elif trait == "玻璃体质":
                trait_mod *= 1.50
        if _player_age(player) > 32:
            trait_mod *= 1.20

        light_prob = light_rate * wear_factor * trait_mod
        medium_prob = medium_rate * wear_factor * trait_mod
        severe_prob = severe_rate * wear_factor * trait_mod

        roll = random.random()

        severity = 0
        if roll < severe_prob:
            severity = 3
        elif roll < severe_prob + medium_prob:
            severity = 2
        elif roll < severe_prob + medium_prob + light_prob:
            severity = 1

        if severity == 0:
            return None

        # 训练伤病应主要由劳损驱动：低劳损最多轻伤，中等劳损最多中伤。
        if max_wear < 35:
            severity = 1
        elif max_wear < 60:
            severity = min(severity, 2)

        # 确定严重程度分布（基于劳损值）
        if severity == 1:
            sev_dist_roll = random.random()
            if max_wear <= 40:
                pass  # 保持 1
            elif max_wear <= 60:
                if sev_dist_roll < 0.30:
                    severity = 2
            elif max_wear <= 80:
                if sev_dist_roll < 0.55:
                    severity = 2
                elif sev_dist_roll < 0.85:
                    severity = 3
            else:
                if sev_dist_roll < 0.35:
                    severity = 2
                elif sev_dist_roll < 0.90:
                    severity = 3

        # 选择伤病部位：训练 wear_impact 中涉及的部位，选劳损最高的
        candidate_parts = [p for p in training_item.wear_impact.keys() if p in BODY_PARTS]
        if not candidate_parts:
            candidate_parts = [max_part]

        selected_part = max(candidate_parts, key=lambda p: InjuryService.get_body_wear(player, p))

        # 恢复天数
        min_days, max_days = RECOVERY_RANGES[selected_part][severity]
        days = random.randint(min_days, max_days)

        injury_name = INJURY_NAMES[selected_part][severity]

        return {
            "body_part": selected_part,
            "injury_name": injury_name,
            "severity": severity,
            "days": days,
        }

    # ========================================================================
    # 应用伤病到球员
    # ========================================================================

    @staticmethod
    def apply_injury(player: Player, injury: dict, cause: str = "training") -> None:
        """将伤病信息应用到球员状态"""
        player.current_injury = {
            "body_part": injury["body_part"],
            "injury_name": injury["injury_name"],
            "severity": injury["severity"],
            "remaining_days": injury["days"],
            "created_at": datetime.utcnow().isoformat(),
            "cause": cause,
        }
        if injury.get("season_id"):
            player.current_injury["season_id"] = injury["season_id"]
        if injury.get("fixture_id"):
            player.current_injury["fixture_id"] = injury["fixture_id"]
        if player.team_id:
            player.current_injury["team_id"] = player.team_id
        _flag_json_modified(player, "current_injury")

        if injury["severity"] >= 2:
            player.status = PlayerStatus.INJURED

        # 记录历史
        history = player.injury_history or []
        history.append(player.current_injury.copy())
        # 只保留最近 30 条
        player.injury_history = history[-30:]
        _flag_json_modified(player, "injury_history")

    # ========================================================================
    # 每日恢复结算
    # ========================================================================

    @staticmethod
    def apply_daily_recovery(
        player: Player,
        activity_type: str = "normal_training",
    ) -> dict:
        """
        每日 BodyWear 恢复结算。
        activity_type: full_rest / recovery_training / light_training / normal_training / high_intensity_training
        返回恢复摘要。
        """
        recovery_summary = {}

        # 基础恢复值。睡眠恢复每天独立触发，即使高强度训练也至少恢复 sleep。
        base_recovery = DAILY_BASE_RECOVERY.get(activity_type, DAILY_BASE_RECOVERY["normal_training"])

        # 特质修正
        trait_mod = 1.0
        for trait in player.traits or []:
            trait_mod *= TRAIT_RECOVERY_MODIFIERS.get(trait, 1.0)
        age = _player_age(player)
        if age < 23:
            trait_mod *= 1.20
        elif age > 32:
            trait_mod *= 0.80

        total_recovery = base_recovery + DAILY_BASE_RECOVERY["sleep"]
        if total_recovery <= 0:
            return recovery_summary
        effective_recovery = total_recovery * trait_mod

        for part in BODY_PARTS:
            current = InjuryService.get_body_wear(player, part)
            if current > 0:
                new_val = _clamp(current - effective_recovery)
                InjuryService.set_body_wear(player, part, new_val)
                recovered = current - new_val
                if recovered > 0.01:
                    recovery_summary[part] = round(recovered, 2)

        return recovery_summary

    # ========================================================================
    # 伤病恢复倒计时
    # ========================================================================

    @staticmethod
    def tick_injury_recovery(player: Player) -> bool:
        """
        每天减少伤病剩余天数。
        返回 True 如果伤病已痊愈。
        """
        if player.current_injury is None:
            return False

        remaining = player.current_injury.get("remaining_days", 0)
        if remaining <= 1:
            # 伤愈
            InjuryService._recover_from_injury(player)
            return True

        player.current_injury["remaining_days"] = remaining - 1
        _flag_json_modified(player, "current_injury")

        # 伤病期间每天额外恢复该部位劳损
        part = player.current_injury.get("body_part")
        if part:
            current = InjuryService.get_body_wear(player, part)
            # 每天 -15（强制休息）
            new_val = max(0, current - 15.0)
            InjuryService.set_body_wear(player, part, new_val)

        return False

    @staticmethod
    def _recover_from_injury(player: Player) -> None:
        """伤病痊愈处理"""
        part = player.current_injury.get("body_part") if player.current_injury else None
        player.current_injury = None
        _flag_json_modified(player, "current_injury")
        if player.status == PlayerStatus.INJURED:
            player.status = PlayerStatus.ACTIVE

        # 残余劳损：15~30 随机值
        if part:
            residual = random.uniform(15.0, 30.0)
            # 铁人残余更低
            if "铁人" in (player.traits or []):
                residual = random.uniform(10.0, 20.0)
            elif "玻璃体质" in (player.traits or []):
                residual = random.uniform(25.0, 40.0)
            InjuryService.set_body_wear(player, part, residual)

    # ========================================================================
    # 比赛 wear 回写（从 match-engine 结果）
    # ========================================================================

    @staticmethod
    def apply_match_wear(player: Player, match_wear: dict) -> None:
        """
        将 match-engine 返回的比赛磨损回写到球员 body_wear。
        match_wear 格式: {"hamstring": 5.2, "knee": 3.1, ...}
        """
        if not match_wear:
            return

        trait_mod = 1.0
        for trait in player.traits or []:
            trait_mod *= TRAIT_WEAR_MODIFIERS.get(trait, 1.0)
        if _player_age(player) > 32:
            trait_mod *= 1.20

        for part, value in match_wear.items():
            if part in BODY_PARTS:
                InjuryService.add_body_wear(player, part, value * trait_mod)

    # ========================================================================
    # 赛后伤病检定（从 match-engine 结果）
    # ========================================================================

    @staticmethod
    def apply_match_injury(player: Player, injury_info: dict) -> None:
        """
        将 match-engine 返回的伤病信息回写到球员。
        injury_info 格式: {"body_part": "hamstring", "injury_name": "腿筋中度拉伤", "severity": 3, "days": 10}
        """
        if not injury_info:
            return
        if player.current_injury is not None:
            return

        InjuryService.apply_injury(player, injury_info, cause="match")

    # ========================================================================
    # 辅助查询
    # ========================================================================

    @staticmethod
    def get_wear_status(player: Player) -> dict:
        """获取球员各部位劳损状态（用于前端展示）"""
        status = {}
        for part in BODY_PARTS:
            wear = InjuryService.get_body_wear(player, part)
            if wear <= 25:
                level = "normal"
                label = "正常"
            elif wear <= 50:
                level = "caution"
                label = "略有疲劳"
            elif wear <= 70:
                level = "warning"
                label = "需要关注"
            elif wear <= 90:
                level = "danger"
                label = "濒临受伤"
            else:
                level = "critical"
                label = "极度疲劳"
            status[part] = {
                "value": round(wear, 1),
                "level": level,
                "label": label,
            }
        return status

    @staticmethod
    def is_match_fit(player: Player) -> bool:
        """判断球员是否可以参赛"""
        if player.current_injury is None:
            return True
        return player.current_injury.get("severity", 0) < 2

    @staticmethod
    def get_injury_summary(player: Player) -> Optional[dict]:
        """获取当前伤病摘要"""
        if player.current_injury is None:
            return None
        return {
            "body_part": player.current_injury.get("body_part"),
            "injury_name": player.current_injury.get("injury_name"),
            "severity": player.current_injury.get("severity"),
            "remaining_days": player.current_injury.get("remaining_days"),
        }
