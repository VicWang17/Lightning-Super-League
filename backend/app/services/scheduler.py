"""
Schedule generation algorithms - 赛程生成算法

包含：
1. 联赛圆形轮转算法（16队双循环）
2. 闪电杯赛程算法（64队，小组赛+淘汰赛）
3. 杰尼杯赛程算法（192队，首轮+淘汰赛）
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
        生成16队双循环赛程（30轮）
        
        算法：圆形轮转法 + 随机打乱轮次
        - 位置0固定，其余15队顺时针轮转
        - 每轮8场比赛（左半区vs右半区镜像）
        - 前15轮主场，后15轮交换主客场
        - 最后将30轮随机打乱，避免球队连续主/客场
        """
        assert len(teams) == 16, "联赛必须有16支球队"
        
        # 随机打乱（创建赛季时执行一次）
        shuffled = teams.copy()
        random.shuffle(shuffled)
        
        rounds = []
        rotating = shuffled[1:]  # 15队参与轮转
        
        for round_num in range(1, 31):
            # 构建本轮位置分布
            positions = [shuffled[0]] + rotating  # 16个位置
            
            matches = []
            is_second_half = round_num > 15  # 第16轮开始交换主客场
            
            for i in range(8):
                home = positions[i]
                away = positions[15 - i]  # 镜像位置
                
                # 第二轮循环交换主客场
                if is_second_half:
                    home, away = away, home
                
                matches.append(MatchPair(home, away))
            
            rounds.append(RoundSchedule(round_num, matches))
            
            # 轮转：最后一个元素移到第一个后面
            rotating = [rotating[-1]] + rotating[:-1]
        
        # 随机打乱30轮的顺序，使主客场分布更均匀
        random.shuffle(rounds)
        
        # 重新分配轮次编号
        for i, round_schedule in enumerate(rounds, 1):
            round_schedule.round_number = i
        
        return LeagueSchedule(league_id, rounds)


# ============== 闪电杯赛程算法 ==============

class LightningCupGenerator:
    """闪电杯赛程生成器"""
    
    GROUP_NAMES = [chr(ord('A') + i) for i in range(16)]  # A-P
    
    @classmethod
    def generate(
        cls,
        competition_id: str,
        top_leagues: List[List[str]]  # 4个顶级联赛，每个16队
    ) -> Tuple[CupSchedule, List[CupGroup]]:
        """
        生成闪电杯赛程（64队）
        
        赛制：
        - 小组赛：64队分16组，每组4队，单循环3轮
        - 淘汰赛：32强->16强->8强->4强->决赛，共5轮
        - 总计：3 + 5 = 8轮
        """
        # 收集64队并随机分组
        all_teams = []
        for league in top_leagues:
            all_teams.extend(league)
        
        random.shuffle(all_teams)
        
        # 分16组
        group_schedules = []
        cup_groups = []
        
        for i in range(16):
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
        # 32强: 16场比赛（16组前2名=32队）
        # 16强: 8场
        # 8强: 4场
        # 半决赛: 2场
        # 决赛: 1场
        knockout_rounds = [
            RoundSchedule(4, []),  # ROUND_32 - 待填充
            RoundSchedule(5, []),  # ROUND_16 - 待填充
            RoundSchedule(6, []),  # QUARTER - 待填充
            RoundSchedule(7, []),  # SEMI - 待填充
            RoundSchedule(8, []),  # FINAL - 待填充
        ]
        
        return CupSchedule(competition_id, group_schedules, knockout_rounds), cup_groups


# ============== 杰尼杯赛程算法 ==============

@dataclass
class JennyCupSchedule(CupSchedule):
    """杰尼杯赛程（包含轮空球队）"""
    bye_team_ids: List[str]  # 首轮轮空的二级球队


