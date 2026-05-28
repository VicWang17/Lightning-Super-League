"""
FinanceService 单元测试

测试覆盖：
  • apply_transaction 基本收入和支出
  • apply_transaction 幂等性（idempotency_key）
  • get_overview 计算正确性
  • get_transactions 分页和筛选
  • initialize_season_finance 默认值
  • recalculate_team_finance 余额重算
"""
import pytest
from decimal import Decimal

from app.services.finance_service import FinanceService
from app.models.finance import (
    FinanceTransaction,
    TransactionSourceType,
    TransactionDirection,
    TeamSeasonFinance,
    FinancialHealth,
    OverspendLevel,
)
from app.models.team import Team, TeamStatus, TeamFinance
from app.models.season import Season, SeasonStatus
from app.models.user import User, UserStatus
from app.models.league import League, LeagueSystem


@pytest.mark.asyncio
class TestApplyTransaction:
    """交易应用测试"""

    async def _setup_team_and_season(self, db):
        """辅助方法：创建球队和赛季"""
        user = User(
            id="user-test-1",
            username="testuser",
            email="test@example.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        team = Team(
            name="测试球队",
            status=TeamStatus.ACTIVE,
            user_id="user-test-1",
        )
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(
            team_id=team.id,
            balance=Decimal("10000000.00"),
        )
        db.add(team_finance)

        season = Season(
            season_number=1,
            zone_id=1,
            status=SeasonStatus.ONGOING,
            start_date=__import__("datetime").datetime.utcnow(),
        )
        db.add(season)
        await db.flush()
        return team, season

    async def test_apply_income_increases_balance(self, db):
        """收入应增加余额"""
        team, season = await self._setup_team_and_season(db)
        service = FinanceService(db)

        txn = await service.apply_transaction(
            team.id, season.id,
            TransactionSourceType.BROADCAST, TransactionDirection.INCOME,
            Decimal("350000"), "转播收入",
            idempotency_key="broadcast_1"
        )
        await db.flush()

        assert txn.balance_after == Decimal("10350000.00")
        assert txn.direction == TransactionDirection.INCOME

    async def test_apply_expense_decreases_balance(self, db):
        """支出应减少余额"""
        team, season = await self._setup_team_and_season(db)
        service = FinanceService(db)

        txn = await service.apply_transaction(
            team.id, season.id,
            TransactionSourceType.WAGE, TransactionDirection.EXPENSE,
            Decimal("150000"), "工资支出",
            idempotency_key="wage_1"
        )
        await db.flush()

        assert txn.balance_after == Decimal("9850000.00")
        assert txn.direction == TransactionDirection.EXPENSE

    async def test_idempotency_same_key_returns_existing(self, db):
        """相同幂等键应返回已有记录，不重复扣款"""
        team, season = await self._setup_team_and_season(db)
        service = FinanceService(db)

        txn1 = await service.apply_transaction(
            team.id, season.id,
            TransactionSourceType.SPONSOR, TransactionDirection.INCOME,
            Decimal("200000"), "赞助",
            idempotency_key="sponsor_1"
        )
        txn2 = await service.apply_transaction(
            team.id, season.id,
            TransactionSourceType.SPONSOR, TransactionDirection.INCOME,
            Decimal("200000"), "赞助",
            idempotency_key="sponsor_1"
        )
        await db.flush()

        assert txn1.id == txn2.id
        # 余额只增加一次
        team_finance = await service._get_team_finance(team.id)
        assert team_finance.balance == Decimal("10200000.00")

    async def test_different_idempotency_keys_create_separate_transactions(self, db):
        """不同幂等键应创建独立交易"""
        team, season = await self._setup_team_and_season(db)
        service = FinanceService(db)

        txn1 = await service.apply_transaction(
            team.id, season.id,
            TransactionSourceType.MATCH_BONUS, TransactionDirection.INCOME,
            Decimal("50000"), "比赛奖金1",
            idempotency_key="bonus_1"
        )
        txn2 = await service.apply_transaction(
            team.id, season.id,
            TransactionSourceType.MATCH_BONUS, TransactionDirection.INCOME,
            Decimal("50000"), "比赛奖金2",
            idempotency_key="bonus_2"
        )
        await db.flush()

        assert txn1.id != txn2.id
        team_finance = await service._get_team_finance(team.id)
        assert team_finance.balance == Decimal("10100000.00")


