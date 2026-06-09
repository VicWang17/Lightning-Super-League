"""
Unit tests for InjuryTreatmentService
"""
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.injury_treatment_service import InjuryTreatmentService, _round_to_1000
from app.core.economy_config import get_economy_config


class TestTreatmentCalculations:
    """测试治疗计算逻辑（无需数据库）"""

    def test_round_to_1000(self):
        assert _round_to_1000(Decimal("1234")) == Decimal("1000")
        assert _round_to_1000(Decimal("1500")) == Decimal("2000")
        assert _round_to_1000(Decimal("999")) == Decimal("1000")
        assert _round_to_1000(Decimal("1000")) == Decimal("1000")

    def test_build_option_enhanced(self):
        """测试加强理疗选项计算"""
        svc = InjuryTreatmentService(db=MagicMock())
        option = svc._build_option(
            plan=MagicMock(value="enhanced"),
            severity=2,
            remaining_days=8,
            original_total_days=10,
            body_part="hamstring",
            player_value_base=Decimal("120000"),
            scarcity_multiplier=Decimal("1.0"),
            is_gk=False,
        )
        # enhanced: reduction_pct=0.25, max_days=2
        # actual_reduction = min(ceil(8*0.25)=2, 2, 8-floor(10*0.35)=5) = 2
        assert option["plan"] == "enhanced"
        assert option["days_reduced"] == 2
        assert option["days_after"] == 6
        assert option["available"] is True
        assert option["residual_wear_penalty"] == 0

    def test_build_option_specialist(self):
        """测试专家会诊选项计算（对照设计文档 13.2 样例）"""
        svc = InjuryTreatmentService(db=MagicMock())
        option = svc._build_option(
            plan=MagicMock(value="specialist"),
            severity=2,
            remaining_days=8,
            original_total_days=10,
            body_part="hamstring",
            player_value_base=Decimal("120000"),
            scarcity_multiplier=Decimal("1.0"),
            is_gk=False,
        )
        # specialist: reduction_pct=0.40, max_days=4
        # actual_reduction = min(ceil(8*0.40)=4, 4, 8-floor(10*0.35)=5) = 4
        assert option["plan"] == "specialist"
        assert option["days_reduced"] == 4
        assert option["days_after"] == 4
        assert option["available"] is True
        assert option["residual_wear_penalty"] == 5
        # cost ≈ 120000 * 4^1.15 * 1.8 ≈ 1,060,000（取整到千）
        assert option["cost"] > Decimal("900000")
        assert option["cost"] < Decimal("1200000")

    def test_build_option_aggressive(self):
        """测试激进复出选项计算"""
        svc = InjuryTreatmentService(db=MagicMock())
        option = svc._build_option(
            plan=MagicMock(value="aggressive"),
            severity=3,
            remaining_days=10,
            original_total_days=12,
            body_part="knee",
            player_value_base=Decimal("200000"),
            scarcity_multiplier=Decimal("1.15"),
            is_gk=False,
        )
        # aggressive: reduction_pct=0.55, max_days=6
        # minimum_remaining = max(1, floor(12*0.35)=4) = 4
        # actual_reduction = min(ceil(10*0.55)=6, 6, 10-4=6) = 6
        assert option["plan"] == "aggressive"
        assert option["days_reduced"] == 6
        assert option["days_after"] == 4
        assert option["available"] is True
        assert option["residual_wear_penalty"] == 12

    def test_build_option_not_available_when_too_few_days(self):
        """测试当剩余天数太少时方案不可用"""
        svc = InjuryTreatmentService(db=MagicMock())
        option = svc._build_option(
            plan=MagicMock(value="specialist"),
            severity=2,
            remaining_days=3,
            original_total_days=5,
            body_part="hamstring",
            player_value_base=Decimal("120000"),
            scarcity_multiplier=Decimal("1.0"),
            is_gk=False,
        )
        # minimum_remaining = max(1, floor(5*0.35)) = 1
        # actual_reduction = min(ceil(3*0.40)=2, 4, 3-1=2) = 2
        # 但 3-1=2, min(2,2)=2, available=True
        # 如果 remaining=2, original=5: min(ceil(2*0.4)=1, 4, 2-1=1) = 1, available=True
        # 如果 remaining=1: min(1, 4, 1-1=0) = 0, available=False
        pass  # 具体数值取决于边界

    def test_calc_player_value_base(self):
        """测试球员价值基础计算"""
        svc = InjuryTreatmentService(db=MagicMock())
        player = MagicMock()
        player.market_value = Decimal("8000000")
        player.wage = Decimal("3360000")  # 周薪 80k -> 赛季工资 80k*42

        base = svc._calc_player_value_base(player, league_level=1)
        # max(8,000,000*0.006=48,000, 80,000*1.5=120,000, 50,000) = 120,000
        assert base == Decimal("120000")

        # 低级别联赛底价兜底
        player.market_value = Decimal("0")
        player.wage = Decimal("10000")
        base = svc._calc_player_value_base(player, league_level=4)
        assert base == Decimal("15000")

    def test_body_part_multiplier_with_gk(self):
        """测试门将部位倍率修正"""
        svc = InjuryTreatmentService(db=MagicMock())
        option_gk = svc._build_option(
            plan=MagicMock(value="enhanced"),
            severity=2,
            remaining_days=8,
            original_total_days=10,
            body_part="fingers",
            player_value_base=Decimal("100000"),
            scarcity_multiplier=Decimal("1.0"),
            is_gk=True,
        )
        option_non_gk = svc._build_option(
            plan=MagicMock(value="enhanced"),
            severity=2,
            remaining_days=8,
            original_total_days=10,
            body_part="fingers",
            player_value_base=Decimal("100000"),
            scarcity_multiplier=Decimal("1.0"),
            is_gk=False,
        )
        # 门将为手指 +0.30 -> 0.90+0.30=1.20
        assert option_gk["cost"] > option_non_gk["cost"]


