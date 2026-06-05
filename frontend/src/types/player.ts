// Player types - PRD v5 简化版

export type PlayerPosition = 'FW' | 'MF' | 'DF' | 'GK'
export type PlayerRace = 'asian' | 'western'
export type PlayerFoot = 'LEFT' | 'RIGHT' | 'BOTH'
export type PlayerStatus = 'ACTIVE' | 'INJURED' | 'SUSPENDED' | 'RETIRED'
export type MatchForm = 'HOT' | 'GOOD' | 'NEUTRAL' | 'LOW'
export type PotentialLetter = 'S' | 'A' | 'B' | 'C' | 'D'
export type ContractType = 'NORMAL' | 'ROOKIE' | 'FREE'
export type SquadRole = 'key_player' | 'first_team' | 'rotation' | 'backup' | 'hot_prospect' | 'youngster' | 'not_needed'

export interface PlayerSkill {
  skill_id: string
  rarity: string
  quality?: string
  color?: 'white' | 'blue' | 'purple' | 'red'
  type?: string
  trigger: string
  effect: string
}

export interface Player {
  id: string
  name: string
  race: PlayerRace
  avatar_url?: string
  position: PlayerPosition
  preferred_foot: PlayerFoot
  preferred_number: number
  squad_number?: number
  height: number
  weight: number
  birth_offset: number
  age: number

  // 23项属性 (1-20) - 兼容平铺和嵌套两种格式
  abilities?: {
    sho: number; pas: number; dri: number; spd: number; str: number; sta: number
    acc: number; hea: number; bal: number; defe: number; tkl: number; vis: number
    cro: number; con: number; fin: number; com: number; sav: number; ref: number
    pos: number; rus: number; dec: number; fk: number; pk: number
  }
  sho: number   // 射门
  pas: number   // 传球
  dri: number   // 盘带
  spd: number   // 速度
  str: number   // 力量
  sta: number   // 体能
  acc: number   // 爆发力
  hea: number   // 头球
  bal: number   // 平衡
  defe: number  // 防守意识
  tkl: number   // 抢断
  vis: number   // 视野
  cro: number   // 传中
  con: number   // 控球
  fin: number   // 远射
  com: number   // 镇定
  sav: number   // 扑救
  ref: number   // 反应
  pos: number   // 站位
  rus: number   // 出击
  dec: number   // 球商
  fk: number    // 任意球
  pk: number    // 点球

  ovr: number
  potential_letter: PotentialLetter
  skills: PlayerSkill[]

  status: PlayerStatus
  match_form: MatchForm
  fitness: number

  contract_type: ContractType
  contract_end_season?: number
  wage: number
  release_clause?: number
  squad_role: SquadRole
  market_value: number
  match_rust_score?: number

  matches_played: number
  goals: number
  assists: number
  yellow_cards: number
  red_cards: number
  average_rating: number
  minutes_played: number

  // 进攻
  shots: number
  shots_on_target: number
  shot_accuracy: number
  dribbles: number
  dribbles_succ: number
  dribble_accuracy: number
  headers: number
  headers_succ: number
  header_accuracy: number

  // 传球
  passes: number
  passes_succ: number
  pass_accuracy: number
  key_passes: number
  crosses: number
  crosses_succ: number
  cross_accuracy: number

  // 防守
  tackles: number
  tackles_succ: number
  tackle_accuracy: number
  interceptions: number
  clearances: number
  blocks: number

  // 门将
  saves: number
  clean_sheets: number

  // 纪律/其他
  fouls: number
  fouls_drawn: number
  offsides: number
  turnovers: number
  touches: number
  free_kicks: number
  free_kick_goals: number
  penalties: number
  penalty_goals: number

  team_id?: string
  created_at: string
  updated_at: string
}

export interface PlayerStats {
  matches_played: number
  goals: number
  assists: number
  yellow_cards: number
  red_cards: number
  average_rating: number
  minutes_played: number

  // 进攻
  shots: number
  shots_on_target: number
  shot_accuracy: number
  dribbles: number
  dribbles_succ: number
  dribble_accuracy: number
  headers: number
  headers_succ: number
  header_accuracy: number

