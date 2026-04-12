"""
Cup progression logic - 杯赛晋级逻辑

处理：
1. 小组赛排名计算
2. 淘汰赛对阵生成（交叉对阵规则）
3. 后续轮次自动填充
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.season import (
    CupCompetition, CupGroup, Fixture, FixtureType, FixtureStatus, Season
)


@dataclass
class GroupStanding:
    """小组排名条目"""
    team_id: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0
    points: int = 0
    
    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


class CupProgressionService:
    """杯赛晋级服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== 小组赛排名计算 ====================
    
    async def calculate_group_standings(self, cup_group: CupGroup) -> List[GroupStanding]:
        """
        计算小组排名
        
        排名规则：
        1. 积分
        2. 净胜球
        3. 进球数
        4. 相互对战成绩
        """
        team_ids = cup_group.team_ids
        standings = {team_id: GroupStanding(team_id=team_id) for team_id in team_ids}
        
        # 获取该小组的所有比赛
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_group_name == cup_group.name,
                    Fixture.fixture_type == FixtureType.CUP_LIGHTNING_GROUP,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        fixtures = result.scalars().all()
        
        # 统计比赛数据
        for fixture in fixtures:
            home = standings[fixture.home_team_id]
            away = standings[fixture.away_team_id]
            
            home.played += 1
            away.played += 1
            
            home.goals_for += fixture.home_score or 0
            home.goals_against += fixture.away_score or 0
            away.goals_for += fixture.away_score or 0
            away.goals_against += fixture.home_score or 0
            
            if fixture.home_score > fixture.away_score:
                home.won += 1
                home.points += 3
                away.lost += 1
            elif fixture.home_score < fixture.away_score:
                away.won += 1
                away.points += 3
                home.lost += 1
            else:
                home.drawn += 1
                away.drawn += 1
                home.points += 1
                away.points += 1
        
        # 排序
        sorted_standings = sorted(
            standings.values(),
            key=lambda s: (s.points, s.goal_difference, s.goals_for),
            reverse=True
        )
        
        return sorted_standings
    
    async def process_group_stage_completion(self, competition_id: str) -> Dict[str, List[str]]:
        """
        处理小组赛结束，计算所有小组排名并返回晋级球队
        
        返回: {小组名: [第1名ID, 第2名ID]}
        """
        result = await self.db.execute(
            select(CupGroup).where(CupGroup.competition_id == competition_id)
        )
        groups = result.scalars().all()
        
        group_results = {}
        
        for group in groups:
            standings = await self.calculate_group_standings(group)
            
            # 前2名晋级
            qualified = [s.team_id for s in standings[:2]]
            group.qualified_team_ids = qualified
            group.standings = {
                s.team_id: {
                    "played": s.played,
                    "won": s.won,
                    "drawn": s.drawn,
                    "lost": s.lost,
                    "goals_for": s.goals_for,
                    "goals_against": s.goals_against,
                    "points": s.points
                }
                for s in standings
            }
            
            group_results[group.name] = qualified
        
        await self.db.commit()
        return group_results
    
    # ==================== 淘汰赛对阵生成 ====================
    
    def generate_round_of_16_fixtures(self, group_results: Dict[str, List[str]]) -> List[Tuple[str, str, str]]:
        """
        生成16强对阵
        
        对阵规则（交叉对阵，8个小组A-H）：
        - A1 vs B2, B1 vs A2
        - C1 vs D2, D1 vs C2
        - E1 vs F2, F1 vs E2
        - G1 vs H2, H1 vs G2
        
        返回: [(小组A, 小组B, 对阵描述), ...]
        """
        group_pairs = [
            ("A", "B"), ("C", "D"), ("E", "F"), ("G", "H")
        ]
        
        fixtures = []
        
        for g1, g2 in group_pairs:
            # 小组第一 vs 相邻小组第二
            if g1 in group_results and g2 in group_results:
                # 第一 vs 第二
                fixtures.append((g1, g2, f"{g1}1 vs {g2}2"))
                # 第二 vs 第一
                fixtures.append((g2, g1, f"{g2}1 vs {g1}2"))
        
        return fixtures
    
    def generate_knockout_bracket(
        self,
        round_of_16_winners: List[str]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        生成完整淘汰赛对阵表
        
        假设16强胜者按顺序进入：
        - Match 1 winner vs Match 2 winner -> 8强
        - Match 3 winner vs Match 4 winner -> 8强
        ...
        """
        if len(round_of_16_winners) != 8:
            raise ValueError("16强必须有8支胜者球队")
        
        # 8强对阵（相邻配对）
        quarter_finals = []
        for i in range(0, 8, 2):
            quarter_finals.append((round_of_16_winners[i], round_of_16_winners[i+1]))
        
        # 半决赛占位
        semi_finals = [(f"QF-{i*2+1}W", f"QF-{i*2+2}W") for i in range(2)]
        
        # 决赛占位
        final = [(f"SF-1W", f"SF-2W")]
        
        return {
            "quarter_finals": quarter_finals,
            "semi_finals": semi_finals,
            "final": final
        }
    
    # ==================== 晋级处理入口 ====================
    
    async def fill_lightning_cup_knockout_fixtures(
        self,
        competition: CupCompetition,
        season: Season
    ) -> int:
        """
        填充闪电杯淘汰赛对阵
        
        在小组赛结束后调用，生成16强对阵
        返回生成的比赛数量
        """
        # 1. 计算小组排名
        group_results = await self.process_group_stage_completion(competition.id)
        
        # 2. 生成16强对阵
        fixture_pairs = self.generate_round_of_16_fixtures(group_results)
        
        # 3. 获取16强比赛日（第4轮杯赛 = Day 10）
        cup_days = [4, 6, 8, 10, 12, 14, 21]  # 闪电杯7轮
        round_of_16_day = cup_days[3]  # 第4个杯赛日
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=round_of_16_day - 1)
        kickoff = match_date.replace(hour=20, minute=0, second=0)
        
        # 4. 创建Fixture记录
        created_count = 0
        for group1, group2, _ in fixture_pairs:
            team1_id = group_results[group1][0]  # 小组第一
            team2_id = group_results[group2][1]  # 相邻小组第二
            
            fixture = Fixture(
                season_id=season.id,
                fixture_type=FixtureType.CUP_LIGHTNING_KNOCKOUT,
                season_day=round_of_16_day,
                scheduled_at=kickoff,
                round_number=4,
                league_id=None,
                cup_competition_id=competition.id,
                cup_group_name=None,
                cup_stage="ROUND_16",
                home_team_id=team1_id,
                away_team_id=team2_id,
                status=FixtureStatus.SCHEDULED
            )
            self.db.add(fixture)
            created_count += 1
        
        # 5. 更新杯赛状态
        competition.current_round = 4
        
        await self.db.commit()
        return created_count
    
    async def fill_next_knockout_round(
        self,
        competition: CupCompetition,
        season: Season,
        current_stage: str
    ) -> int:
        """
        根据上一轮的胜者填充下一轮对阵
        
        stages: ROUND_16 -> QUARTER -> SEMI -> FINAL
        """
        stage_sequence = ["ROUND_16", "QUARTER", "SEMI", "FINAL"]
        
        if current_stage not in stage_sequence:
            raise ValueError(f"Invalid stage: {current_stage}")
        
        current_idx = stage_sequence.index(current_stage)
        if current_idx >= len(stage_sequence) - 1:
            return 0  # 已经是决赛
        
        next_stage = stage_sequence[current_idx + 1]
        
        # 获取上一轮的已完成比赛
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_competition_id == competition.id,
                    Fixture.cup_stage == current_stage,
                    Fixture.status == FixtureStatus.FINISHED
                )
            ).order_by(Fixture.id)
        )
        fixtures = result.scalars().all()
        
        if len(fixtures) == 0:
            return 0
        
        # 获取胜者
        winners = []
        for f in fixtures:
            if f.home_score > f.away_score:
                winners.append(f.home_team_id)
            elif f.away_score > f.home_score:
                winners.append(f.away_team_id)
            else:
                # 平局情况 - 这里需要处理点球或其他规则
                # 暂时按主队晋级
                winners.append(f.home_team_id)
        
        # 获取下一轮比赛日
        cup_days = [4, 6, 8, 10, 12, 14, 21]  # 闪电杯7轮
        stage_to_cup_round = {
            "ROUND_16": 4,  # Day 10
            "QUARTER": 5,   # Day 12
            "SEMI": 6,      # Day 14
            "FINAL": 7      # Day 21
        }
        next_cup_round = stage_to_cup_round[next_stage]
        next_day = cup_days[next_cup_round - 1]
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=next_day - 1)
        kickoff = match_date.replace(hour=20, minute=0, second=0)
        
        # 创建下一轮比赛（相邻配对）
        created_count = 0
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                fixture = Fixture(
                    season_id=season.id,
                    fixture_type=FixtureType.CUP_LIGHTNING_KNOCKOUT,
                    season_day=next_day,
                    scheduled_at=kickoff,
                    round_number=next_cup_round,
                    league_id=None,
                    cup_competition_id=competition.id,
                    cup_group_name=None,
                    cup_stage=next_stage,
                    home_team_id=winners[i],
                    away_team_id=winners[i+1],
                    status=FixtureStatus.SCHEDULED
                )
                self.db.add(fixture)
                created_count += 1
        
        # 更新杯赛状态
        competition.current_round = next_cup_round
        
        await self.db.commit()
        return created_count
    
    # ==================== 杰尼杯晋级（体系内杯赛）====================
    
    async def fill_jenny_cup_round_2(
        self,
        competition: CupCompetition,
        season: Season,
        tier2_teams: List[str]  # 次级联赛8支球队作为种子
    ) -> int:
        """
        填充杰尼杯第2轮（32强）
        
        预选赛24场（48进24）+ 8支次级联赛种子 = 32队
        """
        # 获取预选赛胜者
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_competition_id == competition.id,
                    Fixture.round_number == 1,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        round1_fixtures = result.scalars().all()
        
        round1_winners = []
        for f in round1_fixtures:
            if f.home_score > f.away_score:
                round1_winners.append(f.home_team_id)
            else:
                round1_winners.append(f.away_team_id)
        
        # 合并：24支预选赛胜者 + 8支次级联赛种子 = 32队
        all_teams = round1_winners + tier2_teams
        
        # 随机打乱
        import random
        random.shuffle(all_teams)
        
        # 生成16场比赛（32进16）
        cup_days = [4, 8, 10, 12, 14, 15]  # 杰尼杯6轮（预选赛day4, 32强day8, 16强day10, 8强day12, 半决赛day14, 决赛day15）
        round2_day = cup_days[1]  # Day 8
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=round2_day - 1)
        kickoff = match_date.replace(hour=20, minute=0, second=0)
        
        created_count = 0
        for i in range(0, 32, 2):
            fixture = Fixture(
                season_id=season.id,
                fixture_type=FixtureType.CUP_JENNY,
                season_day=round2_day,
                scheduled_at=kickoff,
                round_number=2,
                league_id=None,
                cup_competition_id=competition.id,
                cup_stage="ROUND_32",
                home_team_id=all_teams[i],
                away_team_id=all_teams[i+1],
                status=FixtureStatus.SCHEDULED
            )
            self.db.add(fixture)
            created_count += 1
        
        competition.current_round = 2
        await self.db.commit()
        return created_count
    
    async def fill_jenny_cup_next_round(
        self,
        competition: CupCompetition,
        season: Season,
        current_round: int
    ) -> int:
        """
        填充杰尼杯下一轮（从第3轮开始，常规淘汰赛）
        
        杰尼杯共6轮：预选赛 + 32强 + 16强 + 8强 + 半决赛 + 决赛
        """
        if current_round < 2 or current_round >= 6:
            return 0
        
        # 获取当前轮次胜者
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.cup_competition_id == competition.id,
                    Fixture.round_number == current_round,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        fixtures = result.scalars().all()
        
        winners = []
        for f in fixtures:
            if f.home_score > f.away_score:
                winners.append(f.home_team_id)
            else:
                winners.append(f.away_team_id)
        
        # 下一轮
        next_round = current_round + 1
        cup_days = [4, 8, 10, 12, 14, 15]  # 杰尼杯6轮（预选赛day4, 32强day8, 16强day10, 8强day12, 半决赛day14, 决赛day15）
        next_day = cup_days[next_round - 1]
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=next_day - 1)
        kickoff = match_date.replace(hour=20, minute=0, second=0)
        
        # 阶段名称映射
        stage_map = {
            2: "ROUND_32",
            3: "ROUND_16",
            4: "QUARTER",
            5: "SEMI",
            6: "FINAL"
        }
        
        created_count = 0
        for i in range(0, len(winners), 2):
            if i + 1 < len(winners):
                fixture = Fixture(
                    season_id=season.id,
                    fixture_type=FixtureType.CUP_JENNY,
                    season_day=next_day,
                    scheduled_at=kickoff,
                    round_number=next_round,
                    league_id=None,
                    cup_competition_id=competition.id,
                    cup_stage=stage_map.get(next_round),
                    home_team_id=winners[i],
                    away_team_id=winners[i+1],
                    status=FixtureStatus.SCHEDULED
                )
                self.db.add(fixture)
                created_count += 1
        
        competition.current_round = next_round
        await self.db.commit()
        return created_count
