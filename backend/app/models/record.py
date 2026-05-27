"""
Record model - 纪录系统核心模型
存储比赛级、赛季级和生涯级的各类纪录
"""
from enum import Enum as PyEnum
from datetime import date

from sqlalchemy import String, ForeignKey, Enum, JSON, DECIMAL, UniqueConstraint, Integer, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RecordScope(str, PyEnum):
    """纪录范围/维度"""
    WORLD = "world"      # 世界纪录（全服）
    LEAGUE = "league"    # 联赛纪录（scope_target_id = league_id）
    TEAM = "team"        # 队伍纪录（scope_target_id = team_id）


class RecordCategory(str, PyEnum):
    """纪录分类"""
    TEAM = "team"        # 球队纪录
    PLAYER = "player"    # 球员纪录
    MATCH = "match"      # 比赛纪录


class RecordType(str, PyEnum):
    """纪录类型 - 完整清单"""
    # --- 球员纪录 ---
    CAREER_GOALS = "career_goals"                    # 生涯总进球最多
    CAREER_ASSISTS = "career_assists"                # 生涯总助攻最多
    CAREER_APPEARANCES = "career_appearances"        # 生涯出场最多
    CAREER_YELLOW_CARDS = "career_yellow_cards"      # 生涯黄牌最多
    CAREER_RED_CARDS = "career_red_cards"            # 生涯红牌最多
    CAREER_RATING = "career_rating"                  # 生涯最高场均评分(min 50场)
    
    SEASON_GOALS = "season_goals"                    # 单赛季进球最多
    SEASON_ASSISTS = "season_assists"                # 单赛季助攻最多
    SEASON_RATING = "season_rating"                  # 单赛季最高场均评分(min 10场)
    
    MATCH_GOALS = "match_goals"                      # 单场进球最多
    MATCH_ASSISTS = "match_assists"                  # 单场助攻最多
    FASTEST_GOAL = "fastest_goal"                    # 最快进球 (秒)
    YOUNGEST_SCORER = "youngest_scorer"              # 最年轻进球者
    OLDEST_SCORER = "oldest_scorer"                  # 最年长进球者
    HAT_TRICKS = "hat_tricks"                        # 帽子戏法次数
    SCORING_STREAK = "scoring_streak"                # 连续进球场次
    ASSIST_STREAK = "assist_streak"                  # 连续助攻场次
    
    # --- 球队纪录 ---
    SEASON_TEAM_GOALS = "season_team_goals"          # 单赛季球队进球最多
    SEASON_TEAM_GOALS_AGAINST = "season_team_goals_against"  # 单赛季失球最少
    SEASON_TEAM_POINTS = "season_team_points"        # 单赛季积分最高
    SEASON_TEAM_WINS = "season_team_wins"            # 单赛季胜场最多
    SEASON_CLEAN_SHEETS = "season_clean_sheets"      # 单赛季零封最多
    
    BIGGEST_WIN_MARGIN = "biggest_win_margin"        # 最大比分胜利
    BIGGEST_DEFEAT_MARGIN = "biggest_defeat_margin"  # 最大比分失利
    MOST_GOALS_IN_MATCH = "most_goals_in_match"      # 单场总进球最多
    LONGEST_WIN_STREAK = "longest_win_streak"        # 最长连胜
    LONGEST_UNBEATEN = "longest_unbeaten"            # 最长不败
    LONGEST_LOSING_STREAK = "longest_losing_streak"  # 最长连败


