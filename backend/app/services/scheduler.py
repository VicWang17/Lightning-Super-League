"""
Schedule generation algorithms - 赛程生成算法（配置驱动版）

包含：
1. 联赛圆形轮转算法（支持任意偶数队，当前默认8队双循环）
2. 闪电杯赛程算法（支持动态分组，当前默认32队8组小组赛+淘汰赛）
3. 杰尼杯赛程算法（支持动态规模，当前默认体系内56队）
4. 赛程合并与日期分配（从赛季模板读取）

解耦说明：
- 所有硬编码数字已提取到 app.core.formats 的 FormatConfig 中
- 当前默认使用 DEFAULT_FORMAT（1区赛制）
- 未来新增2区时，传入新的 FormatConfig 即可，无需修改本文件
"""
import random
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import clock

from app.models.season import Season, CupCompetition, CupGroup, Fixture, FixtureType, FixtureStatus, SeasonStatus
from app.models.league import League
from app.models.team import Team
from app.core.formats import (
    get_default_format,
    LeagueScheduleConfig,
    CupConfig,
    SeasonTimelineConfig,
    FormatConfig,
)


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
    """联赛赛程生成器 - 圆形轮转法（配置驱动）"""
    
    @staticmethod
    def generate(
        teams: List[str],
        league_id: str,
        config: Optional[LeagueScheduleConfig] = None
    ) -> LeagueSchedule:
        """
        生成联赛赛程（默认8队双循环14轮）
        
        通过传入 config 可支持不同队数/轮次，当前1区使用默认配置。
        """
        cfg = config or get_default_format().league
        n = cfg.teams_per_league
        total_rounds = cfg.total_rounds
        
        assert len(teams) == n, f"联赛必须有{n}支球队，实际{len(teams)}支"
        assert n % 2 == 0, f"当前只支持偶数支球队，实际{n}支"
        
        # 随机打乱（创建赛季时执行一次）
        shuffled = teams.copy()
        random.shuffle(shuffled)
        
        rounds = []
        rotating = shuffled[1:]  # n-1队参与轮转
        half = n // 2
        
        for round_num in range(1, total_rounds + 1):
            # 构建本轮位置分布
            positions = [shuffled[0]] + rotating  # n个位置
            
            matches = []
            is_second_half = round_num > total_rounds // 2
            
            for i in range(half):
                home = positions[i]
                away = positions[n - 1 - i]  # 镜像位置
                
                # 第二轮循环交换主客场
                if is_second_half:
                    home, away = away, home
                
                matches.append(MatchPair(home, away))
            
            rounds.append(RoundSchedule(round_num, matches))
            
            # 轮转：最后一个元素移到第一个后面
            rotating = [rotating[-1]] + rotating[:-1]
        
        # 随机打乱轮次的顺序，使主客场分布更均匀
        random.shuffle(rounds)
        
        # 重新分配轮次编号
        for i, round_schedule in enumerate(rounds, 1):
            round_schedule.round_number = i
        
        return LeagueSchedule(league_id, rounds)


# ============== 闪电杯赛程算法 ==============

