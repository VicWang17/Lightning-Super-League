"""
Training service - 训练主服务
按设计文档 TRAINING-SYSTEM-DESIGN.md 第 16 章实现。
"""
import random
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models.player import Player, PlayerPosition, PlayerStatus
from app.models.season import Season, Fixture, FixtureStatus
from app.models.training import (
    TeamTrainingPlan, TrainingResult, TrainingSlot, TrainingMode,
    TrainingPlanStatus, TrainingCreatedBy,
)
from app.models.team import Team
from sqlalchemy import or_
from app.core.training_config import (
    TrainingItem, get_training_item, list_training_items,
    get_template, list_templates, INTENSITY_LOAD_POINTS,
)
from app.services.training_growth_service import TrainingGrowthService
from app.services.player_fatigue_service import PlayerFatigueService
from app.services.injury_service import InjuryService
from app.services.player_generator import AttributeGenerator
from app.core.logging import get_logger
from collections import defaultdict


ATTR_LABELS = {
    "sho": "射门", "pas": "传球", "dri": "盘带", "spd": "速度",
    "str_": "力量", "sta": "体能", "acc": "爆发力", "hea": "头球",
    "bal": "平衡", "defe": "防守意识", "tkl": "抢断", "vis": "视野",
    "cro": "传中", "con": "控球", "fin": "远射", "com": "镇定",
    "sav": "扑救", "ref": "反应", "pos": "站位", "rus": "出击",
    "dec": "球商", "fk": "任意球", "pk": "点球",
}

logger = get_logger("app.training")


