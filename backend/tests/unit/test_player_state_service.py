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
    """Test initial stamina calculation"""
    
    def test_calculate_initial_stamina(self):
        """Test stamina calculation with fitness and modifier"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        # Create a mock player
        player = Player(
            fitness=80,
        )
        
        stamina = service.calculate_initial_stamina(player)
        # fitness 80 -> score 0, stamina_mod 0 -> initial = 80
        assert stamina == 80.0
        
        player.fitness = 60
        stamina = service.calculate_initial_stamina(player)
        # fitness 60 -> score 0, stamina_mod -4 -> initial = 56
        assert stamina == 56.0
        
        player.fitness = 95
        stamina = service.calculate_initial_stamina(player)
        # fitness 95 -> score 1, stamina_mod 3 -> initial = 98
        assert stamina == 98.0
    
    def test_stamina_clamping(self):
        """Test stamina is clamped to 30-100"""
        service = PlayerStateService.__new__(PlayerStateService)
        
        player = Player(fitness=20)
        stamina = service.calculate_initial_stamina(player)
        # fitness 20 -> score -5, stamina_mod -30 -> initial = -10 -> clamped to 30
        assert stamina == 30.0
        
        player = Player(fitness=100)
        stamina = service.calculate_initial_stamina(player)
        # fitness 100 -> score 1, stamina_mod 3 -> initial = 103 -> clamped to 100
        assert stamina == 100.0


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
