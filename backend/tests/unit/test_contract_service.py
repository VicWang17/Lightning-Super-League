"""
Contract service unit tests
"""
import pytest
import pytest_asyncio
from decimal import Decimal

from app.services.contract_service import ContractService
from app.models.player import (
    Player,
    PlayerPosition,
    PlayerFoot,
    PlayerRace,
    PlayerPersonality,
    ContractType,
    SquadRole,
)
from app.models.team import Team, TeamStatus
from app.models.league import League
from app.models.wage_config import WageConfig, WageConfigType


@pytest_asyncio.fixture
async def test_league(db):
    """Create test league"""
    # 先创建 league_system
    from app.models.league import LeagueSystem
    system = LeagueSystem(name="Test System", code="TEST")
    db.add(system)
    await db.flush()
    
    league = League(
        name="Test League",
        level=3,
        system_id=system.id,
    )
    db.add(league)
    await db.flush()
    return league


@pytest_asyncio.fixture
async def test_team(db, test_league):
    """Create test team"""
    from app.models.user import User, UserStatus
    from app.models.season import Season, SeasonStatus
    
    user = User(
        username="test_user_1",
        email="test@example.com",
        hashed_password="test",
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.flush()
    
    from datetime import date
    import random
    season = Season(
        season_number=random.randint(1000, 9999),
        zone_id=1,
        status=SeasonStatus.ONGOING,
        start_date=date.today(),
    )
    db.add(season)
    await db.flush()
    
    team = Team(
        name="Test Team",
        status=TeamStatus.ACTIVE,
        user_id=user.id,
        current_league_id=test_league.id,
        current_season_id=season.id,
    )
    db.add(team)
    await db.flush()
    return team


@pytest_asyncio.fixture
async def test_player(db, test_team):
    """Create test player"""
    player = Player(
        name="Test Player",
        race=PlayerRace.WESTERN,
        position=PlayerPosition.FW,
        preferred_foot=PlayerFoot.RIGHT,
        height=180,
        weight=75,
        birth_offset=-22,
        personality=PlayerPersonality.PROFESSIONAL,
        contract_type=ContractType.NORMAL,
        wage=Decimal("50000"),
        squad_role=SquadRole.FIRST_TEAM,
        team_id=test_team.id,
        sho=12, pas=10, dri=11, spd=13, str_=12, sta=10,
        acc=12, hea=10, bal=11, defe=5, tkl=6, vis=8,
        cro=7, con=10, fin=11, com=10, sav=5, ref=6,
        pos=5, rus=4, dec=10, fk=8, pk=7,
    )
    db.add(player)
    await db.flush()
    return player


class TestWageSatisfaction:
    """Test wage satisfaction mapping"""
    
    def test_wage_ratio_to_satisfaction(self):
        """Test wage ratio to satisfaction mapping (design doc 5.4)"""
        service = ContractService.__new__(ContractService)
        
        assert service._wage_ratio_to_satisfaction(Decimal("0.50")) == -3
        assert service._wage_ratio_to_satisfaction(Decimal("0.75")) == -2
        assert service._wage_ratio_to_satisfaction(Decimal("0.90")) == -1
        assert service._wage_ratio_to_satisfaction(Decimal("1.00")) == 0
        assert service._wage_ratio_to_satisfaction(Decimal("1.20")) == 1
        assert service._wage_ratio_to_satisfaction(Decimal("1.50")) == 2


class TestRecommendedWage:
    """Test recommended wage calculation"""
    
    @pytest.mark.asyncio
    async def test_calculate_recommended_wage(self, db, test_player, test_team):
        """Test recommended wage calculation with real WageConfig data"""
        service = ContractService(db)
        
        recommended = await service.calculate_recommended_wage(
            test_player.id,
            test_team.id,
            ContractType.NORMAL,
            SquadRole.FIRST_TEAM,
        )
        
        # Should be positive
        assert recommended > 0
        
        # Should be a reasonable amount (base_wage * factors)
        # OVR ~50-60 for default player, base ~30000-40000
        # With league_factor(1.0), age_factor(1.0), contract_factor(1.0)
        assert recommended >= Decimal("10000")
    
    @pytest.mark.asyncio
    async def test_base_wage_interpolation(self, db):
        """Test OVR base wage interpolation"""
        service = ContractService.__new__(ContractService)
        service.db = db
        
        # Test exact match
        wage_30 = await service._get_base_wage_by_ovr(30)
        assert wage_30 > 0
        
        # Test interpolation between 30 and 40
        wage_35 = await service._get_base_wage_by_ovr(35)
        wage_30 = await service._get_base_wage_by_ovr(30)
        wage_40 = await service._get_base_wage_by_ovr(40)
        assert wage_30 <= wage_35 <= wage_40


class TestContractPreview:
    """Test contract preview"""
    
    @pytest.mark.asyncio
    async def test_preview_contract_offer(self, db, test_player, test_team):
        """Test contract preview returns valid data"""
        service = ContractService(db)
        
        preview = await service.preview_contract_offer(
            player_id=test_player.id,
            team_id=test_team.id,
            contract_type=ContractType.NORMAL,
            years=2,
            wage=Decimal("60000"),
            squad_role=SquadRole.FIRST_TEAM,
        )
        
        assert preview.recommended_wage > 0
        assert preview.wage_ratio > 0
        assert isinstance(preview.hidden_wage_satisfaction, int)
        assert preview.can_submit in (True, False)
        assert isinstance(preview.warnings, list)


class TestAgeRangeKey:
    """Test age range key mapping"""
    
    def test_age_range_mapping(self):
        """Test age to range key mapping"""
        service = ContractService.__new__(ContractService)
        
        assert service._age_range_key(18) == "<=20"
        assert service._age_range_key(20) == "<=20"
        assert service._age_range_key(23) == "21-25"
        assert service._age_range_key(27) == "26-28"
        assert service._age_range_key(29) == "29-30"
        assert service._age_range_key(32) == "31-33"
        assert service._age_range_key(35) == ">=34"
