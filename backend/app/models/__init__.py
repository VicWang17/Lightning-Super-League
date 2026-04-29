"""
SQLAlchemy models
"""
from app.models.base import Base
from app.models.user import User, UserStatus
from app.models.team import Team, TeamStatus, TeamFinance
from app.models.league import (
    LeagueSystem,
    League,
    LeagueStanding,
)
from app.models.season import (
    Season,
    SeasonStatus,
    Fixture,
    FixtureType,
    FixtureStatus,
    CupCompetition,
    CupGroup,
)
from app.models.player import (
    Player,
    PlayerPosition,
    PlayerFoot,
    PlayerStatus,
    SquadRole,
)
from app.models.player_season_stats import (
    PlayerSeasonStats,
)

__all__ = [
    # Base
    "Base",
    # User
    "User",
    "UserStatus",
    # Team
    "Team",
    "TeamStatus",
    "TeamFinance",
    # League
    "LeagueSystem",
    "League",
    "LeagueStanding",
    # Season & Cup
    "Season",
    "SeasonStatus",
    "Fixture",
    "FixtureType",
    "FixtureStatus",
    "CupCompetition",
    "CupGroup",
    # Player
    "Player",
    "PlayerPosition",
    "PlayerFoot",
    "PlayerStatus",
    "SquadRole",
    # Player Season Stats
    "PlayerSeasonStats",
]
