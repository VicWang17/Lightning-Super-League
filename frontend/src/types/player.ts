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
  height: number
  weight: number
  birth_offset: number
  age: number

  // 19项属性 (1-20) - 兼容平铺和嵌套两种格式
  abilities?: {
    sho: number; pas: number; dri: number; spd: number; str: number; sta: number
    acc: number; hea: number; bal: number; defe: number; tkl: number; vis: number
    cro: number; con: number; fin: number; com: number; sav: number; ref: number
    pos: number; set: number; dec: number
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
  defe: number  // 站位（防守站位）
  tkl: number   // 抢断
  vis: number   // 视野
  cro: number   // 传中
  con: number   // 控球
  fin: number   // 远射
  com: number   // 镇定
  sav: number   // 扑救
  ref: number   // 反应
  pos: number   // 跑位（进攻选位）
  set: number   // 定位球
  dec: number   // 球商

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
  team_id?: string
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
