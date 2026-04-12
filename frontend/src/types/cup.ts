// Cup types - 杯赛类型定义

export interface CupCompetition {
  id: string
  name: string
  code: 'LIGHTNING_CUP' | 'JENNY_CUP'
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
  fixture_type: 'cup_lightning_group' | 'cup_lightning_knockout' | 'cup_jenny'
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
export const CUP_STAGE_CONFIG: Record<string, { name: string; icon: string; color: string }> = {
  GROUP: { name: '小组赛', icon: '⚔️', color: 'from-blue-500 to-cyan-500' },
  ROUND_48: { name: '预选赛', icon: '🎯', color: 'from-slate-500 to-gray-500' },
  ROUND_32: { name: '32强', icon: '🏆', color: 'from-emerald-500 to-teal-500' },
  ROUND_16: { name: '16强', icon: '🏆', color: 'from-violet-500 to-purple-500' },
  QUARTER: { name: '1/4决赛', icon: '⚡', color: 'from-amber-500 to-orange-500' },
  SEMI: { name: '半决赛', icon: '🔥', color: 'from-rose-500 to-pink-500' },
  FINAL: { name: '决赛', icon: '👑', color: 'from-yellow-400 to-amber-500' },
}

// 杯赛配置
export const CUP_CONFIG: Record<string, { icon: string; color: string; gradient: string; description: string }> = {
  LIGHTNING_CUP: {
    icon: '⚡',
    color: 'text-yellow-400',
    gradient: 'from-yellow-500/20 to-amber-500/5',
    description: '顶级杯赛，64支球队参赛，小组赛+淘汰赛制'
  },
  JENNY_CUP: {
    icon: '🏆',
    color: 'text-emerald-400',
    gradient: 'from-emerald-500/20 to-teal-500/5',
    description: '次级联赛杯赛，192支球队参赛，纯淘汰赛制'
  },
}

// 小组名列表（闪电杯16个小组）
export const GROUP_NAMES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
