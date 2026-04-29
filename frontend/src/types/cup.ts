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

export interface CupTopScorer {
  rank: number
  player_id: string
  player_name: string
  team_name: string
  goals: number
  matches: number
}

export interface CupTopAssist {
  rank: number
  player_id: string
  player_name: string
  team_name: string
  assists: number
  matches: number
}

export interface CupCleanSheet {
  rank: number
  player_id: string
  player_name: string
  team_name: string
  clean_sheets: number
  matches: number
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
  GROUP: { name: '小组赛', icon: '⚔️', color: 'bg-blue-500' },
  ROUND_48: { name: '预选赛', icon: '🎯', color: 'bg-slate-500' },
  ROUND_32: { name: '32强', icon: '🏆', color: 'bg-emerald-500' },
  ROUND_16: { name: '16强', icon: '🏆', color: 'bg-violet-500' },
  QUARTER: { name: '1/4决赛', icon: '⚡', color: 'bg-amber-500' },
  SEMI: { name: '半决赛', icon: '🔥', color: 'bg-rose-500' },
  FINAL: { name: '决赛', icon: '👑', color: 'bg-yellow-400' },
}

// 杯赛配置
export const CUP_CONFIG: Record<string, { icon: string; color: string; gradient: string; description: string }> = {
  LIGHTNING_CUP: {
    icon: '⚡',
    color: 'text-yellow-400',
    gradient: 'bg-yellow-500/20',
    description: '顶级杯赛，64支球队参赛，小组赛+淘汰赛制'
  },
  JENNY_CUP: {
    icon: '🏆',
    color: 'text-emerald-400',
    gradient: 'bg-emerald-500/20',
    description: '次级联赛杯赛，192支球队参赛，纯淘汰赛制'
  },
}

// 小组名列表（闪电杯16个小组）
export const GROUP_NAMES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
