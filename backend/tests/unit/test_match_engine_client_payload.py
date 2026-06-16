"""
Verify MatchEngineClient builds a payload that includes V2/V3/V4 instructions.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Team, User, Player, PlayerPersonality, PlayerPosition, PlayerStatus, TeamTactics
from app.schemas.tactics import (
    TeamInstructions,
    TacticsSetup,
    PlayerInstruction,
    SituationalRule,
    SituationalRuleCondition,
    SituationalRuleOverride,
)
from app.services.match_engine_client import MatchEngineClient


async def _create_team_with_players(db: AsyncSession, name: str = "Test FC") -> tuple[Team, list[Player]]:
    user = User(username=f"mc_{name}", email=f"mc_{name}@test.com", hashed_password="fake")
    db.add(user)
    await db.flush()

    team = Team(name=name, user_id=user.id)
    db.add(team)
    await db.flush()

    positions = [
        PlayerPosition.GK,
        PlayerPosition.DF,
        PlayerPosition.DF,
        PlayerPosition.MF,
        PlayerPosition.MF,
        PlayerPosition.MF,
        PlayerPosition.FW,
        PlayerPosition.FW,
    ]
    players = []
    for i, position in enumerate(positions):
        player = Player(
            name=f"P{i}",
            race="western",
            position=position,
            height=180,
            birth_offset=-20,
            personality=PlayerPersonality.PROFESSIONAL,
            team_id=team.id,
            status=PlayerStatus.ACTIVE,
        )
        db.add(player)
        players.append(player)
    await db.flush()
    return team, players


@pytest.mark.asyncio
async def test_build_team_setup_includes_all_instruction_layers(db: AsyncSession):
    team, players = await _create_team_with_players(db)

    instructions = TeamInstructions.from_legacy(
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
    instructions.player_instructions = [
        PlayerInstruction(player_id=players[0].id, carry_ball=4, shooting_frequency=4)
    ]
    instructions.situational_rules = [
        SituationalRule(
            id="chase",
            name="落后追分",
            enabled=True,
            condition=SituationalRuleCondition(minute_gte=40, goal_diff_lte=-1),
            override=SituationalRuleOverride(tempo=4, pressing_intensity=4),
        )
    ]

    team_tactics = TeamTactics(
        team_id=team.id,
        formation_id="F01",
        lineup_player_ids=[p.id for p in players],
        bench_player_ids=[],
        team_instructions=instructions.model_dump(),
        set_piece_instructions={},
        substitution_rules={},
    )
    db.add(team_tactics)
    await db.flush()

    client = MatchEngineClient()
    payload = await client._build_team_setup(team, players, db=db, season_number=1)

    assert payload["formation_id"] == "F01"
    assert len(payload["players"]) == 8
    assert "team_instructions" in payload

    ti = payload["team_instructions"]
    assert ti["in_possession"]["attack_route"] == "mixed"
    assert len(ti["player_instructions"]) == 1
    assert ti["player_instructions"][0]["player_id"] == players[0].id
    assert ti["player_instructions"][0]["carry_ball"] == 4

    assert len(ti["situational_rules"]) == 1
    assert ti["situational_rules"][0]["id"] == "chase"
    assert ti["situational_rules"][0]["override"]["tempo"] == 4