class LightningCupGenerator:
    """闪电杯赛程生成器（配置驱动）"""
    
    GROUP_NAMES = [chr(ord('A') + i) for i in range(26)]  # A-Z，最多26组
    
    @classmethod
    def generate(
        cls,
        competition_id: str,
        top_leagues: List[List[str]],  # 各级别联赛球队列表
        config: Optional[CupConfig] = None
    ) -> Tuple[CupSchedule, List[CupGroup]]:
        """
        生成闪电杯赛程（默认32队分8组）
        
        通过传入 config 可支持不同规模，当前1区使用默认配置。
        """
        cfg = config or get_default_format().cup
        
        # 收集球队
        all_teams = []
        for league in top_leagues:
            all_teams.extend(league)
        
        assert len(all_teams) == cfg.lightning_total_teams, (
            f"闪电杯必须有{cfg.lightning_total_teams}支球队，实际{len(all_teams)}支"
        )
        random.shuffle(all_teams)
        
        # 分组
        group_count = cfg.lightning_group_count
        teams_per_group = cfg.lightning_teams_per_group
        group_rounds = cfg.lightning_group_rounds
        
        group_schedules = []
        cup_groups = []
        
        for i in range(group_count):
            group_name = cls.GROUP_NAMES[i]
            group_teams = all_teams[i * teams_per_group : (i + 1) * teams_per_group]
            
            # 小组单循环赛程（当前只显式支持4队3轮，其余用通用算法）
            rounds = cls._generate_group_rounds(group_teams, group_rounds)
            
            group_schedules.append(CupGroupSchedule(group_name, group_teams, rounds))
            cup_groups.append(CupGroup(
                competition_id=competition_id,
                name=group_name,
                team_ids=group_teams,
                standings=None,
                qualified_team_ids=None
            ))
        
        # 淘汰赛占位
        first_ko_round = group_rounds + 1
        knockout_rounds = [
            RoundSchedule(first_ko_round + i, [])
            for i in range(cfg.lightning_knockout_rounds)
        ]
        
        return CupSchedule(competition_id, group_schedules, knockout_rounds), cup_groups
    
    @classmethod
    def _generate_group_rounds(cls, team_ids: List[str], rounds: int) -> List[RoundSchedule]:
        """生成小组单循环赛程"""
        n = len(team_ids)
        if n == 4 and rounds == 3:
            # 4队单循环的3轮固定对阵（保持与旧版一致）
            return [
                RoundSchedule(1, [
                    MatchPair(team_ids[0], team_ids[1]),
                    MatchPair(team_ids[2], team_ids[3])
                ]),
                RoundSchedule(2, [
                    MatchPair(team_ids[0], team_ids[2]),
                    MatchPair(team_ids[1], team_ids[3])
                ]),
                RoundSchedule(3, [
                    MatchPair(team_ids[0], team_ids[3]),
                    MatchPair(team_ids[1], team_ids[2])
                ]),
            ]
        
        # 通用圆形轮转算法（支持任意偶数队）
        assert n % 2 == 0, "小组球队数必须为偶数"
        result = []
        rotating = team_ids[1:]
        fixed = team_ids[0]
        half = n // 2
        
        for r in range(1, rounds + 1):
            positions = [fixed] + rotating
            matches = []
            for i in range(half):
                matches.append(MatchPair(positions[i], positions[n - 1 - i]))
            result.append(RoundSchedule(r, matches))
            rotating = [rotating[-1]] + rotating[:-1]
        
        return result


# ============== 杰尼杯赛程算法 ==============

@dataclass
class JennyCupSchedule(CupSchedule):
    """杰尼杯赛程（体系内杯赛）"""
    system_code: str  # 所属体系代码
    tier2_teams: List[str]  # 次级联赛球队（种子）


class JennyCupGenerator:
    """杰尼杯赛程生成器（配置驱动）"""
    
    @classmethod
    def generate(
        cls,
        competition_id: str,
        system_code: str,
        tier2_league: List[str],      # 种子球队
        tier3_leagues: List[List[str]],  # 三级联赛球队列表
        tier4_leagues: List[List[str]],   # 四级联赛球队列表
        config: Optional[CupConfig] = None
    ) -> JennyCupSchedule:
        """
        生成杰尼杯赛程（默认体系内56队：48非种子+8种子）
        
        通过传入 config 可支持不同规模。
        """
        cfg = config or get_default_format().cup
        
        # 收集非种子球队
        non_seed_teams = []
        for league in tier3_leagues:
            non_seed_teams.extend(league)
        for league in tier4_leagues:
            non_seed_teams.extend(league)
        
        assert len(non_seed_teams) == cfg.jenny_preliminary_teams, (
            f"杰尼杯非种子球队应为{cfg.jenny_preliminary_teams}支，实际{len(non_seed_teams)}支"
        )
        assert len(tier2_league) == cfg.jenny_seed_teams, (
            f"杰尼杯种子球队应为{cfg.jenny_seed_teams}支，实际{len(tier2_league)}支"
        )
        
        # 预选赛：非种子球队随机配对
        random.shuffle(non_seed_teams)
        round1_matches = []
        preliminary_matches = cfg.jenny_preliminary_teams // 2
        for i in range(preliminary_matches):
            round1_matches.append(MatchPair(non_seed_teams[i * 2], non_seed_teams[i * 2 + 1]))
        
        # 后续淘汰赛占位
        knockout_rounds = [RoundSchedule(1, round1_matches)]
        for i in range(1, cfg.jenny_total_rounds):
            knockout_rounds.append(RoundSchedule(i + 1, []))
        
        return JennyCupSchedule(
            competition_id=competition_id,
            group_schedules=None,
            knockout_rounds=knockout_rounds,
            system_code=system_code,
            tier2_teams=tier2_league
        )


