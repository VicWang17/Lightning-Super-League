"""
Training system unit tests
"""
import pytest
from decimal import Decimal

from app.models.player import Player, PlayerPosition, PlayerStatus, MatchForm
from app.services.training_growth_service import TrainingGrowthService
from app.services.player_fatigue_service import PlayerFatigueService
from app.core.training_config import get_training_item, list_training_items, list_templates


class TestTrainingGrowthService:
    """Test training growth calculation"""
    
    def test_age_factor_early_bloomer(self):
        service = TrainingGrowthService()
        assert service.calculate_age_factor(20, "early_bloomer") > 1.0
        assert service.calculate_age_factor(30, "early_bloomer") < 0.5
        assert service.calculate_age_factor(35, "early_bloomer") == 0.0
    
    def test_age_factor_late_bloomer(self):
        service = TrainingGrowthService()
        assert service.calculate_age_factor(18, "late_bloomer") < 1.0
        assert service.calculate_age_factor(26, "late_bloomer", peak_age=31) > 1.0
        assert service.calculate_age_factor(29, "late_bloomer", peak_age=31) > 0.5
    
    def test_age_factor_steady(self):
        service = TrainingGrowthService()
        assert service.calculate_age_factor(25, "steady") > 0.8
    
    def test_potential_factor(self):
        service = TrainingGrowthService()
        assert service.calculate_potential_factor(10.0, 15.0) == 1.0
        assert service.calculate_potential_factor(14.0, 15.0) == 0.25
        assert service.calculate_potential_factor(14.9, 15.0) == 0.04

    def test_development_stage_factor_targets_young_players(self):
        service = TrainingGrowthService()
        young_factor = service.calculate_development_stage_factor(20, 82, "steady", 27)
        prime_factor = service.calculate_development_stage_factor(26, 82, "steady", 27)
        old_factor = service.calculate_development_stage_factor(31, 82, "steady", 27)
        late_old_factor = service.calculate_development_stage_factor(31, 82, "late_bloomer", 31)

        assert young_factor > prime_factor
        assert old_factor < 0.15
        assert late_old_factor > old_factor
    
    def test_diminishing_factor(self):
        service = TrainingGrowthService()
        assert service.calculate_diminishing_factor(0) == 1.00
        assert service.calculate_diminishing_factor(2) == 1.00
        assert service.calculate_diminishing_factor(3) == 0.85
        assert service.calculate_diminishing_factor(5) == 0.70
        assert service.calculate_diminishing_factor(8) == 0.60
    
    def test_fatigue_factor(self):
        service = TrainingGrowthService()
        assert service.calculate_fatigue_factor(10) == 1.05
        assert service.calculate_fatigue_factor(25) == 1.00
        assert service.calculate_fatigue_factor(45) == 0.92
        assert service.calculate_fatigue_factor(65) == 0.78
        assert service.calculate_fatigue_factor(85) == 0.60
        assert service.calculate_fatigue_factor(95) == 0.40
    
    def test_group_fit(self):
        service = TrainingGrowthService()
        assert service.calculate_group_fit("team") == 1.00
        assert service.calculate_group_fit("groups_2") == 1.05
        assert service.calculate_group_fit("groups_3") == 1.10
    
    def test_generate_player_growth_profile(self):
        service = TrainingGrowthService()
        profile = service.generate_player_growth_profile(75, PlayerPosition.FW, 22)
        
        assert "growth_peak_age" in profile
        assert "growth_curve_type" in profile
        assert "growth_speed" in profile
        assert "growth_stability" in profile
        assert "late_bloom_factor" in profile
        assert "attribute_caps" in profile
        
        assert profile["growth_curve_type"] in ["early_bloomer", "steady", "late_bloomer", "explosive", "plateau"]
        assert 20 <= profile["growth_peak_age"] <= 32
        assert 0.70 <= float(profile["growth_speed"]) <= 1.40
        assert len(profile["attribute_caps"]) == 23
        assert all(1.0 <= v <= 20.0 for v in profile["attribute_caps"].values())
    
    def test_apply_attribute_progress_no_breakthrough(self):
        service = TrainingGrowthService()
        player = Player(
            sho=10, pas=10, sta=10,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        player.attribute_progress = {}
        
        breakthroughs = service.apply_attribute_progress(player, {"sho": 0.5})
        assert len(breakthroughs) == 0
        assert player.sho == 10
        assert player.attribute_progress["sho"] == 0.5
    
    def test_apply_attribute_progress_with_breakthrough(self):
        service = TrainingGrowthService()
        player = Player(
            sho=10, pas=10, sta=10,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        player.attribute_progress = {"sho": 0.6}
        
        breakthroughs = service.apply_attribute_progress(player, {"sho": 0.5})
        assert len(breakthroughs) == 1
        assert breakthroughs[0]["attribute"] == "sho"
        assert breakthroughs[0]["before"] == 10
        assert breakthroughs[0]["after"] == 11
        assert player.sho == 11
        assert player.attribute_progress["sho"] == 0.1
    
    def test_apply_attribute_progress_cap_at_20(self):
        service = TrainingGrowthService()
        player = Player(
            sho=19, pas=10, sta=10,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        player.attribute_progress = {"sho": 0.9}
        
        breakthroughs = service.apply_attribute_progress(player, {"sho": 0.5})
        assert len(breakthroughs) == 1
        assert breakthroughs[0]["after"] == 20
        assert player.sho == 20
        # 不能超过20
        breakthroughs2 = service.apply_attribute_progress(player, {"sho": 0.5})
        assert player.sho == 20


class TestPlayerFatigueService:
    """Test player fatigue service"""
    
    def test_apply_training_load(self):
        service = PlayerFatigueService()
        player = Player(
            fitness=80, fatigue=30, sta=10,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        item = get_training_item("repeat_sprint")
        
        service.apply_training_load(player, item)
        assert player.fitness == 71  # 80 - 9
        assert player.fatigue == 44  # 30 + 14
    
    def test_apply_match_load_played(self):
        service = PlayerFatigueService()
        player = Player(
            fitness=80, fatigue=30, sta=10,
            position=PlayerPosition.MF,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        
        service.apply_match_load(player, minutes=70)
        # 70min -> (56,70) 区间: fitness=-14, fatigue=18
        # MF position modifier: 18 * 1.1 = 19.8 -> 20
        assert player.fitness == 66  # 80 - 14
        assert player.fatigue == 50  # 30 + 20
    
    def test_apply_match_load_not_played(self):
        service = PlayerFatigueService()
        player = Player(
            fitness=60, fatigue=50, sta=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        
        service.apply_match_load(player, minutes=0)
        assert player.fitness == 68  # 60 + 8
        assert player.fatigue == 46  # 50 - 4
    
    def test_calculate_initial_stamina_no_fatigue(self):
        service = PlayerFatigueService()
        player = Player(
            fitness=90, fatigue=0, sta=12,
            position=PlayerPosition.MF,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        
        stamina = service.calculate_initial_stamina(player)
        # base = 90 + (12-10)*1.2 = 92.4
        # multiplier = 1 - 0*0.0026 = 1
        assert stamina == 92.4
    
    def test_calculate_initial_stamina_with_fatigue(self):
        service = PlayerFatigueService()
        player = Player(
            fitness=95, fatigue=50, sta=10,
            position=PlayerPosition.MF,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
        )
        
        stamina = service.calculate_initial_stamina(player)
        # base = 95 + 0 = 95
        # multiplier = 1 - 50*0.0026 = 0.87
        # 95 * 0.87 = 82.65
        assert stamina == 82.7
    
    def test_get_fatigue_band(self):
        service = PlayerFatigueService()
        player = Player(fatigue=10, sta=10, status=PlayerStatus.ACTIVE, match_form=MatchForm.NEUTRAL)
        band = service.get_fatigue_band(player)
        assert band["band"] == "清爽"
        assert band["training_growth_factor"] == 1.05
        
        player.fatigue = 50
        band = service.get_fatigue_band(player)
        assert band["band"] == "累积负荷"
        assert band["training_growth_factor"] == 0.92
        
        player.fatigue = 95
        band = service.get_fatigue_band(player)
        assert band["band"] == "透支"
        assert band["training_growth_factor"] == 0.40
    
    def test_can_do_high_intensity_training(self):
        service = PlayerFatigueService()
        player = Player(fatigue=90, sta=10, status=PlayerStatus.ACTIVE, match_form=MatchForm.NEUTRAL)
        assert service.can_do_high_intensity_training(player) is True
        
        player.fatigue = 91
        assert service.can_do_high_intensity_training(player) is False
    
    def test_3day_load_score(self):
        service = PlayerFatigueService()
        assert service.calculate_3day_load_score(5) == 1
        assert service.calculate_3day_load_score(10) == 0
        assert service.calculate_3day_load_score(15) == -1
        assert service.calculate_3day_load_score(22) == -2
        assert service.calculate_3day_load_score(30) == -3


class TestTrainingConfig:
    """Test training configuration"""
    
    def test_training_items_loaded(self):
        items = list_training_items()
        assert len(items) > 0
        
        # 检查必要的分类存在
        categories = {i.category for i in items}
        assert "finishing" in categories
        assert "passing" in categories
        assert "recovery" in categories
    
    def test_templates_loaded(self):
        templates = list_templates()
        assert len(templates) == 10
        
        template_ids = {t.id for t in templates}
        assert "standard_microcycle" in template_ids
        assert "finishing_week" in template_ids
        assert "recovery_week" in template_ids
    
    def test_penalty_training_exists(self):
        item = get_training_item("penalty_pressure")
        assert item is not None
        assert item.category == "finishing"
        assert "pk" in item.attribute_weights
        assert "com" in item.attribute_weights
    
    def test_recovery_training_no_growth(self):
        item = get_training_item("full_rest")
        assert item.is_recovery is True
        assert item.base_gain == 0.0
        assert item.fitness_delta > 0
        assert item.fatigue_delta < 0
    
    def test_gk_training_position_fit(self):
        item = get_training_item("gk_low_save")
        assert item.position_fit["GK"] > 1.0
        assert item.position_fit["FW"] < 0.5


class TestSingleAttributeGain:
    """Test full gain calculation"""
    
    def test_young_player_high_gain(self):
        service = TrainingGrowthService()
        player = Player(
            sho=10, pas=10, sta=10, acc=10, bal=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fatigue=20,
            potential_max=82,
            attribute_caps={"sho": 18.0},
            attribute_progress={},
            growth_curve_type="steady",
            growth_peak_age=27,
            growth_speed=Decimal("1.10"),
            growth_stability=Decimal("0.00"),
        )
        
        item = get_training_item("box_finish_one_touch")
        gain = service.calculate_single_attribute_gain(
            player, item, "sho", 1.0, age=22, recent_count=0, mode="groups_3"
        )
        
        # 年轻球员适配训练应该有明显成长
        assert gain > 0.08
        assert gain < 0.20
    
    def test_old_player_low_gain(self):
        service = TrainingGrowthService()
        player = Player(
            sho=14, pas=10, sta=10, acc=10, bal=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fatigue=30,
            potential_max=60,
            attribute_caps={"sho": 15.0},
            attribute_progress={},
            growth_curve_type="early_bloomer",
            growth_peak_age=25,
            growth_speed=Decimal("0.90"),
            growth_stability=Decimal("0.00"),
        )
        
        item = get_training_item("box_finish_one_touch")
        gain = service.calculate_single_attribute_gain(
            player, item, "sho", 1.0, age=32, recent_count=0, mode="team"
        )
        
        # 老将接近上限成长应该很小或为零
        assert gain < 0.01

    def test_young_high_potential_player_outgrows_regular_old_player(self):
        service = TrainingGrowthService()
        item = get_training_item("box_finish_one_touch")
        young = Player(
            sho=10, pas=10, sta=10, acc=10, bal=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fatigue=20,
            potential_max=84,
            attribute_caps={"sho": 18.0},
            attribute_progress={},
            growth_curve_type="steady",
            growth_peak_age=27,
            growth_speed=Decimal("1.25"),
            growth_stability=Decimal("0.00"),
        )
        old = Player(
            sho=10, pas=10, sta=10, acc=10, bal=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fatigue=20,
            potential_max=84,
            attribute_caps={"sho": 18.0},
            attribute_progress={},
            growth_curve_type="steady",
            growth_peak_age=27,
            growth_speed=Decimal("1.25"),
            growth_stability=Decimal("0.00"),
        )

        young_gain = service.calculate_single_attribute_gain(
            young, item, "sho", 1.0, age=20, recent_count=0, mode="groups_3"
        )
        old_gain = service.calculate_single_attribute_gain(
            old, item, "sho", 1.0, age=31, recent_count=0, mode="groups_3"
        )

        assert young_gain > old_gain * 20
    
    def test_high_fatigue_reduces_gain(self):
        service = TrainingGrowthService()
        player = Player(
            sho=10, pas=10, sta=10, acc=10, bal=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fatigue=80,
            attribute_caps={"sho": 18.0},
            attribute_progress={},
            growth_curve_type="steady",
            growth_peak_age=27,
            growth_speed=Decimal("1.00"),
            growth_stability=Decimal("1.00"),
        )
        
        item = get_training_item("box_finish_one_touch")
        gain_high_fatigue = service.calculate_single_attribute_gain(
            player, item, "sho", 1.0, age=22, recent_count=0, mode="team"
        )
        
        player.fatigue = 20
        gain_low_fatigue = service.calculate_single_attribute_gain(
            player, item, "sho", 1.0, age=22, recent_count=0, mode="team"
        )
        
        assert gain_high_fatigue < gain_low_fatigue
    
    def test_diminishing_returns(self):
        service = TrainingGrowthService()
        player = Player(
            sho=10, pas=10, sta=10, acc=10, bal=10,
            position=PlayerPosition.FW,
            status=PlayerStatus.ACTIVE,
            match_form=MatchForm.NEUTRAL,
            fatigue=20,
            attribute_caps={"sho": 18.0},
            attribute_progress={},
            growth_curve_type="steady",
            growth_peak_age=27,
            growth_speed=Decimal("1.00"),
            growth_stability=Decimal("1.00"),
        )
        
        item = get_training_item("box_finish_one_touch")
        gain_first = service.calculate_single_attribute_gain(
            player, item, "sho", 1.0, age=22, recent_count=1, mode="team"
        )
        gain_repeated = service.calculate_single_attribute_gain(
            player, item, "sho", 1.0, age=22, recent_count=5, mode="team"
        )
        
        assert gain_repeated < gain_first
