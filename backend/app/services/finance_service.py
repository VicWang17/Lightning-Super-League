"""
Finance service - 经济系统业务逻辑服务
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.models.finance import (
    FinanceTransaction,
    TransactionSourceType,
    TransactionDirection,
    TeamSeasonFinance,
    FinancialHealth,
    OverspendLevel,
    BudgetPolicy,
    SponsorPolicy,
    SponsorContractStatus,
    TeamBudgetPlan,
    SponsorContract,
)
from app.models.team import TeamFinance, Team
from app.models.season import Season, Fixture, FixtureType, FixtureStatus
from app.models.league import League, LeagueStanding
from app.models.player import Player, PlayerStatus
from app.models.mail import Mail, MailCategory, MailPriority
from app.models.user import User
from app.core.logging import get_logger
from app.core.economy_config import get_economy_config
import random

logger = get_logger("app.finance")

MONEY_QUANT = Decimal("0.01")
PERFORMANCE_SPONSOR_BASE_RATE = Decimal("0.60")
PERFORMANCE_SPONSOR_WIN_RATE = Decimal("0.09")
PERFORMANCE_SPONSOR_DRAW_RATE = Decimal("0.03")
PERFORMANCE_SPONSOR_MAX_BONUS_RATE = Decimal("1.25")
SEASON_BUDGET_CASH_RESERVE_ACCESS_RATE = Decimal("0.10")


def quantize_money(value: Decimal | int | float | str) -> Decimal:
    """Normalize money before persisting to DECIMAL(..., 2) columns."""
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


# 预算策略预设
BUDGET_PRESETS: Dict[BudgetPolicy, Dict[str, int]] = {
    BudgetPolicy.BALANCED: {"transfer": 25, "youth": 10, "wage": 55, "reserve": 10},
    BudgetPolicy.YOUTH_FOCUS: {"transfer": 18, "youth": 22, "wage": 47, "reserve": 13},
    BudgetPolicy.TRANSFER_PUSH: {"transfer": 35, "youth": 8, "wage": 52, "reserve": 5},
    BudgetPolicy.WAGE_CONTROL: {"transfer": 18, "youth": 8, "wage": 62, "reserve": 12},
}


class FinanceService:
    """财务服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.economy = get_economy_config()
    
    # =====================================================================
    # Phase 1: 核心交易与概览
    # =====================================================================
    
    async def apply_transaction(
        self,
        team_id: str,
        season_id: str,
        source_type: TransactionSourceType,
        direction: TransactionDirection,
        amount: Decimal,
        description: str,
        extra_data: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> FinanceTransaction:
        """应用财务交易（幂等）"""
        amount = quantize_money(amount)
        txn_extra = dict(extra_data) if extra_data else {}
        if idempotency_key:
            txn_extra["idempotency_key"] = idempotency_key
        
        if txn_extra.get("idempotency_key"):
            existing = await self._find_transaction_by_idempotency(
                team_id, season_id, source_type, txn_extra["idempotency_key"]
            )
            if existing:
                logger.info(f"幂等返回已存在交易: {existing.id}")
                return existing
        
        team_finance = await self._get_team_finance(team_id)
        if not team_finance:
            raise ValueError(f"Team finance not found for team {team_id}")
        
        if direction == TransactionDirection.INCOME:
            new_balance = team_finance.balance + amount
        else:
            new_balance = team_finance.balance - amount
        new_balance = quantize_money(new_balance)
        
        transaction = FinanceTransaction(
            team_id=team_id,
            season_id=season_id,
            source_type=source_type,
            direction=direction,
            amount=amount,
            balance_after=new_balance,
            description=description,
            extra_data=txn_extra,
        )
        self.db.add(transaction)
        team_finance.balance = new_balance
        
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        season_finance.current_balance = new_balance
        
        await self.db.flush()
        logger.info(f"交易已应用: {transaction.id}, team={team_id}, {direction.value}={amount}")
        return transaction
    
    async def get_overview(self, team_id: str, season_id: Optional[str] = None) -> Dict:
        """获取财务概览"""
        target_season_id = season_id
        if not target_season_id:
            season = await self._get_current_season_for_team(team_id)
            if season:
                target_season_id = season.id
        
        if not target_season_id:
            raise ValueError("No season found for team")
        
        season_finance = await self._get_or_create_team_season_finance(team_id, target_season_id)
        team_finance = await self._get_team_finance(team_id)
        stats = await self._aggregate_season_transactions(team_id, target_season_id)
        
        wage_cap = season_finance.wage_cap if season_finance.wage_cap > 0 else Decimal("1")
        wage_bill = season_finance.wage_bill
        wage_pressure_pct = int((wage_bill / wage_cap) * 100) if wage_cap > 0 else 0
        
        if wage_pressure_pct <= 90:
            wage_status = "normal"
        elif wage_pressure_pct <= 100:
            wage_status = "warning"
        else:
            wage_status = "exceeded"
        
        current_balance = team_finance.balance if team_finance else season_finance.current_balance
        
        # Phase 3: 获取预算计划和赞助合同
        budget_plan = await self._get_budget_plan(team_id, target_season_id)
        sponsor_contract = await self._get_active_sponsor_contract(team_id, target_season_id)
        
        return {
            "team_id": team_id,
            "season_id": target_season_id,
            "current_balance": current_balance,
            "opening_balance": season_finance.opening_balance,
            "projected_income": season_finance.projected_income,
            "projected_expense": season_finance.projected_expense,
            "locked_budget_total": season_finance.locked_budget_total,
            "transfer_budget": season_finance.transfer_budget,
            "youth_budget": season_finance.youth_budget,
            "wage_budget": season_finance.wage_budget,
            "reserve_budget": season_finance.reserve_budget,
            "total_income": stats["total_income"],
            "total_expense": stats["total_expense"],
            "income_breakdown": stats["income_breakdown"],
            "expense_breakdown": stats["expense_breakdown"],
            "wage_cap_info": {
                "wage_cap": season_finance.wage_cap,
                "wage_bill": wage_bill,
                "wage_pressure_pct": wage_pressure_pct,
                "status": wage_status,
            },
            "financial_health": season_finance.financial_health.value,
            "overspend_level": season_finance.overspend_level.value,
            "budget_locked": season_finance.budget_locked_at is not None,
            "budget_locked_at": season_finance.budget_locked_at,
            "budget_plan": {
                "team_id": team_id,
                "target_season_id": target_season_id,
                "policy": budget_plan.policy.value if budget_plan else "balanced",
                "transfer_pct": budget_plan.transfer_pct if budget_plan else 25,
                "youth_pct": budget_plan.youth_pct if budget_plan else 10,
                "wage_pct": budget_plan.wage_pct if budget_plan else 55,
                "reserve_pct": budget_plan.reserve_pct if budget_plan else 10,
                "is_player_confirmed": budget_plan.is_player_confirmed if budget_plan else False,
                "locked_at": budget_plan.locked_at if budget_plan else None,
            } if budget_plan else None,
            "sponsor_contract": {
                "team_id": team_id,
                "season_id": target_season_id,
                "policy": sponsor_contract.policy.value,
                "base_amount": sponsor_contract.base_amount,
                "win_bonus": sponsor_contract.win_bonus,
                "draw_bonus": sponsor_contract.draw_bonus,
                "max_bonus": sponsor_contract.max_bonus,
                "health_modifier_pct": sponsor_contract.health_modifier_pct,
                "status": sponsor_contract.status.value,
            } if sponsor_contract else None,
        }
    
    async def get_transactions(
        self,
        team_id: str,
        season_id: Optional[str] = None,
        source_type: Optional[TransactionSourceType] = None,
        direction: Optional[TransactionDirection] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict:
        """获取交易列表（分页）"""
        query = select(FinanceTransaction).where(FinanceTransaction.team_id == team_id)
        
        if season_id:
            query = query.where(FinanceTransaction.season_id == season_id)
        if source_type:
            query = query.where(FinanceTransaction.source_type == source_type)
        if direction:
            query = query.where(FinanceTransaction.direction == direction)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.order_by(desc(FinanceTransaction.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        transactions = result.scalars().all()
        
        return {
            "items": list(transactions),
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }
    
    # =====================================================================
    # Phase 2: 赛季经济事件
    # =====================================================================
    
    async def initialize_season_finance(
        self,
        team_id: str,
        season_id: str,
    ) -> TeamSeasonFinance:
        """初始化赛季财务快照（Phase 5 增强版：扣除青训预算、应用赞助修正）"""
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        
        if season_finance.opening_balance > 0:
            existing_txns = await self.db.execute(
                select(FinanceTransaction)
                .where(FinanceTransaction.team_id == team_id)
                .where(FinanceTransaction.season_id == season_id)
                .where(FinanceTransaction.source_type == TransactionSourceType.BROADCAST)
            )
            if existing_txns.scalar_one_or_none():
                return season_finance
        
        team_finance = await self._get_team_finance(team_id)
        opening_balance = team_finance.balance if team_finance else Decimal("10000000")
        
        league_level = await self._get_team_league_level(team_id)

        await self._ensure_budget_and_sponsor_before_finance_init(team_id, season_id, league_level)
        
        # Phase 5: 使用有效赞助基础金额（应用 health modifier + crisis penalty）
        sponsor_contract = await self._get_active_sponsor_contract(team_id, season_id)
        if sponsor_contract:
            sponsor_income = await self.get_effective_sponsor_base(
                team_id, season_id, sponsor_contract.base_amount
            )
        else:
            base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
            sponsor_income = await self.get_effective_sponsor_base(team_id, season_id, base)
        
        broadcast_income = self._calculate_broadcast_income(league_level)
        season_ticket_income = self._calculate_season_ticket_income(league_level)
        projected_income = broadcast_income + sponsor_income + season_ticket_income
        
        wage_bill = await self._calculate_team_wage_bill(team_id)
        projected_expense = wage_bill
        
        # Phase 3: 预算总额使用赛季经营收入 + 少量现金储备。
        # 青训预算会真实扣款，如果直接按全部现金余额分配，会导致球队越有钱每季烧钱越多。
        locked_total = projected_income + opening_balance * SEASON_BUDGET_CASH_RESERVE_ACCESS_RATE
        budget_plan = await self._get_budget_plan(team_id, season_id)
        if budget_plan and budget_plan.locked_at:
            transfer_pct = budget_plan.transfer_pct
            youth_pct = budget_plan.youth_pct
            wage_pct = budget_plan.wage_pct
            reserve_pct = budget_plan.reserve_pct
        else:
            transfer_pct = self.economy.budget.default_transfer_pct
            youth_pct = self.economy.budget.default_youth_pct
            wage_pct = self.economy.budget.default_wage_pct
            reserve_pct = self.economy.budget.default_reserve_pct
        
        # Phase 5: crisis 球队强制 youth 预算为 5%
        if season_finance.overspend_level == OverspendLevel.CRISIS:
            youth_pct = self.economy.budget.youth_min_pct
        
        season_finance.opening_balance = quantize_money(opening_balance)
        season_finance.current_balance = quantize_money(opening_balance)
        season_finance.projected_income = quantize_money(projected_income)
        season_finance.projected_expense = quantize_money(projected_expense)
        season_finance.locked_budget_total = quantize_money(locked_total)
        season_finance.transfer_budget = quantize_money(locked_total * Decimal(str(transfer_pct)) / Decimal("100"))
        season_finance.youth_budget = quantize_money(locked_total * Decimal(str(youth_pct)) / Decimal("100"))
        season_finance.wage_budget = quantize_money(locked_total * Decimal(str(wage_pct)) / Decimal("100"))
        season_finance.reserve_budget = quantize_money(locked_total * Decimal(str(reserve_pct)) / Decimal("100"))
        
        health = season_finance.financial_health.value
        season_finance.wage_cap = self._calculate_wage_cap(league_level, health)
        season_finance.wage_bill = quantize_money(wage_bill)
        
        await self.db.flush()
        
        # 发放赛季初收入
        await self.apply_transaction(
            team_id, season_id,
            TransactionSourceType.BROADCAST, TransactionDirection.INCOME,
            broadcast_income, "赛季转播收入",
            idempotency_key=f"broadcast_{season_id}"
        )
        await self.apply_transaction(
            team_id, season_id,
            TransactionSourceType.SPONSOR, TransactionDirection.INCOME,
            sponsor_income, "商业赞助收入",
            idempotency_key=f"sponsor_{season_id}"
        )
        await self.apply_transaction(
            team_id, season_id,
            TransactionSourceType.MANUAL_ADJUSTMENT, TransactionDirection.INCOME,
            season_ticket_income, "赛季套票收入",
            extra_data={"income_type": "season_ticket"},
            idempotency_key=f"season_ticket_{season_id}"
        )
        
        # Phase 5: 扣除青训预算
        await self._deduct_youth_budget(team_id, season_id, season_finance.youth_budget)
        
        await self.db.flush()
        logger.info(
            f"赛季财务已初始化: team={team_id}, season={season_id}, "
            f"broadcast={broadcast_income}, sponsor={sponsor_income}, "
            f"season_ticket={season_ticket_income}, youth_deducted={season_finance.youth_budget}"
        )
        return season_finance
    
    async def settle_match_finance(self, fixture_id: str) -> None:
        """比赛财务结算（Phase 5 增强：performance sponsor 应用 effective base）"""
        result = await self.db.execute(
            select(Fixture).where(Fixture.id == fixture_id)
        )
        fixture = result.scalar_one_or_none()
        if not fixture or fixture.status != FixtureStatus.FINISHED:
            return
        
        # 杯赛参与奖金
        if fixture.fixture_type in (
            FixtureType.CUP_LIGHTNING_GROUP,
            FixtureType.CUP_LIGHTNING_KNOCKOUT,
            FixtureType.CUP_JENNY,
        ):
            cup_bonus = Decimal("5000")
            for team_id in (fixture.home_team_id, fixture.away_team_id):
                await self.apply_transaction(
                    team_id, fixture.season_id,
                    TransactionSourceType.CUP_PRIZE, TransactionDirection.INCOME,
                    cup_bonus, "杯赛参与奖金",
                    idempotency_key=f"cup_bonus_{fixture_id}_{team_id}"
                )
        
        # Phase 3/5: 绩效赞助商比赛奖金（应用 effective sponsor base 修正）
        for team_id in (fixture.home_team_id, fixture.away_team_id):
            sponsor_contract = await self._get_active_sponsor_contract(team_id, fixture.season_id)
            if sponsor_contract and sponsor_contract.policy == SponsorPolicy.PERFORMANCE:
                # Phase 5: 应用 effective base 修正到奖金
                effective_base = await self.get_effective_sponsor_base(
                    team_id, fixture.season_id, sponsor_contract.base_amount
                )
                base_ratio = effective_base / sponsor_contract.base_amount if sponsor_contract.base_amount > 0 else Decimal("1")
                
                bonus = Decimal("0")
                is_home = fixture.home_team_id == team_id
                team_score = fixture.home_score if is_home else fixture.away_score
                opponent_score = fixture.away_score if is_home else fixture.home_score
                
                if team_score > opponent_score:
                    bonus = sponsor_contract.win_bonus * base_ratio
                elif team_score == opponent_score:
                    bonus = sponsor_contract.draw_bonus * base_ratio
                
                if bonus > 0:
                    # 检查是否超过 max_bonus
                    total_bonus_result = await self.db.execute(
                        select(func.sum(FinanceTransaction.amount))
                        .where(FinanceTransaction.team_id == team_id)
                        .where(FinanceTransaction.season_id == fixture.season_id)
                        .where(FinanceTransaction.source_type == TransactionSourceType.SPONSOR)
                        .where(FinanceTransaction.direction == TransactionDirection.INCOME)
                        .where(FinanceTransaction.extra_data["sponsor_bonus"].as_boolean() == True)
                    )
                    total_bonus = total_bonus_result.scalar() or Decimal("0")
                    remaining = sponsor_contract.max_bonus - total_bonus
                    bonus = min(bonus, remaining)
                    
                    if bonus > 0:
                        await self.apply_transaction(
                            team_id, fixture.season_id,
                            TransactionSourceType.SPONSOR, TransactionDirection.INCOME,
                            bonus, "赞助商绩效奖金",
                            extra_data={"sponsor_bonus": True, "fixture_id": fixture_id},
                            idempotency_key=f"sponsor_bonus_{fixture_id}_{team_id}"
                        )
        
        await self.db.flush()
    
    async def pay_wages(self, season_id: str, period_key: str) -> None:
        """工资发放"""
        result = await self.db.execute(
            select(Team).where(Team.current_season_id == season_id)
        )
        teams = result.scalars().all()
        
        if not teams:
            result = await self.db.execute(
                select(Fixture.home_team_id, Fixture.away_team_id)
                .where(Fixture.season_id == season_id)
                .distinct()
            )
            team_ids = set()
            for row in result.all():
                team_ids.add(row[0])
                team_ids.add(row[1])
            if not team_ids:
                return
            result = await self.db.execute(select(Team).where(Team.id.in_(list(team_ids))))
            teams = result.scalars().all()
        
        payment_count = self.economy.wage.payments_per_season
        
        for team in teams:
            season_finance = await self._get_or_create_team_season_finance(team.id, season_id)
            # 每次发放都重新计算当前在队球员工资总额（支持赛季中签约/解约实时反映）
            wage_bill = await self._calculate_team_wage_bill(team.id)
            season_finance.wage_bill = wage_bill
            
            if wage_bill <= 0:
                continue
            
            payment_amount = wage_bill / Decimal(payment_count)
            
            await self.apply_transaction(
                team.id, season_id,
                TransactionSourceType.WAGE, TransactionDirection.EXPENSE,
                payment_amount, f"工资发放 ({period_key})",
                idempotency_key=f"wage_{season_id}_{period_key}_{team.id}"
            )
            
            # Phase 4: 工资发放后检查超支并发送警告
            await self._check_overspend_and_notify(team.id, season_id)
        
        await self.db.flush()
        logger.info(f"工资发放完成: season={season_id}, period={period_key}, teams={len(teams)}")
    
    async def close_season_finance(self, season_id: str) -> None:
        """赛季财务结算"""
        result = await self.db.execute(
            select(TeamSeasonFinance).where(TeamSeasonFinance.season_id == season_id)
        )
        season_finances = result.scalars().all()
        
        for season_finance in season_finances:
            team_id = season_finance.team_id
            
            prize = await self._calculate_league_prize(team_id, season_id)
            if prize > 0:
                await self.apply_transaction(
                    team_id, season_id,
                    TransactionSourceType.LEAGUE_PRIZE, TransactionDirection.INCOME,
                    prize, "赛季联赛排名奖金",
                    idempotency_key=f"league_prize_{season_id}_{team_id}"
                )
            
            stats = await self._aggregate_season_transactions(team_id, season_id)
            net_income = stats["total_income"] - stats["total_expense"]
            season_finance.current_balance = season_finance.opening_balance + net_income
            
            health = await self._calculate_financial_health(season_finance)
            season_finance.financial_health = health
            await self._update_overspend_level(season_finance)
            
            # Phase 4: 发送赛季财务总结邮件
            await self._send_season_summary_mail(team_id, season_id, season_finance, stats)
        
        await self.db.flush()
        logger.info(f"赛季财务结算完成: season={season_id}, teams={len(season_finances)}")
    
    # =====================================================================
    # Phase 3: 预算与赞助商决策
    # =====================================================================
    
    async def open_budget_window(self, season_id: str) -> Dict:
        """预算窗口打开（BUDGET_WINDOW_OPENED）
        
        为所有球队生成默认预算计划和赞助商选项：
        - AI 球队：自动确认预算（balanced）和赞助商（stable）
        - 人类球队：发送邮件通知，等待手动确认
        """
        result = await self.db.execute(select(Season).where(Season.id == season_id))
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")
        
        # 获取本赛季所有球队
        result = await self.db.execute(
            select(Fixture.home_team_id, Fixture.away_team_id)
            .where(Fixture.season_id == season_id)
            .distinct()
        )
        team_ids = set()
        for row in result.all():
            team_ids.add(row[0])
            team_ids.add(row[1])
        
        created_budgets = 0
        created_sponsors = 0
        ai_auto_decisions = 0
        human_mails_sent = 0
        
        for team_id in team_ids:
            # 生成默认预算计划
            budget_plan = await self._get_or_create_budget_plan(team_id, season_id)
            if not budget_plan.is_player_confirmed:
                preset = BUDGET_PRESETS[BudgetPolicy.BALANCED]
                budget_plan.policy = BudgetPolicy.BALANCED
                budget_plan.transfer_pct = preset["transfer"]
                budget_plan.youth_pct = preset["youth"]
                budget_plan.wage_pct = preset["wage"]
                budget_plan.reserve_pct = preset["reserve"]
                created_budgets += 1
            
            # Phase 5: crisis 球队强制 youth 预算为最小值 5%
            season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
            if season_finance.overspend_level == OverspendLevel.CRISIS:
                excess = max(0, budget_plan.youth_pct - self.economy.budget.youth_min_pct)
                budget_plan.youth_pct = self.economy.budget.youth_min_pct
                # 重新平衡：从 transfer 和 reserve 中扣除，保持总和 100
                budget_plan.transfer_pct = max(0, budget_plan.transfer_pct - excess // 2)
                budget_plan.reserve_pct = max(0, budget_plan.reserve_pct - excess + excess // 2)
                # 最终确保 wage 吸收余量，保证总和为 100
                total = budget_plan.transfer_pct + budget_plan.youth_pct + budget_plan.wage_pct + budget_plan.reserve_pct
                if total != 100:
                    budget_plan.wage_pct += 100 - total
            
            # 生成默认赞助商选项（stable，pending）
            sponsor = await self._get_active_sponsor_contract(team_id, season_id)
            if not sponsor:
                league_level = await self._get_team_league_level(team_id)
                base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
                sponsor = SponsorContract(
                    team_id=team_id,
                    season_id=season_id,
                    policy=SponsorPolicy.STABLE,
                    base_amount=base,
                    status=SponsorContractStatus.PENDING,
                )
                self.db.add(sponsor)
                created_sponsors += 1
            
            is_ai = await self._is_ai_team(team_id)
            if is_ai:
                # AI 自动决策
                await self._auto_ai_budget_decision(team_id, season_id)
                ai_auto_decisions += 1
            else:
                # 人类玩家发送通知邮件
                await self._send_finance_mail(
                    team_id, season_id,
                    category=MailCategory.FINANCE,
                    priority=MailPriority.HIGH,
                    subject="【重要】下赛季预算规划窗口已开启",
                    body="董事会已开启下赛季预算规划窗口，请尽快前往财务中心制定预算分配方案。\n\n"
                         "默认方案为「均衡发展」：转会25% / 青训10% / 工资55% / 储备10%。\n\n"
                         "同时请确认下赛季赞助商策略：稳定型赞助商收入固定，绩效型赞助商根据比赛结果浮动。\n\n"
                         "窗口将在几天后关闭，逾期未设置将自动应用推荐方案。",
                    related_url=f"/finance/budget?target_season_id={season_id}",
                    action_label="前往规划",
                )
                human_mails_sent += 1
        
        await self.db.flush()
        logger.info(
            f"预算窗口已打开: season={season_id}, "
            f"budgets={created_budgets}, sponsors={created_sponsors}, "
            f"ai_auto={ai_auto_decisions}, human_mails={human_mails_sent}"
        )
        return {
            "season_id": season_id,
            "teams": len(team_ids),
            "budgets_created": created_budgets,
            "sponsors_created": created_sponsors,
            "ai_auto_decisions": ai_auto_decisions,
            "human_mails_sent": human_mails_sent,
        }
    
    async def close_budget_window(self, season_id: str) -> Dict:
        """预算窗口关闭（BUDGET_WINDOW_CLOSED）
        
        锁定所有未确认的预算计划，自动选择默认赞助商。
        向被自动处理的人类玩家发送通知邮件。
        """
        result = await self.db.execute(select(Season).where(Season.id == season_id))
        season = result.scalar_one_or_none()
        if not season:
            raise ValueError(f"Season not found: {season_id}")
        
        # 锁定所有未确认的预算计划
        result = await self.db.execute(
            select(TeamBudgetPlan).where(TeamBudgetPlan.target_season_id == season_id)
        )
        budget_plans = result.scalars().all()
        
        locked_count = 0
        auto_locked_teams = []  # 记录被自动锁定的球队（用于发邮件）
        
        for plan in budget_plans:
            if not plan.locked_at:
                plan.locked_at = datetime.utcnow()
                if not plan.is_player_confirmed:
                    preset = BUDGET_PRESETS.get(plan.policy, BUDGET_PRESETS[BudgetPolicy.BALANCED])
                    plan.transfer_pct = preset["transfer"]
                    plan.youth_pct = preset["youth"]
                    plan.wage_pct = preset["wage"]
                    plan.reserve_pct = preset["reserve"]
                    auto_locked_teams.append(plan.team_id)
                locked_count += 1
        
        # 锁定所有未签署的赞助商合同（默认 stable）
        result = await self.db.execute(
            select(SponsorContract)
            .where(SponsorContract.season_id == season_id)
            .where(SponsorContract.status == SponsorContractStatus.PENDING)
        )
        pending_sponsors = result.scalars().all()
        
        for sponsor in pending_sponsors:
            sponsor.status = SponsorContractStatus.ACTIVE
            if sponsor.team_id not in auto_locked_teams:
                auto_locked_teams.append(sponsor.team_id)
        
        # 向被自动处理的人类玩家发送通知
        for team_id in auto_locked_teams:
            is_ai = await self._is_ai_team(team_id)
            if not is_ai:
                await self._send_finance_mail(
                    team_id, season_id,
                    category=MailCategory.FINANCE,
                    priority=MailPriority.NORMAL,
                    subject="下赛季预算计划已自动锁定",
                    body="预算规划窗口已关闭。由于您未在截止前确认方案，系统已自动为您应用推荐方案：\n\n"
                         "预算策略：均衡发展（转会25% / 青训10% / 工资55% / 储备10%）\n"
                         "赞助商：稳定型赞助商\n\n"
                         "新赛季开始后，您可以在财务中心查看详细预算分配。",
                    related_url="/finance",
                    action_label="查看财务",
                )
        
        await self.db.flush()
        logger.info(f"预算窗口已关闭: season={season_id}, locked={locked_count}, auto_sponsors={len(pending_sponsors)}")
        return {
            "season_id": season_id,
            "budgets_locked": locked_count,
            "sponsors_activated": len(pending_sponsors),
            "auto_locked_teams": len(auto_locked_teams),
        }
    
    async def confirm_budget_plan(
        self,
        team_id: str,
        target_season_id: str,
        policy: BudgetPolicy,
        transfer_pct: int,
        youth_pct: int,
        wage_pct: int,
        reserve_pct: int,
    ) -> TeamBudgetPlan:
        """球员确认预算计划"""
        if transfer_pct + youth_pct + wage_pct + reserve_pct != 100:
            raise ValueError("预算分配百分比总和必须等于 100")
        
        budget_plan = await self._get_or_create_budget_plan(team_id, target_season_id)
        
        if budget_plan.locked_at:
            raise ValueError("预算计划已锁定，无法修改")
        
        budget_plan.policy = policy
        budget_plan.transfer_pct = transfer_pct
        budget_plan.youth_pct = youth_pct
        budget_plan.wage_pct = wage_pct
        budget_plan.reserve_pct = reserve_pct
        budget_plan.is_player_confirmed = True
        
        await self.db.flush()
        logger.info(f"预算计划已确认: team={team_id}, policy={policy.value}")
        return budget_plan
    
    async def get_budget_plan(self, team_id: str, target_season_id: str) -> Optional[TeamBudgetPlan]:
        """获取预算计划"""
        result = await self.db.execute(
            select(TeamBudgetPlan)
            .where(TeamBudgetPlan.team_id == team_id)
            .where(TeamBudgetPlan.target_season_id == target_season_id)
        )
        return result.scalar_one_or_none()
    
    async def generate_sponsor_options(self, team_id: str, season_id: str) -> List[Dict]:
        """生成赞助商选项"""
        league_level = await self._get_team_league_level(team_id)
        base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
        
        # Stable
        stable_amount = base
        
        # Performance
        perf_base = base * PERFORMANCE_SPONSOR_BASE_RATE
        perf_win = base * PERFORMANCE_SPONSOR_WIN_RATE
        perf_draw = base * PERFORMANCE_SPONSOR_DRAW_RATE
        perf_max = base * PERFORMANCE_SPONSOR_MAX_BONUS_RATE
        
        # 估算 performance 的期望收入（假设 50% 胜率，14 场联赛 + 杯赛）
        expected_matches = 20
        expected_wins = int(expected_matches * 0.5)
        expected_draws = int(expected_matches * 0.2)
        expected_perf = perf_base + (perf_win * expected_wins) + (perf_draw * expected_draws)
        expected_perf = min(expected_perf, perf_base + perf_max)
        
        return [
            {
                "policy": SponsorPolicy.STABLE.value,
                "label": "稳定赞助商",
                "base_amount": stable_amount,
                "win_bonus": Decimal("0"),
                "draw_bonus": Decimal("0"),
                "max_bonus": Decimal("0"),
                "description": f"固定收入 {int(stable_amount / 10000)}万，不受比赛结果影响。适合追求稳健的球队。",
            },
            {
                "policy": SponsorPolicy.PERFORMANCE.value,
                "label": "绩效赞助商",
                "base_amount": perf_base,
                "win_bonus": perf_win,
                "draw_bonus": perf_draw,
                "max_bonus": perf_max,
                "description": f"基础收入较低（{int(perf_base / 10000)}万），但比赛奖金丰厚。预计总收入约 {int(expected_perf / 10000)}万。适合有竞争力的球队。",
            },
        ]
    
    async def sign_sponsor_contract(
        self,
        team_id: str,
        season_id: str,
        policy: SponsorPolicy,
    ) -> SponsorContract:
        """签署赞助合同"""
        # 检查是否已有活跃合同
        existing = await self._get_active_sponsor_contract(team_id, season_id)
        if existing and existing.status == SponsorContractStatus.ACTIVE:
            raise ValueError("本赛季已有生效的赞助合同")
        
        league_level = await self._get_team_league_level(team_id)
        base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
        
        if policy == SponsorPolicy.STABLE:
            contract = SponsorContract(
                team_id=team_id,
                season_id=season_id,
                policy=SponsorPolicy.STABLE,
                base_amount=base,
                status=SponsorContractStatus.ACTIVE,
            )
        else:
            contract = SponsorContract(
                team_id=team_id,
                season_id=season_id,
                policy=SponsorPolicy.PERFORMANCE,
                base_amount=base * PERFORMANCE_SPONSOR_BASE_RATE,
                win_bonus=base * PERFORMANCE_SPONSOR_WIN_RATE,
                draw_bonus=base * PERFORMANCE_SPONSOR_DRAW_RATE,
                max_bonus=base * PERFORMANCE_SPONSOR_MAX_BONUS_RATE,
                status=SponsorContractStatus.ACTIVE,
            )
        
        self.db.add(contract)
        await self.db.flush()
        logger.info(f"赞助合同已签署: team={team_id}, policy={policy.value}")
        return contract
    
    async def recalculate_team_finance(self, team_id: str, season_id: str) -> Dict:
        """重新计算球队财务数据"""
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        team_finance = await self._get_team_finance(team_id)
        
        stats = await self._aggregate_season_transactions(team_id, season_id)
        net_income = stats["total_income"] - stats["total_expense"]
        recalculated_balance = season_finance.opening_balance + net_income
        
        season_finance.current_balance = recalculated_balance
        if team_finance:
            team_finance.balance = recalculated_balance
        
        await self._update_overspend_level(season_finance)
        await self.db.flush()
        
        return await self.get_overview(team_id, season_id)
    
    # =====================================================================
    # 内部辅助方法
    # =====================================================================
    
    async def _get_team_finance(self, team_id: str) -> Optional[TeamFinance]:
        result = await self.db.execute(
            select(TeamFinance).where(TeamFinance.team_id == team_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_team(self, team_id: str) -> Optional[Team]:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
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
    
    async def _find_transaction_by_idempotency(
        self,
        team_id: str,
        season_id: str,
        source_type: TransactionSourceType,
        idempotency_key: str,
    ) -> Optional[FinanceTransaction]:
        result = await self.db.execute(
            select(FinanceTransaction)
            .where(FinanceTransaction.team_id == team_id)
            .where(FinanceTransaction.season_id == season_id)
            .where(FinanceTransaction.source_type == source_type)
            .where(FinanceTransaction.extra_data["idempotency_key"].as_string() == idempotency_key)
        )
        return result.scalar_one_or_none()
    
    async def _aggregate_season_transactions(
        self, team_id: str, season_id: str
    ) -> Dict:
        result = await self.db.execute(
            select(FinanceTransaction)
            .where(FinanceTransaction.team_id == team_id)
            .where(FinanceTransaction.season_id == season_id)
            .where(FinanceTransaction.deleted_at.is_(None))
        )
        transactions = result.scalars().all()
        
        total_income = Decimal("0")
        total_expense = Decimal("0")
        income_breakdown = {
            "broadcast": Decimal("0"),
            "sponsor": Decimal("0"),
            "match_bonus": Decimal("0"),
            "cup_prize": Decimal("0"),
            "league_prize": Decimal("0"),
            "other": Decimal("0"),
        }
        expense_breakdown = {
            "wage": Decimal("0"),
            "youth": Decimal("0"),
            "transfer": Decimal("0"),
            "penalty": Decimal("0"),
            "other": Decimal("0"),
        }
        
        for txn in transactions:
            source = txn.source_type.value
            if txn.direction == TransactionDirection.INCOME:
                total_income += txn.amount
                if source in income_breakdown:
                    income_breakdown[source] += txn.amount
                else:
                    income_breakdown["other"] += txn.amount
            else:
                total_expense += txn.amount
                if source in expense_breakdown:
                    expense_breakdown[source] += txn.amount
                else:
                    expense_breakdown["other"] += txn.amount
        
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "income_breakdown": income_breakdown,
            "expense_breakdown": expense_breakdown,
        }
    
    async def _update_overspend_level(self, season_finance: TeamSeasonFinance) -> None:
        wage_cap = season_finance.wage_cap
        wage_bill = season_finance.wage_bill
        current_balance = season_finance.current_balance
        projected_income = season_finance.projected_income if season_finance.projected_income > 0 else Decimal("1")
        
        if wage_cap <= 0:
            return
        
        wage_ratio = wage_bill / wage_cap
        
        if wage_ratio > Decimal("1.15") or current_balance < -(projected_income * Decimal("0.1")):
            season_finance.overspend_level = OverspendLevel.CRISIS
        elif wage_ratio > Decimal("1.0") or current_balance < Decimal("0"):
            season_finance.overspend_level = OverspendLevel.RESTRICTED
        elif wage_ratio > Decimal("0.9"):
            season_finance.overspend_level = OverspendLevel.WARNING
        else:
            season_finance.overspend_level = OverspendLevel.NONE
    
    async def _get_current_season_for_team(self, team_id: str) -> Optional[Season]:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team or not team.current_season_id:
            result = await self.db.execute(
                select(Season).order_by(desc(Season.season_number)).limit(1)
            )
            return result.scalar_one_or_none()
        
        result = await self.db.execute(select(Season).where(Season.id == team.current_season_id))
        return result.scalar_one_or_none()
    
    async def _get_team_league_level(self, team_id: str) -> int:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team or not team.current_league_id:
            return 4
        
        result = await self.db.execute(select(League.level).where(League.id == team.current_league_id))
        level = result.scalar_one_or_none()
        return level or 4
    
    async def can_sign_player(
        self,
        team_id: str,
        new_wage: Decimal,
        replaced_player_id: str | None = None,
        season_id: str | None = None,
    ) -> bool:
        """检查球队是否可以签约球员（余额校验）
        
        设计文档简化后：不再因为工资参考线超限直接失败。
        - 球队余额不能为负（签约后至少保留少量资金）
        - 续约/重签同队球员时，应扣除该球员旧工资，避免把续约当成新增球员
        """
        season = None
        if season_id:
            result = await self.db.execute(select(Season).where(Season.id == season_id))
            season = result.scalar_one_or_none()
        if not season:
            season = await self._get_current_season_for_team(team_id)
        if not season:
            return False
        
        season_finance = await self._get_or_create_team_season_finance(team_id, season.id)
        
        # 计算加入新工资后的压力（保留计算供外部决策使用）
        current_wage_bill = await self._calculate_team_wage_bill(team_id)
        replaced_wage = Decimal("0")
        if replaced_player_id:
            result = await self.db.execute(
                select(Player.wage, Player.team_id).where(Player.id == replaced_player_id)
            )
            row = result.one_or_none()
            if row and row[1] == team_id:
                replaced_wage = Decimal(row[0] or 0)
        projected_wage_bill = current_wage_bill - replaced_wage + new_wage
        if projected_wage_bill < 0:
            projected_wage_bill = Decimal("0")
        season_finance.wage_bill = quantize_money(current_wage_bill)
        
        # 检查余额（至少保留 1 万）
        team_finance = await self._get_team_finance(team_id)
        if team_finance and team_finance.balance < Decimal("10000"):
            return False
        
        return True
    
    async def _calculate_team_wage_bill(self, team_id: str) -> Decimal:
        result = await self.db.execute(
            select(func.sum(Player.wage)).where(
                and_(
                    Player.team_id == team_id,
                    Player.status != "retired",
                )
            )
        )
        total = result.scalar_one_or_none()
        return Decimal(total) if total else Decimal("0")
    
    def _calculate_broadcast_income(self, league_level: int) -> Decimal:
        base = self.economy.broadcast.base_by_level.get(league_level, Decimal("100000"))
        return base * self.economy.broadcast.reputation_default

    def _calculate_season_ticket_income(self, league_level: int) -> Decimal:
        base = self.economy.season_ticket.base_by_level.get(league_level, Decimal("250000"))
        return base * self.economy.season_ticket.reputation_default
    
    def _calculate_sponsor_income(self, league_level: int, health: FinancialHealth) -> Decimal:
        base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
        modifier = self.economy.sponsor.health_modifier.get(health.value, Decimal("1.0"))
        return base * modifier

    def _calculate_wage_cap(self, league_level: int, health: str) -> Decimal:
        base = self.economy.wage_cap.base_by_level.get(league_level, Decimal("800000"))
        modifier = self.economy.wage_cap.modifier_by_health.get(health, Decimal("1.0"))
        return quantize_money(base * modifier)
    
    async def _calculate_league_prize(self, team_id: str, season_id: str) -> Decimal:
        result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = result.scalar_one_or_none()
        if not team or not team.current_league_id:
            return Decimal("0")
        
        result = await self.db.execute(select(League.level).where(League.id == team.current_league_id))
        level = result.scalar_one_or_none() or 4
        
        result = await self.db.execute(
            select(LeagueStanding.position)
            .where(LeagueStanding.team_id == team_id)
            .where(LeagueStanding.season_id == season_id)
            .where(LeagueStanding.league_id == team.current_league_id)
        )
        position = result.scalar_one_or_none()
        if not position:
            return Decimal("0")
        
        prizes = self.economy.league_prize.prize_by_level.get(level, ())
        if position <= len(prizes):
            return prizes[position - 1]
        return Decimal("0")
    
    async def _calculate_financial_health(self, season_finance: TeamSeasonFinance) -> FinancialHealth:
        current_balance = season_finance.current_balance
        wage_cap = season_finance.wage_cap
        wage_bill = season_finance.wage_bill
        
        if wage_cap <= 0:
            wage_cap = Decimal("1")
        
        if current_balance > 0 and wage_bill <= wage_cap * Decimal("0.8") and season_finance.overspend_level in (OverspendLevel.NONE,):
            return FinancialHealth.A
        
        if current_balance >= 0 and wage_bill <= wage_cap:
            return FinancialHealth.B
        
        if current_balance < 0 or wage_bill > wage_cap:
            return FinancialHealth.C
        
        if season_finance.overspend_level == OverspendLevel.CRISIS:
            return FinancialHealth.D
        
        return FinancialHealth.C
    
    # =====================================================================
    # Phase 3 内部辅助
    # =====================================================================
    
    async def _get_budget_plan(self, team_id: str, target_season_id: str) -> Optional[TeamBudgetPlan]:
        result = await self.db.execute(
            select(TeamBudgetPlan)
            .where(TeamBudgetPlan.team_id == team_id)
            .where(TeamBudgetPlan.target_season_id == target_season_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_or_create_budget_plan(self, team_id: str, target_season_id: str) -> TeamBudgetPlan:
        plan = await self._get_budget_plan(team_id, target_season_id)
        if not plan:
            preset = BUDGET_PRESETS[BudgetPolicy.BALANCED]
            plan = TeamBudgetPlan(
                team_id=team_id,
                target_season_id=target_season_id,
                policy=BudgetPolicy.BALANCED,
                transfer_pct=preset["transfer"],
                youth_pct=preset["youth"],
                wage_pct=preset["wage"],
                reserve_pct=preset["reserve"],
            )
            self.db.add(plan)
            await self.db.flush()
        return plan
    
    async def _get_active_sponsor_contract(self, team_id: str, season_id: str) -> Optional[SponsorContract]:
        result = await self.db.execute(
            select(SponsorContract)
            .where(SponsorContract.team_id == team_id)
            .where(SponsorContract.season_id == season_id)
            .where(SponsorContract.status.in_([SponsorContractStatus.PENDING.value, SponsorContractStatus.ACTIVE.value]))
        )
        return result.scalar_one_or_none()
    
    # =====================================================================
    # Phase 5: Transfer/Youth/Contract 执行检查与耦合
    # =====================================================================
    
    async def can_place_transfer_bid(
        self,
        team_id: str,
        season_id: str,
        amount: Decimal,
    ) -> tuple[bool, str]:
        """检查球队是否可以参与转会竞价（拍卖出价）
        
        TODO(Phase 6: TransferService): 在 list_player_for_auction() / place_bid() 中调用此方法
        
        Returns:
            (can_bid: bool, reason: str) — reason 为空表示允许
        """
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        
        if season_finance.overspend_level in (OverspendLevel.RESTRICTED, OverspendLevel.CRISIS):
            return False, f"球队处于{season_finance.overspend_level.value}状态，禁止参与拍卖竞价"
        
        team_finance = await self._get_team_finance(team_id)
        if team_finance and team_finance.balance < amount:
            return False, f"球队余额不足（当前 {int(team_finance.balance / 10000)} 万，需要 {int(amount / 10000)} 万）"
        
        return True, ""
    
    async def can_sign_free_player(
        self,
        team_id: str,
        season_id: str,
        wage: Decimal,
    ) -> tuple[bool, str]:
        """检查球队是否可以签约自由球员
        
        TODO(Phase 6: ContractService): 在 sign_contract() / renew_contract() 中调用此方法
        
        Returns:
            (can_sign: bool, reason: str)
        """
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        
        if season_finance.overspend_level == OverspendLevel.CRISIS:
            return False, "球队处于危机状态，禁止签约新球员（最低合同除外）"
        
        # 工资帽检查
        current_wage_bill = await self._calculate_team_wage_bill(team_id)
        season_finance.wage_bill = quantize_money(current_wage_bill)
        new_wage_bill = current_wage_bill + wage
        if new_wage_bill > season_finance.wage_cap:
            return False, (
                f"签约后工资总额将超出工资帽"
                f"（当前工资 {int(current_wage_bill / 10000)} 万 + 新工资 {int(wage / 10000)} 万"
                f" > 工资帽 {int(season_finance.wage_cap / 10000)} 万）"
            )
        
        return True, ""
    
    async def get_effective_sponsor_base(
        self,
        team_id: str,
        season_id: str,
        base: Decimal,
    ) -> Decimal:
        """获取经财务健康评级修正后的有效赞助基础金额
        
        修正逻辑：
        - 健康 A/B/C/D 使用 health_modifier（A=+5%, B=0%, C=-10%, D=-30%）
        - crisis 状态额外 -30%（与 D 叠加后最高 -60%）
        
        被 initialize_season_finance() 和 settle_match_finance() 调用。
        """
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        health = season_finance.financial_health
        
        modifier = self.economy.sponsor.health_modifier.get(health.value, Decimal("1.0"))
        effective = base * modifier
        
        # Crisis 额外惩罚 -30%
        if season_finance.overspend_level == OverspendLevel.CRISIS:
            effective = effective * Decimal("0.70")
        
        return effective
    
    async def preview_wage_cap_after_signing(
        self,
        team_id: str,
        season_id: str,
        proposed_wage: Decimal,
    ) -> dict:
        """预览签约后的工资帽压力
        
        TODO(Phase 6: ContractService): 在签约/续约界面调用此方法展示预测
        
        Returns:
            {
                "current_wage_bill": Decimal,
                "wage_cap": Decimal,
                "after_wage_bill": Decimal,
                "wage_pressure_pct": int,
                "would_exceed": bool,
                "remaining_cap": Decimal,
            }
        """
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        
        current_bill = season_finance.wage_bill
        wage_cap = season_finance.wage_cap if season_finance.wage_cap > 0 else Decimal("1")
        after_bill = current_bill + proposed_wage
        
        current_pressure = int((current_bill / wage_cap) * 100)
        after_pressure = int((after_bill / wage_cap) * 100)
        would_exceed = after_bill > wage_cap
        remaining = wage_cap - after_bill
        
        return {
            "current_wage_bill": current_bill,
            "wage_cap": wage_cap,
            "after_wage_bill": after_bill,
            "current_pressure_pct": current_pressure,
            "after_pressure_pct": after_pressure,
            "would_exceed": would_exceed,
            "remaining_cap": remaining,
        }
    
    async def _deduct_youth_budget(
        self,
        team_id: str,
        season_id: str,
        amount: Decimal,
    ) -> Optional[FinanceTransaction]:
        """扣除青训预算（内部方法，由 initialize_season_finance 调用）
        
        TODO(Phase 6: YouthService): 在 generate_youth_candidates() 前确认 budget 已扣除
        """
        if amount <= 0:
            return None
        
        return await self.apply_transaction(
            team_id, season_id,
            TransactionSourceType.YOUTH, TransactionDirection.EXPENSE,
            amount, "青训预算投入",
            idempotency_key=f"youth_budget_{season_id}_{team_id}"
        )
    
    # =====================================================================
    # Phase 4: AI 决策与邮件通知
    # =====================================================================
    
    async def _is_ai_team(self, team_id: str) -> bool:
        """检查球队是否为 AI 控制"""
        result = await self.db.execute(
            select(User.is_ai)
            .join(Team, Team.user_id == User.id)
            .where(Team.id == team_id)
        )
        is_ai = result.scalar_one_or_none()
        return bool(is_ai)

    async def _ensure_budget_and_sponsor_before_finance_init(
        self,
        team_id: str,
        season_id: str,
        league_level: int,
    ) -> None:
        """赛季财务初始化前确保预算和赞助合同存在。

        当前事件顺序是财务初始化早于预算窗口。为了让当季青训预算生效，
        AI 球队在这里提前完成预算/赞助决策；人类球队保留默认待确认方案。
        """
        budget_plan = await self._get_or_create_budget_plan(team_id, season_id)
        sponsor = await self._get_active_sponsor_contract(team_id, season_id)
        if not sponsor:
            base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
            sponsor = SponsorContract(
                team_id=team_id,
                season_id=season_id,
                policy=SponsorPolicy.STABLE,
                base_amount=base,
                status=SponsorContractStatus.PENDING,
            )
            self.db.add(sponsor)
            await self.db.flush()

        if await self._is_ai_team(team_id):
            await self._auto_ai_budget_decision(team_id, season_id)
            return

        if not budget_plan.locked_at and not budget_plan.is_player_confirmed:
            preset = BUDGET_PRESETS[BudgetPolicy.BALANCED]
            budget_plan.policy = BudgetPolicy.BALANCED
            budget_plan.transfer_pct = preset["transfer"]
            budget_plan.youth_pct = preset["youth"]
            budget_plan.wage_pct = preset["wage"]
            budget_plan.reserve_pct = preset["reserve"]
    
    async def _auto_ai_budget_decision(self, team_id: str, season_id: str) -> None:
        """AI 自动决策预算和赞助商
        
        基础算法：
        - 根据财务健康、球队相对联赛实力、工资压力选择赞助商。
        - 有竞争力的健康球队更容易选择绩效赞助，弱队和财务差球队倾向稳定赞助。
        - 预算策略：根据球队年龄结构微调（当前简化：一律 balanced）
        """
        # 获取上赛季的财务健康评级（如果有）
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        health = season_finance.financial_health
        
        # 确认预算计划：AI 根据球队处境动态选择。
        budget_plan = await self._get_or_create_budget_plan(team_id, season_id)
        budget_detail = {}
        if not budget_plan.is_player_confirmed and not budget_plan.locked_at:
            policy, preset, budget_detail = await self._choose_ai_budget_policy(
                team_id, season_id, health, season_finance
            )
            budget_plan.policy = policy
            budget_plan.transfer_pct = preset["transfer"]
            budget_plan.youth_pct = preset["youth"]
            budget_plan.wage_pct = preset["wage"]
            budget_plan.reserve_pct = preset["reserve"]
            budget_plan.is_player_confirmed = True
            budget_plan.locked_at = datetime.utcnow()
        
        # 赞助商决策
        sponsor = await self._get_active_sponsor_contract(team_id, season_id)
        decision_detail = {}
        if sponsor and sponsor.status == SponsorContractStatus.PENDING:
            choose_performance, decision_detail = await self._should_ai_choose_performance_sponsor(
                team_id, season_id, health, season_finance
            )
            
            if choose_performance:
                league_level = await self._get_team_league_level(team_id)
                base = self.economy.sponsor.base_by_level.get(league_level, Decimal("50000"))
                sponsor.policy = SponsorPolicy.PERFORMANCE
                sponsor.base_amount = base * PERFORMANCE_SPONSOR_BASE_RATE
                sponsor.win_bonus = base * PERFORMANCE_SPONSOR_WIN_RATE
                sponsor.draw_bonus = base * PERFORMANCE_SPONSOR_DRAW_RATE
                sponsor.max_bonus = base * PERFORMANCE_SPONSOR_MAX_BONUS_RATE
                sponsor.status = SponsorContractStatus.ACTIVE
            else:
                sponsor.status = SponsorContractStatus.ACTIVE
        
        await self.db.flush()
        logger.info(
            f"AI 自动决策完成: team={team_id}, health={health.value}, "
            f"budget={budget_plan.policy.value if budget_plan else 'none'}, budget_detail={budget_detail}, "
            f"sponsor={sponsor.policy.value if sponsor else 'none'}, sponsor_detail={decision_detail if sponsor else {}}"
        )

    async def _choose_ai_budget_policy(
        self,
        team_id: str,
        season_id: str,
        health: FinancialHealth,
        season_finance: TeamSeasonFinance,
    ) -> tuple[BudgetPolicy, Dict[str, int], Dict]:
        team_result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = team_result.scalar_one_or_none()

        league_level = await self._get_team_league_level(team_id)
        team_top8 = await self._calculate_team_top8_ovr(team_id)
        league_top8 = await self._calculate_league_average_top8_ovr(team.current_league_id) if team and team.current_league_id else None
        strength_edge = team_top8 - league_top8 if league_top8 is not None else Decimal("0")

        wage_bill = await self._calculate_team_wage_bill(team_id)
        wage_cap = season_finance.wage_cap
        if wage_cap <= 0:
            wage_cap = self._calculate_wage_cap(league_level, health.value)
        wage_pressure = wage_bill / wage_cap if wage_cap > 0 else Decimal("0")

        previous_standing = await self._get_latest_team_standing_before(team_id, season_id)
        position_ratio = None
        if previous_standing:
            position, league_size, points = previous_standing
            if league_size > 0:
                position_ratio = Decimal(position) / Decimal(league_size)

        low_hope = strength_edge <= Decimal("-3")
        high_hope = strength_edge >= Decimal("3")
        if position_ratio is not None:
            low_hope = low_hope or position_ratio >= Decimal("0.65")
            high_hope = high_hope or position_ratio <= Decimal("0.30")

        policy = BudgetPolicy.BALANCED
        reason = "balanced_default"
        roll = Decimal(str(random.random()))

        if health in (FinancialHealth.C, FinancialHealth.D) or wage_pressure >= Decimal("0.88"):
            policy = BudgetPolicy.WAGE_CONTROL
            reason = "finance_or_wage_pressure"
        elif low_hope:
            if roll < Decimal("0.75"):
                policy = BudgetPolicy.YOUTH_FOCUS
                reason = "low_season_hope_youth_rebuild"
            elif roll < Decimal("0.90"):
                policy = BudgetPolicy.BALANCED
                reason = "low_season_hope_balanced"
            else:
                policy = BudgetPolicy.WAGE_CONTROL
                reason = "low_season_hope_cost_control"
        elif high_hope:
            if roll < Decimal("0.70"):
                policy = BudgetPolicy.TRANSFER_PUSH
                reason = "high_season_hope_push"
            elif roll < Decimal("0.85"):
                policy = BudgetPolicy.BALANCED
                reason = "high_season_hope_balanced"
            else:
                policy = BudgetPolicy.YOUTH_FOCUS
                reason = "high_season_hope_future_depth"
        elif roll < Decimal("0.20"):
            policy = BudgetPolicy.YOUTH_FOCUS
            reason = "mid_table_youth_bet"

        preset = dict(BUDGET_PRESETS[policy])
        detail = {
            "reason": reason,
            "roll": float(roll),
            "league_level": league_level,
            "team_top8": float(team_top8),
            "league_top8": float(league_top8) if league_top8 is not None else None,
            "strength_edge": float(strength_edge),
            "position_ratio": float(position_ratio) if position_ratio is not None else None,
            "wage_pressure": float(wage_pressure),
            "preset": preset,
        }
        return policy, preset, detail

    async def _get_latest_team_standing_before(self, team_id: str, season_id: str) -> Optional[tuple[int, int, int]]:
        season_result = await self.db.execute(select(Season).where(Season.id == season_id))
        season = season_result.scalar_one_or_none()
        if not season:
            return None

        result = await self.db.execute(
            select(LeagueStanding, Season)
            .join(Season, LeagueStanding.season_id == Season.id)
            .where(LeagueStanding.team_id == team_id)
            .where(Season.season_number < season.season_number)
            .order_by(desc(Season.season_number))
            .limit(1)
        )
        row = result.one_or_none()
        if not row:
            return None
        standing, _ = row

        size_result = await self.db.execute(
            select(func.count())
            .select_from(LeagueStanding)
            .where(LeagueStanding.season_id == standing.season_id)
            .where(LeagueStanding.league_id == standing.league_id)
        )
        league_size = int(size_result.scalar_one() or 0)
        return int(standing.position or 0), league_size, int(standing.points or 0)

    async def _should_ai_choose_performance_sponsor(
        self,
        team_id: str,
        season_id: str,
        health: FinancialHealth,
        season_finance: TeamSeasonFinance,
    ) -> tuple[bool, Dict]:
        """AI 赞助商选择：让强队有上涨空间，但弱队/差财务优先保底。"""
        team_result = await self.db.execute(select(Team).where(Team.id == team_id))
        team = team_result.scalar_one_or_none()

        team_top8 = await self._calculate_team_top8_ovr(team_id)
        league_top8 = await self._calculate_league_average_top8_ovr(team.current_league_id) if team and team.current_league_id else None
        strength_edge = team_top8 - league_top8 if league_top8 is not None else Decimal("0")

        if health == FinancialHealth.D:
            chance = Decimal("0.00")
        elif health == FinancialHealth.C:
            chance = Decimal("0.08")
        elif strength_edge >= Decimal("3"):
            chance = Decimal("0.65")
        elif strength_edge >= Decimal("0"):
            chance = Decimal("0.45")
        elif strength_edge >= Decimal("-2"):
            chance = Decimal("0.25")
        else:
            chance = Decimal("0.12")

        if health == FinancialHealth.A:
            chance += Decimal("0.05")

        wage_pressure = Decimal("0")
        if season_finance.wage_cap > 0:
            wage_pressure = season_finance.wage_bill / season_finance.wage_cap
        if wage_pressure > Decimal("0.95"):
            chance -= Decimal("0.10")
        elif wage_pressure > Decimal("0.75") and health in (FinancialHealth.A, FinancialHealth.B):
            chance += Decimal("0.05")

        chance = max(Decimal("0"), min(Decimal("0.75"), chance))
        roll = Decimal(str(random.random()))

        detail = {
            "chance": float(chance),
            "roll": float(roll),
            "team_top8": float(team_top8),
            "league_top8": float(league_top8) if league_top8 is not None else None,
            "strength_edge": float(strength_edge),
            "wage_pressure": float(wage_pressure),
        }
        return roll < chance, detail

    async def _calculate_team_top8_ovr(self, team_id: str) -> Decimal:
        result = await self.db.execute(
            select(Player.ovr)
            .where(Player.team_id == team_id)
            .where(Player.status.in_([PlayerStatus.ACTIVE, PlayerStatus.INJURED, PlayerStatus.SUSPENDED]))
            .order_by(desc(Player.ovr))
            .limit(8)
        )
        values = list(result.scalars().all())
        if not values:
            return Decimal("0")
        return Decimal(sum(values)) / Decimal(len(values))

    async def _calculate_league_average_top8_ovr(self, league_id: str) -> Optional[Decimal]:
        result = await self.db.execute(select(Team.id).where(Team.current_league_id == league_id))
        team_ids = list(result.scalars().all())
        if not team_ids:
            return None

        totals = []
        for league_team_id in team_ids:
            top8 = await self._calculate_team_top8_ovr(league_team_id)
            if top8 > 0:
                totals.append(top8)
        if not totals:
            return None
        return sum(totals, Decimal("0")) / Decimal(len(totals))
    
    async def _check_overspend_and_notify(self, team_id: str, season_id: str) -> None:
        """检查超支状态并向人类玩家发送警告邮件"""
        season_finance = await self._get_or_create_team_season_finance(team_id, season_id)
        await self._update_overspend_level(season_finance)
        
        level = season_finance.overspend_level
        if level == OverspendLevel.NONE:
            return
        
        is_ai = await self._is_ai_team(team_id)
        if is_ai:
            return
        
        # 检查是否已经发送过同级别的警告（避免重复）
        # 使用 related_type 标记为 overspend_{level} 以便精确去重
        related_type = f"overspend_{level.value}"
        existing = await self.db.execute(
            select(Mail)
            .where(Mail.team_id == team_id)
            .where(Mail.season_id == season_id)
            .where(Mail.category == MailCategory.FINANCE)
            .where(Mail.related_type == related_type)
        )
        if existing.scalar_one_or_none():
            return
        
        if level == OverspendLevel.WARNING:
            subject = "【注意】超支警告：工资支出接近工资帽上限"
            body = f"您的球队工资支出已超过工资帽的 90%，目前处于警告状态。[{level.value}]\n\n"
            body += "请注意控制薪资结构，避免触发转会限制。"
            priority = MailPriority.NORMAL
        elif level == OverspendLevel.RESTRICTED:
            subject = "【警告】超支警告：球队处于财务受限状态"
            body = f"您的球队工资支出已超过工资帽，或账户余额为负，目前处于受限状态。[{level.value}]\n\n"
            body += "受限期间，您将无法参与拍卖竞价。请尽快出售球员或调整薪资结构。"
            priority = MailPriority.HIGH
        elif level == OverspendLevel.CRISIS:
            subject = "【紧急】超支警告：球队陷入财务危机"
            body = f"您的球队财务状况严重恶化，已陷入危机状态。[{level.value}]\n\n"
            body += "危机期间，您将无法进行自由签约，且青训预算将被强制调整为 5%。\n"
            body += "请立即采取措施改善财务状况。"
            priority = MailPriority.URGENT
        else:
            return
        
        await self._send_finance_mail(
            team_id, season_id,
            category=MailCategory.FINANCE,
            priority=priority,
            subject=subject,
            body=body,
            related_url="/finance",
            related_type=related_type,
            action_label="查看财务",
        )
    
    async def _send_season_summary_mail(
        self,
        team_id: str,
        season_id: str,
        season_finance: TeamSeasonFinance,
        stats: Dict,
    ) -> None:
        """发送赛季财务总结邮件"""
        is_ai = await self._is_ai_team(team_id)
        if is_ai:
            return
        
        net_income = stats["total_income"] - stats["total_expense"]
        health_label = {
            FinancialHealth.A: "A 级（优秀）",
            FinancialHealth.B: "B 级（良好）",
            FinancialHealth.C: "C 级（一般）",
            FinancialHealth.D: "D 级（困难）",
        }.get(season_finance.financial_health, "未知")
        
        body = f"本赛季财务结算已完成，以下是您的财务总结：\n\n"
        body += f"赛季净收入：{int(net_income / 10000)} 万\n"
        body += f"总支出：{int(stats['total_expense'] / 10000)} 万\n"
        body += f"总收入：{int(stats['total_income'] / 10000)} 万\n"
        body += f"当前余额：{int(season_finance.current_balance / 10000)} 万\n"
        body += f"财务健康评级：{health_label}\n\n"
        
        if season_finance.financial_health == FinancialHealth.A:
            body += "恭喜！您的财务管理非常出色，下赛季将获得赞助商收入和工资帽加成。"
        elif season_finance.financial_health == FinancialHealth.B:
            body += "您的财务状况良好，继续保持稳健的运营策略。"
        elif season_finance.financial_health == FinancialHealth.C:
            body += "您的财务状况一般，下赛季赞助商收入将减少 10%，建议加强成本控制。"
        elif season_finance.financial_health == FinancialHealth.D:
            body += "您的球队面临严重的财务困难，下赛季赞助商收入将减少 30%，且转会将受到限制。请尽快改善财务状况。"
        
        await self._send_finance_mail(
            team_id, season_id,
            category=MailCategory.FINANCE,
            priority=MailPriority.NORMAL,
            subject="赛季财务总结报告",
            body=body,
            related_url="/finance",
            action_label="查看详情",
        )
    
    async def _send_finance_mail(
        self,
        team_id: str,
        season_id: str,
        category: MailCategory,
        priority: MailPriority,
        subject: str,
        body: str,
        related_url: Optional[str] = None,
        related_type: Optional[str] = None,
        action_label: Optional[str] = None,
    ) -> None:
        """发送财务相关邮件通知"""
        team = await self._get_team(team_id)
        if not team:
            return
        
        mail = Mail(
            user_id=team.user_id,
            team_id=team_id,
            season_id=season_id,
            category=category,
            priority=priority,
            sender_name="财务总监",
            subject=subject,
            body=body,
            is_read=False,
            has_action=bool(related_url),
            action_label=action_label,
            related_id=None,
            related_type=related_type,
            related_url=related_url,
        )
        self.db.add(mail)
        await self.db.flush()
