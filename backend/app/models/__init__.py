"""
SQLAlchemy models
"""
from app.models.base import Base
from app.models.user import User, UserStatus
from app.models.team import Team, TeamStatus, TeamFinance
from app.models.team_tactics import TeamTactics
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
from app.models.player_feedback import (
    PlayerFeedback,
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
from app.models.team_honor import (
    TeamHonor,
    HonorType,
)
from app.models.player_award import (
    PlayerAward,
    AwardType,
    AwardLevel,
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
from app.models.injury_treatment import (
    InjuryTreatment,
    TreatmentPlan,
)
from app.models.training import (
    TrainingSlot,
    TrainingMode,
    TrainingPlanStatus,
    TrainingCreatedBy,
    TeamTrainingPlan,
    TrainingResult,
    TeamTrainingAIProfile,
)
from app.models.transfer import (
    TransferListing,
    TransferListingStatus,
    TransferNegotiation,
    NegotiationStatus,
    TransferOffer,
    OfferKind,
    OfferStatus,
    TransferDailyQuota,
    TransferRecord,
    TransferType,
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
    "TeamTactics",
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
    # Player Feedback
    "PlayerFeedback",
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
    # Team Honor
    "TeamHonor",
    "HonorType",
    # Player Award
    "PlayerAward",
    "AwardType",
    "AwardLevel",
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
    # Training
    "TrainingSlot",
    "TrainingMode",
    "TrainingPlanStatus",
    "TrainingCreatedBy",
    "TeamTrainingPlan",
    "TrainingResult",
    "TeamTrainingAIProfile",
    # Injury Treatment
    "InjuryTreatment",
    "TreatmentPlan",
    # Transfer
    "TransferListing",
    "TransferListingStatus",
    "TransferNegotiation",
    "NegotiationStatus",
    "TransferOffer",
    "OfferKind",
    "OfferStatus",
    "TransferDailyQuota",
    "TransferRecord",
    "TransferType",
]
