"""
Injury treatment service - 伤病医疗加速与风险准备金联动服务
按 EMERGENCY-FUND-INJURY-FINANCE-DESIGN.md 实现。
负责：治疗选项计算、治疗执行（扣款+更新伤病）、自动缓冲、赛季末准备金结转。
"""
import math
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm.attributes import flag_modified

from app.models.player import Player, PlayerPosition
from app.models.finance import (
    FinanceTransaction,
    TransactionSourceType,
    TransactionDirection,
    TeamSeasonFinance,
    FinancialHealth,
)
from app.models.injury_treatment import InjuryTreatment, TreatmentPlan
from app.models.team import Team, TeamFinance
from app.models.league import League
from app.core.economy_config import get_economy_config
from app.core.logging import get_logger
from app.services.notification_service import NotificationService

logger = get_logger("app.injury_treatment")

MONEY_QUANT = Decimal("0.01")


def _quantize(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _round_to_1000(value: Decimal) -> Decimal:
    """金额取整到千位"""
    v = int(value)
    return Decimal((v + 500) // 1000 * 1000)


class InjuryTreatmentService:
    """伤病治疗服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.economy = get_economy_config()

    # =====================================================================
    # 公共查询
    # =====================================================================

    async def list_treatment_options(
        self,
        team_id: str,
        player_id: str,
        injury_record_id: str,
    ) -> List[Dict]:
        """
        返回某次伤病的可选治疗方案列表。
        若伤病不可治疗（severity=1 或已治疗），返回空列表。
        """
        player = await self._get_player(player_id)
        if not player or player.team_id != team_id:
            raise ValueError("球员不存在或不属于该球队")

        injury = player.current_injury
        if not injury:
            return []

        # 用 injury_record_id 匹配（这里用 created_at + player_id 作为简单唯一标识）
        # 设计文档建议 injury_record_id 对应活跃伤病，这里用 created_at 的 iso 字符串
        current_injury_id = injury.get("created_at", "")
        if injury_record_id != current_injury_id:
            # 也允许 injury_record_id 为任意值时匹配当前活跃伤病（简化）
            pass

        severity = injury.get("severity", 0)
        if severity < 2:
            return []  # 轻伤不展示治疗

        if injury.get("treatment_applied", False):
            return []  # 已治疗过

        remaining_days = injury.get("remaining_days", 0)
        original_total_days = injury.get("original_total_days", remaining_days)
        body_part = injury.get("body_part", "")

        league_level = await self._get_team_league_level(team_id)
        player_value_base = self._calc_player_value_base(player, league_level)
        scarcity_multiplier = await self._calc_scarcity_multiplier(team_id, player.position)

        options = []
        for plan in (TreatmentPlan.ENHANCED, TreatmentPlan.SPECIALIST, TreatmentPlan.AGGRESSIVE):
            option = self._build_option(
                plan=plan,
                severity=severity,
                remaining_days=remaining_days,
                original_total_days=original_total_days,
                body_part=body_part,
                player_value_base=player_value_base,
                scarcity_multiplier=scarcity_multiplier,
                is_gk=(player.position == PlayerPosition.GK),
            )
            options.append(option)

        return options

    async def apply_treatment(
        self,
        team_id: str,
        player_id: str,
        injury_record_id: str,
        plan: TreatmentPlan,
    ) -> Dict:
        """
        执行治疗：扣款、更新伤病、写入流水。
        在事务内执行，需由调用方 commit。
        """
        player = await self._get_player(player_id)
        if not player or player.team_id != team_id:
            raise ValueError("球员不存在或不属于该球队")

        injury = player.current_injury
        if not injury:
            raise ValueError("球员当前无活跃伤病")

        if injury.get("treatment_applied", False):
            raise ValueError("该伤病已经接受过治疗")

        severity = injury.get("severity", 0)
        if severity < 2:
            raise ValueError("轻伤不支持医疗加速")

        remaining_days = injury.get("remaining_days", 0)
        original_total_days = injury.get("original_total_days", remaining_days)
        body_part = injury.get("body_part", "")

        # 重新计算费用（不信任前端）
        league_level = await self._get_team_league_level(team_id)
        player_value_base = self._calc_player_value_base(player, league_level)
        scarcity_multiplier = await self._calc_scarcity_multiplier(team_id, player.position)

        option = self._build_option(
            plan=plan,
            severity=severity,
            remaining_days=remaining_days,
            original_total_days=original_total_days,
            body_part=body_part,
            player_value_base=player_value_base,
            scarcity_multiplier=scarcity_multiplier,
            is_gk=(player.position == PlayerPosition.GK),
        )

        if not option.get("available", False):
            raise ValueError("该治疗方案当前不可用")

        medical_cost = option["cost"]
        days_reduced = option["days_reduced"]
        days_after = option["days_after"]
        residual_penalty = option["residual_wear_penalty"]
        recurrence_bonus = option["recurrence_risk_bonus"]

        # 获取赛季财务
        season_id = injury.get("season_id")
        if not season_id:
            # 尝试从球队获取当前赛季
            season_id = await self._get_current_season_id(team_id)

        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        reserve_available = max(Decimal("0"), season_finance.reserve_budget - season_finance.reserve_spent)

        # 支付顺序：准备金优先，余额补足
        reserve_pay = min(reserve_available, medical_cost)
        cash_pay = medical_cost - reserve_pay

        # 扣球队余额
        team_finance = await self._get_team_finance(team_id)
        if not team_finance:
            raise ValueError("球队财务不存在")

        if team_finance.balance < cash_pay:
            raise ValueError("球队余额不足以支付医疗费用")

        # 1. 扣余额
        new_balance = team_finance.balance - medical_cost
        team_finance.balance = _quantize(new_balance)

        # 2. 写入 injury_treatments
        treatment = InjuryTreatment(
            team_id=team_id,
            player_id=player_id,
            season_id=season_id,
            injury_record_id=injury_record_id,
            plan=plan,
            cost=medical_cost,
            reserve_paid=reserve_pay,
            cash_paid=cash_pay,
            days_before=remaining_days,
            days_reduced=days_reduced,
            days_after=days_after,
            residual_wear_penalty=residual_penalty,
            recurrence_risk_bonus=recurrence_bonus,
        )
        self.db.add(treatment)

        # 3. 写入财政流水
        txn_extra = {
            "player_id": player_id,
            "injury_record_id": injury_record_id,
            "plan": plan.value,
            "days_before": remaining_days,
            "days_reduced": days_reduced,
            "days_after": days_after,
            "reserve_paid": str(reserve_pay),
            "cash_paid": str(cash_pay),
        }
        transaction = FinanceTransaction(
            team_id=team_id,
            season_id=season_id,
            source_type=TransactionSourceType.MEDICAL,
            direction=TransactionDirection.EXPENSE,
            amount=medical_cost,
            balance_after=team_finance.balance,
            description=f"{player.name} - {option['plan_label']} ({body_part})",
            extra_data=txn_extra,
        )
        self.db.add(transaction)

        # 4. 更新球员伤病状态
        injury["remaining_days"] = days_after
        injury["treatment_applied"] = True
        injury["treatment_risk_bonus"] = float(recurrence_bonus)
        injury["residual_wear_penalty"] = residual_penalty
        flag_modified(player, "current_injury")

        # 5. 更新赛季财务准备金字段
        season_finance.reserve_spent = _quantize(season_finance.reserve_spent + reserve_pay)
        season_finance.reserve_medical_used = _quantize(season_finance.reserve_medical_used + reserve_pay)
        season_finance.reserve_events_used += 1
        season_finance.current_balance = team_finance.balance

        notify = NotificationService(self.db)
        await notify.send_treatment_completed(
            team_id=team_id,
            season_id=season_id,
            player_name=player.name,
            player_id=player_id,
            plan_name=option['plan_label'],
            days_before=remaining_days,
            days_after=days_after,
            cost=float(medical_cost),
            side_effect=option.get('side_effect', ''),
        )

        await self.db.flush()
        logger.info(
            f"治疗已执行: player={player_id}, plan={plan.value}, "
            f"cost={medical_cost}, reserve_pay={reserve_pay}, cash_pay={cash_pay}, "
            f"days_before={remaining_days}, days_after={days_after}"
        )

        return {
            "treatment_id": treatment.id,
            "player_id": player_id,
            "plan": plan.value,
            "cost": medical_cost,
            "reserve_paid": reserve_pay,
            "cash_paid": cash_pay,
            "days_before": remaining_days,
            "days_reduced": days_reduced,
            "days_after": days_after,
            "reserve_available_after": max(Decimal("0"), season_finance.reserve_budget - season_finance.reserve_spent),
        }

    async def auto_cover_event(
        self,
        team_id: str,
        season_id: str,
        event_type: str,
        amount: Decimal,
    ) -> Optional[FinanceTransaction]:
        """
        自动准备金缓冲事件。
        若超过上限则返回 None，表示不自动保护。
        """
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        reserve_available = max(Decimal("0"), season_finance.reserve_budget - season_finance.reserve_spent)

        if reserve_available <= 0:
            return None

        # 检查频率限制
        auto_limit = season_finance.reserve_budget * Decimal("0.50")
        if season_finance.reserve_auto_used >= auto_limit:
            return None
        if season_finance.reserve_events_used >= 5:
            return None

        # 各类事件上限
        cover_limits = {
            "minor_injury": min(Decimal("20000"), reserve_available),
            "medium_diagnosis": min(Decimal("40000"), reserve_available),
            "wage_shortage": amount * Decimal("0.50"),
            "youth_accident": amount * Decimal("0.50"),
            "facility_accident": season_finance.reserve_budget * Decimal("0.10"),
        }
        cover = min(cover_limits.get(event_type, Decimal("0")), amount, reserve_available)
        if cover <= 0:
            return None

        # 扣球队余额（自动缓冲仍从余额扣，但财政健康计算会区分）
        team_finance = await self._get_team_finance(team_id)
        if not team_finance or team_finance.balance < cover:
            return None

        team_finance.balance = _quantize(team_finance.balance - cover)
        season_finance.current_balance = team_finance.balance
        season_finance.reserve_spent = _quantize(season_finance.reserve_spent + cover)
        season_finance.reserve_auto_used = _quantize(season_finance.reserve_auto_used + cover)
        season_finance.reserve_events_used += 1

        transaction = FinanceTransaction(
            team_id=team_id,
            season_id=season_id,
            source_type=TransactionSourceType.RESERVE_AUTO_COVER,
            direction=TransactionDirection.EXPENSE,
            amount=cover,
            balance_after=team_finance.balance,
            description=f"自动缓冲: {event_type}",
            extra_data={"event_type": event_type, "auto_cover": True},
        )
        self.db.add(transaction)
        await self.db.flush()
        logger.info(f"自动缓冲已执行: team={team_id}, event={event_type}, cover={cover}")
        return transaction

    async def settle_reserve_carryover(
        self,
        team_id: str,
        season_id: str,
    ) -> Optional[FinanceTransaction]:
        """
        赛季末未使用准备金结转。
        """
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        unused_reserve = max(Decimal("0"), season_finance.reserve_budget - season_finance.reserve_spent)
        if unused_reserve <= 0:
            return None

        health = season_finance.financial_health.value
        rate = self.economy.reserve_carryover.rate_by_health.get(health, Decimal("0.50"))
        carryover_amount = _quantize(unused_reserve * rate)

        if carryover_amount <= 0:
            return None

        team_finance = await self._get_team_finance(team_id)
        if team_finance:
            team_finance.balance = _quantize(team_finance.balance + carryover_amount)

        transaction = FinanceTransaction(
            team_id=team_id,
            season_id=season_id,
            source_type=TransactionSourceType.RESERVE_SETTLEMENT,
            direction=TransactionDirection.INCOME,
            amount=carryover_amount,
            balance_after=team_finance.balance if team_finance else Decimal("0"),
            description=f"风险准备金结转 (健康度 {health}, 结转率 {int(rate*100)}%)",
            extra_data={
                "unused_reserve": str(unused_reserve),
                "carryover_rate": str(rate),
                "financial_health": health,
            },
        )
        self.db.add(transaction)
        await self.db.flush()
        logger.info(
            f"准备金结转: team={team_id}, unused={unused_reserve}, "
            f"health={health}, rate={rate}, carryover={carryover_amount}"
        )
        return transaction

    async def get_reserve_status(self, team_id: str, season_id: str) -> Dict:
        """获取球队风险准备金状态"""
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        reserve_budget = season_finance.reserve_budget
        reserve_spent = season_finance.reserve_spent
        reserve_available = max(Decimal("0"), reserve_budget - reserve_spent)

        reserve_usage_pct = 0.0
        if reserve_budget > 0:
            reserve_usage_pct = float(reserve_spent / reserve_budget)

        # 风险等级
        reserve_pct = 0
        budget_plan_result = await self.db.execute(
            select(TeamSeasonFinance.reserve_budget, TeamSeasonFinance.locked_budget_total)
            .where(TeamSeasonFinance.team_id == team_id)
            .where(TeamSeasonFinance.season_id == season_id)
        )
        row = budget_plan_result.one_or_none()
        if row:
            locked_total = row[1] if row[1] > 0 else Decimal("1")
            reserve_pct = int((reserve_budget / locked_total) * 100)

        if reserve_pct <= 4:
            risk_level = "激进"
        elif reserve_pct <= 9:
            risk_level = "标准"
        elif reserve_pct <= 14:
            risk_level = "稳健"
        else:
            risk_level = "保守"

        return {
            "team_id": team_id,
            "season_id": season_id,
            "reserve_budget": reserve_budget,
            "reserve_spent": reserve_spent,
            "reserve_available": reserve_available,
            "reserve_usage_pct": round(reserve_usage_pct, 2),
            "reserve_auto_used": season_finance.reserve_auto_used,
            "reserve_medical_used": season_finance.reserve_medical_used,
            "reserve_events_used": season_finance.reserve_events_used,
            "risk_level": risk_level,
        }

    # =====================================================================
    # 内部计算方法
    # =====================================================================

    def _build_option(
        self,
        plan: TreatmentPlan,
        severity: int,
        remaining_days: int,
        original_total_days: int,
        body_part: str,
        player_value_base: Decimal,
        scarcity_multiplier: Decimal,
        is_gk: bool,
    ) -> Dict:
        """构建单个治疗方案选项"""
        plan_cfg = getattr(self.economy.treatment_plan, plan.value)
        med_cfg = self.economy.medical_cost

        reduction_pct = Decimal(str(plan_cfg["reduction_pct"]))
        max_days = plan_cfg["max_days"]
        cost_multiplier = Decimal(str(plan_cfg["cost_multiplier"]))
        residual_penalty = plan_cfg["residual_wear_penalty"]
        recurrence_bonus = Decimal(str(plan_cfg["recurrence_risk_bonus"]))

        # 缩短天数公式
        raw_reduction = math.ceil(remaining_days * float(reduction_pct))
        day_reduction = min(raw_reduction, max_days)
        minimum_remaining = max(1, math.floor(original_total_days * float(med_cfg.minimum_remaining_pct)))
        actual_reduction = min(day_reduction, remaining_days - minimum_remaining)

        available = actual_reduction > 0

        # 费用公式
        severity_mult = med_cfg.severity_multiplier.get(severity, Decimal("1.0"))
        body_part_mult = med_cfg.body_part_multiplier.get(body_part, Decimal("1.0"))
        if is_gk and body_part in med_cfg.gk_sensitive_parts:
            body_part_mult += med_cfg.gk_body_part_bonus

        days_mult = Decimal(actual_reduction ** med_cfg.days_exponent)
        plan_mult = cost_multiplier

        medical_cost = (
            player_value_base
            * severity_mult
            * body_part_mult
            * scarcity_multiplier
            * days_mult
            * plan_mult
        )
        medical_cost = _round_to_1000(medical_cost)

        plan_labels = {
            TreatmentPlan.ENHANCED: "加强理疗",
            TreatmentPlan.SPECIALIST: "专家会诊",
            TreatmentPlan.AGGRESSIVE: "激进复出",
        }

        return {
            "plan": plan.value,
            "plan_label": plan_labels.get(plan, plan.value),
            "available": available,
            "days_reduced": actual_reduction,
            "days_after": remaining_days - actual_reduction,
            "cost": medical_cost,
            "residual_wear_penalty": residual_penalty,
            "recurrence_risk_bonus": recurrence_bonus,
            "side_effect": self._side_effect_description(plan, residual_penalty, recurrence_bonus),
        }

    def _side_effect_description(self, plan: TreatmentPlan, penalty: int, bonus: Decimal) -> str:
        if plan == TreatmentPlan.ENHANCED:
            return "无明显副作用"
        elif plan == TreatmentPlan.SPECIALIST:
            return "伤愈后该部位复发风险小幅上升"
        elif plan == TreatmentPlan.AGGRESSIVE:
            return "复发风险显著上升，残余劳损增加"
        return ""

    def _calc_player_value_base(self, player: Player, league_level: int) -> Decimal:
        """计算医疗费基础值"""
        med_cfg = self.economy.medical_cost
        market_value = player.market_value or Decimal("0")
        weekly_wage = _quantize(player.wage / Decimal("42")) if player.wage else Decimal("0")
        league_floor = med_cfg.league_floor.get(league_level, Decimal("15000"))

        return max(
            _quantize(market_value * med_cfg.market_value_pct),
            _quantize(weekly_wage * med_cfg.weekly_wage_multiplier),
            league_floor,
        )

    async def _calc_scarcity_multiplier(self, team_id: str, position: PlayerPosition) -> Decimal:
        """计算位置短缺倍率（简化：基于同位置可用球员数）"""
        result = await self.db.execute(
            select(func.count(Player.id))
            .where(Player.team_id == team_id)
            .where(Player.position == position)
            .where(Player.status != "RETIRED")
        )
        count = result.scalar() or 0
        # 如果该位置不足 3 人，短缺倍率上升
        shortage = max(0, 3 - count)
        return Decimal("1.0") + Decimal(str(shortage)) * Decimal("0.15")

    # =====================================================================
    # 数据访问辅助
    # =====================================================================

    async def _get_player(self, player_id: str) -> Optional[Player]:
        result = await self.db.execute(select(Player).where(Player.id == player_id))
        return result.scalar_one_or_none()

    async def _get_team_finance(self, team_id: str) -> Optional[TeamFinance]:
        result = await self.db.execute(select(TeamFinance).where(TeamFinance.team_id == team_id))
        return result.scalar_one_or_none()

    async def _get_or_create_team_season_finance(
        self, team_id: str, season_id: str
    ) -> TeamSeasonFinance:
        result = await self.db.execute(
            select(TeamSeasonFinance)
            .where(TeamSeasonFinance.team_id == team_id)
            .where(TeamSeasonFinance.season_id == season_id)
        )
        season_finance = result.scalar_one_or_none()
        if not season_finance:
            season_finance = TeamSeasonFinance(team_id=team_id, season_id=season_id)
            self.db.add(season_finance)
            await self.db.flush()
        return season_finance

    async def _get_team_league_level(self, team_id: str) -> int:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team or not team.current_league_id:
            return 4
        result = await self.db.execute(select(League.level).where(League.id == team.current_league_id))
        level = result.scalar_one_or_none()
        return level or 4

    async def _get_current_season_id(self, team_id: str) -> Optional[str]:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if team and team.current_season_id:
            return team.current_season_id
        from app.models.season import Season
        result = await self.db.execute(select(Season).order_by(Season.season_number.desc()).limit(1))
        season = result.scalar_one_or_none()
        return season.id if season else None

    # =====================================================================
    # AI 决策规则 (EMERGENCY-FUND-INJURY-FINANCE-DESIGN.md §10)
    # =====================================================================

    async def ai_evaluate_and_treat(
        self,
        team_id: str,
        player: Player,
        season_id: str,
    ) -> Optional[Dict]:
        """
        AI 对单个受伤球员的治疗决策。
        返回治疗结果，若决定不治疗则返回 None。
        """
        injury = player.current_injury
        if not injury or injury.get("treatment_applied", False):
            return None

        severity = injury.get("severity", 0)
        if severity < 2:
            return None  # 轻伤不治疗

        remaining_days = injury.get("remaining_days", 0)
        if remaining_days < 3:
            return None  # 快好了，不值得治

        # 获取球队财务健康
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        health = season_finance.financial_health.value
        reserve_available = max(Decimal("0"), season_finance.reserve_budget - season_finance.reserve_spent)

        # 获取阵容深度
        roster_count = await self._get_active_roster_count(team_id)
        same_position_count = await self._get_same_position_available_count(team_id, player.position)

        # 1. 计算球员重要性分 (0-40)
        player_importance = self._calc_ai_player_importance(player, roster_count, same_position_count)

        # 2. 赛程重要性分 (0-25) — 简化：按 remaining_days 估算
        schedule_importance = 10 if remaining_days >= 5 else 5

        # 3. 升降级压力分 (0-20) — 简化用 random 模拟赛季中段压力
        promotion_pressure = 10

        # 4. 财政风险分 (0-30)
        financial_risk = 0
        if health == "D":
            financial_risk = 25
        elif health == "C":
            financial_risk = 15
        if reserve_available < Decimal("50000"):
            financial_risk += 10

        # 5. 复发风险分 (0-15)
        recurrence_risk = 0

        score = player_importance + schedule_importance + promotion_pressure - financial_risk - recurrence_risk

        # 决策阈值
        # 财政健康 C/D 只允许加强理疗，除非阵容不足 8 人
        allow_specialist = True
        allow_aggressive = False
        if health in ("C", "D"):
            allow_specialist = False
        if roster_count < 8:
            allow_specialist = True  # 阵容严重不足时放开

        # 关键比赛 / 决赛 / 保级生死战 才允许激进复出
        # 简化：score >= 45 视为关键战需求
        if score >= 45 and health not in ("D",):
            allow_aggressive = True

        # 获取可选方案
        injury_record_id = injury.get("created_at", "")
        options = await self.list_treatment_options(team_id, player.id, injury_record_id)
        if not options:
            return None

        # 按优先级选方案
        chosen_plan = None
        if score >= 50 and allow_aggressive:
            # 激进复出（极少使用）
            for opt in options:
                if opt["plan"] == "aggressive" and opt["available"]:
                    chosen_plan = TreatmentPlan.AGGRESSIVE
                    break

        if chosen_plan is None and score >= 35 and allow_specialist:
            # 专家会诊
            for opt in options:
                if opt["plan"] == "specialist" and opt["available"]:
                    # 检查费用是否超过准备金的 80%
                    if opt["cost"] <= reserve_available * Decimal("0.80"):
                        chosen_plan = TreatmentPlan.SPECIALIST
                        break

        if chosen_plan is None and score >= 15:
            # 加强理疗（最保守）
            for opt in options:
                if opt["plan"] == "enhanced" and opt["available"]:
                    chosen_plan = TreatmentPlan.ENHANCED
                    break

        if chosen_plan is None:
            return None

        try:
            result = await self.apply_treatment(team_id, player.id, injury_record_id, chosen_plan)
            logger.info(
                f"AI 治疗决策: team={team_id}, player={player.id}, "
                f"plan={chosen_plan.value}, score={score}, importance={player_importance}"
            )
            return result
        except Exception as e:
            logger.warning(f"AI 治疗执行失败: team={team_id}, player={player.id}, error={e}")
            return None

    def _calc_ai_player_importance(self, player: Player, roster_count: int, same_position_count: int) -> int:
        """计算 AI 视角的球员重要性分 (0-40)"""
        score = 0
        # OVR 分
        if player.ovr >= 80:
            score += 20
        elif player.ovr >= 70:
            score += 15
        elif player.ovr >= 60:
            score += 10
        else:
            score += 5

        # 角色分
        role_scores = {
            "key_player": 10,
            "first_team": 7,
            "rotation": 4,
            "backup": 2,
            "hot_prospect": 3,
            "youngster": 1,
            "not_needed": 0,
        }
        role = player.squad_role.value if hasattr(player.squad_role, "value") else str(player.squad_role)
        score += role_scores.get(role, 0)

        # 位置稀缺分
        if same_position_count <= 1:
            score += 10  # 该位置只有 0-1 人可用，极度重要
        elif same_position_count <= 2:
            score += 5

        return min(score, 40)

    async def _get_active_roster_count(self, team_id: str) -> int:
        """获取球队当前可用人数（非退役）"""
        from app.models.player import PlayerStatus
        result = await self.db.execute(
            select(func.count(Player.id))
            .where(Player.team_id == team_id)
            .where(Player.status != PlayerStatus.RETIRED)
        )
        return result.scalar() or 0

    async def _get_same_position_available_count(self, team_id: str, position: PlayerPosition) -> int:
        """获取同位置可用球员数（非伤病/停赛）"""
        from app.models.player import PlayerStatus
        result = await self.db.execute(
            select(func.count(Player.id))
            .where(Player.team_id == team_id)
            .where(Player.position == position)
            .where(Player.status == PlayerStatus.ACTIVE)
        )
        return result.scalar() or 0
