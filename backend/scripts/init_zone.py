"""
新区初始化脚本 - Initialize New Zone

功能：
1. 在现有数据库基础上新增一个完整大区（Zone）
2. 创建4个联赛体系、32个联赛、256支球队、AI用户、球员
3. 不删除现有数据，只做增量创建

用法:
    cd backend
    python -m scripts.init_zone --zone 2

注意:
    - 运行前需确保数据库已存在且包含1区数据（或至少表结构已创建）
    - 如需删除某区数据，请参考 ZONE-EXPANSION-OPS.md 中的回滚SQL
"""
import asyncio
import sys
import os
import argparse
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from passlib.context import CryptContext

from app.config import get_settings
from app.models import (
    Base, User, UserStatus,
    Team, TeamStatus, TeamFinance,
    LeagueSystem, League,
    Player, PlayerPosition, PlayerFoot, PlayerStatus, SquadRole
)
from app.core.formats import get_default_format
from data.teams_and_users import LEAGUE_SYSTEMS

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
AI_USER_PASSWORD = "ai_password"
IS_DEV_MODE = os.getenv("ENV", "").lower() == "dev"

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def generate_user_email(system_code: str, zone_id: int, league_level: int, league_index: int, index: int) -> str:
    return f"ai_z{zone_id}_{system_code.lower()}_l{league_level}_{league_index}_{index:03d}@lightning.dev"


def generate_user_username(team_name: str, zone_id: int) -> str:
    return f"manager_{team_name[:4]}_z{zone_id}"


async def init_zone_league_systems(db: AsyncSession, zone_id: int) -> dict:
    """初始化指定大区的联赛体系"""
    print(f"\n🏟️ 初始化第{zone_id}区联赛体系...")
    
    fmt = get_default_format()
    systems = {}
    
    for code, data in LEAGUE_SYSTEMS.items():
        zone_code = f"{code}_Z{zone_id}"
        zone_name = f"{data['name']}{zone_id}区"
        
        # 检查是否已存在
        result = await db.execute(
            select(LeagueSystem).where(LeagueSystem.code == zone_code)
        )
        if result.scalar_one_or_none():
            print(f"   ⚠️ {zone_name} ({zone_code}) 已存在，跳过")
            continue
        
        system = LeagueSystem(
            name=zone_name,
            code=zone_code,
            description=data.get("description"),
            zone_id=zone_id,
            max_teams_per_league=fmt.league.teams_per_league
        )
        db.add(system)
        await db.flush()
        systems[code] = system
        print(f"   ✅ {zone_name} ({zone_code})")
    
    await db.commit()
    return systems


async def init_zone_leagues(db: AsyncSession, zone_id: int, systems: dict) -> dict:
    """初始化指定大区的联赛"""
    print(f"\n📋 初始化第{zone_id}区联赛...")
    
    fmt = get_default_format()
    leagues = {}
    
    for system_code, system_data in LEAGUE_SYSTEMS.items():
        system = systems.get(system_code)
        if not system:
            continue
        
        level_counters = {1: 0, 2: 0, 3: 0, 4: 0}
        
        for league_data in system_data["leagues"]:
            level = league_data["level"]
            level_counters[level] += 1
            
            level_config = fmt.promotion.level_rules.get(level, fmt.promotion.level_rules.get(4))
            
            league = League(
                name=league_data["name"],
                level=level,
                system_id=system.id,
                max_teams=fmt.league.teams_per_league,
                promotion_spots=level_config.promotion_spots,
                relegation_spots=level_config.relegation_spots,
                has_promotion_playoff=level_config.has_promotion_playoff,
                has_relegation_playoff=level_config.has_relegation_playoff
            )
            db.add(league)
            await db.flush()
            
            league_key = f"{system_code}_L{level}_{level_counters[level]}"
            leagues[league_key] = league
            print(f"   ✅ {league_data['name']} (Level {level})")
    
    await db.commit()
    return leagues