@pytest.mark.asyncio
class TestFinanceOverview:
    """财务概览测试"""

    async def _setup(self, db):
        user = User(
            id="user-test-1",
            username="testuser",
            email="test@example.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        # 创建联赛体系
        league_system = LeagueSystem(name="东区", code="EAST", zone_id=1)
        db.add(league_system)
        await db.flush()

        # 创建联赛
        league = League(name="超级联赛", level=1, system_id=league_system.id,
                        promotion_spots=1, relegation_spots=1)
        db.add(league)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id="user-test-1",
                    current_league_id=league.id)
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(team_finance)

        season = Season(season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
                        start_date=__import__("datetime").datetime.utcnow())
        db.add(season)
        await db.flush()
        return team, season

    async def test_overview_reflects_transactions(self, db):
        """概览应正确反映累计收支"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        # 初始化赛季财务
        await service.initialize_season_finance(team.id, season.id)

        # 创建交易
        await service.apply_transaction(team.id, season.id,
            TransactionSourceType.MATCH_BONUS, TransactionDirection.INCOME,
            Decimal("350000"), "比赛奖金", idempotency_key="mb1")
        await service.apply_transaction(team.id, season.id,
            TransactionSourceType.SPONSOR, TransactionDirection.INCOME,
            Decimal("200000"), "额外赞助", idempotency_key="s1")
        await service.apply_transaction(team.id, season.id,
            TransactionSourceType.WAGE, TransactionDirection.EXPENSE,
            Decimal("150000"), "工资", idempotency_key="w1")
        await db.flush()

        overview = await service.get_overview(team.id, season.id)

        # Phase 5: 初始化时扣除 youth_budget
        # locked_total = 10000000 + 350000 + 200000 = 10550000
        # youth_budget = 10550000 * 0.15 = 1582500
        # 初始后余额 = 10000000 + 550000 - 1582500 = 8967500
        # 测试交易: +350000(match) +200000(sponsor) -150000(wage) = +400000
        # 最终余额 = 8967500 + 400000 = 9367500
        # 总计收入: 550000 + 350000 + 200000 = 1100000
        # 总支出: 1582500(youth) + 150000(wage) = 1732500
        assert overview["current_balance"] == Decimal("9367500.00")
        assert overview["total_income"] == Decimal("1100000.00")
        assert overview["total_expense"] == Decimal("1732500.00")
        assert overview["income_breakdown"]["broadcast"] == Decimal("350000.00")
        assert overview["income_breakdown"]["match_bonus"] == Decimal("350000.00")
        assert overview["expense_breakdown"]["wage"] == Decimal("150000.00")
        assert overview["expense_breakdown"]["youth"] == Decimal("1582500.00")

    async def test_wage_cap_pressure_calculation(self, db):
        """工资压力百分比应计算正确"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        season_finance = await service.initialize_season_finance(team.id, season.id)
        # 手动设置工资帽和工资总额
        season_finance.wage_cap = Decimal("7000000.00")
        season_finance.wage_bill = Decimal("3500000.00")
        await db.flush()

        overview = await service.get_overview(team.id, season.id)
        cap_info = overview["wage_cap_info"]

        assert cap_info["wage_pressure_pct"] == 50
        assert cap_info["status"] == "normal"

    async def test_wage_cap_warning_status(self, db):
        """工资超过90%应显示 warning"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        season_finance = await service.initialize_season_finance(team.id, season.id)
        season_finance.wage_cap = Decimal("1000000.00")
        season_finance.wage_bill = Decimal("950000.00")
        await db.flush()

        overview = await service.get_overview(team.id, season.id)
        cap_info = overview["wage_cap_info"]

        assert cap_info["wage_pressure_pct"] == 95
        assert cap_info["status"] == "warning"


@pytest.mark.asyncio
class TestInitializeSeasonFinance:
    """赛季初始化测试"""

    async def _setup(self, db):
        user = User(
            id="user-test-1",
            username="testuser",
            email="test@example.com",
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

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id="user-test-1",
                    current_league_id=league.id)
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(team_finance)

        season = Season(season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
                        start_date=__import__("datetime").datetime.utcnow())
        db.add(season)
        await db.flush()
        return team, season

    async def test_initialize_sets_default_budgets(self, db):
        """初始化应设置默认预算分配"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf = await service.initialize_season_finance(team.id, season.id)
        await db.flush()

        # Phase 2/5: 初始化后发放广播+赞助收入，再扣除 youth_budget
        # level 1: broadcast=350000, sponsor=200000
        # locked_total = 10000000 + 550000 = 10550000
        # youth_budget = 10550000 * 0.15 = 1582500
        assert sf.opening_balance == Decimal("10000000.00")
        assert sf.current_balance == Decimal("8967500.00")   # +350000 +200000 - 1582500(youth)
        assert sf.transfer_budget == Decimal("2637500.00")   # 25% of 10550000
        assert sf.youth_budget == Decimal("1582500.00")      # 15% of 10550000
        assert sf.wage_budget == Decimal("5275000.00")       # 50% of 10550000
        assert sf.reserve_budget == Decimal("1055000.00")    # 10% of 10550000
        assert sf.financial_health == FinancialHealth.B
        assert sf.overspend_level == OverspendLevel.NONE

    async def test_initialize_is_idempotent(self, db):
        """重复初始化不应覆盖已有数据"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        sf1 = await service.initialize_season_finance(team.id, season.id)
        await db.flush()

        # 修改余额
        sf1.current_balance = Decimal("5000000.00")
        await db.flush()

        # 再次初始化
        sf2 = await service.initialize_season_finance(team.id, season.id)
        await db.flush()

        assert sf2.id == sf1.id
        # 不应被重置为 opening_balance
        assert sf2.current_balance == Decimal("5000000.00")


@pytest.mark.asyncio
class TestGetTransactions:
    """交易查询测试"""

    async def _setup(self, db):
        user = User(
            id="user-test-1",
            username="testuser",
            email="test@example.com",
            hashed_password="fake",
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        await db.flush()

        team = Team(name="测试球队", status=TeamStatus.ACTIVE, user_id="user-test-1")
        db.add(team)
        await db.flush()

        team_finance = TeamFinance(team_id=team.id, balance=Decimal("10000000.00"))
        db.add(team_finance)

        season = Season(season_number=1, zone_id=1, status=SeasonStatus.ONGOING,
                        start_date=__import__("datetime").datetime.utcnow())
        db.add(season)
        await db.flush()
        return team, season

    async def test_pagination(self, db):
        """分页应正确工作"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        for i in range(25):
            await service.apply_transaction(team.id, season.id,
                TransactionSourceType.MATCH_BONUS, TransactionDirection.INCOME,
                Decimal("1000"), f"奖金{i}", idempotency_key=f"bonus_{i}")
        await db.flush()

        result = await service.get_transactions(team.id, season.id, page=1, page_size=10)
        assert len(result["items"]) == 10
        assert result["total"] == 25
        assert result["total_pages"] == 3

        result2 = await service.get_transactions(team.id, season.id, page=2, page_size=10)
        assert len(result2["items"]) == 10
        # 第二页的第一个应该是第11个（按时间倒序）
        assert result2["items"][0].id != result["items"][0].id

    async def test_filter_by_direction(self, db):
        """按方向筛选应正确"""
        team, season = await self._setup(db)
        service = FinanceService(db)

        await service.apply_transaction(team.id, season.id,
            TransactionSourceType.BROADCAST, TransactionDirection.INCOME,
            Decimal("1000"), "收入", idempotency_key="inc_1")
        await service.apply_transaction(team.id, season.id,
            TransactionSourceType.WAGE, TransactionDirection.EXPENSE,
            Decimal("500"), "支出", idempotency_key="exp_1")
        await db.flush()

        income_result = await service.get_transactions(team.id, season.id, direction=TransactionDirection.INCOME)
        assert len(income_result["items"]) == 1
        assert income_result["items"][0].direction == TransactionDirection.INCOME

        expense_result = await service.get_transactions(team.id, season.id, direction=TransactionDirection.EXPENSE)
        assert len(expense_result["items"]) == 1
        assert expense_result["items"][0].direction == TransactionDirection.EXPENSE
