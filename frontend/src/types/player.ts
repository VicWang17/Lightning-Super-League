// Player types

export type PlayerPosition = 
  | 'GK' | 'CB' | 'LB' | 'RB' | 'LWB' | 'RWB'
  | 'CDM' | 'CM' | 'CAM' | 'LM' | 'RM'
  | 'LW' | 'RW' | 'LF' | 'RF' | 'ST' | 'CF'

export type PlayerFoot = 'left' | 'right' | 'both'
export type PlayerStatus = 'active' | 'injured' | 'suspended' | 'retired'
export type SquadRole = 'key_player' | 'first_team' | 'rotation' | 'backup' | 'hot_prospect' | 'youngster' | 'not_needed'

export interface Player {
  id: string
  first_name: string
  last_name: string
  display_name?: string
  nationality: string
  birth_date: string
  age: number
  height?: number
  weight?: number
  preferred_foot: PlayerFoot
  primary_position: PlayerPosition
  secondary_position?: PlayerPosition
  
  // Abilities
  shooting: number
  finishing: number
  long_shots: number
  passing: number
  vision: number
  crossing: number
  dribbling: number
  ball_control: number
  defending: number
  tackling: number
  marking: number
  pace: number
  acceleration: number
  strength: number
  stamina: number
  diving: number
  handling: number
  kicking: number
  reflexes: number
  positioning: number
  aggression: number
  composure: number
  work_rate: number
  
  overall_rating: number
  potential: number
  
  status: PlayerStatus
  fitness: number
  morale: number
  form: number
  
  wage: number
  contract_end?: string
  release_clause?: number
  squad_role: SquadRole
  market_value: number
  
  // Stats
  matches_played: number
  goals: number
  assists: number
  yellow_cards: number
  red_cards: number
  average_rating: number
  minutes_played: number
  
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
}

export interface PlayerDetail extends Player {
  stats?: PlayerStats
}

// Position display names
export const POSITION_NAMES: Record<PlayerPosition, string> = {
  GK: '门将',
  CB: '中后卫',
  LB: '左后卫',
  RB: '右后卫',
  LWB: '左翼卫',
  RWB: '右翼卫',
  CDM: '防守型中场',
  CM: '中场',
  CAM: '进攻型中场',
  LM: '左中场',
  RM: '右中场',
  LW: '左边锋',
  RW: '右边锋',
  LF: '左前锋',
  RF: '右前锋',
  ST: '前锋',
  CF: '中锋',
}

// Position colors
export const POSITION_COLORS: Record<string, string> = {
  GK: 'bg-amber-500 text-black',
  DF: 'bg-blue-500 text-white',
  MF: 'bg-emerald-500 text-white',
  FW: 'bg-red-500 text-white',
}

export function getPositionColor(position: PlayerPosition): string {
  if (position === 'GK') return POSITION_COLORS.GK
  if (['CB', 'LB', 'RB', 'LWB', 'RWB'].includes(position)) return POSITION_COLORS.DF
  if (['CDM', 'CM', 'CAM', 'LM', 'RM'].includes(position)) return POSITION_COLORS.MF
  return POSITION_COLORS.FW
}

export function getPositionGroup(position: PlayerPosition): string {
  if (position === 'GK') return 'GK'
  if (['CB', 'LB', 'RB', 'LWB', 'RWB'].includes(position)) return 'DF'
  if (['CDM', 'CM', 'CAM', 'LM', 'RM'].includes(position)) return 'MF'
  return 'FW'
}
