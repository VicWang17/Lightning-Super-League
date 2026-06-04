"""
Integration tests for transfer market
"""
import pytest
import pytest_asyncio
from decimal import Decimal
from datetime import datetime, timedelta

from app.models import (
    User,
    Team,
    League,
    LeagueSystem,
    Season,
    SeasonStatus,
    Player,
    PlayerPosition,
    PlayerStatus,
    PlayerRace,
    PlayerPersonality,
    ContractType,
    PotentialLetter,
    SquadRole,
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus as FreeAgentListingStatus,
    Mail,
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
from app.models.finance import TransactionSourceType, TransactionDirection, TeamSeasonFinance
from app.services.transfer_service import TransferService
from app.services.ai_transfer_service import AITransferService
from app.core.events import EventQueue, EventType


@pytest_asyncio.fixture
async def transfer_setup(db):
    """创建测试所需的球队、球员、赛季"""
    # 创建联赛系统
    league_system = LeagueSystem(name="测试联赛", code="TEST", description="测试")
    db.add(league_system)
    await db.flush()

    league = League(system_id=league_system.id, level=1, name="L1")
    db.add(league)
    await db.flush()

    # 创建赛季
    season = Season(
        season_number=1,
        zone_id=1,
        start_date=datetime.utcnow(),
        status=SeasonStatus.ONGOING,
        current_day=10,
        total_days=42,
    )
    db.add(season)
    await db.flush()

    # 创建用户和球队
    user_a = User(username="a", email="a@test.com", hashed_password="x", nickname="TeamA")
    user_b = User(username="b", email="b@test.com", hashed_password="x", nickname="TeamB")
    db.add_all([user_a, user_b])
    await db.flush()

    team_a = Team(name="TeamA", user_id=user_a.id, current_league_id=league.id, current_season_id=season.id)
    team_b = Team(name="TeamB", user_id=user_b.id, current_league_id=league.id, current_season_id=season.id)
    db.add_all([team_a, team_b])
    await db.flush()

    # 创建球队财务
    from app.models.team import TeamFinance
    finance_a = TeamFinance(team_id=team_a.id, balance=Decimal("50000000"))
    finance_b = TeamFinance(team_id=team_b.id, balance=Decimal("50000000"))
    db.add_all([finance_a, finance_b])
    await db.flush()

    # 创建球员（TeamA 拥有）
    players = []
    for i in range(12):
        p = Player(
            name=f"Player{i}",
            race=PlayerRace.ASIAN,
            position=PlayerPosition.FW if i < 3 else PlayerPosition.MF if i < 7 else PlayerPosition.DF,
            preferred_foot="RIGHT",
            height=180,
            weight=75,
            birth_offset=-22,
            team_id=team_a.id,
            contract_type=ContractType.NORMAL,
            contract_end_season=3,
            wage=Decimal("1000000"),
            potential_max=50,
            personality=PlayerPersonality.PROFESSIONAL,
            status=PlayerStatus.ACTIVE,
        )
        players.append(p)
    db.add_all(players)
    await db.flush()

    # 创建 TeamB 球员
    players_b = []
    for i in range(12):
        p = Player(
            name=f"PlayerB{i}",
            race=PlayerRace.WESTERN,
            position=PlayerPosition.FW if i < 3 else PlayerPosition.MF if i < 7 else PlayerPosition.DF,
            preferred_foot="RIGHT",
            height=180,
            weight=75,
            birth_offset=-22,
            team_id=team_b.id,
            contract_type=ContractType.NORMAL,
            contract_end_season=3,
            wage=Decimal("1000000"),
            potential_max=45,
            personality=PlayerPersonality.PROFESSIONAL,
            status=PlayerStatus.ACTIVE,
        )
        players_b.append(p)
    db.add_all(players_b)
    await db.flush()

    return {
        "season": season,
        "league": league,
        "team_a": team_a,
        "team_b": team_b,
        "players_a": players,
        "players_b": players_b,
    }


class TestValuation:
    @pytest.mark.asyncio
    async def test_calculate_market_value(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        value = await service.calculate_market_value(player.id, transfer_setup["team_a"].id)
        assert value > 0


class TestListPlayer:
    @pytest.mark.asyncio
    async def test_list_player_success(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team = transfer_setup["team_a"]

        market_value = await service.calculate_market_value(player.id, team.id)
        list_price = market_value * Decimal("1.0")

        listing = await service.list_player(player.id, team.id, list_price)
        assert listing.status == TransferListingStatus.ACTIVE
        assert listing.list_price == list_price

    @pytest.mark.asyncio
    async def test_list_player_below_min_price_fails(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team = transfer_setup["team_a"]

        market_value = await service.calculate_market_value(player.id, team.id)
        with pytest.raises(ValueError, match="挂牌价"):
            await service.list_player(player.id, team.id, market_value * Decimal("0.50"))


class TestCreateOffer:
    @pytest.mark.asyncio
    async def test_create_offer_success(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team_a = transfer_setup["team_a"]
        team_b = transfer_setup["team_b"]

        market_value = await service.calculate_market_value(player.id, team_a.id)
        offer = await service.create_offer(player.id, team_b.id, market_value * Decimal("1.2"))

        assert offer.offer_kind == OfferKind.INITIAL
        assert offer.status == OfferStatus.PENDING_RESPONSE

    @pytest.mark.asyncio
    async def test_create_offer_exceeds_daily_quota(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team_b = transfer_setup["team_b"]
        market_value = await service.calculate_market_value(player.id, transfer_setup["team_a"].id)

        # 发送 2 次
        await service.create_offer(player.id, team_b.id, market_value * Decimal("1.2"))
        await service.create_offer(transfer_setup["players_a"][1].id, team_b.id, market_value * Decimal("1.2"))

        # 第 3 次应失败
        with pytest.raises(ValueError, match="额度"):
            await service.create_offer(transfer_setup["players_a"][2].id, team_b.id, market_value * Decimal("1.2"))


class TestOfferChain:
    @pytest.mark.asyncio
    async def test_full_negotiation_chain(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team_a = transfer_setup["team_a"]
        team_b = transfer_setup["team_b"]

        market_value = await service.calculate_market_value(player.id, team_a.id)

        # 初始报价
        initial = await service.create_offer(player.id, team_b.id, market_value)

        # 反报价
        counter = await service.create_counter_offer(initial.id, team_a.id, market_value * Decimal("1.1"))
        assert counter.offer_kind == OfferKind.COUNTER

        # 最终报价
        final = await service.create_final_offer(counter.negotiation_id, team_b.id, market_value * Decimal("1.05"))
        assert final.offer_kind == OfferKind.FINAL

        # 接受
        record = await service.accept_offer(final.id, team_a.id)
        assert record.transfer_type == TransferType.CLUB_TRANSFER

        # 检查球员转队
        await db.refresh(player)
        assert player.team_id == team_b.id


class TestRelease:
    @pytest.mark.asyncio
    async def test_release_preview(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team = transfer_setup["team_a"]

        preview = await service.preview_release_penalty(player.id, team.id)
        assert preview["can_release"] is True
        assert preview["final_penalty"] > 0

    @pytest.mark.asyncio
    async def test_release_player(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team = transfer_setup["team_a"]

        record = await service.release_player_with_penalty(player.id, team.id)
        assert record.transfer_type == TransferType.RELEASE

        await db.refresh(player)
        assert player.team_id is None
        assert player.contract_type == ContractType.FREE


class TestExpiredOffers:
    @pytest.mark.asyncio
    async def test_expired_non_listed_offer_auto_rejected(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team_b = transfer_setup["team_b"]
        market_value = await service.calculate_market_value(player.id, transfer_setup["team_a"].id)

        offer = await service.create_offer(player.id, team_b.id, market_value)

        # 模拟过期
        from app.services.game_clock_state import GameClockStateService
        clock = GameClockStateService(db)
        now = await clock.now()
        stats = await service.process_expired_offers(now + timedelta(days=4))

        assert stats["auto_rejected"] >= 1

    @pytest.mark.asyncio
    async def test_expired_listed_offer_auto_accepted(self, db, transfer_setup):
        service = TransferService(db)
        player = transfer_setup["players_a"][0]
        team_a = transfer_setup["team_a"]
        team_b = transfer_setup["team_b"]

        market_value = await service.calculate_market_value(player.id, team_a.id)

        # 挂牌
        listing = await service.list_player(player.id, team_a.id, market_value)

        # 报价
        offer = await service.create_offer(player.id, team_b.id, market_value, listing_id=listing.id)

        # 模拟过期
        from app.services.game_clock_state import GameClockStateService
        clock = GameClockStateService(db)
        now = await clock.now()
        stats = await service.process_expired_offers(now + timedelta(days=4))

        assert stats["auto_accepted"] >= 1