class TrainingService:
    """训练服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.growth_service = TrainingGrowthService()
        self.fatigue_service = PlayerFatigueService()
        self.injury_service = InjuryService()
    
    # =====================================================================
    # 查询接口
    # =====================================================================
    
    def list_training_items(self, category: str = None) -> list[TrainingItem]:
        """获取训练内容列表"""
        return list_training_items(category=category)
    
    def list_templates(self) -> list:
        """获取训练套餐列表"""
        return list_templates()
    
    async def get_team_training_plan(
        self,
        team_id: str,
        season_id: str,
        start_day: int,
        days: int = 7,
    ) -> list[TeamTrainingPlan]:
        """获取球队未来训练计划"""
        result = await self.db.execute(
            select(TeamTrainingPlan)
            .where(
                and_(
                    TeamTrainingPlan.team_id == team_id,
                    TeamTrainingPlan.season_id == season_id,
                    TeamTrainingPlan.season_day >= start_day,
                    TeamTrainingPlan.season_day < start_day + days,
                )
            )
            .order_by(TeamTrainingPlan.season_day, TeamTrainingPlan.slot)
        )
        return list(result.scalars().all())
    
    async def get_training_results(
        self,
        team_id: str,
        season_id: str,
        player_id: str = None,
        start_day: int = None,
        days: int = None,
        limit: int = 100,
    ) -> list[TrainingResult]:
        """获取训练结算记录"""
        query = select(TrainingResult).where(
            and_(
                TrainingResult.team_id == team_id,
                TrainingResult.season_id == season_id,
            )
        )
        if player_id:
            query = query.where(TrainingResult.player_id == player_id)
        if start_day is not None and days is not None:
            query = query.where(
                and_(
                    TrainingResult.season_day >= start_day,
                    TrainingResult.season_day < start_day + days,
                )
            )
        query = query.order_by(desc(TrainingResult.season_day), desc(TrainingResult.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # =====================================================================
    # 计划管理
    # =====================================================================
    
    async def save_training_plan(
        self,
        team_id: str,
        season_id: str,
        items: list[dict],
        created_by: TrainingCreatedBy = TrainingCreatedBy.PLAYER,
    ) -> list[TeamTrainingPlan]:
        """保存训练计划
        
        items: [{season_day, slot, mode, training_item_id, groups}]
        """
        # 收集需要检查比赛日的日期
        days_to_check = set()
        for item in items:
            slot = item.get("slot")
            if slot == TrainingSlot.EVENING.value:
                days_to_check.add(item["season_day"])
        
        match_days = set()
        if days_to_check:
            result = await self.db.execute(
                select(Fixture.season_day).where(
                    and_(
                        Fixture.season_id == season_id,
                        Fixture.season_day.in_(list(days_to_check)),
                        or_(
                            Fixture.home_team_id == team_id,
                            Fixture.away_team_id == team_id,
                        ),
                    )
                ).distinct()
            )
            match_days = {row[0] for row in result.all()}
        
        saved = []
        for item in items:
            season_day = item["season_day"]
            slot = item["slot"]
            slot_enum = TrainingSlot(slot) if isinstance(slot, str) else slot
            
            # 比赛日跳过 evening slot
            if season_day in match_days and slot == TrainingSlot.EVENING.value:
                continue
            
            # 查找是否已存在
            result = await self.db.execute(
                select(TeamTrainingPlan).where(
                    and_(
                        TeamTrainingPlan.team_id == team_id,
                        TeamTrainingPlan.season_id == season_id,
                        TeamTrainingPlan.season_day == season_day,
                        TeamTrainingPlan.slot == slot,
                    )
                )
            )
            existing = result.scalar_one_or_none()
            
            mode = TrainingMode(item.get("mode", TrainingMode.TEAM.value))
            training_item_id = item.get("training_item_id")
            groups = item.get("groups")
            
            if existing:
                existing.mode = mode
                existing.training_item_id = training_item_id
                existing.groups = groups
                existing.created_by = created_by
                existing.status = TrainingPlanStatus.PLANNED
                saved.append(existing)
            else:
                plan = TeamTrainingPlan(
                    team_id=team_id,
                    season_id=season_id,
                    season_day=season_day,
                    slot=slot_enum,
                    mode=mode,
                    training_item_id=training_item_id,
                    groups=groups,
                    status=TrainingPlanStatus.PLANNED,
                    created_by=created_by,
                )
                self.db.add(plan)
                saved.append(plan)
        
        await self.db.flush()
        return saved
    
    async def get_team_match_days(
        self,
        team_id: str,
        season_id: str,
        start_day: int,
        days: int = 7,
    ) -> set[int]:
        """查询球队在某段时间内的比赛日"""
        result = await self.db.execute(
            select(Fixture.season_day).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.season_day >= start_day,
                    Fixture.season_day < start_day + days,
                    or_(
                        Fixture.home_team_id == team_id,
                        Fixture.away_team_id == team_id,
                    ),
                )
            ).distinct()
        )
        return {row[0] for row in result.all()}

    async def apply_template(
        self,
        team_id: str,
        season_id: str,
        template_id: str,
        start_day: int,
    ) -> list[TeamTrainingPlan]:
        """套用训练套餐
        
        比赛日只有两个训练时段（上午/下午），晚上是比赛，
        因此套餐中的 evening 训练项在比赛日会被自动跳过。
        """
        template = get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # 查询该时间段内的比赛日
        match_days = await self.get_team_match_days(
            team_id, season_id, start_day, len(template.schedule)
        )
        
        slots = [TrainingSlot.MORNING.value, TrainingSlot.AFTERNOON.value, TrainingSlot.EVENING.value]
        items = []
        
        for day_offset, day_schedule in enumerate(template.schedule):
            season_day = start_day + day_offset
            is_match_day = season_day in match_days
            for slot_idx, training_item_id in enumerate(day_schedule):
                # 比赛日跳过 evening slot（第3个时段）
                if is_match_day and slot_idx >= 2:
                    continue
                items.append({
                    "season_day": season_day,
                    "slot": slots[slot_idx],
                    "mode": TrainingMode.TEAM.value,
                    "training_item_id": training_item_id,
                    "groups": None,
                })
        
        return await self.save_training_plan(team_id, season_id, items, TrainingCreatedBy.PLAYER)
    
    async def auto_group_players(
        self,
        team_id: str,
        mode: str = "groups_3",
    ) -> list[dict]:
        """一键按位置分组
        
        返回分组配置，供前端直接使用。
        """
        result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.team_id == team_id,
                    Player.status == PlayerStatus.ACTIVE,
                )
            )
        )
        players = list(result.scalars().all())
        
        if mode == "groups_3":
            attack = [p.id for p in players if p.position == PlayerPosition.FW]
            defense = [p.id for p in players if p.position in (PlayerPosition.DF, PlayerPosition.MF)]
            gk = [p.id for p in players if p.position == PlayerPosition.GK]
            
            # MF 智能分配：随机分配一半到进攻组
            mf_players = [p for p in players if p.position == PlayerPosition.MF]
            for p in mf_players:
                if p.id in defense:
                    defense.remove(p.id)
                if random.random() < 0.5:
                    attack.append(p.id)
                else:
                    defense.append(p.id)
            
            groups = [
                {"group_id": "attack", "name": "进攻组", "player_ids": attack},
                {"group_id": "defense", "name": "防守组", "player_ids": defense},
                {"group_id": "gk", "name": "门将组", "player_ids": gk},
            ]
        elif mode == "groups_2":
            group_a = [p.id for p in players if p.position in (PlayerPosition.FW, PlayerPosition.MF)]
            group_b = [p.id for p in players if p.position in (PlayerPosition.DF, PlayerPosition.GK)]
            groups = [
                {"group_id": "group_a", "name": "A组", "player_ids": group_a},
                {"group_id": "group_b", "name": "B组", "player_ids": group_b},
            ]
        else:
            all_players = [p.id for p in players]
            groups = [
                {"group_id": "team", "name": "全队", "player_ids": all_players},
            ]
        
        return [g for g in groups if g["player_ids"]]
    
    # =====================================================================
    # 训练结算
    # =====================================================================
    
    async def complete_training_slot(
        self,
        team_id: str,
        season_id: str,
        season_day: int,
        slot: TrainingSlot,
        current_season_number: int = 0,
    ) -> dict:
        """结算单个训练时段
        
        返回结算摘要。
        """
        result = await self.db.execute(
            select(TeamTrainingPlan).where(
                and_(
                    TeamTrainingPlan.team_id == team_id,
                    TeamTrainingPlan.season_id == season_id,
                    TeamTrainingPlan.season_day == season_day,
                    TeamTrainingPlan.slot == slot,
                )
            )
        )
        plan = result.scalar_one_or_none()
        
        if not plan:
            return {"completed": False, "reason": "no_plan"}
        
        if plan.status == TrainingPlanStatus.COMPLETED:
            return {"completed": False, "reason": "already_completed"}
        
        # 获取训练内容
        if plan.mode == TrainingMode.TEAM.value and plan.training_item_id:
            training_item = get_training_item(plan.training_item_id)
            if not training_item:
                return {"completed": False, "reason": "invalid_training_item"}
            
            # 获取全队可训练球员
            players = await self._get_trainable_players(team_id)
            
            summary = await self._execute_training(
                plan, players, training_item, TrainingMode.TEAM.value,
                current_season_number,
            )
        elif plan.mode in (TrainingMode.GROUPS_2.value, TrainingMode.GROUPS_3.value) and plan.groups:
            summary = {"total_players": 0, "total_breakthroughs": 0, "breakthrough_players": []}
            
            for group in plan.groups:
                training_item_id = group.get("training_item_id")
                player_ids = group.get("player_ids", [])
                if not training_item_id or not player_ids:
                    continue
                
                training_item = get_training_item(training_item_id)
                if not training_item:
                    continue
                
                players = await self._get_players_by_ids(player_ids)
                group_summary = await self._execute_training(
                    plan, players, training_item, plan.mode,
                    current_season_number,
                )
                
                summary["total_players"] += group_summary["total_players"]
                summary["total_breakthroughs"] += group_summary["total_breakthroughs"]
                summary["breakthrough_players"].extend(group_summary["breakthrough_players"])
        else:
            return {"completed": False, "reason": "invalid_plan_config"}
        
        plan.status = TrainingPlanStatus.COMPLETED
        await self.db.flush()
        
        summary["completed"] = True
        summary["plan_id"] = plan.id
        return summary
    
    async def _execute_training(
        self,
        plan: TeamTrainingPlan,
        players: list[Player],
        training_item: TrainingItem,
        mode: str,
        current_season_number: int,
    ) -> dict:
        """执行训练结算"""
        total_breakthroughs = 0
        total_declines = 0
        breakthrough_players = []
        
        # 获取最近7天该球队的所有训练计划（用于计算重复训练递减）
        recent_plans = await self._get_recent_training_plans(
            plan.team_id, plan.season_id, plan.season_day, days=7
        )
        recent_item_counts = self._count_recent_training_items(recent_plans, plan.id)
        
        for player in players:
            age = current_season_number + abs(player.birth_offset)
            recent_count = recent_item_counts.get(training_item.id, 0)
            
            # 检查是否允许高强度训练
            if training_item.intensity == "hard" and not self.fatigue_service.can_do_high_intensity_training(player):
                continue
            
            # 计算各属性成长（包含退步因子，可能为负）
            gains = {}
            for attr, weight in training_item.attribute_weights.items():
                gain = self.growth_service.calculate_single_attribute_gain(
                    player, training_item, attr, weight, age, recent_count, mode
                )
                if gain != 0:
                    gains[attr] = gain
            
            # 应用疲劳影响
            fitness_before = player.fitness
            fatigue_before = player.fatigue
            self.fatigue_service.apply_training_load(player, training_item)
            
            # 应用劳损累积 (伤病系统 v2)
            body_wear_before = dict(player.body_wear) if player.body_wear else {}
            self.injury_service.apply_training_wear(player, training_item)
            
            # 训练后伤病检定 (伤病系统 v2)
            training_injury = None
            if not training_item.is_recovery:
                training_injury = self.injury_service.check_training_injury(player, training_item)
                if training_injury:
                    training_injury["season_id"] = plan.season_id
                    self.injury_service.apply_injury(player, training_injury, cause="training")
            
            # 应用属性成长/衰退
            before_snapshot = self._snapshot_attributes(player)
            breakthroughs = self.growth_service.apply_attribute_progress(player, gains)
            after_snapshot = self._snapshot_attributes(player)
            
            # 区分统计突破与衰退
            bt_count = sum(1 for b in breakthroughs if b.get("type") == "breakthrough")
            dc_count = sum(1 for b in breakthroughs if b.get("type") == "decline")
            total_breakthroughs += bt_count
            total_declines += dc_count
            
            # 记录结果
            efficiency = self._calculate_efficiency(gains, training_item)
            
            result = TrainingResult(
                plan_id=plan.id,
                team_id=plan.team_id,
                player_id=player.id,
                season_id=plan.season_id,
                season_day=plan.season_day,
                slot=plan.slot,
                training_item_id=training_item.id,
                attribute_gains=gains,
                before_attributes=before_snapshot,
                after_attributes=after_snapshot,
                fitness_before=fitness_before,
                fitness_after=player.fitness,
                fatigue_before=fatigue_before,
                fatigue_after=player.fatigue,
                load_points=training_item.load_points,
                breakthroughs=breakthroughs,
                efficiency=Decimal(str(efficiency)),
            )
            self.db.add(result)
            
            if breakthroughs:
                breakthrough_players.append({
                    "player_id": player.id,
                    "player_name": player.name,
                    "breakthroughs": breakthroughs,
                })
            
            # 如果有训练伤病，也记录下来 (可以后续扩展 TrainingResult 表)
            if training_injury:
                logger.warning(
                    f"Training injury: {player.name} ({player.id}) - "
                    f"{training_injury['injury_name']} ({training_injury['body_part']}, "
                    f"severity={training_injury['severity']}, days={training_injury['days']})"
                )
        
        await self.db.flush()
        
        return {
            "total_players": len(players),
            "total_breakthroughs": total_breakthroughs,
            "total_declines": total_declines,
            "breakthrough_players": breakthrough_players,
        }
    
    async def _get_trainable_players(self, team_id: str) -> list[Player]:
        """获取可训练球员（排除伤停和重伤球员）"""
        result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.team_id == team_id,
                    Player.status == PlayerStatus.ACTIVE,
                )
            )
        )
        players = list(result.scalars().all())
        # 排除中伤/重伤球员（severity >= 2）
        return [
            p for p in players
            if p.current_injury is None or p.current_injury.get("severity", 0) < 2
        ]
    
    async def _get_players_by_ids(self, player_ids: list[str]) -> list[Player]:
        """根据ID列表获取球员"""
        if not player_ids:
            return []
        result = await self.db.execute(
            select(Player).where(Player.id.in_(player_ids))
        )
        return list(result.scalars().all())
    
    async def _get_recent_training_plans(
        self, team_id: str, season_id: str, current_day: int, days: int = 7
    ) -> list[TeamTrainingPlan]:
        """获取最近N天的已完成训练计划"""
        result = await self.db.execute(
            select(TeamTrainingPlan).where(
                and_(
                    TeamTrainingPlan.team_id == team_id,
                    TeamTrainingPlan.season_id == season_id,
                    TeamTrainingPlan.season_day >= current_day - days,
                    TeamTrainingPlan.season_day < current_day,
                    TeamTrainingPlan.status == TrainingPlanStatus.COMPLETED,
                )
            )
        )
        return list(result.scalars().all())
    
    @staticmethod
    def _count_recent_training_items(plans: list[TeamTrainingPlan], exclude_plan_id: str = None) -> dict[str, int]:
        """统计最近N天内各训练内容出现次数"""
        counts = {}
        for plan in plans:
            if exclude_plan_id and plan.id == exclude_plan_id:
                continue
            item_id = plan.training_item_id
            if item_id:
                counts[item_id] = counts.get(item_id, 0) + 1
            # 分组训练
            if plan.groups:
                for group in plan.groups:
                    gid = group.get("training_item_id")
                    if gid:
                        counts[gid] = counts.get(gid, 0) + 1
        return counts
    
    @staticmethod
    def _snapshot_attributes(player: Player) -> dict:
        """快照球员当前属性"""
        return {
            attr: getattr(player, attr, 10)
            for attr in [
                "sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
                "defe", "tkl", "vis", "cro", "con", "fin",
                "com", "sav", "ref", "pos", "rus", "dec", "fk", "pk"
            ]
        }
    
    @staticmethod
    def _calculate_efficiency(gains: dict, training_item: TrainingItem) -> float:
        """计算本次训练效率"""
        if not gains or training_item.is_recovery:
            return 1.00
        total_gain = sum(gains.values())
        expected_gain = training_item.base_gain * len(gains)
        if expected_gain <= 0:
            return 1.00
        return round(min(total_gain / expected_gain, 2.00), 2)
    
    # =====================================================================
    # 球员训练进度查询
    # =====================================================================
    
    async def get_player_training_progress(
        self,
        player_id: str,
        season_id: str,
        days: int = 7,
    ) -> dict:
        """获取球员训练成长进度"""
        player = await self.db.get(Player, player_id)
        if not player:
            raise ValueError(f"Player not found: {player_id}")
        
        # 最近训练结果
        results = await self.db.execute(
            select(TrainingResult).where(
                and_(
                    TrainingResult.player_id == player_id,
                    TrainingResult.season_id == season_id,
                )
            )
            .order_by(desc(TrainingResult.created_at))
            .limit(days * 3)
        )
        results = list(results.scalars().all())
        
        # 汇总成长
        total_gains = {}
        for r in results:
            for attr, gain in (r.attribute_gains or {}).items():
                total_gains[attr] = total_gains.get(attr, 0.0) + gain
        
        # 属性上限提示
        cap_hints = {}
        caps = player.attribute_caps or {}
        for attr in [
            "sho", "pas", "dri", "spd", "str_", "sta", "acc", "hea", "bal",
            "defe", "tkl", "vis", "cro", "con", "fin",
            "com", "sav", "ref", "pos", "rus", "dec", "fk", "pk"
        ]:
            current = getattr(player, attr, 10)
            progress = (player.attribute_progress or {}).get(attr, 0.0)
            total = current + progress
            cap = caps.get(attr)
            if cap:
                remaining = cap - total
                if remaining <= 0.5:
                    hint = "已到上限"
                elif remaining <= 3.0:
                    hint = "接近上限"
                else:
                    hint = "仍有明显成长空间"
            else:
                hint = "仍有明显成长空间"
            cap_hints[attr] = {
                "current": current,
                "progress": round(progress, 2),
                "cap": cap,
                "hint": hint,
            }
        
        return {
            "player_id": player_id,
            "player_name": player.name,
            "recent_sessions": len(results),
            "total_gains": {k: round(v, 4) for k, v in total_gains.items()},
            "attribute_status": cap_hints,
            "growth_curve": {
                "type": player.growth_curve_type,
                "peak_age": player.growth_peak_age,
                "speed": float(player.growth_speed) if player.growth_speed else 1.0,
            },
        }

    # =====================================================================
    # 批量训练结算（压测/事件循环优化）
    # =====================================================================

    async def bulk_complete_training_day(
        self,
        season_id: str,
        season_day: int,
        current_season_number: int,
        team_ids: list[str],
    ) -> dict:
        """为多个球队批量结算当天的全部训练时段。

        相比逐球队逐时段调用 complete_training_slot，本方法一次性加载
        所有必要数据，显著减少数据库往返。
        """
        from collections import defaultdict

        slots = [TrainingSlot.MORNING.value, TrainingSlot.AFTERNOON.value, TrainingSlot.EVENING.value]

        # 0. 查询当天有比赛的球队
        match_teams_result = await self.db.execute(
            select(Fixture.home_team_id, Fixture.away_team_id).where(
                and_(
                    Fixture.season_id == season_id,
                    Fixture.season_day == season_day,
                    or_(
                        Fixture.home_team_id.in_(team_ids),
                        Fixture.away_team_id.in_(team_ids),
                    ),
                )
            )
        )
        teams_with_match = set()
        for home_id, away_id in match_teams_result.all():
            teams_with_match.add(home_id)
            teams_with_match.add(away_id)

        # 1. 加载当天所有球队的训练计划
        plans_result = await self.db.execute(
            select(TeamTrainingPlan).where(
                and_(
                    TeamTrainingPlan.season_id == season_id,
                    TeamTrainingPlan.season_day == season_day,
                    TeamTrainingPlan.team_id.in_(team_ids),
                )
            )
        )
        plans = list(plans_result.scalars().all())
        plan_map: dict[tuple[str, str], TeamTrainingPlan] = {}
        for p in plans:
            plan_map[(p.team_id, p.slot.value)] = p

        # 2. 加载所有可训练球员
        players_result = await self.db.execute(
            select(Player).where(
                and_(
                    Player.team_id.in_(team_ids),
                    Player.status == PlayerStatus.ACTIVE,
                )
            )
        )
        players_by_team: dict[str, list[Player]] = defaultdict(list)
        for p in players_result.scalars().all():
            players_by_team[p.team_id].append(p)
        # 按球员 id 排序，保证多事务更新同一批球员时的加锁顺序一致，减少死锁
        for team_id in players_by_team:
            players_by_team[team_id].sort(key=lambda p: p.id)

        # 3. 加载最近 7 天所有球队的已完成计划（用于重复递减）
        recent_plans_result = await self.db.execute(
            select(TeamTrainingPlan).where(
                and_(
                    TeamTrainingPlan.season_id == season_id,
                    TeamTrainingPlan.season_day >= season_day - 7,
                    TeamTrainingPlan.season_day < season_day,
                    TeamTrainingPlan.team_id.in_(team_ids),
                    TeamTrainingPlan.status == TrainingPlanStatus.COMPLETED,
                )
            )
        )
        recent_counts: dict[tuple[str, str], int] = {}
        for p in recent_plans_result.scalars().all():
            key = (p.team_id, p.training_item_id)
            recent_counts[key] = recent_counts.get(key, 0) + 1

        total_sessions = 0
        total_breakthroughs = 0
        total_declines = 0
        total_training_injuries = 0
        training_injuries_by_severity = {1: 0, 2: 0, 3: 0}
        training_injury_samples: list[str] = []
        injured_players: list[dict] = []
        results_to_add: list[TrainingResult] = []

        for team_id in team_ids:
            for slot in slots:
                # 比赛日跳过 evening slot
                if team_id in teams_with_match and slot == TrainingSlot.EVENING.value:
                    continue
                plan = plan_map.get((team_id, slot))
                if not plan or plan.status == TrainingPlanStatus.COMPLETED.value:
                    continue

                training_item = get_training_item(plan.training_item_id) if plan.training_item_id else None
                if not training_item:
                    continue

                players = players_by_team.get(team_id, [])
                if not players:
                    continue

                recent_count = recent_counts.get((team_id, training_item.id), 0)

                for player in players:
                    if player.status != PlayerStatus.ACTIVE:
                        continue
                    if player.current_injury is not None and player.current_injury.get("severity", 0) >= 2:
                        continue

                    age = current_season_number + abs(player.birth_offset)

                    if training_item.intensity == "hard" and not self.fatigue_service.can_do_high_intensity_training(player):
                        continue

                    gains = {}
                    for attr, weight in training_item.attribute_weights.items():
                        gain = self.growth_service.calculate_single_attribute_gain(
                            player, training_item, attr, weight, age, recent_count, TrainingMode.TEAM.value,
                        )
                        if gain != 0:
                            gains[attr] = gain

                    fitness_before = player.fitness
                    fatigue_before = player.fatigue
                    self.fatigue_service.apply_training_load(player, training_item)
                    self.injury_service.apply_training_wear(player, training_item)

                    training_injury = None
                    if not training_item.is_recovery:
                        training_injury = self.injury_service.check_training_injury(player, training_item)
                        if training_injury:
                            training_injury["season_id"] = season_id
                            self.injury_service.apply_injury(player, training_injury, cause="training")
                            total_training_injuries += 1
                            severity = int(training_injury.get("severity", 0) or 0)
                            if severity in training_injuries_by_severity:
                                training_injuries_by_severity[severity] += 1
                            injured_players.append({
                                "player_id": player.id,
                                "player_name": player.name,
                                "team_id": team_id,
                                "injury_name": training_injury["injury_name"],
                                "body_part": training_injury["body_part"],
                                "severity": training_injury["severity"],
                                "days": training_injury["days"],
                            })
                            if len(training_injury_samples) < 5:
                                training_injury_samples.append(
                                    f"{player.name}:{training_injury['injury_name']}"
                                    f"(S{training_injury['severity']},{training_injury['days']}d)"
                                )

                    before_snapshot = self._snapshot_attributes(player)
                    breakthroughs = self.growth_service.apply_attribute_progress(player, gains)
                    after_snapshot = self._snapshot_attributes(player)

                    bt_count = sum(1 for b in breakthroughs if b.get("type") == "breakthrough")
                    dc_count = sum(1 for b in breakthroughs if b.get("type") == "decline")
                    total_breakthroughs += bt_count
                    total_declines += dc_count

                    efficiency = self._calculate_efficiency(gains, training_item)

                    result = TrainingResult(
                        plan_id=plan.id,
                        team_id=plan.team_id,
                        player_id=player.id,
                        season_id=plan.season_id,
                        season_day=plan.season_day,
                        slot=plan.slot,
                        training_item_id=training_item.id,
                        attribute_gains=gains,
                        before_attributes=before_snapshot,
                        after_attributes=after_snapshot,
                        fitness_before=fitness_before,
                        fitness_after=player.fitness,
                        fatigue_before=fatigue_before,
                        fatigue_after=player.fatigue,
                        load_points=training_item.load_points,
                        breakthroughs=breakthroughs,
                        efficiency=Decimal(str(efficiency)),
                    )
                    results_to_add.append(result)

                plan.status = TrainingPlanStatus.COMPLETED.value
                total_sessions += 1

        if results_to_add:
            self.db.add_all(results_to_add)
        await self.db.flush()
        if total_training_injuries:
            logger.info(
                "Training injuries: season=%s day=%s total=%s minor/medium/major=%s/%s/%s samples=%s",
                season_id,
                season_day,
                total_training_injuries,
                training_injuries_by_severity[1],
                training_injuries_by_severity[2],
                training_injuries_by_severity[3],
                "; ".join(training_injury_samples),
            )

        return {
            "teams_processed": len(team_ids),
            "sessions_completed": total_sessions,
            "total_breakthroughs": total_breakthroughs,
            "total_declines": total_declines,
            "training_injuries": total_training_injuries,
            "training_injuries_minor": training_injuries_by_severity[1],
            "training_injuries_medium": training_injuries_by_severity[2],
            "training_injuries_major": training_injuries_by_severity[3],
            "injured_players": injured_players,
        }


    async def get_team_training_progress(
        self,
        team_id: str,
        season_id: str,
        player_ids: list[str],
        metric: str,
        start_day: int,
        end_day: int,
    ) -> dict:
        """获取指定球员在某项能力/OVR上的训练成长曲线

        - 按天聚合，同一天多个 slot 取最后一个 slot 的 after_attributes
        - 缺失天数前向填充，保证折线连续
        - 同时返回该指标下的整数突破标记
        """
        if metric != "ovr" and metric not in ATTR_LABELS:
            raise ValueError(f"不支持的指标: {metric}")

        slot_order = {"morning": 0, "afternoon": 1, "evening": 2}

        results = await self.db.execute(
            select(TrainingResult)
            .where(
                and_(
                    TrainingResult.team_id == team_id,
                    TrainingResult.season_id == season_id,
                    TrainingResult.player_id.in_(player_ids),
                    TrainingResult.season_day >= start_day,
                    TrainingResult.season_day <= end_day,
                )
            )
            .order_by(TrainingResult.season_day, TrainingResult.slot)
        )
        results = list(results.scalars().all())

        # 加载球员信息
        players_result = await self.db.execute(
            select(Player).where(Player.id.in_(player_ids))
        )
        players = {p.id: p for p in players_result.scalars().all()}

        # 按球员 -> 天数 -> 最后一个 slot 的结果
        by_player_day: dict[str, dict[int, TrainingResult]] = defaultdict(dict)
        for r in results:
            slot_value = r.slot.value if hasattr(r.slot, "value") else r.slot
            slot_idx = slot_order.get(slot_value, 99)
            existing = by_player_day[r.player_id].get(r.season_day)
            if existing is None:
                by_player_day[r.player_id][r.season_day] = r
            else:
                existing_slot = existing.slot.value if hasattr(existing.slot, "value") else existing.slot
                if slot_order.get(existing_slot, 99) < slot_idx:
                    by_player_day[r.player_id][r.season_day] = r

        series = []
        for pid in player_ids:
            player = players.get(pid)
            if not player:
                continue

            day_map = by_player_day.get(pid, {})
            current_value: float | None = None
            values = []
            breakthroughs = []

            for day in range(start_day, end_day + 1):
                r = day_map.get(day)
                if r:
                    attrs = r.after_attributes or {}
                    if metric == "ovr":
                        current_value = float(AttributeGenerator.calculate_ovr(player.position, attrs))
                    else:
                        current_value = float(attrs.get(metric, current_value or 0))

                    for bt in r.breakthroughs or []:
                        if bt.get("attribute") == metric:
                            breakthroughs.append({
                                "season_day": day,
                                "attribute": metric,
                                "before": bt.get("before", 0),
                                "after": bt.get("after", 0),
                            })

                if current_value is not None:
                    values.append({"season_day": day, "value": current_value})

            series.append({
                "player_id": pid,
                "player_name": player.name,
                "avatar_url": player.avatar_url,
                "values": values,
                "breakthroughs": breakthroughs,
            })

        return {
            "metric": metric,
            "metric_label": "OVR" if metric == "ovr" else ATTR_LABELS.get(metric, metric),
            "start_day": start_day,
            "end_day": end_day,
            "series": series,
        }
