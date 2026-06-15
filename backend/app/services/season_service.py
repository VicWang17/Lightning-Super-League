"""
Season service - 赛季业务逻辑服务
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update

from app.models.season import Season, SeasonStatus, Fixture, FixtureType, FixtureStatus, CupCompetition
from app.models.league import League, LeagueSystem, LeagueStanding
from app.models.team import Team, TeamStatus
from app.models.user import User
from app.services.scheduler import SeasonScheduler, ScheduleMerger
from app.core.formats import get_default_format
from app.core.clock import clock
from app.core.events import EventQueue, GameEvent, EventType, EventStatus
from app.services.match_simulator import MatchSimulator
from app.services.match_engine_client import (
    MatchEngineUnavailableError,
    get_match_engine_client,
)
from app.services.cup_progression import CupProgressionService
from app.services.promotion_service import PromotionService
from app.services.notification_service import NotificationService
from app.core.logging import get_logger

logger = get_logger(__name__)


class SeasonService:
    """赛季服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.scheduler = SeasonScheduler(db)
        self.simulator = MatchSimulator()
        self.cup_progression = CupProgressionService(db)
        self.promotion_service = PromotionService(db)
        self.notify = NotificationService(db)

    async def get_current_season(self, zone_id: int = 1) -> Optional[Season]:
        """获取当前赛季（优先进行中，其次待开始）"""
        result = await self.db.execute(
            select(Season)
            .where(Season.status.in_([SeasonStatus.ONGOING, SeasonStatus.PENDING]))
            .where(Season.zone_id == zone_id)
            .order_by(Season.season_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_season_by_number(self, season_number: int, zone_id: int = 1) -> Optional[Season]:
        """根据赛季编号获取赛季"""
        result = await self.db.execute(
            select(Season)
            .where(Season.season_number == season_number)
            .where(Season.zone_id == zone_id)
        )
        return result.scalar_one_or_none()

    async def create_new_season(self, start_date: Optional[datetime] = None, zone_id: int = 1) -> Season:
        """创建新赛季

        Args:
            start_date: 赛季开始日期，默认明天
            zone_id: 所属大区ID，默认1区
        """
        from sqlalchemy.orm import selectinload

        # 获取上一个赛季编号
        result = await self.db.execute(
            select(Season).order_by(Season.season_number.desc()).limit(1)
        )
        last_season = result.scalar_one_or_none()
        next_season_number = (last_season.season_number + 1) if last_season else 1

        # 默认明天开始
        if start_date is None:
            start_date = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # 获取指定大区的联赛
        result = await self.db.execute(
            select(League)
            .join(League.system)
            .where(LeagueSystem.zone_id == zone_id)
            .options(selectinload(League.system))
        )
        leagues = result.scalars().all()

        # 获取每个联赛的球队
        teams_by_league: Dict[str, List[Team]] = {}
        for league in leagues:
            result = await self.db.execute(
                select(Team).where(Team.current_league_id == league.id)
            )
            teams = result.scalars().all()
            teams_by_league[league.id] = list(teams)

        # 创建赛季和赛程
        season = await self.scheduler.create_season(
            season_number=next_season_number,
            start_date=start_date,
            leagues=list(leagues),
            teams_by_league=teams_by_league
        )

        # 生成并写入 EventQueue 事件序列
        await self._seed_season_events(season, start_date)

        return season

    async def start_season(self, season: Season) -> None:
        """启动赛季"""
        if season.status != SeasonStatus.PENDING:
            raise ValueError(f"Cannot start season with status: {season.status}")

        await self.scheduler.start_season(season)

    # =================================================================
    # 事件驱动核心（Phase 3）
    # =================================================================

    async def _seed_season_events(self, season: Season, start_date: datetime) -> None:
        """为赛季生成完整的 EventQueue 事件序列"""
        fmt = get_default_format()
        template = fmt.season

        events = EventQueue.build_season_events(
            season_id=season.id,
            league_days=list(template.league_days),
            cup_days=list(template.lightning_cup_days),
            promotion_day=template.promotion_day,
            total_days=season.total_days,
            start_date=start_date,
            wage_days=list(template.wage_days),
        )
        await EventQueue.push_many(self.db, events)

    async def process_next_event(self, now: Optional[datetime] = None) -> Optional[Dict]:
        """处理下一个事件（事件驱动核心入口）

        1. 从 EventQueue pop 一个 PENDING 事件
        2. 根据 event_type 分发到对应处理器
        3. 处理完成后标记为 COMPLETED（或 FAILED）
        """
        event = await EventQueue.pop(self.db, now=now or clock.now())
        if not event:
            return None

        event_id = event.id
        try:
            result = await self._dispatch_event(event)
            await EventQueue.complete(self.db, event_id)
            return result
        except Exception as e:
            from app.core.logging import get_logger
            _logger = get_logger(__name__)
            _logger.error(f"Event processing failed: event_id={event_id}, error={str(e)}", exc_info=True)
            await self.db.rollback()
            await EventQueue.fail(self.db, event_id, str(e))
            raise

    async def _dispatch_event(self, event: GameEvent) -> Dict:
        """根据事件类型分发处理"""
        if event.event_type == EventType.SEASON_START:
            return await self._handle_season_start(event)
        elif event.event_type == EventType.MATCH_DAY:
            return await self._handle_match_day(event)
        elif event.event_type == EventType.CUP_PROGRESSION:
            return await self._handle_cup_progression(event)
        elif event.event_type == EventType.PROMOTION_RELEGATION:
            return await self._handle_promotion_relegation(event)
        elif event.event_type == EventType.SEASON_END:
            return await self._handle_season_end(event)
        elif event.event_type == EventType.SEASON_FINANCE_INITIALIZED:
            return await self._handle_season_finance_initialized(event)
        elif event.event_type == EventType.MATCH_FINANCE_SETTLED:
            return await self._handle_match_finance_settled(event)
        elif event.event_type == EventType.WAGES_PAID:
            return await self._handle_wages_paid(event)
        elif event.event_type == EventType.SEASON_FINANCE_CLOSED:
            return await self._handle_season_finance_closed(event)
        elif event.event_type == EventType.BUDGET_WINDOW_OPENED:
            return await self._handle_budget_window_opened(event)
        elif event.event_type == EventType.BUDGET_WINDOW_CLOSED:
            return await self._handle_budget_window_closed(event)
        # Training day
        elif event.event_type == EventType.TRAINING_DAY:
            return await self._handle_training_day(event)
        # Phase 3/4/5: 青训、选秀、AI 管理事件
        elif event.event_type == EventType.YOUTH_REFRESH:
            return await self._handle_youth_refresh(event)
        elif event.event_type == EventType.YOUTH_TRAINING:
            return await self._handle_youth_training(event)
        # 选秀事件已移除（简化闭环设计）
        elif event.event_type in (EventType.DRAFT_PREFERENCES_OPEN, EventType.DRAFT_RUN, EventType.DRAFT_SIGNING_EXPIRE):
            return {"event": event.event_type.value, "status": "deprecated"}
        # Transfer market events
        elif event.event_type == EventType.TRANSFER_OFFER_EXPIRES:
            return await self._handle_transfer_offer_expires(event)
        elif event.event_type == EventType.TRANSFER_LISTING_DEADLINE:
            return await self._handle_transfer_listing_deadline(event)
        elif event.event_type == EventType.AI_TRANSFER_MARKET_SCAN:
            return await self._handle_ai_transfer_market_scan(event)
        elif event.event_type == EventType.AI_TRANSFER_OFFER_RESPONSE:
            return await self._handle_ai_transfer_offer_response(event)
        # Phase 7: 邮件提醒事件
        elif event.event_type == EventType.MATCH_PREVIEW_REMINDER:
            return await self._handle_match_preview_reminder(event)
        elif event.event_type == EventType.TACTICS_REMINDER:
            return await self._handle_tactics_reminder(event)
        elif event.event_type == EventType.TRAINING_REMINDER:
            return await self._handle_training_reminder(event)
        else:
            raise ValueError(f"Unknown event type: {event.event_type}")

    # =====================================================================
    # Phase 7: 邮件提醒事件处理器
    # =====================================================================

    async def _handle_match_preview_reminder(self, event: GameEvent) -> Dict:
        """MATCH_PREVIEW_REMINDER: 早上发送比赛预告提醒"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)

        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season_id)
            .where(Fixture.season_day == day)
            .where(Fixture.status == FixtureStatus.SCHEDULED)
        )
        fixtures = list(result.scalars().all())

        team_names = {}
        team_ids = set()
        for fixture in fixtures:
            team_ids.add(fixture.home_team_id)
            team_ids.add(fixture.away_team_id)
        if team_ids:
            from app.models.team import Team
            teams_result = await self.db.execute(
                select(Team.id, Team.name).where(Team.id.in_(list(team_ids)))
            )
            for tid, tname in teams_result.all():
                team_names[tid] = tname

        for fixture in fixtures:
            home_name = team_names.get(fixture.home_team_id, "主场球队")
            away_name = team_names.get(fixture.away_team_id, "客场球队")
            round_info = f"第 {fixture.round_number} 轮"
            fixture_type_map = {
                FixtureType.LEAGUE.value: "联赛",
                FixtureType.CUP_LIGHTNING_GROUP.value: "闪电杯小组赛",
                FixtureType.CUP_LIGHTNING_KNOCKOUT.value: "闪电杯淘汰赛",
                FixtureType.CUP_JENNY.value: "杰尼杯",
                FixtureType.PLAYOFF.value: "附加赛",
            }
            fixture_type_name = fixture_type_map.get(fixture.fixture_type.value, fixture.fixture_type.value)

            await self.notify.send_match_preview(
                team_id=fixture.home_team_id,
                season_id=season_id,
                fixture_id=fixture.id,
                opponent_name=away_name,
                is_home=True,
                fixture_type=fixture_type_name,
                round_info=round_info,
                day=day,
            )
            await self.notify.send_match_preview(
                team_id=fixture.away_team_id,
                season_id=season_id,
                fixture_id=fixture.id,
                opponent_name=home_name,
                is_home=False,
                fixture_type=fixture_type_name,
                round_info=round_info,
                day=day,
            )

        await self.db.flush()
        return {"event": "match_preview_reminder", "season_id": season_id, "day": day, "fixtures": len(fixtures)}

    async def _handle_tactics_reminder(self, event: GameEvent) -> Dict:
        """TACTICS_REMINDER: 中午发送战术设置提醒"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)

        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season_id)
            .where(Fixture.season_day == day)
            .where(Fixture.status == FixtureStatus.SCHEDULED)
        )
        fixtures = list(result.scalars().all())

        team_names = {}
        team_ids = set()
        for fixture in fixtures:
            team_ids.add(fixture.home_team_id)
            team_ids.add(fixture.away_team_id)
        if team_ids:
            from app.models.team import Team
            teams_result = await self.db.execute(
                select(Team.id, Team.name).where(Team.id.in_(list(team_ids)))
            )
            for tid, tname in teams_result.all():
                team_names[tid] = tname

        for fixture in fixtures:
            home_name = team_names.get(fixture.home_team_id, "主场球队")
            away_name = team_names.get(fixture.away_team_id, "客场球队")
            await self.notify.send_tactics_reminder(
                team_id=fixture.home_team_id,
                season_id=season_id,
                fixture_id=fixture.id,
                opponent_name=away_name,
                is_home=True,
            )
            await self.notify.send_tactics_reminder(
                team_id=fixture.away_team_id,
                season_id=season_id,
                fixture_id=fixture.id,
                opponent_name=home_name,
                is_home=False,
            )

        await self.db.flush()
        return {"event": "tactics_reminder", "season_id": season_id, "day": day, "fixtures": len(fixtures)}

    async def _handle_training_reminder(self, event: GameEvent) -> Dict:
        """TRAINING_REMINDER: 早上发送训练提醒"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)

        result = await self.db.execute(
            select(Team, User)
            .join(User, Team.user_id == User.id)
            .where(Team.status == TeamStatus.ACTIVE)
            .where(User.is_ai == False)
        )
        human_teams = list(result.scalars().all())

        for team in human_teams:
            await self.notify.send_default_training_reminder(
                team_id=team.id,
                season_id=season_id,
                day=day,
            )

        await self.db.flush()
        return {"event": "training_reminder", "season_id": season_id, "day": day, "teams": len(human_teams)}

    async def _handle_budget_window_opened(self, event: GameEvent) -> Dict:
        """BUDGET_WINDOW_OPENED: 打开预算窗口"""
        season_id = event.payload.get("season_id")
        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)
        result = await finance_service.open_budget_window(season_id)
        await self.db.commit()
        return {"event": "budget_window_opened", **result}

    async def _handle_budget_window_closed(self, event: GameEvent) -> Dict:
        """BUDGET_WINDOW_CLOSED: 关闭预算窗口"""
        season_id = event.payload.get("season_id")
        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)
        result = await finance_service.close_budget_window(season_id)
        await self.db.commit()
        return {"event": "budget_window_closed", **result}

    # =====================================================================
    # Phase 3: 青训事件
    # =====================================================================

    async def _handle_youth_refresh(self, event: GameEvent) -> Dict:
        """YOUTH_REFRESH: 青训刷新 + AI 决策"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 1)
        from app.services.youth_academy_service import YouthAcademyService
        service = YouthAcademyService(self.db)
        result = await service.refresh_academy_players(season_id, day)

        # AI 青训决策
        from app.services.ai_team_management_service import AITeamManagementService
        ai_service = AITeamManagementService(self.db)
        ai_result = await ai_service.run_midseason_academy_decisions(season_id, day)

        await self.db.commit()
        return {"event": "youth_refresh", "refresh": result, "ai": ai_result}

    async def _handle_youth_training(self, event: GameEvent) -> Dict:
        """YOUTH_TRAINING: 青训训练"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 1)
        from app.services.youth_academy_service import YouthAcademyService
        service = YouthAcademyService(self.db)
        result = await service.train_academy_players(season_id, day)
        await self.db.commit()
        return {"event": "youth_training", **result}

    async def _handle_training_day(self, event: GameEvent) -> Dict:
        """TRAINING_DAY: 为所有球队生成并结算当天训练"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)

        result = await self.db.execute(select(Season).where(Season.id == season_id))
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        from app.models.team import Team, TeamStatus
        from app.models.user import User
        from app.models.training import TrainingCreatedBy
        from app.services.ai_training_planner import AITrainingPlanner
        from app.services.training_service import TrainingService

        teams_result = await self.db.execute(
            select(Team, User)
            .join(User, Team.user_id == User.id)
            .where(Team.status == TeamStatus.ACTIVE)
        )
        teams = list(teams_result.all())

        planner = AITrainingPlanner(self.db)
        training_service = TrainingService(self.db)

        # 1. 为所有球队生成当天训练计划（AI / 人类默认）
        team_ids = []
        human_team_ids = []
        for team, user in teams:
            is_ai = user.is_ai if user else False
            try:
                if is_ai:
                    plan_items = await planner.generate_daily_plan(team.id, season_id, day)
                else:
                    plan_items = await planner.generate_default_plan(team.id, season_id, day)
                    human_team_ids.append(team.id)
                await training_service.save_training_plan(
                    team.id, season_id, plan_items, TrainingCreatedBy.DEFAULT
                )
                team_ids.append(team.id)
            except Exception as e:
                logger.warning(f"训练计划生成失败: team={team.id}, day={day}, error={e}")

        # 2. 批量结算（一次性加载所有数据，避免 N×M 次查询）
        total_sessions = 0
        total_breakthroughs = 0
        total_declines = 0
        training_injuries = 0
        training_injuries_minor = 0
        training_injuries_medium = 0
        training_injuries_major = 0
        injured_players = []
        recovery_summary = {"players_processed": 0, "injury_recovered": 0}
        if team_ids:
            try:
                summary = await training_service.bulk_complete_training_day(
                    season_id, day, season.season_number, team_ids
                )
                total_sessions = summary.get("sessions_completed", 0)
                total_breakthroughs = summary.get("total_breakthroughs", 0)
                total_declines = summary.get("total_declines", 0)
                training_injuries = summary.get("training_injuries", 0)
                training_injuries_minor = summary.get("training_injuries_minor", 0)
                training_injuries_medium = summary.get("training_injuries_medium", 0)
                training_injuries_major = summary.get("training_injuries_major", 0)
                injured_players = summary.get("injured_players", [])
            except Exception as e:
                logger.warning(f"批量训练结算失败: day={day}, error={e}")
            recovery_summary = await self._apply_training_day_recovery(season_id, day, team_ids)

        # 3. 发送训练相关邮件（仅人类球队）
        for team_id in human_team_ids:
            await self.notify.send_training_summary(
                team_id=team_id,
                season_id=season_id,
                day=day,
                sessions_completed=total_sessions // max(len(team_ids), 1),
                breakthroughs=total_breakthroughs,
                declines=total_declines,
                injuries=training_injuries,
            )
            await self.notify.send_default_training_reminder(team_id, season_id, day)

        for inj in injured_players:
            await self.notify.send_training_injury(
                team_id=inj["team_id"],
                season_id=season_id,
                player_name=inj["player_name"],
                player_id=inj["player_id"],
                injury_name=inj["injury_name"],
                severity=inj["severity"],
                days=inj["days"],
            )

        await self.db.commit()

        return {
            "event": "training_day",
            "season_id": season_id,
            "season_day": day,
            "teams_processed": len(team_ids),
            "sessions_completed": total_sessions,
            "total_breakthroughs": total_breakthroughs,
            "total_declines": total_declines,
            "training_injuries": training_injuries,
            "training_injuries_minor": training_injuries_minor,
            "training_injuries_medium": training_injuries_medium,
            "training_injuries_major": training_injuries_major,
            "recovery": recovery_summary,
        }

    async def _apply_training_day_recovery(self, season_id: str, day: int, team_ids: list[str]) -> Dict:
        """Apply end-of-day recovery after training has been completed."""
        from app.core.training_config import get_training_item
        from app.models.player import Player, PlayerStatus
        from app.models.training import TeamTrainingPlan, TrainingPlanStatus
        from app.services.player_fatigue_service import PlayerFatigueService

        plans_result = await self.db.execute(
            select(TeamTrainingPlan).where(
                and_(
                    TeamTrainingPlan.season_id == season_id,
                    TeamTrainingPlan.season_day == day,
                    TeamTrainingPlan.team_id.in_(team_ids),
                    TeamTrainingPlan.status == TrainingPlanStatus.COMPLETED,
                )
            )
        )
        team_intensities: dict[str, set[str]] = {}
        for plan in plans_result.scalars().all():
            item = get_training_item(plan.training_item_id) if plan.training_item_id else None
            if not item:
                continue
            team_intensities.setdefault(plan.team_id, set()).add(item.intensity)

        players_result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.team_id.in_(team_ids),
                    Player.status.in_([PlayerStatus.ACTIVE, PlayerStatus.INJURED, PlayerStatus.SUSPENDED]),
                )
            )
        )
        fatigue_service = PlayerFatigueService()
        summary = {
            "players_processed": 0,
            "injury_recovered": 0,
            "wear_recovered_players": 0,
        }
        for player in players_result.scalars().all():
            intensities = team_intensities.get(player.team_id, set())
            if "hard" in intensities:
                activity_type = "high_intensity_training"
            elif intensities and intensities.issubset({"recovery"}):
                activity_type = "recovery_training"
            elif intensities and intensities.issubset({"light", "recovery"}):
                activity_type = "light_training"
            else:
                activity_type = "normal_training"

            result = fatigue_service.apply_daily_recovery(
                player,
                had_high_intensity_training=activity_type == "high_intensity_training",
                activity_type=activity_type,
            )
            summary["players_processed"] += 1
            if result.get("injury_recovered"):
                summary["injury_recovered"] += 1
            if result.get("wear_recovery"):
                summary["wear_recovered_players"] += 1

        return summary

    async def _apply_rest_day_recovery(
        self,
        excluded_team_ids: set[str] | None = None,
    ) -> Dict:
        """Apply full-rest recovery to active roster players whose teams did not play today."""
        from app.models.player import Player, PlayerStatus
        from app.services.player_fatigue_service import PlayerFatigueService

        excluded_team_ids = excluded_team_ids or set()
        query = select(Player).where(
            Player.status.in_([PlayerStatus.ACTIVE, PlayerStatus.INJURED, PlayerStatus.SUSPENDED]),
            Player.team_id.isnot(None),
        )
        if excluded_team_ids:
            query = query.where(Player.team_id.not_in(excluded_team_ids))

        players = (await self.db.execute(query)).scalars().all()
        fatigue_service = PlayerFatigueService()
        summary = {
            "players_processed": 0,
            "injury_recovered": 0,
            "wear_recovered_players": 0,
        }
        for player in players:
            result = fatigue_service.apply_daily_recovery(player, activity_type="full_rest")
            summary["players_processed"] += 1
            if result.get("injury_recovered"):
                summary["injury_recovered"] += 1
            if result.get("wear_recovery"):
                summary["wear_recovered_players"] += 1
        return summary

    # =====================================================================
    # Phase 4: 选秀事件（已移除）
    # =====================================================================
    # 选秀系统已在简化闭环设计中被移除

    async def _handle_season_start(self, event: GameEvent) -> Dict:
        """SEASON_START: 赛季开始，发送通知并重置球员体力和疲劳"""
        season_id = event.payload.get("season_id")

        # 获取本赛季所有参赛球队
        result = await self.db.execute(
            select(Fixture.home_team_id, Fixture.away_team_id)
            .where(Fixture.season_id == season_id)
            .distinct()
        )
        team_ids = set()
        for row in result.all():
            team_ids.add(row[0])
            team_ids.add(row[1])

        # 重置所有参赛球员的体力和疲劳（休赛期恢复）
        from app.models.player import Player
        if team_ids:
            await self.db.execute(
                update(Player)
                .where(Player.team_id.in_(list(team_ids)))
                .values(fitness=100, fatigue=0)
            )

        season = await self.db.execute(select(Season).where(Season.id == season_id))
        season = season.scalar_one_or_none()
        season_number = season.season_number if season else 1

        # 为所有 AI 球队生成默认战术方案
        from app.services.ai_tactics_advisor import AITacticsAdvisor
        ai_tactics_advisor = AITacticsAdvisor(self.db)
        ai_tactics_result = await ai_tactics_advisor.generate_for_all_ai_teams()

        for team_id in team_ids:
            await self.notify.send_season_start(team_id, season_id, season_number)

        await self.db.commit()
        return {
            "event": "season_start",
            "season_id": season_id,
            "ai_tactics": ai_tactics_result,
        }

    async def _handle_season_finance_initialized(self, event: GameEvent) -> Dict:
        """SEASON_FINANCE_INITIALIZED: 为所有球队初始化赛季财务"""
        season_id = event.payload.get("season_id")

        result = await self.db.execute(select(Season).where(Season.id == season_id))
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)

        # 获取本赛季所有参赛球队
        result = await self.db.execute(
            select(Fixture.home_team_id, Fixture.away_team_id)
            .where(Fixture.season_id == season_id)
            .distinct()
        )
        team_ids = set()
        for row in result.all():
            team_ids.add(row[0])
            team_ids.add(row[1])

        initialized = 0
        for team_id in team_ids:
            try:
                await finance_service.initialize_season_finance(team_id, season_id)
                initialized += 1
            except Exception as e:
                logger.warning(f"赛季财务初始化失败: team={team_id}, error={e}")

        await self.db.commit()
        return {"event": "season_finance_initialized", "season_id": season_id, "teams_initialized": initialized}

    async def _handle_match_finance_settled(self, event: GameEvent) -> Dict:
        """MATCH_FINANCE_SETTLED: 单场财务结算（通常由 MATCH_DAY 自动触发）"""
        fixture_id = event.payload.get("fixture_id")
        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)
        await finance_service.settle_match_finance(fixture_id)
        await self.db.commit()
        return {"event": "match_finance_settled", "fixture_id": fixture_id}

    async def _handle_wages_paid(self, event: GameEvent) -> Dict:
        """WAGES_PAID: 定期工资发放"""
        season_id = event.payload.get("season_id")
        period_key = event.payload.get("period_key", "default")

        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)
        await finance_service.pay_wages(season_id, period_key)
        await self.db.commit()
        return {"event": "wages_paid", "season_id": season_id, "period_key": period_key}

    async def _handle_season_finance_closed(self, event: GameEvent) -> Dict:
        """SEASON_FINANCE_CLOSED: 赛季末财务结算"""
        season_id = event.payload.get("season_id")

        result = await self.db.execute(select(Season).where(Season.id == season_id))
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)
        await finance_service.close_season_finance(season_id)
        await self.db.commit()
        return {"event": "season_finance_closed", "season_id": season_id}

    async def _handle_match_day(self, event: GameEvent) -> Dict:
        """MATCH_DAY: 批量并发模拟当天所有比赛"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)

        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        # 获取当天所有 SCHEDULED 比赛
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season_id)
            .where(Fixture.season_day == day)
            .where(Fixture.status == FixtureStatus.SCHEDULED)
        )
        fixtures = list(result.scalars().all())

        # 预加载球队名称用于赛后结果邮件
        team_names = {}
        team_ids_in_fixtures = set()
        for fixture in fixtures:
            team_ids_in_fixtures.add(fixture.home_team_id)
            team_ids_in_fixtures.add(fixture.away_team_id)
        if team_ids_in_fixtures:
            from app.models.team import Team
            teams_result = await self.db.execute(
                select(Team.id, Team.name).where(Team.id.in_(list(team_ids_in_fixtures)))
            )
            for tid, tname in teams_result.all():
                team_names[tid] = tname

        # Step 1: 将本日比赛显式分层为 ongoing -> finished。
        # TODO(real-time-engine): 这里未来应改为创建 Go engine match sessions，
        # 由引擎按 match_speed tick 推送事件，并接收临场战术/换人命令；
        # Python 后端只负责持久化状态、广播和最终结算回调。
        for fixture in fixtures:
            fixture.status = FixtureStatus.ONGOING
        await self.db.flush()

        # Step 2: 调用 Go 比赛引擎。当前仍是同步最终结果：
        # engine 返回后，比赛立即从 ongoing 落为 finished。
        sim_results = []
        try:
            sim_results = await self._simulate_fixtures_with_engine(fixtures)
        except Exception:
            for fixture in fixtures:
                if fixture.status == FixtureStatus.ONGOING:
                    fixture.status = FixtureStatus.SCHEDULED
            await self.db.flush()
            raise

        # Step 3: 串行 apply_result（避免 standings 共享状态竞争）
        match_results = []
        match_injury_counts = {1: 0, 2: 0, 3: 0}
        for fixture, sim_result in zip(fixtures, sim_results):
            await self.simulator.apply_result(fixture, sim_result, self.db)
            fixture_injury_counts = {1: 0, 2: 0, 3: 0}
            for player_stat in sim_result.player_stats or []:
                severity = int(player_stat.get("injury_severity", 0) or 0)
                if severity in fixture_injury_counts:
                    fixture_injury_counts[severity] += 1
                    match_injury_counts[severity] += 1
            # 收集比赛结果邮件数据
            goals = []
            yellow_cards = 0
            red_cards = 0
            mvp_name = None
            injuries = []
            if sim_result.events:
                for evt in sim_result.events:
                    if evt.get("type") == "GOAL":
                        goals.append({
                            "minute": evt.get("minute", 0),
                            "player_name": evt.get("player_name", "未知"),
                        })
                    elif evt.get("type") == "YELLOW_CARD":
                        yellow_cards += 1
                    elif evt.get("type") == "RED_CARD":
                        red_cards += 1
            if sim_result.player_stats:
                for ps in sim_result.player_stats:
                    if ps.get("is_mvp"):
                        mvp_name = ps.get("player_name", "未知")
                    severity = int(ps.get("injury_severity", 0) or 0)
                    if severity > 0:
                        injuries.append({
                            "player_name": ps.get("player_name", "未知"),
                            "injury_name": ps.get("injury_name", "受伤"),
                            "days": ps.get("injury_days", 3),
                        })

            home_name = team_names.get(fixture.home_team_id, "主场球队")
            away_name = team_names.get(fixture.away_team_id, "客场球队")

            await self.notify.send_match_result(
                team_id=fixture.home_team_id,
                season_id=season_id,
                fixture_id=fixture.id,
                opponent_name=away_name,
                is_home=True,
                home_score=sim_result.home_score,
                away_score=sim_result.away_score,
                fixture_type=fixture.fixture_type.value,
                goals=goals,
                yellow_cards=yellow_cards,
                red_cards=red_cards,
                mvp_name=mvp_name,
                injuries=injuries,
            )
            await self.notify.send_match_result(
                team_id=fixture.away_team_id,
                season_id=season_id,
                fixture_id=fixture.id,
                opponent_name=home_name,
                is_home=False,
                home_score=sim_result.home_score,
                away_score=sim_result.away_score,
                fixture_type=fixture.fixture_type.value,
                goals=goals,
                yellow_cards=yellow_cards,
                red_cards=red_cards,
                mvp_name=mvp_name,
                injuries=injuries,
            )

            match_results.append({
                "fixture_id": fixture.id,
                "type": fixture.fixture_type.value,
                "home_team": fixture.home_team_id,
                "away_team": fixture.away_team_id,
                "home_score": sim_result.home_score,
                "away_score": sim_result.away_score,
                "match_setup": (sim_result.engine_raw or {}).get("match_setup") if sim_result.engine_raw else None,
                "match_injuries": sum(fixture_injury_counts.values()),
                "match_injuries_minor": fixture_injury_counts[1],
                "match_injuries_medium": fixture_injury_counts[2],
                "match_injuries_major": fixture_injury_counts[3],
            })

        # 更新赛季状态（复用 scheduler.process_matchday 的逻辑，但不重复 commit）
        season.current_day = day
        fmt = get_default_format()
        template = fmt.season
        league_days = list(template.league_days)
        if day in league_days:
            season.current_league_round = league_days.index(day) + 1
        cup_days = list(template.lightning_cup_days)
        if day in cup_days:
            season.current_cup_round = cup_days.index(day) + 1
        
        # 尽早 commit 赛季状态，减少锁持有时间，避免与财务结算死锁
        await self.db.commit()

        # Phase 2: 比赛财务结算
        from app.services.finance_service import FinanceService
        finance_service = FinanceService(self.db)
        for fixture in fixtures:
            if fixture.status == FixtureStatus.FINISHED:
                try:
                    await finance_service.settle_match_finance(fixture.id)
                except Exception as e:
                    logger.warning(f"比赛财务结算失败: fixture={fixture.id}, error={e}")

        match_team_ids = {
            team_id
            for fixture in fixtures
            for team_id in (fixture.home_team_id, fixture.away_team_id)
            if team_id
        }
        rest_recovery = await self._apply_rest_day_recovery(excluded_team_ids=match_team_ids)

        await self.db.commit()

        return {
            "event": "match_day",
            "season_id": season_id,
            "season_day": day,
            "fixtures_processed": len(match_results),
            "results": match_results,
            "match_injuries": sum(match_injury_counts.values()),
            "match_injuries_minor": match_injury_counts[1],
            "match_injuries_medium": match_injury_counts[2],
            "match_injuries_major": match_injury_counts[3],
            "rest_recovery": rest_recovery,
        }

    async def _simulate_fixtures_with_engine(self, fixtures: list[Fixture]):
        """Run fixtures through the authoritative Go match engine."""
        from app.config import get_settings

        settings = get_settings()
        client = get_match_engine_client()
        try:
            engine_results = await client.simulate_fixtures(self.db, fixtures)
            return [
                MatchSimulator.from_engine_result(fixture, engine_result)
                for fixture, engine_result in zip(fixtures, engine_results)
            ]
        except MatchEngineUnavailableError:
            if settings.MATCH_ENGINE_FALLBACK_RANDOM:
                return [await self.simulator.simulate(fixture) for fixture in fixtures]
            raise

    async def _simulate_with_engine(self, fixture: Fixture):
        """Run one fixture through the authoritative Go match engine."""
        from app.config import get_settings

        settings = get_settings()
        client = get_match_engine_client()
        try:
            engine_result = await client.simulate_fixture(self.db, fixture)
            return MatchSimulator.from_engine_result(fixture, engine_result)
        except MatchEngineUnavailableError:
            if settings.MATCH_ENGINE_FALLBACK_RANDOM:
                return await self.simulator.simulate(fixture)
            raise

    async def _handle_cup_progression(self, event: GameEvent) -> Dict:
        """CUP_PROGRESSION: 处理杯赛晋级"""
        season_id = event.payload.get("season_id")
        after_day = event.payload.get("after_day", 0)

        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        progression = await self._process_cup_progression(season, after_day)
        await self.db.commit()
        return {
            "event": "cup_progression",
            "season_id": season_id,
            "after_day": after_day,
            "results": progression,
        }

    async def _handle_promotion_relegation(self, event: GameEvent) -> Dict:
        """PROMOTION_RELEGATION: 处理升降级"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)

        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        promotion = await self._process_promotion_relegation(season, day)
        await self.db.commit()
        return {
            "event": "promotion_relegation",
            "season_id": season_id,
            "day": day,
            "results": promotion,
        }

    async def _handle_season_end(self, event: GameEvent) -> Dict:
        """SEASON_END: 赛季结算

        处理顺序：
        1. 赛季末名单闭环（退役、合同到期、自动补员）
        2. 标记赛季结束
        3. 创建并启动下赛季
        """
        season_id = event.payload.get("season_id")

        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")

        # Phase 5: AI 赛季末决策（续约、签青训、签自由市场）
        from app.services.ai_team_management_service import AITeamManagementService
        ai_service = AITeamManagementService(self.db)
        ai_result = await ai_service.run_season_end_roster_decisions(season_id)

        # Phase 2: 赛季末名单闭环（退役、合同到期、选秀、自动补员）
        from app.services.roster_lifecycle_service import RosterLifecycleService
        roster_service = RosterLifecycleService(self.db)
        roster_result = await roster_service.close_season(season_id)

        season.current_day = season.total_days
        end_date_raw = event.payload.get("end_date")
        end_date = datetime.fromisoformat(end_date_raw) if end_date_raw else event.scheduled_at

        season.status = SeasonStatus.FINISHED
        season.end_date = end_date
        await self.db.commit()

        # 授予联赛冠军荣誉
        from app.services.honor_service import HonorService
        honor_service = HonorService(self.db)
        # 查询所有联赛的最终积分榜冠军
        league_champions_result = await self.db.execute(
            select(LeagueStanding, League)
            .join(League, LeagueStanding.league_id == League.id)
            .where(LeagueStanding.season_id == season_id)
            .where(LeagueStanding.position == 1)
        )
        for standing, league in league_champions_result.all():
            await honor_service.award_league_champion(
                team_id=standing.team_id,
                season_id=season_id,
                league_id=league.id,
                league_name=league.name,
                league_level=league.level,
            )
        await self.db.commit()

        # 发送赛季结束通知
        result = await self.db.execute(
            select(Fixture.home_team_id, Fixture.away_team_id)
            .where(Fixture.season_id == season_id)
            .distinct()
        )
        team_ids = set()
        for row in result.all():
            team_ids.add(row[0])
            team_ids.add(row[1])
        for team_id in team_ids:
            await self.notify.send_season_end(team_id, season_id, season.season_number)

        next_start = (end_date + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        next_season = await self.create_new_season(start_date=next_start, zone_id=season.zone_id)
        await self.start_season(next_season)

        return {
            "event": "season_end",
            "season_id": season_id,
            "season_number": season.season_number,
            "next_season_id": next_season.id,
            "next_season_number": next_season.season_number,
            "ai_roster": ai_result,
            "roster_lifecycle": roster_result,
        }

    async def process_next_day(self, season: Season) -> Dict:
        """处理下一天的比赛（兼容接口，内部使用事件驱动）

        不断处理事件，直到遇到一个 MATCH_DAY 或 SEASON_END 为止。
        如果赛季已结束，自动创建并切换到新赛季。
        """
        if season.status == SeasonStatus.FINISHED:
            print(f"\n  🔄 第{season.season_number}赛季已结束，自动创建新赛季...")
            new_season = await self.create_new_season(zone_id=season.zone_id)
            await self.start_season(new_season)
            print(f"  ✅ 第{new_season.season_number}赛季已启动！\n")
            return await self.process_next_day(new_season)

        if season.status != SeasonStatus.ONGOING:
            raise ValueError(f"Season is not ongoing: {season.status}")

        # 处理事件直到遇到 MATCH_DAY 或 SEASON_END
        while True:
            result = await self.process_next_event()
            if result is None:
                # 没有更多事件
                return {"season_day": season.current_day, "fixtures_processed": 0, "results": [], "cup_progression": {}}

            if result.get("event") in ("match_day", "season_end"):
                return result

    async def run_until_next_event(self, season: Season, max_events: int = 100) -> List[Dict]:
        """运行时钟直到下一个需要暂停的事件（用于 step/turbo 模式）

        在 step 模式下：处理到下一个 MATCH_DAY 或 SEASON_END 停止
        在 turbo 模式下：连续处理所有到期事件直到队列为空
        """
        results: List[Dict] = []
        for _ in range(max_events):
            result = await self.process_next_event()
            if result is None:
                break
            results.append(result)
            if result.get("event") in ("match_day", "season_end"):
                break
        return results

    async def fast_forward(self, target_day: int, season: Season) -> List[Dict]:
        """快进赛季到指定天数（用于测试/调试）

        不断处理事件直到 season.current_day >= target_day。
        """
        results: List[Dict] = []
        while season.current_day < target_day and season.status == SeasonStatus.ONGOING:
            batch = await self.run_until_next_event(season, max_events=50)
            if not batch:
                break
            results.extend(batch)
            # refresh season state
            await self.db.refresh(season)
        return results

    async def _process_cup_progression(self, season: Season, day: int) -> Dict:
        """
        处理杯赛晋级逻辑

        杯赛日期: Day 6,9,12,15,18,21,24,27
        - Day 12: 闪电杯小组赛结束，生成32强对阵
        - Day 15: 杰尼杯第1轮结束，生成第2轮（128进64）
        """
        from app.models.season import CupCompetition

        fmt = get_default_format()
        cup_days = list(fmt.season.cup_progression_days)

        if day not in cup_days:
            return {}

        results = {}

        # 获取所有杯赛
        result = await self.db.execute(
            select(CupCompetition).where(CupCompetition.season_id == season.id)
        )
        competitions = result.scalars().all()

        for comp in competitions:
            if comp.code == "LIGHTNING_CUP":
                # 闪电杯晋级处理
                if day == 8:  # 小组赛结束，生成16强（day 10比赛）
                    count = await self.cup_progression.fill_lightning_cup_knockout_fixtures(comp, season)
                    results["lightning_cup"] = f"Generated {count} ROUND_16 fixtures"
                elif day == 10:  # 16强结束，生成8强（day 12比赛）
                    count = await self.cup_progression.fill_next_knockout_round(comp, season, "ROUND_16")
                    results["lightning_cup_quarter"] = f"Generated {count} QUARTER fixtures"
                elif day == 12:  # 8强结束，生成半决赛（day 14比赛）
                    count = await self.cup_progression.fill_next_knockout_round(comp, season, "QUARTER")
                    results["lightning_cup_semi"] = f"Generated {count} SEMI fixtures"
                elif day == 14:  # 半决赛结束，生成决赛（day 21比赛）
                    count = await self.cup_progression.fill_next_knockout_round(comp, season, "SEMI")
                    results["lightning_cup_final"] = f"Generated {count} FINAL fixtures"
                elif day == 21:  # 决赛已结束，设置冠军
                    winner = await self._get_cup_winner(comp)
                    if winner:
                        comp.winner_team_id = winner
                        results["lightning_cup_winner"] = f"Winner set: {winner}"
                        # 授予杯赛冠军荣誉
                        from app.services.honor_service import HonorService
                        honor_service = HonorService(self.db)
                        await honor_service.award_cup_champion(
                            team_id=winner,
                            season_id=season.id,
                            cup_competition_id=comp.id,
                            cup_name=comp.name,
                        )

            elif comp.code.startswith("JENNY_CUP_"):
                # 杰尼杯晋级处理（JENNY_CUP_EAST, JENNY_CUP_NORTH, JENNY_CUP_SOUTH, JENNY_CUP_WEST）
                jenny_cup_days = list(fmt.season.jenny_cup_days)
                system_code = comp.code.replace('JENNY_CUP_', '')
                if day == jenny_cup_days[0]:  # 预选赛结束，生成32强
                    tier2_teams = await self._get_jenny_cup_tier2_teams(system_code, season)
                    count = await self.cup_progression.fill_jenny_cup_round_2(comp, season, tier2_teams)
                    results[f"jenny_cup_{system_code.lower()}"] = f"Generated {count} ROUND_32 fixtures"
                elif day == jenny_cup_days[1]:  # 32强结束，生成16强
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 2)
                    results[f"jenny_cup_{system_code.lower()}_16"] = f"Generated {count} ROUND_16 fixtures"
                elif day == jenny_cup_days[2]:  # 16强结束，生成8强
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 3)
                    results[f"jenny_cup_{system_code.lower()}_quarter"] = f"Generated {count} QUARTER fixtures"
                elif day == jenny_cup_days[3]:  # 8强结束，生成半决赛
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 4)
                    results[f"jenny_cup_{system_code.lower()}_semi"] = f"Generated {count} SEMI fixtures"
                elif day == jenny_cup_days[4]:  # 半决赛结束，生成决赛
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 5)
                    results[f"jenny_cup_{system_code.lower()}_final"] = f"Generated {count} FINAL fixtures"
                elif day == jenny_cup_days[5]:  # 决赛结束，设置冠军
                    winner = await self._get_cup_winner(comp)
                    if winner:
                        comp.winner_team_id = winner
                        results[f"jenny_cup_{system_code.lower()}_winner"] = f"Winner set: {winner}"
                        # 授予杯赛冠军荣誉
                        from app.services.honor_service import HonorService
                        honor_service = HonorService(self.db)
                        await honor_service.award_cup_champion(
                            team_id=winner,
                            season_id=season.id,
                            cup_competition_id=comp.id,
                            cup_name=comp.name,
                        )

        return results

    async def _get_cup_winner(self, competition: CupCompetition) -> Optional[str]:
        """
        获取杯赛冠军（决赛胜者）
        """
        from app.models.match_result import MatchResult as EngineMatchResult

        # 获取决赛比赛
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_competition_id == competition.id,
                    Fixture.cup_stage == "FINAL",
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        final = result.scalar_one_or_none()

        if not final:
            return None

        engine_result = await self.db.execute(
            select(EngineMatchResult).where(EngineMatchResult.fixture_id == final.id)
        )
        persisted = engine_result.scalar_one_or_none()
        if persisted and persisted.winner_team_id:
            return persisted.winner_team_id

        # 返回胜者
        if final.home_score > final.away_score:
            return final.home_team_id
        elif final.away_score > final.home_score:
            return final.away_team_id
        else:
            # 平局按主队晋级（或可以实现点球规则）
            return final.home_team_id

    async def _get_jenny_cup_tier2_teams(self, system_code: str, season: Season) -> List[str]:
        """
        获取杰尼杯次级联赛种子球队（该体系Level 2联赛的8支球队）
        从该赛季的联赛赛程中获取，而不是依赖 Team.current_league_id
        """
        from app.models.league import LeagueSystem

        # 获取该体系的次级联赛（Level 2）
        result = await self.db.execute(
            select(League).join(LeagueSystem).where(
                and_(
                    LeagueSystem.code == system_code,
                    League.level == 2
                )
            )
        )
        tier2_league = result.scalar_one_or_none()

        if not tier2_league:
            return []

        # 从该赛季的联赛赛程中获取球队（而不是依赖 current_league_id）
        # 查询该联赛在本赛季的所有联赛赛程（LEAGUE类型的比赛）
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.LEAGUE,
                    Fixture.league_id == tier2_league.id
                )
            )
        )
        fixtures = result.scalars().all()

        # 从赛程中提取所有参与过的球队ID（去重）
        team_ids = set()
        for f in fixtures:
            team_ids.add(f.home_team_id)
            team_ids.add(f.away_team_id)

        return list(team_ids)

    async def get_today_fixtures(self, season: Season) -> List[Fixture]:
        """获取今天（当前天）的所有比赛"""
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.season_day == season.current_day)
        )
        return list(result.scalars().all())

    async def get_team_fixtures(
        self,
        season: Season,
        team_id: str,
        fixture_type: Optional[FixtureType] = None
    ) -> List[Fixture]:
        """获取某支球队在赛季中的所有比赛"""
        query = select(Fixture).where(
            and_(
                Fixture.season_id == season.id,
                (Fixture.home_team_id == team_id) | (Fixture.away_team_id == team_id)
            )
        )

        if fixture_type:
            query = query.where(Fixture.fixture_type == fixture_type)

        query = query.order_by(Fixture.season_day)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_season_calendar(
        self,
        season: Season,
        team_id: Optional[str] = None
    ) -> List[Dict]:
        """获取赛季日历（按天组织的赛程）"""
        # 获取所有相关比赛
        query = select(Fixture).where(Fixture.season_id == season.id)

        if team_id:
            query = query.where(
                (Fixture.home_team_id == team_id) | (Fixture.away_team_id == team_id)
            )

        query = query.order_by(Fixture.season_day, Fixture.scheduled_at)
        result = await self.db.execute(query)
        fixtures = result.scalars().all()

        # 获取所有相关球队信息
        team_ids = set()
        for fixture in fixtures:
            team_ids.add(fixture.home_team_id)
            team_ids.add(fixture.away_team_id)

        # 批量获取球队名称
        teams_map = {}
        if team_ids:
            result = await self.db.execute(select(Team).where(Team.id.in_(team_ids)))
            teams = result.scalars().all()
            teams_map = {t.id: t.name for t in teams}

        # 按天分组
        calendar = {}
        for fixture in fixtures:
            day = fixture.season_day
            if day not in calendar:
                calendar[day] = {
                    "day": day,
                    "date": fixture.scheduled_at.strftime("%Y-%m-%d"),
                    "fixtures": []
                }

            calendar[day]["fixtures"].append({
                "id": fixture.id,
                "type": fixture.fixture_type.value,
                "round": fixture.round_number,
                "home_team_id": fixture.home_team_id,
                "away_team_id": fixture.away_team_id,
                "home_team_name": teams_map.get(fixture.home_team_id, "未知球队"),
                "away_team_name": teams_map.get(fixture.away_team_id, "未知球队"),
                "home_score": fixture.home_score,
                "away_score": fixture.away_score,
                "status": fixture.status.value,
                "cup_stage": fixture.cup_stage,
                "cup_group": fixture.cup_group_name,
            })

        return [calendar[day] for day in sorted(calendar.keys())]

    async def _process_promotion_relegation(self, season: Season, day: int) -> Dict:
        """
        处理升降级和附加赛

        Day 21: 闪电杯决赛结束，处理赛季结束，计算升降级并创建附加赛
        Day 22: 附加赛预选赛 (Day 1)
        Day 23: 附加赛决赛 (Day 2)，应用最终升降级
        Day 24-25: 休赛期
        """
        results = {}
        fmt = get_default_format()
        template = fmt.season
        final_day = template.lightning_cup_days[-1] if template.lightning_cup_days else 21
        preliminary_day = template.playoff_days[0] if template.playoff_days else 22
        final_playoff_day = template.playoff_days[1] if len(template.playoff_days) > 1 else preliminary_day + 1
        movement_day = template.promotion_day

        if day == final_day:
            # 闪电杯决赛结束，赛季正式结束，计算升降级并创建附加赛
            print(f"\n  📊 闪电杯决赛结束，处理赛季结束，计算升降级...")
            promotion_data = await self.promotion_service.process_season_end(season)

            # 创建附加赛赛程
            if promotion_data['playoff_teams']:
                playoff_fixtures = await self.promotion_service.create_playoff_fixtures(
                    season, promotion_data['playoff_teams']
                )
                results['playoff_fixtures_created'] = len(playoff_fixtures)
                print(f"  📝 创建附加赛: {len(playoff_fixtures)} 场")

            # 显示直升/直降信息
            auto_up = len(promotion_data['auto_promotions'])
            auto_down = len(promotion_data['auto_relegations'])
            results['auto_promotions'] = auto_up
            results['auto_relegations'] = auto_down
            print(f"  ⬆️ 直升: {auto_up} 队")
            print(f"  ⬇️ 直降: {auto_down} 队")

        elif day == preliminary_day:
            # 附加赛预选赛日，比赛由主循环模拟
            # 预选赛后创建Day 23的决赛对阵
            playoff_fixtures = await self._create_playoff_finals(season)
            if playoff_fixtures:
                results['playoff_finals_created'] = len(playoff_fixtures)
                print(f"  📝 创建附加赛决赛: {len(playoff_fixtures)} 场")

        elif day == movement_day:
            # Day 24 休赛期，统一处理所有升降级
            print(f"\n  📊 处理赛季升降级...")

            # 事件处理会重新从数据库加载 Season；不要依赖前序事件的内存属性。
            # 直升/直降只依赖最终积分榜，可在实际应用变更前安全重算。
            promotion_data = await self.promotion_service.process_season_end(season)

            # 处理附加赛结果，确定最终升降级名单
            final_results = await self._process_playoff_results(
                season, promotion_data
            )

            # 应用球队位置变更
            await self.promotion_service.apply_team_movements(
                final_results['final_promotions'],
                final_results['final_relegations']
            )

            results['final_promotions'] = len(final_results['final_promotions'])
            results['final_relegations'] = len(final_results['final_relegations'])
            print(f"  ✅ 升降级完成: {results['final_promotions']} 升级, {results['final_relegations']} 降级")

        return results

    async def _create_playoff_finals(self, season: Season) -> List[Fixture]:
        """
        根据Day 22预选赛结果创建Day 23决赛

        每个体系需要创建：
        1. L1第7 vs L2第2（1场）- 已在playoff_teams中
        2. L2第6 vs L3预赛胜者（1场）
        3. L3A第6 vs L4A-B预赛胜者（1场）
        4. L3B第6 vs L4C-D预赛胜者（1场）
        共4场/体系 × 4体系 = 16场
        """
        from app.models.league import LeagueSystem, LeagueStanding

        fixtures = []
        template = get_default_format().season
        preliminary_day = template.playoff_days[0] if template.playoff_days else 22
        final_playoff_day = template.playoff_days[1] if len(template.playoff_days) > 1 else preliminary_day + 1

        # 获取附加赛预选赛结果
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.PLAYOFF,
                    Fixture.season_day == preliminary_day,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        day22_fixtures = result.scalars().all()

        # 建立预选赛胜者映射 {体系名_类型: 胜者ID}
        winners = {}
        for f in day22_fixtures:
            stage = f.cup_stage or ""
            winner_id = f.home_team_id if f.home_score > f.away_score else f.away_team_id
            if f.home_score == f.away_score:
                winner_id = f.home_team_id

            # 从 cup_stage 提取体系名（格式: P_L3亚军预赛-东区 或 P_L4A-L4B亚军预赛-东区）
            if "L3亚军预赛-" in stage:
                system = stage.split("-")[-1]  # 取最后一部分（体系名）
                winners[f"{system}_L3"] = winner_id
            elif "L4A-L4B亚军预赛-" in stage:
                system = stage.split("-")[-1]
                winners[f"{system}_L4AB"] = winner_id
            elif "L4C-L4D亚军预赛-" in stage:
                system = stage.split("-")[-1]
                winners[f"{system}_L4CD"] = winner_id

        final_date = season.start_date + timedelta(days=final_playoff_day - 1)
        final_kickoff = final_date.replace(hour=template.kickoff_hour, minute=0, second=0)

        # 获取升降级数据（包含L1-L2决赛对阵）
        promotion_data = getattr(season, '_promotion_data', {})
        playoff_teams = promotion_data.get('playoff_teams', {})

        # 1. 创建L1-L2决赛（4场）
        for match_name, (home_id, away_id) in playoff_teams.items():
            if "-L3" not in match_name and "-L4" not in match_name and "亚军预赛" not in match_name:
                if home_id and away_id:  # 确保不是占位符
                    short_name = match_name.replace("联赛", "").replace("附加赛", "")
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=final_playoff_day,
                        scheduled_at=final_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_{short_name[:15]}",
                        home_team_id=home_id,
                        away_team_id=away_id,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)

        # 2. 查询所有体系，创建L2-L3和L3-L4决赛
        systems_result = await self.db.execute(select(LeagueSystem))
        systems = systems_result.scalars().all()

        for system in systems:
            # 获取该体系的所有联赛
            leagues_result = await self.db.execute(
                select(League).where(League.system_id == system.id)
            )
            leagues = leagues_result.scalars().all()

            l1 = next((l for l in leagues if l.level == 1), None)
            l2 = next((l for l in leagues if l.level == 2), None)
            l3_leagues = [l for l in leagues if l.level == 3]
            l4_leagues = [l for l in leagues if l.level == 4]

            if not l1 or not l2 or len(l3_leagues) < 2 or len(l4_leagues) < 4:
                continue

            l3a, l3b = sorted(l3_leagues, key=lambda x: x.name)[:2]
            l4a, l4b, l4c, l4d = sorted(l4_leagues, key=lambda x: x.name)[:4]

            # 获取积分榜
            l2_standings = await self._get_league_standings(l2.id, season.id)
            l3a_standings = await self._get_league_standings(l3a.id, season.id)
            l3b_standings = await self._get_league_standings(l3b.id, season.id)

            sys_name = system.name  # 使用中文名（东区、西区等）

            # 创建L2-L3决赛：L2倒数第(relegation_spots+1)名 vs L3预赛胜者
            l2_playoff_idx = -(l2.relegation_spots + 1) if l2.relegation_spots > 0 else None
            l3_key = f"{sys_name}_L3"
            l3_winner = winners.get(l3_key)
            if l2_playoff_idx is not None and len(l2_standings) >= abs(l2_playoff_idx) and l3_winner:
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=final_playoff_day,
                        scheduled_at=final_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_L2L3_{system.code[:8]}",
                        home_team_id=l2_standings[l2_playoff_idx].team_id,
                        away_team_id=l3_winner,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)

            # 创建L3-L4决赛1：L3A倒数第(relegation_spots+1)名 vs L4A-B预赛胜者
            l3a_playoff_idx = -(l3a.relegation_spots + 1) if l3a.relegation_spots > 0 else None
            l4ab_key = f"{sys_name}_L4AB"
            l4ab_winner = winners.get(l4ab_key)
            if l3a_playoff_idx is not None and len(l3a_standings) >= abs(l3a_playoff_idx) and l4ab_winner:
                if l4ab_winner:
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=final_playoff_day,
                        scheduled_at=final_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_L3AL4_{system.code[:8]}",
                        home_team_id=l3a_standings[l3a_playoff_idx].team_id,
                        away_team_id=l4ab_winner,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)

            # 创建L3-L4决赛2：L3B倒数第(relegation_spots+1)名 vs L4C-D预赛胜者
            l3b_playoff_idx = -(l3b.relegation_spots + 1) if l3b.relegation_spots > 0 else None
            l4cd_key = f"{sys_name}_L4CD"
            l4cd_winner = winners.get(l4cd_key)
            if l3b_playoff_idx is not None and len(l3b_standings) >= abs(l3b_playoff_idx) and l4cd_winner:
                if l4cd_winner:
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=final_playoff_day,
                        scheduled_at=final_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_L3BL4_{system.code[:8]}",
                        home_team_id=l3b_standings[l3b_playoff_idx].team_id,
                        away_team_id=l4cd_winner,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)

        await self.db.commit()
        return fixtures

    async def _get_league_standings(self, league_id: str, season_id: str):
        """获取联赛积分榜"""
        from app.models.league import LeagueStanding
        result = await self.db.execute(
            select(LeagueStanding).where(
                and_(
                    LeagueStanding.league_id == league_id,
                    LeagueStanding.season_id == season_id
                )
            ).order_by(LeagueStanding.position)
        )
        return list(result.scalars().all())

    async def _process_playoff_results(
        self,
        season: Season,
        promotion_data: Dict
    ) -> Dict[str, List]:
        """
        处理附加赛结果，确定最终升降级名单

        附加赛规则：
        - L1-L2: L1第7 vs L2第2，胜者升级/保级，败者降级/留级
        - L2-L3: L2第6 vs L3预赛胜者，胜者升级/保级，败者降级/留级
        - L3-L4: L3第6 vs L4预赛胜者，胜者升级/保级，败者降级/留级
        """
        auto_promotions = list(promotion_data.get('auto_promotions', []))
        auto_relegations = list(promotion_data.get('auto_relegations', []))

        #  playoff_promotions 和 playoff_relegations 用于存储附加赛产生的升降级
        playoff_promotions = []
        playoff_relegations = []

        template = get_default_format().season
        final_playoff_day = template.playoff_days[1] if len(template.playoff_days) > 1 else 23

        # 获取附加赛决赛结果
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.PLAYOFF,
                    Fixture.season_day == final_playoff_day,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        day23_fixtures = result.scalars().all()

        # 获取所有联赛信息
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(League).options(selectinload(League.system))
        )
        leagues = {l.id: l for l in result.scalars().all()}

        # 获取所有球队信息
        result = await self.db.execute(select(Team))
        teams = {t.id: t for t in result.scalars().all()}

        # 建立联赛层级映射 {league_id: level}
        league_levels = {l.id: l.level for l in leagues.values()}

        for fixture in day23_fixtures:
            # 确定胜者
            if fixture.home_score > fixture.away_score:
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            elif fixture.away_score > fixture.home_score:
                winner_id = fixture.away_team_id
                loser_id = fixture.home_team_id
            else:
                # 平局按主队获胜
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id

            winner_team = teams.get(winner_id)
            loser_team = teams.get(loser_id)

            if not winner_team or not loser_team:
                continue

            # 根据球队当前所在联赛层级确定升降级
            winner_level = league_levels.get(winner_team.current_league_id, 0)
            loser_level = league_levels.get(loser_team.current_league_id, 0)

            stage = fixture.cup_stage or ""

            # L1-L2附加赛: L1第7(主队, level=1) vs L2第2(客队, level=2)
            # L2第2胜则升级, L1第7败则降级
            if "L1-L2" in stage or "超级-甲级" in stage or "超级联赛-甲级联赛" in stage:
                # L2球队(低级别)获胜 -> 升级
                if winner_level > loser_level:  # winner是L2球队
                    # 找到L1联赛(需要知道是哪个L1)
                    l1_league = next((l for l in leagues.values() if l.level == 1 and loser_team.current_league_id == l.id), None)
                    l2_league = next((l for l in leagues.values() if l.level == 2 and winner_team.current_league_id == l.id), None)
                    if l1_league and l2_league:
                        playoff_promotions.append((winner_id, l2_league.id, l1_league.id))
                        playoff_relegations.append((loser_id, l1_league.id, l2_league.id))
                else:  # L1球队获胜，保级成功，不需要额外处理
                    pass

            # L2-L3附加赛: L2第6(主队, level=2) vs L3预赛胜者(客队, level=3)
            # L3球队获胜 -> 升级, L2第6败则降级
            elif "L2L3" in stage:
                if winner_level > loser_level:  # winner是L3球队
                    l2_league = next((l for l in leagues.values() if l.level == 2 and loser_team.current_league_id == l.id), None)
                    l3_league = next((l for l in leagues.values() if l.level == 3 and winner_team.current_league_id == l.id), None)
                    if l2_league and l3_league:
                        playoff_promotions.append((winner_id, l3_league.id, l2_league.id))
                        playoff_relegations.append((loser_id, l2_league.id, l3_league.id))

            # L3-L4附加赛: L3第6(主队, level=3) vs L4预赛胜者(客队, level=4)
            # L4球队获胜 -> 升级, L3第6败则降级
            elif "L3AL4" in stage or "L3BL4" in stage:
                if winner_level > loser_level:  # winner是L4球队
                    l3_league = next((l for l in leagues.values() if l.level == 3 and loser_team.current_league_id == l.id), None)
                    l4_league = next((l for l in leagues.values() if l.level == 4 and winner_team.current_league_id == l.id), None)
                    if l3_league and l4_league:
                        playoff_promotions.append((winner_id, l4_league.id, l3_league.id))
                        playoff_relegations.append((loser_id, l3_league.id, l4_league.id))

        # 合并所有升降级
        final_promotions = auto_promotions + playoff_promotions
        final_relegations = auto_relegations + playoff_relegations

        return {
            'final_promotions': final_promotions,
            'final_relegations': final_relegations,
            'playoff_promotions': playoff_promotions,
            'playoff_relegations': playoff_relegations
        }

    # =====================================================================
    # Transfer market event handlers
    # =====================================================================

    async def _handle_transfer_offer_expires(self, event: GameEvent) -> Dict:
        """TRANSFER_OFFER_EXPIRES: 处理过期报价"""
        from app.services.transfer_service import TransferService
        transfer_service = TransferService(self.db)
        stats = await transfer_service.process_expired_offers()
        return {"event": "transfer_offer_expires", "stats": stats}

    async def _handle_transfer_listing_deadline(self, event: GameEvent) -> Dict:
        """TRANSFER_LISTING_DEADLINE: 处理挂牌等待期截止"""
        from app.services.transfer_service import TransferService
        transfer_service = TransferService(self.db)
        stats = await transfer_service.process_listing_deadlines()
        return {"event": "transfer_listing_deadline", "stats": stats}

    async def _handle_ai_transfer_market_scan(self, event: GameEvent) -> Dict:
        """AI_TRANSFER_MARKET_SCAN: AI 每日转会市场扫描"""
        from app.services.ai_transfer_service import AITransferService
        ai_service = AITransferService(self.db)
        stats = await ai_service.run_ai_transfer_market_scan()
        return {"event": "ai_transfer_market_scan", "stats": stats}

    async def _handle_ai_transfer_offer_response(self, event: GameEvent) -> Dict:
        """AI_TRANSFER_OFFER_RESPONSE: AI 快速响应报价"""
        negotiation_id = event.payload.get("negotiation_id")
        from app.services.ai_transfer_service import AITransferService
        ai_service = AITransferService(self.db)
        await ai_service.run_ai_offer_response(negotiation_id)
        return {"event": "ai_transfer_offer_response", "negotiation_id": negotiation_id}
