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
    PlayerRace,
    PotentialLetter,
    PlayerPersonality,
    ContractType,
    MatchForm,
    SquadRole,
    OriginType,
)
from app.models.player_contract import (
    PlayerContract,
    ContractStatus,
)
from app.models.player_state_snapshot import (
    PlayerStateSnapshot,
)
from app.models.wage_config import (
    WageConfig,
    WageConfigType,
)
from app.models.free_agent_listing import (
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus,
)
from app.models.youth_academy_player import (
    YouthAcademyPlayer,
    AcademyPlayerStatus,
    GrowthSpeed,
)
from app.models.youth_academy_snapshot import (
    YouthAcademySnapshot,
)
from app.models.player_season_stats import (
    PlayerSeasonStats,
)
from app.models.events import EventQueue
from app.models.match_result import MatchResult
from app.models.record import (
    Record,
    RecordScope,
    RecordCategory,
    RecordType,
)
from app.models.mail import (
    Mail,
    MailCategory,
    MailPriority,
)
from app.models.clock import GameClockState
from app.models.finance import (
    FinanceTransaction,
    TransactionSourceType,
    TransactionDirection,
    TeamSeasonFinance,
    FinancialHealth,
    OverspendLevel,
    BudgetPolicy,
    SponsorPolicy,
    SponsorContractStatus,
    TeamBudgetPlan,
    SponsorContract,
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
    "PlayerRace",
    "PotentialLetter",
    "PlayerPersonality",
    "ContractType",
    "MatchForm",
    "SquadRole",
    "OriginType",
    # Player Contract
    "PlayerContract",
    "ContractStatus",
    # Player State Snapshot
    "PlayerStateSnapshot",
    # Wage Config
    "WageConfig",
    "WageConfigType",
    # Free Agent Listing
    "FreeAgentListing",
    "FreeAgentOrigin",
    "ListingStatus",
    # Youth Academy
    "YouthAcademyPlayer",
    "AcademyPlayerStatus",
    "GrowthSpeed",
    "YouthAcademySnapshot",
    # Player Season Stats
    "PlayerSeasonStats",
    # Event Queue
    "EventQueue",
    # Match Engine
    "MatchResult",
    # Records
    "Record",
    "RecordScope",
    "RecordCategory",
    "RecordType",
    # Mail
    "Mail",
    "MailCategory",
    "MailPriority",
    # Clock
    "GameClockState",
    # Finance
    "FinanceTransaction",
    "TransactionSourceType",
    "TransactionDirection",
    "TeamSeasonFinance",
    "FinancialHealth",
    "OverspendLevel",
    "BudgetPolicy",
    "SponsorPolicy",
    "SponsorContractStatus",
    "TeamBudgetPlan",
    "SponsorContract",
]
