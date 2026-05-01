"""
Cup progression logic - 杯赛晋级逻辑（配置驱动版）

处理：
1. 小组赛排名计算
2. 淘汰赛对阵生成（交叉对阵规则）
3. 后续轮次自动填充

解耦说明：
- 杯赛轮次、日期从 SeasonTimelineConfig / CupConfig 读取
- 小组对阵基于 group_count 动态生成
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.season import (
    CupCompetition, CupGroup, Fixture, FixtureType, FixtureStatus, Season
)
from app.core.formats import get_default_format, CupConfig, SeasonTimelineConfig


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
    """杯赛晋级服务（配置驱动）"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== 小组赛排名计算 ====================
    
    async def calculate_group_standings(self, cup_group: CupGroup, season_id: str) -> List[GroupStanding]:
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
        
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.cup_group_name == cup_group.name,
                    Fixture.fixture_type == FixtureType.CUP_LIGHTNING_GROUP,
                    Fixture.status == FixtureStatus.FINISHED
                )
            )
        )
        fixtures = result.scalars().all()
        
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
        
        sorted_standings = sorted(
            standings.values(),
            key=lambda s: (s.points, s.goal_difference, s.goals_for),
            reverse=True
        )
        
        return sorted_standings
    
    async def process_group_stage_completion(self, competition_id: str, season_id: str) -> Dict[str, List[str]]:
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
            standings = await self.calculate_group_standings(group, season_id)
            
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
        生成16强对阵（基于小组数动态生成交叉对阵）
        
        默认8组A-H：
        - A1 vs B2, B1 vs A2
        - C1 vs D2, D1 vs C2
        - E1 vs F2, F1 vs E2
        - G1 vs H2, H1 vs G2
        """
        group_names = sorted(group_results.keys())
        
        fixtures = []
        
        for i in range(0, len(group_names), 2):
            if i + 1 < len(group_names):
                g1 = group_names[i]
                g2 = group_names[i + 1]
                if g1 in group_results and g2 in group_results:
                    fixtures.append((g1, g2, f"{g1}1 vs {g2}2"))
                    fixtures.append((g2, g1, f"{g2}1 vs {g1}2"))
        
        return fixtures
    
    def generate_knockout_bracket(
        self,
        round_of_16_winners: List[str]
    ) -> Dict[str, List[Tuple[str, str]]]:
        """
        生成完整淘汰赛对阵表
        
        假设16强胜者按顺序进入相邻配对
        """
        expected = 8
        if len(round_of_16_winners) != expected:
            raise ValueError(f"16强必须有{expected}支胜者球队，实际{len(round_of_16_winners)}支")
        
        quarter_finals = []
        for i in range(0, len(round_of_16_winners), 2):
            quarter_finals.append((round_of_16_winners[i], round_of_16_winners[i + 1]))
        
        semi_finals = [(f"QF-{i*2+1}W", f"QF-{i*2+2}W") for i in range(2)]
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
        """
        fmt = get_default_format()
        cup_config = fmt.cup
        season_template = fmt.season
        
        group_results = await self.process_group_stage_completion(competition.id, season.id)
        
        fixture_pairs = self.generate_round_of_16_fixtures(group_results)
        
        # 获取16强比赛日
        cup_days = list(season_template.lightning_cup_days)
        group_rounds = cup_config.lightning_group_rounds
        round_of_16_day = cup_days[group_rounds] if group_rounds < len(cup_days) else cup_days[-1]
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=round_of_16_day - 1)
        kickoff = match_date.replace(hour=season_template.kickoff_hour, minute=0, second=0)
        
        created_count = 0
        for group1, group2, _ in fixture_pairs:
            team1_id = group_results[group1][0]  # 小组第一
            team2_id = group_results[group2][1]  # 相邻小组第二
            
            fixture = Fixture(
                season_id=season.id,
                fixture_type=FixtureType.CUP_LIGHTNING_KNOCKOUT,
                season_day=round_of_16_day,
                scheduled_at=kickoff,
                round_number=group_rounds + 1,
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
        
        competition.current_round = group_rounds + 1
        
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
        fmt = get_default_format()
        cup_config = fmt.cup
        season_template = fmt.season
        
        stage_sequence = ["ROUND_16", "QUARTER", "SEMI", "FINAL"]
        
        if current_stage not in stage_sequence:
            raise ValueError(f"Invalid stage: {current_stage}")
        
        current_idx = stage_sequence.index(current_stage)
        if current_idx >= len(stage_sequence) - 1:
            return 0
        
        next_stage = stage_sequence[current_idx + 1]
        
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
        
        winners = []
        for f in fixtures:
            if f.home_score > f.away_score:
                winners.append(f.home_team_id)
            elif f.away_score > f.home_score:
                winners.append(f.away_team_id)
            else:
                winners.append(f.home_team_id)
        
        # 获取下一轮比赛日
        cup_days = list(season_template.lightning_cup_days)
        group_rounds = cup_config.lightning_group_rounds
        stage_to_cup_round = {
            "ROUND_16": group_rounds + 1,
            "QUARTER": group_rounds + 2,
            "SEMI": group_rounds + 3,
            "FINAL": group_rounds + 4,
        }
        next_cup_round = stage_to_cup_round[next_stage]
        next_day = cup_days[next_cup_round - 1] if next_cup_round - 1 < len(cup_days) else cup_days[-1]
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=next_day - 1)
        kickoff = match_date.replace(hour=season_template.kickoff_hour, minute=0, second=0)
        
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
                    away_team_id=winners[i + 1],
                    status=FixtureStatus.SCHEDULED
                )
                self.db.add(fixture)
                created_count += 1
        
        competition.current_round = next_cup_round
        
        await self.db.commit()
        return created_count
    
    # ==================== 杰尼杯晋级（体系内杯赛）====================
    
    async def fill_jenny_cup_round_2(
        self,
        competition: CupCompetition,
        season: Season,
        tier2_teams: List[str]
    ) -> int:
        """
        填充杰尼杯第2轮（32强）
        
        预选赛24场（48进24）+ 8支次级联赛种子 = 32队
        """
        fmt = get_default_format()
        cup_config = fmt.cup
        season_template = fmt.season
        
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
        
        if len(round1_winners) != cup_config.jenny_preliminary_teams // 2:
            print(f"  ⚠️  杰尼杯预选赛胜者数量不对: {len(round1_winners)}/{cup_config.jenny_preliminary_teams // 2}")
            return 0
        if len(tier2_teams) != cup_config.jenny_seed_teams:
            print(f"  ⚠️  杰尼杯种子球队数量不对: {len(tier2_teams)}/{cup_config.jenny_seed_teams}")
            return 0
        
        all_teams = round1_winners + tier2_teams
        
        import random
        random.shuffle(all_teams)
        
        cup_days = list(season_template.jenny_cup_days)
        round2_day = cup_days[1] if len(cup_days) > 1 else cup_days[0]
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=round2_day - 1)
        kickoff = match_date.replace(hour=season_template.kickoff_hour, minute=0, second=0)
        
        created_count = 0
        for i in range(0, len(all_teams), 2):
            if i + 1 < len(all_teams):
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
                    away_team_id=all_teams[i + 1],
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
        fmt = get_default_format()
        cup_config = fmt.cup
        season_template = fmt.season
        
        if current_round < 2 or current_round >= cup_config.jenny_total_rounds:
            return 0
        
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
        
        next_round = current_round + 1
        cup_days = list(season_template.jenny_cup_days)
        next_day = cup_days[next_round - 1] if next_round - 1 < len(cup_days) else cup_days[-1]
        
        from datetime import timedelta
        match_date = season.start_date + timedelta(days=next_day - 1)
        kickoff = match_date.replace(hour=season_template.kickoff_hour, minute=0, second=0)
        
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
                    away_team_id=winners[i + 1],
                    status=FixtureStatus.SCHEDULED
                )
                self.db.add(fixture)
                created_count += 1
        
        competition.current_round = next_round
        await self.db.commit()
        return created_count
