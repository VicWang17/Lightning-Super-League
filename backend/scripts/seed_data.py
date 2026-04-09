"""
数据填充脚本 - 初始化联赛体系、AI用户和球队

使用方法:
    cd backend && python scripts/seed_data.py

环境变量:
    ENV=dev - 开发模式，允许使用默认密码123456登录AI用户
"""
import asyncio
import os
import sys
import random
from datetime import datetime, date, timedelta
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from passlib.context import CryptContext

from app.config import get_settings
from app.models import (
    Base, User, UserStatus,
    Team, TeamStatus, TeamFinance,
    LeagueSystem, League, Season, SeasonStatus,
    LeagueStanding, Match, MatchStatus,
    Player, PlayerPosition, PlayerFoot, PlayerStatus, SquadRole
)
from data.teams_and_users import LEAGUE_SYSTEMS

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# AI用户默认密码（开发环境使用）
AI_USER_PASSWORD = "123456"

# 开发模式标志
IS_DEV_MODE = os.getenv("ENV", "").lower() == "dev"


def hash_password(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)


def generate_team_short_name(team_name: str) -> str:
    """生成球队简称（取前3个字）"""
    return team_name[:3] if len(team_name) >= 3 else team_name


def generate_user_email(system_code: str, league_level: int, index: int) -> str:
    """生成AI用户邮箱"""
    return f"ai_{system_code.lower()}_l{league_level}_{index:03d}@lightning.dev"


def generate_user_username(team_name: str) -> str:
    """生成AI用户名（用球队名相关）"""
    # 取球队名拼音或简称
    return f"manager_{team_name[:4]}"


async def seed_league_systems(db: AsyncSession) -> dict:
    """填充联赛体系数据"""
    print("🗂️  创建联赛体系...")
    
    systems = {}
    for code, data in LEAGUE_SYSTEMS.items():
        system = LeagueSystem(
            name=data["name"],
            code=code,
            description=data["description"],
            max_teams_per_league=16
        )
        db.add(system)
        await db.flush()  # 获取ID
        systems[code] = system
        print(f"   ✅ {data['name']} ({code}) - ID: {system.id}")
    
    await db.commit()
    print(f"✅ 联赛体系创建完成: {len(systems)} 个\n")
    return systems


async def seed_leagues(db: AsyncSession, systems: dict) -> dict:
    """填充联赛数据"""
    print("🏆 创建联赛...")
    
    leagues = {}
    for system_code, system_data in LEAGUE_SYSTEMS.items():
        system = systems[system_code]
        
        for league_data in system_data["leagues"]:
            level = league_data["level"]
            
            # 根据级别设置升降级规则
            if level == 1:  # 超级联赛
                promotion_spots = 0
                relegation_spots = 4
                has_promotion_playoff = False
                has_relegation_playoff = False
            elif level == 2:  # 甲级联赛
                promotion_spots = 4
                relegation_spots = 4
                has_promotion_playoff = False
                has_relegation_playoff = True  # 第13-14名与乙级亚军附加赛
            else:  # 乙级联赛A/B
                promotion_spots = 3 if level == 3 else 1  # 3A冠军+3B冠军+各1个亚军附加赛
                relegation_spots = 0
                has_promotion_playoff = True
                has_relegation_playoff = False
            
            league = League(
                name=league_data["name"],
                level=level,
                system_id=system.id,
                max_teams=16,
                promotion_spots=promotion_spots,
                relegation_spots=relegation_spots,
                has_promotion_playoff=has_promotion_playoff,
                has_relegation_playoff=has_relegation_playoff
            )
            db.add(league)
            await db.flush()
            
            leagues[f"{system_code}_L{level}"] = league
            print(f"   ✅ {league_data['name']} - Level {level}")
    
    await db.commit()
    print(f"✅ 联赛创建完成: {len(leagues)} 个\n")
    return leagues


