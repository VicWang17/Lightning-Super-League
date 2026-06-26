"""
Awards router - 球员荣誉/奖项 API
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.base import ResponseSchema
from app.schemas.award import (
    PlayerAwardResponse,
    PlayerAwardSummary,
    SeasonAwardsResponse,
    LeagueAwardsResponse,
    CupAwardsResponse,
)
from app.services.award_service import AwardService
from app.models.player_award import PlayerAward, AwardType, AwardLevel
from app.models.player import Player
from app.models.league import League
from app.models.season import Season
from app.models.season import CupCompetition
from sqlalchemy import select

router = APIRouter(prefix="/awards", tags=["awards"])


def _award_to_response(award: PlayerAward) -> PlayerAwardResponse:
    """将 PlayerAward 模型转换为响应 schema"""
    return PlayerAwardResponse(
        id=award.id,
        player_id=award.player_id,
        player_name=award.player.name if award.player else None,
        player_avatar_url=award.player.avatar_url if award.player else None,
        player_position=award.player.position.value if award.player and award.player.position else None,
        season_id=award.season_id,
        season_number=award.season_number,
        award_type=award.award_type.value,
        award_level=award.award_level.value,
        league_id=award.league_id,
        league_name=award.league.name if award.league else None,
        cup_id=award.cup_id,
        cup_name=award.cup.name if award.cup else None,
        fixture_id=award.fixture_id,
        position=award.position,
        metadata=award.award_metadata,
        description=award.description,
        created_at=award.created_at,
    )


# ===== 手动触发接口（调试用） =====

@router.post("/match-mvp/{fixture_id}", response_model=ResponseSchema[Optional[PlayerAwardResponse]])
async def trigger_match_mvp(fixture_id: str, db: AsyncSession = Depends(get_db)):
    """手动触发单场 MVP 评选"""
    from app.models.match_result import MatchResult
    result = await db.get(MatchResult, fixture_id)
    if not result:
        raise HTTPException(status_code=404, detail="比赛结果不存在")

    award = await AwardService.award_match_mvp(fixture_id, result, db)
    await db.commit()
    if award:
        # 刷新关联对象
        await db.refresh(award, ["player", "season", "league", "cup"])
    return ResponseSchema(
        success=award is not None,
        data=_award_to_response(award) if award else None,
    )


@router.post("/league/{league_id}/season-end", response_model=ResponseSchema[List[PlayerAwardResponse]])
async def trigger_league_awards(league_id: str, season_id: str, db: AsyncSession = Depends(get_db)):
    """手动触发联赛奖项评选"""
    awards = await AwardService.award_league_end_of_season(league_id, season_id, db)
    await db.commit()
    for a in awards:
        await db.refresh(a, ["player", "league"])
    return ResponseSchema(
        success=True,
        data=[_award_to_response(a) for a in awards],
    )


@router.post("/cup/{cup_id}/end", response_model=ResponseSchema[List[PlayerAwardResponse]])
async def trigger_cup_awards(cup_id: str, season_id: str, db: AsyncSession = Depends(get_db)):
    """手动触发杯赛奖项评选"""
    awards = await AwardService.award_cup_end(cup_id, season_id, db)
    await db.commit()
    for a in awards:
        await db.refresh(a, ["player", "cup"])
    return ResponseSchema(
        success=True,
        data=[_award_to_response(a) for a in awards],
    )


@router.post("/season-end/{season_id}", response_model=ResponseSchema[List[PlayerAwardResponse]])
async def trigger_season_awards(season_id: str, db: AsyncSession = Depends(get_db)):
    """手动触发赛季大奖评选"""
    awards = await AwardService.award_season_end(season_id, db)
    await db.commit()
    for a in awards:
        await db.refresh(a, ["player"])
    return ResponseSchema(
        success=True,
        data=[_award_to_response(a) for a in awards],
    )


# ===== 查询接口 =====

@router.get("/player/{player_id}", response_model=ResponseSchema[List[PlayerAwardResponse]])
async def get_player_awards(player_id: str, db: AsyncSession = Depends(get_db)):
    """获取球员荣誉列表"""
    awards = await AwardService.get_player_awards(player_id, db)
    return ResponseSchema(
        success=True,
        data=[_award_to_response(a) for a in awards],
    )


@router.get("/player/{player_id}/summary", response_model=ResponseSchema[PlayerAwardSummary])
async def get_player_award_summary(player_id: str, db: AsyncSession = Depends(get_db)):
    """获取球员荣誉统计摘要"""
    summary = await AwardService.get_player_award_summary(player_id, db)
    return ResponseSchema(
        success=True,
        data=PlayerAwardSummary(**summary),
    )


@router.get("/season/{season_id}", response_model=ResponseSchema[SeasonAwardsResponse])
async def get_season_awards(season_id: str, db: AsyncSession = Depends(get_db)):
    """获取某赛季全部大奖"""
    season = await db.get(Season, season_id)
    if not season:
        raise HTTPException(status_code=404, detail="赛季不存在")

    grouped = await AwardService.get_season_awards(season_id, db)

    def _first(awards: List[PlayerAward]) -> Optional[PlayerAwardResponse]:
        if not awards:
            return None
        return _award_to_response(awards[0])

    for awards in grouped.values():
        for a in awards:
            await db.refresh(a, ["player"])

    return ResponseSchema(
        success=True,
        data=SeasonAwardsResponse(
            season_id=season_id,
            season_number=season.season_number,
            best_player=_first(grouped.get(AwardType.SEASON_BEST_PLAYER, [])),
            best_fw=_first(grouped.get(AwardType.SEASON_BEST_FW, [])),
            best_mf=_first(grouped.get(AwardType.SEASON_BEST_MF, [])),
            best_df=_first(grouped.get(AwardType.SEASON_BEST_DF, [])),
            best_gk=_first(grouped.get(AwardType.SEASON_BEST_GK, [])),
            golden_boot=_first(grouped.get(AwardType.SEASON_GOLDEN_BOOT, [])),
            playmaker=_first(grouped.get(AwardType.SEASON_PLAYMAKER, [])),
            golden_glove=_first(grouped.get(AwardType.SEASON_GOLDEN_GLOVE, [])),
            golden_wall=_first(grouped.get(AwardType.SEASON_GOLDEN_WALL, [])),
        ),
    )


@router.get("/league/{league_id}", response_model=ResponseSchema[LeagueAwardsResponse])
async def get_league_awards(
    league_id: str,
    season_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某联赛某赛季奖项"""
    league = await db.get(League, league_id)
    if not league:
        raise HTTPException(status_code=404, detail="联赛不存在")

    awards = await AwardService.get_league_awards(league_id, season_id, db)
    for a in awards:
        await db.refresh(a, ["player"])

    def _first_of_type(atype: AwardType) -> Optional[PlayerAwardResponse]:
        items = [a for a in awards if a.award_type == atype]
        return _award_to_response(items[0]) if items else None

    season = await db.get(Season, season_id)
    season_number = season.season_number if season else 0

    return ResponseSchema(
        success=True,
        data=LeagueAwardsResponse(
            league_id=league_id,
            season_id=season_id,
            season_number=season_number,
            team_of_season=[_award_to_response(a) for a in awards if a.award_type == AwardType.LEAGUE_TEAM_OF_SEASON],
            best_fw=_first_of_type(AwardType.LEAGUE_BEST_FW),
            best_mf=_first_of_type(AwardType.LEAGUE_BEST_MF),
            best_df=_first_of_type(AwardType.LEAGUE_BEST_DF),
            best_gk=_first_of_type(AwardType.LEAGUE_BEST_GK),
            golden_boot=_first_of_type(AwardType.LEAGUE_GOLDEN_BOOT),
            playmaker=_first_of_type(AwardType.LEAGUE_PLAYMAKER),
            golden_glove=_first_of_type(AwardType.LEAGUE_GOLDEN_GLOVE),
            golden_wall=_first_of_type(AwardType.LEAGUE_GOLDEN_WALL),
        ),
    )


