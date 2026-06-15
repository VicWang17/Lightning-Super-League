"""
Integration tests for AI tactics advisor.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Team, User, Player, PlayerPersonality, PlayerPosition, PlayerStatus, TeamTrainingAIProfile
from app.services.ai_tactics_advisor import AITacticsAdvisor


async def _create_ai_team(db: AsyncSession, name: str = "AI FC") -> Team:
    user = User(username=f"ai_{name.lower().replace(' ', '_')}", email=f"ai_{name}@test.com", is_ai=True, hashed_password="fake")
    db.add(user)
    await db.flush()

    team = Team(name=name, user_id=user.id)
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
async def test_generate_default_tactics_creates_team_tactics(db: AsyncSession):
    team = await _create_ai_team(db)

    # Create a balanced squad for F01
    await _create_player(db, team.id, PlayerPosition.GK, "GK")
    await _create_player(db, team.id, PlayerPosition.DF, "DF1")
    await _create_player(db, team.id, PlayerPosition.DF, "DF2")
    await _create_player(db, team.id, PlayerPosition.MF, "MF1")
    await _create_player(db, team.id, PlayerPosition.MF, "MF2")
    await _create_player(db, team.id, PlayerPosition.MF, "MF3")
    await _create_player(db, team.id, PlayerPosition.FW, "FW1")
    await _create_player(db, team.id, PlayerPosition.FW, "FW2")

    advisor = AITacticsAdvisor(db)
    record = await advisor.generate_default_tactics(team.id)

    assert record.team_id == team.id
    assert record.formation_id in {"F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08"}
    assert len(record.lineup_player_ids) == 8
    assert record.ai_profile is not None
    assert record.ai_profile.get("style") is not None

    instructions = record.team_instructions
    assert "situational_rules" in instructions
    assert len(instructions["situational_rules"]) == 2
    assert any(rule["name"] == "落后追分" for rule in instructions["situational_rules"])
    assert any(rule["name"] == "领先稳守" for rule in instructions["situational_rules"])


@pytest.mark.asyncio
async def test_generate_default_tactics_uses_existing_profile(db: AsyncSession):
    team = await _create_ai_team(db)
    profile = TeamTrainingAIProfile(team_id=team.id, style="attacking")
    db.add(profile)
    await db.flush()

    # Attacking squad: 1 GK, 1 DF, 2 MF, 4 FW
    await _create_player(db, team.id, PlayerPosition.GK, "GK")
    await _create_player(db, team.id, PlayerPosition.DF, "DF1")
    await _create_player(db, team.id, PlayerPosition.MF, "MF1")
    await _create_player(db, team.id, PlayerPosition.MF, "MF2")
    await _create_player(db, team.id, PlayerPosition.FW, "FW1")
    await _create_player(db, team.id, PlayerPosition.FW, "FW2")
    await _create_player(db, team.id, PlayerPosition.FW, "FW3")
    await _create_player(db, team.id, PlayerPosition.FW, "FW4")

    advisor = AITacticsAdvisor(db)
    record = await advisor.generate_default_tactics(team.id)

    assert record.ai_profile.get("style") == "attacking"
    assert record.formation_id in {"F03", "F05"}


@pytest.mark.asyncio
async def test_generate_for_all_ai_teams(db: AsyncSession):
    team1 = await _create_ai_team(db, "AI One")
    team2 = await _create_ai_team(db, "AI Two")

    for team in [team1, team2]:
        for i in range(8):
            pos = PlayerPosition.GK if i == 0 else PlayerPosition.FW
            await _create_player(db, team.id, pos, f"P{i}")

    advisor = AITacticsAdvisor(db)
    result = await advisor.generate_for_all_ai_teams()

    # The test DB may contain pre-existing AI teams; just verify the two
    # newly created teams are included in the count.
    assert result["total"] >= 2
    assert result["created"] >= 2
