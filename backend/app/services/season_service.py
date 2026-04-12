"""
Season service - 赛季业务逻辑服务
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.season import Season, SeasonStatus, Fixture, FixtureType, FixtureStatus, CupCompetition
from app.models.league import League
from app.models.team import Team
from app.services.scheduler import SeasonScheduler, ScheduleMerger
from app.services.match_simulator import MatchSimulator
from app.services.cup_progression import CupProgressionService


class SeasonService:
    """赛季服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scheduler = SeasonScheduler(db)
        self.simulator = MatchSimulator()
        self.cup_progression = CupProgressionService(db)
    
    async def get_current_season(self) -> Optional[Season]:
        """获取当前进行中的赛季"""
        result = await self.db.execute(
            select(Season)
            .where(Season.status == SeasonStatus.ONGOING)
            .order_by(Season.season_number.desc())
        )
        return result.scalar_one_or_none()
    
    async def get_season_by_number(self, season_number: int) -> Optional[Season]:
        """根据赛季编号获取赛季"""
        result = await self.db.execute(
            select(Season).where(Season.season_number == season_number)
        )
        return result.scalar_one_or_none()
    
    async def create_new_season(self, start_date: Optional[datetime] = None) -> Season:
        """创建新赛季"""
        # 获取上一个赛季编号
        result = await self.db.execute(
            select(Season).order_by(Season.season_number.desc())
        )
        last_season = result.scalar_one_or_none()
        next_season_number = (last_season.season_number + 1) if last_season else 1
        
        # 默认明天开始
        if start_date is None:
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 获取所有联赛
        result = await self.db.execute(select(League))
        leagues = result.scalars().all()
        
        # 获取每个联赛的球队
        teams_by_league: Dict[str, List[Team]] = {}
        for league in leagues:
            result = await self.db.execute(
                select(Team).where(Team.current_league_id == league.id)
            )
            teams = result.scalars().all()
            teams_by_league[league.id] = list(teams)
        
        # 创建赛季和赛程
        season = await self.scheduler.create_season(
            season_number=next_season_number,
            start_date=start_date,
            leagues=list(leagues),
            teams_by_league=teams_by_league
        )
        
        return season
    
    async def start_season(self, season: Season) -> None:
        """启动赛季"""
        if season.status != SeasonStatus.PENDING:
            raise ValueError(f"Cannot start season with status: {season.status}")
        
        await self.scheduler.start_season(season)
    
    async def process_next_day(self, season: Season) -> Dict:
        """处理下一天的比赛"""
        if season.status != SeasonStatus.ONGOING:
            raise ValueError(f"Season is not ongoing: {season.status}")
        
        next_day = season.current_day + 1
        
        # 获取当天比赛
        fixtures = await self.scheduler.process_matchday(season)
        
        # 模拟所有比赛
        results = []
        for fixture in fixtures:
            result = await self.simulator.simulate(fixture)
            await self.simulator.apply_result(fixture, result, self.db)
            results.append({
                "fixture_id": fixture.id,
                "type": fixture.fixture_type.value,
                "home_team": fixture.home_team_id,
                "away_team": fixture.away_team_id,
                "home_score": result.home_score,
                "away_score": result.away_score,
            })
        
        await self.db.commit()
        
        # 处理杯赛晋级
        progression_results = await self._process_cup_progression(season, next_day)
        
        return {
            "season_day": season.current_day,
            "fixtures_processed": len(results),
            "results": results,
            "cup_progression": progression_results
        }
    
    async def _process_cup_progression(self, season: Season, day: int) -> Dict:
        """
        处理杯赛晋级逻辑
        
        杯赛日期: Day 6,9,12,15,18,21,24,27
        - Day 12: 闪电杯小组赛结束，生成32强对阵
        - Day 15: 杰尼杯第1轮结束，生成第2轮（128进64）
        """
        from app.models.season import CupCompetition
        
        cup_days = [6, 8, 10, 12, 14, 15, 21]  # 杯赛晋级处理日（闪电杯+杰尼杯）
        
        if day not in cup_days:
            return {}
        
        results = {}
        
        # 获取所有杯赛
        result = await self.db.execute(
            select(CupCompetition).where(CupCompetition.season_id == season.id)
        )
        competitions = result.scalars().all()
        
        for comp in competitions:
            if comp.code == "LIGHTNING_CUP":
                # 闪电杯晋级处理
                if day == 8:  # 小组赛结束，生成16强（day 10比赛）
                    count = await self.cup_progression.fill_lightning_cup_knockout_fixtures(comp, season)
                    results["lightning_cup"] = f"Generated {count} ROUND_16 fixtures"
                elif day == 10:  # 16强结束，生成8强（day 12比赛）
                    count = await self.cup_progression.fill_next_knockout_round(comp, season, "ROUND_16")
                    results["lightning_cup_quarter"] = f"Generated {count} QUARTER fixtures"
                elif day == 12:  # 8强结束，生成半决赛（day 14比赛）
                    count = await self.cup_progression.fill_next_knockout_round(comp, season, "QUARTER")
                    results["lightning_cup_semi"] = f"Generated {count} SEMI fixtures"
                elif day == 14:  # 半决赛结束，生成决赛（day 21比赛）
                    count = await self.cup_progression.fill_next_knockout_round(comp, season, "SEMI")
                    results["lightning_cup_final"] = f"Generated {count} FINAL fixtures"
                elif day == 21:  # 决赛已结束，设置冠军
                    winner = await self._get_cup_winner(comp)
                    if winner:
                        comp.winner_team_id = winner
                        results["lightning_cup_winner"] = f"Winner set: {winner}"
                    
            elif comp.code.startswith("JENNY_CUP_"):
                # 杰尼杯晋级处理（JENNY_CUP_EAST, JENNY_CUP_NORTH, JENNY_CUP_SOUTH, JENNY_CUP_WEST）
                if day == 6:  # 第1轮（预选赛）结束，生成第2轮（32强）
                    # 获取该体系次级联赛（Level 2）的8支球队作为种子
                    system_code = comp.code.replace('JENNY_CUP_', '')
                    tier2_teams = await self._get_jenny_cup_tier2_teams(system_code)
                    count = await self.cup_progression.fill_jenny_cup_round_2(comp, season, tier2_teams)
                    results[f"jenny_cup_{system_code.lower()}"] = f"Generated {count} ROUND_32 fixtures"
                elif day == 8:  # 32强结束，生成16强（day 10比赛）
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 2)
                    results[f"jenny_cup_{comp.code.replace('JENNY_CUP_', '').lower()}_16"] = f"Generated {count} ROUND_16 fixtures"
                elif day == 10:  # 16强结束，生成8强（day 12比赛）
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 3)
                    results[f"jenny_cup_{comp.code.replace('JENNY_CUP_', '').lower()}_quarter"] = f"Generated {count} QUARTER fixtures"
                elif day == 12:  # 8强结束，生成半决赛（day 14比赛）
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 4)
                    results[f"jenny_cup_{comp.code.replace('JENNY_CUP_', '').lower()}_semi"] = f"Generated {count} SEMI fixtures"
                elif day == 14:  # 半决赛结束，生成决赛（day 15比赛）
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 5)
                    results[f"jenny_cup_{comp.code.replace('JENNY_CUP_', '').lower()}_final"] = f"Generated {count} FINAL fixtures"
                elif day == 15:  # 决赛结束，设置冠军
                    winner = await self._get_cup_winner(comp)
                    if winner:
                        comp.winner_team_id = winner
                        results[f"jenny_cup_{comp.code.replace('JENNY_CUP_', '').lower()}_winner"] = f"Winner set: {winner}"
        
        return results
    
    async def _get_cup_winner(self, competition: CupCompetition) -> Optional[str]:
        """
        获取杯赛冠军（决赛胜者）
        """
        # 获取决赛比赛
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_competition_id == competition.id,
                    Fixture.cup_stage == "FINAL",
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        final = result.scalar_one_or_none()
        
        if not final:
            return None
        
        # 返回胜者
        if final.home_score > final.away_score:
            return final.home_team_id
        elif final.away_score > final.home_score:
            return final.away_team_id
        else:
            # 平局按主队晋级（或可以实现点球规则）
            return final.home_team_id
    
    async def _get_jenny_cup_tier2_teams(self, system_code: str) -> List[str]:
        """
        获取杰尼杯次级联赛种子球队（该体系Level 2联赛的8支球队）
        """
        from app.models.league import LeagueSystem
        
        # 获取该体系的次级联赛（Level 2）
        result = await self.db.execute(
            select(League).join(LeagueSystem).where(
                and_(
                    LeagueSystem.code == system_code,
                    League.level == 2
                )
            )
        )
        tier2_league = result.scalar_one_or_none()
        
        if not tier2_league:
            return []
        
        # 获取该联赛的8支球队
        result = await self.db.execute(
            select(Team).where(Team.current_league_id == tier2_league.id)
        )
        teams = result.scalars().all()
        
        return [t.id for t in teams]
    
    async def get_today_fixtures(self, season: Season) -> List[Fixture]:
        """获取今天（当前天）的所有比赛"""
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.season_day == season.current_day)
        )
        return list(result.scalars().all())
    
    async def get_team_fixtures(
        self,
        season: Season,
        team_id: str,
        fixture_type: Optional[FixtureType] = None
    ) -> List[Fixture]:
        """获取某支球队在赛季中的所有比赛"""
        query = select(Fixture).where(
            and_(
                Fixture.season_id == season.id,
                (Fixture.home_team_id == team_id) | (Fixture.away_team_id == team_id)
            )
        )
        
        if fixture_type:
            query = query.where(Fixture.fixture_type == fixture_type)
        
        query = query.order_by(Fixture.season_day)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_season_calendar(
        self,
        season: Season,
        team_id: Optional[str] = None
    ) -> List[Dict]:
        """获取赛季日历（按天组织的赛程）"""
        # 获取所有相关比赛
        query = select(Fixture).where(Fixture.season_id == season.id)
        
        if team_id:
            query = query.where(
                (Fixture.home_team_id == team_id) | (Fixture.away_team_id == team_id)
            )
        
        query = query.order_by(Fixture.season_day, Fixture.scheduled_at)
        result = await self.db.execute(query)
        fixtures = result.scalars().all()
        
        # 获取所有相关球队信息
        team_ids = set()
        for fixture in fixtures:
            team_ids.add(fixture.home_team_id)
            team_ids.add(fixture.away_team_id)
        
        # 批量获取球队名称
        teams_map = {}
        if team_ids:
            result = await self.db.execute(select(Team).where(Team.id.in_(team_ids)))
            teams = result.scalars().all()
            teams_map = {t.id: t.name for t in teams}
        
        # 按天分组
        calendar = {}
        for fixture in fixtures:
            day = fixture.season_day
            if day not in calendar:
                calendar[day] = {
                    "day": day,
                    "date": fixture.scheduled_at.strftime("%Y-%m-%d"),
                    "fixtures": []
                }
            
            calendar[day]["fixtures"].append({
                "id": fixture.id,
                "type": fixture.fixture_type.value,
                "round": fixture.round_number,
                "home_team_id": fixture.home_team_id,
                "away_team_id": fixture.away_team_id,
                "home_team_name": teams_map.get(fixture.home_team_id, "未知球队"),
                "away_team_name": teams_map.get(fixture.away_team_id, "未知球队"),
                "home_score": fixture.home_score,
                "away_score": fixture.away_score,
                "status": fixture.status.value,
                "cup_stage": fixture.cup_stage,
                "cup_group": fixture.cup_group_name,
            })
        
        return [calendar[day] for day in sorted(calendar.keys())]
