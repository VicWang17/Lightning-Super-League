"""
Phase 4: 收件箱决策系统测试

测试覆盖：
  • AI 球队在预算窗口打开时自动确认预算和赞助商
  • 人类球队收到预算/赞助商通知邮件
  • close_budget_window 自动锁定未确认方案并发送邮件
  • 超支状态变化时发送警告邮件
  • 赛季结算时发送财务总结邮件
"""
import pytest
from decimal import Decimal
from sqlalchemy import select

from app.services.finance_service import FinanceService
from app.models.finance import (
    TeamBudgetPlan,
    SponsorContract,
    SponsorContractStatus,
    BudgetPolicy,
    SponsorPolicy,
    FinancialHealth,
    OverspendLevel,
    TeamSeasonFinance,
)
from app.models.team import Team, TeamStatus, TeamFinance
from app.models.season import Season, SeasonStatus, Fixture, FixtureType, FixtureStatus
from app.models.user import User, UserStatus
from app.models.league import League, LeagueSystem
from app.models.mail import Mail, MailCategory


@pytest.mark.asyncio
class TestBudgetWindowAIvsHuman:
    """预算窗口 AI vs Human 决策测试"""

    async def _setup_season_with_teams(self, db, ai_count=1, human_count=1):
        """创建包含 AI 和人类球队的赛季，并生成一场比赛"""
        # 联赛体系
        league_system = LeagueSystem(name="东区", code="EAST", zone_id=1)
        db.add(league_system)
        await db.flush()

        league = League(name="超级联赛", level=1, system_id=league_system.id,
                        promotion_spots=1, relegation_spots=1)
        db.add(league)
        await db.flush()

        season = Season(
            season_number=1,
            zone_id=1,
            status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()

        teams = []
        users = []

        # AI 用户
        for i in range(ai_count):
            user = User(
                username=f"ai_user_{i}",
                email=f"ai{i}@ai.com",
                hashed_password="fake",
                status=UserStatus.ACTIVE,
                is_ai=True,
            )
            db.add(user)
            await db.flush()
            users.append(user)

            team = Team(
                name=f"AI球队{i}",
                status=TeamStatus.ACTIVE,
                user_id=user.id,
                current_league_id=league.id,
                current_season_id=season.id,
            )
            db.add(team)
            await db.flush()
            teams.append(team)

            tf = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
            db.add(tf)

        # 人类用户
        for i in range(human_count):
            user = User(
                username=f"human_user_{i}",
                email=f"human{i}@test.com",
                hashed_password="fake",
                status=UserStatus.ACTIVE,
                is_ai=False,
            )
            db.add(user)
            await db.flush()
            users.append(user)

            team = Team(
                name=f"人类球队{i}",
                status=TeamStatus.ACTIVE,
                user_id=user.id,
                current_league_id=league.id,
                current_season_id=season.id,
            )
            db.add(team)
            await db.flush()
            teams.append(team)

            tf = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
            db.add(tf)

        # 创建一场比赛让所有球队参与（open_budget_window 通过 Fixture 获取球队）
        # 即使只有一支球队也创建一个 fixture（home/away 可以相同，仅用于测试）
        if len(teams) >= 1:
            fixture = Fixture(
                season_id=season.id,
                fixture_type=FixtureType.LEAGUE,
                season_day=1,
                scheduled_at=__import__("datetime").datetime.utcnow(),
                round_number=1,
                home_team_id=teams[0].id,
                away_team_id=teams[1].id if len(teams) >= 2 else teams[0].id,
                status=FixtureStatus.SCHEDULED,
                league_id=league.id,
            )
            db.add(fixture)
            await db.flush()

        return season, teams, users

    async def test_ai_team_auto_confirms_budget_and_sponsor(self, db):
        """AI 球队应自动确认预算并激活赞助商"""
        season, teams, users = await self._setup_season_with_teams(db, ai_count=1, human_count=0)
        ai_team = teams[0]
        service = FinanceService(db)

        result = await service.open_budget_window(season.id)
        await db.flush()

        assert result["ai_auto_decisions"] == 1
        assert result["human_mails_sent"] == 0

        # 验证预算已确认
        budget = await service.get_budget_plan(ai_team.id, season.id)
        assert budget is not None
        assert budget.is_player_confirmed is True
        assert budget.locked_at is not None
        assert budget.policy == BudgetPolicy.BALANCED

        # 验证赞助商已激活
        sponsor = await service._get_active_sponsor_contract(ai_team.id, season.id)
        assert sponsor is not None
        assert sponsor.status == SponsorContractStatus.ACTIVE

    async def test_human_team_receives_budget_mail(self, db):
        """人类球队应收到预算规划邮件"""
        season, teams, users = await self._setup_season_with_teams(db, ai_count=0, human_count=1)
        human_team = teams[0]
        service = FinanceService(db)

        result = await service.open_budget_window(season.id)
        await db.flush()

        assert result["ai_auto_decisions"] == 0
        assert result["human_mails_sent"] == 1

        # 验证邮件已发送
        mail_result = await db.execute(
            select(Mail).where(Mail.team_id == human_team.id).where(Mail.season_id == season.id)
        )
        mails = mail_result.scalars().all()
        assert len(mails) >= 1
        assert mails[0].category == MailCategory.FINANCE
        assert mails[0].has_action is True
        assert "预算" in mails[0].subject

        # 预算未确认（人类需要手动确认）
        budget = await service.get_budget_plan(human_team.id, season.id)
        assert budget is not None
        assert budget.is_player_confirmed is False

        # 赞助商为 PENDING
        sponsor = await service._get_active_sponsor_contract(human_team.id, season.id)
        assert sponsor is not None
        assert sponsor.status == SponsorContractStatus.PENDING

    async def test_close_budget_window_auto_locks_human_teams(self, db):
        """关闭预算窗口时应自动锁定人类球队的默认方案并发送通知"""
        season, teams, users = await self._setup_season_with_teams(db, ai_count=0, human_count=1)
        human_team = teams[0]
        service = FinanceService(db)

        # 先打开窗口
        await service.open_budget_window(season.id)
        await db.flush()

        # 关闭窗口
        result = await service.close_budget_window(season.id)
        await db.flush()

        assert result["budgets_locked"] == 1
        assert result["sponsors_activated"] == 1

        # 预算已锁定
        budget = await service.get_budget_plan(human_team.id, season.id)
        assert budget.locked_at is not None

        # 赞助商已激活
        sponsor = await service._get_active_sponsor_contract(human_team.id, season.id)
        assert sponsor.status == SponsorContractStatus.ACTIVE
        assert sponsor.policy == SponsorPolicy.STABLE

        # 应收到锁定通知邮件
        mail_result = await db.execute(
            select(Mail)
            .where(Mail.team_id == human_team.id)
            .where(Mail.season_id == season.id)
            .where(Mail.subject.contains("锁定"))
        )
        lock_mail = mail_result.scalar_one_or_none()
        assert lock_mail is not None

    async def test_ai_team_does_not_receive_mails(self, db):
        """AI 球队不应收到任何预算相关邮件"""
        season, teams, users = await self._setup_season_with_teams(db, ai_count=1, human_count=0)
        ai_team = teams[0]
        service = FinanceService(db)

        await service.open_budget_window(season.id)
        await service.close_budget_window(season.id)
        await db.flush()

        mail_result = await db.execute(
            select(Mail).where(Mail.team_id == ai_team.id)
        )
        mails = mail_result.scalars().all()
        assert len(mails) == 0


@pytest.mark.asyncio
class TestOverspendNotification:
    """超支警告邮件测试"""

    async def _setup(self, db):
        user = User(
            username="human_user",
            email="human@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
            is_ai=False,
        )
        db.add(user)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id=user.id)
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(team_finance)

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()
        return team, season

    async def test_overspend_warning_mail_sent(self, db):
        """工资支出超过 90% 时应发送警告邮件"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        # 初始化赛季财务
        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("950000.00")  # 95%，超过 90%
        sf.current_balance = Decimal("10000000.00")
        sf.projected_income = Decimal("1000000.00")
        await db.flush()

        await service._check_overspend_and_notify(team.id, season.id)
        await db.flush()

        mail_result = await db.execute(
            select(Mail).where(Mail.team_id == team.id).where(Mail.category == MailCategory.FINANCE)
        )
        mail = mail_result.scalar_one_or_none()
        assert mail is not None
        assert "警告" in mail.subject or "注意" in mail.subject
        assert mail.priority.value in ("normal", "high", "urgent")

    async def test_no_duplicate_overspend_mails(self, db):
        """同一级别超支不应重复发送邮件"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("950000.00")
        sf.current_balance = Decimal("10000000.00")
        sf.projected_income = Decimal("1000000.00")
        await db.flush()

        # 第一次检查
        await service._check_overspend_and_notify(team.id, season.id)
        await db.flush()

        # 第二次检查
        await service._check_overspend_and_notify(team.id, season.id)
        await db.flush()

        mail_result = await db.execute(
            select(Mail).where(Mail.team_id == team.id).where(Mail.category == MailCategory.FINANCE)
        )
        mails = mail_result.scalars().all()
        assert len(mails) == 1

    async def test_ai_team_no_overspend_mail(self, db):
        """AI 球队不应收到超支警告邮件"""
        ai_user = User(
            username="ai_user",
            email="ai@ai.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
            is_ai=True,
        )
        db.add(ai_user)
        await db.flush()

        team = Team(name="AI球队", status=TeamStatus.ACTIVE, user_id=ai_user.id)
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(team_finance)

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()

        service = FinanceService(db)
        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("950000.00")
        sf.current_balance = Decimal("10000000.00")
        sf.projected_income = Decimal("1000000.00")
        await db.flush()

        await service._check_overspend_and_notify(team.id, season.id)
        await db.flush()

        mail_result = await db.execute(select(Mail).where(Mail.team_id == team.id))
        mails = mail_result.scalars().all()
        assert len(mails) == 0


