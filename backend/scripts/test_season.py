#!/usr/bin/env python3
"""
赛季测试脚本 - 完整赛季模拟测试

用法:
    cd backend && python -m scripts.test_season

功能:
    1. 创建/使用现有赛季
    2. 完整模拟42天赛季
    3. 每天显示比赛结果、积分榜变化、杯赛进程
    4. 生成最终报告
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.dependencies import AsyncSessionLocal as async_session_maker
from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus, FixtureType
from app.models.season import CupCompetition, CupGroup
from app.models.league import League, LeagueStanding
from app.models.team import Team
from app.services.season_service import SeasonService
from app.services.standing_service import StandingService


class SeasonTester:
    """赛季测试器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.season_service = SeasonService(db)
        self.standing_service = StandingService(db)
        self.report = {
            "season_number": None,
            "start_time": datetime.now().isoformat(),
            "daily_reports": [],
            "final_standings": {},
            "cup_progress": {},
            "errors": []
        }
    
    def print_header(self, text: str):
        """打印标题"""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80)
    
    def print_section(self, text: str):
        """打印小节标题"""
        print(f"\n{'─' * 60}")
        print(f"  {text}")
        print("─" * 60)
    
    async def get_or_create_season(self) -> Season:
        """获取或创建测试赛季"""
        # 先查找现有赛季
        result = await self.db.execute(
            select(Season).order_by(Season.season_number.desc())
        )
        season = result.scalar_one_or_none()
        
        if season and season.status == SeasonStatus.ONGOING:
            print(f"使用进行中的赛季: 第{season.season_number}赛季")
            return season
        
        if season and season.status == SeasonStatus.PENDING:
            print(f"使用待开始的赛季: 第{season.season_number}赛季")
            return season
        
        # 创建新赛季
        print("创建新赛季...")
        season = await self.season_service.create_new_season()
        print(f"创建成功: 第{season.season_number}赛季")
        return season
    
    async def display_match_result(self, result: dict):
        """显示单场比赛结果"""
        # 获取球队名称
        home_team = await self.db.get(Team, result['home_team'])
        away_team = await self.db.get(Team, result['away_team'])
        
        home_name = home_team.name if home_team else result['home_team'][:8]
        away_name = away_team.name if away_team else result['away_team'][:8]
        
        type_emoji = {
            "league": "🏆",
            "cup_lightning_group": "⚡",
            "cup_lightning_knockout": "⚡",
            "cup_jenny": "🏅"
        }.get(result['type'], "⚽")
        
        print(f"  {type_emoji} {home_name:20s} {result['home_score']} - {result['away_score']} {away_name:20s}")
    
    async def display_league_standings(self, season_id: str):
        """显示联赛积分榜"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(League).options(selectinload(League.system)).order_by(League.level, League.system_id)
        )
        leagues = result.scalars().all()
        
        for league in leagues:
            # 获取积分榜
            standings = await self.standing_service.get_league_standings_with_team_names(
                league.id, season_id
            )
            
            if not standings or standings[0]['played'] == 0:
                continue
            
            system_name = league.system.code if league.system else "未知"
            print(f"\n  📊 {system_name} - {league.name} (Level {league.level})")
            print(f"  {'排名':<6}{'球队':<20}{'赛':<4}{'胜':<4}{'平':<4}{'负':<4}{'进球':<6}{'失球':<6}{'净胜':<6}{'积分':<6}")
            print(f"  {'─' * 70}")
            
            for s in standings[:5]:  # 只显示前5名
                print(f"  {s['position']:<6}{s['team_name'][:18]:<20}{s['played']:<4}{s['won']:<4}{s['drawn']:<4}{s['lost']:<4}{s['goals_for']:<6}{s['goals_against']:<6}{s['goal_difference']:<6}{s['points']:<6}")
            
            if len(standings) > 5:
                print(f"  ... 共 {len(standings)} 支球队")
    
    async def display_cup_progress(self, season_id: str):
        """显示杯赛进程"""
        result = await self.db.execute(
            select(CupCompetition).where(CupCompetition.season_id == season_id)
        )
        competitions = result.scalars().all()
        
        for comp in competitions:
            print(f"\n  🏆 {comp.name}")
            print(f"     状态: {comp.status.value}")
            print(f"     当前轮次: {comp.current_round}")
            
            if comp.code == "LIGHTNING_CUP":
                # 闪电杯 - 显示小组赛情况
                if comp.current_round <= 3:
                    result = await self.db.execute(
                        select(CupGroup).where(CupGroup.competition_id == comp.id)
                    )
                    groups = result.scalars().all()
                    print(f"     小组赛: {len(groups)} 个小组")
                else:
                    print(f"     淘汰赛阶段")
            
            elif comp.code == "JENNY_CUP":
                print(f"     淘汰赛制")
            
            # 显示已完成的比赛数
            result = await self.db.execute(
                select(Fixture).where(
                    Fixture.season_id == season_id,
                    Fixture.cup_competition_id == comp.id,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
            finished_count = len(result.scalars().all())
            print(f"     已完成比赛: {finished_count} 场")
    
    async def process_day(self, season: Season, day: int) -> dict:
        """处理一天的比赛"""
        day_report = {
            "day": day,
            "date": datetime.now().isoformat(),
            "fixtures": [],
            "league_changes": [],
            "cup_events": []
        }
        
        try:
            # 保存处理前的积分榜
            pre_standings = await self.standing_service.get_all_leagues_standings(season.id)
            
            # 处理这一天
            result = await self.season_service.process_next_day(season)
            
            # 显示比赛结果
            if result['results']:
                print(f"\n  📅 第 {day} 天 - 共 {result['fixtures_processed']} 场比赛")
                for match_result in result['results']:
                    await self.display_match_result(match_result)
                    day_report['fixtures'].append(match_result)
            else:
                print(f"\n  📅 第 {day} 天 - 无比赛")
            
            # 显示杯赛晋级事件
            if result.get('cup_progression'):
                print(f"\n  🎯 杯赛晋级事件:")
                for event, desc in result['cup_progression'].items():
                    print(f"     • {event}: {desc}")
                    day_report['cup_events'].append({"event": event, "description": desc})
            
            # 每天显示一次积分榜（前10天、最后5天、每5天）
            if day <= 10 or day >= 38 or day % 5 == 0:
                await self.display_league_standings(season.id)
            
            # 杯赛日显示杯赛进度
            cup_days = [6, 9, 12, 15, 18, 21, 24, 27]
            if day in cup_days:
                await self.display_cup_progress(season.id)
            
            day_report['success'] = True
            return day_report
            
        except Exception as e:
            error_msg = f"第 {day} 天处理失败: {str(e)}"
            print(f"  ❌ {error_msg}")
            day_report['success'] = False
            day_report['error'] = error_msg
            self.report['errors'].append(error_msg)
            return day_report
    
    async def run_full_season(self):
        """运行完整赛季"""
        self.print_header("赛季系统测试 - 完整赛季模拟")
        
        # 获取或创建赛季
        season = await self.get_or_create_season()
        self.report['season_number'] = season.season_number
        
        # 如果赛季未开始，启动它
        if season.status == SeasonStatus.PENDING:
            print(f"\n启动赛季...")
            await self.season_service.start_season(season)
            print(f"赛季已启动！")
        
        # 显示初始状态
        self.print_section("初始状态")
        print(f"  赛季编号: 第{season.season_number}赛季")
        print(f"  当前天数: {season.current_day}/42")
        print(f"  状态: {season.status.value}")
        
        # 显示赛程概览
        result = await self.db.execute(
            select(Fixture).where(Fixture.season_id == season.id)
        )
        all_fixtures = result.scalars().all()
        league_fixtures = [f for f in all_fixtures if f.fixture_type == FixtureType.LEAGUE]
        cup_fixtures = [f for f in all_fixtures if f.fixture_type != FixtureType.LEAGUE]
        
        print(f"\n  赛程统计:")
        print(f"  • 联赛比赛: {len(league_fixtures)} 场")
        print(f"  • 杯赛比赛: {len(cup_fixtures)} 场（部分淘汰赛待生成）")
        print(f"  • 总计: {len(all_fixtures)} 场")
        
        # 运行每一天
        self.print_section("开始模拟比赛")
        
        start_day = season.current_day + 1
        for day in range(start_day, 43):
            day_report = await self.process_day(season, day)
            self.report['daily_reports'].append(day_report)
            
            # 刷新赛季状态
            await self.db.refresh(season)
            
            if season.status == SeasonStatus.FINISHED:
                print(f"\n  ✅ 赛季已结束！")
                break
        
        # 生成最终报告
        await self.generate_final_report(season)
    
    async def generate_final_report(self, season: Season):
        """生成最终报告"""
        self.print_header("赛季结束 - 最终报告")
        
        # 最终积分榜
        self.print_section("最终积分榜")
        final_standings = await self.standing_service.get_all_leagues_standings(season.id)
        self.report['final_standings'] = final_standings
        
        for league_name, data in final_standings.items():
            if not data['standings']:
                continue
            
            print(f"\n  🏆 {data['system']} - {league_name}")
            print(f"  {'排名':<6}{'球队':<20}{'赛':<4}{'胜':<4}{'平':<4}{'负':<4}{'进球':<6}{'失球':<6}{'净胜':<6}{'积分':<6}")
            print(f"  {'─' * 70}")
            
            for s in data['standings']:
                marker = ""
                if s['position'] <= 4:
                    marker = "🏆"  # 升级区/冠军
                elif s['position'] > 12:
                    marker = "⬇️"  # 降级区
                
                print(f"  {s['position']:<6}{s['team_name'][:18]:<20}{s['played']:<4}{s['won']:<4}{s['drawn']:<4}{s['lost']:<4}{s['goals_for']:<6}{s['goals_against']:<6}{s['goal_difference']:<6}{s['points']:<6} {marker}")
        
        # 杯赛冠军
        self.print_section("杯赛结果")
        result = await self.db.execute(
            select(CupCompetition).where(CupCompetition.season_id == season.id)
        )
        competitions = result.scalars().all()
        
        for comp in competitions:
            if comp.winner_team_id:
                winner = await self.db.get(Team, comp.winner_team_id)
                winner_name = winner.name if winner else "未知"
                print(f"  🏆 {comp.name} 冠军: {winner_name}")
            else:
                print(f"  🏆 {comp.name}: 未产生冠军")
        
        # 统计信息
        self.print_section("统计摘要")
        
        result = await self.db.execute(
            select(Fixture).where(
                Fixture.season_id == season.id,
                Fixture.status == FixtureStatus.FINISHED
            )
        )
        finished_fixtures = result.scalars().all()
        
        total_goals = sum(f.home_score + f.away_score for f in finished_fixtures if f.home_score is not None)
        avg_goals = total_goals / len(finished_fixtures) if finished_fixtures else 0
        
        print(f"  总比赛场次: {len(finished_fixtures)}")
        print(f"  总进球数: {total_goals}")
        print(f"  场均进球: {avg_goals:.2f}")
        print(f"  测试耗时: {datetime.now() - datetime.fromisoformat(self.report['start_time'])}")
        
        if self.report['errors']:
            print(f"\n  ⚠️ 错误数: {len(self.report['errors'])}")
            for error in self.report['errors']:
                print(f"     • {error}")
        else:
            print(f"\n  ✅ 测试完成，无错误")
        
        self.report['end_time'] = datetime.now().isoformat()


async def main():
    """主函数"""
    print("=" * 80)
    print("Lightning Super League - 赛季系统测试")
    print("=" * 80)
    
    async with async_session_maker() as db:
        tester = SeasonTester(db)
        await tester.run_full_season()


if __name__ == "__main__":
    asyncio.run(main())
