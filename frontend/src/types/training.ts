// Training system types

export type TrainingSlot = 'morning' | 'afternoon' | 'evening'
export type TrainingMode = 'team' | 'groups_2' | 'groups_3'
export type TrainingStatus = 'planned' | 'completed' | 'cancelled'

export interface TrainingItem {
  id: string
  name: string
  category: string
  recommended_group: string
  base_gain: number
  intensity: string
  fitness_delta: number
  fatigue_delta: number
  load_points: number
  attribute_weights: Record<string, number>
  position_fit: Record<string, number>
  is_recovery: boolean
}

export interface TrainingGroup {
  group_id: string
  name: string
  training_item_id: string
  player_ids: string[]
}

export interface TrainingPlanSlot {
  id?: string
  team_id: string
  season_id: string
  season_day: number
  slot: TrainingSlot
  mode: TrainingMode
  training_item_id: string | null
  groups: TrainingGroup[] | null
  status: TrainingStatus
  created_by: string
  training_item?: TrainingItem
}

export interface TrainingTemplate {
  id: string
  name: string
  description: string
}

/** 前端使用的模板详情（含7天schedule） */
export interface TrainingTemplateDetail {
  id: string
  name: string
  description: string
  schedule: string[][] // 7天 x 最多3时段的训练项ID
}

/** 前端本地计划单元格元数据 */
export interface LocalPlanCell {
  training_item_id: string | null
  isAutoSuggested: boolean
  isUserModified: boolean
  isMatchDay: boolean
}

/** 训练计划分组（前端使用） */
export interface PlanGroup {
  group_id: string
  name: string
  player_ids: string[]
  training_item_id: string | null
}

/** 训练计划时段数据（前端使用） */
export interface PlanSlotData {
  mode: TrainingMode
  training_item_id: string | null
  groups: PlanGroup[] | null
  isAutoSuggested: boolean
  isUserModified: boolean
  isMatchDay: boolean
}

export interface TrainingResultItem {
  id: string
  player_id: string
  player_name: string | null
  season_day: number
  slot: TrainingSlot
  training_item_id: string
  training_item_name: string | null
  attribute_gains: Record<string, number>
  fitness_before: number
  fitness_after: number
  fatigue_before: number
  fatigue_after: number
  breakthroughs: Array<{
    attribute: string
    from: number
    to: number
  }>
  efficiency: number
  created_at: string
}

export interface TrainingDailySummary {
  season_day: number
  slot: TrainingSlot
  total_players: number
  total_breakthroughs: number
  breakthrough_players: Array<{
    player_id: string
    player_name: string
    attribute: string
    from: number
    to: number
  }>
}

export interface PlayerFatigueItem {
  player_id: string
  player_name: string
  avatar_url?: string
  fitness: number
  fatigue: number
  stamina_preview: number
  fatigue_band: string
  stamina_multiplier: number
  recommendation: string
  can_high_intensity: boolean
}

export interface TeamFatigueResponse {
  team_id: string
  players: PlayerFatigueItem[]
  avg_fitness: number
  avg_fatigue: number
}

export interface PlayerTrainingProgress {
  player_id: string
  player_name: string
  recent_sessions: number
  total_gains: Record<string, number>
  attribute_status: Record<string, {
    current: number
    cap: number
    progress_pct: number
    status: string
  }>
  growth_curve: Record<string, unknown>
}

export interface AutoGroupResponse {
  mode: TrainingMode
  groups: TrainingGroup[]
}