@router.get("/cup/{cup_id}", response_model=ResponseSchema[CupAwardsResponse])
async def get_cup_awards(
    cup_id: str,
    season_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某杯赛某赛季奖项"""
    cup = await db.get(CupCompetition, cup_id)
    if not cup:
        raise HTTPException(status_code=404, detail="杯赛不存在")

    awards = await AwardService.get_cup_awards(cup_id, season_id, db)
    for a in awards:
        await db.refresh(a, ["player"])

    def _first_of_type(atype: AwardType) -> Optional[PlayerAwardResponse]:
        items = [a for a in awards if a.award_type == atype]
        return _award_to_response(items[0]) if items else None

    season = await db.get(Season, season_id)
    season_number = season.season_number if season else 0

    return ResponseSchema(
        success=True,
        data=CupAwardsResponse(
            cup_id=cup_id,
            season_id=season_id,
            season_number=season_number,
            golden_boot=_first_of_type(AwardType.CUP_GOLDEN_BOOT),
            playmaker=_first_of_type(AwardType.CUP_PLAYMAKER),
            golden_glove=_first_of_type(AwardType.CUP_GOLDEN_GLOVE),
            golden_wall=_first_of_type(AwardType.CUP_GOLDEN_WALL),
        ),
    )


@router.get("/season/{season_id}/leagues", response_model=ResponseSchema[List[LeagueAwardsResponse]])
async def get_all_league_awards_for_season(
    season_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取某赛季所有联赛的奖项"""
    season = await db.get(Season, season_id)
    if not season:
        raise HTTPException(status_code=404, detail="赛季不存在")

    # 获取所有联赛
    leagues_result = await db.execute(select(League))
    leagues = leagues_result.scalars().all()

    results: List[LeagueAwardsResponse] = []
    for league in leagues:
        awards = await AwardService.get_league_awards(league.id, season_id, db)
        for a in awards:
            await db.refresh(a, ["player"])

        def _first_of_type(atype: AwardType) -> Optional[PlayerAwardResponse]:
            items = [a for a in awards if a.award_type == atype]
            return _award_to_response(items[0]) if items else None

        results.append(LeagueAwardsResponse(
            league_id=league.id,
            season_id=season_id,
            season_number=season.season_number,
            team_of_season=[_award_to_response(a) for a in awards if a.award_type == AwardType.LEAGUE_TEAM_OF_SEASON],
            best_fw=_first_of_type(AwardType.LEAGUE_BEST_FW),
            best_mf=_first_of_type(AwardType.LEAGUE_BEST_MF),
            best_df=_first_of_type(AwardType.LEAGUE_BEST_DF),
            best_gk=_first_of_type(AwardType.LEAGUE_BEST_GK),
            golden_boot=_first_of_type(AwardType.LEAGUE_GOLDEN_BOOT),
            playmaker=_first_of_type(AwardType.LEAGUE_PLAYMAKER),
            golden_glove=_first_of_type(AwardType.LEAGUE_GOLDEN_GLOVE),
            golden_wall=_first_of_type(AwardType.LEAGUE_GOLDEN_WALL),
        ))

    return ResponseSchema(success=True, data=results)
