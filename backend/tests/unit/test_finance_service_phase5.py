"""
Phase 5: Transfer/Youth/Contract Coupling 测试

测试覆盖：
  • can_place_transfer_bid — overspend 限制 + 余额检查
  • can_sign_free_player — crisis 限制 + 工资帽检查
  • get_effective_sponsor_base — health/crisis 修正
  • preview_wage_cap_after_signing — 签约预览
  • initialize_season_finance — 扣除 youth_budget
  • open_budget_window — crisis 球队 youth_pct 强制为 5
"""
import pytest
from decimal import Decimal
from sqlalchemy import select

from app.services.finance_service import FinanceService
from app.models.finance import (
    FinanceTransaction,
    TransactionSourceType,
    TransactionDirection,
    TeamSeasonFinance,
    FinancialHealth,
    OverspendLevel,
    TeamBudgetPlan,
)
from app.models.team import Team, TeamStatus, TeamFinance
from app.models.season import Season, SeasonStatus, Fixture, FixtureType, FixtureStatus
from app.models.user import User, UserStatus
from app.models.league import League, LeagueSystem


@pytest.mark.asyncio
class TestTransferRestrictions:
    """转会限制执行测试"""

    async def _setup(self, db):
        user = User(
            username="test_user",
            email="test@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
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

    async def test_can_place_bid_normal_team(self, db):
        """正常球队应允许竞价"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.overspend_level = OverspendLevel.NONE
        await db.flush()

        can, reason = await service.can_place_transfer_bid(team.id, season.id, Decimal("500000"))
        assert can is True
        assert reason == ""

    async def test_can_place_bid_restricted_team(self, db):
        """restricted 球队应禁止竞价"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.overspend_level = OverspendLevel.RESTRICTED
        await db.flush()

        can, reason = await service.can_place_transfer_bid(team.id, season.id, Decimal("100000"))
        assert can is False
        assert "restricted" in reason.lower() or "受限" in reason

    async def test_can_place_bid_crisis_team(self, db):
        """crisis 球队应禁止竞价"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.overspend_level = OverspendLevel.CRISIS
        await db.flush()

        can, reason = await service.can_place_transfer_bid(team.id, season.id, Decimal("100000"))
        assert can is False
        assert "crisis" in reason.lower() or "危机" in reason

    async def test_can_place_bid_insufficient_balance(self, db):
        """余额不足应禁止竞价"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        tf = await service._get_team_finance(team.id)
        tf.balance = Decimal("10000.00")
        await db.flush()

        can, reason = await service.can_place_transfer_bid(team.id, season.id, Decimal("500000"))
        assert can is False
        assert "余额不足" in reason or "不足" in reason


@pytest.mark.asyncio
class TestFreeSigningRestrictions:
    """自由签约限制执行测试"""

    async def _setup(self, db):
        user = User(
            username="test_user",
            email="test@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
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

    async def test_can_sign_normal_team(self, db):
        """正常球队且工资帽内应允许签约"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.overspend_level = OverspendLevel.NONE
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("500000.00")
        await db.flush()

        can, reason = await service.can_sign_free_player(team.id, season.id, Decimal("300000"))
        assert can is True
        assert reason == ""

    async def test_can_sign_crisis_team_blocked(self, db):
        """crisis 球队应禁止签约"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.overspend_level = OverspendLevel.CRISIS
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("500000.00")
        await db.flush()

        can, reason = await service.can_sign_free_player(team.id, season.id, Decimal("100000"))
        assert can is False
        assert "危机" in reason or "crisis" in reason.lower()

    async def test_can_sign_exceeds_wage_cap(self, db):
        """签约后超出工资帽应禁止"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.overspend_level = OverspendLevel.NONE
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("900000.00")
        await db.flush()

        can, reason = await service.can_sign_free_player(team.id, season.id, Decimal("200000"))
        assert can is False
        assert "工资帽" in reason or "wage cap" in reason.lower()


@pytest.mark.asyncio
class TestEffectiveSponsorBase:
    """有效赞助基础金额修正测试"""

    async def _setup(self, db):
        user = User(
            username="test_user",
            email="test@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id=user.id)
        db.add(team)
        await db.flush()

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()
        return team, season

    async def test_health_a_bonus(self, db):
        """A 级健康应获得 +5% 加成"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.financial_health = FinancialHealth.A
        sf.overspend_level = OverspendLevel.NONE
        await db.flush()

        effective = await service.get_effective_sponsor_base(team.id, season.id, Decimal("100000"))
        assert effective == Decimal("105000.00")

    async def test_health_d_penalty(self, db):
        """D 级健康应获得 -30% 惩罚"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.financial_health = FinancialHealth.D
        sf.overspend_level = OverspendLevel.NONE
        await db.flush()

        effective = await service.get_effective_sponsor_base(team.id, season.id, Decimal("100000"))
        assert effective == Decimal("70000.00")

    async def test_crisis_extra_penalty(self, db):
        """crisis 状态应额外 -30%（与 D 叠加 = -60%）"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.financial_health = FinancialHealth.D
        sf.overspend_level = OverspendLevel.CRISIS
        await db.flush()

        effective = await service.get_effective_sponsor_base(team.id, season.id, Decimal("100000"))
        assert effective == Decimal("49000.00")  # 100000 * 0.70 * 0.70


@pytest.mark.asyncio
class TestWageCapPreview:
    """工资帽签约预览测试"""

    async def _setup(self, db):
        user = User(
            username="test_user",
            email="test@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id=user.id)
        db.add(team)
        await db.flush()

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()
        return team, season

    async def test_preview_within_cap(self, db):
        """签约后未超工资帽"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("500000.00")
        await db.flush()

        preview = await service.preview_wage_cap_after_signing(team.id, season.id, Decimal("300000"))
        assert preview["would_exceed"] is False
        assert preview["after_wage_bill"] == Decimal("800000.00")
        assert preview["after_pressure_pct"] == 80

    async def test_preview_exceeds_cap(self, db):
        """签约后超出工资帽"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service._get_or_create_team_season_finance(team.id, season.id)
        sf.wage_cap = Decimal("1000000.00")
        sf.wage_bill = Decimal("900000.00")
        await db.flush()

        preview = await service.preview_wage_cap_after_signing(team.id, season.id, Decimal("200000"))
        assert preview["would_exceed"] is True
        assert preview["after_wage_bill"] == Decimal("1100000.00")
        assert preview["after_pressure_pct"] == 110


@pytest.mark.asyncio
class TestYouthBudgetDeduction:
    """青训预算扣除测试"""

    async def _setup(self, db):
        user = User(
            username="test_user",
            email="test@test.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        league_system = LeagueSystem(name="东区", code="EAST", zone_id=1)
        db.add(league_system)
        await db.flush()

        league = League(name="超级联赛", level=1, system_id=league_system.id,
                        promotion_spots=1, relegation_spots=1)
        db.add(league)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id=user.id,
                    current_league_id=league.id)
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

    async def test_initialize_deducts_youth_budget(self, db):
        """赛季初始化时应扣除青训预算"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        # 预设 budget plan
        plan = TeamBudgetPlan(
            team_id=team.id,
            target_season_id=season.id,
            policy="balanced",
            transfer_pct=25,
            youth_pct=15,
            wage_pct=50,
            reserve_pct=10,
            is_player_confirmed=True,
            locked_at=__import__("datetime").datetime.utcnow(),
        )
        db.add(plan)
        await db.flush()

        sf = await service.initialize_season_finance(team.id, season.id)
        await db.flush()

        # 验证 youth_budget > 0
        assert sf.youth_budget > 0

        # 验证存在 YOUTH 支出交易
        txn_result = await db.execute(
            select(FinanceTransaction)
            .where(FinanceTransaction.team_id == team.id)
            .where(FinanceTransaction.season_id == season.id)
            .where(FinanceTransaction.source_type == TransactionSourceType.YOUTH)
            .where(FinanceTransaction.direction == TransactionDirection.EXPENSE)
        )
        txn = txn_result.scalar_one_or_none()
        assert txn is not None
        assert txn.amount == sf.youth_budget


@pytest.mark.asyncio
class TestCrisisBudgetOverride:
    """Crisis 球队预算强制测试"""

    async def _setup_season_with_teams(self, db, crisis_count=1, normal_count=0):
        league_system = LeagueSystem(name="东区", code="EAST", zone_id=1)
        db.add(league_system)
        await db.flush()

        league = League(name="超级联赛", level=1, system_id=league_system.id,
                        promotion_spots=1, relegation_spots=1)
        db.add(league)
        await db.flush()

        season = Season(
            season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()

        teams = []

        for i in range(crisis_count):
            user = User(username=f"crisis_user_{i}", email=f"c{i}@test.com",
                        hashed_password="fake", status=UserStatus.ACTIVE)
            db.add(user)
            await db.flush()
            team = Team(name=f"Crisis球队{i}", status=TeamStatus.ACTIVE, user_id=user.id,
                        current_league_id=league.id)
            db.add(team)
            await db.flush()
            tf = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
            db.add(tf)
            # 预设 crisis
            sf = await FinanceService(db)._get_or_create_team_season_finance(team.id, season.id)
            sf.overspend_level = OverspendLevel.CRISIS
            await db.flush()
            teams.append(team)

        for i in range(normal_count):
            user = User(username=f"normal_user_{i}", email=f"n{i}@test.com",
                        hashed_password="fake", status=UserStatus.ACTIVE)
            db.add(user)
            await db.flush()
            team = Team(name=f"Normal球队{i}", status=TeamStatus.ACTIVE, user_id=user.id,
                        current_league_id=league.id)
            db.add(team)
            await db.flush()
            tf = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
            db.add(tf)
            teams.append(team)

        # 创建 fixture
        if len(teams) >= 1:
            fixture = Fixture(
                season_id=season.id,
                fixture_type=FixtureType.LEAGUE,
                season_day=1,
                scheduled_at=__import__("datetime").datetime.utcnow(),
                round_number=1,
                home_team_id=teams[0].id,
                away_team_id=teams[-1].id if len(teams) >= 2 else teams[0].id,
                status=FixtureStatus.SCHEDULED,
                league_id=league.id,
            )
            db.add(fixture)
            await db.flush()

        return season, teams

    async def test_open_budget_crisis_forces_youth_min(self, db):
        """open_budget_window 时 crisis 球队 youth_pct 被强制为 5%"""
        season, teams = await self._setup_season_with_teams(db, crisis_count=1, normal_count=0)
        crisis_team = teams[0]
        service = FinanceService(db)

        await service.open_budget_window(season.id)
        await db.flush()

        plan = await service.get_budget_plan(crisis_team.id, season.id)
        assert plan.youth_pct == 5
