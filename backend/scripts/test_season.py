#!/usr/bin/env python3
"""
赛季测试脚本 - 支持手动控制和自动模式

用法:
    cd backend && python -m scripts.test_season                    # 交互式模式（默认）
    cd backend && python -m scripts.test_season --init             # 仅初始化数据库
    cd backend && python -m scripts.test_season --next             # 推进一天
    cd backend && python -m scripts.test_season --next 5           # 推进5天
    cd backend && python -m scripts.test_season --auto 50          # 自动推进50天（原模式）
    cd backend && python -m scripts.test_season --standings        # 显示当前积分榜
    cd backend && python -m scripts.test_season --fixtures         # 显示今日赛程

交互式命令:
    n, next     - 推进到下一天
    a, auto N   - 自动推进N天
    s, standings - 显示积分榜
    f, fixtures  - 显示今日赛程
    c, cups      - 显示杯赛情况
    r, results   - 显示最近比赛结果
    i, info      - 显示当前赛季信息
    h, help      - 显示帮助
    q, quit      - 退出
"""

import asyncio
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select, delete, text, and_

from app.config import get_settings
from app.models.base import Base
from app.dependencies import AsyncSessionLocal as async_session_maker
from app.models.season import Season, SeasonStatus, Fixture, FixtureStatus, FixtureType
from app.models.season import CupCompetition, CupGroup
from app.models.league import League, LeagueStanding, LeagueSystem
from app.models.team import Team
from app.models.player import Player
from app.models.user import User, UserStatus
from app.services.season_service import SeasonService
from app.services.standing_service import StandingService


# 初始化系统数据
TEAM_NAMES = {
    "EAST": {
        1: ["东方巨龙", "南海蛟龙", "西海金龙", "北海苍龙", "青龙偃月", "白虎啸天", "朱雀焚霞", "玄武镇海"],
        2: ["华南虎威", "东北虎啸", "西域猛虎", "中原飞虎", "金虎啸月", "银狼啸天", "雪虎踏山", "黑虎掏心"],
        3: ["金鹰破晓", "苍鹰搏兔", "紫电鹰扬", "铁翼飞鹰", "苍穹雄鹰", "沙漠孤鹰", "雪山神鹰", "草原猎鹰",
            "草原战狼", "幽冥鬼狼", "金狼逐日", "火狼焚原", "北方苍狼", "冰狼踏雪", "西域雪狼", "青狼啸月"],
        4: ["武当弟子", "少林武僧", "峨眉女侠", "华山剑客", "昆仑道士", "青城隐者", "崆峒高手", "峨嵋剑客",
            "铁掌水上", "棉里针", "大力金刚", "无影腿", "凌波微步", "降龙十八", "六脉神剑", "九阳神功",
            "太极宗师", "八卦掌门", "形意拳师", "螳螂拳手", "鹰爪功", "铁布衫", "金钟罩", "铁头功",
            "轻功水上", "飞檐走壁", "百步穿杨", "一苇渡江", "如来神掌", "独孤九剑", "葵花宝典", "辟邪剑谱"],
    },
    "WEST": {
        1: ["沙漠之狐", "金字塔尖", "尼罗河神", "撒哈拉驼", "一千零一夜", "阿拉伯夜", "辛巴达航", "绿洲明珠"],
        2: ["石油大亨", "天然气王", "炼油大师", "能源霸主", "石化巨人", "汽油骑士", "管道巨头", "黑金帝国"],
        3: ["波斯地毯", "伊斯法罕", "设拉子酒", "波斯猫王", "居鲁士帝", "薛西斯军", "大流士王", "波斯勇士",
            "阿里巴巴", "阿拉丁灯", "魔毯飞行", "沙漠玫瑰", "咖啡起源", "香料之路", "天方夜谭", "阿拉伯舞"],
        4: ["美索不达", "巴比伦塔", "空中花园", "亚述勇士", "腓尼基船", "迦太基战", "努米底亚", "毛里塔尼",
            "努比亚金", "阿克苏姆", "迦南之地", "死海 scrolls", "佩特拉城", "杰拉什门", "帕尔米拉", "巴尔米拉",
            "闪米特人", "阿拉米人", "亚兰文士", "希伯来先知", "以东勇士", "摩押战士", "亚扪骑士", "赫梯铁匠",
            "米坦尼马", "喀西特弓", "埃兰战车", "苏美尔城", "阿卡德帝", "乌尔第三", "拉格什神", "乌玛勇士"],
    },
    "SOUTH": {
        1: ["桑巴舞者", "美丽游戏", "五人制王", "快乐足球", "绿茵魔术师", "足球精灵", "街球之王", "沙滩足球"],
        2: ["探戈情人", "高乔骑士", "潘帕斯草", "拉普拉塔", "巴塔哥尼", "安第斯山", "布宜诺斯", "阿根廷梦"],
        3: ["里约狂欢", "圣保罗彩", "累西腓鼓", "萨尔瓦多", "花车巡游", "莫莫之王", "桑巴学校", "威尼斯假",
            "亚马逊河", "乌拉圭牛", "印加帝国", "复活节岛", "马丘比丘", "纳斯卡线", "智利红酒", "热带雨林"],
        4: ["加勒比海", "牙买加闪", "古巴雪茄", "多米尼加", "海地革命", "波多黎各", "开曼海龟", "巴哈马群",
            "厄瓜多尔", "哥伦比亚", "委内瑞拉", "圭亚那高", "苏里南河", "法属圭亚", "福克兰群", "火地岛居",
            "阿塔卡马", "瓦尔帕莱", "康塞普西", "拉塞雷纳", "安托法加", "伊基克港", "阿里卡城", "蓬塔阿雷",
            "门多萨酒", "圣胡安矿", "科尔多瓦", "罗萨里奥", "马德普拉", "圣菲之河", "土库曼镇", "圣地亚哥"],
    },
    "NORTH": {
        1: ["红魔曼联", "红军利物浦", "蓝月亮城", "枪手兵工厂", "蓝军切尔西", "白百合热", "三狮军团", "喜鹊纽卡"],
        2: ["太妃糖埃弗", "铁锤帮西汉", "圣徒南安普", "农场主富勒", "山楂球西布", "狼队伍尔弗", "蜜蜂布伦特", "老鹰水晶宫"],
        3: ["银河战舰", "宇宙巴萨", "床单军团", "黄色潜水艇", "皇家社会", "塞维利业", "蝙蝠军团", "斗牛士团",
            "蓝黑战士", "红黑恶魔", "蓝鹰拉齐", "斑马军团", "那不勒斯", "红狼罗马", "紫百合佛", "真蓝黑亚"],
        4: ["维冈竞技", "布莱克浦", "卡迪夫城", "斯旺西海", "布里斯托", "诺丁汉森", "德比郡马", "谢周三",
            "米德尔斯", "桑德兰黑", "米尔沃尔", "查尔顿", "朴茨茅斯", "普利茅斯", "布赖顿海", "水晶宫老",
            "沃特福德", "伯恩利", "赫尔城虎", "利兹联白", "莱斯特城", "考文垂天", "加的夫蓝", "诺维奇金",
            "哈德斯菲", "罗瑟汉姆", "谢菲联", "布拉德福", "唐卡斯特", "吉灵厄姆", "温布尔登", " AFC温布"],
    }
}