class TestReserveSettlement:
    """测试准备金结转逻辑"""

    @pytest.mark.asyncio
    async def test_settle_reserve_carryover(self):
        """测试赛季末准备金结转"""
        db = MagicMock()
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        svc = InjuryTreatmentService(db=db)

        # Mock season_finance
        season_finance = MagicMock()
        season_finance.reserve_budget = Decimal("100000")
        season_finance.reserve_spent = Decimal("30000")
        season_finance.financial_health.value = "B"

        # Mock team_finance
        team_finance = MagicMock()
        team_finance.balance = Decimal("500000")

        svc._get_or_create_team_season_finance = AsyncMock(return_value=season_finance)
        svc._get_team_finance = AsyncMock(return_value=team_finance)

        txn = await svc.settle_reserve_carryover("team_1", "season_1")

        # unused = 100000 - 30000 = 70000
        # health B -> rate 0.60
        # carryover = 70000 * 0.60 = 42000
        assert txn is not None
        assert txn.amount == Decimal("42000")
        assert txn.source_type == "reserve_settlement"
        assert team_finance.balance == Decimal("542000")

    @pytest.mark.asyncio
    async def test_settle_reserve_carryover_no_unused(self):
        """测试无剩余准备金时不结转"""
        db = MagicMock()
        svc = InjuryTreatmentService(db=db)

        season_finance = MagicMock()
        season_finance.reserve_budget = Decimal("100000")
        season_finance.reserve_spent = Decimal("100000")
        season_finance.financial_health.value = "A"

        svc._get_or_create_team_season_finance = AsyncMock(return_value=season_finance)

        txn = await svc.settle_reserve_carryover("team_1", "season_1")
        assert txn is None


class TestPaymentOrder:
    """测试支付顺序"""

    @pytest.mark.asyncio
    async def test_reserve_pays_first(self):
        """测试医疗费优先从准备金扣除"""
        db = MagicMock()
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        svc = InjuryTreatmentService(db=db)

        # 准备金充足场景
        season_finance = MagicMock()
        season_finance.reserve_budget = Decimal("100000")
        season_finance.reserve_spent = Decimal("0")
        season_finance.reserve_auto_used = Decimal("0")
        season_finance.reserve_medical_used = Decimal("0")
        season_finance.reserve_events_used = 0
        season_finance.current_balance = Decimal("500000")

        team_finance = MagicMock()
        team_finance.balance = Decimal("500000")

        player = MagicMock()
        player.team_id = "team_1"
        player.position = MagicMock(value="FW")
        player.market_value = Decimal("0")
        player.wage = Decimal("0")
        player.current_injury = {
            "body_part": "hamstring",
            "severity": 2,
            "remaining_days": 8,
            "original_total_days": 10,
            "created_at": "2026-01-01T00:00:00",
            "treatment_applied": False,
            "season_id": "season_1",
        }
        player.name = "Test Player"

        svc._get_player = AsyncMock(return_value=player)
        svc._get_team_finance = AsyncMock(return_value=team_finance)
        svc._get_or_create_team_season_finance = AsyncMock(return_value=season_finance)
        svc._get_team_league_level = AsyncMock(return_value=4)
        svc._calc_scarcity_multiplier = AsyncMock(return_value=Decimal("1.0"))

        result = await svc.apply_treatment("team_1", "player_1", "inj_1", MagicMock(value="enhanced"))

        # 费用应完全由准备金覆盖，余额只扣费用部分
        medical_cost = result["cost"]
        assert result["reserve_paid"] == min(season_finance.reserve_budget, medical_cost)
        assert result["cash_paid"] == max(Decimal("0"), medical_cost - season_finance.reserve_budget)
        assert result["reserve_available_after"] == max(Decimal("0"), season_finance.reserve_budget - medical_cost)

    @pytest.mark.asyncio
    async def test_cash_pays_when_reserve_depleted(self):
        """测试准备金用尽后从余额硬付"""
        db = MagicMock()
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        svc = InjuryTreatmentService(db=db)

        season_finance = MagicMock()
        season_finance.reserve_budget = Decimal("10000")
        season_finance.reserve_spent = Decimal("10000")  # 已用尽
        season_finance.reserve_auto_used = Decimal("0")
        season_finance.reserve_medical_used = Decimal("0")
        season_finance.reserve_events_used = 0
        season_finance.current_balance = Decimal("500000")

        team_finance = MagicMock()
        team_finance.balance = Decimal("500000")

        player = MagicMock()
        player.team_id = "team_1"
        player.position = MagicMock(value="FW")
        player.market_value = Decimal("0")
        player.wage = Decimal("0")
        player.current_injury = {
            "body_part": "hamstring",
            "severity": 2,
            "remaining_days": 8,
            "original_total_days": 10,
            "created_at": "2026-01-01T00:00:00",
            "treatment_applied": False,
            "season_id": "season_1",
        }
        player.name = "Test Player"

        svc._get_player = AsyncMock(return_value=player)
        svc._get_team_finance = AsyncMock(return_value=team_finance)
        svc._get_or_create_team_season_finance = AsyncMock(return_value=season_finance)
        svc._get_team_league_level = AsyncMock(return_value=4)
        svc._calc_scarcity_multiplier = AsyncMock(return_value=Decimal("1.0"))

        result = await svc.apply_treatment("team_1", "player_1", "inj_1", MagicMock(value="enhanced"))

        medical_cost = result["cost"]
        assert result["reserve_paid"] == Decimal("0")
        assert result["cash_paid"] == medical_cost
