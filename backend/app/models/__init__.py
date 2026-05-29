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
    # Player Contract
    "PlayerContract",
    "ContractStatus",
    # Player State Snapshot
    "PlayerStateSnapshot",
    # Wage Config
    "WageConfig",
    "WageConfigType",
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
