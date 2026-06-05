"""
AI Training Planner - AI 训练规划器
按设计文档 TRAINING-SYSTEM-DESIGN.md 第 14 章实现。
"""
import random
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.player import Player, PlayerPosition, PlayerStatus
from app.models.season import Season, Fixture, FixtureStatus
from app.models.team import Team
from app.models.training import TeamTrainingAIProfile, TrainingSlot, TrainingMode, TrainingCreatedBy
from app.core.training_config import (
    list_training_items, get_template, TrainingItem,
)
from app.services.player_fatigue_service import PlayerFatigueService
from app.core.logging import get_logger

logger = get_logger("app.ai_training")


class AITrainingPlanner:
    """AI 训练规划器"""
    
    # AI 风格偏好权重
    _STYLE_CATEGORY_WEIGHTS = {
        "attacking": {
            "finishing": 1.30,
            "technical": 1.15,
            "passing": 1.10,
            "tactical": 1.00,
            "physical": 0.90,
            "defending": 0.70,
            "set_piece": 0.80,
            "goalkeeper": 0.50,
            "recovery": 1.00,
            "analysis": 0.90,
        },
        "defensive": {
            "finishing": 0.70,
            "technical": 0.90,
            "passing": 1.00,
            "tactical": 1.10,
            "physical": 1.00,
            "defending": 1.30,
            "set_piece": 1.10,
            "goalkeeper": 0.80,
            "recovery": 1.00,
            "analysis": 1.00,
        },
        "physical": {
            "finishing": 0.90,
            "technical": 0.90,
            "passing": 0.95,
            "tactical": 1.00,
            "physical": 1.30,
            "defending": 1.00,
            "set_piece": 0.80,
            "goalkeeper": 0.60,
            "recovery": 0.90,
            "analysis": 0.80,
        },
        "technical": {
            "finishing": 0.90,
            "technical": 1.20,
            "passing": 1.25,
            "tactical": 1.10,
            "physical": 0.85,
            "defending": 0.85,
            "set_piece": 0.90,
            "goalkeeper": 0.60,
            "recovery": 1.00,
            "analysis": 1.05,
        },
        "balanced": {
            "finishing": 1.00,
            "technical": 1.00,
            "passing": 1.00,
            "tactical": 1.00,
            "physical": 1.00,
            "defending": 1.00,
            "set_piece": 1.00,
            "goalkeeper": 0.80,
            "recovery": 1.00,
            "analysis": 1.00,
        },
        "youth_focus": {
            "finishing": 1.05,
            "technical": 1.15,
            "passing": 1.10,
            "tactical": 0.95,
            "physical": 0.95,
            "defending": 1.00,
            "set_piece": 0.90,
            "goalkeeper": 0.80,
            "recovery": 1.00,
            "analysis": 1.05,
        },
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.fatigue_service = PlayerFatigueService()
    
    async def generate_daily_plan(
        self,
        team_id: str,
        season_id: str,
        season_day: int,
    ) -> list[dict]:
        """为 AI 球队生成单日训练计划
        
        比赛日只有两个训练时段（上午/下午），晚上是比赛。
        """
        
        # 获取 AI 偏好
        profile = await self._get_or_create_ai_profile(team_id)
        style = profile.style or "balanced"
        
        # 获取球队信息
        team = await self.db.get(Team, team_id)
        if not team:
            raise ValueError(f"Team not found: {team_id}")
        
        # 获取可训练球员和平均疲劳
        players = await self._get_trainable_players(team_id)
        avg_fatigue = sum(p.fatigue or 0 for p in players) / max(len(players), 1)
        avg_fitness = sum(p.fitness or 100 for p in players) / max(len(players), 1)
        
        # 检查未来赛程
        has_match_soon = await self._has_match_within_days(team_id, season_id, season_day, days=2)
        # 检查当天是否有比赛
        has_match_today = await self._has_match_on_day(team_id, season_id, season_day)
        
        # 获取风格权重
        category_weights = self._STYLE_CATEGORY_WEIGHTS.get(style, self._STYLE_CATEGORY_WEIGHTS["balanced"])
        
        # 判断是否需要恢复
        needs_recovery = avg_fitness < 70 or avg_fatigue > 55
        
        slots = [TrainingSlot.MORNING.value, TrainingSlot.AFTERNOON.value]
        if not has_match_today:
            slots.append(TrainingSlot.EVENING.value)
        plan_items = []
        
        for slot in slots:
            # 选择训练内容
            item_id = self._pick_training_item(
                category_weights,
                needs_recovery=needs_recovery,
                is_evening=(slot == TrainingSlot.EVENING.value),
                has_match_soon=has_match_soon,
                random_seed=profile.random_seed + season_day + hash(slot),
            )
            
            plan_items.append({
                "season_day": season_day,
                "slot": slot,
                "mode": TrainingMode.GROUPS_3.value,
                "training_item_id": item_id,
                "groups": None,  # AI 分组由训练服务在结算时动态生成
            })
        
        return plan_items
    
    async def generate_default_plan(
        self,
        team_id: str,
        season_id: str,
        season_day: int,
    ) -> list[dict]:
        """为未规划的人类玩家生成默认训练计划
        
        比赛日只有两个训练时段（上午/下午），晚上是比赛。
        """
        # 检查当天是否有比赛
        has_match_today = await self._has_match_on_day(team_id, season_id, season_day)
        max_slots = 2 if has_match_today else 3
        
        # 使用标准微周期模板
        template = get_template("standard_microcycle")
        if not template:
            # fallback：简单默认
            slots = [TrainingSlot.MORNING.value, TrainingSlot.AFTERNOON.value, TrainingSlot.EVENING.value]
            default_items = ["rondo_4v2", "first_touch_escape", "mobility_session"]
            return [
                {
                    "season_day": season_day,
                    "slot": slots[i],
                    "mode": TrainingMode.TEAM.value,
                    "training_item_id": default_items[i],
                    "groups": None,
                }
                for i in range(max_slots)
            ]
        
        day_offset = (season_day - 1) % 7
        if day_offset >= len(template.schedule):
            day_offset = 0
        
        day_schedule = template.schedule[day_offset]
        slots = [TrainingSlot.MORNING.value, TrainingSlot.AFTERNOON.value, TrainingSlot.EVENING.value]
        
        return [
            {
                "season_day": season_day,
                "slot": slots[i],
                "mode": TrainingMode.TEAM.value,
                "training_item_id": day_schedule[i],
                "groups": None,
            }
            for i in range(min(max_slots, len(day_schedule)))
        ]
    
    async def auto_fill_missing_plans(
        self,
        team_id: str,
        season_id: str,
        start_day: int,
        days: int = 7,
    ) -> list[dict]:
        """自动填充缺失的训练计划"""
        from app.services.training_service import TrainingService
        
        training_service = TrainingService(self.db)
        existing = await training_service.get_team_training_plan(team_id, season_id, start_day, days)
        existing_slots = {(p.season_day, p.slot.value) for p in existing}
        
        # 判断是否为 AI 球队
        team = await self.db.get(Team, team_id)
        is_ai = team and team.user and getattr(team.user, 'is_ai', False)
        
        items = []
        for day in range(start_day, start_day + days):
            for slot in [TrainingSlot.MORNING.value, TrainingSlot.AFTERNOON.value, TrainingSlot.EVENING.value]:
                if (day, slot) in existing_slots:
                    continue
                
                if is_ai:
                    day_plan = await self.generate_daily_plan(team_id, season_id, day)
                    for item in day_plan:
                        if item["slot"] == slot:
                            items.append(item)
                else:
                    day_plan = await self.generate_default_plan(team_id, season_id, day)
                    for item in day_plan:
                        if item["slot"] == slot:
                            items.append(item)
        
        if items:
            await training_service.save_training_plan(
                team_id, season_id, items, TrainingCreatedBy.DEFAULT
            )
        
        return items
    
    async def _get_or_create_ai_profile(self, team_id: str) -> TeamTrainingAIProfile:
        """获取或创建 AI 训练偏好"""
        result = await self.db.execute(
            select(TeamTrainingAIProfile).where(TeamTrainingAIProfile.team_id == team_id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            styles = list(self._STYLE_CATEGORY_WEIGHTS.keys())
            style = random.choice(styles)
            profile = TeamTrainingAIProfile(
                team_id=team_id,
                style=style,
                risk_tolerance=round(random.uniform(0.3, 0.7), 2),
                youth_focus=round(random.uniform(0.2, 0.5), 2),
                random_seed=random.randint(0, 10000),
            )
            self.db.add(profile)
            await self.db.flush()
        
        return profile
    
    async def _get_trainable_players(self, team_id: str) -> list[Player]:
        """获取可训练球员"""
        result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.team_id == team_id,
                    Player.status == PlayerStatus.ACTIVE,
                )
            )
        )
        return list(result.scalars().all())
    
    async def _has_match_within_days(
        self, team_id: str, season_id: str, current_day: int, days: int = 2
    ) -> bool:
        """检查未来N天是否有比赛"""
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.season_day > current_day,
                    Fixture.season_day <= current_day + days,
                    Fixture.status == FixtureStatus.SCHEDULED,
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id,
                    ),
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _has_match_on_day(
        self, team_id: str, season_id: str, day: int
    ) -> bool:
        """检查当天是否有比赛"""
        result = await self.db.execute(
            select(Fixture).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.season_day == day,
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id,
                    ),
                )
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    def _pick_training_item(
        self,
        category_weights: dict[str, float],
        needs_recovery: bool = False,
        is_evening: bool = False,
        has_match_soon: bool = False,
        random_seed: int = 0,
    ) -> str:
        """选择训练内容"""
        rng = random.Random(random_seed)
        
        all_items = list_training_items()
        candidates = []
        weights = []
        
        for item in all_items:
            # 恢复需求优先恢复训练
            if needs_recovery:
                if item.is_recovery:
                    candidates.append(item)
                    weights.append(2.0)
                elif item.intensity == "light":
                    candidates.append(item)
                    weights.append(0.5)
                continue
            
            # 晚上偏向低强度
            if is_evening:
                if item.intensity == "hard":
                    continue
                if item.is_recovery:
                    candidates.append(item)
                    weights.append(1.5 if has_match_soon else 1.0)
                    continue
            
            # 赛前偏向恢复/低强度
            if has_match_soon and is_evening:
                if item.is_recovery:
                    candidates.append(item)
                    weights.append(2.0)
                    continue
                elif item.intensity != "light":
                    continue
            
            # 正常选择
            cat_weight = category_weights.get(item.category, 1.0)
            # 随机扰动 10-20%
            noise = rng.uniform(0.85, 1.15)
            candidates.append(item)
            weights.append(cat_weight * noise)
        
        if not candidates:
            return "full_rest"
        
        chosen = rng.choices(candidates, weights=weights, k=1)[0]
        return chosen.id


# 需要导入 or_ 用于查询
from sqlalchemy import or_
