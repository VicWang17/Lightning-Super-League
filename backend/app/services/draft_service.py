"""
Draft Service - 选秀系统服务
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 第 9 节实现。
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, asc, update

from app.models import (
    Player,
    PlayerStatus,
    ContractType,
    SquadRole,
    OriginType,
    YouthAcademyPlayer,
    AcademyPlayerStatus,
    FreeAgentListing,
    FreeAgentOrigin,
    ListingStatus,
    Season,
    SeasonStatus,
    Team,
)
from app.models.league import League, LeagueStanding
from app.models.draft_pool import (
    DraftPool,
    DraftPoolStatus,
    DraftPoolPlayer,
    DraftPoolPlayerStatus,
    DraftPreference,
    DraftSelection,
    DraftSelectionStatus,
)
from app.core.formats import SeasonTimelineConfig
from app.services.contract_service import ContractService
from app.services.player_generator import estimate_initial_wage
from app.core.logging import get_logger

logger = get_logger("app.draft")


class DraftService:
    """选秀系统服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =====================================================================
    # 创建选秀池
    # =====================================================================
    
    async def create_draft_pools(self, season_id: str) -> Dict[str, Any]:
        """赛季末：将未签约青训球员按联赛聚合创建选秀池
        
        由 RosterLifecycleService.close_season 或事件调用。
        """
        season = await self._get_season(season_id)
        if not season:
            return {"created": 0, "errors": ["Season not found"]}
        
        # 获取所有状态为 released_to_draft 的青训球员
        result = await self.db.execute(
            select(YouthAcademyPlayer, Player, Team)
            .join(Player, YouthAcademyPlayer.player_id == Player.id)
            .join(Team, YouthAcademyPlayer.team_id == Team.id)
            .where(
                and_(
                    YouthAcademyPlayer.season_id == season_id,
                    YouthAcademyPlayer.status == AcademyPlayerStatus.RELEASED_TO_DRAFT,
                )
            )
        )
        rows = result.all()
        
        if not rows:
            logger.info(f"No academy players to draft for season {season_id}")
            return {"created": 0, "pools": []}
        
        # 按联赛分组
        by_league: Dict[str, List] = {}
        for academy_player, player, team in rows:
            league_id = team.current_league_id
            if not league_id:
                continue
            by_league.setdefault(league_id, []).append((academy_player, player, team))
        
        created_pools = []
        for league_id, players in by_league.items():
            try:
                pool = await self._create_pool_for_league(season, league_id, players)
                created_pools.append({"league_id": league_id, "pool_id": pool.id, "players": len(players)})
            except Exception as e:
                logger.exception(f"Failed to create draft pool for league {league_id}")
        
        await self.db.commit()
        logger.info(f"Created {len(created_pools)} draft pools for season {season_id}")
        return {"created": len(created_pools), "pools": created_pools}
    
    async def _create_pool_for_league(
        self,
        season: Season,
        league_id: str,
        players: List,
    ) -> DraftPool:
        """为单个联赛创建选秀池"""
        # 检查是否已有选秀池
        existing = await self.db.execute(
            select(DraftPool).where(
                and_(DraftPool.season_id == season.id, DraftPool.league_id == league_id)
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Draft pool already exists for league {league_id}")
        
        pool = DraftPool(
            season_id=season.id,
            league_id=league_id,
            status=DraftPoolStatus.PREPARING,
            opened_at_day=season.total_days - 3 if season.total_days else 22,
            draft_day=season.total_days - 1 if season.total_days else 24,
        )
        self.db.add(pool)
        await self.db.flush()
        
        # 排序：OVR 降序、潜力降序、年龄升序
        sorted_players = sorted(
            players,
            key=lambda x: (-x[1].ovr, -self._potential_value(x[1].potential_letter), abs(x[1].birth_offset))
        )
        
        for rank, (academy_player, player, team) in enumerate(sorted_players, 1):
            pool_player = DraftPoolPlayer(
                draft_pool_id=pool.id,
                player_id=player.id,
                source_team_id=team.id,
                status=DraftPoolPlayerStatus.AVAILABLE,
                rank_snapshot=rank,
            )
            self.db.add(pool_player)
            
            # 更新青训球员状态
            academy_player.status = AcademyPlayerStatus.DRAFTED
        
        return pool
    
    def _potential_value(self, letter) -> int:
        """潜力字母转数值用于排序"""
        mapping = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
        return mapping.get(letter.value if hasattr(letter, "value") else str(letter), 0)
    
    # =====================================================================
    # 查询选秀池
    # =====================================================================
    
    async def get_draft_pool(self, league_id: str, season_id: Optional[str] = None) -> Dict[str, Any]:
        """获取联赛选秀池"""
        if not season_id:
            season = await self._get_current_season()
            season_id = season.id if season else None
        
        if not season_id:
            return {"league_id": league_id, "players": [], "status": "none"}
        
        pool_result = await self.db.execute(
            select(DraftPool).where(
                and_(DraftPool.league_id == league_id, DraftPool.season_id == season_id)
            )
        )
        pool = pool_result.scalar_one_or_none()
        
        if not pool:
            return {"league_id": league_id, "players": [], "status": "none"}
        
        players_result = await self.db.execute(
            select(DraftPoolPlayer, Player, Team)
            .join(Player, DraftPoolPlayer.player_id == Player.id)
            .outerjoin(Team, DraftPoolPlayer.source_team_id == Team.id)
            .where(DraftPoolPlayer.draft_pool_id == pool.id)
            .order_by(asc(DraftPoolPlayer.rank_snapshot))
        )
        rows = players_result.all()
        
        players = []
        for pool_player, player, source_team in rows:
            players.append({
                "pool_player_id": pool_player.id,
                "player_id": player.id,
                "name": player.name,
                "race": player.race.value,
                "avatar_url": player.avatar_url,
                "position": player.position.value,
                "age": abs(player.birth_offset),
                "ovr": player.ovr,
                "potential_letter": player.potential_letter.value,
                "source_team_name": source_team.name if source_team else None,
                "status": pool_player.status.value,
                "rank_snapshot": pool_player.rank_snapshot,
            })
        
        return {
            "pool_id": pool.id,
            "league_id": league_id,
            "season_id": season_id,
            "status": pool.status.value,
            "opened_at_day": pool.opened_at_day,
            "draft_day": pool.draft_day,
            "players": players,
        }
    
    # =====================================================================
    # 志愿管理
    # =====================================================================
    
    async def get_team_preferences(self, draft_pool_id: str, team_id: str) -> List[Dict[str, Any]]:
        """获取球队志愿排序"""
        result = await self.db.execute(
            select(DraftPreference, Player)
            .join(Player, DraftPreference.player_id == Player.id)
            .where(
                and_(
                    DraftPreference.draft_pool_id == draft_pool_id,
                    DraftPreference.team_id == team_id,
                )
            )
            .order_by(asc(DraftPreference.priority))
        )
        rows = result.all()
        
        return [
            {
                "player_id": pref.player_id,
                "name": player.name,
                "position": player.position.value,
                "ovr": player.ovr,
                "potential_letter": player.potential_letter.value,
                "priority": pref.priority,
                "excluded": pref.excluded,
            }
            for pref, player in rows
        ]
    
    async def save_preferences(
        self,
        draft_pool_id: str,
        team_id: str,
        preferences: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """保存球队志愿排序
        
        preferences: [{"player_id": "...", "priority": 1, "excluded": false}, ...]
        """
        # 删除旧志愿
        await self.db.execute(
            select(DraftPreference).where(
                and_(
                    DraftPreference.draft_pool_id == draft_pool_id,
                    DraftPreference.team_id == team_id,
                )
            )
        )
        # 注意：上面只是查询，需要实际删除
        from sqlalchemy import delete
        await self.db.execute(
            delete(DraftPreference).where(
                and_(
                    DraftPreference.draft_pool_id == draft_pool_id,
                    DraftPreference.team_id == team_id,
                )
            )
        )
        
        # 插入新志愿
        for pref in preferences:
            dp = DraftPreference(
                draft_pool_id=draft_pool_id,
                team_id=team_id,
                player_id=pref["player_id"],
                priority=pref.get("priority", 1),
                excluded=pref.get("excluded", False),
            )
            self.db.add(dp)
        
        await self.db.commit()
        return {"saved": len(preferences)}
    
    # =====================================================================
    # 执行选秀
    # =====================================================================
    
    async def run_draft(self, season_id: str) -> Dict[str, Any]:
        """执行选秀分配
        
        按联赛排名倒序，每队选择 1 名。
        """
        season = await self._get_season(season_id)
        if not season:
            return {"selections": 0, "errors": ["Season not found"]}
        
        # 获取所有准备中的选秀池
        pools_result = await self.db.execute(
            select(DraftPool).where(
                and_(
                    DraftPool.season_id == season_id,
                    DraftPool.status.in_([DraftPoolStatus.PREPARING, DraftPoolStatus.PREFERENCES_OPEN]),
                )
            )
        )
        pools = pools_result.scalars().all()
        
        total_selections = 0
        for pool in pools:
            try:
                count = await self._run_draft_for_pool(pool, season)
                total_selections += count
                pool.status = DraftPoolStatus.COMPLETED
            except Exception as e:
                logger.exception(f"Failed to run draft for pool {pool.id}")
        
        await self.db.commit()
        logger.info(f"Draft completed: {total_selections} selections for season {season_id}")
        return {"selections": total_selections}
    
    async def _run_draft_for_pool(self, pool: DraftPool, season: Season) -> int:
        """为单个联赛执行选秀"""
        # 获取联赛排名（按 position DESC，第8名先选）
        standings_result = await self.db.execute(
            select(LeagueStanding, Team)
            .join(Team, LeagueStanding.team_id == Team.id)
            .where(LeagueStanding.league_id == pool.league_id)
            .order_by(desc(LeagueStanding.position))
        )
        standings = standings_result.all()
        
        # 获取选秀池球员
        pool_players_result = await self.db.execute(
            select(DraftPoolPlayer, Player)
            .join(Player, DraftPoolPlayer.player_id == Player.id)
            .where(
                and_(
                    DraftPoolPlayer.draft_pool_id == pool.id,
                    DraftPoolPlayer.status == DraftPoolPlayerStatus.AVAILABLE,
                )
            )
        )
        available_pool_players = {pp.id: (pp, player) for pp, player in pool_players_result.all()}
        
        selection_count = 0
        selection_order = 0
        
        for standing, team in standings:
            selection_order += 1
            
            # 检查 roster 是否已满
            roster_count_result = await self.db.execute(
                select(func.count(Player.id)).where(Player.team_id == team.id)
            )
            roster_count = roster_count_result.scalar() or 0
            if roster_count >= 15:
                logger.info(
                    "Draft pick skipped because roster is full: "
                    f"season={season.id}, pool={pool.id}, team={team.id}, order={selection_order}"
                )
                continue
            
            # 读取志愿
            prefs_result = await self.db.execute(
                select(DraftPreference).where(
                    and_(
                        DraftPreference.draft_pool_id == pool.id,
                        DraftPreference.team_id == team.id,
                        DraftPreference.excluded == False,
                    )
                ).order_by(asc(DraftPreference.priority))
            )
            prefs = prefs_result.scalars().all()
            
            # 优先从志愿中选择
            selected_pool_player = None
            for pref in prefs:
                # 找到对应的 pool_player
                for pp_id, (pp, player) in available_pool_players.items():
                    if player.id == pref.player_id:
                        selected_pool_player = (pp, player)
                        break
                if selected_pool_player:
                    break
            
            # 志愿无可用，按默认排序补选
            if not selected_pool_player:
                sorted_available = sorted(
                    available_pool_players.values(),
                    key=lambda x: x[0].rank_snapshot
                )
                if sorted_available:
                    selected_pool_player = sorted_available[0]
            
            if not selected_pool_player:
                continue  # 池内无可用球员
            
            pool_player, player = selected_pool_player
            
            # 标记为已选
            pool_player.status = DraftPoolPlayerStatus.SELECTED
            pool_player.selected_by_team_id = team.id
            del available_pool_players[pool_player.id]
            
            # 创建选中记录
            expires_at = datetime.utcnow() + timedelta(hours=24)
            selection = DraftSelection(
                draft_pool_id=pool.id,
                team_id=team.id,
                player_id=player.id,
                season_id=season.id,
                status=DraftSelectionStatus.PENDING,
                selection_order=selection_order,
                expires_at=expires_at,
            )
            self.db.add(selection)
            selection_count += 1
        
        await self.db.flush()
        return selection_count
    
    # =====================================================================
    # 查询选秀结果
    # =====================================================================
    
    async def get_draft_results(self, league_id: str, season_id: Optional[str] = None) -> Dict[str, Any]:
        """获取联赛选秀结果"""
        if not season_id:
            season = await self._get_current_season()
            season_id = season.id if season else None
        
        if not season_id:
            return {"league_id": league_id, "selections": []}
        
        pool_result = await self.db.execute(
            select(DraftPool).where(
                and_(DraftPool.league_id == league_id, DraftPool.season_id == season_id)
            )
        )
        pool = pool_result.scalar_one_or_none()
        if not pool:
            return {"league_id": league_id, "selections": []}
        
        selections_result = await self.db.execute(
            select(DraftSelection, Player, Team)
            .join(Player, DraftSelection.player_id == Player.id)
            .join(Team, DraftSelection.team_id == Team.id)
            .where(DraftSelection.draft_pool_id == pool.id)
            .order_by(asc(DraftSelection.selection_order))
        )
        rows = selections_result.all()
        
        selections = []
        for sel, player, team in rows:
            selections.append({
                "selection_id": sel.id,
                "selection_order": sel.selection_order,
                "team_id": team.id,
                "team_name": team.name,
                "player_id": player.id,
                "player_name": player.name,
                "position": player.position.value,
                "ovr": player.ovr,
                "potential_letter": player.potential_letter.value,
                "status": sel.status.value,
                "expires_at": sel.expires_at.isoformat() if sel.expires_at else None,
            })
        
        return {
            "pool_id": pool.id,
            "league_id": league_id,
            "season_id": season_id,
            "status": pool.status.value,
            "selections": selections,
        }
    
    async def get_team_selections(self, team_id: str, season_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取球队待签约选秀结果"""
        if not season_id:
            season = await self._get_current_season()
            season_id = season.id if season else None
        
        if not season_id:
            return []
        
        result = await self.db.execute(
            select(DraftSelection, Player)
            .join(Player, DraftSelection.player_id == Player.id)
            .where(
                and_(
                    DraftSelection.team_id == team_id,
                    DraftSelection.season_id == season_id,
                    DraftSelection.status == DraftSelectionStatus.PENDING,
                )
            )
            .order_by(asc(DraftSelection.selection_order))
        )
        rows = result.all()
        
        return [
            {
                "selection_id": sel.id,
                "player_id": player.id,
                "name": player.name,
                "race": player.race.value,
                "avatar_url": player.avatar_url,
                "position": player.position.value,
                "age": abs(player.birth_offset),
                "ovr": player.ovr,
                "potential_letter": player.potential_letter.value,
                "expires_at": sel.expires_at.isoformat() if sel.expires_at else None,
            }
            for sel, player in rows
        ]
    
    # =====================================================================
    # 选秀球员签约 / 放弃
    # =====================================================================
    
    async def preview_signing(
        self,
        selection_id: str,
        team_id: str,
        years: int,
        wage: Decimal,
        squad_role: SquadRole = SquadRole.YOUNGSTER,
    ) -> Dict[str, Any]:
        """选秀球员签约预览"""
        selection = await self._get_selection(selection_id)
        if not selection:
            raise ValueError("选秀记录不存在")
        if selection.status != DraftSelectionStatus.PENDING:
            raise ValueError("该选秀记录不可签约")
        if selection.team_id != team_id:
            raise ValueError("无权操作该选秀记录")
        
        contract_service = ContractService(self.db)
        preview = await contract_service.preview_contract_offer(
            player_id=selection.player_id,
            team_id=team_id,
            contract_type=ContractType.ROOKIE,
            years=years,
            wage=wage,
            squad_role=squad_role,
        )
        
        preview_dict = preview.to_dict()
        preview_dict["signing_fee"] = 0
        preview_dict["balance_after_fee"] = float(
            (await self._get_team_balance(team_id)) - Decimal("0")
        )
        preview_dict["can_pay_signing_fee"] = True
        
        return preview_dict
    
    async def sign_selection(
        self,
        selection_id: str,
        team_id: str,
        years: int,
        wage: Decimal,
        squad_role: SquadRole = SquadRole.YOUNGSTER,
    ) -> Dict[str, Any]:
        """签约选秀球员"""
        selection = await self._get_selection(selection_id)
        if not selection:
            raise ValueError("选秀记录不存在")
        if selection.status != DraftSelectionStatus.PENDING:
            raise ValueError("该选秀记录不可签约")
        if selection.team_id != team_id:
            raise ValueError("无权操作该选秀记录")
        
        # 检查 roster
        roster_count_result = await self.db.execute(
            select(func.count(Player.id)).where(Player.team_id == team_id)
        )
        roster_count = roster_count_result.scalar() or 0
        if roster_count >= 15:
            raise ValueError("一线队已满 15 人，无法签约")
        
        contract_service = ContractService(self.db)
        contract = await contract_service.sign_contract(
            player_id=selection.player_id,
            team_id=team_id,
            contract_type=ContractType.ROOKIE,
            years=years,
            wage=wage,
            squad_role=squad_role,
        )
        
        selection.status = DraftSelectionStatus.SIGNED
        
        # 更新球员
        player = await self._get_player(selection.player_id)
        if player:
            player.team_id = team_id
            player.joined_first_team_season = (await self._get_current_season()).season_number
        
        await self.db.commit()
        
        return {
            "contract_id": contract.id,
            "player_id": selection.player_id,
            "team_id": team_id,
            "signing_fee": 0,
        }
    
    async def decline_selection(self, selection_id: str) -> Dict[str, Any]:
        """放弃选秀球员，使其进入自由市场"""
        selection = await self._get_selection(selection_id)
        if not selection:
            raise ValueError("选秀记录不存在")
        if selection.status != DraftSelectionStatus.PENDING:
            raise ValueError("该选秀记录不可放弃")
        
        selection.status = DraftSelectionStatus.DECLINED
        
        # 创建自由市场 listing
        await self._create_free_agent_listing(selection)
        
        await self.db.commit()
        
        return {
            "selection_id": selection_id,
            "status": DraftSelectionStatus.DECLINED.value,
        }
    
    # =====================================================================
    # 过期处理
    # =====================================================================
    
    async def expire_pending_selections(self, season_id: str) -> Dict[str, Any]:
        """处理 24 小时到期的待签约选秀结果
        
        - 玩家球队若未处理，系统尝试自动签约。
        - 自动签约失败则进入自由市场。
        """
        now = datetime.utcnow()
        
        result = await self.db.execute(
            select(DraftSelection, Player, Team)
            .join(Player, DraftSelection.player_id == Player.id)
            .join(Team, DraftSelection.team_id == Team.id)
            .where(
                and_(
                    DraftSelection.season_id == season_id,
                    DraftSelection.status == DraftSelectionStatus.PENDING,
                    DraftSelection.expires_at <= now,
                )
            )
        )
        rows = result.all()
        
        signed = 0
        expired = 0
        
        for selection, player, team in rows:
            # 检查是否是 AI 球队
            user_result = await self.db.execute(
                select(Team.user_id).where(Team.id == team.id)
            )
            user_id = user_result.scalar_one_or_none()
            
            from app.models.user import User
            is_ai = False
            if user_id:
                user_result = await self.db.execute(
                    select(User.is_ai).where(User.id == user_id)
                )
                is_ai = user_result.scalar_one_or_none() or False
            
            # AI 球队已在选秀后处理，这里只处理玩家球队未处理的情况
            # 但为了简化，统一走自动签约逻辑
            try:
                roster_count_result = await self.db.execute(
                    select(func.count(Player.id)).where(Player.team_id == team.id)
                )
                roster_count = roster_count_result.scalar() or 0
                if roster_count >= 15:
                    raise ValueError("Roster full")
                
                # 自动签约：默认 2 年，建议工资 0.70
                contract_service = ContractService(self.db)
                recommended = await contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    squad_role=SquadRole.YOUNGSTER,
                )
                
                await contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    years=2,
                    wage=recommended,
                    squad_role=SquadRole.YOUNGSTER,
                )
                
                selection.status = DraftSelectionStatus.SIGNED
                player.team_id = team.id
                signed += 1
            except Exception:
                # 自动签约失败，进入自由市场
                selection.status = DraftSelectionStatus.EXPIRED
                await self._create_free_agent_listing(selection)
                expired += 1
        
        await self.db.commit()
        logger.info(f"Draft expiration processed: {signed} signed, {expired} expired for season {season_id}")
        return {"signed": signed, "expired": expired}
    
    # =====================================================================
    # 内部辅助
    # =====================================================================
    
    async def _create_free_agent_listing(self, selection: DraftSelection) -> None:
        """为放弃或过期的选秀球员创建自由市场 listing"""
        player = await self._get_player(selection.player_id)
        if not player:
            return
        
        season = await self._get_season(selection.season_id)
        season_number = season.season_number if season else 1
        
        origin = FreeAgentOrigin.DRAFT_DECLINED if selection.status == DraftSelectionStatus.DECLINED else FreeAgentOrigin.DRAFT_UNSELECTED
        
        listing = FreeAgentListing(
            player_id=player.id,
            season_id=selection.season_id,
            origin=origin,
            signing_fee=Decimal("5000"),  # 选秀相关签字费较低
            recommended_wage=estimate_initial_wage(player.ovr, player.potential_max, abs(player.birth_offset)),
            status=ListingStatus.ACTIVE,
            listed_at_day=season_number,
        )
        self.db.add(listing)
        
        # 更新青训状态
        academy_result = await self.db.execute(
            select(YouthAcademyPlayer).where(YouthAcademyPlayer.player_id == player.id)
        )
        academy_player = academy_result.scalar_one_or_none()
        if academy_player:
            academy_player.status = AcademyPlayerStatus.FREE_MARKET
    
    async def _get_season(self, season_id: str) -> Optional[Season]:
        result = await self.db.execute(select(Season).where(Season.id == season_id))
        return result.scalar_one_or_none()
    
    async def _get_current_season(self) -> Optional[Season]:
        result = await self.db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number)).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_selection(self, selection_id: str) -> Optional[DraftSelection]:
        result = await self.db.execute(
            select(DraftSelection).where(DraftSelection.id == selection_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()
    
    async def _get_team_balance(self, team_id: str) -> Decimal:
        from app.models.team import TeamFinance
        result = await self.db.execute(
            select(TeamFinance.balance).where(TeamFinance.team_id == team_id)
        )
        balance = result.scalar_one_or_none()
        return balance or Decimal("0")
