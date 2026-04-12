"""
升降级服务 - 处理赛季结束后的升降级和附加赛
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
        name: str,  # 对阵名称，如 "L1-L2附加赛"
        day: int,   # 比赛日（23或24）
        home_team_source: str,  # 主队来源描述
        away_team_source: str,  # 客队来源描述
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
        
        流程:
        1. 计算最终积分榜
        2. 确定直升/直降球队
        3. 确定需要附加赛的球队
        4. 创建附加赛赛程
        
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
            
            # L1-L2: L1第8名直降，L2冠军直升，L1第7名 vs L2第2名附加赛
            await self._process_l1_l2_promotion(
                system_leagues, season.id, result
            )
            
            # L2-L3: L2第7-8名直降，L3各联赛冠军直升，
            # L2第7名 vs (L3A亚军 vs L3B亚军胜者) 附加赛
            await self._process_l2_l3_promotion(
                system_leagues, season.id, result
            )
            
            # L3-L4: L3各联赛第7-8名直降，L4各联赛冠军直升，
            # L3A第7名 vs (L4A亚军 vs L4B亚军胜者) 附加赛
            # L3B第7名 vs (L4C亚军 vs L4D亚军胜者) 附加赛
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
        """处理L1-L2升降级"""
        l1 = next((l for l in system_leagues if l.level == 1), None)
        l2 = next((l for l in system_leagues if l.level == 2), None)
        
        if not l1 or not l2:
            return
        
        l1_standings = await self._get_league_standings(l1.id, season_id)
        l2_standings = await self._get_league_standings(l2.id, season_id)
        
        if len(l1_standings) < 8 or len(l2_standings) < 8:
            return
        
        # L2冠军直升
        result['auto_promotions'].append(
            (l2_standings[0].team_id, l2.id, l1.id)
        )
        
        # L1第8名直降
        result['auto_relegations'].append(
            (l1_standings[7].team_id, l1.id, l2.id)
        )
        
        # 附加赛: L1第7名 vs L2第2名
        result['playoff_teams'][f"{l1.name}-{l2.name}附加赛"] = (
            l1_standings[6].team_id,  # L1第7名
            l2_standings[1].team_id   # L2第2名
        )
    
    async def _process_l2_l3_promotion(
        self,
        system_leagues: List[League],
        season_id: str,
        result: Dict
    ):
        """处理L2-L3升降级"""
        l2 = next((l for l in system_leagues if l.level == 2), None)
        l3_leagues = [l for l in system_leagues if l.level == 3]
        
        if not l2 or len(l3_leagues) < 2:
            return
        
        l2_standings = await self._get_league_standings(l2.id, season_id)
        l3a_standings = await self._get_league_standings(l3_leagues[0].id, season_id)
        l3b_standings = await self._get_league_standings(l3_leagues[1].id, season_id)
        
        if len(l2_standings) < 8:
            return
        
        # L3各联赛冠军直升
        if len(l3a_standings) >= 1:
            result['auto_promotions'].append(
                (l3a_standings[0].team_id, l3_leagues[0].id, l2.id)
            )
        if len(l3b_standings) >= 1:
            result['auto_promotions'].append(
                (l3b_standings[0].team_id, l3_leagues[1].id, l2.id)
            )
        
        # L2最后2名直降（第7、8名）
        result['auto_relegations'].append(
            (l2_standings[6].team_id, l2.id, l3_leagues[0].id)  # 第7名降入L3A
        )
        result['auto_relegations'].append(
            (l2_standings[7].team_id, l2.id, l3_leagues[1].id)  # 第8名降入L3B
        )
        
        # Day 22: L3A亚军 vs L3B亚军（胜者进入Day 23 vs L2第6名）
        if len(l3a_standings) >= 2 and len(l3b_standings) >= 2:
            result['playoff_teams'][f"L3亚军预赛-{l3_leagues[0].system.name}"] = (
                l3a_standings[1].team_id,  # L3A亚军
                l3b_standings[1].team_id   # L3B亚军
            )
            # Day 23决赛对阵在Day 22结束后创建
    
    async def _process_l3_l4_promotion(
        self,
        system_leagues: List[League],
        season_id: str,
        result: Dict
    ):
        """处理L3-L4升降级"""
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
        
        # L4各联赛冠军直升到对应L3
        if len(l4a_standings) >= 1:
            result['auto_promotions'].append((l4a_standings[0].team_id, l4a.id, l3a.id))
        if len(l4b_standings) >= 1:
            result['auto_promotions'].append((l4b_standings[0].team_id, l4b.id, l3a.id))
        if len(l4c_standings) >= 1:
            result['auto_promotions'].append((l4c_standings[0].team_id, l4c.id, l3b.id))
        if len(l4d_standings) >= 1:
            result['auto_promotions'].append((l4d_standings[0].team_id, l4d.id, l3b.id))
        
        # L3各联赛最后2名直降（第7、8名）
        if len(l3a_standings) >= 8:
            result['auto_relegations'].append((l3a_standings[6].team_id, l3a.id, l4a.id))  # L3A第7名→L4A
            result['auto_relegations'].append((l3a_standings[7].team_id, l3a.id, l4b.id))  # L3A第8名→L4B
        if len(l3b_standings) >= 8:
            result['auto_relegations'].append((l3b_standings[6].team_id, l3b.id, l4c.id))  # L3B第7名→L4C
            result['auto_relegations'].append((l3b_standings[7].team_id, l3b.id, l4d.id))  # L3B第8名→L4D
        
        # Day 22: L4A亚军 vs L4B亚军（胜者进入Day 23 vs L3A第6名）
        system_name = l3a.system.name if l3a.system else ""
        if len(l4a_standings) >= 2 and len(l4b_standings) >= 2:
            result['playoff_teams'][f"L4A-L4B亚军预赛-{system_name}"] = (
                l4a_standings[1].team_id,
                l4b_standings[1].team_id
            )
            # 决赛占位符：L3A第6名 vs L4A-B预赛胜者
            if len(l3a_standings) >= 6:
                result['playoff_teams'][f"{l3a.name}-L4-{system_name}"] = (
                    l3a_standings[5].team_id,  # L3A第6名
                    None  # 待Day 22结束后确定
                )
        
        # Day 22: L4C亚军 vs L4D亚军（胜者进入Day 23 vs L3B第6名）
        if len(l4c_standings) >= 2 and len(l4d_standings) >= 2:
            result['playoff_teams'][f"L4C-L4D亚军预赛-{system_name}"] = (
                l4c_standings[1].team_id,
                l4d_standings[1].team_id
            )
            # 决赛占位符：L3B第6名 vs L4C-D预赛胜者
            if len(l3b_standings) >= 6:
                result['playoff_teams'][f"{l3b.name}-L4-{system_name}"] = (
                    l3b_standings[5].team_id,  # L3B第6名
                    None  # 待Day 22结束后确定
                )
    
    async def create_playoff_fixtures(
        self,
        season: Season,
        playoff_teams: Dict[str, Tuple[str, str]]
    ) -> List[Fixture]:
        """
        创建附加赛赛程
        
        Day 22: 预选赛（L3A亚军vsL3B亚军，L4A亚军vsL4B亚军，L4C亚军vsL4D亚军）
        Day 23: 决赛（L1第7 vs L2第2，L2第7 vs L3预赛胜者，L3A第7 vs L4A-B胜者，L3B第7 vs L4C-D胜者）
        """
        fixtures = []
        
        # Day 22 - 预选赛
        day22_date = season.start_date + timedelta(days=21)  # Day 22
        day22_kickoff = day22_date.replace(hour=20, minute=0, second=0)
        
        # Day 23 - 决赛
        day23_date = season.start_date + timedelta(days=22)  # Day 23
        day23_kickoff = day23_date.replace(hour=20, minute=0, second=0)
        
        # 只创建Day 22的预赛，Day 23的决赛由 _create_playoff_finals 统一创建
        for match_name, (home_id, away_id) in playoff_teams.items():
            # 只创建预赛（有实际对阵的）
            if "亚军预赛" in match_name or "L3亚军" in match_name:
                if home_id and away_id:  # 确保不是占位符
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
                        cup_stage=f"P_{short_name[:17]}",  # P_ = Preliminary
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
        
        # 获取Day 23的附加赛结果（用于确定Day 24的胜者对手）
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
            # 确定胜者
            if fixture.home_score > fixture.away_score:
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            elif fixture.away_score > fixture.home_score:
                winner_id = fixture.away_team_id
                loser_id = fixture.home_team_id
            else:
                # 平局按主队获胜（或可以实现加时/点球）
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            
            # 解析对阵信息确定升降级
            stage = fixture.cup_stage or ""
            
            if "L1-L2" in stage or "超级-甲级" in stage:
                # L1第7 vs L2第2: L1第7胜则保级，L2第2胜则升级
                # 这里需要知道谁是主队（L1第7）谁是客队（L2第2）
                # 实际上应该根据比赛前确定的球队ID来判断
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
        显示完整的联赛名称
        """
        # 获取所有联赛信息用于显示名称
        result = await self.db.execute(select(League))
        leagues = {l.id: l for l in result.scalars().all()}
        
        # 按联赛分组显示升级球队
        promotions_by_to_league: Dict[str, List] = {}
        for team_id, from_league_id, to_league_id in promotions:
            if to_league_id not in promotions_by_to_league:
                promotions_by_to_league[to_league_id] = []
            promotions_by_to_league[to_league_id].append((team_id, from_league_id, to_league_id))
        
        # 按联赛分组显示降级球队
        relegations_by_to_league: Dict[str, List] = {}
        for team_id, from_league_id, to_league_id in relegations:
            if to_league_id not in relegations_by_to_league:
                relegations_by_to_league[to_league_id] = []
            relegations_by_to_league[to_league_id].append((team_id, from_league_id, to_league_id))
        
        # 处理升级
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
        
        # 处理降级
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
