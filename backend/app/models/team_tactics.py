"""
Team tactics model - 球队战术方案表

保存球队的默认战术方案：阵型、首发、替补、战术滑条、定位球、换人规则。
V1 只支持球队默认方案，赛前临时方案（match_plans）放到后续迭代。
"""
from datetime import datetime

from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class TeamTactics(Base):
    """Team tactics model - 球队战术方案表

    说明：
    - 与 teams 表一对一关系
    - 人类玩家和 AI 球队共用同一张表
    - 赛季初始化时为 AI 球队生成默认方案
    """

    __tablename__ = "team_tactics"

    team_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # 阵型 F01-F08
    formation_id: Mapped[str] = mapped_column(String(8), nullable=False, default="F01")

    # 首发 8 人 + 替补 5 人的 player_id 列表
    lineup_player_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    bench_player_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    # 旧 12 字段战术配置（兼容现有 TacticalSetup）
    team_instructions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # 预留字段：定位球、换人规则
    set_piece_instructions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    substitution_rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # AI 画像摘要，用于解释 AI 战术来源（V1 仅记录，不用于引擎逻辑）
    ai_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 关联关系
    team: Mapped["Team"] = relationship("Team")

    def __repr__(self) -> str:
        return f"<TeamTactics(team={self.team_id}, formation={self.formation_id})>"
