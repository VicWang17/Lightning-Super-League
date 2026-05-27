"""
Pydantic Schemas for API request/response validation
"""
from app.schemas.base import (
    BaseSchema, ResponseSchema, PaginatedResponse, PaginationParams, ErrorResponse
)
from app.schemas.user import (
    UserBase, UserCreate, UserUpdate, UserResponse, UserLogin,
    TokenResponse, UserWithToken
)
from app.schemas.team import TeamBase, TeamCreate, TeamUpdate, TeamResponse, TeamSummary, DashboardStats
from app.schemas.player import (
    PlayerBase, PlayerCreate, PlayerUpdate, PlayerResponse,
    PlayerStats, PlayerPosition, PlayerAbility, PlayerRace,
    PotentialLetter, ContractType, MatchForm, PlayerSkill,
    PlayerListItem,
)
from app.schemas.league import (
    LeagueResponse, LeagueDetailResponse, LeagueSystemResponse,
    LeagueStandingItem,
    TopScorerItem, TopAssistItem, CleanSheetItem
)
from app.schemas.season import (
    SeasonResponse, SeasonDetailResponse, SeasonDayResponse,
    SeasonCalendarResponse, TeamFixtureResponse, TodayFixtureResponse,
    SeasonStatusForDisplay
)
from app.schemas.records import (
    RecordItem,
    RecordsByCategory,
    RecordScope,
    RecordCategory,
    RecordType,
    PlayerSeasonHistoryItem,
    PlayerCareerSummary,
    PlayerMilestone,
    PlayerHistoryResponse,
    TeamSeasonHistoryItem,
    TeamHistoryResponse,
)

__all__ = [
    # Base
    "BaseSchema",
    "ResponseSchema",
    "PaginatedResponse",
    "PaginationParams",
    "ErrorResponse",
    # User
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "TokenResponse",
    "UserWithToken",
    # Team
    "TeamBase",
    "TeamCreate",
    "TeamUpdate",
    "TeamResponse",
    "TeamSummary",
    "DashboardStats",
    # Player
    "PlayerBase",
    "PlayerCreate",
    "PlayerUpdate",
    "PlayerResponse",
    "PlayerStats",
    "PlayerPosition",
    "PlayerAbility",
    "PlayerRace",
    "PotentialLetter",
    "ContractType",
    "MatchForm",
    "PlayerSkill",
    "PlayerListItem",
    # League
    "LeagueResponse",
    "LeagueDetailResponse",
    "LeagueSystemResponse",
    "LeagueStandingItem",
    "TopScorerItem",
    "TopAssistItem",
    "CleanSheetItem",
    # Season
    "SeasonResponse",
    "SeasonDetailResponse",
    "SeasonDayResponse",
    "SeasonCalendarResponse",
    "TeamFixtureResponse",
    "TodayFixtureResponse",
    "SeasonStatusForDisplay",
    # Records
    "RecordItem",
    "RecordsByCategory",
    "RecordScope",
    "RecordCategory",
    "RecordType",
    "PlayerSeasonHistoryItem",
    "PlayerCareerSummary",
    "PlayerMilestone",
    "PlayerHistoryResponse",
    "TeamSeasonHistoryItem",
    "TeamHistoryResponse",
]
