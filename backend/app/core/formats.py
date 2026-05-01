"""
League format configuration - 联赛赛制配置中心

把所有写死在业务代码中的赛制参数提取到这里，实现配置驱动。
当前 DEFAULT_FORMAT 完全对应1区（256队）的现有赛制。

未来扩展2区时：
1. 在此文件新增一个 FormatConfig（如 ZONE2_FORMAT）
2. 在 LeagueSystem 上绑定对应的 format_code
3. 业务代码无需修改，自动读取新配置运行
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


@dataclass(frozen=True)
class LeagueScheduleConfig:
    """联赛赛程配置"""
    teams_per_league: int = 8
    round_robin_type: str = "double"  # double | single
    # 总轮次（可由 type 推导，但显式配置更安全）
    total_rounds: int = 14
    
    # 积分规则
    points_win: int = 3
    points_draw: int = 1
    points_loss: int = 0


@dataclass(frozen=True)
class CupConfig:
    """杯赛赛制配置"""
    # 闪电杯
    lightning_total_teams: int = 32
    lightning_eligible_levels: Tuple[int, ...] = (1,)
    lightning_has_group_stage: bool = True
    lightning_group_count: int = 8
    lightning_teams_per_group: int = 4
    lightning_group_rounds: int = 3
    lightning_knockout_rounds: int = 4  # 16强, 8强, 半决赛, 决赛
    
    # 杰尼杯
    jenny_eligible_levels: Tuple[int, ...] = (2, 3, 4)
    jenny_has_preliminary: bool = True
    jenny_preliminary_teams: int = 48
    jenny_seed_teams: int = 8
    jenny_seed_level: int = 2
    jenny_total_rounds: int = 6  # 预选赛 + 32强 + 16强 + 8强 + 半决赛 + 决赛


@dataclass(frozen=True)
class SeasonTimelineConfig:
    """赛季时间线模板"""
    total_days: int = 25
    league_days: Tuple[int, ...] = (1, 2, 3, 5, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20)
    lightning_cup_days: Tuple[int, ...] = (4, 6, 8, 10, 12, 14, 21)
    jenny_cup_days: Tuple[int, ...] = (4, 6, 8, 10, 12, 14)
    playoff_days: Tuple[int, ...] = (22, 23)
    promotion_day: int = 24
    offseason_days: Tuple[int, ...] = (25,)
    kickoff_hour: int = 20
    
    @property
    def cup_progression_days(self) -> Tuple[int, ...]:
        """杯赛晋级处理日（闪电杯+杰尼杯的去重合并）"""
        return tuple(sorted(set(self.lightning_cup_days + self.jenny_cup_days)))


@dataclass(frozen=True)
class PromotionLevelConfig:
    """单个级别的升降级配置"""
    promotion_spots: int = 1          # 直升名额
    relegation_spots: int = 1         # 直降名额
    has_promotion_playoff: bool = True
    has_relegation_playoff: bool = True
    # 附加赛对阵规则描述
    # 格式: {"playoff_type": "cross", "upper_positions": [-2], "lower_positions": [2]}
    playoff_rule: Optional[Dict] = None


@dataclass(frozen=True)
class PromotionConfig:
    """升降级全局配置"""
    # 按联赛级别定义规则 {level: PromotionLevelConfig}
    level_rules: Dict[int, PromotionLevelConfig] = field(default_factory=dict)
    # 跨级别附加赛详情（L1-L2, L2-L3, L3-L4 的具体对阵）
    cross_level_playoffs: Dict[str, Dict] = field(default_factory=dict)


@dataclass(frozen=True)
class SystemStructureConfig:
    """联赛体系结构配置（每个体系内各级联赛数量）"""
    # 各级联赛数量，索引0=level1, 索引1=level2, ...
    levels: Tuple[int, ...] = (1, 1, 2, 4)
    # 体系代码列表
    system_codes: Tuple[str, ...] = ("EAST", "WEST", "SOUTH", "NORTH")
    system_names: Dict[str, str] = field(default_factory=lambda: {
        "EAST": "东区", "WEST": "西区", "SOUTH": "南区", "NORTH": "北区"
    })


@dataclass(frozen=True)
class FormatConfig:
    """完整的赛制配置（一个大区使用一套）"""
    code: str
    name: str
    league: LeagueScheduleConfig
    cup: CupConfig
    season: SeasonTimelineConfig
    promotion: PromotionConfig
    structure: SystemStructureConfig


# ==============================================================================
# 默认配置：对应当前1区（256队，4体系×8联赛×8队）
# ==============================================================================

DEFAULT_PROMOTION = PromotionConfig(
    level_rules={
        1: PromotionLevelConfig(
            promotion_spots=0,
            relegation_spots=1,
            has_promotion_playoff=False,
            has_relegation_playoff=True,
            playoff_rule={"upper_positions": [-2], "lower_positions": [2]}  # L1第7 vs L2第2
        ),
        2: PromotionLevelConfig(
            promotion_spots=1,
            relegation_spots=2,
            has_promotion_playoff=True,
            has_relegation_playoff=False,
            playoff_rule={"upper_positions": [-3], "lower_positions": [2, 2]}  # L2第6 vs L3亚军预赛胜者
        ),
        3: PromotionLevelConfig(
            promotion_spots=1,
            relegation_spots=2,
            has_promotion_playoff=True,
            has_relegation_playoff=False,
            playoff_rule={"upper_positions": [-3], "lower_positions": [2, 2]}  # L3第6 vs L4亚军预赛胜者
        ),
        4: PromotionLevelConfig(
            promotion_spots=1,
            relegation_spots=0,
            has_promotion_playoff=False,
            has_relegation_playoff=False
        ),
    },
    cross_level_playoffs={
        "l1_l2": {"upper_league_count": 1, "lower_league_count": 1, "type": "direct"},
        "l2_l3": {"upper_league_count": 1, "lower_league_count": 2, "type": "preliminary_between_lower"},
        "l3_l4": {"upper_league_count": 2, "lower_league_count": 4, "type": "preliminary_between_lower"},
    }
)

DEFAULT_FORMAT = FormatConfig(
    code="DEFAULT_8",
    name="默认8队双循环赛制",
    league=LeagueScheduleConfig(),
    cup=CupConfig(),
    season=SeasonTimelineConfig(),
    promotion=DEFAULT_PROMOTION,
    structure=SystemStructureConfig()
)

# ==============================================================================
# 配置注册表
# ==============================================================================

_FORMAT_REGISTRY: Dict[str, FormatConfig] = {
    DEFAULT_FORMAT.code: DEFAULT_FORMAT,
}


def register_format(config: FormatConfig) -> None:
    """注册新的赛制配置（用于线上动态扩展）"""
    _FORMAT_REGISTRY[config.code] = config


def get_format(code: str = "DEFAULT_8") -> FormatConfig:
    """获取赛制配置，默认返回1区配置"""
    if code not in _FORMAT_REGISTRY:
        raise ValueError(f"未知的赛制配置: {code}，可用: {list(_FORMAT_REGISTRY.keys())}")
    return _FORMAT_REGISTRY[code]


def get_default_format() -> FormatConfig:
    """获取默认配置（当前1区）"""
    return DEFAULT_FORMAT