  // 传球
  passes: number
  passes_succ: number
  pass_accuracy: number
  key_passes: number
  crosses: number
  crosses_succ: number
  cross_accuracy: number

  // 防守
  tackles: number
  tackles_succ: number
  tackle_accuracy: number
  interceptions: number
  clearances: number
  blocks: number

  // 门将
  saves: number
  clean_sheets: number

  // 纪律/其他
  fouls: number
  fouls_drawn: number
  offsides: number
  turnovers: number
  touches: number
  free_kicks: number
  free_kick_goals: number
  penalties: number
  penalty_goals: number
}

export interface PlayerListItem {
  id: string
  name: string
  race: PlayerRace
  avatar_url?: string
  age: number
  position: PlayerPosition
  ovr: number
  potential_letter: PotentialLetter
  market_value: number
  squad_number?: number
  team_id?: string
  matches_played: number
  minutes_played: number
  goals: number
  assists: number
  average_rating: number
  yellow_cards: number
  red_cards: number
  // 进攻
  shots: number
  shots_on_target: number
  dribbles: number
  dribbles_succ: number
  headers: number
  headers_succ: number
  // 传球
  passes: number
  passes_succ: number
  key_passes: number
  crosses: number
  crosses_succ: number
  // 防守
  tackles: number
  tackles_succ: number
  interceptions: number
  clearances: number
  blocks: number
  // 门将
  saves: number
  clean_sheets: number
  // 纪律/其他
  fouls: number
  fouls_drawn: number
  offsides: number
  turnovers: number
  touches: number
  free_kicks: number
  free_kick_goals: number
  penalties: number
  penalty_goals: number
}

// =====================================================================
// Contract & State types (v1 新增)
// =====================================================================

export interface PlayerContract {
  player_id: string
  team_id: string | null
  contract_type: ContractType
  start_season_number: number
  end_season_number: number | null
  wage: number
  recommended_wage: number
  wage_ratio: number
  release_clause: number | null
  squad_role: SquadRole
  status: string
  created_at: string
}

export interface ContractPreview {
  recommended_wage: number
  offered_wage: number
  wage_ratio: number
  visible_reaction: string
  hidden_wage_satisfaction: number
  wage_cap_after_pct: number
  can_submit: boolean
  warnings: string[]
}

export interface ContractOffer {
  team_id: string
  contract_type: ContractType
  years: number
  wage: number
  squad_role: SquadRole
  release_clause?: number
}

export interface PlayerState {
  player_id: string
  visible_form: MatchForm
  fitness: number
  availability: PlayerStatus
  trend: string
  hints: string[]
  state_score?: number
  contract_score?: number
  recent_match_score?: number
  fitness_score?: number
  match_load_score?: number
  match_rust_score?: number
}

export interface TeamPlayerStates {
  team_id: string
  players: PlayerState[]
}

// =====================================================================
// Growth Curve types
// =====================================================================

export interface GrowthCurvePoint {
  age: number
  ovr: number
  is_projected: boolean
}

export interface AttributeProgressItem {
  attribute: string
  label: string
  current: number
  cap: number
  progress_pct: number
}

export interface PlayerGrowthData {
  current_age: number
  current_ovr: number
  peak_age: number
  curve_type: string
  curve_type_label: string
  growth_speed: number
  stability: number
  late_bloom_factor: number
  projected_curve: GrowthCurvePoint[]
  attribute_progress: AttributeProgressItem[]
}

// Position display names
export const POSITION_NAMES: Record<PlayerPosition, string> = {
  FW: '前锋',
  MF: '中场',
  DF: '后卫',
  GK: '门将',
}

// Position colors
export const POSITION_COLORS: Record<PlayerPosition, string> = {
  FW: 'bg-red-500 text-white',
  MF: 'bg-emerald-500 text-white',
  DF: 'bg-blue-500 text-white',
  GK: 'bg-amber-500 text-black',
}

export function getPositionColor(position: PlayerPosition): string {
  return POSITION_COLORS[position]
}

export function getPositionGroup(position: PlayerPosition): PlayerPosition {
  return position
}