@pytest.mark.asyncio
class TestSeasonSummaryMail:
    """赛季财务总结邮件测试"""

    async def _setup(self, db, is_ai=False):
        user = User(
            username="test_user",
            email="test@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
            is_ai=is_ai,
        )
        db.add(user)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id=user.id)
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(team_finance)

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()
        return team, season

    async def test_season_summary_sent_to_human(self, db):
        """人类球队应收到赛季财务总结"""
        team, season = await self._setup(db, is_ai=False)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.financial_health = FinancialHealth.B
        sf.current_balance = Decimal("11000000.00")
        sf.opening_balance = Decimal("10000000.00")
        await db.flush()

        stats = {
            "total_income": Decimal("2000000.00"),
            "total_expense": Decimal("1000000.00"),
        }
        await service._send_season_summary_mail(team.id, season.id, sf, stats)
        await db.flush()

        mail_result = await db.execute(
            select(Mail).where(Mail.team_id == team.id).where(Mail.category == MailCategory.FINANCE)
        )
        mail = mail_result.scalar_one_or_none()
        assert mail is not None
        assert "赛季财务总结" in mail.subject
        assert "B 级" in mail.body

    async def test_season_summary_not_sent_to_ai(self, db):
        """AI 球队不应收到赛季财务总结"""
        team, season = await self._setup(db, is_ai=True)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        stats = {"total_income": Decimal("0"), "total_expense": Decimal("0")}
        await service._send_season_summary_mail(team.id, season.id, sf, stats)
        await db.flush()

        mail_result = await db.execute(select(Mail).where(Mail.team_id == team.id))
        mails = mail_result.scalars().all()
        assert len(mails) == 0


