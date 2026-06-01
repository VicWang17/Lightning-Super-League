"""
Rookie market tests - 新人自由市场保护期测试
"""
import pytest
import pytest_asyncio
from decimal import Decimal

from app.services.youth_academy_service import YouthAcademyService
from app.services.ai_team_management_service import AITeamManagementService
from app.models.youth_academy_player import AcademyPlayerStatus
from app.models.free_agent_listing import FreeAgentOrigin, ListingStatus


@pytest_asyncio.fixture
async def test_league(db):
    from app.models.league import LeagueSystem, League
    system = LeagueSystem(name="Test System", code="TEST")
    db.add(system)
    await db.flush()
    league = League(name="Test League", level=3, system_id=system.id)
    db.add(league)
    await db.flush()
    return league


@pytest_asyncio.fixture
async def test_team(db, test_league):
    from app.models.user import User, UserStatus
    from app.models.team import Team, TeamStatus
    from app.models.season import Season, SeasonStatus
    from datetime import date
    import random

    user = User(
        username="test_user_1",
        email="test@example.com",
        hashed_password="test",
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.flush()

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


class TestRookieScore:
    """Test rookie scoring logic"""

    def test_calculate_rookie_score(self):
        service = AITeamManagementService.__new__(AITeamManagementService)
        from unittest.mock import MagicMock
        from app.models import Player, PlayerPosition, GrowthSpeed, YouthAcademyPlayer

        player = MagicMock()
        player.ovr = 50
        player.birth_offset = -16
        player.position = PlayerPosition.FW
        player.potential_letter = MagicMock()
        player.potential_letter.value = "A"

        academy = MagicMock()
        academy.growth_speed = GrowthSpeed.FAST

        need = {"FW": 2, "MF": 0, "DF": 0, "GK": 0}

        score = service._calculate_rookie_score(player, academy, need, roster_count=10, wage_pressure=0.5)
        assert score > 35  # Should be high enough to sign

        # Low score with bad potential, old age, no position need
        player.potential_letter.value = "D"
        academy.growth_speed = GrowthSpeed.SLOW
        player.birth_offset = -18
        player.ovr = 30
        need = {"FW": 0, "MF": 0, "DF": 0, "GK": 0}
        score = service._calculate_rookie_score(player, academy, need, roster_count=16, wage_pressure=1.1)
        assert score < 25


class TestContractServiceRosterMax:
    """Test roster max increased to 18"""

    def test_roster_max_is_18(self):
        from app.services.contract_service import ContractService
        assert ContractService.ROSTER_MAX == 18
        assert ContractService.ROSTER_MIN == 8

    def test_roster_lifecycle_max_is_18(self):
        from app.services.roster_lifecycle_service import RosterLifecycleService
        assert RosterLifecycleService.ROSTER_MAX == 18
