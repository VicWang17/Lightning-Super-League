"""
Season service - 赛季业务逻辑服务
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.season import Season, SeasonStatus, Fixture, FixtureType, FixtureStatus, CupCompetition
from app.models.league import League, LeagueSystem
from app.models.team import Team
from app.services.scheduler import SeasonScheduler, ScheduleMerger
from app.core.formats import get_default_format
from app.core.clock import clock
from app.core.events import EventQueue, GameEvent, EventType, EventStatus
from app.services.match_simulator import MatchSimulator
from app.services.cup_progression import CupProgressionService
from app.services.promotion_service import PromotionService


class SeasonService:
    """赛季服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scheduler = SeasonScheduler(db)
        self.simulator = MatchSimulator()
        self.cup_progression = CupProgressionService(db)
        self.promotion_service = PromotionService(db)
    
    async def get_current_season(self, zone_id: int = 1) -> Optional[Season]:
        """获取当前进行中的赛季"""
        result = await self.db.execute(
            select(Season)
            .where(Season.status == SeasonStatus.ONGOING)
            .where(Season.zone_id == zone_id)
            .order_by(Season.season_number.desc())
        )
        return result.scalar_one_or_none()
    
    async def get_season_by_number(self, season_number: int, zone_id: int = 1) -> Optional[Season]:
        """根据赛季编号获取赛季"""
        result = await self.db.execute(
            select(Season)
            .where(Season.season_number == season_number)
            .where(Season.zone_id == zone_id)
        )
        return result.scalar_one_or_none()
    
    async def create_new_season(self, start_date: Optional[datetime] = None, zone_id: int = 1) -> Season:
        """创建新赛季
        
        Args:
            start_date: 赛季开始日期，默认明天
            zone_id: 所属大区ID，默认1区
        """
        from sqlalchemy.orm import selectinload
        
        # 获取上一个赛季编号
        result = await self.db.execute(
            select(Season).order_by(Season.season_number.desc()).limit(1)
        )
        last_season = result.scalar_one_or_none()
        next_season_number = (last_season.season_number + 1) if last_season else 1
        
        # 默认明天开始
        if start_date is None:
            start_date = clock.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 获取指定大区的联赛
        result = await self.db.execute(
            select(League)
            .join(League.system)
            .where(LeagueSystem.zone_id == zone_id)
            .options(selectinload(League.system))
        )
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
        
        # 生成并写入 EventQueue 事件序列
        await self._seed_season_events(season, start_date)
        
        return season
    
    async def start_season(self, season: Season) -> None:
        """启动赛季"""
        if season.status != SeasonStatus.PENDING:
            raise ValueError(f"Cannot start season with status: {season.status}")
        
        await self.scheduler.start_season(season)
    
    # =================================================================
    # 事件驱动核心（Phase 3）
    # =================================================================
    
    async def _seed_season_events(self, season: Season, start_date: datetime) -> None:
        """为赛季生成完整的 EventQueue 事件序列"""
        fmt = get_default_format()
        template = fmt.season
        
        events = EventQueue.build_season_events(
            season_id=season.id,
            league_days=list(template.league_days),
            cup_days=list(template.lightning_cup_days),
            promotion_day=22,  # 升降级处理日
            total_days=season.total_days,
            start_date=start_date,
        )
        await EventQueue.push_many(self.db, events)
    
    async def process_next_event(self, now: Optional[datetime] = None) -> Optional[Dict]:
        """处理下一个事件（事件驱动核心入口）
        
        1. 从 EventQueue pop 一个 PENDING 事件
        2. 根据 event_type 分发到对应处理器
        3. 处理完成后标记为 COMPLETED（或 FAILED）
        """
        event = await EventQueue.pop(self.db, now=now or clock.now())
        if not event:
            return None
        
        try:
            result = await self._dispatch_event(event)
            await EventQueue.complete(self.db, event.id)
            return result
        except Exception as e:
            from app.core.logging import get_logger
            _logger = get_logger(__name__)
            _logger.error("Event processing failed", event_id=event.id, error=str(e), exc_info=True)
            await EventQueue.fail(self.db, event.id, str(e))
            raise
    
    async def _dispatch_event(self, event: GameEvent) -> Dict:
        """根据事件类型分发处理"""
        if event.event_type == EventType.SEASON_START:
            return await self._handle_season_start(event)
        elif event.event_type == EventType.MATCH_DAY:
            return await self._handle_match_day(event)
        elif event.event_type == EventType.CUP_PROGRESSION:
            return await self._handle_cup_progression(event)
        elif event.event_type == EventType.PROMOTION_RELEGATION:
            return await self._handle_promotion_relegation(event)
        elif event.event_type == EventType.SEASON_END:
            return await self._handle_season_end(event)
        else:
            raise ValueError(f"Unknown event type: {event.event_type}")
    
    async def _handle_season_start(self, event: GameEvent) -> Dict:
        """SEASON_START: 无额外操作（赛季已在 create_new_season 中创建）"""
        return {"event": "season_start", "season_id": event.payload.get("season_id")}
    
    async def _handle_match_day(self, event: GameEvent) -> Dict:
        """MATCH_DAY: 批量并发模拟当天所有比赛"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)
        
        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")
        
        # 获取当天所有 SCHEDULED 比赛
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season_id)
            .where(Fixture.season_day == day)
            .where(Fixture.status == FixtureStatus.SCHEDULED)
        )
        fixtures = list(result.scalars().all())
        
        # Step 1: 并发模拟所有比赛（纯计算，无 DB 写）
        sim_tasks = [self.simulator.simulate(f) for f in fixtures]
        sim_results = await asyncio.gather(*sim_tasks)
        
        # Step 2: 串行 apply_result（避免 standings 共享状态竞争）
        match_results = []
        for fixture, sim_result in zip(fixtures, sim_results):
            await self.simulator.apply_result(fixture, sim_result, self.db)
            match_results.append({
                "fixture_id": fixture.id,
                "type": fixture.fixture_type.value,
                "home_team": fixture.home_team_id,
                "away_team": fixture.away_team_id,
                "home_score": sim_result.home_score,
                "away_score": sim_result.away_score,
            })
        
        # 更新赛季状态（复用 scheduler.process_matchday 的逻辑，但不重复 commit）
        season.current_day = day
        fmt = get_default_format()
        template = fmt.season
        league_days = list(template.league_days)
        if day in league_days:
            season.current_league_round = league_days.index(day) + 1
        cup_days = list(template.lightning_cup_days)
        if day in cup_days:
            season.current_cup_round = cup_days.index(day) + 1
        
        await self.db.commit()
        
        return {
            "event": "match_day",
            "season_id": season_id,
            "season_day": day,
            "fixtures_processed": len(match_results),
            "results": match_results,
        }
    
    async def _handle_cup_progression(self, event: GameEvent) -> Dict:
        """CUP_PROGRESSION: 处理杯赛晋级"""
        season_id = event.payload.get("season_id")
        after_day = event.payload.get("after_day", 0)
        
        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")
        
        progression = await self._process_cup_progression(season, after_day)
        await self.db.commit()
        return {
            "event": "cup_progression",
            "season_id": season_id,
            "after_day": after_day,
            "results": progression,
        }
    
    async def _handle_promotion_relegation(self, event: GameEvent) -> Dict:
        """PROMOTION_RELEGATION: 处理升降级"""
        season_id = event.payload.get("season_id")
        day = event.payload.get("day", 0)
        
        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")
        
        promotion = await self._process_promotion_relegation(season, day)
        await self.db.commit()
        return {
            "event": "promotion_relegation",
            "season_id": season_id,
            "day": day,
            "results": promotion,
        }
    
    async def _handle_season_end(self, event: GameEvent) -> Dict:
        """SEASON_END: 赛季结算"""
        season_id = event.payload.get("season_id")
        
        result = await self.db.execute(
            select(Season).where(Season.id == season_id)
        )
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")
        
        season.status = SeasonStatus.FINISHED
        season.end_date = clock.now()
        await self.db.commit()
        
        return {
            "event": "season_end",
            "season_id": season_id,
            "season_number": season.season_number,
        }
    
    async def process_next_day(self, season: Season) -> Dict:
        """处理下一天的比赛（兼容接口，内部使用事件驱动）
        
        不断处理事件，直到遇到一个 MATCH_DAY 或 SEASON_END 为止。
        如果赛季已结束，自动创建并切换到新赛季。
        """
        if season.status == SeasonStatus.FINISHED:
            print(f"\n  🔄 第{season.season_number}赛季已结束，自动创建新赛季...")
            new_season = await self.create_new_season(zone_id=season.zone_id)
            await self.start_season(new_season)
            print(f"  ✅ 第{new_season.season_number}赛季已启动！\n")
            return await self.process_next_day(new_season)
        
        if season.status != SeasonStatus.ONGOING:
            raise ValueError(f"Season is not ongoing: {season.status}")
        
        # 处理事件直到遇到 MATCH_DAY 或 SEASON_END
        while True:
            result = await self.process_next_event()
            if result is None:
                # 没有更多事件
                return {"season_day": season.current_day, "fixtures_processed": 0, "results": [], "cup_progression": {}}
            
            if result.get("event") in ("match_day", "season_end"):
                return result
    
    async def run_until_next_event(self, season: Season, max_events: int = 100) -> List[Dict]:
        """运行时钟直到下一个需要暂停的事件（用于 step/turbo 模式）
        
        在 step 模式下：处理到下一个 MATCH_DAY 或 SEASON_END 停止
        在 turbo 模式下：连续处理所有到期事件直到队列为空
        """
        results: List[Dict] = []
        for _ in range(max_events):
            result = await self.process_next_event()
            if result is None:
                break
            results.append(result)
            if result.get("event") in ("match_day", "season_end"):
                break
        return results
    
    async def fast_forward(self, target_day: int, season: Season) -> List[Dict]:
        """快进赛季到指定天数（用于测试/调试）
        
        不断处理事件直到 season.current_day >= target_day。
        """
        results: List[Dict] = []
        while season.current_day < target_day and season.status == SeasonStatus.ONGOING:
            batch = await self.run_until_next_event(season, max_events=50)
            if not batch:
                break
            results.extend(batch)
            # refresh season state
            await self.db.refresh(season)
        return results
    
    async def _process_cup_progression(self, season: Season, day: int) -> Dict:
        """
        处理杯赛晋级逻辑
        
        杯赛日期: Day 6,9,12,15,18,21,24,27
        - Day 12: 闪电杯小组赛结束，生成32强对阵
        - Day 15: 杰尼杯第1轮结束，生成第2轮（128进64）
        """
        from app.models.season import CupCompetition
        
        fmt = get_default_format()
        cup_days = list(fmt.season.cup_progression_days)
        
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
                jenny_cup_days = list(fmt.season.jenny_cup_days)
                system_code = comp.code.replace('JENNY_CUP_', '')
                if day == jenny_cup_days[0]:  # 预选赛结束，生成32强
                    tier2_teams = await self._get_jenny_cup_tier2_teams(system_code, season)
                    count = await self.cup_progression.fill_jenny_cup_round_2(comp, season, tier2_teams)
                    results[f"jenny_cup_{system_code.lower()}"] = f"Generated {count} ROUND_32 fixtures"
                elif day == jenny_cup_days[1]:  # 32强结束，生成16强
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 2)
                    results[f"jenny_cup_{system_code.lower()}_16"] = f"Generated {count} ROUND_16 fixtures"
                elif day == jenny_cup_days[2]:  # 16强结束，生成8强
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 3)
                    results[f"jenny_cup_{system_code.lower()}_quarter"] = f"Generated {count} QUARTER fixtures"
                elif day == jenny_cup_days[3]:  # 8强结束，生成半决赛
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 4)
                    results[f"jenny_cup_{system_code.lower()}_semi"] = f"Generated {count} SEMI fixtures"
                elif day == jenny_cup_days[4]:  # 半决赛结束，生成决赛
                    count = await self.cup_progression.fill_jenny_cup_next_round(comp, season, 5)
                    results[f"jenny_cup_{system_code.lower()}_final"] = f"Generated {count} FINAL fixtures"
                elif day == jenny_cup_days[5]:  # 决赛结束，设置冠军
                    winner = await self._get_cup_winner(comp)
                    if winner:
                        comp.winner_team_id = winner
                        results[f"jenny_cup_{system_code.lower()}_winner"] = f"Winner set: {winner}"
        
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
    
    async def _get_jenny_cup_tier2_teams(self, system_code: str, season: Season) -> List[str]:
        """
        获取杰尼杯次级联赛种子球队（该体系Level 2联赛的8支球队）
        从该赛季的联赛赛程中获取，而不是依赖 Team.current_league_id
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
        
        # 从该赛季的联赛赛程中获取球队（而不是依赖 current_league_id）
        # 查询该联赛在本赛季的所有联赛赛程（LEAGUE类型的比赛）
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.LEAGUE,
                    Fixture.league_id == tier2_league.id
                )
            )
        )
        fixtures = result.scalars().all()
        
        # 从赛程中提取所有参与过的球队ID（去重）
        team_ids = set()
        for f in fixtures:
            team_ids.add(f.home_team_id)
            team_ids.add(f.away_team_id)
        
        return list(team_ids)
    
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
    
    async def _process_promotion_relegation(self, season: Season, day: int) -> Dict:
        """
        处理升降级和附加赛
        
        Day 21: 闪电杯决赛结束，处理赛季结束，计算升降级并创建附加赛
        Day 22: 附加赛预选赛 (Day 1)
        Day 23: 附加赛决赛 (Day 2)，应用最终升降级
        Day 24-25: 休赛期
        """
        results = {}
        
        if day == 21:
            # 闪电杯决赛结束，赛季正式结束，计算升降级并创建附加赛
            print(f"\n  📊 闪电杯决赛结束，处理赛季结束，计算升降级...")
            promotion_data = await self.promotion_service.process_season_end(season)
            
            # 创建附加赛赛程
            if promotion_data['playoff_teams']:
                playoff_fixtures = await self.promotion_service.create_playoff_fixtures(
                    season, promotion_data['playoff_teams']
                )
                results['playoff_fixtures_created'] = len(playoff_fixtures)
                print(f"  📝 创建附加赛: {len(playoff_fixtures)} 场")
            
            # 保存升降级数据供后续使用
            season._promotion_data = promotion_data
            
            # 显示直升/直降信息
            auto_up = len(promotion_data['auto_promotions'])
            auto_down = len(promotion_data['auto_relegations'])
            print(f"  ⬆️ 直升: {auto_up} 队")
            print(f"  ⬇️ 直降: {auto_down} 队")
            
        elif day == 22:
            # 附加赛预选赛日，比赛由主循环模拟
            # 预选赛后创建Day 23的决赛对阵
            playoff_fixtures = await self._create_playoff_finals(season)
            if playoff_fixtures:
                results['playoff_finals_created'] = len(playoff_fixtures)
                print(f"  📝 创建附加赛决赛: {len(playoff_fixtures)} 场")
            
        elif day == 24:
            # Day 24 休赛期，统一处理所有升降级
            print(f"\n  📊 处理赛季升降级...")
            
            # 获取之前保存的升降级数据
            promotion_data = getattr(season, '_promotion_data', {
                'auto_promotions': [],
                'auto_relegations': []
            })
            
            # 处理附加赛结果，确定最终升降级名单
            final_results = await self._process_playoff_results(
                season, promotion_data
            )
            
            # 应用球队位置变更
            await self.promotion_service.apply_team_movements(
                final_results['final_promotions'],
                final_results['final_relegations']
            )
            
            results['final_promotions'] = len(final_results['final_promotions'])
            results['final_relegations'] = len(final_results['final_relegations'])
            print(f"  ✅ 升降级完成: {results['final_promotions']} 升级, {results['final_relegations']} 降级")
        
        return results
    
    async def _create_playoff_finals(self, season: Season) -> List[Fixture]:
        """
        根据Day 22预选赛结果创建Day 23决赛
        
        每个体系需要创建：
        1. L1第7 vs L2第2（1场）- 已在playoff_teams中
        2. L2第6 vs L3预赛胜者（1场）  
        3. L3A第6 vs L4A-B预赛胜者（1场）
        4. L3B第6 vs L4C-D预赛胜者（1场）
        共4场/体系 × 4体系 = 16场
        """
        from app.models.league import LeagueSystem, LeagueStanding
        
        fixtures = []
        
        # 获取Day 22的附加赛结果
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.fixture_type == FixtureType.PLAYOFF,
                    Fixture.season_day == 22,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        day22_fixtures = result.scalars().all()
        
        # 建立预选赛胜者映射 {体系名_类型: 胜者ID}
        winners = {}
        for f in day22_fixtures:
            stage = f.cup_stage or ""
            winner_id = f.home_team_id if f.home_score > f.away_score else f.away_team_id
            if f.home_score == f.away_score:
                winner_id = f.home_team_id
            
            # 从 cup_stage 提取体系名（格式: P_L3亚军预赛-东区 或 P_L4A-L4B亚军预赛-东区）
            if "L3亚军预赛-" in stage:
                system = stage.split("-")[-1]  # 取最后一部分（体系名）
                winners[f"{system}_L3"] = winner_id
            elif "L4A-L4B亚军预赛-" in stage:
                system = stage.split("-")[-1]
                winners[f"{system}_L4AB"] = winner_id
            elif "L4C-L4D亚军预赛-" in stage:
                system = stage.split("-")[-1]
                winners[f"{system}_L4CD"] = winner_id
        
        # Day 23 决赛时间
        day23_date = season.start_date + timedelta(days=22)
        day23_kickoff = day23_date.replace(hour=20, minute=0, second=0)
        
        # 获取升降级数据（包含L1-L2决赛对阵）
        promotion_data = getattr(season, '_promotion_data', {})
        playoff_teams = promotion_data.get('playoff_teams', {})
        
        # 1. 创建L1-L2决赛（4场）
        for match_name, (home_id, away_id) in playoff_teams.items():
            if "-L3" not in match_name and "-L4" not in match_name and "亚军预赛" not in match_name:
                if home_id and away_id:  # 确保不是占位符
                    short_name = match_name.replace("联赛", "").replace("附加赛", "")
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=23,
                        scheduled_at=day23_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_{short_name[:15]}",
                        home_team_id=home_id,
                        away_team_id=away_id,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)
        
        # 2. 查询所有体系，创建L2-L3和L3-L4决赛
        systems_result = await self.db.execute(select(LeagueSystem))
        systems = systems_result.scalars().all()
        
        for system in systems:
            # 获取该体系的所有联赛
            leagues_result = await self.db.execute(
                select(League).where(League.system_id == system.id)
            )
            leagues = leagues_result.scalars().all()
            
            l1 = next((l for l in leagues if l.level == 1), None)
            l2 = next((l for l in leagues if l.level == 2), None)
            l3_leagues = [l for l in leagues if l.level == 3]
            l4_leagues = [l for l in leagues if l.level == 4]
            
            if not l1 or not l2 or len(l3_leagues) < 2 or len(l4_leagues) < 4:
                continue
            
            l3a, l3b = sorted(l3_leagues, key=lambda x: x.name)[:2]
            l4a, l4b, l4c, l4d = sorted(l4_leagues, key=lambda x: x.name)[:4]
            
            # 获取积分榜
            l2_standings = await self._get_league_standings(l2.id, season.id)
            l3a_standings = await self._get_league_standings(l3a.id, season.id)
            l3b_standings = await self._get_league_standings(l3b.id, season.id)
            
            sys_name = system.name  # 使用中文名（东区、西区等）
            
            # 创建L2-L3决赛：L2倒数第(relegation_spots+1)名 vs L3预赛胜者
            l2_playoff_idx = -(l2.relegation_spots + 1) if l2.relegation_spots > 0 else None
            l3_key = f"{sys_name}_L3"
            l3_winner = winners.get(l3_key)
            if l2_playoff_idx is not None and len(l2_standings) >= abs(l2_playoff_idx) and l3_winner:
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=23,
                        scheduled_at=day23_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_L2L3_{system.code[:8]}",
                        home_team_id=l2_standings[l2_playoff_idx].team_id,
                        away_team_id=l3_winner,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)
            
            # 创建L3-L4决赛1：L3A倒数第(relegation_spots+1)名 vs L4A-B预赛胜者
            l3a_playoff_idx = -(l3a.relegation_spots + 1) if l3a.relegation_spots > 0 else None
            l4ab_key = f"{sys_name}_L4AB"
            l4ab_winner = winners.get(l4ab_key)
            if l3a_playoff_idx is not None and len(l3a_standings) >= abs(l3a_playoff_idx) and l4ab_winner:
                if l4ab_winner:
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=23,
                        scheduled_at=day23_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_L3AL4_{system.code[:8]}",
                        home_team_id=l3a_standings[l3a_playoff_idx].team_id,
                        away_team_id=l4ab_winner,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)
            
            # 创建L3-L4决赛2：L3B倒数第(relegation_spots+1)名 vs L4C-D预赛胜者
            l3b_playoff_idx = -(l3b.relegation_spots + 1) if l3b.relegation_spots > 0 else None
            l4cd_key = f"{sys_name}_L4CD"
            l4cd_winner = winners.get(l4cd_key)
            if l3b_playoff_idx is not None and len(l3b_standings) >= abs(l3b_playoff_idx) and l4cd_winner:
                if l4cd_winner:
                    fixture = Fixture(
                        season_id=season.id,
                        fixture_type=FixtureType.PLAYOFF,
                        season_day=23,
                        scheduled_at=day23_kickoff,
                        round_number=2,
                        league_id=None,
                        cup_competition_id=None,
                        cup_group_name=None,
                        cup_stage=f"F_L3BL4_{system.code[:8]}",
                        home_team_id=l3b_standings[l3b_playoff_idx].team_id,
                        away_team_id=l4cd_winner,
                        status=FixtureStatus.SCHEDULED
                    )
                    self.db.add(fixture)
                    fixtures.append(fixture)
        
        await self.db.commit()
        return fixtures
    
    async def _get_league_standings(self, league_id: str, season_id: str):
        """获取联赛积分榜"""
        from app.models.league import LeagueStanding
        result = await self.db.execute(
            select(LeagueStanding).where(
                and_(
                    LeagueStanding.league_id == league_id,
                    LeagueStanding.season_id == season_id
                )
            ).order_by(LeagueStanding.position)
        )
        return list(result.scalars().all())
    
    async def _process_playoff_results(
        self,
        season: Season,
        promotion_data: Dict
    ) -> Dict[str, List]:
        """
        处理附加赛结果，确定最终升降级名单
        
        附加赛规则：
        - L1-L2: L1第7 vs L2第2，胜者升级/保级，败者降级/留级
        - L2-L3: L2第6 vs L3预赛胜者，胜者升级/保级，败者降级/留级  
        - L3-L4: L3第6 vs L4预赛胜者，胜者升级/保级，败者降级/留级
        """
        auto_promotions = list(promotion_data.get('auto_promotions', []))
        auto_relegations = list(promotion_data.get('auto_relegations', []))
        
        #  playoff_promotions 和 playoff_relegations 用于存储附加赛产生的升降级
        playoff_promotions = []
        playoff_relegations = []
        
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
        
        # 获取所有联赛信息
        from sqlalchemy.orm import selectinload
        result = await self.db.execute(
            select(League).options(selectinload(League.system))
        )
        leagues = {l.id: l for l in result.scalars().all()}
        
        # 获取所有球队信息
        result = await self.db.execute(select(Team))
        teams = {t.id: t for t in result.scalars().all()}
        
        # 建立联赛层级映射 {league_id: level}
        league_levels = {l.id: l.level for l in leagues.values()}
        
        for fixture in day23_fixtures:
            # 确定胜者
            if fixture.home_score > fixture.away_score:
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            elif fixture.away_score > fixture.home_score:
                winner_id = fixture.away_team_id
                loser_id = fixture.home_team_id
            else:
                # 平局按主队获胜
                winner_id = fixture.home_team_id
                loser_id = fixture.away_team_id
            
            winner_team = teams.get(winner_id)
            loser_team = teams.get(loser_id)
            
            if not winner_team or not loser_team:
                continue
            
            # 根据球队当前所在联赛层级确定升降级
            winner_level = league_levels.get(winner_team.current_league_id, 0)
            loser_level = league_levels.get(loser_team.current_league_id, 0)
            
            stage = fixture.cup_stage or ""
            
            # L1-L2附加赛: L1第7(主队, level=1) vs L2第2(客队, level=2)
            # L2第2胜则升级, L1第7败则降级
            if "L1-L2" in stage or "超级-甲级" in stage or "超级联赛-甲级联赛" in stage:
                # L2球队(低级别)获胜 -> 升级
                if winner_level > loser_level:  # winner是L2球队
                    # 找到L1联赛(需要知道是哪个L1)
                    l1_league = next((l for l in leagues.values() if l.level == 1 and loser_team.current_league_id == l.id), None)
                    l2_league = next((l for l in leagues.values() if l.level == 2 and winner_team.current_league_id == l.id), None)
                    if l1_league and l2_league:
                        playoff_promotions.append((winner_id, l2_league.id, l1_league.id))
                        playoff_relegations.append((loser_id, l1_league.id, l2_league.id))
                else:  # L1球队获胜，保级成功，不需要额外处理
                    pass
            
            # L2-L3附加赛: L2第6(主队, level=2) vs L3预赛胜者(客队, level=3)
            # L3球队获胜 -> 升级, L2第6败则降级
            elif "L2L3" in stage:
                if winner_level > loser_level:  # winner是L3球队
                    l2_league = next((l for l in leagues.values() if l.level == 2 and loser_team.current_league_id == l.id), None)
                    l3_league = next((l for l in leagues.values() if l.level == 3 and winner_team.current_league_id == l.id), None)
                    if l2_league and l3_league:
                        playoff_promotions.append((winner_id, l3_league.id, l2_league.id))
                        playoff_relegations.append((loser_id, l2_league.id, l3_league.id))
            
            # L3-L4附加赛: L3第6(主队, level=3) vs L4预赛胜者(客队, level=4)
            # L4球队获胜 -> 升级, L3第6败则降级
            elif "L3AL4" in stage or "L3BL4" in stage:
                if winner_level > loser_level:  # winner是L4球队
                    l3_league = next((l for l in leagues.values() if l.level == 3 and loser_team.current_league_id == l.id), None)
                    l4_league = next((l for l in leagues.values() if l.level == 4 and winner_team.current_league_id == l.id), None)
                    if l3_league and l4_league:
                        playoff_promotions.append((winner_id, l4_league.id, l3_league.id))
                        playoff_relegations.append((loser_id, l3_league.id, l4_league.id))
        
        # 合并所有升降级
        final_promotions = auto_promotions + playoff_promotions
        final_relegations = auto_relegations + playoff_relegations
        
        return {
            'final_promotions': final_promotions,
            'final_relegations': final_relegations,
            'playoff_promotions': playoff_promotions,
            'playoff_relegations': playoff_relegations
        }
