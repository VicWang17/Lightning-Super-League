"""
NotificationService - 统一邮件/通知服务

封装所有游戏内邮件发送逻辑，替代分散在各 Service 中的 Mail ORM 直接创建。
各业务服务在关键节点调用本服务发送通知，避免重复代码。
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.mail import Mail, MailCategory, MailPriority
from app.models.team import Team
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger("app.notification")


class NotificationService:
    """统一通知服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # =====================================================================
    # 基础工具
    # =====================================================================

    async def is_ai_team(self, team_id: str) -> bool:
        """检查球队是否为 AI 控制"""
        result = await self.db.execute(
            select(User.is_ai)
            .join(Team, Team.user_id == User.id)
            .where(Team.id == team_id)
        )
        is_ai = result.scalar_one_or_none()
        return bool(is_ai)

    async def get_team_user_id(self, team_id: str) -> Optional[str]:
        """获取球队对应用户的 ID"""
        result = await self.db.execute(
            select(Team.user_id).where(Team.id == team_id)
        )
        return result.scalar_one_or_none()

    async def check_duplicate(
        self,
        team_id: str,
        season_id: Optional[str],
        related_type: str,
        related_id: Optional[str] = None,
    ) -> bool:
        """检查同赛季同类型邮件是否已发送（去重）

        Returns:
            True 如果已存在（重复），False 如果不存在（可发送）
        """
        where_clause = [
            Mail.team_id == team_id,
            Mail.related_type == related_type,
        ]
        if season_id:
            where_clause.append(Mail.season_id == season_id)
        if related_id:
            where_clause.append(Mail.related_id == related_id)

        result = await self.db.execute(
            select(func.count(Mail.id)).where(and_(*where_clause))
        )
        count = result.scalar_one_or_none() or 0
        return count > 0

    # =====================================================================
    # 核心发送接口
    # =====================================================================

    async def send_mail(
        self,
        team_id: str,
        season_id: Optional[str],
        category: MailCategory,
        priority: MailPriority,
        sender_name: str,
        subject: str,
        body: str,
        summary: Optional[str] = None,
        related_id: Optional[str] = None,
        related_type: Optional[str] = None,
        related_url: Optional[str] = None,
        action_label: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        skip_ai: bool = True,
    ) -> Optional[Mail]:
        """发送单封邮件

        Args:
            skip_ai: True 时自动跳过 AI 球队（默认）
        """
        if skip_ai:
            try:
                if await self.is_ai_team(team_id):
                    return None
            except Exception as exc:
                logger.warning(f"AI check failed for team {team_id}: {exc}")
                return None

        user_id = await self.get_team_user_id(team_id)
        if not user_id:
            return None

        mail = Mail(
            user_id=user_id,
            team_id=team_id,
            season_id=season_id,
            category=category,
            priority=priority,
            sender_name=sender_name,
            subject=subject,
            summary=summary,
            body=body,
            is_read=False,
            has_action=bool(related_url),
            action_label=action_label,
            related_id=related_id,
            related_type=related_type,
            related_url=related_url,
            expires_at=expires_at,
        )
        self.db.add(mail)
        logger.info(
            f"Mail sent: team={team_id}, category={category.value}, "
            f"priority={priority.value}, subject={subject}"
        )
        return mail

    async def send_mail_to_human_teams(
        self,
        team_ids: List[str],
        season_id: Optional[str],
        category: MailCategory,
        priority: MailPriority,
        sender_name: str,
        subject: str,
        body: str,
        summary: Optional[str] = None,
        related_type: Optional[str] = None,
        related_url: Optional[str] = None,
        action_label: Optional[str] = None,
    ) -> int:
        """批量发送邮件给多支球队的人类玩家，自动过滤 AI

        Returns:
            实际发送的邮件数量
        """
        if not team_ids:
            return 0

        # 批量查询人类球队
        result = await self.db.execute(
            select(Team.id, Team.user_id)
            .join(User, Team.user_id == User.id)
            .where(Team.id.in_(team_ids))
            .where(User.is_ai == False)
        )
        human_teams = {row[0]: row[1] for row in result.all()}

        sent = 0
        for team_id, user_id in human_teams.items():
            mail = Mail(
                user_id=user_id,
                team_id=team_id,
                season_id=season_id,
                category=category,
                priority=priority,
                sender_name=sender_name,
                subject=subject,
                summary=summary,
                body=body,
                is_read=False,
                has_action=bool(related_url),
                action_label=action_label,
                related_type=related_type,
                related_url=related_url,
            )
            self.db.add(mail)
            sent += 1

        logger.info(
            f"Batch mail sent: category={category.value}, "
            f"targets={len(team_ids)}, sent={sent}"
        )
        return sent

    # =====================================================================
    # 比赛相关
    # =====================================================================

    async def send_match_preview(
        self,
        team_id: str,
        season_id: str,
        fixture_id: str,
        opponent_name: str,
        is_home: bool,
        fixture_type: str,
        round_info: str,
        day: int,
    ) -> Optional[Mail]:
        """比赛预告"""
        location = "主场" if is_home else "客场"
        subject = f"【比赛预告】{location} vs {opponent_name}"
        body = (
            f"第 {day} 天，您的球队将在{location}迎战 {opponent_name}。\n\n"
            f"赛事类型：{fixture_type}\n"
            f"轮次：{round_info}\n\n"
            f"请确保您的首发阵容和战术安排已经就绪。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.MATCH_PREVIEW,
            priority=MailPriority.NORMAL,
            sender_name="赛事组委会",
            subject=subject,
            body=body,
            related_id=fixture_id,
            related_type="fixture_preview",
            related_url=f"/fixtures/{fixture_id}",
            action_label="查看比赛",
        )

    async def send_match_result(
        self,
        team_id: str,
        season_id: str,
        fixture_id: str,
        opponent_name: str,
        is_home: bool,
        home_score: int,
        away_score: int,
        fixture_type: str,
        goals: List[Dict[str, Any]],
        yellow_cards: int,
        red_cards: int,
        mvp_name: Optional[str] = None,
        injuries: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Mail]:
        """比赛结果"""
        location = "主场" if is_home else "客场"
        my_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score

        if my_score > opp_score:
            result_text = "胜利"
            priority = MailPriority.NORMAL
        elif my_score == opp_score:
            result_text = "平局"
            priority = MailPriority.NORMAL
        else:
            result_text = "失利"
            priority = MailPriority.NORMAL

        subject = f"【比赛结果】{location} vs {opponent_name} {home_score}:{away_score}"
        body = f"比赛结束，您的球队 {my_score}:{opp_score} {result_text}。\n\n"

        if goals:
            body += "进球记录：\n"
            for g in goals:
                body += f"  • {g.get('minute', '?')}分钟 - {g.get('player_name', '未知球员')}\n"
            body += "\n"

        if mvp_name:
            body += f"本场 MVP：{mvp_name}\n\n"

        if yellow_cards or red_cards:
            body += f"红黄牌：黄牌 {yellow_cards} 张"
            if red_cards:
                body += f"，红牌 {red_cards} 张"
            body += "\n\n"

        if injuries:
            body += "【伤病快报】\n"
            for inj in injuries:
                body += (
                    f"  • {inj.get('player_name', '未知球员')} - "
                    f"{inj.get('injury_name', '受伤')} "
                    f"(预计恢复 {inj.get('days', '?')} 天)\n"
                )
            body += "\n"

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.MATCH_RESULT,
            priority=priority,
            sender_name="赛事组委会",
            subject=subject,
            body=body,
            related_id=fixture_id,
            related_type="fixture_result",
            related_url=f"/matches/{fixture_id}",
            action_label="查看战报",
        )

    async def send_cup_progression(
        self,
        team_id: str,
        season_id: str,
        competition_name: str,
        advanced: bool,
        stage_name: Optional[str] = None,
    ) -> Optional[Mail]:
        """杯赛晋级/淘汰通知"""
        if advanced:
            subject = f"【杯赛】{competition_name} 晋级！"
            body = f"恭喜！您的球队在 {competition_name} 中成功晋级"
            if stage_name:
                body += f"，进入 {stage_name}"
            body += "。\n\n继续保持出色表现！"
            priority = MailPriority.HIGH
        else:
            subject = f"【杯赛】{competition_name} 止步"
            body = (
                f"很遗憾，您的球队在 {competition_name} 中被淘汰。\n\n"
                f"总结经验，下赛季再战！"
            )
            priority = MailPriority.NORMAL

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.MATCH_RESULT,
            priority=priority,
            sender_name="杯赛组委会",
            subject=subject,
            body=body,
            related_type="cup_progression",
        )

    async def send_promotion_relegation(
        self,
        team_id: str,
        season_id: str,
        promoted: bool,
        new_league_name: Optional[str] = None,
    ) -> Optional[Mail]:
        """升降级确认"""
        if promoted:
            subject = "【喜讯】球队成功升级！"
            body = "恭喜您的球队在本赛季表现出色，成功升入更高级别联赛！"
            if new_league_name:
                body += f"\n\n下赛季联赛：{new_league_name}"
            body += "\n\n更高的舞台，更大的挑战，祝您再创佳绩！"
            priority = MailPriority.HIGH
        else:
            subject = "【通知】球队降级"
            body = (
                "很遗憾，您的球队本赛季表现不佳，将降入下一级别联赛。"
            )
            if new_league_name:
                body += f"\n\n下赛季联赛：{new_league_name}"
            body += "\n\n不要气馁，重整旗鼓，下赛季杀回来！"
            priority = MailPriority.HIGH

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=priority,
            sender_name="联赛组委会",
            subject=subject,
            body=body,
            related_type="promotion_relegation",
            related_url="/league",
            action_label="查看联赛",
        )

    async def send_tactics_reminder(
        self,
        team_id: str,
        season_id: str,
        fixture_id: str,
        opponent_name: str,
        is_home: bool,
        hours_left: int = 2,
    ) -> Optional[Mail]:
        """战术设置提醒"""
        location = "主场" if is_home else "客场"
        subject = f"【战术提醒】{location} vs {opponent_name}"
        body = (
            f"您的球队即将在{location}迎战 {opponent_name}。\n\n"
            f"建议您检查并调整首发阵容和战术安排，"
            f"合理的战术布置可以显著提升比赛表现。\n\n"
            f"• 进攻战术：调整传球风格、进攻宽度、节奏\n"
            f"• 防守战术：调整逼抢强度、防线高度、铲球风格\n"
            f"• 定位球：设置角球和任意球主罚人选\n\n"
            f"祝您的球队取得好成绩！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.MATCH_PREVIEW,
            priority=MailPriority.NORMAL,
            sender_name="战术教练",
            subject=subject,
            body=body,
            related_id=fixture_id,
            related_type="tactics_reminder",
            related_url=f"/tactics?fixture_id={fixture_id}",
            action_label="设置战术",
        )

    # =====================================================================
    # 赛季流程
    # =====================================================================

    async def send_season_start(
        self,
        team_id: str,
        season_id: str,
        season_number: int,
    ) -> Optional[Mail]:
        """赛季开始通知"""
        subject = f"第 {season_number} 赛季正式开始！"
        body = (
            f"欢迎来到第 {season_number} 赛季！\n\n"
            f"新赛季的赛程已经生成，您可以：\n"
            f"• 查看完整赛程安排\n"
            f"• 制定赛季初的转会策略\n"
            f"• 确认赞助商合同\n"
            f"• 规划青训投入\n\n"
            f"祝您本赛季取得佳绩！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="联赛主席",
            subject=subject,
            body=body,
            related_type="season_start",
            related_url="/schedule",
            action_label="查看赛程",
        )

    async def send_season_end(
        self,
        team_id: str,
        season_id: str,
        season_number: int,
        league_position: Optional[int] = None,
    ) -> Optional[Mail]:
        """赛季结束通知"""
        subject = f"第 {season_number} 赛季结束"
        body = f"第 {season_number} 赛季已经落下帷幕。\n\n"
        if league_position:
            body += f"您的联赛最终排名：第 {league_position} 名\n\n"
        body += (
            f"休赛期期间，系统将依次处理：\n"
            f"• 球员退役\n"
            f"• 合同到期释放\n"
            f"• 青训营刷新\n"
            f"• 财务结算\n"
            f"• 升降级调整\n\n"
            f"新赛季即将开始，敬请期待！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="联赛主席",
            subject=subject,
            body=body,
            related_type="season_end",
            related_url="/season/summary",
            action_label="赛季总结",
        )

    async def send_wages_paid(
        self,
        team_id: str,
        season_id: str,
        amount: float,
        balance_after: float,
    ) -> Optional[Mail]:
        """工资发放通知"""
        subject = "工资已发放"
        body = (
            f"本期工资已自动从球队账户扣除。\n\n"
            f"扣除金额：{amount:,.0f}\n"
            f"账户余额：{balance_after:,.0f}\n\n"
            f"如工资支出接近工资帽上限，请及时调整阵容。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.FINANCE,
            priority=MailPriority.LOW,
            sender_name="财务总监",
            subject=subject,
            body=body,
            related_type="wages_paid",
            related_url="/finance",
            action_label="查看财务",
        )

    # =====================================================================
    # 伤病相关
    # =====================================================================

    async def send_injury_report(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        injury_name: str,
        body_part: str,
        severity: int,
        days: int,
        cause: str = "match",
    ) -> Optional[Mail]:
        """球员伤病通知"""
        cause_text = "比赛中" if cause == "match" else "训练中"
        if severity >= 3:
            priority = MailPriority.HIGH
            prefix = "【重伤】"
        elif severity >= 2:
            priority = MailPriority.HIGH
            prefix = "【中伤】"
        else:
            priority = MailPriority.NORMAL
            prefix = "【轻伤】"

        subject = f"{prefix}{player_name} {injury_name}"
        body = (
            f"很遗憾，{player_name} 在{cause_text}遭遇伤病。\n\n"
            f"伤病详情：\n"
            f"  部位：{body_part}\n"
            f"  诊断：{injury_name}\n"
            f"  严重度：{'★' * severity}{'☆' * (3 - severity)}\n"
            f"  预计恢复：{days} 天\n\n"
        )
        if severity >= 2:
            body += (
                f"该球员预计缺席多场比赛。"
                f"您可以前往医疗中心查看可选的治疗方案，加速康复进程。\n\n"
                f"注意：医疗加速可能带来复发风险，请谨慎选择。"
            )
        else:
            body += "该球员预计很快恢复，请合理安排轮换。"

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=priority,
            sender_name="队医",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type=f"injury_{cause}",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    async def send_injury_recovery(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        body_part: str,
    ) -> Optional[Mail]:
        """球员伤愈通知"""
        subject = f"【康复】{player_name} 已伤愈复出"
        body = (
            f"好消息！{player_name} 已经康复，可以重新上场比赛。\n\n"
            f"原伤病部位：{body_part}\n\n"
            f"注意：伤愈后该部位仍有残余劳损，建议初期控制上场时间，"
            f"避免高强度连续比赛导致复发。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="队医",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="injury_recovery",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    async def send_injury_warning(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        body_part: str,
        wear_value: float,
    ) -> Optional[Mail]:
        """伤病预警（劳损过高）"""
        subject = f"【预警】{player_name} {body_part}劳损过高"
        body = (
            f"{player_name} 的 {body_part} 劳损值已达到 {wear_value:.1f}，"
            f"接近受伤临界线。\n\n"
            f"建议：\n"
            f"• 下场比赛安排轮休\n"
            f"• 安排恢复性训练\n"
            f"• 减少该球员近期比赛时间\n\n"
            f"及时干预可以有效避免伤病发生。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="体能教练",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="injury_warning",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    async def send_treatment_available(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        injury_name: str,
    ) -> Optional[Mail]:
        """医疗方案可用提醒"""
        subject = f"【医疗】{player_name} 治疗方案已就绪"
        body = (
            f"{player_name} 确诊为 {injury_name}，"
            f"医疗团队已制定可选的治疗方案。\n\n"
            f"可选方案：\n"
            f"• 加强理疗：费用较低，恢复小幅加速\n"
            f"• 专家会诊：费用中等，恢复明显加速\n"
            f"• 激进复出：费用较高，恢复大幅加速但有复发风险\n\n"
            f"治疗将优先使用风险准备金，不足部分从余额扣除。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.HIGH,
            sender_name="医疗主管",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="treatment_available",
            related_url="/medical",
            action_label="查看方案",
        )

    async def send_treatment_completed(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        plan_name: str,
        days_before: int,
        days_after: int,
        cost: float,
        side_effect: str,
    ) -> Optional[Mail]:
        """治疗完成通知"""
        subject = f"【医疗】{player_name} 治疗已完成"
        body = (
            f"{player_name} 已接受 {plan_name} 治疗。\n\n"
            f"治疗结果：\n"
            f"  原恢复天数：{days_before} 天\n"
            f"  现恢复天数：{days_after} 天\n"
            f"  缩短：{days_before - days_after} 天\n"
            f"  费用：{cost:,.0f}\n\n"
        )
        if side_effect:
            body += f"副作用提示：{side_effect}\n\n"
        body += "请继续关注球员恢复情况。"

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="医疗主管",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="treatment_completed",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    # =====================================================================
    # 青训相关
    # =====================================================================

    async def send_youth_refresh(
        self,
        team_id: str,
        season_id: str,
        day: int,
        new_count: int,
    ) -> Optional[Mail]:
        """青训营刷新通知"""
        subject = f"【青训】青训营迎来 {new_count} 名新球员"
        body = (
            f"第 {day} 天，青训营进行了新一轮人才筛选，"
            f"共有 {new_count} 名新球员加入。\n\n"
            f"您可以前往青训营查看他们的潜力评估，"
            f"决定是否签约入一线队或继续培养。\n\n"
            f"青训球员每轮训练都会成长，建议定期关注。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="青训主管",
            subject=subject,
            body=body,
            related_type="youth_refresh",
            related_url="/youth",
            action_label="查看青训",
        )

    async def send_youth_breakthrough(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        old_ovr: int,
        new_ovr: int,
    ) -> Optional[Mail]:
        """青训球员成长突破"""
        subject = f"【青训】{player_name} 能力提升！"
        body = (
            f"{player_name} 在最近的训练中取得了明显进步，"
            f"综合能力从 {old_ovr} 提升至 {new_ovr}！\n\n"
            f"潜力正在兑现，建议考虑是否将其提拔至一线队。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.LOW,
            sender_name="青训主管",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="youth_breakthrough",
            related_url="/youth",
            action_label="查看青训",
        )

    async def send_youth_signed(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        years: int,
        wage: float,
    ) -> Optional[Mail]:
        """青训签约成功"""
        subject = f"【青训】{player_name} 签约一线队"
        body = (
            f"{player_name} 已正式从青训营签约至一线队。\n\n"
            f"合同详情：\n"
            f"  年限：{years} 年\n"
            f"  周薪：{wage:,.0f}\n\n"
            f"祝他在一线队有出色的表现！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.TRANSFER,
            priority=MailPriority.NORMAL,
            sender_name="青训主管",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="youth_signed",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    # =====================================================================
    # 合同与生命周期
    # =====================================================================

    async def send_contract_expiring(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        end_season: int,
        current_season: int,
    ) -> Optional[Mail]:
        """合同到期提醒"""
        seasons_left = end_season - current_season
        if seasons_left <= 0:
            subject = f"【合同】{player_name} 合同即将到期"
            body = (
                f"{player_name} 的合同将在本赛季结束后到期，"
                f"届时他将成为自由球员进入转会市场。\n\n"
                f"如果您希望留用该球员，请尽快启动续约谈判。"
            )
        else:
            subject = f"【合同】{player_name} 合同剩 {seasons_left} 个赛季"
            body = (
                f"{player_name} 的合同将在 {end_season} 赛季结束后到期"
                f"（还剩 {seasons_left} 个赛季）。\n\n"
                f"建议提前规划续约或寻找替代人选。"
            )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.HIGH,
            sender_name="人事主管",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="contract_expiring",
            related_url="/contracts",
            action_label="查看合同",
        )

    async def send_player_retired(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        age: int,
        seasons_served: int,
    ) -> Optional[Mail]:
        """球员退役通知"""
        subject = f"【退役】{player_name} 挂靴退役"
        body = (
            f"{player_name}（{age}岁）在本赛季结束后正式退役。\n\n"
            f"他在您的球队效力了 {seasons_served} 个赛季，"
            f"感谢他为球队做出的贡献。\n\n"
            f"他的球衣号码将被释放，供新加盟球员使用。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="人事主管",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="player_retired",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    async def send_auto_fill(
        self,
        team_id: str,
        season_id: str,
        filled_count: int,
        player_names: List[str],
    ) -> Optional[Mail]:
        """自动补员通知"""
        names_str = "、".join(player_names) if player_names else "若干名球员"
        subject = f"【补员】系统自动补充 {filled_count} 名球员"
        body = (
            f"由于您的球队阵容人数不足下限，"
            f"系统已自动为您补充 {filled_count} 名球员：\n\n"
            f"{names_str}\n\n"
            f"注意：自动补员的球员能力值较低，仅为应急之用。\n"
            f"建议您在转会市场寻找更优质的球员替换他们。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="人事主管",
            subject=subject,
            body=body,
            related_type="auto_fill",
            related_url="/transfer",
            action_label="查看转会",
        )

    async def send_new_signing(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        source: str,
        years: int,
        wage: float,
    ) -> Optional[Mail]:
        """新签约成功通知"""
        source_map = {
            "free_market": "自由市场",
            "academy": "青训营",
            "draft": "选秀",
            "auto_fill": "自动补员",
        }
        source_text = source_map.get(source, source)
        subject = f"【签约】{player_name} 加盟球队"
        body = (
            f"{player_name} 已通过 {source_text} 正式加盟您的球队！\n\n"
            f"合同详情：\n"
            f"  年限：{years} 年\n"
            f"  周薪：{wage:,.0f}\n\n"
            f"祝他在新球队有出色的表现！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.TRANSFER,
            priority=MailPriority.NORMAL,
            sender_name="转会总监",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="new_signing",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    # =====================================================================
    # 训练相关
    # =====================================================================

    async def send_training_summary(
        self,
        team_id: str,
        season_id: str,
        day: int,
        sessions_completed: int,
        breakthroughs: int,
        declines: int,
        injuries: int,
        top_performers: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Mail]:
        """每日训练总结"""
        subject = f"第 {day} 天训练总结"
        body = f"今日训练已完成，以下是训练总结：\n\n"
        body += f"训练项目完成：{sessions_completed} 项\n"
        if breakthroughs:
            body += f"能力提升：{breakthroughs} 人次\n"
        if declines:
            body += f"状态下滑：{declines} 人次\n"
        if injuries:
            body += f"训练伤病：{injuries} 人\n"
        body += "\n"

        if top_performers:
            body += "今日表现突出：\n"
            for p in top_performers[:3]:
                body += f"  • {p.get('name', '未知')} - {p.get('highlight', '表现优异')}\n"
            body += "\n"

        if injuries:
            body += "【注意】训练中出现伤病，请查看伤病报告。\n\n"

        body += "明天别忘了继续安排训练计划！"

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.LOW,
            sender_name="体能教练",
            subject=subject,
            body=body,
            related_type="training_summary",
            related_url="/training",
            action_label="查看训练",
        )

    async def send_training_injury(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        injury_name: str,
        severity: int,
        days: int,
    ) -> Optional[Mail]:
        """训练伤病通知"""
        subject = f"【训练伤病】{player_name} 训练中受伤"
        body = (
            f"{player_name} 在今天的训练中遭遇伤病。\n\n"
            f"伤病详情：\n"
            f"  诊断：{injury_name}\n"
            f"  严重度：{'★' * severity}{'☆' * (3 - severity)}\n"
            f"  预计恢复：{days} 天\n\n"
            f"建议调整后续训练强度，避免更多伤病发生。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="体能教练",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="training_injury",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    async def send_default_training_reminder(
        self,
        team_id: str,
        season_id: str,
        day: int,
    ) -> Optional[Mail]:
        """默认训练提醒（提醒玩家手动设置）"""
        subject = f"【提醒】第 {day} 天训练计划为默认安排"
        body = (
            f"今天是第 {day} 天，系统将为您安排默认训练计划。\n\n"
            f"默认训练的效果仅为手动定制训练的 80%，"
            f"建议您根据球队当前状态和 upcoming 比赛对手，"
            f"前往训练中心制定更针对性的训练方案。\n\n"
            f"您可以：\n"
            f"• 调整训练强度（恢复/轻量/正常/高强度）\n"
            f"• 选择重点训练属性\n"
            f"• 针对特定球员定制加练\n\n"
            f"合理的训练安排是取得好成绩的关键！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.NORMAL,
            sender_name="体能教练",
            subject=subject,
            body=body,
            related_type="default_training_reminder",
            related_url="/training",
            action_label="设置训练",
        )

    # =====================================================================
    # 赞助商相关
    # =====================================================================

    async def send_sponsor_choice_reminder(
        self,
        team_id: str,
        season_id: str,
    ) -> Optional[Mail]:
        """赞助商选择邀请"""
        subject = "【赞助商】请选择本赛季赞助商策略"
        body = (
            f"新赛季赞助商合同待确认。请选择您的赞助商策略：\n\n"
            f"• 稳定型赞助商：每场比赛固定收入，风险低\n"
            f"• 表现型赞助商：基础收入 + 胜负奖金，上限高但风险大\n\n"
            f"选择建议：\n"
            f"  - 球队实力强、期望冲击冠军 → 表现型\n"
            f"  - 球队实力一般或财务紧张 → 稳定型\n\n"
            f"逾期未选择将自动应用稳定型赞助商。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SPONSOR,
            priority=MailPriority.HIGH,
            sender_name="商务总监",
            subject=subject,
            body=body,
            related_type="sponsor_choice",
            related_url="/finance/sponsor",
            action_label="选择赞助商",
        )

    async def send_sponsor_bonus(
        self,
        team_id: str,
        season_id: str,
        amount: float,
        match_result: str,
    ) -> Optional[Mail]:
        """赞助表现奖金到账"""
        subject = "【赞助商】表现奖金已到账"
        body = (
            f"表现型赞助商根据上一场比赛结果（{match_result}）"
            f"发放了表现奖金。\n\n"
            f"到账金额：{amount:,.0f}\n\n"
            f"继续保持良好表现，获取更多奖金！"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SPONSOR,
            priority=MailPriority.LOW,
            sender_name="商务总监",
            subject=subject,
            body=body,
            related_type="sponsor_bonus",
            related_url="/finance",
            action_label="查看财务",
        )

    # =====================================================================
    # 系统/其他
    # =====================================================================

    async def send_player_suspended(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        reason: str,
        matches: int,
    ) -> Optional[Mail]:
        """球员停赛通知"""
        subject = f"【停赛】{player_name} 被停赛 {matches} 场"
        body = (
            f"{player_name} 因 {reason} 被停赛 {matches} 场。\n\n"
            f"停赛期间该球员无法上场比赛，"
            f"请调整阵容安排。"
        )
        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.HIGH,
            sender_name="赛事纪律委员会",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="player_suspended",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )

    async def send_player_form_change(
        self,
        team_id: str,
        season_id: str,
        player_name: str,
        player_id: str,
        old_form: str,
        new_form: str,
        reason: Optional[str] = None,
    ) -> Optional[Mail]:
        """球员状态大幅变化"""
        subject = f"【状态】{player_name} 状态变为 {new_form}"
        body = f"{player_name} 的比赛状态从 {old_form} 变为 {new_form}。\n\n"
        if reason:
            body += f"原因：{reason}\n\n"
        if new_form in ("HOT", "EXCELLENT"):
            body += "该球员近期表现出色，建议给予更多上场时间。"
        elif new_form in ("LOW", "POOR"):
            body += "该球员近期状态低迷，建议适当轮换或增加针对性训练。"
        else:
            body += "请持续关注该球员的表现变化。"

        return await self.send_mail(
            team_id=team_id,
            season_id=season_id,
            category=MailCategory.SYSTEM,
            priority=MailPriority.LOW,
            sender_name="助理教练",
            subject=subject,
            body=body,
            related_id=player_id,
            related_type="form_change",
            related_url=f"/players/{player_id}",
            action_label="查看球员",
        )
