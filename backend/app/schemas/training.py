"""
Training-related schemas
"""
from typing import Optional, List, Dict
from decimal import Decimal
from datetime import datetime
from pydantic import Field
from enum import Enum

from app.schemas.base import BaseSchema


class TrainingSlot(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class TrainingMode(str, Enum):
    TEAM = "team"
    GROUPS_2 = "groups_2"
    GROUPS_3 = "groups_3"


class TrainingItemSchema(BaseSchema):
    """训练内容 schema"""
    id: str
    name: str
    category: str
    recommended_group: str
    base_gain: float
    intensity: str
    fitness_delta: int
    fatigue_delta: int
    load_points: int
    attribute_weights: Dict[str, float] = Field(default_factory=dict)
    position_fit: Dict[str, float] = Field(default_factory=dict)
    is_recovery: bool = False


class TrainingGroupSchema(BaseSchema):
    """分组配置 schema"""
    group_id: str
    name: str
    training_item_id: str
    player_ids: List[str]


class TrainingPlanSlotSchema(BaseSchema):
    """训练计划时段 schema"""
    id: Optional[str] = None
    team_id: str
    season_id: str
    season_day: int
    slot: TrainingSlot
    mode: TrainingMode = TrainingMode.TEAM
    training_item_id: Optional[str] = None
    groups: Optional[List[TrainingGroupSchema]] = None
    status: str = "planned"
    created_by: str = "player"
    training_item: Optional[TrainingItemSchema] = None


class TrainingPlanSaveRequest(BaseSchema):
    """保存训练计划请求"""
    season_id: str
    items: List[dict] = Field(..., description="训练计划项列表")


class TemplateApplyRequest(BaseSchema):
    """套用套餐请求"""
    season_id: str
    start_day: int


class TrainingResultSchema(BaseSchema):
    """训练结果 schema"""
    id: str
    player_id: str
    player_name: Optional[str] = None
    season_day: int
    slot: TrainingSlot
    training_item_id: str
    training_item_name: Optional[str] = None
    attribute_gains: Dict[str, float] = Field(default_factory=dict)
    fitness_before: int
    fitness_after: int
    fatigue_before: int
    fatigue_after: int
    breakthroughs: List[dict] = Field(default_factory=list)
    efficiency: Decimal
    created_at: datetime


class TrainingDailySummarySchema(BaseSchema):
    """每日训练总结"""
    season_day: int
    slot: TrainingSlot
    total_players: int
    total_breakthroughs: int
    breakthrough_players: List[dict] = Field(default_factory=list)


class PlayerFatigueSchema(BaseSchema):
    """球员疲劳状态 schema"""
    player_id: str
    player_name: str
    fitness: int
    fatigue: int
    stamina_preview: float
    fatigue_band: str
    stamina_multiplier: float
    recommendation: str
    can_high_intensity: bool


class PlayerTrainingProgressSchema(BaseSchema):
    """球员训练进度 schema"""
    player_id: str
    player_name: str
    recent_sessions: int
    total_gains: Dict[str, float] = Field(default_factory=dict)
    attribute_status: Dict[str, dict] = Field(default_factory=dict)
    growth_curve: dict = Field(default_factory=dict)


class AutoGroupResponse(BaseSchema):
    """自动分组响应"""
    mode: TrainingMode
    groups: List[TrainingGroupSchema]


class TrainingTemplateSchema(BaseSchema):
    """训练套餐 schema"""
    id: str
    name: str
    description: str


class PlayerFatigueBatchResponse(BaseSchema):
    """全队疲劳状态响应"""
    team_id: str
    players: List[PlayerFatigueSchema]
    avg_fitness: float
    avg_fatigue: float



class TrainingProgressPoint(BaseSchema):
    """折线图单点"""
    season_day: int
    value: float


class TrainingProgressBreakthrough(BaseSchema):
    """整数突破标记"""
    season_day: int
    attribute: str
    before: int
    after: int


class TrainingProgressSeries(BaseSchema):
    """单个球员在某项指标上的折线序列"""
    player_id: str
    player_name: str
    avatar_url: Optional[str] = None
    values: List[TrainingProgressPoint] = Field(default_factory=list)
    breakthroughs: List[TrainingProgressBreakthrough] = Field(default_factory=list)


class TrainingProgressResponse(BaseSchema):
    """训练成长曲线响应"""
    metric: str
    metric_label: str
    start_day: int
    end_day: int
    series: List[TrainingProgressSeries] = Field(default_factory=list)