async def init_zone_teams_and_users(db: AsyncSession, zone_id: int, systems: dict, leagues: dict) -> tuple:
    """初始化指定大区的球队和AI用户"""
    print(f"\n👤 初始化第{zone_id}区AI用户和球队...")
    
    hashed_password = hash_password(AI_USER_PASSWORD)
    users = []
    teams = []
    team_index = 0
    
    system_level_counters = {}
    for system_code in LEAGUE_SYSTEMS.keys():
        system_level_counters[system_code] = {1: 0, 2: 0, 3: 0, 4: 0}
    
    for system_code, system_data in LEAGUE_SYSTEMS.items():
        if system_code not in systems:
            continue
        
        for league_data in system_data["leagues"]:
            level = league_data["level"]
            system_level_counters[system_code][level] += 1
            league_key = f"{system_code}_L{level}_{system_level_counters[system_code][level]}"
            league = leagues.get(league_key)
            
            if not league:
                continue
            
            for idx, (team_name, user_display_name) in enumerate(league_data["teams"], 1):
                team_index += 1
                
                user = User(
                    username=generate_user_username(team_name, zone_id),
                    email=generate_user_email(system_code, zone_id, level, system_level_counters[system_code][level], idx),
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
                
                team = Team(
                    name=team_name,
                    short_name=team_name[:4],
                    user_id=user.id,
                    current_league_id=league.id,
                    overall_rating=50 + (4 - level) * 5 + (16 - idx) // 3,
                    status=TeamStatus.ACTIVE
                )
                db.add(team)
                await db.flush()
                teams.append(team)
                
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
    print(f"✅ 第{zone_id}区已创建 {len(users)} 个AI用户和 {len(teams)} 支球队")
    return users, teams


async def init_zone_players(db: AsyncSession, zone_id: int, teams: list) -> list:
    """为指定大区的球队创建球员"""
    print(f"\n⚽ 初始化第{zone_id}区球员...")
    
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
    print(f"✅ 第{zone_id}区已创建 {len(players)} 名球员")
    return players


async def show_zone_summary(db: AsyncSession, zone_id: int):
    """显示指定大区初始化摘要"""
    print("\n" + "=" * 60)
    print(f"📊 第{zone_id}区基础数据初始化完成")
    print("=" * 60)
    
    from sqlalchemy import select
    
    result = await db.execute(
        select(LeagueSystem).where(LeagueSystem.zone_id == zone_id)
    )
    systems_count = len(result.scalars().all())
    
    result = await db.execute(
        select(League).join(LeagueSystem).where(LeagueSystem.zone_id == zone_id)
    )
    leagues_count = len(result.scalars().all())
    
    result = await db.execute(
        select(Team).join(League).join(LeagueSystem).where(LeagueSystem.zone_id == zone_id)
    )
    teams_count = len(result.scalars().all())
    
    result = await db.execute(
        select(Player).join(Team).join(League).join(LeagueSystem).where(LeagueSystem.zone_id == zone_id)
    )
    players_count = len(result.scalars().all())
    
    print(f"\n🏟️ 联赛体系: {systems_count} 个")
    print(f"📋 联赛: {leagues_count} 个")
    print(f"⚽ 球队: {teams_count} 支")
    print(f"🏃 球员: {players_count} 人")
    print("\n" + "=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="闪电超级联赛 - 新区初始化")
    parser.add_argument("--zone", type=int, required=True, help="要初始化的大区ID（如 2, 3, 4...）")
    args = parser.parse_args()
    
    zone_id = args.zone
    
    print("=" * 60)
    print(f"⚡ 闪电超级联赛 - 第{zone_id}区基础数据初始化")
    print("=" * 60)
    
    if zone_id == 1:
        print("\n⚠️  第1区请使用 scripts.init_system 初始化")
        print("   python -m scripts.init_system")
        return
    
    async with AsyncSessionLocal() as db:
        try:
            systems = await init_zone_league_systems(db, zone_id)
            if not systems:
                print("\n❌ 没有新增任何体系，可能该大区已存在")
                return
            
            leagues = await init_zone_leagues(db, zone_id, systems)
            users, teams = await init_zone_teams_and_users(db, zone_id, systems, leagues)
            players = await init_zone_players(db, zone_id, teams)
            await show_zone_summary(db, zone_id)
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise
    
    await engine.dispose()
    print(f"\n✅ 第{zone_id}区基础数据初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())
