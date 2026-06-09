"""
Player feedback service - 球员反馈生成服务
职责：基于球员状态、比赛表现、球队形势等生成每日反馈文本。
"""
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_

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
        ("伤病让我非常沮丧，每天都在努力康复，希望能早日回到球场。", 3),
        ("现在只能坐在场边看着队友训练，这种滋味真不好受。", 2),
        ("医生建议我再休息几天，但我已经等不及想踢比赛了。", 2),
        ("康复进度比预期慢一些，我会保持耐心，争取彻底养好伤。", 1),
    ],
    "suspended": [
        ("停赛让我错失了关键比赛，下次一定要更注意自己的动作。", 3),
        ("在场边看着球队比赛却帮不上忙，这种感觉太煎熬了。", 2),
        ("我会利用停赛期好好反思，回归后拿出更好的表现。", 2),
        ("缺席比赛让我很难受，希望队友们能顶住这段时间。", 1),
    ],
    "low_fitness": [
        ("最近体能状况不太理想，跑起来感觉腿很沉。", 3),
        ("体能恢复得慢，可能需要调整一下训练节奏。", 2),
        ("我感觉自己还没恢复到最佳状态，需要更多的恢复时间。", 2),
        ("体能储备不足，比赛后半段明显跟不上节奏。", 1),
    ],
    "wage_dissatisfied": [
        ("说实话，我对目前的薪资待遇不太满意，希望俱乐部能重视这个问题。", 3),
        ("我觉得自己的表现配得上更好的合同，管理层应该看到这一点。", 2),
        ("薪资问题一直困扰着我，希望双方能尽快找到一个解决方案。", 2),
        ("我不是只看重钱，但合理的报酬是对球员价值的认可。", 1),
    ],
    "wage_satisfied": [
        ("俱乐部给我的合同很公道，我很感激，会全力以赴回报球队。", 3),
        ("对目前的待遇感到满意，这让我可以专心踢球，不用分心其他事情。", 2),
        ("管理层对我的认可让我很开心，我会用场上表现来证明自己值得这份薪水。", 2),
        ("合同问题处理得很好，我对自己的处境感到安心。", 1),
    ],
    "scoring_drought": [
        ("最近几场比赛没能取得进球，我需要更加冷静地面对机会。", 3),
        ("进球荒让我有点焦虑，但我相信只要坚持训练，破门只是时间问题。", 2),
        ("前锋就是为进球而生的，我会调整射门感觉，尽快打破僵局。", 2),
        ("运气似乎不太站在我这边，但我会继续努力，直到球再次入网。", 1),
    ],
    "assist_drought": [
        ("最近创造机会的能力下降了，我需要重新找到和队友的默契。", 3),
        ("助攻数据不好看，但我会继续为团队服务，相信好传球会来的。", 2),
        ("传球感觉还没到位，训练中我会多练习最后一传的精度。", 2),
        ("队友没能把我创造的绝佳机会转化为进球，希望接下来运气好一点。", 1),
    ],
    "championship_race": [
        ("赛季进入尾声，每一场比赛都至关重要，我们必须咬紧牙关。", 3),
        ("球队处在争冠集团，这种紧张刺激的感觉让我充满动力。", 2),
        ("最后几轮不能有丝毫松懈，冠军就在眼前，谁都不想功亏一篑。", 2),
        ("能和队友一起为冠军而战，这是每个球员的梦想时刻。", 1),
    ],
    "relegation_battle": [
        ("保级形势严峻，每个人都需要比平时多付出百分之百的努力。", 3),
        ("球队现在处境不妙，但我们不会放弃，保级的信念一直在。", 2),
        ("每一场都是生死战，我们必须团结一致，为了留在联赛而战。", 2),
        ("压力巨大，但我相信只要拼尽全力，我们一定能渡过难关。", 1),
    ],
    "hot_form": [
        ("最近脚风很顺，信心爆棚，希望这种好状态能一直延续下去。", 3),
        ("我感觉自己无所不能，训练和比赛都充满了能量。", 2),
        ("连续几场发挥出色，队友和教练的信任让我更加放松。", 2),
        ("现在每次拿球都觉得自己能制造威胁，这就是最好的感觉。", 1),
    ],
    "low_form": [
        ("最近状态确实不好，连简单的动作都做不流畅，需要尽快调整。", 3),
        ("连续几场表现低迷，我自己也很失望，希望能早日走出低谷。", 2),
        ("比赛中的决策总是慢半拍，我知道这不是真正的自己。", 2),
        ("教练一直在鼓励我，我会加倍训练，把状态找回来。", 1),
    ],
    "benched": [
        ("最近出场时间太少了，我需要更多比赛来保持竞技状态。", 3),
        ("坐在替补席上的时间越来越多，我渴望回到首发阵容证明自己。", 2),
        ("训练中的表现不差，但比赛机会有限，这让我有些沮丧。", 2),
        ("我理解教练的轮换安排，但也希望能得到更多信任。", 1),
    ],
    "overworked": [
        ("最近比赛和训练连轴转，身体已经非常疲惫，担心会出现伤病。", 3),
        ("疲劳感越来越明显，我需要适当的休息来避免透支。", 2),
        ("连续的满场作战让我体力见底，希望赛程能稍微宽松一点。", 2),
        ("身体发出了警报，我会和队医沟通，看看是否需要调整负荷。", 1),
    ],
    "yellow_card_risk": [
        ("我得注意自己的动作了，再吃牌就要停赛，这对球队是巨大损失。", 3),
        ("最近黄牌积累有点多，比赛中必须更冷静，不能再冒险犯规了。", 2),
        ("裁判似乎对我特别严格，我会控制自己的侵略性，避免不必要的麻烦。", 2),
        ("再吃一张牌就要缺席关键比赛，我必须小心翼翼。", 1),
    ],
    "key_match": [
        ("下一场比赛非常关键，全队都知道它的分量，我已经做好了准备。", 3),
        ("这种决定性的时刻最能激发我的斗志，期待在重要比赛中挺身而出。", 2),
        ("赛季到了最关键的阶段，每一分都可能决定最终的命运。", 2),
        ("我会把这场比赛当成决赛来踢，不留遗憾。", 1),
    ],
    "neutral": [
        ("一切正常，我正在按部就班地准备下一场比赛。", 3),
        ("球队氛围不错，训练状态也还可以，没什么特别想说的。", 2),
        ("最近没什么大起大落，保持平常心继续踢球就好。", 2),
        ("生活和训练都在正轨上，期待下一场能为球队做出贡献。", 1),
        ("状态平稳，没有伤病困扰，这是球员最需要的节奏。", 1),
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
            生成的反馈文本（2-3 句）
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
        
        # 选取 2-3 个不重复的类别
        selected = self._select_categories(matched_categories, k=random.randint(2, 3))
        
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
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback
    
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
            query = (
                select(MatchResultModel.player_stats)
                .join(Fixture, MatchResultModel.fixture_id == Fixture.id)
                .where(Fixture.status == FixtureStatus.FINISHED)
                .order_by(desc(Fixture.season_day))
                .limit(limit * 2)
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
