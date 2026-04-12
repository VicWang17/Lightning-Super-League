#!/usr/bin/env python3
"""
赛季测试脚本 - 完整赛季模拟测试（支持双赛季+升降级测试）

用法:
    cd backend && python -m scripts.test_season

功能:
    1. 自动初始化数据库
    2. 运行完整第1赛季
    3. 处理升降级
    4. 运行完整第2赛季
    5. 生成最终报告
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, text

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
# 球队命名规则：每个体系需要 8+8+16+32 = 64 个队名
# Level 1: 8队, Level 2: 8队, Level 3: 16队(2联赛), Level 4: 32队(4联赛)
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
    """获取指定层级球队的名称
    
    Args:
        system: 体系代码
        tier: 级别 (1-4)
        league_idx: 在该级别内的联赛索引 (0-based)
        team_idx: 在该联赛内的球队索引 (0-based)
    """
    # 计算在完整球队列表中的全局索引
    if tier == 1:
        global_idx = team_idx  # 0-7
    elif tier == 2:
        global_idx = 8 + team_idx  # 8-15
    elif tier == 3:
        global_idx = 16 + league_idx * 8 + team_idx  # 16-31
    else:  # tier == 4
        global_idx = 32 + league_idx * 8 + team_idx  # 32-63
    
    base_names = TEAM_NAMES[system].get(tier, [])
    
    # 为重复层级选择正确的子列表
    if tier == 3:
        # Level 3: 2个联赛，16个队名
        base_names = base_names[league_idx * 8 : (league_idx + 1) * 8]
    elif tier == 4:
        # Level 4: 4个联赛，32个队名
        base_names = base_names[league_idx * 8 : (league_idx + 1) * 8]
    
    if team_idx < len(base_names):
        return base_names[team_idx], f"ai_{system.lower()}_{global_idx+1:03d}@lightning.dev"
    return f"Team_{system}_{tier}_{global_idx}", f"ai_{system.lower()}_{global_idx+1:03d}@lightning.dev"


class SeasonTester:
    """赛季测试器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.season_service = SeasonService(db)
        self.standing_service = StandingService(db)
        self.all_reports = []
        self.current_report = None
    
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
        
        # 删除所有表并重新创建（确保ENUM类型更新）
        print("  清理并重建数据库...")
        
        # 重新创建所有表（使用 SQLAlchemy 自动处理依赖关系）
        from app.dependencies import engine
        async with engine.begin() as conn:
            # 先删除所有表（按依赖顺序）
            await conn.run_sync(Base.metadata.drop_all)
            # 重新创建所有表
            await conn.run_sync(Base.metadata.create_all)
        
        print("  ✅ 数据库表已重建")
        
        print("  创建联赛体系...")
        # 创建4个联赛体系
        systems = []
        for code, name in [("EAST", "东区"), ("WEST", "西区"), ("SOUTH", "南区"), ("NORTH", "北区")]:
            system = LeagueSystem(code=code, name=name)
            self.db.add(system)
            systems.append(system)
        await self.db.flush()
        
        # 创建联赛（每体系: 1个L1 + 1个L2 + 2个L3 + 4个L4 = 8个联赛，共56队用于杰尼杯）
        print("  创建联赛...")
        leagues = []
        for system in systems:
            # Level 1: 1个联赛（8队，闪电杯）
            league = League(
                name=f"{system.name}超级联赛",
                level=1,
                system_id=system.id,
                max_teams=8
            )
            self.db.add(league)
            leagues.append(league)
            
            # Level 2: 1个联赛（8队，杰尼杯种子）
            league = League(
                name=f"{system.name}甲级联赛",
                level=2,
                system_id=system.id,
                max_teams=8
            )
            self.db.add(league)
            leagues.append(league)
            
            # Level 3: 2个联赛（16队，杰尼杯预选赛）
            for i in range(2):
                league = League(
                    name=f"{system.name}乙级联赛{'AB'[i]}",
                    level=3,
                    system_id=system.id,
                    max_teams=8
                )
                self.db.add(league)
                leagues.append(league)
            
            # Level 4: 4个联赛（32队，杰尼杯预选赛）
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
        
        # 创建球队和用户
        print("  创建球队和球员...")
        for system in systems:
            # 按级别分组联赛
            system_leagues = [l for l in leagues if l.system_id == system.id]
            leagues_by_level = {1: [], 2: [], 3: [], 4: []}
            for league in system_leagues:
                leagues_by_level[league.level].append(league)
            
            for level in range(1, 5):
                for league_idx, league in enumerate(leagues_by_level[level]):
                    teams_in_league = []
                    for team_idx in range(8):
                        team_name, user_email = get_tier_team_names(system.code, level, league_idx, team_idx)
                        
                        # 创建AI用户
                        user = User(
                            email=user_email,
                            username=team_name,
                            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
                            is_ai=True,
                            status=UserStatus.ACTIVE
                        )
                        self.db.add(user)
                        await self.db.flush()
                        
                        # 创建球队
                        team = Team(
                            name=team_name,
                            user_id=user.id,
                            current_league_id=league.id
                        )
                        self.db.add(team)
                        teams_in_league.append(team)
                        
                        # 为球队创建18名球员
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
        
        # 添加比赛阶段信息
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
        from sqlalchemy import select, and_
        
        # 查询当天的所有杯赛
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
        
        # 按杯赛类型分组
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
        
        # 显示闪电杯小组赛
        if cup_fixtures['lightning_group']:
            print(f"\n  ⚡ 闪电杯 - 小组赛")
            for f in cup_fixtures['lightning_group']:
                await self._display_cup_fixture(f, show_group=True)
        
        # 显示闪电杯淘汰赛
        if cup_fixtures['lightning_knockout']:
            print(f"\n  ⚡ 闪电杯 - 淘汰赛")
            for f in cup_fixtures['lightning_knockout']:
                await self._display_cup_fixture(f)
        
        # 显示杰尼杯
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
            # 高亮获胜方
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
        from sqlalchemy import select, and_
        
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
            
            # 解析阶段
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
    
    async def display_league_standings(self, season_id: str, show_all: bool = False):
        """显示联赛积分榜"""
        from sqlalchemy.orm import selectinload
        
        result = await self.db.execute(
            select(League).options(selectinload(League.system)).order_by(League.level, League.system_id)
        )
        leagues = result.scalars().all()
        
        for league in leagues:
            standings = await self.standing_service.get_league_standings_with_team_names(
                league.id, season_id
            )
            
            if not standings or standings[0]['played'] == 0:
                continue
            
            system_name = league.system.code if league.system else "未知"
            print(f"\n  📊 {system_name} - {league.name} (Level {league.level})")
            print(f"  {'排名':<6}{'球队':<20}{'赛':<4}{'胜':<4}{'平':<4}{'负':<4}{'进球':<6}{'失球':<6}{'净胜':<6}{'积分':<6}")
            print(f"  {'─' * 70}")
            
            display_count = len(standings) if show_all else 5
            for s in standings[:display_count]:
                marker = ""
                if s['position'] <= 2 and league.level > 1:
                    marker = "⬆️"  # 升级区
                elif s['position'] <= 4 and league.level == 1:
                    marker = "🏆"  # 顶级联赛欧战区
                elif s['position'] > 6:
                    marker = "⬇️"  # 降级区
                
                print(f"  {s['position']:<6}{s['team_name'][:18]:<20}{s['played']:<4}{s['won']:<4}{s['drawn']:<4}{s['lost']:<4}{s['goals_for']:<6}{s['goals_against']:<6}{s['goal_difference']:<6}{s['points']:<6} {marker}")
    
    async def show_promotion_relegation(self, season: Season):
        """显示升降级情况（由系统自动处理，这里仅展示结果）"""
        self.print_section("赛季结束 - 升降级情况")
        
        # 显示各联赛冠军和升降级区
        result = await self.db.execute(select(League).order_by(League.level))
        leagues = result.scalars().all()
        
        for league in leagues:
            standings = await self.standing_service.get_league_standings_with_team_names(
                league.id, season.id
            )
            if not standings:
                continue
            
            if league.level == 1:
                # 顶级联赛冠军
                print(f"  🏆 {league.name} 冠军: {standings[0]['team_name']}")
            else:
                # 升级区
                up_teams = [s['team_name'] for s in standings[:2]]
                print(f"  ⬆️ {league.name} 升级: {', '.join(up_teams)}")
            
            if league.level < 4:
                # 降级区
                down_teams = [s['team_name'] for s in standings[-2:]]
                print(f"  ⬇️ {league.name} 降级: {', '.join(down_teams)}")
        
        print(f"\n  ℹ️  升降级由系统自动处理，新赛季将自动调整球队位置")
    
    async def run_season(self, season_number: int) -> Season:
        """运行单个赛季"""
        self.print_header(f"第{season_number}赛季 - 完整模拟")
        
        # 创建新赛季
        season = await self.season_service.create_new_season()
        self.current_report = {
            "season_number": season.season_number,
            "start_time": datetime.now().isoformat(),
            "daily_reports": [],
            "errors": []
        }
        
        print(f"创建成功: 第{season.season_number}赛季")
        
        # 启动赛季
        print(f"\n启动赛季...")
        await self.season_service.start_season(season)
        print(f"赛季已启动！")
        
        # 显示赛程统计
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
        
        # 运行每一天
        self.print_section("开始模拟比赛")
        
        for day in range(1, 26):  # Day 1-25
            day_report = await self.process_day(season, day)
            self.current_report['daily_reports'].append(day_report)
            
            await self.db.refresh(season)
            
            if season.status == SeasonStatus.FINISHED:
                print(f"\n  ✅ 赛季已结束！")
                break
        
        # 生成赛季报告
        await self.generate_season_report(season)
        
        self.current_report['end_time'] = datetime.now().isoformat()
        self.all_reports.append(self.current_report)
        
        return season
    
    async def process_day(self, season: Season, day: int) -> dict:
        """处理一天的比赛"""
        day_report = {
            "day": day,
            "fixtures": [],
            "cup_events": []
        }
        
        # 特殊日期定义
        lightning_cup_days = [4, 6, 8, 10, 12, 14, 21]  # 闪电杯比赛日
        jenny_cup_days = [4, 6, 8, 10, 12, 14, 15]  # 杰尼杯比赛日
        playoff_days = [22, 23]  # 升降级附加赛日
        promotion_day = 24  # 升降级处理日
        offseason_days = [25]  # 休赛期（Day 25）
        
        is_cup_day = day in lightning_cup_days or day in jenny_cup_days
        is_playoff_day = day in playoff_days
        is_promotion_day = day == promotion_day
        is_offseason = day in offseason_days
        
        try:
            result = await self.season_service.process_next_day(season)
            
            # 处理休赛期
            if is_offseason:
                print(f"\n  📅 第 {day} 天 - 休赛期")
                if result.get('cup_progression'):
                    print(f"  🎯 事件: {', '.join(result['cup_progression'].keys())}")
                day_report['success'] = True
                return day_report
            
            # 处理升降级日
            if is_promotion_day:
                print(f"\n  📅 第 {day} 天 - 升降级处理")
                if result.get('cup_progression'):
                    for event, desc in result['cup_progression'].items():
                        print(f"  🎯 {event}: {desc}")
                day_report['success'] = True
                return day_report
            
            # 处理有比赛的日子
            if result['results']:
                # 附加赛日：详细显示
                if is_playoff_day:
                    print(f"\n  📅 第 {day} 天 - 共 {result['fixtures_processed']} 场比赛")
                    await self.display_playoff_details(season.id, day)
                    # 显示升降级事件
                    if result.get('cup_progression'):
                        for event, desc in result['cup_progression'].items():
                            if 'promotion' in event.lower() or 'relegation' in event.lower():
                                print(f"  🎯 {event}: {desc}")
                # 杯赛日：简化显示（只显示数量）
                elif is_cup_day:
                    fixture_types = {}
                    for r in result['results']:
                        t = r['type']
                        fixture_types[t] = fixture_types.get(t, 0) + 1
                    type_str = ', '.join([f"{k}:{v}" for k, v in fixture_types.items()])
                    print(f"  📅 第 {day:2d} 天 - {result['fixtures_processed']:3d} 场 ({type_str})")
                    
                    # 只在杯赛晋级日显示事件
                    if result.get('cup_progression'):
                        events = [k for k in result['cup_progression'].keys() if 'winner' in k.lower()]
                        if events:
                            print(f"  🎯 {', '.join(events)}")
                # 普通联赛日：最简化
                else:
                    print(f"  📅 第 {day:2d} 天 - {result['fixtures_processed']:3d} 场 (联赛)")
                
                day_report['fixtures'] = result['results']
            else:
                # 无比赛日
                print(f"  📅 第 {day:2d} 天 - 无比赛")
            
            day_report['success'] = True
            return day_report
            
        except Exception as e:
            import traceback
            error_msg = f"第 {day} 天处理失败: {str(e)}"
            print(f"  ❌ {error_msg}")
            print(f"  📋 堆栈跟踪:")
            traceback.print_exc()
            day_report['success'] = False
            day_report['error'] = error_msg
            self.current_report['errors'].append(error_msg)
            return day_report
    
    async def generate_season_report(self, season: Season):
        """生成赛季报告"""
        self.print_section("赛季总结")
        
        # 显示最终积分榜（简要）
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
        
        # 杯赛冠军
        print("\n  🏆 杯赛冠军:")
        result = await self.db.execute(
            select(CupCompetition).where(CupCompetition.season_id == season.id)
        )
        competitions = result.scalars().all()
        
        for comp in competitions:
            if comp.winner_team_id:
                winner = await self.db.get(Team, comp.winner_team_id)
                print(f"  {comp.name}: {winner.name if winner else '未知'}")
        
        # 统计
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
    
    async def generate_final_report(self):
        """生成最终测试报告"""
        self.print_header("测试完成 - 最终报告")
        
        for report in self.all_reports:
            print(f"\n  第{report['season_number']}赛季:")
            print(f"    比赛日: {len(report['daily_reports'])} 天")
            print(f"    错误数: {len(report.get('errors', []))}")
            if report.get('errors'):
                for err in report['errors']:
                    print(f"      - {err}")
        
        print(f"\n  ✅ 所有赛季测试完成！")


async def main():
    """主函数"""
    print("=" * 80)
    print("Lightning Super League - 双赛季系统测试")
    print("=" * 80)
    
    async with async_session_maker() as db:
        tester = SeasonTester(db)
        
        # 1. 初始化数据库
        await tester.init_database()
        
        # 2. 运行第1赛季（包含Day 24升降级处理）
        season1 = await tester.run_season(1)
        
        # 3. 运行第2赛季（球队位置已在Day 24更新）
        season2 = await tester.run_season(2)
        
        # 5. 生成最终报告
        await tester.generate_final_report()


if __name__ == "__main__":
    asyncio.run(main())
