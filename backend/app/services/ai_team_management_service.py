"""
AI Team Management Service - AI 球队自主运营服务
按设计文档 CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md 第 14 节实现。

目标：保证全 AI 联赛可以持续运转，无需玩家干预。
"""
import random
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, asc

from app.models import (
    Player,
    PlayerPosition,
    PlayerStatus,
    ContractType,
    SquadRole,
    OriginType,
    YouthAcademyPlayer,
    AcademyPlayerStatus,
    GrowthSpeed,
    FreeAgentListing,
    ListingStatus,
    Season,
    SeasonStatus,
    Team,
    User,
)
from app.models.player_contract import PlayerContract, ContractStatus
from app.models.draft_pool import (
    DraftPool,
    DraftPoolPlayer,
    DraftPoolPlayerStatus,
    DraftPreference,
    DraftSelection,
    DraftSelectionStatus,
)
from app.models.league import League, LeagueStanding
from app.models.wage_config import WageConfig, WageConfigType
from app.services.contract_service import ContractService
from app.services.finance_service import FinanceService
from app.core.logging import get_logger

logger = get_logger("app.ai_team_management")


class AITeamManagementService:
    """AI 球队自主运营服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.contract_service = ContractService(db)
    
    # =====================================================================
    # 辅助：获取 AI 球队
    # =====================================================================
    
    async def _get_ai_teams(self) -> List[Team]:
        """获取所有 AI 球队"""
        result = await self.db.execute(
            select(Team)
            .join(User, Team.user_id == User.id)
            .where(User.is_ai == True)
        )
        return list(result.scalars().all())
    
    async def _get_team_players(self, team_id: str) -> List[Player]:
        """获取球队一线队球员"""
        result = await self.db.execute(
            select(Player)
            .where(
                and_(
                    Player.team_id == team_id,
                    Player.status == PlayerStatus.ACTIVE,
                )
            )
            .order_by(desc(Player.ovr))
        )
        return list(result.scalars().all())
    
    async def _get_current_season(self) -> Optional[Season]:
        result = await self.db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING).order_by(desc(Season.season_number)).limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_team_academy_players(self, team_id: str, season_id: str) -> List:
        """获取球队青训营球员"""
        result = await self.db.execute(
            select(YouthAcademyPlayer, Player)
            .join(Player, YouthAcademyPlayer.player_id == Player.id)
            .where(
                and_(
                    YouthAcademyPlayer.team_id == team_id,
                    YouthAcademyPlayer.season_id == season_id,
                    YouthAcademyPlayer.status == AcademyPlayerStatus.IN_ACADEMY,
                )
            )
            .order_by(desc(Player.ovr))
        )
        return list(result.all())
    
    # =====================================================================
    # 1. 赛季开始规划
    # =====================================================================
    
    async def run_season_start_planning(self, season_id: str) -> Dict[str, Any]:
        """赛季开始：AI 球队检查名单结构、工资帽"""
        season = await self._get_current_season()
        if not season:
            return {"processed": 0}
        
        ai_teams = await self._get_ai_teams()
        processed = 0
        
        for team in ai_teams:
            try:
                await self._season_start_for_team(team, season)
                processed += 1
            except Exception as e:
                logger.exception(f"AI season start failed for team {team.id}")
        
        await self.db.commit()
        return {"processed": processed}
    
    async def _season_start_for_team(self, team: Team, season: Season) -> None:
        """单个 AI 球队的赛季开始检查"""
        players = await self._get_team_players(team.id)
        
        # 检查 roster 人数
        if len(players) < 10:
            # 赛季初人数不足，后续自由市场会补
            logger.info(f"AI team {team.id} roster low ({len(players)}), will supplement later")
    
    # =====================================================================
    # 2. 青训刷新后决策
    # =====================================================================
    
    async def run_midseason_academy_decisions(self, season_id: str, day: int) -> Dict[str, Any]:
        """青训刷新后：AI 判断是否签约青训球员"""
        season = await self._get_current_season()
        if not season:
            return {"signed": 0, "declined": 0}
        
        ai_teams = await self._get_ai_teams()
        signed_count = 0
        declined_count = 0
        
        for team in ai_teams:
            try:
                s, d = await _ai_academy_decisions_for_team(self.db, team, season)
                signed_count += s
                declined_count += d
            except Exception as e:
                logger.exception(f"AI academy decision failed for team {team.id}")
        
        await self.db.commit()
        return {"signed": signed_count, "declined": declined_count}
    
    # =====================================================================
    # 3. 选秀志愿
    # =====================================================================
    
    async def run_pre_draft_preferences(self, season_id: str) -> Dict[str, Any]:
        """志愿开放日：为 AI 球队生成选秀志愿"""
        season = await self._get_current_season()
        if not season:
            return {"processed": 0}
        
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
        
        processed = 0
        for pool in pools:
            try:
                count = await self._generate_ai_preferences(pool, season)
                processed += count
            except Exception as e:
                logger.exception(f"AI preferences failed for pool {pool.id}")
        
        await self.db.commit()
        return {"processed": processed}
    
    async def _generate_ai_preferences(self, pool: DraftPool, season: Season) -> int:
        """为单个选秀池的所有 AI 球队生成志愿"""
        # 获取池内球员
        pool_players_result = await self.db.execute(
            select(DraftPoolPlayer, Player)
            .join(Player, DraftPoolPlayer.player_id == Player.id)
            .where(DraftPoolPlayer.draft_pool_id == pool.id)
            .order_by(asc(DraftPoolPlayer.rank_snapshot))
        )
        pool_players = pool_players_result.all()
        
        # 获取联赛内 AI 球队
        teams_result = await self.db.execute(
            select(Team)
            .join(User, Team.user_id == User.id)
            .where(
                and_(
                    User.is_ai == True,
                    Team.current_league_id == pool.league_id,
                )
            )
        )
        ai_teams = teams_result.scalars().all()
        
        for team in ai_teams:
            # 删除旧志愿
            from sqlalchemy import delete
            await self.db.execute(
                delete(DraftPreference).where(
                    and_(
                        DraftPreference.draft_pool_id == pool.id,
                        DraftPreference.team_id == team.id,
                    )
                )
            )
            
            # 计算位置需求
            position_need = await self._calculate_position_need(team.id)
            
            # 按 draft_value_score 排序
            scored = []
            for pp, player in pool_players:
                score = self._calculate_draft_value_score(player, position_need)
                scored.append((pp, player, score))
            
            scored.sort(key=lambda x: -x[2])
            
            # 保存前 10 名志愿
            for priority, (pp, player, score) in enumerate(scored[:10], 1):
                pref = DraftPreference(
                    draft_pool_id=pool.id,
                    team_id=team.id,
                    player_id=player.id,
                    priority=priority,
                    excluded=False,
                )
                self.db.add(pref)
        
        await self.db.flush()
        return len(ai_teams)
    
    def _calculate_draft_value_score(self, player: Player, position_need: Dict[str, int]) -> float:
        """计算选秀价值分"""
        score = float(player.ovr) * 1.0
        
        # 潜力加成
        potential_bonus = {"S": 15, "A": 10, "B": 5, "C": 2, "D": 0}
        score += potential_bonus.get(player.potential_letter.value if hasattr(player.potential_letter, "value") else str(player.potential_letter), 0)
        
        # 位置需求加成
        pos = player.position.value if hasattr(player.position, "value") else str(player.position)
        score += position_need.get(pos, 0) * 3
        
        # 年龄惩罚（18岁无惩罚，越小越好）
        age = abs(player.birth_offset)
        if age <= 16:
            score += 3
        elif age == 17:
            score += 1
        
        return score
    
    # =====================================================================
    # 4. 选秀签约决策
    # =====================================================================
    
    async def run_draft_selection_decisions(self, season_id: str) -> Dict[str, Any]:
        """选秀结束后：AI 判断是否签约选中的球员"""
        season = await self._get_current_season()
        if not season:
            return {"signed": 0, "declined": 0}
        
        # 获取所有 pending 的选秀结果
        result = await self.db.execute(
            select(DraftSelection, Player, Team)
            .join(Player, DraftSelection.player_id == Player.id)
            .join(Team, DraftSelection.team_id == Team.id)
            .join(User, Team.user_id == User.id)
            .where(
                and_(
                    DraftSelection.season_id == season_id,
                    DraftSelection.status == DraftSelectionStatus.PENDING,
                    User.is_ai == True,
                )
            )
        )
        rows = result.all()
        
        signed_count = 0
        declined_count = 0
        
        for selection, player, team in rows:
            try:
                should_sign = await self._ai_should_sign_draft_player(team, player, season)
                if should_sign:
                    await self._ai_sign_draft_player(selection, team, player, season)
                    signed_count += 1
                else:
                    await self._ai_decline_draft_player(selection)
                    declined_count += 1
            except Exception as e:
                logger.exception(f"AI draft decision failed for selection {selection.id}")
        
        await self.db.commit()
        return {"signed": signed_count, "declined": declined_count}
    
    async def _ai_should_sign_draft_player(self, team: Team, player: Player, season: Season) -> bool:
        """AI 判断是否签约选秀球员"""
        # 检查 roster
        roster_count_result = await self.db.execute(
            select(func.count(Player.id)).where(Player.team_id == team.id)
        )
        roster_count = roster_count_result.scalar() or 0
        if roster_count >= 15:
            return False
        
        # 计算价值分
        position_need = await self._calculate_position_need(team.id)
        score = self._calculate_draft_value_score(player, position_need)
        
        # 获取联赛级别
        league_level = 3
        if team.current_league_id:
            league_result = await self.db.execute(
                select(League.level).where(League.id == team.current_league_id)
            )
            level = league_result.scalar_one_or_none()
            if level:
                league_level = level
        
        # 门槛按联赛级别调整
        thresholds = {1: 35, 2: 30, 3: 25, 4: 20}
        threshold = thresholds.get(league_level, 25)
        
        return score >= threshold
    
    async def _ai_sign_draft_player(self, selection: DraftSelection, team: Team, player: Player, season: Season) -> None:
        """AI 签约选秀球员"""
        recommended = await self.contract_service.calculate_recommended_wage(
            player_id=player.id,
            team_id=team.id,
            contract_type=ContractType.ROOKIE,
            squad_role=SquadRole.YOUNGSTER,
        )
        
        contract = await self.contract_service.sign_contract(
            player_id=player.id,
            team_id=team.id,
            contract_type=ContractType.ROOKIE,
            years=2,
            wage=recommended,
            squad_role=SquadRole.YOUNGSTER,
        )
        
        selection.status = DraftSelectionStatus.SIGNED
        player.team_id = team.id
        player.joined_first_team_season = season.season_number
    
    async def _ai_decline_draft_player(self, selection: DraftSelection) -> None:
        """AI 放弃选秀球员"""
        selection.status = DraftSelectionStatus.DECLINED
        # 创建自由市场 listing
        from app.services.draft_service import DraftService
        draft_service = DraftService(self.db)
        await draft_service._create_free_agent_listing(selection)
    
    # =====================================================================
    # 5. 赛季末续约与 roster 决策
    # =====================================================================
    
    async def run_season_end_roster_decisions(self, season_id: str) -> Dict[str, Any]:
        """赛季末：AI 续约关键球员、放弃低价值青训"""
        season = await self._get_current_season()
        if not season:
            return {"renewed": 0, "academy_signed": 0, "free_market_signed": 0}
        
        ai_teams = await self._get_ai_teams()
        renewed_count = 0
        academy_signed_count = 0
        free_market_signed_count = 0
        
        for team in ai_teams:
            try:
                r = await self._ai_renew_contracts(team, season)
                renewed_count += r
                
                a = await self._ai_sign_academy_before_season_end(team, season)
                academy_signed_count += a
                
                f = await self._ai_sign_free_market(team, season)
                free_market_signed_count += f
            except Exception as e:
                logger.exception(f"AI season end failed for team {team.id}")
        
        await self.db.commit()
        return {
            "renewed": renewed_count,
            "academy_signed": academy_signed_count,
            "free_market_signed": free_market_signed_count,
        }
    
    async def _ai_renew_contracts(self, team: Team, season: Season) -> int:
        """AI 续约合同即将到期的球员"""
        # 获取球队所有球员
        players = await self._get_team_players(team.id)
        
        # 计算 keep_score
        scored_players = []
        for idx, player in enumerate(players):
            score = await self._calculate_keep_score(team, player, idx, len(players), season)
            scored_players.append((player, score))
        
        # 按分数降序
        scored_players.sort(key=lambda x: -x[1])
        
        # 获取工资帽压力
        finance_service = FinanceService(self.db)
        season_finance = await finance_service._get_or_create_team_season_finance(team.id, season.id)
        total_wage = await finance_service._calculate_team_wage_bill(team.id)
        wage_cap = season_finance.wage_cap if season_finance.wage_cap > 0 else Decimal("1")
        pressure = float(total_wage / wage_cap) if wage_cap > 0 else 0.0
        
        renewed = 0
        max_renew = 6 if pressure > 0.95 else 8
        
        for player, score in scored_players[:max_renew]:
            # 检查合同是否即将到期
            if player.contract_end_season is None:
                continue
            if player.contract_end_season < season.season_number:
                continue  # 已过期，不续约
            if player.contract_end_season > season.season_number + 1:
                continue  # 还有时间
            
            age = season.season_number + abs(player.birth_offset)
            if age >= 34 and score < 50:
                continue  # 34+ 且不是核心，不续约
            
            try:
                years = self._ai_determine_contract_years(age)
                role = self._ai_determine_role(player, idx)
                
                recommended = await self.contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=player.contract_type or ContractType.NORMAL,
                    squad_role=role,
                )
                
                # AI 工资调整
                if score >= 70:
                    wage = recommended
                elif score >= 50:
                    wage = recommended * Decimal("0.95")
                else:
                    wage = recommended * Decimal("0.85")
                
                await self.contract_service.renew_contract(
                    player_id=player.id,
                    team_id=team.id,
                    years=years,
                    wage=wage.quantize(Decimal("1")),
                    squad_role=role,
                )
                renewed += 1
            except Exception as e:
                logger.warning(f"AI renew failed for player {player.id}: {e}")
        
        return renewed
    
    async def _calculate_keep_score(self, team: Team, player: Player, rank: int, total: int, season: Season) -> float:
        """计算球员留队分"""
        score = 0.0
        
        # OVR 分（前 8 名优先）
        if rank < 8:
            score += (8 - rank) * 5
        score += float(player.ovr) * 0.3
        
        # 潜力分
        potential_bonus = {"S": 15, "A": 10, "B": 5, "C": 2, "D": 0}
        score += potential_bonus.get(player.potential_letter.value if hasattr(player.potential_letter, "value") else str(player.potential_letter), 0)
        
        # 年龄分
        age = season.season_number + abs(player.birth_offset)
        if 18 <= age <= 23:
            score += 10
        elif 24 <= age <= 28:
            score += 5
        elif 29 <= age <= 33:
            score += 2
        elif age >= 34:
            score -= 10
        
        # 位置需求分
        position_need = await self._calculate_position_need(team.id)
        pos = player.position.value if hasattr(player.position, "value") else str(player.position)
        score += position_need.get(pos, 0) * 2
        
        # 状态分
        if player.match_form.value if hasattr(player.match_form, "value") else str(player.match_form) in ("HOT", "GOOD"):
            score += 3
        
        return score
    
    def _ai_determine_contract_years(self, age: int) -> int:
        """AI 根据年龄确定合同年限"""
        if 18 <= age <= 24:
            return random.choice([3, 4])
        elif 25 <= age <= 30:
            return random.choice([2, 3])
        elif 31 <= age <= 33:
            return random.choice([1, 2])
        else:
            return 1
    
    def _ai_determine_role(self, player: Player, rank: int) -> SquadRole:
        """AI 确定阵容角色"""
        if rank < 3:
            return SquadRole.KEY_PLAYER
        elif rank < 6:
            return SquadRole.FIRST_TEAM
        elif rank < 9:
            return SquadRole.ROTATION
        elif rank < 12:
            return SquadRole.BACKUP
        else:
            return SquadRole.YOUNGSTER
    
    async def _ai_sign_academy_before_season_end(self, team: Team, season: Season) -> int:
        """赛季末：AI 签约本队青训球员（在选秀前）"""
        academy_players = await self._get_team_academy_players(team.id, season.id)
        if not academy_players:
            return 0
        
        roster_count_result = await self.db.execute(
            select(func.count(Player.id)).where(Player.team_id == team.id)
        )
        roster_count = roster_count_result.scalar() or 0
        
        if roster_count >= 15:
            return 0
        
        # 计算 academy_score
        scored = []
        for academy_player, player in academy_players:
            score = self._calculate_academy_score(player, academy_player, roster_count)
            scored.append((academy_player, player, score))
        
        scored.sort(key=lambda x: -x[2])
        
        signed = 0
        max_sign = 15 - roster_count
        if max_sign > 2:
            max_sign = 2
        
        for academy_player, player, score in scored[:max_sign]:
            if score < 30:
                continue
            try:
                recommended = await self.contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    squad_role=SquadRole.YOUNGSTER,
                )
                
                contract = await self.contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.ROOKIE,
                    years=2,
                    wage=recommended,
                    squad_role=SquadRole.YOUNGSTER,
                )
                
                academy_player.status = AcademyPlayerStatus.SIGNED
                academy_player.signed_at_season = season.season_number
                player.team_id = team.id
                player.joined_first_team_season = season.season_number
                signed += 1
            except Exception as e:
                logger.warning(f"AI academy sign failed for player {player.id}: {e}")
        
        return signed
    
    def _calculate_academy_score(self, player: Player, academy_player, roster_count: int) -> float:
        """计算青训签约分"""
        score = 0.0
        
        # 潜力
        potential_bonus = {"S": 20, "A": 15, "B": 8, "C": 3, "D": 0}
        score += potential_bonus.get(player.potential_letter.value if hasattr(player.potential_letter, "value") else str(player.potential_letter), 0)
        
        # 成长速度
        speed_bonus = {GrowthSpeed.FAST: 10, GrowthSpeed.NORMAL: 5, GrowthSpeed.SLOW: 0}
        score += speed_bonus.get(academy_player.growth_speed, 0)
        
        # OVR
        score += float(player.ovr) * 0.3
        
        # roster 压力惩罚
        if roster_count >= 13:
            score -= 15
        elif roster_count >= 11:
            score -= 5
        
        return score
    
    async def _ai_sign_free_market(self, team: Team, season: Season) -> int:
        """AI 在自由市场签约补人"""
        roster_count_result = await self.db.execute(
            select(func.count(Player.id)).where(Player.team_id == team.id)
        )
        roster_count = roster_count_result.scalar() or 0
        
        if roster_count >= 10:
            return 0  # 人数足够，不主动签自由市场
        
        # 获取自由市场 listing
        listings_result = await self.db.execute(
            select(FreeAgentListing, Player)
            .join(Player, FreeAgentListing.player_id == Player.id)
            .where(
                and_(
                    FreeAgentListing.status == ListingStatus.ACTIVE,
                    FreeAgentListing.season_id == season.id,
                )
            )
            .order_by(desc(Player.ovr))
            .limit(10)
        )
        listings = listings_result.all()
        
        signed = 0
        max_needed = 10 - roster_count
        if max_needed > 3:
            max_needed = 3
        
        for listing, player in listings[:max_needed]:
            if roster_count + signed >= 10:
                break
            try:
                recommended = await self.contract_service.calculate_recommended_wage(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.NORMAL,
                    squad_role=SquadRole.BACKUP,
                )
                
                contract = await self.contract_service.sign_contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_type=ContractType.NORMAL,
                    years=1,
                    wage=recommended,
                    squad_role=SquadRole.BACKUP,
                )
                
                listing.status = ListingStatus.SIGNED
                listing.signed_team_id = team.id
                signed += 1
            except Exception as e:
                logger.warning(f"AI free market sign failed for player {player.id}: {e}")
        
        return signed
    
    # =====================================================================
    # 位置需求计算
    # =====================================================================
    
    async def _calculate_position_need(self, team_id: str) -> Dict[str, int]:
        """计算球队各位置需求（人数缺口）"""
        result = await self.db.execute(
            select(Player.position, func.count(Player.id))
            .where(and_(Player.team_id == team_id, Player.status == PlayerStatus.ACTIVE))
            .group_by(Player.position)
        )
        counts = {pos.value if hasattr(pos, "value") else str(pos): cnt for pos, cnt in result.all()}
        
        # 目标人数
        targets = {"FW": 3, "MF": 5, "DF": 4, "GK": 2}
        need = {}
        for pos, target in targets.items():
            current = counts.get(pos, 0)
            need[pos] = max(0, target - current)
        
        return need


# =====================================================================
# 独立函数：青训刷新后决策（避免循环导入）
# =====================================================================

async def _ai_academy_decisions_for_team(db: AsyncSession, team: Team, season: Season) -> tuple:
    """单个 AI 球队的青训决策"""
    service = AITeamManagementService(db)
    academy_players = await service._get_team_academy_players(team.id, season.id)
    if not academy_players:
        return 0, 0
    
    roster_count_result = await db.execute(
        select(func.count(Player.id)).where(Player.team_id == team.id)
    )
    roster_count = roster_count_result.scalar() or 0
    
    if roster_count >= 15:
        return 0, 0
    
    scored = []
    for academy_player, player in academy_players:
        score = service._calculate_academy_score(player, academy_player, roster_count)
        scored.append((academy_player, player, score))
    
    scored.sort(key=lambda x: -x[2])
    
    signed = 0
    declined = 0
    max_sign = min(2, 15 - roster_count)
    
    for academy_player, player, score in scored:
        if signed >= max_sign:
            break
        if score >= 35:  # 高潜快成长才签
            try:
                contract_service = ContractService(db)
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
                
                academy_player.status = AcademyPlayerStatus.SIGNED
                academy_player.signed_at_season = season.season_number
                player.team_id = team.id
                player.joined_first_team_season = season.season_number
                signed += 1
            except Exception as e:
                logger.warning(f"AI midseason academy sign failed: {e}")
        else:
            # 低分球员放弃，进入选秀
            academy_player.status = AcademyPlayerStatus.RELEASED_TO_DRAFT
            declined += 1
    
    return signed, declined