def get_tier_team_names(system: str, tier: int, league_idx: int, team_idx: int) -> Tuple[str, str]:
    """获取指定层级球队的名称"""
    if tier == 1:
        global_idx = team_idx
    elif tier == 2:
        global_idx = 8 + team_idx
    elif tier == 3:
        global_idx = 16 + league_idx * 8 + team_idx
    else:
        global_idx = 32 + league_idx * 8 + team_idx
    
    base_names = TEAM_NAMES[system].get(tier, [])
    
    if tier == 3:
        base_names = base_names[league_idx * 8 : (league_idx + 1) * 8]
    elif tier == 4:
        base_names = base_names[league_idx * 8 : (league_idx + 1) * 8]
    
    if team_idx < len(base_names):
        return base_names[team_idx], f"ai_{system.lower()}_{global_idx+1:03d}@lightning.dev"
    return f"Team_{system}_{tier}_{global_idx}", f"ai_{system.lower()}_{global_idx+1:03d}@lightning.dev"


class SeasonTester:
    """赛季测试器 - 支持手动控制"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.season_service = SeasonService(db)
        self.standing_service = StandingService(db)
        self.all_reports = []
        self.current_report = None
        self._current_season: Optional[Season] = None
    
    @property
    async def current_season(self) -> Optional[Season]:
        """获取当前正在进行的赛季"""
        if self._current_season is None:
            result = await self.db.execute(
                select(Season).where(Season.status == SeasonStatus.ONGOING)
            )
            self._current_season = result.scalar_one_or_none()
        return self._current_season
    
    async def refresh_season(self) -> Optional[Season]:
        """刷新当前赛季"""
        result = await self.db.execute(
            select(Season).where(Season.status == SeasonStatus.ONGOING)
        )
        self._current_season = result.scalar_one_or_none()
        return self._current_season
    
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
    
    async def init_database(self):
        """初始化数据库"""
        self.print_header("初始化数据库")
        
        print("  清理并重建数据库...")
        
        from app.dependencies import engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        
        print("  ✅ 数据库表已重建")
        
        print("  创建联赛体系...")
        systems = []
        for code, name in [("EAST", "东区"), ("WEST", "西区"), ("SOUTH", "南区"), ("NORTH", "北区")]:
            system = LeagueSystem(code=code, name=name)
            self.db.add(system)
            systems.append(system)
        await self.db.flush()
        
        print("  创建联赛...")
        leagues = []
        for system in systems:
            league = League(
                name=f"{system.name}超级联赛",
                level=1,
                system_id=system.id,
                max_teams=8
            )
            self.db.add(league)
            leagues.append(league)
            
            league = League(
                name=f"{system.name}甲级联赛",
                level=2,
                system_id=system.id,
                max_teams=8
            )
            self.db.add(league)
            leagues.append(league)
            
            for i in range(2):
                league = League(
                    name=f"{system.name}乙级联赛{'AB'[i]}",
                    level=3,
                    system_id=system.id,
                    max_teams=8
                )
                self.db.add(league)
                leagues.append(league)
            
            for i in range(4):
                league = League(
                    name=f"{system.name}丙级联赛{'ABCD'[i]}",
                    level=4,
                    system_id=system.id,
                    max_teams=8
                )
                self.db.add(league)
                leagues.append(league)
        await self.db.flush()
        
        print("  创建球队和球员...")
        for system in systems:
            system_leagues = [l for l in leagues if l.system_id == system.id]
            leagues_by_level = {1: [], 2: [], 3: [], 4: []}
            for league in system_leagues:
                leagues_by_level[league.level].append(league)
            
            for level in range(1, 5):
                for league_idx, league in enumerate(leagues_by_level[level]):
                    for team_idx in range(8):
                        team_name, user_email = get_tier_team_names(system.code, level, league_idx, team_idx)
                        
                        user = User(
                            email=user_email,
                            username=team_name,
                            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                            is_ai=True,
                            status=UserStatus.ACTIVE
                        )
                        self.db.add(user)
                        await self.db.flush()
                        
                        team = Team(
                            name=team_name,
                            user_id=user.id,
                            current_league_id=league.id
                        )
                        self.db.add(team)
                        
                        for j in range(18):
                            from datetime import date
                            player = Player(
                                first_name=f"球员{j+1}",
                                last_name=team.name,
                                nationality="中国",
                                birth_date=date(2000 + (j % 10), 1, 1),
                                team_id=team.id,
                                primary_position=["GK", "CB", "CM", "ST"][j % 4],
                                shooting=50 + (j % 30),
                                finishing=50 + (j % 30),
                                passing=50 + (j % 30),
                                dribbling=50 + (j % 30),
                                tackling=50 + (j % 30),
                                marking=50 + (j % 30),
                                positioning=50 + (j % 30),
                                reflexes=50 + (j % 30) if j % 4 == 0 else None,
                                handling=50 + (j % 30) if j % 4 == 0 else None
                            )
                            self.db.add(player)
                    
                    await self.db.flush()
        
        await self.db.commit()
        print("  ✅ 数据库初始化完成！")
    
    async def display_current_status(self):
        """显示当前赛季状态"""
        season = await self.refresh_season()
        
        if not season:
            # 检查是否有任何赛季
            result = await self.db.execute(
                select(Season).order_by(Season.season_number.desc())
            )
            last_season = result.scalar_one_or_none()
            
            if last_season:
                print(f"\n  📅 第{last_season.season_number}赛季已结束")
                print(f"     状态: {last_season.status.value}")
                print(f"     最终比赛日: Day {last_season.current_day}")
            else:
                print("\n  ⚠️  没有活跃的赛季")
            return
        
        print(f"\n  📅 第{season.season_number}赛季 - Day {season.current_day}/25")
        print(f"     状态: {season.status.value}")
        
        # 显示今日赛程
        await self.display_today_fixtures(season)
    
    async def display_today_fixtures(self, season: Season):
        """显示今日赛程"""
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season.id,
                    Fixture.season_day == season.current_day
                )
            ).order_by(Fixture.fixture_type)
        )
        fixtures = result.scalars().all()
        
        if not fixtures:
            print(f"     今日无比赛")
            return
        
        league_count = sum(1 for f in fixtures if f.fixture_type == FixtureType.LEAGUE)
        cup_count = sum(1 for f in fixtures if f.fixture_type != FixtureType.LEAGUE)
        
        print(f"     今日赛程: {league_count}场联赛, {cup_count}场杯赛")
        
        for f in fixtures[:5]:  # 只显示前5场
            home = await self.db.get(Team, f.home_team_id)
            away = await self.db.get(Team, f.away_team_id)
            home_name = home.name if home else "?"
            away_name = away.name if away else "?"
            
            type_emoji = {
                FixtureType.LEAGUE: "🏆",
                FixtureType.CUP_LIGHTNING_GROUP: "⚡",
                FixtureType.CUP_LIGHTNING_KNOCKOUT: "⚡",
                FixtureType.CUP_JENNY: "🏅",
                FixtureType.PLAYOFF: "🔄"
            }.get(f.fixture_type, "⚽")
            
            status = "✅" if f.status == FixtureStatus.FINISHED else "⏳"
            score = f"{f.home_score}-{f.away_score}" if f.status == FixtureStatus.FINISHED else "vs"
            print(f"     {type_emoji} {status} {home_name[:12]:<12} {score:^5} {away_name[:12]:<12}")
        
        if len(fixtures) > 5:
            print(f"     ... 还有 {len(fixtures) - 5} 场比赛")
    
    async def display_match_result(self, result: dict, show_stage: bool = False):
        """显示单场比赛结果"""
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
        
        stage_info = ""
        if show_stage and result.get('cup_stage'):
            stage_map = {
                "ROUND_32": "32强",
                "ROUND_16": "16强", 
                "QUARTER": "1/4",
                "SEMI": "半决赛",
                "FINAL": "决赛",
                "GROUP": "小组"
            }
            stage_name = stage_map.get(result['cup_stage'], result['cup_stage'])
            stage_info = f"[{stage_name}] "
        
        print(f"  {type_emoji} {stage_info}{home_name:20s} {result['home_score']} - {result['away_score']} {away_name:20s}")
    
    async def display_cup_details(self, season_id: str, day: int):
        """显示杯赛日的详细信息"""
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.season_day == day,
                    Fixture.fixture_type.in_([FixtureType.CUP_LIGHTNING_GROUP, FixtureType.CUP_LIGHTNING_KNOCKOUT, FixtureType.CUP_JENNY])
                )
            ).order_by(Fixture.fixture_type, Fixture.cup_stage, Fixture.cup_competition_id)
        )
        fixtures = result.scalars().all()
        
        if not fixtures:
            return
        
        cup_fixtures = {
            'lightning_group': [],
            'lightning_knockout': [],
            'jenny': {}
        }
        
        for f in fixtures:
            if f.fixture_type == FixtureType.CUP_LIGHTNING_GROUP:
                cup_fixtures['lightning_group'].append(f)
            elif f.fixture_type == FixtureType.CUP_LIGHTNING_KNOCKOUT:
                cup_fixtures['lightning_knockout'].append(f)
            elif f.fixture_type == FixtureType.CUP_JENNY:
                comp_id = f.cup_competition_id or 'unknown'
                if comp_id not in cup_fixtures['jenny']:
                    cup_fixtures['jenny'][comp_id] = []
                cup_fixtures['jenny'][comp_id].append(f)
        
        if cup_fixtures['lightning_group']:
            print(f"\n  ⚡ 闪电杯 - 小组赛")
            for f in cup_fixtures['lightning_group']:
                await self._display_cup_fixture(f, show_group=True)
        
        if cup_fixtures['lightning_knockout']:
            print(f"\n  ⚡ 闪电杯 - 淘汰赛")
            for f in cup_fixtures['lightning_knockout']:
                await self._display_cup_fixture(f)
        
        if cup_fixtures['jenny']:
            for comp_id, fixtures in cup_fixtures['jenny'].items():
                if fixtures:
                    comp = await self.db.get(CupCompetition, comp_id)
                    comp_name = comp.name if comp else "杰尼杯"
                    stage = fixtures[0].cup_stage or ""
                    stage_map = {"ROUND_32": "32强", "ROUND_16": "16强", "QUARTER": "8强", "SEMI": "半决赛", "FINAL": "决赛"}
                    stage_name = stage_map.get(stage, stage)
                    print(f"\n  🏅 {comp_name} - {stage_name}")
                    for f in fixtures:
                        await self._display_cup_fixture(f)
    
    async def _display_cup_fixture(self, fixture: Fixture, show_group: bool = False):
        """显示单个杯赛对阵"""
        home_team = await self.db.get(Team, fixture.home_team_id)
        away_team = await self.db.get(Team, fixture.away_team_id)
        
        home_name = home_team.name if home_team else fixture.home_team_id[:8]
        away_name = away_team.name if away_team else fixture.away_team_id[:8]
        
        group_info = f"[{fixture.cup_group_name}] " if show_group and fixture.cup_group_name else ""
        
        if fixture.status == FixtureStatus.FINISHED:
            if fixture.home_score > fixture.away_score:
                print(f"     {group_info}{home_name:18s} ✓ {fixture.home_score} - {fixture.away_score}   {away_name:18s}")
            elif fixture.home_score < fixture.away_score:
                print(f"     {group_info}{home_name:18s}   {fixture.home_score} - {fixture.away_score} ✓ {away_name:18s}")
            else:
                print(f"     {group_info}{home_name:18s}   {fixture.home_score} - {fixture.away_score}   {away_name:18s}")
        else:
            print(f"     {group_info}{home_name:18s}   vs   {away_name:18s}")
    
    async def display_playoff_details(self, season_id: str, day: int):
        """显示升降级附加赛详情"""
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.season_day == day,
                    Fixture.fixture_type == FixtureType.PLAYOFF
                )
            )
        )
        fixtures = result.scalars().all()
        
        if not fixtures:
            return
        
        print(f"\n  🏆 升降级附加赛 - Day {day}")
        for f in fixtures:
            home_team = await self.db.get(Team, f.home_team_id)
            away_team = await self.db.get(Team, f.away_team_id)
            home_name = home_team.name if home_team else f.home_team_id[:8]
            away_name = away_team.name if away_team else f.away_team_id[:8]
            
            stage = ""
            if f.cup_stage:
                if f.cup_stage.startswith("P_"):
                    stage = "[预选] "
                elif f.cup_stage.startswith("F_"):
                    stage = "[决赛] "
            
            if f.status == FixtureStatus.FINISHED:
                if f.home_score > f.away_score:
                    print(f"     {stage}{home_name:18s} ✓ {f.home_score} - {f.away_score}   {away_name:18s}")
                elif f.home_score < f.away_score:
                    print(f"     {stage}{home_name:18s}   {f.home_score} - {f.away_score} ✓ {away_name:18s}")
                else:
                    print(f"     {stage}{home_name:18s}   {f.home_score} - {f.away_score}   {away_name:18s}")
            else:
                print(f"     {stage}{home_name:18s}   vs   {away_name:18s}")
    
    async def display_league_standings(self, season_id: Optional[str] = None, show_all: bool = False):
        """显示联赛积分榜"""
        if season_id is None:
            season = await self.refresh_season()
            if season:
                season_id = season.id
            else:
                # 获取最近一个赛季
                result = await self.db.execute(
                    select(Season).order_by(Season.season_number.desc())
                )
                last_season = result.scalar_one_or_none()
                if last_season:
                    season_id = last_season.id
                else:
                    print("  ⚠️  没有找到赛季")
                    return
        
        self.print_section("联赛积分榜")
        
        result = await self.db.execute(
            select(League).options(selectinload(League.system)).order_by(League.level, League.system_id)
        )
        leagues = result.scalars().all()
        
        for league in leagues:
            standings = await self.standing_service.get_league_standings_with_team_names(
                league.id, season_id
            )
            
            if not standings:
                continue
            
            # 只显示有比赛的联赛
            has_played = any(s['played'] > 0 for s in standings)
            if not has_played and not show_all:
                continue
            
            system_name = league.system.code if league.system else "未知"
            print(f"\n  📊 {system_name} - {league.name} (Level {league.level})")
            print(f"  {'排名':<6}{'球队':<20}{'赛':<4}{'胜':<4}{'平':<4}{'负':<4}{'进球':<6}{'失球':<6}{'净胜':<6}{'积分':<6}")
            print(f"  {'─' * 70}")
            
            display_count = len(standings) if show_all else 8
            for s in standings[:display_count]:
                marker = ""
                if s['position'] <= 2 and league.level > 1:
                    marker = "⬆️"
                elif s['position'] <= 4 and league.level == 1:
                    marker = "🏆"
                elif s['position'] > 6:
                    marker = "⬇️"
                
                print(f"  {s['position']:<6}{s['team_name'][:18]:<20}{s['played']:<4}{s['won']:<4}{s['drawn']:<4}{s['lost']:<4}{s['goals_for']:<6}{s['goals_against']:<6}{s['goal_difference']:<6}{s['points']:<6} {marker}")
    
    async def display_cup_standings(self):
        """显示杯赛情况"""
        season = await self.refresh_season()
        if not season:
            print("  ⚠️  没有活跃的赛季")
            return
        
        self.print_section("杯赛情况")
        
        # 闪电杯
        result = await self.db.execute(
            select(CupCompetition).where(
                and_(
                    CupCompetition.season_id == season.id,
                    CupCompetition.name.like("%闪电杯%")
                )
            )
        )
        lightning = result.scalar_one_or_none()
        
        if lightning:
            print(f"\n  ⚡ 闪电杯")
            print(f"     阶段: {lightning.stage.value}")
            if lightning.winner_team_id:
                winner = await self.db.get(Team, lightning.winner_team_id)
                print(f"     冠军: {winner.name if winner else '未知'}")
            
            # 显示当前进行中的比赛
            result = await self.db.execute(
                select(Fixture).where(
                    and_(
                        Fixture.cup_competition_id == lightning.id,
                        Fixture.status == FixtureStatus.SCHEDULED
                    )
                ).order_by(Fixture.season_day)
            )
            upcoming = result.scalars().all()
            if upcoming:
                print(f"     即将进行: {len(upcoming)} 场比赛")
        
        # 杰尼杯
        result = await self.db.execute(
            select(CupCompetition).where(
                and_(
                    CupCompetition.season_id == season.id,
                    CupCompetition.name.like("%杰尼杯%")
                )
            )
        )
        jenny_comps = result.scalars().all()
        
        if jenny_comps:
            print(f"\n  🏅 杰尼杯（{len(jenny_comps)} 个赛区）")
            for comp in jenny_comps[:4]:  # 只显示前4个
                print(f"     {comp.name}: {comp.stage.value}")
                if comp.winner_team_id:
                    winner = await self.db.get(Team, comp.winner_team_id)
                    print(f"       冠军: {winner.name if winner else '未知'}")
    
    async def display_recent_results(self, days: int = 3):
        """显示最近几天的比赛结果"""
        season = await self.refresh_season()
        if not season:
            print("  ⚠️  没有活跃的赛季")
            return
        
        self.print_section(f"最近比赛结果")
        
        start_day = max(1, season.current_day - days)
        
        for day in range(start_day, season.current_day):
            result = await self.db.execute(
                select(Fixture).where(
                    and_(
                        Fixture.season_id == season.id,
                        Fixture.season_day == day,
                        Fixture.status == FixtureStatus.FINISHED
                    )
                )
            )
            fixtures = result.scalars().all()
            
            if not fixtures:
                continue
            
            print(f"\n  📅 Day {day} ({len(fixtures)} 场比赛)")
            
            for f in fixtures[:6]:  # 每场显示前6场
                home = await self.db.get(Team, f.home_team_id)
                away = await self.db.get(Team, f.away_team_id)
                home_name = home.name if home else "?"
                away_name = away.name if away else "?"
                
                type_emoji = {
                    FixtureType.LEAGUE: "🏆",
                    FixtureType.CUP_LIGHTNING_GROUP: "⚡",
                    FixtureType.CUP_LIGHTNING_KNOCKOUT: "⚡",
                    FixtureType.CUP_JENNY: "🏅",
                    FixtureType.PLAYOFF: "🔄"
                }.get(f.fixture_type, "⚽")
                
                print(f"     {type_emoji} {home_name[:12]:<12} {f.home_score}-{f.away_score} {away_name[:12]:<12}")
            
            if len(fixtures) > 6:
                print(f"     ... 还有 {len(fixtures) - 6} 场")
    
    async def process_next_day(self, count: int = 1) -> dict:
        """推进一天或多天"""
        season = await self.refresh_season()
        
        if not season:
            print("  ⚠️  没有活跃的赛季，尝试创建新赛季...")
            season = await self.season_service.create_new_season()
            await self.season_service.start_season(season)
            print(f"  ✅ 创建并启动第{season.season_number}赛季")
            self._current_season = season
        
        results = {
            'days_processed': 0,
            'fixtures_total': 0,
            'season_switched': False,
            'new_season_number': None
        }
        
        for i in range(count):
            season = await self.refresh_season()
            
            if not season or season.status == SeasonStatus.FINISHED:
                # 赛季已结束，尝试创建新赛季
                season = await self.season_service.create_new_season()
                await self.season_service.start_season(season)
                results['season_switched'] = True
                results['new_season_number'] = season.season_number
                print(f"\n  ✅ 自动创建并启动第{season.season_number}赛季")
            
            day = season.current_day
            
            try:
                result = await self.season_service.process_next_day(season)
                results['days_processed'] += 1
                results['fixtures_total'] += result.get('fixtures_processed', 0)
                
                # 显示结果
                fixtures_processed = result.get('fixtures_processed', 0)
                cup_events = result.get('cup_progression', {})
                
                if fixtures_processed > 0:
                    # 分类统计
                    fixture_types = {}
                    for r in result.get('results', []):
                        t = r['type']
                        fixture_types[t] = fixture_types.get(t, 0) + 1
                    
                    type_str = ', '.join([f"{k.replace('cup_', '').replace('lightning_', '⚡').replace('jenny', '🏅')}:{v}" 
                                          for k, v in fixture_types.items()])
                    
                    print(f"  📅 Day {day:2d}: {fixtures_processed:2d} 场 ({type_str})")
                else:
                    print(f"  📅 Day {day:2d}: 无比赛")
                
                # 显示杯赛事件
                for event, desc in cup_events.items():
                    if 'winner' in event.lower():
                        print(f"     🏆 {desc}")
                    elif 'promotion' in event.lower() or 'relegation' in event.lower():
                        print(f"     🔄 {desc}")
                
                # 检查赛季是否刚结束
                await self.db.refresh(season)
                if season.status == SeasonStatus.FINISHED:
                    print(f"\n  ✅ 第{season.season_number}赛季已结束！")
                    
            except Exception as e:
                print(f"  ❌ Day {day} 处理失败: {e}")
                import traceback
                traceback.print_exc()
                break
        
        return results
    
    async def interactive_mode(self):
        """交互式模式"""
        self.print_header("Lightning Super League - 交互式赛季控制台")
        print("""
  命令:
    n, next      - 推进到下一天
    a, auto N    - 自动推进N天
    s, standings - 显示积分榜
    f, fixtures  - 显示今日赛程
    c, cups      - 显示杯赛情况
    r, results   - 显示最近比赛结果
    i, info      - 显示当前赛季信息
    h, help      - 显示帮助
    q, quit      - 退出
        """)
        
        # 显示初始状态
        await self.display_current_status()
        
        while True:
            try:
                season = await self.refresh_season()
                day = season.current_day if season else "?"
                season_num = season.season_number if season else "?"
                
                cmd = input(f"\n[S{season_num}D{day}] > ").strip().lower()
                
                if not cmd:
                    continue
                
                parts = cmd.split()
                action = parts[0]
                
                if action in ('n', 'next'):
                    count = int(parts[1]) if len(parts) > 1 else 1
                    await self.process_next_day(count)
                
                elif action in ('a', 'auto'):
                    count = int(parts[1]) if len(parts) > 1 else 5
                    print(f"\n  自动推进 {count} 天...")
                    await self.process_next_day(count)
                
                elif action in ('s', 'standings'):
                    await self.display_league_standings()
                
                elif action in ('f', 'fixtures'):
                    season = await self.refresh_season()
                    if season:
                        await self.display_today_fixtures(season)
                    else:
                        print("  ⚠️  没有活跃的赛季")
                
                elif action in ('c', 'cups'):
                    await self.display_cup_standings()
                
                elif action in ('r', 'results'):
                    days = int(parts[1]) if len(parts) > 1 else 3
                    await self.display_recent_results(days)
                
                elif action in ('i', 'info'):
                    await self.display_current_status()
                
                elif action in ('h', 'help'):
                    print("""
  命令:
    n, next [N]  - 推进N天（默认1天）
    a, auto N    - 自动推进N天
    s, standings - 显示积分榜
    f, fixtures  - 显示今日赛程
    c, cups      - 显示杯赛情况
    r, results [N] - 显示最近N天结果（默认3天）
    i, info      - 显示当前赛季信息
    h, help      - 显示帮助
    q, quit      - 退出
                    """)
                
                elif action in ('q', 'quit', 'exit'):
                    print("\n  再见！")
                    break
                
                else:
                    print(f"  未知命令: {action}，输入 h 查看帮助")
            
            except KeyboardInterrupt:
                print("\n\n  再见！")
                break
            except Exception as e:
                print(f"  错误: {e}")
                import traceback
                traceback.print_exc()
    
    # ============ 以下保持原有功能兼容 ============
    
    async def run_season(self, season_number: int) -> Season:
        """运行单个赛季（自动模式）"""
        self.print_header(f"第{season_number}赛季 - 完整模拟")
        
        season = await self.season_service.create_new_season()
        self.current_report = {
            "season_number": season.season_number,
            "start_time": datetime.now().isoformat(),
            "daily_reports": [],
            "errors": []
        }
        
        print(f"创建成功: 第{season.season_number}赛季")
        
        print(f"\n启动赛季...")
        await self.season_service.start_season(season)
        print(f"赛季已启动！")
        
        result = await self.db.execute(
            select(Fixture).where(Fixture.season_id == season.id)
        )
        all_fixtures = result.scalars().all()
        league_fixtures = [f for f in all_fixtures if f.fixture_type == FixtureType.LEAGUE]
        cup_fixtures = [f for f in all_fixtures if f.fixture_type != FixtureType.LEAGUE]
        
        print(f"\n  赛程统计:")
        print(f"  • 联赛比赛: {len(league_fixtures)} 场")
        print(f"  • 杯赛比赛: {len(cup_fixtures)} 场")
        print(f"  • 总计: {len(all_fixtures)} 场")
        
        self.print_section("开始模拟比赛")
        
        for day in range(1, 26):
            day_report = await self._process_day_auto(season, day)
            self.current_report['daily_reports'].append(day_report)
            
            await self.db.refresh(season)
            
            if season.status == SeasonStatus.FINISHED:
                print(f"\n  ✅ 赛季已结束！")
                break
        
        await self._generate_season_report(season)
        
        self.current_report['end_time'] = datetime.now().isoformat()
        self.all_reports.append(self.current_report)
        
        return season
    
    async def _process_day_auto(self, season: Season, day: int) -> dict:
        """自动模式处理一天"""
        day_report = {
            "day": day,
            "fixtures": [],
            "cup_events": []
        }
        
        lightning_cup_days = [4, 6, 8, 10, 12, 14, 21]
        jenny_cup_days = [4, 6, 8, 10, 12, 14, 15]
        playoff_days = [22, 23]
        promotion_day = 24
        offseason_days = [25]
        
        is_cup_day = day in lightning_cup_days or day in jenny_cup_days
        is_playoff_day = day in playoff_days
        is_promotion_day = day == promotion_day
        is_offseason = day in offseason_days
        
        try:
            result = await self.season_service.process_next_day(season)
            
            if is_offseason:
                print(f"\n  📅 第 {day} 天 - 休赛期")
                day_report['success'] = True
                return day_report
            
            if is_promotion_day:
                print(f"\n  📅 第 {day} 天 - 升降级处理")
                day_report['success'] = True
                return day_report
            
            if result['results']:
                if is_playoff_day:
                    print(f"\n  📅 第 {day} 天 - 共 {result['fixtures_processed']} 场比赛")
                    await self.display_playoff_details(season.id, day)
                elif is_cup_day:
                    fixture_types = {}
                    for r in result['results']:
                        t = r['type']
                        fixture_types[t] = fixture_types.get(t, 0) + 1
                    type_str = ', '.join([f"{k}:{v}" for k, v in fixture_types.items()])
                    print(f"  📅 第 {day:2d} 天 - {result['fixtures_processed']:3d} 场 ({type_str})")
                    
                    if result.get('cup_progression'):
                        events = [k for k in result['cup_progression'].keys() if 'winner' in k.lower()]
                        if events:
                            print(f"  🎯 {', '.join(events)}")
                else:
                    print(f"  📅 第 {day:2d} 天 - {result['fixtures_processed']:3d} 场 (联赛)")
                
                day_report['fixtures'] = result['results']
            else:
                print(f"  📅 第 {day:2d} 天 - 无比赛")
            
            day_report['success'] = True
            return day_report
            
        except Exception as e:
            import traceback
            error_msg = f"第 {day} 天处理失败: {str(e)}"
            print(f"  ❌ {error_msg}")
            traceback.print_exc()
            day_report['success'] = False
            day_report['error'] = error_msg
            self.current_report['errors'].append(error_msg)
            return day_report
    
    async def _generate_season_report(self, season: Season):
        """生成赛季报告"""
        self.print_section("赛季总结")
        
        print("\n  📊 各联赛前3名:")
        result = await self.db.execute(
            select(League).order_by(League.level)
        )
        leagues = result.scalars().all()
        
        for league in leagues:
            standings = await self.standing_service.get_league_standings_with_team_names(
                league.id, season.id
            )
            if standings and len(standings) > 0:
                top3 = [s['team_name'] for s in standings[:3]]
                print(f"  {league.name}: {', '.join(top3)}")
        
        print("\n  🏆 杯赛冠军:")
        result = await self.db.execute(
            select(CupCompetition).where(CupCompetition.season_id == season.id)
        )
        competitions = result.scalars().all()
        
        for comp in competitions:
            if comp.winner_team_id:
                winner = await self.db.get(Team, comp.winner_team_id)
                print(f"  {comp.name}: {winner.name if winner else '未知'}")
        
        result = await self.db.execute(
            select(Fixture).where(
                Fixture.season_id == season.id,
                Fixture.status == FixtureStatus.FINISHED
            )
        )
        finished_fixtures = result.scalars().all()
        total_goals = sum(f.home_score + f.away_score for f in finished_fixtures if f.home_score is not None)
        avg_goals = total_goals / len(finished_fixtures) if finished_fixtures else 0
        
        print(f"\n  📈 统计:")
        print(f"  总比赛: {len(finished_fixtures)} 场")
        print(f"  总进球: {total_goals} 球")
        print(f"  场均进球: {avg_goals:.2f} 球")
    
    async def run_continuous(self, total_days: int = 50):
        """连续推进多天（原自动模式）"""
        self.print_header(f"连续推进测试 - 共 {total_days} 天")
        
        season = await self.season_service.create_new_season()
        print(f"创建成功: 第{season.season_number}赛季")
        
        await self.season_service.start_season(season)
        print(f"赛季已启动！\n")
        
        season_count = 1
        
        for global_day in range(1, total_days + 1):
            try:
                result = await self.season_service.process_next_day(season)
                
                result_query = await self.db.execute(
                    select(Season).where(Season.status == SeasonStatus.ONGOING)
                )
                current_season = result_query.scalar_one_or_none()
                
                if current_season and current_season.id != season.id:
                    season_count += 1
                    print(f"\n  ✅ 自动切换到第{current_season.season_number}赛季")
                    season = current_season
                elif current_season:
                    season = current_season
                
                day = season.current_day
                is_special = day in [1, 21, 22, 23, 24, 25] or global_day % 5 == 0
                
                if is_special:
                    print(f"  📅 全局第 {global_day:2d} 天 | 第{season.season_number}赛季第 {day:2d} 天 - {result['fixtures_processed']} 场比赛")
                
                if result.get('cup_progression'):
                    for event, desc in result['cup_progression'].items():
                        if 'promotion' in event.lower() or 'relegation' in event.lower() or '升降级' in str(desc):
                            print(f"     🎯 {desc}")
                
            except Exception as e:
                print(f"  ❌ 第 {global_day} 天处理失败: {e}")
                import traceback
                traceback.print_exc()
                raise
        
        print(f"\n  ✅ 连续推进完成！共 {total_days} 天，经历了 {season_count} 个赛季")
        return season_count


async def main():
    """主函数 - 支持命令行参数"""
    parser = argparse.ArgumentParser(
        description='Lightning Super League 赛季测试工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m scripts.test_season                    # 交互式模式
  python -m scripts.test_season --init             # 仅初始化数据库
  python -m scripts.test_season --next             # 推进一天
  python -m scripts.test_season --next 5           # 推进5天
  python -m scripts.test_season --auto 50          # 自动推进50天
  python -m scripts.test_season --standings        # 显示积分榜
  python -m scripts.test_season --fixtures         # 显示今日赛程
        """
    )
    
    parser.add_argument('--init', action='store_true', help='初始化数据库')
    parser.add_argument('--next', type=int, nargs='?', const=1, metavar='N', help='推进N天（默认1天）')
    parser.add_argument('--auto', type=int, metavar='DAYS', help='自动推进D天')
    parser.add_argument('--standings', action='store_true', help='显示积分榜')
    parser.add_argument('--fixtures', action='store_true', help='显示今日赛程')
    parser.add_argument('--cups', action='store_true', help='显示杯赛情况')
    parser.add_argument('--interactive', '-i', action='store_true', help='交互式模式（默认）')
    
    args = parser.parse_args()
    
    async with async_session_maker() as db:
        tester = SeasonTester(db)
        
        # 检查是否有命令行参数
        has_args = any([args.init, args.next, args.auto, args.standings, args.fixtures, args.cups])
        
        if args.init:
            await tester.init_database()
            print("\n✅ 数据库初始化完成！")
            return
        
        if args.next:
            await tester.process_next_day(args.next)
            return
        
        if args.auto:
            await tester.run_continuous(args.auto)
            return
        
        if args.standings:
            await tester.display_league_standings()
            return
        
        if args.fixtures:
            season = await tester.refresh_season()
            if season:
                await tester.display_today_fixtures(season)
            else:
                print("⚠️  没有活跃的赛季")
            return
        
        if args.cups:
            await tester.display_cup_standings()
            return
        
        # 默认交互式模式
        if not has_args or args.interactive:
            # 检查是否需要初始化
            result = await db.execute(select(Season))
            has_season = result.scalar_one_or_none() is not None
            
            if not has_season:
                print("检测到数据库为空，先进行初始化...")
                await tester.init_database()
            
            await tester.interactive_mode()


if __name__ == "__main__":
    asyncio.run(main())
