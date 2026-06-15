"""
Tests for tactics service and validation logic.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Team, User, Player, PlayerPersonality, PlayerPosition, PlayerStatus, TeamTactics
from app.schemas.tactics import (
    TeamTacticsUpdate,
    TacticsSetup,
    TeamInstructions,
    SituationalRule,
    SituationalRuleCondition,
    SituationalRuleOverride,
)
from app.services.tactics_service import TacticsService, FORMATION_REQUIREMENTS


@pytest.fixture
def valid_tactics() -> TeamInstructions:
    return TeamInstructions.from_legacy(
        TacticsSetup(
            passing_style=2,
            attack_width=2,
            attack_tempo=2,
            defensive_line_height=2,
            crossing_strategy=2,
            shooting_mentality=2,
            playmaker_focus=0,
            pressing_intensity=2,
            defensive_compactness=1,
            marking_strategy=0,
            offside_trap=0,
            tackling_aggression=1,
        )
    )


async def _create_user_and_team(db: AsyncSession, username: str = "testuser") -> Team:
    user = User(username=username, email=f"{username}@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    team = Team(name="Test FC", user_id=user.id)
    db.add(team)
    await db.flush()
    return team


async def _create_player(
    db: AsyncSession,
    team_id: str,
    position: PlayerPosition,
    name: str = "Player",
) -> Player:
    player = Player(
        name=name,
        race="western",
        position=position,
        height=180,
        weight=75,
        birth_offset=-20,
        personality=PlayerPersonality.PROFESSIONAL,
        team_id=team_id,
        status=PlayerStatus.ACTIVE,
    )
    db.add(player)
    await db.flush()
    return player


@pytest.mark.asyncio
async def test_get_or_create_default_creates_record(db: AsyncSession):
    team = await _create_user_and_team(db)
    # Create enough players for an 8-a-side lineup
    await _create_player(db, team.id, PlayerPosition.GK, "GK1")
    await _create_player(db, team.id, PlayerPosition.DF, "DF1")
    await _create_player(db, team.id, PlayerPosition.DF, "DF2")
    await _create_player(db, team.id, PlayerPosition.MF, "MF1")
    await _create_player(db, team.id, PlayerPosition.MF, "MF2")
    await _create_player(db, team.id, PlayerPosition.MF, "MF3")
    await _create_player(db, team.id, PlayerPosition.FW, "FW1")
    await _create_player(db, team.id, PlayerPosition.FW, "FW2")

    service = TacticsService(db)
    record = await service.get_or_create_default(team.id)

    assert record.team_id == team.id
    assert record.formation_id in FORMATION_REQUIREMENTS
    assert len(record.lineup_player_ids) == 8
    assert len(record.bench_player_ids) <= 5
    assert record.team_instructions
    assert "legacy_team_sliders" in record.team_instructions
    assert record.team_instructions["legacy_team_sliders"]["passing_style"] == 2


@pytest.mark.asyncio
async def test_update_tactics(db: AsyncSession, valid_tactics: TeamInstructions):
    team = await _create_user_and_team(db)
    players = [
        await _create_player(db, team.id, PlayerPosition.GK, f"P{i}")
        for i in range(8)
    ]

    service = TacticsService(db)
    data = TeamTacticsUpdate(
        formation_id="F01",
        lineup_player_ids=[p.id for p in players],
        bench_player_ids=[],
        team_instructions=valid_tactics,
    )
    record = await service.update(team.id, data)

    assert record.formation_id == "F01"
    assert record.lineup_player_ids == [p.id for p in players]
    assert record.team_instructions["legacy_team_sliders"]["passing_style"] == 2


@pytest.mark.asyncio
async def test_validate_players_rejects_foreign_player(db: AsyncSession):
    team_a = await _create_user_and_team(db, "team_a")
    team_b = await _create_user_and_team(db, "team_b")

    player_b = await _create_player(db, team_b.id, PlayerPosition.GK, "B GK")

    service = TacticsService(db)
    _, errors = await service.validate_players(team_a.id, [player_b.id])

    assert len(errors) == 1
    assert "不属于本队" in errors[0] or "不可用" in errors[0]


@pytest.mark.asyncio
async def test_validate_formation_requires_gk(db: AsyncSession):
    team = await _create_user_and_team(db)
    players = [
        await _create_player(db, team.id, PlayerPosition.FW, f"FW{i}")
        for i in range(8)
    ]

    service = TacticsService(db)
    errors = await service.validate_formation("F01", players)

    assert any("门将" in e for e in errors)


@pytest.mark.asyncio
async def test_update_tactics_saves_situational_rules(db: AsyncSession, valid_tactics: TeamInstructions):
    team = await _create_user_and_team(db)
    players = [await _create_player(db, team.id, PlayerPosition.GK, f"P{i}") for i in range(8)]

    valid_tactics.situational_rules = [
        SituationalRule(
            id="chase",
            name="落后追分",
            enabled=True,
            condition=SituationalRuleCondition(minute_gte=40, goal_diff_lte=-1),
            override=SituationalRuleOverride(tempo=4, shooting_frequency=4),
        )
    ]

    service = TacticsService(db)
    data = TeamTacticsUpdate(
        formation_id="F01",
        lineup_player_ids=[p.id for p in players],
        bench_player_ids=[],
        team_instructions=valid_tactics,
    )
    record = await service.update(team.id, data)

    rules = record.team_instructions.get("situational_rules", [])
    assert len(rules) == 1
    assert rules[0]["id"] == "chase"
    assert rules[0]["override"]["tempo"] == 4
