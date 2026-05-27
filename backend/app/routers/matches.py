"""
Match API routes backed by fixtures and Go engine results.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models.match_result import MatchResult
from app.models.season import Fixture, FixtureStatus
from app.models.team import Team
from app.schemas import ResponseSchema, PaginatedResponse
from app.services.match_engine_client import get_match_engine_client
from app.services.match_simulator import MatchSimulator

router = APIRouter(prefix="/matches", tags=["比赛"])


@router.get("/", response_model=ResponseSchema[PaginatedResponse[dict]])
async def list_matches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    league_id: Optional[str] = Query(None),
    team_id: Optional[str] = Query(None),
    season_id: Optional[str] = Query(None),
    matchday: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Fixture)
    conditions = []
    if league_id:
        conditions.append(Fixture.league_id == league_id)
    if team_id:
        conditions.append(or_(Fixture.home_team_id == team_id, Fixture.away_team_id == team_id))
    if season_id:
        conditions.append(Fixture.season_id == season_id)
    if matchday:
        conditions.append(Fixture.round_number == matchday)
    if status:
        conditions.append(Fixture.status == status)
    if from_date:
        conditions.append(Fixture.scheduled_at >= from_date)
    if to_date:
        conditions.append(Fixture.scheduled_at <= to_date)
    if conditions:
        query = query.where(and_(*conditions))

    total_result = await db.execute(query)
    all_items = list(total_result.scalars().all())
    items = all_items[(page - 1) * page_size : page * page_size]
    return ResponseSchema(
        data=PaginatedResponse.create(
            items=[_fixture_payload(item) for item in items],
            total=len(all_items),
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{match_id}", response_model=ResponseSchema[dict])
async def get_match(match_id: str, db: AsyncSession = Depends(get_db)):
    fixture = await _get_fixture(db, match_id)
    result = await _get_engine_result(db, match_id)
    payload = _fixture_payload(fixture)
    payload["home_team_name"] = await team_name(db, fixture.home_team_id)
    payload["away_team_name"] = await team_name(db, fixture.away_team_id)
    if result:
        payload["engine_result"] = _result_payload(result)
    return ResponseSchema(data=payload)


@router.get("/{match_id}/live", response_model=ResponseSchema[dict])
async def get_match_live(match_id: str, db: AsyncSession = Depends(get_db)):
    fixture = await _get_fixture(db, match_id)
    result = await _get_engine_result(db, match_id)
    return ResponseSchema(
        data={
            "match_id": match_id,
            "status": fixture.status.value if hasattr(fixture.status, "value") else fixture.status,
            "current_minute": 70 if result and result.resolution in {"extra_time", "penalties"} else 50,
            "home_score": fixture.home_score,
            "away_score": fixture.away_score,
            "events": result.events if result else [],
            "narratives": result.narratives if result else [],
            "stats": result.match_stats if result else {},
        }
    )


@router.get("/{match_id}/stats", response_model=ResponseSchema[dict])
async def get_match_stats(match_id: str, db: AsyncSession = Depends(get_db)):
    await _get_fixture(db, match_id)
    result = await _get_engine_result(db, match_id)
    if not result:
        return ResponseSchema(data={"match_id": match_id, "stats": {}, "player_stats": []})
    return ResponseSchema(
        data={
            "match_id": match_id,
            "stats": result.match_stats,
            "player_stats": result.player_stats,
            "resolution": result.resolution,
            "winner_team_id": result.winner_team_id,
            "penalty_score": result.penalty_score,
        }
    )


@router.get("/{match_id}/lineups", response_model=ResponseSchema[dict])
async def get_match_lineups(match_id: str, db: AsyncSession = Depends(get_db)):
    fixture = await _get_fixture(db, match_id)
    client = get_match_engine_client()
    request = await client._build_request(db, fixture)
    return ResponseSchema(
        data={
            "home_team_name": request["home_team"]["name"],
            "away_team_name": request["away_team"]["name"],
            "home_lineup": request["home_team"]["players"],
            "away_lineup": request["away_team"]["players"],
            "home_bench": request["home_team"]["bench"],
            "away_bench": request["away_team"]["bench"],
            "home_formation": request["home_team"]["formation_id"],
            "away_formation": request["away_team"]["formation_id"],
        }
    )


@router.post("/{match_id}/simulate", response_model=ResponseSchema[dict])
async def simulate_match(match_id: str, db: AsyncSession = Depends(get_db)):
    fixture = await _get_fixture(db, match_id)
    if fixture.status == FixtureStatus.FINISHED:
        result = await _get_engine_result(db, match_id)
        return ResponseSchema(data={"match_id": match_id, "already_finished": True, "result": _result_payload(result) if result else None})

    engine_result = await get_match_engine_client().simulate_fixture(db, fixture)
    match_result = MatchSimulator.from_engine_result(fixture, engine_result)
    await MatchSimulator.apply_result(fixture, match_result, db)
    await db.commit()
    return ResponseSchema(message="比赛模拟完成", data={"match_id": match_id, "result": engine_result})


async def _get_fixture(db: AsyncSession, match_id: str) -> Fixture:
    result = await db.execute(select(Fixture).where(Fixture.id == match_id))
    fixture = result.scalar_one_or_none()
    if not fixture:
        raise HTTPException(status_code=404, detail="Match not found")
    return fixture


async def _get_engine_result(db: AsyncSession, match_id: str) -> Optional[MatchResult]:
    result = await db.execute(select(MatchResult).where(MatchResult.fixture_id == match_id))
    return result.scalar_one_or_none()


async def team_name(db: AsyncSession, team_id: str) -> str:
    result = await db.execute(select(Team.name).where(Team.id == team_id))
    name = result.scalar_one_or_none()
    return name or team_id


def _fixture_payload(fixture: Fixture) -> dict:
    return {
        "id": fixture.id,
        "fixture_type": fixture.fixture_type.value if hasattr(fixture.fixture_type, "value") else fixture.fixture_type,
        "season_id": fixture.season_id,
        "season_day": fixture.season_day,
        "round_number": fixture.round_number,
        "home_team_id": fixture.home_team_id,
        "away_team_id": fixture.away_team_id,
        "home_score": fixture.home_score,
        "away_score": fixture.away_score,
        "status": fixture.status.value if hasattr(fixture.status, "value") else fixture.status,
        "scheduled_at": fixture.scheduled_at.isoformat(),
        "league_id": fixture.league_id,
        "cup_competition_id": fixture.cup_competition_id,
        "cup_stage": fixture.cup_stage,
        "cup_group": fixture.cup_group_name,
    }


def _result_payload(result: MatchResult) -> dict:
    return {
        "winner_team_id": result.winner_team_id,
        "resolution": result.resolution,
        "penalty_score": result.penalty_score,
        "stats": result.match_stats,
        "player_stats": result.player_stats,
        "events": result.events,
        "narratives": result.narratives,
    }
