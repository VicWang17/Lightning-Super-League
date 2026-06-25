// Cup types - 杯赛类型定义

export interface CupCompetition {
  id: string
  name: string
  code: string
  season_id: string
  season_number: number
  status: 'pending' | 'ongoing' | 'finished'
  current_round: number
  total_teams: number
  has_group_stage: boolean
  group_count: number
  teams_per_group: number
  group_rounds: number
  eligible_league_levels: number[]
  winner_team_id?: string | null
  winner_team_name?: string | null
}

export interface CupGroup {
  id: string
  competition_id: string
  name: string  // A, B, C...
  team_ids: string[]
  teams?: CupGroupTeam[]
  standings?: Record<string, CupGroupStanding>
  qualified_team_ids?: string[]
}

export interface CupGroupTeam {
  id: string
  name: string
}

export interface CupGroupStanding {
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  points: number
}

export interface CupFixture {
  id: string
  season_day: number
  round_number: number
  fixture_type: string
  home_team: {
    id: string
    name: string
  }
  away_team: {
    id: string
    name: string
  }
  home_score?: number
  away_score?: number
  winner_team_id?: string | null
  resolution?: 'regular' | 'extra_time' | 'penalties' | 'draw' | string | null
  penalty_score?: {
    home: number
    away: number
  } | null
  status: 'scheduled' | 'ongoing' | 'finished'
  cup_stage?: string  // GROUP, ROUND_32, ROUND_16, QUARTER, SEMI, FINAL
  cup_group_name?: string
  scheduled_at: string
}

export interface CupDetail extends CupCompetition {
  groups?: CupGroup[]
  fixtures?: CupFixture[]
  knockout_fixtures?: CupFixture[]
}

// 淘汰赛对阵树节点
export interface KnockoutMatchNode {
  id: string
  round: number
  stage: string
  match: CupFixture
  next_match_id?: string
  position: number  // 在对阵树中的位置
}

// 杯赛阶段配置
export const CUP_STAGE_CONFIG: Record<string, { name: string; color: string }> = {
  GROUP: { name: '小组赛', color: 'bg-[#59C7EE]' },
  ROUND_48: { name: '预选赛', color: 'bg-[#8B5A2B]/40' },
  ROUND_32: { name: '32强', color: 'bg-[#1F5F43]' },
  ROUND_16: { name: '16强', color: 'bg-[#FF6F59]' },
  QUARTER: { name: '1/4决赛', color: 'bg-[#FFC247]' },
  SEMI: { name: '半决赛', color: 'bg-[#FF6F59]' },
  FINAL: { name: '决赛', color: 'bg-[#B9EF3F]' },
}

// 杯赛配置
export const CUP_CONFIG: Record<string, { description: string }> = {
  LIGHTNING_CUP: {
    description: '顶级杯赛，64支球队参赛，小组赛+淘汰赛制'
  },
  JENNY_CUP: {
    description: '次级联赛杯赛，192支球队参赛，纯淘汰赛制'
  },
}

// 提取杯赛基础 code（处理 JENNY_CUP_west → JENNY_CUP）
export function getCupBaseCode(code: string): string {
  const upper = code.toUpperCase()
  if (upper.startsWith('JENNY_CUP')) return 'JENNY_CUP'
  if (upper.startsWith('LIGHTNING_CUP')) return 'LIGHTNING_CUP'
  return code
}

// 小组名列表（闪电杯16个小组）
export const GROUP_NAMES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