# 纪录类型 → 中文标签映射
RECORD_TYPE_LABELS: dict[RecordType, str] = {
    RecordType.CAREER_GOALS: "生涯总进球最多",
    RecordType.CAREER_ASSISTS: "生涯总助攻最多",
    RecordType.CAREER_APPEARANCES: "生涯出场最多",
    RecordType.CAREER_YELLOW_CARDS: "生涯黄牌最多",
    RecordType.CAREER_RED_CARDS: "生涯红牌最多",
    RecordType.CAREER_RATING: "生涯最高场均评分",
    RecordType.SEASON_GOALS: "单赛季进球最多",
    RecordType.SEASON_ASSISTS: "单赛季助攻最多",
    RecordType.SEASON_RATING: "单赛季最高场均评分",
    RecordType.MATCH_GOALS: "单场进球最多",
    RecordType.MATCH_ASSISTS: "单场助攻最多",
    RecordType.FASTEST_GOAL: "最快进球",
    RecordType.YOUNGEST_SCORER: "最年轻进球者",
    RecordType.OLDEST_SCORER: "最年长进球者",
    RecordType.HAT_TRICKS: "帽子戏法次数",
    RecordType.SCORING_STREAK: "连续进球场次",
    RecordType.ASSIST_STREAK: "连续助攻场次",
    RecordType.SEASON_TEAM_GOALS: "单赛季进球最多",
    RecordType.SEASON_TEAM_GOALS_AGAINST: "单赛季失球最少",
    RecordType.SEASON_TEAM_POINTS: "单赛季积分最高",
    RecordType.SEASON_TEAM_WINS: "单赛季胜场最多",
    RecordType.SEASON_CLEAN_SHEETS: "单赛季零封最多",
    RecordType.BIGGEST_WIN_MARGIN: "最大比分胜利",
    RecordType.BIGGEST_DEFEAT_MARGIN: "最大比分失利",
    RecordType.MOST_GOALS_IN_MATCH: "单场总进球最多",
    RecordType.LONGEST_WIN_STREAK: "最长连胜",
    RecordType.LONGEST_UNBEATEN: "最长不败",
    RecordType.LONGEST_LOSING_STREAK: "最长连败",
}


# 数值越小越好的纪录类型（需要特殊排序逻辑）
RECORD_TYPES_LOWER_IS_BETTER: set[RecordType] = {
    RecordType.FASTEST_GOAL,
    RecordType.YOUNGEST_SCORER,
    RecordType.SEASON_TEAM_GOALS_AGAINST,
}


class Record(Base):
    """纪录表 - 存储各类历史纪录
    
    设计说明:
    - 同 scope + scope_target_id + record_type 只能有一条当前纪录
    - record_value 为字符串展示值，record_value_numeric 用于排序比较
    - 对于"越小越好"的纪录，record_value_numeric 存储为负数，统一使用"越大越好"的比较逻辑
    """
    __tablename__ = "records"
    
    __table_args__ = (
        UniqueConstraint(
            "scope", "scope_target_id", "record_type",
            name="uix_record_scope_type"
        ),
    )
    
    # 纪录维度
    scope: Mapped[RecordScope] = mapped_column(
        Enum(RecordScope), nullable=False, index=True
    )
    scope_target_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True,
        comment="WORLD=null, LEAGUE=league_id, TEAM=team_id"
    )
    
    # 分类与类型
    category: Mapped[RecordCategory] = mapped_column(
        Enum(RecordCategory), nullable=False, index=True
    )
    record_type: Mapped[RecordType] = mapped_column(
        Enum(RecordType), nullable=False, index=True
    )
    
    # 纪录保持者
    holder_player_id: Mapped[str | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    holder_team_id: Mapped[str | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    
    # 纪录数值
    record_value: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="展示值，如 '34球', '11秒'"
    )
    record_value_numeric: Mapped[float] = mapped_column(
        DECIMAL(12, 2), nullable=False, index=True,
        comment="用于排序比较的数值，统一越大越好"
    )
    
    # 创造背景
    season_id: Mapped[str | None] = mapped_column(
        ForeignKey("seasons.id", ondelete="SET NULL"),
        nullable=True
    )
    fixture_id: Mapped[str | None] = mapped_column(
        ForeignKey("fixtures.id", ondelete="SET NULL"),
        nullable=True
    )
    match_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    
    # 额外上下文 JSON
    context: Mapped[dict] = mapped_column(
        JSON, default=dict, nullable=False,
        comment="额外信息，如 streak 起止日期等"
    )
    
    # 关联关系
    holder_player: Mapped["Player | None"] = relationship("Player", foreign_keys=[holder_player_id])
    holder_team: Mapped["Team | None"] = relationship("Team", foreign_keys=[holder_team_id])
    season: Mapped["Season | None"] = relationship("Season")
    fixture: Mapped["Fixture | None"] = relationship("Fixture")