class JennyCupGenerator:
    """杰尼杯赛程生成器"""
    
    @classmethod
    def generate(
        cls,
        competition_id: str,
        tier2_leagues: List[List[str]],  # 8个二级联赛，每个16队
        tier3_leagues: List[List[str]]   # 8个三级联赛，每个16队
    ) -> JennyCupSchedule:
        """
        生成杰尼杯赛程（192队）
        
        赛制：
        - 第1轮：三级联赛128队参赛，64场（二级64队轮空）
        - 第2轮：64支胜者 + 64支二级 = 128进64
        - 第3-8轮：淘汰赛 64->32->16->8->4->决赛
        - 总计：1 + 7 = 8轮
        """
        tier2_teams = []
        for league in tier2_leagues:
            tier2_teams.extend(league)
        
        tier3_teams = []
        for league in tier3_leagues:
            tier3_teams.extend(league)
        
        # 第1轮：三级球队随机配对（需要偶数支球队）
        random.shuffle(tier3_teams)
        round1_matches = []
        # 使用实际拥有的三级球队数，但不超过128支（64场）
        num_teams = min(len(tier3_teams), 128)
        num_teams = num_teams // 2 * 2  # 确保是偶数
        for i in range(num_teams // 2):
            round1_matches.append(MatchPair(tier3_teams[i*2], tier3_teams[i*2+1]))
        
        # 后续淘汰赛占位
        knockout_rounds = [
            RoundSchedule(1, round1_matches),  # 首轮：三级球队
            RoundSchedule(2, []),  # 128进64（首轮胜者+二级轮空）
            RoundSchedule(3, []),  # 64进32
            RoundSchedule(4, []),  # 32进16
            RoundSchedule(5, []),  # 16进8
            RoundSchedule(6, []),  # 8进4
            RoundSchedule(7, []),  # 半决赛
            RoundSchedule(8, []),  # 决赛
        ]
        
        return JennyCupSchedule(competition_id, None, knockout_rounds, tier2_teams)


# ============== 日期分配与合并 ==============

class ScheduleMerger:
    """赛程合并器 - 将联赛和杯赛赛程合并到统一时间线"""
    
    # 默认配置
    CUP_START_DAY = 6       # 杯赛第1轮在第几天
    CUP_INTERVAL = 3        # 杯赛间隔天数
    CUP_ROUNDS = 8          # 杯赛共8轮
    KICKOFF_HOUR = 20       # 开球时间（20:00）
    
    @classmethod
    def assign_dates(
        cls,
        season_start: datetime,
        league_schedules: List[LeagueSchedule],
        lightning_cup: CupSchedule,
        jenny_cup: CupSchedule,
        season_id: str,
        cup_competition_ids: Dict[str, str]  # {"LIGHTNING": id, "JENNY": id}
    ) -> List[Fixture]:
        """
        将所有赛程合并并分配日期
        
        时间线：
        - Day 1-30: 联赛每天一轮
        - Day 6,9,12,15,18,21,24,27: 杯赛
        - Day 31-42: 休赛期（无比赛）
        """
        fixtures = []
        
        # 1. 联赛赛程（Day 1-30）
        for league_schedule in league_schedules:
            for round_schedule in league_schedule.rounds:
                match_date = season_start + timedelta(days=round_schedule.round_number - 1)
                kickoff = match_date.replace(hour=cls.KICKOFF_HOUR, minute=0, second=0)
                
                for match in round_schedule.matches:
                    fixtures.append(Fixture(
                        season_id=season_id,
                        fixture_type=FixtureType.LEAGUE,
                        season_day=round_schedule.round_number,
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
        cup_days = [cls.CUP_START_DAY + i * cls.CUP_INTERVAL for i in range(cls.CUP_ROUNDS)]
        # cup_days = [6, 9, 12, 15, 18, 21, 24, 27]
        
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
        
        # 淘汰赛（5轮）- 对阵待填充
        for round_idx in range(3, 8):  # 第4-8轮是淘汰赛
            day = cup_days[round_idx]
            match_date = season_start + timedelta(days=day - 1)
            kickoff = match_date.replace(hour=cls.KICKOFF_HOUR, minute=0, second=0)
            
            stage_map = {
                3: "ROUND_32",
                4: "ROUND_16",
                5: "QUARTER",
                6: "SEMI",
                7: "FINAL"
            }
            
            # 这里创建占位fixture，实际对阵后续填充
            # 现在先不创建，等小组赛结束后再创建
            pass
        
        # 3. 杰尼杯赛程
        for round_idx in range(8):  # 8轮
            day = cup_days[round_idx]
            match_date = season_start + timedelta(days=day - 1)
            kickoff = match_date.replace(hour=cls.KICKOFF_HOUR, minute=0, second=0)
            
            if round_idx == 0:
                # 第1轮：三级球队比赛
                round_schedule = jenny_cup.knockout_rounds[0]
                for match in round_schedule.matches:
                    fixtures.append(Fixture(
                        season_id=season_id,
                        fixture_type=FixtureType.CUP_JENNY,
                        season_day=day,
                        scheduled_at=kickoff,
                        round_number=1,
                        league_id=None,
                        cup_competition_id=cup_competition_ids["JENNY"],
                        cup_group_name=None,
                        cup_stage="ROUND_128",  # 首轮192进128
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
            total_days=42,
            league_days=30,
            cup_start_day=6,
            cup_interval=3,
            offseason_start=31
        )
        self.db.add(season)
        await self.db.flush()  # 获取season.id
        
        # 2. 创建杯赛定义
        # 闪电杯
        top_leagues = [l for l in leagues if l.level == 1]
        lightning_cup = CupCompetition(
            season_id=season.id,
            name="闪电杯",
            code="LIGHTNING_CUP",
            eligible_league_levels=[1],
            total_teams=64,
            has_group_stage=True,
            group_count=16,
            teams_per_group=4,
            group_rounds=3,
            current_round=0,
            status=SeasonStatus.PENDING,
            winner_team_id=None
        )
        self.db.add(lightning_cup)
        await self.db.flush()
        
        # 杰尼杯
        jenny_cup = CupCompetition(
            season_id=season.id,
            name="杰尼杯",
            code="JENNY_CUP",
            eligible_league_levels=[2, 3],
            total_teams=192,
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
        
        # 3. 生成联赛赛程
        league_schedules = []
        for league in leagues:
            teams = teams_by_league.get(league.id, [])
            if len(teams) != 16:
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
        lightning_schedule, cup_groups = LightningCupGenerator.generate(
            lightning_cup.id,
            top_league_teams
        )
        for group in cup_groups:
            self.db.add(group)
        
        # 杰尼杯
        tier2_leagues = [l for l in leagues if l.level == 2]
        tier3_leagues = [l for l in leagues if l.level == 3]
        tier2_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier2_leagues]
        tier3_teams = [[t.id for t in teams_by_league.get(l.id, [])] for l in tier3_leagues]
        jenny_schedule = JennyCupGenerator.generate(
            jenny_cup.id,
            tier2_teams,
            tier3_teams
        )
        
        # 存储轮空球队（第2轮加入）
        from app.models.season import CupByeTeam
        for team_id in jenny_schedule.bye_team_ids:
            bye_team = CupByeTeam(
                competition_id=jenny_cup.id,
                team_id=team_id,
                round_number=2
            )
            self.db.add(bye_team)
        
        # 5. 合并赛程并创建Fixture记录
        cup_ids = {"LIGHTNING": lightning_cup.id, "JENNY": jenny_cup.id}
        fixtures = ScheduleMerger.assign_dates(
            start_date,
            league_schedules,
            lightning_schedule,
            jenny_schedule,
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
        
        # 更新联赛轮次（如果是联赛日）
        if next_day <= 30:
            season.current_league_round = next_day
        
        # 更新杯赛轮次（如果是杯赛日）
        cup_days = [6, 9, 12, 15, 18, 21, 24, 27]
        if next_day in cup_days:
            season.current_cup_round = cup_days.index(next_day) + 1
        
        # 检查赛季结束
        if next_day >= 42:
            season.status = SeasonStatus.FINISHED
            season.end_date = datetime.utcnow()
        
        await self.db.commit()
        return fixtures
