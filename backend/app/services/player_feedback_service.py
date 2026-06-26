"""
Player feedback service - 球员反馈生成服务
职责：基于球员状态、比赛表现、球队形势等生成每日反馈文本。
"""
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_
from sqlalchemy.exc import IntegrityError

from app.models.player import Player, MatchForm, PlayerPosition, PlayerStatus
from app.models.player_feedback import PlayerFeedback
from app.models.season import Fixture, FixtureStatus, Season
from app.models.league import LeagueStanding
from app.models.match_result import MatchResult as MatchResultModel
from app.models.player_season_stats import PlayerSeasonStats
from app.core.logging import get_logger

logger = get_logger("app.player_feedback")

# =====================================================================
# 反馈模板库
# =====================================================================

_FEEDBACK_TEMPLATES: dict[str, list[tuple[str, int]]] = {
    "injury": [
        ("伤病让我非常沮丧，只想快点回到球场。", 3),
        ("坐在场边看队友训练的感觉太难受了。", 2),
        ("医生说还要再休息几天，我已经等不及了。", 2),
        ("康复比预期慢，但我会彻底养好再复出。", 1),
        ("每天都在做恢复训练，希望早日归队。", 1),
    ],
    "suspended": [
        ("停赛让我错过了关键比赛，下次必须更冷静。", 3),
        ("只能场边观战的感觉太煎熬。", 2),
        ("正好利用这段时间反思自己的问题。", 2),
        ("缺席比赛让我很难受，希望队友顶住。", 1),
    ],
    "low_fitness": [
        ("最近体能不太好，跑起来腿很沉。", 3),
        ("体能恢复得慢，可能需要调整训练节奏。", 2),
        ("比赛后半段明显跟不上，得加强恢复。", 2),
        ("身体还没回到最佳状态，需要更多休息。", 1),
    ],
    "wage_dissatisfied": [
        ("我对现在的薪资待遇不太满意。", 3),
        ("觉得自己配得上更好的合同。", 2),
        ("希望俱乐部能看到我的价值。", 2),
        ("薪资问题一直困扰着我。", 1),
    ],
    "wage_satisfied": [
        ("俱乐部对我很公道，我会用表现回报。", 3),
        ("对合同很满意，可以专心踢球。", 2),
        ("待遇让我安心，只想帮助球队赢球。", 2),
        ("管理层信任我，我会继续努力。", 1),
    ],
    "scoring_drought": [
        ("最近没能进球，需要更冷静地面对机会。", 3),
        ("进球荒让我有点着急，但我会调整过来。", 2),
        ("只要坚持射门感觉，进球迟早会来。", 2),
        ("运气不站在我这边，但我会继续尝试。", 1),
        ("下一场比赛我要更果断一些。", 1),
    ],
    "assist_drought": [
        ("最近助攻少了，需要找回和队友的默契。", 3),
        ("最后一传的感觉还没到位。", 2),
        ("我会继续为队友创造机会。", 2),
        ("传球精度还需要在训练中提高。", 1),
    ],
    "goal_scorer": [
        ("最近进球感觉不错，希望能延续下去。", 3),
        ("每次破门都让我更有信心。", 2),
        ("前锋就是要进球，我会继续帮助球队。", 2),
        ("教练的战术很适合我，我会把握每一次机会。", 1),
    ],
    "playmaker": [
        ("能为队友送出好传球感觉很棒。", 3),
        ("球队的进攻运转起来了，我很高兴能参与。", 2),
        ("视野和传球时机还需要继续打磨。", 2),
        ("助攻也是进球的一部分。", 1),
    ],
    "defensive_steel": [
        ("后防线需要我时刻保持专注。", 3),
        ("零封对手的感觉比进球还爽。", 2),
        ("每一次拦截和抢断都是为了球队。", 2),
        ("我会继续做好防守本职工作。", 1),
    ],
    "championship_race": [
        ("每一场比赛都至关重要，我们必须咬住。", 3),
        ("争冠的感觉让我充满动力。", 2),
        ("最后阶段不能有丝毫松懈。", 2),
        ("能和队友一起冲冠是最好的体验。", 1),
    ],
    "relegation_battle": [
        ("保级形势严峻，每个人都要多付出。", 3),
        ("球队处境不妙，但我们不会放弃。", 2),
        ("每一场都是生死战，必须团结。", 2),
        ("为了留在联赛，我们会拼尽全力。", 1),
    ],
    "hot_form": [
        ("最近状态火热，希望能一直延续。", 3),
        ("我感觉自己充满了能量。", 2),
        ("连续几场发挥出色，信心很足。", 2),
        ("每次拿球都想制造威胁。", 1),
        ("教练和队友的信任让我更放松。", 1),
    ],
    "low_form": [
        ("最近状态不好，需要尽快调整。", 3),
        ("连续低迷让我有些失望。", 2),
        ("比赛中的决策总是慢半拍。", 2),
        ("我会加倍训练，把状态找回来。", 1),
    ],
    "benched": [
        ("最近出场时间太少，我需要比赛节奏。", 3),
        ("坐在替补席的时间变多了，我渴望首发。", 2),
        ("训练表现不差，希望教练能多给机会。", 2),
        ("我理解轮换，但也想为球队出力。", 1),
    ],
    "overworked": [
        ("最近连轴转，身体有点吃不消。", 3),
        ("疲劳感越来越明显，需要适当休息。", 2),
        ("连续满场作战让我体力见底。", 2),
        ("担心疲劳会带来伤病，需要和队医沟通。", 1),
    ],
    "yellow_card_risk": [
        ("再吃牌就要停赛了，我必须冷静。", 3),
        ("黄牌积累有点多，不能再冒险犯规。", 2),
        ("我会控制自己的动作，避免给球队添麻烦。", 2),
        ("裁判对我很严，我要更小心。", 1),
    ],
    "key_match": [
        ("下一场比赛很关键，我已经准备好了。", 3),
        ("关键时刻最能激发斗志。", 2),
        ("赛季到了决定命运的时候。", 2),
        ("我会把这场当决赛来踢。", 1),
    ],
    "neutral": [
        ("一切正常，正在准备下一场比赛。", 3),
        ("训练状态还可以，没什么特别想说的。", 2),
        ("保持平常心，继续踢球。", 2),
        ("生活和训练都在正轨上。", 1),
        ("状态平稳，期待下一场能有所贡献。", 1),
        ("今天的训练感觉不错。", 1),
        ("球队氛围很好，我会继续努力。", 1),
    ],
}

