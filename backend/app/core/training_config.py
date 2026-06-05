"""
Training content configuration - 训练内容配置
按设计文档 TRAINING-SYSTEM-DESIGN.md 第 9 章实现。
v1 使用代码常量定义，不单独建表。
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrainingItem:
    """训练内容定义"""
    id: str
    name: str
    category: str
    recommended_group: str
    base_gain: float
    intensity: str  # light / normal / hard
    fitness_delta: int
    fatigue_delta: int
    load_points: int
    attribute_weights: dict[str, float] = field(default_factory=dict)
    position_fit: dict[str, float] = field(default_factory=dict)
    is_recovery: bool = False
    wear_impact: dict[str, float] = field(default_factory=dict)  # 各部位劳损值 e.g. {"hamstring": 3.0}


# ==================== 训练内容池 ====================

TRAINING_ITEMS: dict[str, TrainingItem] = {}


def _register(item: TrainingItem) -> None:
    TRAINING_ITEMS[item.id] = item


# ----- 9.1 终结训练 -----
_register(TrainingItem("box_finish_one_touch", "禁区一脚终结", "finishing", "进攻组", 0.07, "normal", -4, 7, 2,
    {"sho": 1.0, "com": 0.35, "acc": 0.25},
    {"FW": 1.10, "MF": 0.90, "DF": 0.60, "GK": 0.40}, wear_impact={"quadriceps": 2, "groin": 1, "knee": 1}))
_register(TrainingItem("box_finish_under_pressure", "对抗下射门选择", "finishing", "进攻组", 0.08, "hard", -6, 10, 3,
    {"sho": 0.90, "com": 0.80, "bal": 0.30, "dec": 0.30},
    {"FW": 1.10, "MF": 0.85, "DF": 0.55, "GK": 0.35}, wear_impact={"quadriceps": 3, "groin": 2, "back": 2, "ankle": 1}))
_register(TrainingItem("cutback_finish", "倒三角接应射门", "finishing", "进攻组/中场", 0.07, "normal", -4, 7, 2,
    {"sho": 0.90, "pas": 0.35, "dec": 0.30},
    {"FW": 1.05, "MF": 1.00, "DF": 0.60, "GK": 0.40}, wear_impact={"quadriceps": 2, "groin": 1}))
_register(TrainingItem("near_post_finish", "前点抢射", "finishing", "进攻组", 0.06, "normal", -4, 7, 2,
    {"sho": 1.0, "acc": 0.40, "com": 0.25},
    {"FW": 1.10, "MF": 0.80, "DF": 0.60, "GK": 0.40}, wear_impact={"quadriceps": 2, "knee": 1, "ankle": 1}))
_register(TrainingItem("far_post_arrival", "后点包抄", "finishing", "进攻组/中场", 0.06, "normal", -4, 7, 2,
    {"sho": 0.90, "dec": 0.40, "hea": 0.30, "acc": 0.25},
    {"FW": 1.05, "MF": 0.95, "DF": 0.65, "GK": 0.40}, wear_impact={"hamstring": 2, "quadriceps": 2, "knee": 1}))
_register(TrainingItem("weak_foot_finish", "非惯用脚终结", "finishing", "进攻组", 0.06, "normal", -4, 7, 2,
    {"sho": 1.0, "com": 0.35, "bal": 0.30},
    {"FW": 1.10, "MF": 0.85, "DF": 0.55, "GK": 0.35}, wear_impact={"quadriceps": 2, "ankle": 2, "groin": 1}))
_register(TrainingItem("long_shot_window", "禁区弧顶远射窗口", "finishing", "中场/进攻组", 0.06, "normal", -4, 7, 2,
    {"fin": 1.0, "sho": 0.50, "dec": 0.30},
    {"FW": 0.95, "MF": 1.10, "DF": 0.60, "GK": 0.35}, wear_impact={"quadriceps": 3, "groin": 2, "knee": 1}))
_register(TrainingItem("volley_second_ball", "二点球凌空处理", "finishing", "进攻组/防守组", 0.07, "hard", -6, 10, 3,
    {"sho": 0.90, "hea": 0.40, "bal": 0.30},
    {"FW": 1.05, "MF": 0.90, "DF": 0.80, "GK": 0.40}, wear_impact={"quadriceps": 3, "groin": 2, "back": 2, "knee": 2}))
_register(TrainingItem("penalty_routine", "点球助跑与角度", "finishing", "指定球员/进攻组", 0.05, "light", -2, 3, 1,
    {"pk": 1.0, "com": 0.40, "sho": 0.25},
    {"FW": 1.05, "MF": 0.85, "DF": 0.60, "GK": 0.40}, wear_impact={"quadriceps": 1}))
_register(TrainingItem("penalty_pressure", "压力点球模拟", "finishing", "指定球员/全队", 0.08, "normal", -4, 7, 2,
    {"pk": 1.0, "com": 0.80, "sho": 0.25},
    {"FW": 1.10, "MF": 0.90, "DF": 0.65, "GK": 0.45}, wear_impact={"quadriceps": 1, "groin": 1}))

# ----- 9.2 传控训练 -----
_register(TrainingItem("rondo_4v2", "4v2 小圈保球", "passing", "全队/中场", 0.06, "normal", -4, 7, 2,
    {"pas": 0.90, "con": 0.80, "dec": 0.30, "vis": 0.25},
    {"FW": 0.90, "MF": 1.10, "DF": 0.85, "GK": 0.50}, wear_impact={"ankle": 2, "knee": 1, "groin": 1}))
_register(TrainingItem("third_man_combination", "第三人接应配合", "passing", "中场/进攻组", 0.06, "normal", -4, 7, 2,
    {"pas": 0.90, "vis": 0.70, "dec": 0.35, "con": 0.25},
    {"FW": 0.90, "MF": 1.10, "DF": 0.80, "GK": 0.45}, wear_impact={"ankle": 1, "knee": 1}))
_register(TrainingItem("wall_pass_timing", "撞墙配合时机", "passing", "进攻组/中场", 0.06, "normal", -4, 7, 2,
    {"pas": 1.0, "acc": 0.30, "dec": 0.30},
    {"FW": 1.05, "MF": 1.05, "DF": 0.70, "GK": 0.40}, wear_impact={"ankle": 1, "knee": 1}))
_register(TrainingItem("switch_play", "弱侧转移", "passing", "中场/防守组", 0.06, "normal", -4, 7, 2,
    {"pas": 0.80, "vis": 0.80, "cro": 0.30, "dec": 0.25},
    {"FW": 0.80, "MF": 1.10, "DF": 0.90, "GK": 0.50}, wear_impact={"hamstring": 1, "calf": 1, "knee": 1}))
_register(TrainingItem("line_breaking_pass", "穿线直塞", "passing", "中场", 0.06, "normal", -4, 7, 2,
    {"vis": 0.90, "pas": 0.80, "dec": 0.40, "com": 0.25},
    {"FW": 0.85, "MF": 1.10, "DF": 0.70, "GK": 0.40}, wear_impact={"ankle": 1}))
_register(TrainingItem("first_touch_escape", "第一脚卸压", "passing", "全队/中场", 0.06, "normal", -4, 7, 2,
    {"con": 0.90, "dri": 0.40, "bal": 0.30},
    {"FW": 0.90, "MF": 1.05, "DF": 0.85, "GK": 0.50}, wear_impact={"ankle": 2, "knee": 1}))
_register(TrainingItem("back_to_goal_link", "背身接应做球", "passing", "进攻组", 0.07, "hard", -6, 10, 3,
    {"con": 0.80, "pas": 0.70, "str_": 0.40, "dec": 0.30},
    {"FW": 1.10, "MF": 0.90, "DF": 0.60, "GK": 0.35}, wear_impact={"back": 2, "groin": 2, "knee": 2, "ankle": 1}))
_register(TrainingItem("cross_low_driven", "低平传中", "passing", "边路球员", 0.06, "normal", -4, 7, 2,
    {"cro": 1.0, "pas": 0.35, "dec": 0.25},
    {"FW": 0.80, "MF": 1.00, "DF": 0.90, "GK": 0.35}, wear_impact={"groin": 2, "hamstring": 1, "knee": 1}))
_register(TrainingItem("cross_early", "提前量传中", "passing", "边路球员", 0.06, "normal", -4, 7, 2,
    {"cro": 0.90, "vis": 0.50, "pas": 0.30},
    {"FW": 0.80, "MF": 1.00, "DF": 0.90, "GK": 0.35}, wear_impact={"groin": 2, "hamstring": 1}))
_register(TrainingItem("build_out_under_press", "后场出球抗压", "passing", "防守组/门将", 0.07, "hard", -6, 10, 3,
    {"pas": 0.80, "con": 0.70, "dec": 0.40, "com": 0.30},
    {"FW": 0.50, "MF": 0.80, "DF": 1.05, "GK": 0.90}, wear_impact={"ankle": 2, "knee": 2, "back": 1, "groin": 1}))

# ----- 9.3 个人技术 -----
_register(TrainingItem("dribble_cone_tight", "密集标志盘带", "technical", "进攻组/中场", 0.06, "normal", -4, 7, 2,
    {"dri": 1.0, "con": 0.50, "bal": 0.30},
    {"FW": 1.10, "MF": 0.95, "DF": 0.60, "GK": 0.35}, wear_impact={"ankle": 3, "knee": 2, "groin": 1}))
_register(TrainingItem("one_v_one_wing", "边路 1v1 突破", "technical", "进攻组", 0.07, "hard", -6, 10, 3,
    {"dri": 0.90, "acc": 0.70, "spd": 0.40, "bal": 0.25},
    {"FW": 1.10, "MF": 0.85, "DF": 0.60, "GK": 0.30}, wear_impact={"hamstring": 3, "groin": 2, "ankle": 2, "knee": 2}))
_register(TrainingItem("receive_on_half_turn", "半转身接球", "technical", "中场/进攻组", 0.06, "normal", -4, 7, 2,
    {"con": 0.80, "dec": 0.50, "dri": 0.30, "vis": 0.25},
    {"FW": 0.95, "MF": 1.05, "DF": 0.70, "GK": 0.40}, wear_impact={"ankle": 1, "knee": 1}))
_register(TrainingItem("shield_and_roll", "护球转身摆脱", "technical", "中场/进攻组", 0.07, "hard", -6, 10, 3,
    {"con": 0.80, "str_": 0.60, "bal": 0.40, "dri": 0.30},
    {"FW": 1.00, "MF": 1.00, "DF": 0.65, "GK": 0.30}, wear_impact={"back": 2, "groin": 2, "knee": 2, "ankle": 1}))
_register(TrainingItem("carry_into_space", "带球推进空间识别", "technical", "中场/进攻组", 0.06, "normal", -4, 7, 2,
    {"dri": 0.80, "dec": 0.60, "spd": 0.35, "con": 0.30},
    {"FW": 1.00, "MF": 1.00, "DF": 0.65, "GK": 0.30}, wear_impact={"hamstring": 1, "calf": 1, "ankle": 1}))
_register(TrainingItem("touchline_escape", "边线夹击脱困", "technical", "边路球员", 0.07, "hard", -6, 10, 3,
    {"dri": 0.80, "con": 0.60, "bal": 0.40, "pas": 0.25},
    {"FW": 0.90, "MF": 0.90, "DF": 0.80, "GK": 0.30}, wear_impact={"ankle": 3, "groin": 2, "knee": 2, "hamstring": 2}))
_register(TrainingItem("receiving_scanning", "接球前观察", "technical", "全队/中场", 0.04, "light", -2, 3, 1,
    {"dec": 0.80, "vis": 0.60, "con": 0.30, "pas": 0.20},
    {"FW": 0.90, "MF": 1.05, "DF": 0.90, "GK": 0.60}))

# ----- 9.4 防守训练 -----
_register(TrainingItem("body_shape_defense", "防守身体朝向", "defending", "防守组", 0.06, "normal", -4, 7, 2,
    {"defe": 1.0, "dec": 0.40, "bal": 0.25},
    {"FW": 0.50, "MF": 0.80, "DF": 1.10, "GK": 0.40}, wear_impact={"knee": 1, "ankle": 1}))
_register(TrainingItem("delay_and_channel", "延缓与逼向边线", "defending", "防守组", 0.06, "normal", -4, 7, 2,
    {"defe": 0.80, "dec": 0.60, "spd": 0.30, "tkl": 0.30},
    {"FW": 0.50, "MF": 0.80, "DF": 1.10, "GK": 0.40}, wear_impact={"hamstring": 1, "calf": 1, "knee": 1}))
_register(TrainingItem("standing_tackle_timing", "正面抢断时机", "defending", "防守组", 0.07, "hard", -6, 10, 3,
    {"tkl": 1.0, "defe": 0.50, "bal": 0.25},
    {"FW": 0.45, "MF": 0.75, "DF": 1.10, "GK": 0.35}, wear_impact={"ankle": 3, "knee": 3, "groin": 2, "hamstring": 2}))
_register(TrainingItem("cover_shadow_press", "遮挡传球线路逼抢", "defending", "全队/防守组", 0.07, "hard", -6, 10, 3,
    {"dec": 0.80, "defe": 0.70, "sta": 0.30, "acc": 0.25},
    {"FW": 0.60, "MF": 0.90, "DF": 1.10, "GK": 0.40}, wear_impact={"hamstring": 3, "calf": 2, "groin": 2, "knee": 2}))
_register(TrainingItem("recovery_run", "回追路线", "defending", "防守组/中场", 0.07, "hard", -6, 10, 3,
    {"spd": 0.80, "defe": 0.60, "sta": 0.40, "dec": 0.25},
    {"FW": 0.50, "MF": 0.90, "DF": 1.10, "GK": 0.35}, wear_impact={"hamstring": 4, "calf": 3, "groin": 2, "quadriceps": 2}))
_register(TrainingItem("aerial_duel_defense", "防守争顶", "defending", "防守组", 0.06, "normal", -4, 7, 2,
    {"hea": 0.90, "str_": 0.60, "defe": 0.40, "bal": 0.25},
    {"FW": 0.70, "MF": 0.80, "DF": 1.10, "GK": 0.50}, wear_impact={"back": 2, "knee": 2, "ankle": 1}))
_register(TrainingItem("box_marking", "禁区盯人与保护", "defending", "防守组/门将", 0.06, "normal", -4, 7, 2,
    {"defe": 0.80, "dec": 0.60, "hea": 0.30, "pos": 0.25},
    {"FW": 0.40, "MF": 0.70, "DF": 1.10, "GK": 0.80}, wear_impact={"knee": 1, "ankle": 1, "back": 1}))
_register(TrainingItem("counterpress_after_loss", "丢球后 5 秒反抢", "defending", "全队", 0.07, "hard", -9, 14, 4,
    {"tkl": 0.80, "sta": 0.60, "dec": 0.40, "acc": 0.25},
    {"FW": 0.80, "MF": 1.00, "DF": 1.00, "GK": 0.30}, wear_impact={"hamstring": 3, "calf": 3, "groin": 2, "ankle": 2, "knee": 2}))

# ----- 9.5 定位球训练 -----
_register(TrainingItem("corner_near_post", "角球前点跑位", "set_piece", "进攻组", 0.04, "light", -2, 3, 1,
    {"fk": 0.60, "hea": 0.60, "dec": 0.30, "acc": 0.20},
    {"FW": 1.00, "MF": 0.80, "DF": 0.70, "GK": 0.30}, wear_impact={"knee": 1}))
_register(TrainingItem("corner_far_post", "角球后点包抄", "set_piece", "进攻组/防守组", 0.04, "light", -2, 3, 1,
    {"hea": 0.70, "dec": 0.40, "str_": 0.25, "fk": 0.20},
    {"FW": 0.90, "MF": 0.80, "DF": 0.80, "GK": 0.30}, wear_impact={"knee": 1, "back": 1}))
_register(TrainingItem("free_kick_direct", "直接任意球脚法", "set_piece", "指定球员", 0.04, "light", -2, 3, 1,
    {"fk": 1.0, "com": 0.40, "sho": 0.30},
    {"FW": 0.90, "MF": 1.00, "DF": 0.70, "GK": 0.30}, wear_impact={"quadriceps": 1, "groin": 1}))
_register(TrainingItem("free_kick_routine", "间接任意球配合", "set_piece", "进攻组", 0.04, "light", -2, 3, 1,
    {"fk": 0.80, "dec": 0.50, "pas": 0.30, "hea": 0.20},
    {"FW": 0.90, "MF": 0.90, "DF": 0.60, "GK": 0.30}, wear_impact={"knee": 1}))
_register(TrainingItem("throw_in_pattern", "边线球接应套路", "set_piece", "全队", 0.03, "light", -2, 3, 1,
    {"dec": 0.60, "pas": 0.40, "con": 0.20},
    {"FW": 0.80, "MF": 0.90, "DF": 0.85, "GK": 0.30}, wear_impact={"shoulder": 1}))
_register(TrainingItem("set_piece_marking", "定位球区域盯防", "set_piece", "防守组/门将", 0.03, "light", -2, 3, 1,
    {"defe": 0.70, "pos": 0.50, "hea": 0.30, "dec": 0.20},
    {"FW": 0.40, "MF": 0.70, "DF": 1.00, "GK": 0.80}, wear_impact={"knee": 1}))
_register(TrainingItem("penalty_keeper_read", "门将扑点预判", "set_piece", "门将组", 0.04, "light", -2, 3, 1,
    {"ref": 0.80, "com": 0.60, "sav": 0.50, "dec": 0.30},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"shoulder": 1}))

# ----- 9.6 身体训练 -----
_register(TrainingItem("accel_5m", "5 米启动", "physical", "进攻组/防守组", 0.07, "hard", -9, 14, 4,
    {"acc": 1.0, "spd": 0.50, "bal": 0.25},
    {"FW": 1.05, "MF": 0.90, "DF": 1.00, "GK": 0.40}, wear_impact={"hamstring": 4, "calf": 3, "groin": 2, "quadriceps": 2}))
_register(TrainingItem("repeat_sprint", "重复冲刺能力", "physical", "全队", 0.07, "hard", -9, 14, 4,
    {"sta": 0.90, "spd": 0.60, "acc": 0.30},
    {"FW": 1.00, "MF": 1.00, "DF": 1.00, "GK": 0.40}, wear_impact={"hamstring": 5, "calf": 4, "groin": 3, "quadriceps": 3, "knee": 2}))
_register(TrainingItem("max_velocity", "最高速度跑", "physical", "进攻组/防守组", 0.07, "hard", -9, 14, 4,
    {"spd": 1.0, "acc": 0.40},
    {"FW": 1.05, "MF": 0.85, "DF": 1.00, "GK": 0.35}, wear_impact={"hamstring": 5, "calf": 3, "groin": 2, "quadriceps": 2}))
_register(TrainingItem("change_direction", "变向制动", "physical", "全队", 0.07, "hard", -9, 14, 4,
    {"bal": 0.90, "acc": 0.50, "dri": 0.30, "tkl": 0.20},
    {"FW": 0.90, "MF": 1.00, "DF": 1.00, "GK": 0.50}, wear_impact={"ankle": 4, "knee": 3, "groin": 3, "hamstring": 2}))
_register(TrainingItem("upper_body_duel", "上肢对抗", "physical", "防守组/进攻组", 0.07, "hard", -9, 14, 4,
    {"str_": 1.0, "bal": 0.50, "hea": 0.30},
    {"FW": 1.00, "MF": 0.80, "DF": 1.05, "GK": 0.40}, wear_impact={"shoulder": 3, "back": 3, "ribs": 2}))
_register(TrainingItem("core_stability", "核心稳定", "physical", "全队", 0.05, "normal", -4, 7, 2,
    {"bal": 0.90, "str_": 0.40, "con": 0.25},
    {"FW": 0.90, "MF": 1.00, "DF": 1.00, "GK": 0.60}, wear_impact={"back": 2, "groin": 1}))
_register(TrainingItem("aerobic_blocks", "分段有氧跑", "physical", "全队", 0.06, "hard", -9, 14, 4,
    {"sta": 1.0, "bal": 0.30},
    {"FW": 0.90, "MF": 1.05, "DF": 1.00, "GK": 0.45}, wear_impact={"hamstring": 3, "calf": 3, "quadriceps": 2, "knee": 2}))
_register(TrainingItem("jump_power", "起跳与落地", "physical", "进攻组/防守组", 0.05, "normal", -4, 7, 2,
    {"hea": 0.80, "str_": 0.50, "bal": 0.30},
    {"FW": 1.00, "MF": 0.85, "DF": 1.05, "GK": 0.50}, wear_impact={"knee": 3, "back": 2, "ankle": 2, "achilles": 2}))

# ----- 9.7 战术训练 -----
_register(TrainingItem("build_up_2_3", "2-3 出球结构", "tactical", "全队/防守组", 0.05, "normal", -4, 7, 2,
    {"dec": 0.80, "pas": 0.60, "con": 0.30, "vis": 0.25},
    {"FW": 0.60, "MF": 1.00, "DF": 1.05, "GK": 0.60}, wear_impact={"ankle": 1, "knee": 1}))
_register(TrainingItem("wide_overload", "边路局部人数优势", "tactical", "进攻组/中场", 0.05, "normal", -4, 7, 2,
    {"dec": 0.70, "pas": 0.60, "cro": 0.30, "dri": 0.25},
    {"FW": 1.00, "MF": 1.00, "DF": 0.60, "GK": 0.30}, wear_impact={"hamstring": 1, "groin": 1, "ankle": 1}))
_register(TrainingItem("central_compactness", "中路紧凑防守", "tactical", "防守组/中场", 0.05, "normal", -4, 7, 2,
    {"defe": 0.70, "dec": 0.60, "tkl": 0.30, "sta": 0.25},
    {"FW": 0.40, "MF": 1.00, "DF": 1.05, "GK": 0.50}, wear_impact={"knee": 1, "ankle": 1}))
_register(TrainingItem("press_trigger", "逼抢触发点", "tactical", "全队", 0.06, "hard", -6, 10, 3,
    {"dec": 0.70, "sta": 0.50, "tkl": 0.40, "acc": 0.25},
    {"FW": 0.80, "MF": 1.05, "DF": 1.00, "GK": 0.30}, wear_impact={"hamstring": 3, "calf": 2, "groin": 2, "ankle": 2, "knee": 2}))
_register(TrainingItem("rest_defense", "进攻时防反站位", "tactical", "防守组/中场", 0.05, "normal", -4, 7, 2,
    {"defe": 0.70, "dec": 0.60, "spd": 0.30, "pos": 0.25},
    {"FW": 0.40, "MF": 0.90, "DF": 1.05, "GK": 0.50}, wear_impact={"hamstring": 1, "knee": 1}))
_register(TrainingItem("transition_attack", "抢回球后的第一传", "tactical", "全队", 0.05, "normal", -4, 7, 2,
    {"dec": 0.70, "pas": 0.60, "spd": 0.25, "vis": 0.25},
    {"FW": 0.90, "MF": 1.00, "DF": 0.80, "GK": 0.40}, wear_impact={"hamstring": 1, "calf": 1}))
_register(TrainingItem("transition_defense", "失球权后的回收", "tactical", "全队", 0.06, "hard", -6, 10, 3,
    {"dec": 0.70, "sta": 0.50, "defe": 0.40, "spd": 0.25},
    {"FW": 0.70, "MF": 1.00, "DF": 1.00, "GK": 0.40}, wear_impact={"hamstring": 3, "calf": 2, "groin": 2, "quadriceps": 2}))
_register(TrainingItem("game_model_8v8", "8v8 队内模型赛", "tactical", "全队", 0.06, "hard", -12, 18, 5,
    {"dec": 0.80, "pas": 0.40, "defe": 0.30, "sta": 0.30},
    {"FW": 0.90, "MF": 1.00, "DF": 0.95, "GK": 0.40}, wear_impact={"hamstring": 3, "calf": 3, "knee": 3, "ankle": 3, "groin": 2, "back": 2}))

# ----- 9.8 门将训练 -----
_register(TrainingItem("gk_set_position", "准备姿势与重心", "goalkeeper", "门将组", 0.05, "normal", -4, 7, 2,
    {"pos": 0.90, "ref": 0.50, "bal": 0.25, "com": 0.20},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"knee": 1, "ankle": 1}))
_register(TrainingItem("gk_low_save", "低平球扑救", "goalkeeper", "门将组", 0.05, "normal", -4, 7, 2,
    {"sav": 0.90, "ref": 0.50, "pos": 0.25},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"shoulder": 2, "knee": 2, "back": 1}))
_register(TrainingItem("gk_close_range", "近距离封堵", "goalkeeper", "门将组", 0.06, "hard", -6, 10, 3,
    {"ref": 0.80, "sav": 0.70, "com": 0.30, "rus": 0.25},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"shoulder": 3, "knee": 3, "fingers": 2, "back": 2}))
_register(TrainingItem("gk_cross_claim", "传中球摘取", "goalkeeper", "门将组", 0.05, "normal", -4, 7, 2,
    {"rus": 0.80, "pos": 0.50, "com": 0.30, "hea": 0.20},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"shoulder": 2, "back": 2, "knee": 2, "fingers": 1}))
_register(TrainingItem("gk_one_v_one", "单刀出击", "goalkeeper", "门将组", 0.06, "hard", -6, 10, 3,
    {"rus": 0.80, "com": 0.50, "ref": 0.40, "dec": 0.25},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"knee": 3, "ankle": 3, "shoulder": 2, "back": 2}))
_register(TrainingItem("gk_distribution_short", "短传出球", "goalkeeper", "门将组", 0.04, "light", -2, 3, 1,
    {"pas": 0.70, "com": 0.40, "dec": 0.25, "con": 0.20},
    {"FW": 0.20, "MF": 0.30, "DF": 0.40, "GK": 1.10}, wear_impact={"shoulder": 1}))
_register(TrainingItem("gk_distribution_long", "长距离开球", "goalkeeper", "门将组", 0.04, "normal", -4, 7, 2,
    {"pas": 0.80, "str_": 0.30, "dec": 0.25},
    {"FW": 0.20, "MF": 0.30, "DF": 0.40, "GK": 1.10}, wear_impact={"shoulder": 2, "back": 2, "groin": 1}))
_register(TrainingItem("gk_penalty_read", "点球方向读取", "goalkeeper", "门将组", 0.04, "light", -2, 3, 1,
    {"ref": 0.70, "com": 0.50, "sav": 0.40, "dec": 0.25},
    {"FW": 0.20, "MF": 0.20, "DF": 0.30, "GK": 1.15}, wear_impact={"shoulder": 1}))

# ----- 9.9 恢复与分析 -----
_register(TrainingItem("full_rest", "完全休息", "recovery", "全队", 0.0, "light", 14, -16, -2,
    {}, {}, is_recovery=True))
_register(TrainingItem("mobility_session", "活动度与拉伸", "recovery", "全队", 0.02, "light", 6, -6, 0,
    {"bal": 0.30}, {}, is_recovery=True))
_register(TrainingItem("recovery_bike", "低强度单车恢复", "recovery", "全队/指定球员", 0.02, "light", 8, -8, -1,
    {"sta": 0.25}, {}, is_recovery=True))
_register(TrainingItem("hydro_recovery", "水疗恢复", "recovery", "全队/指定球员", 0.0, "light", 10, -12, -1,
    {}, {}, is_recovery=True))
_register(TrainingItem("individual_treatment", "个人理疗", "recovery", "指定球员", 0.0, "light", 12, -14, -2,
    {}, {}, is_recovery=True))
_register(TrainingItem("match_review_unit", "分组录像复盘", "analysis", "分组", 0.03, "light", 2, -2, 0,
    {"dec": 0.50, "vis": 0.30}, {}, is_recovery=True))
_register(TrainingItem("opponent_clip_study", "对手片段研究", "analysis", "全队/分组", 0.02, "light", 2, -2, 0,
    {"dec": 0.40}, {}, is_recovery=True))
_register(TrainingItem("role_meeting", "位置职责会议", "analysis", "分组", 0.02, "light", 2, -2, 0,
    {"dec": 0.40, "com": 0.20}, {}, is_recovery=True))
_register(TrainingItem("captain_meeting", "队长沟通会", "analysis", "全队", 0.01, "light", 2, -2, 0,
    {"com": 0.30}, {}, is_recovery=True))


# ==================== 强度映射 ====================

INTENSITY_LOAD_POINTS = {
    "light": 1,
    "normal": 2,
    "hard": 3,
}


# ==================== 训练套餐模板 ====================

@dataclass
class TrainingTemplate:
    id: str
    name: str
    description: str
    schedule: list[list[str]]  # 7天 x 3时段的训练项ID


TRAINING_TEMPLATES: dict[str, TrainingTemplate] = {}


def _register_template(t: TrainingTemplate) -> None:
    TRAINING_TEMPLATES[t.id] = t


# 标准微周期
_register_template(TrainingTemplate(
    "standard_microcycle",
    "标准微周期",
    "新手默认，攻防、传控、身体和恢复都有覆盖",
    [
        ["rondo_4v2", "first_touch_escape", "mobility_session"],
        ["box_finish_one_touch", "delay_and_channel", "match_review_unit"],
        ["repeat_sprint", "line_breaking_pass", "full_rest"],
        ["build_up_2_3", "central_compactness", "hydro_recovery"],
        ["dribble_cone_tight", "standing_tackle_timing", "role_meeting"],
        ["game_model_8v8", "corner_near_post", "full_rest"],
        ["full_rest", "mobility_session", "opponent_clip_study"],
    ]
))

# 禁区终结周
_register_template(TrainingTemplate(
    "finishing_week",
    "禁区终结周",
    "提升射门、镇定、远射、爆发力，适合进球效率低的球队",
    [
        ["box_finish_one_touch", "near_post_finish", "mobility_session"],
        ["box_finish_under_pressure", "cutback_finish", "match_review_unit"],
        ["weak_foot_finish", "long_shot_window", "full_rest"],
        ["volley_second_ball", "penalty_routine", "hydro_recovery"],
        ["box_finish_one_touch", "penalty_pressure", "role_meeting"],
        ["cutback_finish", "far_post_arrival", "full_rest"],
        ["full_rest", "mobility_session", "opponent_clip_study"],
    ]
))

# 控球出球周
_register_template(TrainingTemplate(
    "possession_week",
    "控球出球周",
    "提升传球、控球、视野、球商，适合中后场控球和出球",
    [
        ["rondo_4v2", "first_touch_escape", "mobility_session"],
        ["third_man_combination", "switch_play", "match_review_unit"],
        ["line_breaking_pass", "back_to_goal_link", "full_rest"],
        ["build_out_under_press", "receiving_scanning", "hydro_recovery"],
        ["wall_pass_timing", "transition_attack", "role_meeting"],
        ["game_model_8v8", "build_up_2_3", "full_rest"],
        ["full_rest", "mobility_session", "opponent_clip_study"],
    ]
))

# 高压反抢周
_register_template(TrainingTemplate(
    "high_press_week",
    "高压反抢周",
    "提升体能、抢断、防守意识、球商、爆发力，强度高",
    [
        ["press_trigger", "counterpress_after_loss", "mobility_session"],
        ["cover_shadow_press", "recovery_run", "match_review_unit"],
        ["repeat_sprint", "change_direction", "full_rest"],
        ["accel_5m", "transition_defense", "hydro_recovery"],
        ["standing_tackle_timing", "delay_and_channel", "role_meeting"],
        ["game_model_8v8", "aerobic_blocks", "full_rest"],
        ["full_rest", "hydro_recovery", "opponent_clip_study"],
    ]
))

# 低位防守周
_register_template(TrainingTemplate(
    "low_block_week",
    "低位防守周",
    "提升防守意识、头球、站位、球商、抢断，适合保守打法",
    [
        ["body_shape_defense", "central_compactness", "mobility_session"],
        ["aerial_duel_defense", "box_marking", "match_review_unit"],
        ["rest_defense", "set_piece_marking", "full_rest"],
        ["delay_and_channel", "recovery_run", "hydro_recovery"],
        ["standing_tackle_timing", "cover_shadow_press", "role_meeting"],
        ["game_model_8v8", "transition_defense", "full_rest"],
        ["full_rest", "mobility_session", "opponent_clip_study"],
    ]
))

# 边路推进周
_register_template(TrainingTemplate(
    "wide_attack_week",
    "边路推进周",
    "提升传中、盘带、速度、爆发力、传球",
    [
        ["cross_low_driven", "one_v_one_wing", "mobility_session"],
        ["cross_early", "touchline_escape", "match_review_unit"],
        ["accel_5m", "wide_overload", "full_rest"],
        ["max_velocity", "carry_into_space", "hydro_recovery"],
        ["dribble_cone_tight", "switch_play", "role_meeting"],
        ["game_model_8v8", "transition_attack", "full_rest"],
        ["full_rest", "mobility_session", "opponent_clip_study"],
    ]
))

# 定位球攻防周
_register_template(TrainingTemplate(
    "set_piece_week",
    "定位球攻防周",
    "围绕任意球、头球、防守意识、站位、球商",
    [
        ["corner_near_post", "corner_far_post", "mobility_session"],
        ["free_kick_direct", "free_kick_routine", "match_review_unit"],
        ["set_piece_marking", "throw_in_pattern", "full_rest"],
        ["corner_near_post", "set_piece_marking", "hydro_recovery"],
        ["free_kick_direct", "throw_in_pattern", "role_meeting"],
        ["game_model_8v8", "free_kick_routine", "full_rest"],
        ["full_rest", "mobility_session", "opponent_clip_study"],
    ]
))

# 点球与门将扑点周
_register_template(TrainingTemplate(
    "penalty_week",
    "点球与门将扑点周",
    "围绕点球、镇定、射门、反应、扑救",
    [
        ["box_finish_one_touch", "penalty_routine", "match_review_unit"],
        ["box_finish_under_pressure", "penalty_pressure", "mobility_session"],
        ["free_kick_direct", "penalty_routine", "role_meeting"],
        ["full_rest", "penalty_pressure", "opponent_clip_study"],
        ["cutback_finish", "box_finish_under_pressure", "mobility_session"],
        ["penalty_pressure", "gk_penalty_read", "full_rest"],
        ["full_rest", "match_review_unit", "full_rest"],
    ]
))

# 基础技术周
_register_template(TrainingTemplate(
    "youth_tech_week",
    "基础技术周",
    "多个低中强度专项轮转，侧重传球、控球和认知培养，恢复充足",
    [
        ["receiving_scanning", "first_touch_escape", "mobility_session"],
        ["rondo_4v2", "third_man_combination", "match_review_unit"],
        ["dribble_cone_tight", "wall_pass_timing", "recovery_bike"],
        ["core_stability", "switch_play", "role_meeting"],
        ["line_breaking_pass", "receive_on_half_turn", "hydro_recovery"],
        ["game_model_8v8", "build_up_2_3", "full_rest"],
        ["full_rest", "mobility_session", "captain_meeting"],
    ]
))

# 密集赛程恢复周
_register_template(TrainingTemplate(
    "recovery_week",
    "密集赛程恢复周",
    "多恢复和低强度认知课，适合连续比赛后调整",
    [
        ["full_rest", "hydro_recovery", "mobility_session"],
        ["recovery_bike", "match_review_unit", "opponent_clip_study"],
        ["individual_treatment", "role_meeting", "full_rest"],
        ["mobility_session", "captain_meeting", "hydro_recovery"],
        ["full_rest", "opponent_clip_study", "recovery_bike"],
        ["match_review_unit", "mobility_session", "full_rest"],
        ["full_rest", "hydro_recovery", "individual_treatment"],
    ]
))


# ==================== 便捷查询函数 ====================

def get_training_item(item_id: str) -> Optional[TrainingItem]:
    return TRAINING_ITEMS.get(item_id)


def list_training_items(category: str = None, is_recovery: bool = None) -> list[TrainingItem]:
    items = list(TRAINING_ITEMS.values())
    if category:
        items = [i for i in items if i.category == category]
    if is_recovery is not None:
        items = [i for i in items if i.is_recovery == is_recovery]
    return items


def get_training_categories() -> list[str]:
    return sorted({i.category for i in TRAINING_ITEMS.values()})


def get_template(template_id: str) -> Optional[TrainingTemplate]:
    return TRAINING_TEMPLATES.get(template_id)


def list_templates() -> list[TrainingTemplate]:
    return list(TRAINING_TEMPLATES.values())
