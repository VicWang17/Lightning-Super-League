"""
系统初始化脚本 - Initialize System

功能：
1. 删除所有现有数据库表和数据
2. 重新创建所有表
3. 初始化联赛体系、球队、AI用户、球员
4. 【注意】不创建赛季，赛季创建请使用 init_season.py

用法:
    cd backend
    python -m scripts.init_system

环境变量:
    ENV=dev - 开发模式，AI用户密码为 ai_password
"""
import asyncio
import os
import sys
from datetime import datetime, date
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext

from app.config import get_settings
from app.models import (
    Base, User, UserStatus,
    Team, TeamStatus, TeamFinance,
    LeagueSystem, League, 
    Player, PlayerPosition, PlayerFoot, PlayerStatus, SquadRole
)
from data.teams_and_users import LEAGUE_SYSTEMS

# 密码加密
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
AI_USER_PASSWORD = "ai_password"
IS_DEV_MODE = os.getenv("ENV", "").lower() == "dev"

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def hash_password(password: str) -> str:
    """加密密码"""
    return pwd_context.hash(password)


def generate_user_email(system_code: str, league_level: int, league_index: int, index: int) -> str:
    """生成AI用户邮箱
    
    Args:
        system_code: 体系代码 (EAST/WEST/SOUTH/NORTH)
        league_level: 联赛级别 (1/2/3/4)
        league_index: 同级别联赛的索引 (1/2/...)
        index: 球队在联赛中的索引 (1-8)
    """
    return f"ai_{system_code.lower()}_l{league_level}_{league_index}_{index:03d}@lightning.dev"


def generate_user_username(team_name: str) -> str:
    """生成AI用户名"""
    return f"manager_{team_name[:4]}"


async def drop_all_tables():
    """删除所有表"""
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = DATABASE()
        """))
        tables = [row[0] for row in result.fetchall()]
        
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables:
            await conn.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        await conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    
    print(f"✅ 已删除 {len(tables)} 个表")


async def create_tables():
    """创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 所有表创建完成")


async def init_league_systems(db: AsyncSession) -> dict:
    """初始化联赛体系"""
    print("\n🏟️ 初始化联赛体系...")
    
    systems = {}
    for code, data in LEAGUE_SYSTEMS.items():
        system = LeagueSystem(
            name=data["name"],
            code=code,
            description=data["description"],
            max_teams_per_league=8
        )
        db.add(system)
        await db.flush()
        systems[code] = system
        print(f"   ✅ {data['name']} ({code})")
    
    await db.commit()
    return systems


async def init_leagues(db: AsyncSession, systems: dict) -> dict:
    """初始化联赛"""
    print("\n📋 初始化联赛...")
    
    leagues = {}
    
    for system_code, system_data in LEAGUE_SYSTEMS.items():
        system = systems[system_code]
        
        # 按级别分组计数器
        level_counters = {1: 0, 2: 0, 3: 0, 4: 0}
        
        for league_data in system_data["leagues"]:
            level = league_data["level"]
            level_counters[level] += 1
            
            # 根据级别设置升降级规则（新赛制：8队联赛）
            # 规则：冠军直升，最后1名直降，附加赛决定第2个名额
            if level == 1:
                # 顶级联赛：无升级，最后1名降级，第7名参加附加赛
                promotion_spots = 0
                relegation_spots = 1
                has_promotion_playoff = False
                has_relegation_playoff = True
            elif level == 2:
                # 次级联赛：冠军直升，最后2名降级，第2名参加附加赛
                promotion_spots = 1
                relegation_spots = 2
                has_promotion_playoff = True
                has_relegation_playoff = False
            elif level == 3:
                # 三级联赛：冠军直升，无直降，亚军参加附加赛
                promotion_spots = 1
                relegation_spots = 0
                has_promotion_playoff = True
                has_relegation_playoff = False
            else:  # level == 4
                # 四级联赛：冠军直升，无直降，亚军参加附加赛
                promotion_spots = 1
                relegation_spots = 0
                has_promotion_playoff = True
                has_relegation_playoff = False
            
            league = League(
                name=league_data["name"],
                level=level,
                system_id=system.id,
                max_teams=8,
                promotion_spots=promotion_spots,
                relegation_spots=relegation_spots,
                has_promotion_playoff=has_promotion_playoff,
                has_relegation_playoff=has_relegation_playoff
            )
            db.add(league)
            await db.flush()
            
            # 使用带索引的key，如 EAST_L1_1, EAST_L3_1, EAST_L3_2
            league_key = f"{system_code}_L{level}_{level_counters[level]}"
            leagues[league_key] = league
            print(f"   ✅ {league_data['name']} (Level {level})")
    
    await db.commit()
    return leagues