# ============== 日期分配与合并 ==============

class ScheduleMerger:
    """赛程合并器 - 将联赛和杯赛赛程合并到统一时间线（配置驱动）"""
    
    @classmethod
    def assign_dates(
        cls,
        season_start: datetime,
        league_schedules: List[LeagueSchedule],
        lightning_cup: CupSchedule,
        jenny_cups: List[JennyCupSchedule],  # 各体系的杰尼杯
        season_id: str,
        cup_competition_ids: Dict[str, str],  # {"LIGHTNING": id, "JENNY_EAST": id, ...}
        season_template: Optional[SeasonTimelineConfig] = None
    ) -> List[Fixture]:
        """
        将所有赛程合并并分配日期
        
        默认26天时间线从 SeasonTimelineConfig 读取。
        """
        template = season_template or get_default_format().season
        fixtures = []
        
        # 1. 联赛赛程
        league_days = list(template.league_days)
        
        for league_schedule in league_schedules:
            for round_schedule in league_schedule.rounds:
                day_index = round_schedule.round_number - 1
                if day_index < len(league_days):
                    day = league_days[day_index]
                    match_date = season_start + timedelta(days=day - 1)
                    kickoff = match_date.replace(hour=template.kickoff_hour, minute=0, second=0)
                    
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
        cup_days = list(template.lightning_cup_days)
        
        if lightning_cup.group_schedules:
            # 小组赛
            for round_idx in range(len(lightning_cup.group_schedules[0].rounds)):
                if round_idx >= len(cup_days):
                    break
                day = cup_days[round_idx]
                match_date = season_start + timedelta(days=day - 1)
                kickoff = match_date.replace(hour=template.kickoff_hour, minute=0, second=0)
                
                for group in lightning_cup.group_schedules:
                    if round_idx < len(group.rounds):
                        round_schedule = group.rounds[round_idx]
                        for match in round_schedule.matches:
                            fixtures.append(Fixture(
                                season_id=season_id,
                                fixture_type=FixtureType.CUP_LIGHTNING_GROUP,
                                season_day=day,
                                scheduled_at=kickoff,
                                round_number=round_idx + 1,
                                league_id=None,
                                cup_competition_id=cup_competition_ids.get("LIGHTNING"),
                                cup_group_name=group.group_name,
                                cup_stage="GROUP",
                                home_team_id=match.home_team_id,
                                away_team_id=match.away_team_id,
                                status=FixtureStatus.SCHEDULED
                            ))
        
        # 3. 杰尼杯赛程（各体系独立）
        jenny_cup_days = list(template.jenny_cup_days)
        
        for jenny_cup in jenny_cups:
            cup_id = cup_competition_ids.get(f"JENNY_{jenny_cup.system_code}")
            if not cup_id:
                continue
            
            # 预选赛（第1轮）
            if jenny_cup.knockout_rounds and jenny_cup_days:
                round_schedule = jenny_cup.knockout_rounds[0]
                day = jenny_cup_days[0]
                match_date = season_start + timedelta(days=day - 1)
                kickoff = match_date.replace(hour=template.kickoff_hour, minute=0, second=0)
                
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
                        cup_stage="ROUND_48",
                        home_team_id=match.home_team_id,
                        away_team_id=match.away_team_id,
                        status=FixtureStatus.SCHEDULED
                    ))
            
            # 后续轮次待填充
        
        return fixtures


