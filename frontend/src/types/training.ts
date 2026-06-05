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
