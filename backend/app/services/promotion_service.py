"""
升降级服务 - 处理赛季结束后的升降级和附加赛（配置驱动版）

核心解耦：
- 升降级名额不再硬编码为第7/8名，而是从 League.promotion_spots / relegation_spots 读取
- 附加赛对阵位置由 has_promotion_playoff / has_relegation_playoff 推导
- 保留 L1-L2 / L2-L3 / L3-L4 的三级处理结构，因为跨联赛映射关系较复杂
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.season import Season, Fixture, FixtureType, FixtureStatus
from app.models.league import League, LeagueStanding, LeagueSystem
from app.models.team import Team


class PromotionPlayoffMatch:
    """附加赛对阵定义"""
    def __init__(
        self,
        name: str,
        day: int,
        home_team_source: str,
        away_team_source: str,
        home_team_id: Optional[str] = None,
        away_team_id: Optional[str] = None
    ):
        self.name = name
        self.day = day
        self.home_team_source = home_team_source
        self.away_team_source = away_team_source
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id


class PromotionService:
    """
    升降级服务
    
    处理:
    1. 自动升降级（直升/直降）
    2. 升降级附加赛创建和模拟
    3. 最终球队位置调整
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def process_season_end(self, season: Season) -> Dict:
        """
        处理赛季结束后的升降级
        
        返回: {
            'auto_promotions': [(team_id, from_league, to_league)],
            'auto_relegations': [(team_id, from_league, to_league)],
            'playoff_teams': {'match_name': (home_team_id, away_team_id)}
        }
        """
        result = {
            'auto_promotions': [],
            'auto_relegations': [],
            'playoff_teams': {}
        }
        
        # 获取所有联赛
        leagues_result = await self.db.execute(
            select(League).order_by(League.level)
        )
        leagues = leagues_result.scalars().all()
        
        # 按级别分组
        leagues_by_level: Dict[int, List[League]] = {1: [], 2: [], 3: [], 4: []}
        for league in leagues:
            leagues_by_level[league.level].append(league)
        
        # 处理每个体系的升降级
        for system in await self._get_all_systems():
            system_leagues = [l for l in leagues if l.system_id == system.id]
            
            await self._process_l1_l2_promotion(
                system_leagues, season.id, result
            )
            await self._process_l2_l3_promotion(
                system_leagues, season.id, result
            )
            await self._process_l3_l4_promotion(
                system_leagues, season.id, result
            )
        
        return result
    
    async def _get_all_systems(self) -> List[LeagueSystem]:
        """获取所有联赛体系"""
        result = await self.db.execute(select(LeagueSystem))
        return result.scalars().all()
    
    async def _get_league_standings(
        self, league_id: str, season_id: str
    ) -> List[LeagueStanding]:
        """获取联赛最终排名"""
        result = await self.db.execute(
            select(LeagueStanding).where(
                and_(
                    LeagueStanding.league_id == league_id,
                    LeagueStanding.season_id == season_id
                )
            ).order_by(LeagueStanding.position)
        )
        return list(result.scalars().all())
    
    async def _process_l1_l2_promotion(
        self,
        system_leagues: List[League],
        season_id: str,
        result: Dict
    ):
        """处理L1-L2升降级（配置驱动）"""
        l1 = next((l for l in system_leagues if l.level == 1), None)
        l2 = next((l for l in system_leagues if l.level == 2), None)
        
        if not l1 or not l2:
            return
        
        l1_standings = await self._get_league_standings(l1.id, season_id)
        l2_standings = await self._get_league_standings(l2.id, season_id)
        
        if len(l1_standings) < l1.max_teams or len(l2_standings) < l2.max_teams:
            return
        
        # L2 直升（前 promotion_spots 名）
        for i in range(l2.promotion_spots):
            if i < len(l2_standings):
                result['auto_promotions'].append(
                    (l2_standings[i].team_id, l2.id, l1.id)
                )
        
        # L1 直降（后 relegation_spots 名）
        for i in range(1, l1.relegation_spots + 1):
            if i <= len(l1_standings):
                result['auto_relegations'].append(
                    (l1_standings[-i].team_id, l1.id, l2.id)
                )
        
        # 附加赛: L1倒数第(relegation_spots+1)名 vs L2第(promotion_spots+1)名
        if l1.has_relegation_playoff and l2.has_promotion_playoff:
            upper_idx = -(l1.relegation_spots + 1)
            lower_idx = l2.promotion_spots
            if abs(upper_idx) <= len(l1_standings) and lower_idx < len(l2_standings):
                result['playoff_teams'][f"{l1.name}-{l2.name}附加赛"] = (
                    l1_standings[upper_idx].team_id,
                    l2_standings[lower_idx].team_id
                )
    
    async def _process_l2_l3_promotion(
        self,
        system_leagues: List[League],
        season_id: str,
        result: Dict
    ):
        """处理L2-L3升降级（配置驱动）"""
        l2 = next((l for l in system_leagues if l.level == 2), None)
        l3_leagues = [l for l in system_leagues if l.level == 3]
        
        if not l2 or len(l3_leagues) < 2:
            return
        
        l2_standings = await self._get_league_standings(l2.id, season_id)
        l3a_standings = await self._get_league_standings(l3_leagues[0].id, season_id)
        l3b_standings = await self._get_league_standings(l3_leagues[1].id, season_id)
        
        if len(l2_standings) < l2.max_teams:
            return
        
        # L3各联赛冠军直升
        for l3 in l3_leagues:
            l3_standings = await self._get_league_standings(l3.id, season_id)
            for i in range(l3.promotion_spots):
                if i < len(l3_standings):
                    result['auto_promotions'].append(
                        (l3_standings[i].team_id, l3.id, l2.id)
                    )
        
        # L2 直降（后 relegation_spots 名，按联赛数量循环分配）
        relegate_teams = l2_standings[-l2.relegation_spots:] if l2.relegation_spots > 0 else []
        for idx, team in enumerate(relegate_teams):
            target_l3 = l3_leagues[idx % len(l3_leagues)]
            result['auto_relegations'].append(
                (team.team_id, l2.id, target_l3.id)
            )
        
        # Day 22: L3A亚军 vs L3B亚军（胜者进入Day 23 vs L2倒数第(relegation_spots+1)名）
        l3a_runner_idx = l3_leagues[0].promotion_spots
        l3b_runner_idx = l3_leagues[1].promotion_spots
        if (len(l3a_standings) > l3a_runner_idx and len(l3b_standings) > l3b_runner_idx):
            result['playoff_teams'][f"L3亚军预赛-{l3_leagues[0].system.name}"] = (
                l3a_standings[l3a_runner_idx].team_id,
                l3b_standings[l3b_runner_idx].team_id
            )
    
    async def _process_l3_l4_promotion(
        self,
        system_leagues: List[League],
        season_id: str,
        result: Dict
    ):
        """处理L3-L4升降级（配置驱动）"""
        l3_leagues = sorted([l for l in system_leagues if l.level == 3], key=lambda x: x.name)
        l4_leagues = sorted([l for l in system_leagues if l.level == 4], key=lambda x: x.name)
        
        if len(l3_leagues) < 2 or len(l4_leagues) < 4:
            return
        
        l3a, l3b = l3_leagues[0], l3_leagues[1]
        l4a, l4b, l4c, l4d = l4_leagues[0], l4_leagues[1], l4_leagues[2], l4_leagues[3]
        
        l3a_standings = await self._get_league_standings(l3a.id, season_id)
        l3b_standings = await self._get_league_standings(l3b.id, season_id)
        l4a_standings = await self._get_league_standings(l4a.id, season_id)
        l4b_standings = await self._get_league_standings(l4b.id, season_id)
        l4c_standings = await self._get_league_standings(l4c.id, season_id)
        l4d_standings = await self._get_league_standings(l4d.id, season_id)
        
        # L4各联赛冠军直升到对应L3（前一半L4升L3A，后一半升L3B）
        half = len(l4_leagues) // 2
        for idx, l4 in enumerate(l4_leagues):
            l4_standings = await self._get_league_standings(l4.id, season_id)
            target_l3 = l3_leagues[0] if idx < half else l3_leagues[1]
            for i in range(l4.promotion_spots):
                if i < len(l4_standings):
                    result['auto_promotions'].append((l4_standings[i].team_id, l4.id, target_l3.id))
        
        # L3各联赛直降（后 relegation_spots 名，分配到对应L4）
        for l3_idx, l3 in enumerate(l3_leagues):
            l3_standings = await self._get_league_standings(l3.id, season_id)
            relegate_teams = l3_standings[-l3.relegation_spots:] if l3.relegation_spots > 0 else []
            for r_idx, team in enumerate(relegate_teams):
                # L3A -> L4A, L4B; L3B -> L4C, L4D
                target_l4_idx = l3_idx * half + (r_idx % half)
                if target_l4_idx < len(l4_leagues):
                    result['auto_relegations'].append((team.team_id, l3.id, l4_leagues[target_l4_idx].id))
        
        # Day 22: L4A亚军 vs L4B亚军 / L4C亚军 vs L4D亚军
        system_name = l3a.system.name if l3a.system else ""
        runner_idx = l4a.promotion_spots  # 亚军 = promotion_spots 索引（冠军之后）
        
        if (len(l4a_standings) > runner_idx and len(l4b_standings) > runner_idx):
            result['playoff_teams'][f"L4A-L4B亚军预赛-{system_name}"] = (
                l4a_standings[runner_idx].team_id,
                l4b_standings[runner_idx].team_id
            )
            # 决赛占位符：L3A倒数第(relegation_spots+1)名 vs L4A-B预赛胜者
            l3a_playoff_idx = -(l3a.relegation_spots + 1)
            if len(l3a_standings) >= abs(l3a_playoff_idx):
                result['playoff_teams'][f"{l3a.name}-L4-{system_name}"] = (
                    l3a_standings[l3a_playoff_idx].team_id,
                    None
                )
        
        if (len(l4c_standings) > runner_idx and len(l4d_standings) > runner_idx):
            result['playoff_teams'][f"L4C-L4D亚军预赛-{system_name}"] = (
                l4c_standings[runner_idx].team_id,
                l4d_standings[runner_idx].team_id
            )
            l3b_playoff_idx = -(l3b.relegation_spots + 1)
            if len(l3b_standings) >= abs(l3b_playoff_idx):
                result['playoff_teams'][f"{l3b.name}-L4-{system_name}"] = (
                    l3b_standings[l3b_playoff_idx].team_id,
                    None
                )
    
    async def create_playoff_fixtures(
        self,
        season: Season,
        playoff_teams: Dict[str, Tuple[str, str]]
    ) -> List[Fixture]:
        """
        创建附加赛赛程
        
        Day 22: 预选赛（L3A亚军vsL3B亚军，L4A亚军vsL4B亚军，L4C亚军vsL4D亚军）
        Day 23: 决赛（L1第7 vs L2第2，L2第6 vs L3预赛胜者，L3A第7 vs L4A-B胜者，L3B第7 vs L4C-D胜者）
        """
        fixtures = []
        
        # Day 22 - 预选赛
        day22_date = season.start_date + timedelta(days=21)  # Day 22
        day22_kickoff = day22_date.replace(hour=20, minute=0, second=0)
        
        for match_name, (home_id, away_id) in playoff_teams.items():
            if "亚军预赛" in match_name or "L3亚军" in match_name:
                if home_id and away_id:
                    short_name = match_name.replace("联赛", "").replace("附加赛", "")
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=22,
                        scheduled_at=day22_kickoff,
                        round_number=1,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"P_{short_name[:17]}",
                        home_team_id=home_id,
                        away_team_id=away_id,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)
        
        await self.db.commit()
        return fixtures
    
    async def process_playoff_results(
        self,
        season: Season,
        auto_promotions: List[Tuple[str, str, str]],
        auto_relegations: List[Tuple[str, str, str]]
    ) -> Dict[str, List[Tuple[str, str, str]]]:
        """
        处理附加赛结果，确定最终升降级名单
        
        返回: {
            'final_promotions': [(team_id, from_league, to_league)],
            'final_relegations': [(team_id, from_league, to_league)]
        }
        """
        final_promotions = list(auto_promotions)
        final_relegations = list(auto_relegations)
        
        # 获取Day 24的附加赛结果
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.PLAYOFF,
                    Fixture.season_day == 24,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        day24_fixtures = result.scalars().all()
        
        # 获取Day 23的附加赛结果
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.PLAYOFF,
                    Fixture.season_day == 23,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        day23_fixtures = result.scalars().all()
        
        # 根据比赛结果确定升降级
        for fixture in day24_fixtures:
            if fixture.home_score > fixture.away_score:
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            elif fixture.away_score > fixture.home_score:
                winner_id = fixture.away_team_id
                loser_id = fixture.home_team_id
            else:
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            
            stage = fixture.cup_stage or ""
            
            if "L1-L2" in stage or "超级-甲级" in stage:
                pass
        
        return {
            'final_promotions': final_promotions,
            'final_relegations': final_relegations
        }
    
    async def apply_team_movements(
        self,
        promotions: List[Tuple[str, str, str]],
        relegations: List[Tuple[str, str, str]]
    ):
        """
        应用球队位置变更
        
        更新 Team.current_league_id
        """
        result = await self.db.execute(select(League))
        leagues = {l.id: l for l in result.scalars().all()}
        
        promotions_by_to_league: Dict[str, List] = {}
        for team_id, from_league_id, to_league_id in promotions:
            if to_league_id not in promotions_by_to_league:
                promotions_by_to_league[to_league_id] = []
            promotions_by_to_league[to_league_id].append((team_id, from_league_id, to_league_id))
        
        relegations_by_to_league: Dict[str, List] = {}
        for team_id, from_league_id, to_league_id in relegations:
            if to_league_id not in relegations_by_to_league:
                relegations_by_to_league[to_league_id] = []
            relegations_by_to_league[to_league_id].append((team_id, from_league_id, to_league_id))
        
        for to_league_id, promo_list in sorted(promotions_by_to_league.items()):
            to_league = leagues.get(to_league_id)
            to_league_name = to_league.name if to_league else to_league_id[:8]
            print(f"\n  📈 升入 [{to_league_name}]:")
            for team_id, from_league_id, _ in promo_list:
                team = await self.db.get(Team, team_id)
                from_league = leagues.get(from_league_id)
                from_league_name = from_league.name if from_league else from_league_id[:8]
                if team:
                    team.current_league_id = to_league_id
                    print(f"     ⬆️ {team.name:12s} ({from_league_name} → {to_league_name})")
        
        for to_league_id, relegate_list in sorted(relegations_by_to_league.items()):
            to_league = leagues.get(to_league_id)
            to_league_name = to_league.name if to_league else to_league_id[:8]
            print(f"\n  📉 降入 [{to_league_name}]:")
            for team_id, from_league_id, _ in relegate_list:
                team = await self.db.get(Team, team_id)
                from_league = leagues.get(from_league_id)
                from_league_name = from_league.name if from_league else from_league_id[:8]
                if team:
                    team.current_league_id = to_league_id
                    print(f"     ⬇️ {team.name:12s} ({from_league_name} → {to_league_name})")
        
        await self.db.commit()
