"""
Suspension Service - 停赛系统服务

负责赛后纪律判定、停赛应用、场次倒计时与恢复。
完全仿照 InjuryService 的 JSON + Service 模式。
"""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models.player import Player, PlayerStatus
from app.models.player_season_stats import PlayerSeasonStats
from app.models.season import Fixture


# 黄牌累计停赛阈值（本赛季跨赛事累计）
_YELLOW_CARD_SUSPENSION_THRESHOLD = 5

# 红牌停赛场次
_RED_CARD_SUSPENSION_MATCHES = 2


def _flag_json_modified(player: Player, field: str) -> None:
    try:
        flag_modified(player, field)
    except Exception:
        pass


class SuspensionService:
    """停赛服务"""

    # ========================================================================
    # 停赛判定与触发
    # ========================================================================

    @staticmethod
    async def apply_match_discipline(
        player: Player,
        fixture: Fixture,
        yellow_delta: int,
        red_delta: int,
        db: AsyncSession,
    ) -> bool:
        """
        赛后根据本场比赛红黄牌进行纪律判定。

        Returns:
            True 如果触发了新的停赛
        """
        if not player or player.status == PlayerStatus.RETIRED:
            return False

        # 红牌逻辑（直接红牌 / 两黄变一红）
        if red_delta > 0:
            return await SuspensionService._apply_suspension(
                player,
                fixture,
                reason="red_card",
                matches=_RED_CARD_SUSPENSION_MATCHES,
                db=db,
            )

        # 黄牌累计逻辑
        if yellow_delta > 0:
            total_yellows = await SuspensionService._get_season_yellow_cards(
                db, player.id, fixture.season_id
            )
            if total_yellows >= _YELLOW_CARD_SUSPENSION_THRESHOLD:
                # 只有当球员当前不在停赛状态时才触发新的累计黄牌停赛
                if player.current_suspension is None:
                    return await SuspensionService._apply_suspension(
                        player,
                        fixture,
                        reason="yellow_card_accumulation",
                        matches=1,
                        db=db,
                    )

        return False

    @staticmethod
    async def _apply_suspension(
        player: Player,
        fixture: Fixture,
        reason: str,
        matches: int,
        db: AsyncSession,
    ) -> bool:
        """对球员施加停赛"""
        if matches <= 0:
            return False

        player.current_suspension = {
            "reason": reason,
            "matches_remaining": matches,
            "source_fixture_id": str(fixture.id),
            "effective_from_day": fixture.season_day,
            "season_id": str(fixture.season_id),
        }
        _flag_json_modified(player, "current_suspension")

        if player.status != PlayerStatus.SUSPENDED:
            player.status = PlayerStatus.SUSPENDED

        # 发送停赛通知
        from app.services.notification_service import NotificationService
        notify = NotificationService(db)
        reason_text = "红牌" if reason == "red_card" else "黄牌累计"
        await notify.send_player_suspended(
            team_id=player.team_id,
            season_id=str(fixture.season_id),
            player_name=player.name,
            player_id=player.id,
            reason=reason_text,
            matches=matches,
        )
        return True

    @staticmethod
    async def _get_season_yellow_cards(
        db: AsyncSession, player_id: str, season_id: str
    ) -> int:
        """查询球员本赛季跨赛事黄牌累计数"""
        result = await db.execute(
            select(func.coalesce(func.sum(PlayerSeasonStats.yellow_cards), 0)).where(
                PlayerSeasonStats.player_id == player_id,
                PlayerSeasonStats.season_id == season_id,
            )
        )
        return int(result.scalar_one())

    # ========================================================================
    # 停赛倒计时与恢复
    # ========================================================================

    @staticmethod
    def tick_suspension(player: Player) -> bool:
        """
        消耗一场停赛场次。
        在球员所属球队比赛日且该球员未出场时调用。

        Returns:
            True 如果停赛已结束、球员已恢复
        """
        if player.current_suspension is None:
            return False

        remaining = player.current_suspension.get("matches_remaining", 0)
        if remaining <= 1:
            SuspensionService._recover_from_suspension(player)
            return True

        player.current_suspension["matches_remaining"] = remaining - 1
        _flag_json_modified(player, "current_suspension")
        return False

    @staticmethod
    def _recover_from_suspension(player: Player) -> None:
        """停赛恢复处理"""
        player.current_suspension = None
        _flag_json_modified(player, "current_suspension")

        if player.status == PlayerStatus.SUSPENDED:
            player.status = PlayerStatus.ACTIVE

    @staticmethod
    def is_suspended(player: Player) -> bool:
        """判断球员当前是否处于停赛期"""
        return player.current_suspension is not None

    # ========================================================================
    # 赛季级清理
    # ========================================================================

    @staticmethod
    def clear_suspension_for_new_season(player: Player) -> bool:
        """
        赛季切换时强制清空停赛状态。
        Returns True 如果确实清除了停赛。
        """
        if player.current_suspension is not None:
            player.current_suspension = None
            _flag_json_modified(player, "current_suspension")
            if player.status == PlayerStatus.SUSPENDED:
                player.status = PlayerStatus.ACTIVE
            return True
        return False
