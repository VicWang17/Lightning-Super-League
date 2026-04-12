"""
Schedule generation algorithms - 赛程生成算法

包含：
1. 联赛圆形轮转算法（8队双循环，14轮）
2. 闪电杯赛程算法（32队，8组小组赛+淘汰赛）
3. 杰尼杯赛程算法（体系内56队，预选赛+淘汰赛）
4. 赛程合并与日期分配
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.season import Season, CupCompetition, CupGroup, Fixture, FixtureType, FixtureStatus, SeasonStatus
from app.models.league import League
from app.models.team import Team


# ============== 数据类定义 ==============

@dataclass
class MatchPair:
    """对阵组合"""
    home_team_id: str
    away_team_id: str


@dataclass
class RoundSchedule:
    """单轮赛程"""
    round_number: int
    matches: List[MatchPair]


@dataclass
class LeagueSchedule:
    """联赛完整赛程"""
    league_id: str
    rounds: List[RoundSchedule]


@dataclass
class CupGroupSchedule:
    """杯赛小组赛程"""
    group_name: str
    team_ids: List[str]
    rounds: List[RoundSchedule]


@dataclass
class CupSchedule:
    """杯赛完整赛程"""
    competition_id: str
    group_schedules: Optional[List[CupGroupSchedule]]  # 仅闪电杯有
    knockout_rounds: List[RoundSchedule]


# ============== 联赛赛程算法 ==============

class LeagueScheduleGenerator:
    """联赛赛程生成器 - 圆形轮转法"""
    
    @staticmethod
    def generate(teams: List[str], league_id: str) -> LeagueSchedule:
        """
        生成8队双循环赛程（14轮）
        
        算法：圆形轮转法 + 随机打乱轮次
        - 位置0固定，其余7队顺时针轮转
        - 每轮4场比赛（左半区vs右半区镜像）
        - 前7轮主场，后7轮交换主客场
        - 最后将14轮随机打乱，避免球队连续主/客场
        """
        assert len(teams) == 8, "联赛必须有8支球队"
        
        # 随机打乱（创建赛季时执行一次）
        shuffled = teams.copy()
        random.shuffle(shuffled)
        
        rounds = []
        rotating = shuffled[1:]  # 7队参与轮转
        
        for round_num in range(1, 15):
            # 构建本轮位置分布
            positions = [shuffled[0]] + rotating  # 8个位置
            
            matches = []
            is_second_half = round_num > 7  # 第8轮开始交换主客场
            
            for i in range(4):
                home = positions[i]
                away = positions[7 - i]  # 镜像位置
                
                # 第二轮循环交换主客场
                if is_second_half:
                    home, away = away, home
                
                matches.append(MatchPair(home, away))
            
            rounds.append(RoundSchedule(round_num, matches))
            
            # 轮转：最后一个元素移到第一个后面
            rotating = [rotating[-1]] + rotating[:-1]
        
        # 随机打乱14轮的顺序，使主客场分布更均匀
        random.shuffle(rounds)
        
        # 重新分配轮次编号
        for i, round_schedule in enumerate(rounds, 1):
            round_schedule.round_number = i
        
        return LeagueSchedule(league_id, rounds)


# ============== 闪电杯赛程算法 ==============

class LightningCupGenerator:
    """闪电杯赛程生成器"""
    
    GROUP_NAMES = [chr(ord('A') + i) for i in range(8)]  # A-H
    
    @classmethod
    def generate(
        cls,
        competition_id: str,
        top_leagues: List[List[str]]  # 4个顶级联赛，每个8队
    ) -> Tuple[CupSchedule, List[CupGroup]]:
        """
        生成闪电杯赛程（32队）
        
        赛制：
        - 小组赛：32队分8组，每组4队，单循环3轮
        - 淘汰赛：16强->8强->半决赛->决赛，共4轮
        - 总计：3 + 4 = 7轮
        """
        # 收集32队并随机分组
        all_teams = []
        for league in top_leagues:
            all_teams.extend(league)
        
        assert len(all_teams) == 32, "闪电杯必须有32支球队"
        random.shuffle(all_teams)
        
        # 分8组
        group_schedules = []
        cup_groups = []
        
        for i in range(8):
            group_name = cls.GROUP_NAMES[i]
            group_teams = all_teams[i*4:(i+1)*4]
            
            # 小组单循环3轮
            # 4队编号0,1,2,3
            # 第1轮: 0vs1, 2vs3
            # 第2轮: 0vs2, 1vs3
            # 第3轮: 0vs3, 1vs2
            rounds = [
                RoundSchedule(1, [
                    MatchPair(group_teams[0], group_teams[1]),
                    MatchPair(group_teams[2], group_teams[3])
                ]),
                RoundSchedule(2, [
                    MatchPair(group_teams[0], group_teams[2]),
                    MatchPair(group_teams[1], group_teams[3])
                ]),
                RoundSchedule(3, [
                    MatchPair(group_teams[0], group_teams[3]),
                    MatchPair(group_teams[1], group_teams[2])
                ]),
            ]
            
            group_schedules.append(CupGroupSchedule(group_name, group_teams, rounds))
            cup_groups.append(CupGroup(
                competition_id=competition_id,
                name=group_name,
                team_ids=group_teams,
                standings=None,
                qualified_team_ids=None
            ))
        
        # 淘汰赛占位（小组赛结束后填充）
        # 16强: 8场比赛（8组前2名=16队）
        # 8强: 4场
        # 半决赛: 2场
        # 决赛: 1场
        knockout_rounds = [
            RoundSchedule(4, []),  # ROUND_16 - 待填充
            RoundSchedule(5, []),  # QUARTER - 待填充
            RoundSchedule(6, []),  # SEMI - 待填充
            RoundSchedule(7, []),  # FINAL - 待填充
        ]
        
        return CupSchedule(competition_id, group_schedules, knockout_rounds), cup_groups


# ============== 杰尼杯赛程算法 ==============

@dataclass
class JennyCupSchedule(CupSchedule):
    """杰尼杯赛程（体系内杯赛）"""
    system_code: str  # 所属体系代码
    tier2_teams: List[str]  # 次级联赛8支球队（作为种子直接进入32强）


class JennyCupGenerator:
    """杰尼杯赛程生成器（体系内杯赛）"""
    
    @classmethod
    def generate(
        cls,
        competition_id: str,
        system_code: str,
        tier2_league: List[str],      # 次级联赛8队（种子）
        tier3_leagues: List[List[str]],  # 2个三级联赛，各8队
        tier4_leagues: List[List[str]]   # 4个四级联赛，各8队
    ) -> JennyCupSchedule:
        """
        生成杰尼杯赛程（体系内56队）
        
        赛制：
        - 预选赛：48支非种子球队（三级16+四级32）参赛，24场，决出24支球队
        - 32强：24支预选赛胜者 + 8支次级联赛种子 = 32队
        - 淘汰赛：32强->16强->8强->半决赛->决赛，共5轮
        - 总计：1 + 5 = 6轮
        """
        # 收集48支非种子球队
        non_seed_teams = []
        for league in tier3_leagues:
            non_seed_teams.extend(league)
        for league in tier4_leagues:
            non_seed_teams.extend(league)
        
        assert len(non_seed_teams) == 48, f"杰尼杯非种子球队应为48支，实际{len(non_seed_teams)}支"
        assert len(tier2_league) == 8, f"杰尼杯种子球队应为8支，实际{len(tier2_league)}支"
        
        # 预选赛：48队随机配对
        random.shuffle(non_seed_teams)
        round1_matches = []
        for i in range(24):  # 24场比赛
            round1_matches.append(MatchPair(non_seed_teams[i*2], non_seed_teams[i*2+1]))
        
        # 后续淘汰赛占位
        knockout_rounds = [
            RoundSchedule(1, round1_matches),  # 预选赛：48进24
            RoundSchedule(2, []),  # 32强（24胜者+8种子）
            RoundSchedule(3, []),  # 16强
            RoundSchedule(4, []),  # 8强
            RoundSchedule(5, []),  # 半决赛
            RoundSchedule(6, []),  # 决赛
        ]
        
        return JennyCupSchedule(
            competition_id=competition_id,
            group_schedules=None,
            knockout_rounds=knockout_rounds,
            system_code=system_code,
            tier2_teams=tier2_league
        )


# ============== 日期分配与合并 ==============

class ScheduleMerger:
    """赛程合并器 - 将联赛和杯赛赛程合并到统一时间线"""
    
    # 26天赛季配置
    CUP_START_DAY = 4       # 杯赛第1轮在第4天
    CUP_INTERVAL = 2        # 杯赛间隔天数（每2天一轮）
    CUP_ROUNDS = 7          # 闪电杯共7轮
    JENNY_CUP_ROUNDS = 6    # 杰尼杯共6轮
    KICKOFF_HOUR = 20       # 开球时间（20:00）
    
    @classmethod
    def assign_dates(
        cls,
        season_start: datetime,
        league_schedules: List[LeagueSchedule],
        lightning_cup: CupSchedule,
        jenny_cups: List[JennyCupSchedule],  # 4个体系的杰尼杯
        season_id: str,
        cup_competition_ids: Dict[str, str]  # {"LIGHTNING": id, "JENNY_EAST": id, ...}
    ) -> List[Fixture]:
        """
        将所有赛程合并并分配日期
        
        26天时间线：
        - Day 1-20: 联赛14轮（其中穿插杯赛7轮）
        - Day 21: 闪电杯决赛
        - Day 22: 休赛
        - Day 23-24: 升降级附加赛
        - Day 25-26: 休赛期
        """
        fixtures = []
        
        # 1. 联赛赛程（Day 1-20，与杯赛交错）
        # 联赛日：1,2,3,5,7,9,11,13,15,16,17,18,19,20（14轮）
        league_days = [1, 2, 3, 5, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20]
        
        for league_schedule in league_schedules:
            for round_schedule in league_schedule.rounds:
                day_index = round_schedule.round_number - 1
                if day_index < len(league_days):
                    day = league_days[day_index]
                    match_date = season_start + timedelta(days=day - 1)
                    kickoff = match_date.replace(hour=cls.KICKOFF_HOUR, minute=0, second=0)
                    
                    for match in round_schedule.matches:
                        fixtures.append(Fixture(
                            season_id=season_id,
                            fixture_type=FixtureType.LEAGUE,
                            season_day=day,
                            scheduled_at=kickoff,
                            round_number=round_schedule.round_number,
                            league_id=league_schedule.league_id,
                            cup_competition_id=None,
                            cup_group_name=None,
                            cup_stage=None,
                            home_team_id=match.home_team_id,
                            away_team_id=match.away_team_id,
                            status=FixtureStatus.SCHEDULED
                        ))
        
        # 2. 闪电杯赛程
        cup_days = [4, 6, 8, 10, 12, 14, 21]  # 7个杯赛日（第21天决赛）
        
        # 小组赛（3轮）
        if lightning_cup.group_schedules:
            for round_idx in range(3):  # 前3轮是小组赛
                day = cup_days[round_idx]
                match_date = season_start + timedelta(days=day - 1)
                kickoff = match_date.replace(hour=cls.KICKOFF_HOUR, minute=0, second=0)
                
                for group in lightning_cup.group_schedules:
                    round_schedule = group.rounds[round_idx]
                    for match in round_schedule.matches:
                        fixtures.append(Fixture(
                            season_id=season_id,
                            fixture_type=FixtureType.CUP_LIGHTNING_GROUP,
                            season_day=day,
                            scheduled_at=kickoff,
                            round_number=round_idx + 1,
                            league_id=None,
                            cup_competition_id=cup_competition_ids["LIGHTNING"],
                            cup_group_name=group.group_name,
                            cup_stage="GROUP",
                            home_team_id=match.home_team_id,
                            away_team_id=match.away_team_id,
                            status=FixtureStatus.SCHEDULED
                        ))
        
        # 淘汰赛（4轮）- 对阵待填充
        # 第4-7轮是淘汰赛，对阵在小组赛结束后生成
        
        # 3. 杰尼杯赛程（4个体系各自独立）
        for jenny_cup in jenny_cups:
            cup_id = cup_competition_ids.get(f"JENNY_{jenny_cup.system_code}")
            if not cup_id:
                continue
            
            # 杰尼杯6轮：与闪电杯前6轮同一天（第21天是闪电杯决赛，杰尼杯决赛在第14天）
            jenny_cup_days = [4, 6, 8, 10, 12, 14]  # 6轮
            
            # 预选赛（第1轮）
            round_schedule = jenny_cup.knockout_rounds[0]
            day = jenny_cup_days[0]
            match_date = season_start + timedelta(days=day - 1)
            kickoff = match_date.replace(hour=cls.KICKOFF_HOUR, minute=0, second=0)
            
            for match in round_schedule.matches:
                fixtures.append(Fixture(
                    season_id=season_id,
                    fixture_type=FixtureType.CUP_JENNY,
                    season_day=day,
                    scheduled_at=kickoff,
                    round_number=1,
                    league_id=None,
                    cup_competition_id=cup_id,
                    cup_group_name=None,
                    cup_stage="ROUND_48",  # 预选赛48进24
                    home_team_id=match.home_team_id,
                    away_team_id=match.away_team_id,
                    status=FixtureStatus.SCHEDULED
                ))
            
            # 后续轮次待填充
        
        return fixtures


# ============== 赛季调度器服务 ==============

class SeasonScheduler:
    """赛季调度器 - 管理赛季生命周期和比赛执行"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_season(
        self,
        season_number: int,
        start_date: datetime,
        leagues: List[League],
        teams_by_league: Dict[str, List[Team]]
    ) -> Season:
        """创建新赛季并生成完整赛程"""
        
        # 1. 创建赛季
        season = Season(
            season_number=season_number,
            start_date=start_date,
            status=SeasonStatus.PENDING,
            current_day=0,
            current_league_round=0,
            current_cup_round=0,
            total_days=26,
            league_days=20,  # 联赛在20天内完成（与杯赛交错）
            cup_start_day=4,
            cup_interval=2,
            offseason_start=22
        )
        self.db.add(season)
        await self.db.flush()  # 获取season.id
        
        # 2. 创建杯赛定义
        # 闪电杯（全服32队）
        top_leagues = [l for l in leagues if l.level == 1]
        lightning_cup = CupCompetition(
            season_id=season.id,
            name="闪电杯",
            code="LIGHTNING_CUP",
            eligible_league_levels=[1],
            total_teams=32,
            has_group_stage=True,
            group_count=8,
            teams_per_group=4,
            group_rounds=3,
            current_round=0,
            status=SeasonStatus.PENDING,
            winner_team_id=None
        )
        self.db.add(lightning_cup)
        await self.db.flush()
        
        # 杰尼杯（4个体系各自独立，每体系56队）
        jenny_cups = []
        systems = ["EAST", "WEST", "SOUTH", "NORTH"]
        for system_code in systems:
            jenny_cup = CupCompetition(
                season_id=season.id,
                name=f"杰尼杯-{system_code}",
                code=f"JENNY_CUP_{system_code}",
                eligible_league_levels=[2, 3, 4],
                total_teams=56,
                has_group_stage=False,
                group_count=0,
                teams_per_group=0,
                group_rounds=0,
                current_round=0,
                status=SeasonStatus.PENDING,
                winner_team_id=None
            )
            self.db.add(jenny_cup)
            await self.db.flush()
            jenny_cups.append((system_code, jenny_cup))
        
        # 3. 生成联赛赛程
        league_schedules = []
        for league in leagues:
            teams = teams_by_league.get(league.id, [])
            if len(teams) != 8:
                continue
            team_ids = [t.id for t in teams]
            schedule = LeagueScheduleGenerator.generate(team_ids, league.id)
            league_schedules.append(schedule)
        
        # 4. 生成杯赛赛程
        # 闪电杯
        top_league_teams = [
            [t.id for t in teams_by_league.get(l.id, [])]
            for l in top_leagues
        ]
        top_league_teams = [teams for teams in top_league_teams if len(teams) == 8]
        
        lightning_schedule = None
        cup_groups = []
        if len(top_league_teams) >= 4:
            lightning_schedule, cup_groups = LightningCupGenerator.generate(
                lightning_cup.id,
                top_league_teams[:4]
            )
            for group in cup_groups:
                self.db.add(group)
        
        # 杰尼杯（每体系独立）
        jenny_cup_schedules = []
        for system_code, jenny_cup in jenny_cups:
            # 获取该体系的球队
            system_leagues = [l for l in leagues if l.system.code == system_code]
            tier2 = [l for l in system_leagues if l.level == 2]
            tier3 = [l for l in system_leagues if l.level == 3]
            tier4 = [l for l in system_leagues if l.level == 4]
            
            tier2_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier2]
            tier3_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier3]
            tier4_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier4]
            
            # 展平列表
            tier2_flat = [t for sublist in tier2_teams for t in sublist]
            tier3_flat = [t for sublist in tier3_teams for t in sublist]
            tier4_flat = [t for sublist in tier4_teams for t in sublist]
            
            if len(tier2_flat) == 8 and len(tier3_flat) == 16 and len(tier4_flat) == 32:
                jenny_schedule = JennyCupGenerator.generate(
                    jenny_cup.id,
                    system_code,
                    tier2_flat,
                    [tier3_flat[:8], tier3_flat[8:16]],
                    [tier4_flat[:8], tier4_flat[8:16], tier4_flat[16:24], tier4_flat[24:32]]
                )
                jenny_cup_schedules.append(jenny_schedule)
        
        # 5. 合并赛程并创建Fixture记录
        cup_ids = {"LIGHTNING": lightning_cup.id}
        for system_code, jenny_cup in jenny_cups:
            cup_ids[f"JENNY_{system_code}"] = jenny_cup.id
        
        fixtures = ScheduleMerger.assign_dates(
            start_date,
            league_schedules,
            lightning_schedule,
            jenny_cup_schedules,
            season.id,
            cup_ids
        )
        
        for fixture in fixtures:
            self.db.add(fixture)
        
        await self.db.commit()
        return season
    
    async def start_season(self, season: Season) -> None:
        """启动赛季"""
        season.status = SeasonStatus.ONGOING
        await self.db.commit()
    
    async def process_matchday(self, season: Season) -> List[Fixture]:
        """处理比赛日 - 获取当天所有比赛"""
        from sqlalchemy import select
        
        next_day = season.current_day + 1
        
        # 获取当天所有比赛
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.season_day == next_day)
            .where(Fixture.status == FixtureStatus.SCHEDULED)
        )
        fixtures = result.scalars().all()
        
        # 更新赛季天数
        season.current_day = next_day
        
        # 更新联赛轮次
        league_days = [1, 2, 3, 5, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20]
        if next_day in league_days:
            season.current_league_round = league_days.index(next_day) + 1
        
        # 更新杯赛轮次
        cup_days = [4, 6, 8, 10, 12, 14, 21]
        if next_day in cup_days:
            season.current_cup_round = cup_days.index(next_day) + 1
        
        # 检查赛季结束
        if next_day >= 26:
            season.status = SeasonStatus.FINISHED
            season.end_date = datetime.utcnow()
        
        await self.db.commit()
        return fixtures