async def seed_season(db: AsyncSession) -> Season:
    """创建当前赛季 S1
    
    赛季规则：
    - 命名：S1, S2, S3...
    - 时长：42天
    - 时间：精确到0点 (UTC)
    """
    print("📅 创建赛季...")
    
    # 从明天开始作为S1第一天，0点整
    tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    season = Season(
        name="S1",
        start_date=tomorrow.date(),
        end_date=(tomorrow + timedelta(days=41)).date(),  # 42天 = 41天后结束
        status=SeasonStatus.UPCOMING,
        transfer_window_open=True,
        transfer_window_start=tomorrow,
        transfer_window_end=tomorrow + timedelta(days=6)  # 第一周转会窗口
    )
    db.add(season)
    await db.commit()
    
    print(f"   ✅ {season.name} - ID: {season.id}")
    print(f"   📊 赛季时间: {season.start_date} 00:00 ~ {season.end_date} 00:00")
    print(f"   ⏱️  赛季时长: 42天")
    print(f"   💰 转会窗口: {season.transfer_window_start} ~ {season.transfer_window_end}\n")
    
    return season


async def seed_ai_users_and_teams(db: AsyncSession, leagues: dict, season: Season) -> tuple:
    """填充AI用户和球队数据"""
    print("👤 创建AI用户和球队...")
    
    hashed_password = hash_password(AI_USER_PASSWORD)
    users = []
    teams = []
    finances = []
    
    team_index = 0
    
    for system_code, system_data in LEAGUE_SYSTEMS.items():
        for league_data in system_data["leagues"]:
            level = league_data["level"]
            league_key = f"{system_code}_L{level}"
            league = leagues[league_key]
            
            for idx, (team_name, user_display_name) in enumerate(league_data["teams"], 1):
                team_index += 1
                
                # 创建AI用户
                user = User(
                    username=generate_user_username(team_name),
                    email=generate_user_email(system_code, level, idx),
                    hashed_password=hashed_password,
                    nickname=user_display_name,
                    is_ai=True,
                    is_vip=False,
                    level=1,
                    experience=0,
                    status=UserStatus.ACTIVE,
                    is_verified=True
                )
                db.add(user)
                await db.flush()
                users.append(user)
                
                # 创建球队
                team = Team(
                    name=team_name,
                    short_name=generate_team_short_name(team_name),
                    user_id=user.id,
                    current_league_id=league.id,
                    current_season_id=season.id,
                    reputation=1000 + (4 - level) * 200 + (16 - idx) * 10,  # 高级别球队声望更高
                    overall_rating=50 + (4 - level) * 5 + (16 - idx) // 3,  # 50-75之间
                    status=TeamStatus.ACTIVE
                )
                db.add(team)
                await db.flush()
                teams.append(team)
                
                # 创建球队财务
                initial_balance = Decimal("10000000.00") + Decimal((4 - level) * 5000000)
                finance = TeamFinance(
                    team_id=team.id,
                    balance=initial_balance,
                    weekly_wage_bill=Decimal("50000.00"),
                    stadium_capacity=5000 + (4 - level) * 5000,
                    ticket_price=Decimal("20.00") + Decimal((4 - level) * 5),
                    weekly_sponsor_income=Decimal("10000.00"),
                    weekly_ticket_income=Decimal("0.00"),
                    transfer_budget=initial_balance * Decimal("0.5"),
                    wage_budget=Decimal("500000.00")
                )
                db.add(finance)
                finances.append(finance)
                
                if team_index % 32 == 0:
                    print(f"   🔄 已创建 {team_index}/256 ...")
    
    await db.commit()
    
    print(f"✅ AI用户创建完成: {len(users)} 个")
    print(f"✅ 球队创建完成: {len(teams)} 个")
    print(f"✅ 财务记录创建完成: {len(finances)} 个\n")
    
    if IS_DEV_MODE:
        print(f"⚠️  开发模式已启用 (ENV=dev)")
        print(f"   AI用户密码: {AI_USER_PASSWORD}")
        print(f"   示例登录账号:")
        print(f"      邮箱: {users[0].email}")
        print(f"      密码: {AI_USER_PASSWORD}\n")
    
    return users, teams


