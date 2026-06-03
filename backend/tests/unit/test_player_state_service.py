"""
Player state service unit tests
"""
import pytest
from decimal import Decimal

from app.services.player_state_service import PlayerStateService
from app.models.player import (
    Player,
    PlayerPosition,
    PlayerFoot,
    PlayerRace,
    PlayerPersonality,
    PlayerStatus,
    MatchForm,
)


class TestFitnessScore:
    """Test fitness score calculation"""
    
    def test_fitness_score_mapping(self):
        """Test fitness to score and stamina modifier mapping (design doc 6.1)"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        score, stamina = service._calc_fitness_score(95)
        assert score == 1
        assert stamina == 3
        
        score, stamina = service._calc_fitness_score(80)
        assert score == 0
        assert stamina == 0
        
        score, stamina = service._calc_fitness_score(60)
        assert score == 0
        assert stamina == -4
        
        score, stamina = service._calc_fitness_score(40)
        assert score == -1
        assert stamina == -10
        
        score, stamina = service._calc_fitness_score(20)
        assert score == -2
        assert stamina == -18


class TestVisibleFormMapping:
    """Test total score to visible form mapping"""
    
    def test_map_to_visible_form(self):
        """Test total score to match_form mapping (design doc 6.3)"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        assert service._map_to_visible_form(8) == MatchForm.HOT
        assert service._map_to_visible_form(6) == MatchForm.HOT
        assert service._map_to_visible_form(5) == MatchForm.GOOD
        assert service._map_to_visible_form(2) == MatchForm.GOOD
        assert service._map_to_visible_form(1) == MatchForm.NEUTRAL
        assert service._map_to_visible_form(-1) == MatchForm.NEUTRAL
        assert service._map_to_visible_form(-2) == MatchForm.LOW
        assert service._map_to_visible_form(-5) == MatchForm.LOW


class TestAttributeModifier:
    """Test attribute modification"""
    
    def test_apply_state_to_attributes_positive(self):
        """Test positive modifier increases attributes"""
        attrs = {"SHO": 10, "PAS": 15, "DEF": 8}
        modifier = Decimal("0.04")  # +4%
        
        result = PlayerStateService.apply_state_to_attributes(attrs, modifier)
        
        assert result["SHO"] == round(10 * 1.04)  # 10
        assert result["PAS"] == round(15 * 1.04)  # 16
        assert result["DEF"] == round(8 * 1.04)   # 8
    
    def test_apply_state_to_attributes_negative(self):
        """Test negative modifier decreases attributes"""
        attrs = {"SHO": 10, "PAS": 15, "DEF": 8}
        modifier = Decimal("-0.04")  # -4%
        
        result = PlayerStateService.apply_state_to_attributes(attrs, modifier)
        
        assert result["SHO"] == round(10 * 0.96)  # 10
        assert result["PAS"] == round(15 * 0.96)  # 14
        assert result["DEF"] == round(8 * 0.96)   # 8
    
    def test_apply_state_clamping(self):
        """Test attributes are clamped to 1-20 range"""
        attrs = {"SHO": 1, "PAS": 20}
        
        # Try to decrease below 1
        result = PlayerStateService.apply_state_to_attributes(attrs, Decimal("-0.04"))
        assert result["SHO"] == 1
        
        # Try to increase above 20
        result = PlayerStateService.apply_state_to_attributes(attrs, Decimal("0.04"))
        assert result["PAS"] == 20


class TestInitialStamina:
    """Test initial stamina calculation with fatigue system (设计文档 5.2)"""
    
    def test_calculate_initial_stamina(self):
        """Test stamina calculation with fitness and fatigue"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        # 无疲劳时，stamina 约等于 fitness
        player = Player(
            fitness=80,
            sta=10,
            fatigue=0,
        )
        
        stamina = service.calculate_initial_stamina(player)
        assert stamina == 80.0
        
        # 有疲劳时，stamina 被打折
        player.fitness = 80
        player.fatigue = 50
        stamina = service.calculate_initial_stamina(player)
        # multiplier = 1 - 50 * 0.0023 = 0.885, 80 * 0.885 = 70.8
        assert stamina == 70.8
        
        # 高 fitness 低 fatigue
        player.fitness = 95
        player.fatigue = 10
        stamina = service.calculate_initial_stamina(player)
        # multiplier = 1 - 10 * 0.0023 = 0.977, 95 * 0.977 = 92.8
        assert stamina == 92.8
    
    def test_stamina_clamping(self):
        """Test stamina is clamped to 35-100"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        player = Player(fitness=20, sta=10, fatigue=0)
        stamina = service.calculate_initial_stamina(player)
        # 20 * 1 = 20, clamped to 35
        assert stamina == 35.0
        
        player = Player(fitness=100, sta=10, fatigue=0)
        stamina = service.calculate_initial_stamina(player)
        assert stamina == 100.0
        
        # 高 fitness + 高 fatigue 也可能被 clamp
        player.fitness = 100
        player.fatigue = 100
        stamina = service.calculate_initial_stamina(player)
        # multiplier = 1 - 100 * 0.0023 = 0.77, 100 * 0.77 = 77
        assert stamina == 77.0


class TestContractScore:
    """Test contract score calculation"""
    
    def test_contract_score_with_personality(self):
        """Test personality affects contract score"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        # Materialistic player with +2 satisfaction -> round(2 * 1.6) = 3
        player = Player(
            personality=PlayerPersonality.MATERIALISTIC,
            wage_satisfaction=2,
        )
        score = service._calc_contract_score(player)
        assert score == 3
        
        # Loyal player with +2 satisfaction -> round(2 * 0.5) = 1
        player = Player(
            personality=PlayerPersonality.LOYAL,
            wage_satisfaction=2,
        )
        score = service._calc_contract_score(player)
        assert score == 1
        
        # Professional player with -2 satisfaction -> round(-2 * 1.0) = -2
        player = Player(
            personality=PlayerPersonality.PROFESSIONAL,
            wage_satisfaction=-2,
        )
        score = service._calc_contract_score(player)
        assert score == -2
    
    def test_contract_score_clamping(self):
        """Test contract score is clamped to -4~+4"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        # Materialistic player with +3 satisfaction -> round(3 * 1.6) = 5 -> clamped to 4
        player = Player(
            personality=PlayerPersonality.MATERIALISTIC,
            wage_satisfaction=3,
        )
        score = service._calc_contract_score(player)
        assert score == 4
        
        # Materialistic player with -3 satisfaction -> round(-3 * 1.6) = -5 -> clamped to -4
        player = Player(
            personality=PlayerPersonality.MATERIALISTIC,
            wage_satisfaction=-3,
        )
        score = service._calc_contract_score(player)
        assert score == -4