# ============== 赛季调度器服务 ==============

class SeasonScheduler:
    """赛季调度器 - 管理赛季生命周期和比赛执行（配置驱动）"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_season(
        self,
        season_number: int,
        start_date: datetime,
        leagues: List[League],
        teams_by_league: Dict[str, List[Team]],
        format_config: Optional[FormatConfig] = None
    ) -> Season:
        """创建新赛季并生成完整赛程"""
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        
        fmt = format_config or get_default_format()
        
        # 重新查询leagues以eager load system关系
        league_ids = [l.id for l in leagues]
        result = await self.db.execute(
            select(League).options(selectinload(League.system)).where(League.id.in_(league_ids))
        )
        leagues = result.scalars().all()
        
        season_template = fmt.season
        cup_config = fmt.cup
        league_config = fmt.league
        structure = fmt.structure
        
        # 1. 创建赛季
        season = Season(
            season_number=season_number,
            start_date=start_date,
            status=SeasonStatus.PENDING,
            current_day=0,
            current_league_round=0,
            current_cup_round=0,
            total_days=season_template.total_days,
            league_days=len(season_template.league_days),
            cup_start_day=season_template.lightning_cup_days[0] if season_template.lightning_cup_days else 4,
            cup_interval=2,
            offseason_start=season_template.playoff_days[0] if season_template.playoff_days else 24
        )
        self.db.add(season)
        await self.db.flush()  # 获取season.id
        
        # 2. 创建杯赛定义
        # 闪电杯
        top_leagues = [l for l in leagues if l.level in cup_config.lightning_eligible_levels]
        lightning_cup = CupCompetition(
            season_id=season.id,
            name="闪电杯",
            code="LIGHTNING_CUP",
            eligible_league_levels=list(cup_config.lightning_eligible_levels),
            total_teams=cup_config.lightning_total_teams,
            has_group_stage=cup_config.lightning_has_group_stage,
            group_count=cup_config.lightning_group_count,
            teams_per_group=cup_config.lightning_teams_per_group,
            group_rounds=cup_config.lightning_group_rounds,
            current_round=0,
            status=SeasonStatus.PENDING,
            winner_team_id=None
        )
        self.db.add(lightning_cup)
        await self.db.flush()
        
        # 杰尼杯（各体系独立）
        # 从传入的 leagues 中动态提取体系 code，支持多区隔离
        system_codes_in_leagues = sorted(set(l.system.code for l in leagues if l.system))
        
        jenny_cups = []
        for system_code in system_codes_in_leagues:
            jenny_cup = CupCompetition(
                season_id=season.id,
                name=f"杰尼杯-{system_code}",
                code=f"JENNY_CUP_{system_code}",
                eligible_league_levels=list(cup_config.jenny_eligible_levels),
                total_teams=cup_config.jenny_preliminary_teams + cup_config.jenny_seed_teams,
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
            if len(teams) != league_config.teams_per_league:
                continue
            team_ids = [t.id for t in teams]
            schedule = LeagueScheduleGenerator.generate(team_ids, league.id, league_config)
            league_schedules.append(schedule)
        
        # 4. 生成杯赛赛程
        # 闪电杯
        top_league_teams = [
            [t.id for t in teams_by_league.get(l.id, [])]
            for l in top_leagues
        ]
        top_league_teams = [
            teams for teams in top_league_teams
            if len(teams) == league_config.teams_per_league
        ]
        
        lightning_schedule = None
        cup_groups = []
        num_systems = len(system_codes_in_leagues)
        if len(top_league_teams) >= num_systems:
            lightning_schedule, cup_groups = LightningCupGenerator.generate(
                lightning_cup.id,
                top_league_teams[:num_systems],
                cup_config
            )
            for group in cup_groups:
                self.db.add(group)
        
        # 杰尼杯（每体系独立）
        jenny_cup_schedules = []
        expected_tier3 = league_config.teams_per_league * structure.levels[2]
        expected_tier4 = league_config.teams_per_league * structure.levels[3]
        
        for system_code, jenny_cup in jenny_cups:
            system_leagues = [l for l in leagues if l.system.code == system_code]
            tier2 = [l for l in system_leagues if l.level == cup_config.jenny_seed_level]
            tier3 = [l for l in system_leagues if l.level in cup_config.jenny_eligible_levels and l.level == 3]
            tier4 = [l for l in system_leagues if l.level in cup_config.jenny_eligible_levels and l.level == 4]
            
            tier2_flat = [t.id for sublist in ([teams_by_league.get(l.id, []) for l in tier2]) for t in sublist]
            tier3_flat = [t.id for sublist in ([teams_by_league.get(l.id, []) for l in tier3]) for t in sublist]
            tier4_flat = [t.id for sublist in ([teams_by_league.get(l.id, []) for l in tier4]) for t in sublist]
            
            if (len(tier2_flat) == cup_config.jenny_seed_teams and
                len(tier3_flat) == expected_tier3 and
                len(tier4_flat) == expected_tier4):
                
                tier3_sublists = [
                    tier3_flat[i * league_config.teams_per_league:(i + 1) * league_config.teams_per_league]
                    for i in range(structure.levels[2])
                ]
                tier4_sublists = [
                    tier4_flat[i * league_config.teams_per_league:(i + 1) * league_config.teams_per_league]
                    for i in range(structure.levels[3])
                ]
                
                jenny_schedule = JennyCupGenerator.generate(
                    jenny_cup.id,
                    system_code,
                    tier2_flat,
                    tier3_sublists,
                    tier4_sublists,
                    cup_config
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
            cup_ids,
            season_template
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
        """处理比赛日 - 获取当天所有比赛（配置驱动）"""
        from sqlalchemy import select
        
        fmt = get_default_format()
        template = fmt.season
        
        next_day = season.current_day + 1
        
        # 获取当天所有比赛
        result = await self.db.execute(
            select(Fixture)
            .where(Fixture.season_id == season.id)
            .where(Fixture.season_day == next_day)
            .where(Fixture.status == FixtureStatus.SCHEDULED)
        )
        fixtures = result.scalars().all()
        
        # TODO: 触发 Go 实时比赛引擎进行推演
        # =====================================================================
        # 当前：仅返回比赛列表，由外部调用者手动触发模拟（或批量离线模拟）
        # 目标：在此自动调用 match_engine_client.start_match() 启动每场比赛
        #
        # 伪代码：
        #   from app.services.match_engine_client import get_match_engine_client
        #   client = get_match_engine_client()
        #   if await client.health_check():
        #       for fixture in fixtures:
        #           await client.start_match(
        #               match_id=str(fixture.id),
        #               home_team_id=fixture.home_team_id,
        #               away_team_id=fixture.away_team_id,
        #               home_tactic=await self._get_team_tactic(fixture.home_team_id),
        #               away_tactic=await self._get_team_tactic(fixture.away_team_id),
        #               match_type=fixture.fixture_type.value,
        #           )
        #           fixture.status = FixtureStatus.ONGOING
        #   else:
        #       # Go 引擎不可用，降级为批量离线随机模拟
        #       for fixture in fixtures:
        #           result = await MatchSimulator.simulate(fixture)
        #           await MatchSimulator.apply_result(fixture, result, self.db)
        # =====================================================================
        
        # 更新赛季天数
        season.current_day = next_day
        
        # 更新联赛轮次
        league_days = list(template.league_days)
        if next_day in league_days:
            season.current_league_round = league_days.index(next_day) + 1
        
        # 更新杯赛轮次
        cup_days = list(template.lightning_cup_days)
        if next_day in cup_days:
            season.current_cup_round = cup_days.index(next_day) + 1
        
        # 检查赛季结束
        if next_day >= season.total_days:
            season.status = SeasonStatus.FINISHED
            season.end_date = clock.now()
        
        await self.db.commit()
        return fixtures