@pytest.mark.asyncio
class TestAIDecisionAlgorithm:
    """AI 决策算法测试"""

    async def test_ai_with_good_health_may_choose_performance(self, db):
        """财务健康良好的 AI 有概率选择绩效赞助商（概率性测试，多次运行提高置信度）"""
        # 由于随机性，我们至少验证 stable 是可能的，且算法不会报错
        user = User(
            username="ai_user",
            email="ai@ai.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
            is_ai=True,
        )
        db.add(user)
        await db.flush()

        team = Team(name="AI球队", status=TeamStatus.ACTIVE, user_id=user.id)
        db.add(team)
        await db.flush()

        tf = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(tf)

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()

        service = FinanceService(db)

        # 预设 A 级健康
        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.financial_health = FinancialHealth.A
        await db.flush()

        # 创建预算和赞助商
        budget = await service._get_or_create_budget_plan(team.id, season.id)
        sponsor = SponsorContract(
            team_id=team.id,
            season_id=season.id,
            policy=SponsorPolicy.STABLE,
            base_amount=Decimal("200000"),
            status=SponsorContractStatus.PENDING,
        )
        db.add(sponsor)
        await db.flush()

        # 多次运行以覆盖概率分支
        policies = set()
        for _ in range(20):
            sponsor.status = SponsorContractStatus.PENDING
            sponsor.policy = SponsorPolicy.STABLE
            sponsor.base_amount = Decimal("200000")
            sponsor.win_bonus = Decimal("0")
            sponsor.draw_bonus = Decimal("0")
            sponsor.max_bonus = Decimal("0")
            await db.flush()

            budget.is_player_confirmed = False
            budget.locked_at = None
            await db.flush()

            await service._auto_ai_budget_decision(team.id, season.id)
            await db.flush()

            policies.add(sponsor.policy)

        # 应该至少看到过 stable，performance 可能出现也可能不出现
        assert SponsorPolicy.STABLE in policies
        # 预算始终是 balanced
        assert budget.policy == BudgetPolicy.BALANCED
        assert budget.is_player_confirmed is True