_CONNECTORS = [
    "此外，",
    "与此同时，",
    "不过，",
    "值得一提的是，",
    "另一方面，",
]


class _RecentMatchSummary:
    """最近比赛汇总"""
    
    def __init__(self) -> None:
        self.matches_count: int = 0
        self.goals: int = 0
        self.assists: int = 0
        self.yellow_cards: int = 0
        self.minutes_sum: int = 0
        self.avg_rating: float = 6.0
        self.ratings: list[float] = []


class PlayerFeedbackService:
    """球员反馈生成服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =====================================================================
    # 公共接口
    # =====================================================================
    
    async def generate_feedback(
        self,
        player: Player,
        team: Optional[object],
        season: Optional[Season],
        day_number: int,
    ) -> str:
        """基于球员状态生成反馈文本。
        
        Args:
            player: 球员对象
            team: 球队对象（可选）
            season: 赛季对象（可选）
            day_number: 赛季第几天
        
        Returns:
            生成的反馈文本（1-2 句）
        """
        # 收集上下文数据
        recent = await self._get_recent_match_summary(player)
        team_position, remaining_rounds = await self._get_team_context(team, season)
        
        # 评估条件，收集匹配的类别
        matched_categories = self._evaluate_conditions(
            player=player,
            recent=recent,
            team_position=team_position,
            remaining_rounds=remaining_rounds,
        )
        
        # 如果没有匹配任何条件，使用 neutral 保底
        if not matched_categories:
            matched_categories = ["neutral"]
        
        # 选取 1-2 个不重复的类别，保持简短
        selected = self._select_categories(matched_categories, k=random.randint(1, 2))
        
        # 从每个类别中按权重抽取一句模板
        sentences: list[str] = []
        for category in selected:
            templates = _FEEDBACK_TEMPLATES.get(category, [])
            if not templates:
                continue
            sentence = self._weighted_choice(templates)
            if sentence:
                sentences.append(sentence)
        
        # 如果连一句都没抽到（理论上不可能），用 neutral 保底
        if not sentences:
            sentences = [self._weighted_choice(_FEEDBACK_TEMPLATES["neutral"])]
        
        # 用连词拼接
        return self._join_sentences(sentences)
    
    async def get_player_feedbacks(
        self,
        player_id: str,
        limit: int = 7,
    ) -> list[PlayerFeedback]:
        """查询球员最近 N 条反馈记录。"""
        result = await self.db.execute(
            select(PlayerFeedback)
            .where(PlayerFeedback.player_id == player_id)
            .order_by(desc(PlayerFeedback.day_number), desc(PlayerFeedback.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_or_create_daily_feedback(
        self,
        player: Player,
        team: Optional[object],
        season: Optional[Season],
        day_number: int,
    ) -> PlayerFeedback:
        """获取或创建指定日期的球员反馈（每天只生成一次）。"""
        # 查询是否已存在
        result = await self.db.execute(
            select(PlayerFeedback).where(
                PlayerFeedback.player_id == player.id,
                PlayerFeedback.day_number == day_number,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        
        # 生成新反馈
        content = await self.generate_feedback(player, team, season, day_number)
        
        # 推断 tags
        tags = self._infer_tags(content, player)
        
        feedback = PlayerFeedback(
            player_id=player.id,
            team_id=team.id if team else None,
            season_id=season.id if season else None,
            day_number=day_number,
            content=content,
            tags=tags,
        )
        self.db.add(feedback)
        try:
            await self.db.flush()
            await self.db.refresh(feedback)
            return feedback
        except IntegrityError:
            await self.db.rollback()
            result = await self.db.execute(
                select(PlayerFeedback).where(
                    PlayerFeedback.player_id == player.id,
                    PlayerFeedback.day_number == day_number,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
            raise
    
    # =====================================================================
    # 条件评估
    # =====================================================================
    
    def _evaluate_conditions(
        self,
        player: Player,
        recent: _RecentMatchSummary,
        team_position: int,
        remaining_rounds: int,
    ) -> list[str]:
        """评估所有条件，返回匹配的类别列表。"""
        matched: list[str] = []
        
        # injury
        if player.current_injury:
            matched.append("injury")
        
        # suspended
        if player.current_suspension:
            matched.append("suspended")
        
        # low_fitness
        fitness = getattr(player, 'fitness', None) or 0
        if fitness < 60:
            matched.append("low_fitness")
        
        # wage_dissatisfied / wage_satisfied
        wage_satisfaction = getattr(player, 'wage_satisfaction', None) or 0
        if wage_satisfaction < 0:
            matched.append("wage_dissatisfied")
        elif wage_satisfaction > 0:
            matched.append("wage_satisfied")
        
        # scoring_drought (前锋/中场，最近至少2场且0进球)
        if player.position in (PlayerPosition.FW, PlayerPosition.MF):
            if recent.matches_count >= 2 and recent.goals == 0:
                matched.append("scoring_drought")
        
        # assist_drought (中场/前锋，最近至少2场且0助攻)
        if player.position in (PlayerPosition.MF, PlayerPosition.FW):
            if recent.matches_count >= 2 and recent.assists == 0:
                matched.append("assist_drought")
        
        # goal_scorer (前锋/中场，最近有进球)
        if player.position in (PlayerPosition.FW, PlayerPosition.MF):
            if recent.matches_count >= 1 and recent.goals >= 1:
                matched.append("goal_scorer")
        
        # playmaker (中场/前锋，最近有助攻)
        if player.position in (PlayerPosition.MF, PlayerPosition.FW):
            if recent.matches_count >= 1 and recent.assists >= 1:
                matched.append("playmaker")
        
        # defensive_steel (后卫/门将，近期表现稳健)
        if player.position in (PlayerPosition.DF, PlayerPosition.GK):
            if recent.matches_count >= 1 and recent.avg_rating >= 7.0:
                matched.append("defensive_steel")
        
        # championship_race
        if team_position <= 3 and remaining_rounds <= 8:
            matched.append("championship_race")
        
        # relegation_battle (8队联赛，6-8名是危险区)
        if team_position >= 6 and remaining_rounds <= 8:
            matched.append("relegation_battle")
        
        # hot_form
        match_form = getattr(player, 'match_form', None)
        if match_form == MatchForm.HOT or recent.avg_rating >= 7.5:
            matched.append("hot_form")
        
        # low_form
        if match_form == MatchForm.LOW or recent.avg_rating <= 6.0:
            matched.append("low_form")
        
        # benched (场均出场 < 45分钟)
        if recent.matches_count > 0 and (recent.minutes_sum / recent.matches_count) < 45:
            matched.append("benched")
        
        # overworked (疲劳高 或 场均 > 80分钟)
        fatigue = getattr(player, 'fatigue', None) or 0
        if fatigue > 70:
            matched.append("overworked")
        elif recent.matches_count > 0 and (recent.minutes_sum / recent.matches_count) > 80:
            matched.append("overworked")
        
        # yellow_card_risk
        suspension = player.current_suspension or {}
        if recent.yellow_cards >= 2 or suspension.get("reason") == "yellow_card_accumulation":
            matched.append("yellow_card_risk")
        
        # key_match
        if remaining_rounds <= 3 and (team_position <= 3 or team_position >= 6):
            matched.append("key_match")
        
        return matched
    
    # =====================================================================
    # 数据查询
    # =====================================================================
    
    async def _get_recent_match_summary(self, player: Player) -> _RecentMatchSummary:
        """从 MatchResult 中提取球员最近 N 场比赛的数据。"""
        summary = _RecentMatchSummary()
        
        # N 从 recent_ratings / recent_minutes 长度推断
        n_ratings = len(player.recent_ratings or [])
        n_minutes = len(player.recent_minutes or [])
        limit = max(n_ratings, n_minutes)
        if limit == 0:
            limit = 3  # 默认最近 3 场
        
        if not self.db:
            return summary
        
        try:
            json_match = func.json_contains(
                MatchResultModel.player_stats,
                func.json_object("player_id", player.id),
            )
            query = (
                select(MatchResultModel.player_stats)
                .join(Fixture, MatchResultModel.fixture_id == Fixture.id)
                .where(Fixture.status == FixtureStatus.FINISHED)
                .where(json_match)
                .order_by(desc(Fixture.season_day))
                .limit(limit)
            )
            if player.team_id:
                query = query.where(
                    or_(
                        Fixture.home_team_id == player.team_id,
                        Fixture.away_team_id == player.team_id,
                    )
                )
            result = await self.db.execute(query)
            match_stats_list = result.scalars().all()

            for player_stats in match_stats_list:
                if not player_stats:
                    continue
                for ps in player_stats:
                    if ps.get("player_id") == player.id:
                        summary.matches_count += 1
                        summary.goals += int(ps.get("goals", 0))
                        summary.assists += int(ps.get("assists", 0))
                        summary.yellow_cards += int(ps.get("yellow_cards", 0))
                        summary.minutes_sum += int(ps.get("minutes_played", 0))
                        rating = ps.get("rating")
                        if rating is not None:
                            summary.ratings.append(float(rating))
                        break
                if summary.matches_count >= limit:
                    break
            
            if summary.ratings:
                summary.avg_rating = round(sum(summary.ratings) / len(summary.ratings), 2)
        except Exception as e:
            logger.warning(f"Failed to get recent match summary for player {player.id}: {e}")
        
        return summary
    
    async def _get_team_context(
        self,
        team: Optional[object],
        season: Optional[Season],
    ) -> tuple[int, int]:
        """获取球队排名和剩余轮次。"""
        team_position = 4  # 默认中游
        remaining_rounds = 15  # 默认较多
        
        if not self.db or not team or not season:
            return team_position, remaining_rounds
        
        try:
            # 查询排名
            standing_result = await self.db.execute(
                select(LeagueStanding.position)
                .where(
                    LeagueStanding.team_id == team.id,
                    LeagueStanding.season_id == season.id,
                )
            )
            position = standing_result.scalar_one_or_none()
            if position is not None:
                team_position = position
            
            # 计算剩余轮次：联赛总天数 - 当前轮次
            remaining = max(0, season.league_days - season.current_league_round)
            remaining_rounds = remaining
        except Exception as e:
            logger.warning(f"Failed to get team context for team {getattr(team, 'id', None)}: {e}")
        
        return team_position, remaining_rounds
    
    # =====================================================================
    # 文本生成辅助
    # =====================================================================
    
    @staticmethod
    def _weighted_choice(choices: list[tuple[str, int]]) -> str:
        """按权重随机选择。"""
        if not choices:
            return ""
        total_weight = sum(w for _, w in choices)
        r = random.randint(1, total_weight)
        cumulative = 0
        for text, weight in choices:
            cumulative += weight
            if r <= cumulative:
                return text
        return choices[-1][0]
    
    @staticmethod
    def _select_categories(categories: list[str], k: int) -> list[str]:
        """从匹配类别中选取 k 个（不重复），优先保留非 neutral。"""
        # 去重并保持顺序
        seen = set()
        unique = []
        for c in categories:
            if c not in seen:
                seen.add(c)
                unique.append(c)
        
        # 如果只有 neutral，直接返回
        if len(unique) <= k:
            return unique
        
        # 优先保留非 neutral
        non_neutral = [c for c in unique if c != "neutral"]
        neutral = [c for c in unique if c == "neutral"]
        
        selected = non_neutral[:k]
        if len(selected) < k and neutral:
            selected.extend(neutral[: k - len(selected)])
        return selected
    
    @staticmethod
    def _join_sentences(sentences: list[str]) -> str:
        """用连词将句子拼接成段落。"""
        if len(sentences) == 1:
            return sentences[0]
        
        result = sentences[0]
        for i, sentence in enumerate(sentences[1:], start=1):
            connector = random.choice(_CONNECTORS)
            result = f"{result}{connector}{sentence}"
        return result
    
    @staticmethod
    def _infer_tags(content: str, player: Player) -> list[str]:
        """根据内容推断标签。"""
        tags: list[str] = []
        
        keyword_map = {
            "injury": ["伤病", "康复", "休息", "养伤"],
            "suspended": ["停赛", "缺席", "回归"],
            "fitness": ["体能", "疲劳", "恢复"],
            "wage": ["薪资", "合同", "待遇"],
            "form": ["状态", "表现", "发挥"],
            "team": ["球队", "保级", "冠军", "排名"],
            "discipline": ["黄牌", "红牌", "犯规", "冷静"],
            "playing_time": ["出场", "替补", "首发", "时间"],
        }
        
        for tag, keywords in keyword_map.items():
            if any(kw in content for kw in keywords):
                tags.append(tag)
        
        # 去重
        return list(dict.fromkeys(tags))