async def init_teams_and_users(db: AsyncSession, leagues: dict) -> tuple:
    """初始化球队和AI用户"""
    print("\n👤 初始化AI用户和球队...")
    
    hashed_password = hash_password(AI_USER_PASSWORD)
    users = []
    teams = []
    
    team_index = 0
    
    # 按体系分组计数器
    system_level_counters = {}
    for system_code in LEAGUE_SYSTEMS.keys():
        system_level_counters[system_code] = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for system_code, system_data in LEAGUE_SYSTEMS.items():
        for league_data in system_data["leagues"]:
            level = league_data["level"]
            system_level_counters[system_code][level] += 1
            league_key = f"{system_code}_L{level}_{system_level_counters[system_code][level]}"
            league = leagues[league_key]
            
            for idx, (team_name, user_display_name) in enumerate(league_data["teams"], 1):
                team_index += 1
                
                # 创建AI用户
                user = User(
                    username=generate_user_username(team_name),
                    email=generate_user_email(system_code, level, system_level_counters[system_code][level], idx),
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
                    short_name=team_name[:4],
                    user_id=user.id,
                    current_league_id=league.id,
                    reputation=1000 + (4 - level) * 200 + (16 - idx) * 10,
                    overall_rating=50 + (4 - level) * 5 + (16 - idx) // 3,
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
                
                if team_index % 64 == 0:
                    print(f"   🔄 已创建 {team_index}/256 ...")
    
    await db.commit()
    print(f"✅ 已创建 {len(users)} 个AI用户和 {len(teams)} 支球队")
    return users, teams


async def init_players(db: AsyncSession, teams: list) -> list:
    """为每支球队创建球员（18人 squad）"""
    print("\n⚽ 初始化球员...")
    
    players = []
    
    position_configs = [
        (PlayerPosition.GK, 1),
        (PlayerPosition.CB, 2), (PlayerPosition.LB, 1), (PlayerPosition.RB, 1),
        (PlayerPosition.CM, 2), (PlayerPosition.CAM, 1), (PlayerPosition.LM, 1),
        (PlayerPosition.ST, 2), (PlayerPosition.RW, 1),
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
                
                base_rating = team.overall_rating + (player_num <= 11 and 5 or -5)
                overall = max(40, min(85, base_rating + (player_num % 3 - 1) * 5))
                potential = min(99, overall + 10)
                
                first_name = first_names[player_idx % len(first_names)]
                last_name = last_names[player_idx % len(last_names)]
                
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
                    team_id=team.id
                )
                db.add(player)
                players.append(player)
                player_num += 1
        
        if len(players) % (18 * 32) == 0:
            print(f"   🔄 已创建 {len(players)//18}/256 支球队球员...")
    
    await db.commit()
    print(f"✅ 已创建 {len(players)} 名球员")
    return players


async def show_summary(db: AsyncSession):
    """显示初始化摘要"""
    print("\n" + "=" * 60)
    print("📊 系统基础数据初始化完成")
    print("=" * 60)
    
    from sqlalchemy import select
    
    result = await db.execute(select(LeagueSystem))
    systems_count = len(result.scalars().all())
    
    result = await db.execute(select(League))
    leagues_count = len(result.scalars().all())
    
    result = await db.execute(select(User))
    users_count = len(result.scalars().all())
    
    result = await db.execute(select(Team))
    teams_count = len(result.scalars().all())
    
    result = await db.execute(select(Player))
    players_count = len(result.scalars().all())
    
    print(f"\n🏟️ 联赛体系: {systems_count} 个（东区/西区/南区/北区）")
    print(f"📋 联赛: {leagues_count} 个（每体系8个联赛）")
    print(f"👤 AI用户: {users_count} 个")
    print(f"⚽ 球队: {teams_count} 支（每联赛8队）")
    print(f"🏃 球员: {players_count} 人（每队18人）")
    
    print(f"\n📌 联赛结构:")
    print(f"   - 顶级联赛（超级联赛）: 4个联赛 × 8队")
    print(f"   - 次级联赛（甲级联赛）: 4个联赛 × 8队")
    print(f"   - 三级联赛（乙级联赛A/B）: 8个联赛 × 8队")
    print(f"   - 四级联赛（丙级联赛A/B/C/D）: 16个联赛 × 8队")
    
    print(f"\n⚠️  注意: 尚未创建赛季")
    print(f"   请运行: python -m scripts.init_season")
    
    if IS_DEV_MODE:
        print(f"\n🔑 开发模式登录信息:")
        print(f"   邮箱: ai_east_l1_001@lightning.dev")
        print(f"   密码: {AI_USER_PASSWORD}")
    
    print("\n" + "=" * 60)


async def main():
    """主函数"""
    print("=" * 60)
    print("⚡ 闪电超级联赛 - 系统基础数据初始化")
    print("=" * 60)
    
    if IS_DEV_MODE:
        print(f"\n⚠️  开发模式: ENV=dev")
        print(f"   AI用户默认密码: {AI_USER_PASSWORD}")
    
    print("\n⚠️  警告: 这将删除所有现有数据！")
    print("   3秒后开始初始化...")
    await asyncio.sleep(3)
    
    async with AsyncSessionLocal() as db:
        try:
            await drop_all_tables()
            await create_tables()
            systems = await init_league_systems(db)
            leagues = await init_leagues(db, systems)
            users, teams = await init_teams_and_users(db, leagues)
            players = await init_players(db, teams)
            await show_summary(db)
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise
    
    await engine.dispose()
    print("\n✅ 基础数据初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