async def seed_sample_players(db: AsyncSession, teams: list) -> list:
    """为每支球队创建示例球员（18人 squad）"""
    print("⚽ 创建示例球员...")
    
    players = []
    
    # 位置配置：1 GK, 4 DF, 4 MF, 3 FW, 6 替补
    position_configs = [
        # 主力阵容
        (PlayerPosition.GK, 1),
        (PlayerPosition.CB, 2), (PlayerPosition.LB, 1), (PlayerPosition.RB, 1),
        (PlayerPosition.CM, 2), (PlayerPosition.CAM, 1), (PlayerPosition.LM, 1),
        (PlayerPosition.ST, 2), (PlayerPosition.RW, 1),
        # 替补
        (PlayerPosition.GK, 1), (PlayerPosition.CB, 1), (PlayerPosition.CM, 1),
        (PlayerPosition.CAM, 1), (PlayerPosition.ST, 1), (PlayerPosition.LW, 1),
    ]
    
    first_names = ["李", "王", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴", "徐", "孙", "马", "朱", "胡", "郭"]
    last_names = ["伟", "芳", "娜", "敏", "静", "强", "磊", "军", "洋", "勇", "艳", "杰", "涛", "明", "超", "秀英"]
    
    player_idx = 0
    
    for team in teams:
        player_num = 1
        for pos, count in position_configs:
            for _ in range(count):
                player_idx += 1
                
                # 根据球队级别和声望生成能力值
                base_rating = team.overall_rating + (player_num <= 11 and 5 or -5)
                overall = max(40, min(85, base_rating + (player_num % 3 - 1) * 5))
                potential = min(99, overall + 10)
                
                first_name = first_names[player_idx % len(first_names)]
                last_name = last_names[player_idx % len(last_names)]
                
                # 生成随机比赛统计数据
                matches_played = random.randint(8, 12)
                goals = random.randint(0, 8) if pos in [PlayerPosition.ST, PlayerPosition.LW, PlayerPosition.RW] else random.randint(0, 2)
                assists = random.randint(0, 5) if pos in [PlayerPosition.CM, PlayerPosition.CAM, PlayerPosition.LW, PlayerPosition.RW] else random.randint(0, 2)
                
                player = Player(
                    first_name=first_name,
                    last_name=last_name,
                    display_name=f"{first_name}{last_name}",
                    nationality="中国",
                    birth_date=date(1995 + (player_idx % 10), 1 + (player_idx % 12), 1 + (player_idx % 28)),
                    height=170 + (player_idx % 25),
                    weight=65 + (player_idx % 20),
                    preferred_foot=PlayerFoot.RIGHT if player_idx % 3 != 0 else PlayerFoot.LEFT,
                    primary_position=pos,
                    secondary_position=None,
                    # 能力值
                    shooting=overall + (pos in [PlayerPosition.ST, PlayerPosition.LW, PlayerPosition.RW] and 10 or 0),
                    finishing=overall,
                    long_shots=overall - 5,
                    passing=overall + (pos in [PlayerPosition.CM, PlayerPosition.CAM] and 10 or 0),
                    vision=overall,
                    crossing=overall,
                    dribbling=overall + (pos in [PlayerPosition.LW, PlayerPosition.RW] and 10 or 0),
                    ball_control=overall,
                    defending=overall + (pos in [PlayerPosition.CB, PlayerPosition.LB, PlayerPosition.RB] and 15 or -10),
                    tackling=overall,
                    marking=overall,
                    pace=overall + (pos in [PlayerPosition.LW, PlayerPosition.RW, PlayerPosition.ST] and 10 or 0),
                    acceleration=overall,
                    strength=overall + (pos == PlayerPosition.CB and 10 or 0),
                    stamina=overall,
                    diving=overall if pos == PlayerPosition.GK else 30,
                    handling=overall if pos == PlayerPosition.GK else 30,
                    kicking=overall if pos == PlayerPosition.GK else 30,
                    reflexes=overall if pos == PlayerPosition.GK else 30,
                    positioning=overall if pos == PlayerPosition.GK else 30,
                    aggression=overall - 10,
                    composure=overall,
                    work_rate=overall,
                    overall_rating=overall,
                    potential=potential,
                    status=PlayerStatus.ACTIVE,
                    fitness=100,
                    morale=50 + (player_idx % 30),
                    form=50 + (player_idx % 20),
                    wage=Decimal("5000.00") + Decimal(overall * 100),
                    contract_end=date(2025, 6, 30),
                    release_clause=Decimal("1000000.00") + Decimal(overall * 50000),
                    squad_role=SquadRole.FIRST_TEAM if player_num <= 11 else SquadRole.ROTATION,
                    market_value=Decimal("500000.00") + Decimal(overall * 100000),
                    matches_played=matches_played,
                    goals=goals,
                    assists=assists,
                    yellow_cards=random.randint(0, 3),
                    red_cards=random.randint(0, 1),
                    average_rating=Decimal(str(6.0 + (overall - 50) / 20 + random.uniform(-0.5, 0.5))).quantize(Decimal("0.1")),
                    minutes_played=matches_played * 85,
                    team_id=team.id
                )
                db.add(player)
                players.append(player)
                player_num += 1
        
        if len(players) % (18 * 32) == 0:
            print(f"   🔄 已创建 {len(players)//18}/256 支球队球员...")
    
    await db.commit()
    print(f"✅ 球员创建完成: {len(players)} 人 (每队18人)\n")
    
    return players


async def seed_standings_and_matches(db: AsyncSession, leagues: dict, season: Season, teams: list):
    """创建积分榜和比赛数据"""
    print("📊 创建积分榜和比赛数据...")
    
    standings = []
    matches = []
    
    # 按联赛分组球队
    league_teams = {}
    for team in teams:
        if team.current_league_id not in league_teams:
            league_teams[team.current_league_id] = []
        league_teams[team.current_league_id].append(team)
    
    # 为每个联赛创建积分榜和比赛
    for league_id, league_team_list in league_teams.items():
        # 随机排序球队以生成不同的排名
        random.shuffle(league_team_list)
        
        # 创建积分榜
        for position, team in enumerate(league_team_list, 1):
            played = random.randint(10, 12)
            won = random.randint(5, 9)
            drawn = random.randint(1, 3)
            lost = played - won - drawn
            goals_for = won * random.randint(2, 4) + drawn * random.randint(1, 2)
            goals_against = lost * random.randint(1, 3)
            
            # 生成近期状态 (WWDLW)
            form_results = []
            for _ in range(5):
                r = random.random()
                if r < 0.5:
                    form_results.append('W')
                elif r < 0.75:
                    form_results.append('D')
                else:
                    form_results.append('L')
            form = ''.join(form_results)
            
            standing = LeagueStanding(
                league_id=league_id,
                season_id=season.id,
                team_id=team.id,
                position=position,
                played=played,
                won=won,
                drawn=drawn,
                lost=lost,
                goals_for=goals_for,
                goals_against=goals_against,
                goal_difference=goals_for - goals_against,
                points=won * 3 + drawn,
                form=form,
                is_promotion_zone=(position <= 4),
                is_relegation_zone=(position > 12)
            )
            db.add(standing)
            standings.append(standing)
        
        # 创建赛程（简化版：只创建部分已完成的比赛和部分未进行的比赛）
        team_ids = [t.id for t in league_team_list]
        base_time = datetime.utcnow() - timedelta(days=14)
        
        # 为每支球队创建一些已完成的比赛
        for i in range(0, min(len(team_ids), 16), 2):
            if i + 1 < len(team_ids):
                home_team_id = team_ids[i]
                away_team_id = team_ids[i + 1]
                
                # 已完成的比赛
                for matchday in range(1, 6):
                    home_score = random.randint(0, 4)
                    away_score = random.randint(0, 3)
                    
                    match = Match(
                        season_id=season.id,
                        league_id=league_id,
                        matchday=matchday,
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        home_score=home_score,
                        away_score=away_score,
                        status=MatchStatus.FINISHED,
                        scheduled_at=base_time + timedelta(days=matchday * 2),
                        started_at=base_time + timedelta(days=matchday * 2),
                        finished_at=base_time + timedelta(days=matchday * 2, hours=2),
                        home_possession=random.randint(45, 60),
                        away_possession=random.randint(40, 55),
                        home_shots=random.randint(8, 20),
                        away_shots=random.randint(6, 15),
                        home_shots_on_target=random.randint(3, 10),
                        away_shots_on_target=random.randint(2, 8),
                    )
                    db.add(match)
                    matches.append(match)
                
                # 未进行的比赛
                for matchday in range(6, 11):
                    match = Match(
                        season_id=season.id,
                        league_id=league_id,
                        matchday=matchday,
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        home_score=None,
                        away_score=None,
                        status=MatchStatus.SCHEDULED,
                        scheduled_at=base_time + timedelta(days=matchday * 2 + 14),
                    )
                    db.add(match)
                    matches.append(match)
    
    await db.commit()
    print(f"✅ 积分榜记录创建完成: {len(standings)} 条")
    print(f"✅ 比赛记录创建完成: {len(matches)} 场\n")
    
    return standings, matches


async def clear_existing_data(db: AsyncSession):
    """清空现有数据（用于重新填充）"""
    print("🧹 清空现有数据...")
    
    # 按依赖关系顺序删除
    tables = [
        Player, LeagueStanding, Match,
        TeamFinance, Team, User,
        League, LeagueSystem, Season
    ]
    
    for table in tables:
        await db.execute(delete(table))
    
    await db.commit()
    print("✅ 数据清空完成\n")


async def main():
    """主函数"""
    print("=" * 60)
    print("🚀 闪电超级联赛 - 数据填充脚本")
    print("=" * 60)
    print()
    
    if IS_DEV_MODE:
        print("⚠️  开发模式: ENV=dev")
        print(f"   AI用户默认密码: {AI_USER_PASSWORD}")
        print()
    
    # 获取数据库配置
    settings = get_settings()
    
    # 创建引擎和会话
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        try:
            # 清空现有数据
            await clear_existing_data(db)
            
            # 填充数据
            systems = await seed_league_systems(db)
            leagues = await seed_leagues(db, systems)
            season = await seed_season(db)
            users, teams = await seed_ai_users_and_teams(db, leagues, season)
            players = await seed_sample_players(db, teams)
            standings, matches = await seed_standings_and_matches(db, leagues, season, teams)
            
            print("=" * 60)
            print("✅ 数据填充完成!")
            print("=" * 60)
            print()
            print("📊 数据汇总:")
            print(f"   • 联赛体系: 4 个")
            print(f"   • 联赛: 16 个")
            print(f"   • AI用户: {len(users)} 个")
            print(f"   • 球队: {len(teams)} 个")
            print(f"   • 球员: {len(players)} 人")
            print(f"   • 积分榜: {len(standings)} 条")
            print(f"   • 比赛: {len(matches)} 场")
            print(f"   • 赛季: 1 个")
            print()
            
            # 打印第一个联赛的ID供参考
            first_league = list(leagues.values())[0]
            print(f"💡 提示: 第一个联赛ID是 {first_league.id}")
            print(f"   可以在浏览器中访问: http://localhost:5173/leagues/{first_league.id}")
            print()
            
            if IS_DEV_MODE:
                print("🔑 开发环境登录信息:")
                print(f"   邮箱: {users[0].email}")
                print(f"   密码: {AI_USER_PASSWORD}")
                print()
                print("💡 提示: 所有AI用户密码都是 '123456'")
                print()
            
        except Exception as e:
            print(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