// Category display helpers
export const TRAINING_CATEGORY_COLORS: Record<string, string> = {
  '战术': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  '技术': 'bg-red-500/20 text-red-400 border-red-500/30',
  '恢复': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  'tactic': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  'technical': 'bg-red-500/20 text-red-400 border-red-500/30',
  'recovery': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

export const TRAINING_CATEGORY_BG: Record<string, { bg: string; border: string; text: string }> = {
  '战术': { bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.3)', text: 'text-blue-400' },
  '技术': { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: 'text-red-400' },
  '恢复': { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', text: 'text-emerald-400' },
  'tactic': { bg: 'rgba(59,130,246,0.1)', border: 'rgba(59,130,246,0.3)', text: 'text-blue-400' },
  'technical': { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', text: 'text-red-400' },
  'recovery': { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', text: 'text-emerald-400' },
}

// ==================== 训练套餐模板（与后端 training_config.py 保持一致）====================

export const TRAINING_TEMPLATES: TrainingTemplateDetail[] = [
  {
    id: 'standard_microcycle',
    name: '标准微周期',
    description: '新手默认，攻防、传控、身体和恢复都有覆盖',
    schedule: [
      ['rondo_4v2', 'first_touch_escape', 'mobility_session'],
      ['box_finish_one_touch', 'delay_and_channel', 'match_review_unit'],
      ['repeat_sprint', 'line_breaking_pass', 'full_rest'],
      ['build_up_2_3', 'central_compactness', 'hydro_recovery'],
      ['dribble_cone_tight', 'standing_tackle_timing', 'role_meeting'],
      ['game_model_8v8', 'corner_near_post', 'full_rest'],
      ['full_rest', 'mobility_session', 'opponent_clip_study'],
    ],
  },
  {
    id: 'finishing_week',
    name: '禁区终结周',
    description: '提升射门、镇定、远射、爆发力，适合进球效率低的球队',
    schedule: [
      ['box_finish_one_touch', 'near_post_finish', 'mobility_session'],
      ['box_finish_under_pressure', 'cutback_finish', 'match_review_unit'],
      ['weak_foot_finish', 'long_shot_window', 'full_rest'],
      ['volley_second_ball', 'penalty_routine', 'hydro_recovery'],
      ['box_finish_one_touch', 'penalty_pressure', 'role_meeting'],
      ['cutback_finish', 'far_post_arrival', 'full_rest'],
      ['full_rest', 'mobility_session', 'opponent_clip_study'],
    ],
  },
  {
    id: 'possession_week',
    name: '控球出球周',
    description: '提升传球、控球、视野、球商，适合中后场控球和出球',
    schedule: [
      ['rondo_4v2', 'first_touch_escape', 'mobility_session'],
      ['third_man_combination', 'switch_play', 'match_review_unit'],
      ['line_breaking_pass', 'back_to_goal_link', 'full_rest'],
      ['build_out_under_press', 'receiving_scanning', 'hydro_recovery'],
      ['wall_pass_timing', 'transition_attack', 'role_meeting'],
      ['game_model_8v8', 'build_up_2_3', 'full_rest'],
      ['full_rest', 'mobility_session', 'opponent_clip_study'],
    ],
  },
  {
    id: 'high_press_week',
    name: '高压反抢周',
    description: '提升体能、抢断、防守意识、球商、爆发力，强度高',
    schedule: [
      ['press_trigger', 'counterpress_after_loss', 'mobility_session'],
      ['cover_shadow_press', 'recovery_run', 'match_review_unit'],
      ['repeat_sprint', 'change_direction', 'full_rest'],
      ['accel_5m', 'transition_defense', 'hydro_recovery'],
      ['standing_tackle_timing', 'delay_and_channel', 'role_meeting'],
      ['game_model_8v8', 'aerobic_blocks', 'full_rest'],
      ['full_rest', 'hydro_recovery', 'opponent_clip_study'],
    ],
  },
  {
    id: 'recovery_week',
    name: '密集赛程恢复周',
    description: '多恢复和低强度认知课，适合连续比赛后调整',
    schedule: [
      ['full_rest', 'hydro_recovery', 'mobility_session'],
      ['recovery_bike', 'match_review_unit', 'opponent_clip_study'],
      ['individual_treatment', 'role_meeting', 'full_rest'],
      ['mobility_session', 'captain_meeting', 'hydro_recovery'],
      ['full_rest', 'opponent_clip_study', 'recovery_bike'],
      ['match_review_unit', 'mobility_session', 'full_rest'],
      ['full_rest', 'hydro_recovery', 'individual_treatment'],
    ],
  },
]

/** 获取模板的默认训练项ID（按天偏移和时段索引） */
export function getTemplateItemId(template: TrainingTemplateDetail, dayOffset: number, slotIndex: number): string | null {
  const daySchedule = template.schedule[dayOffset % template.schedule.length]
  if (!daySchedule) return null
  return daySchedule[slotIndex] ?? null
}


export interface TrainingProgressPoint {
  season_day: number
  value: number
}

export interface TrainingProgressBreakthrough {
  season_day: number
  attribute: string
  before: number
  after: number
}

export interface TrainingProgressSeries {
  player_id: string
  player_name: string
  avatar_url?: string
  values: TrainingProgressPoint[]
  breakthroughs: TrainingProgressBreakthrough[]
}

export interface TrainingProgressResponse {
  metric: string
  metric_label: string
  start_day: number
  end_day: number
  series: TrainingProgressSeries[]
}
