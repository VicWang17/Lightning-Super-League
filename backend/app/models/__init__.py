"""
SQLAlchemy models
"""
from app.models.base import Base
from app.models.user import User, UserStatus
from app.models.team import Team, TeamStatus, TeamFinance
from app.models.league import (
    LeagueSystem,
    League,
    Season,
    SeasonStatus,
    LeagueStanding,
    Match,
    MatchStatus,
)
from app.models.player import (
    Player,
    PlayerPosition,
    PlayerFoot,
    PlayerStatus,
    SquadRole,
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
    "Season",
    "SeasonStatus",
    "LeagueStanding",
    "Match",
    "MatchStatus",
    # Player
    "Player",
    "PlayerPosition",
    "PlayerFoot",
    "PlayerStatus",
    "SquadRole",
]
