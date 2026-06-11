// Award types - 球员荣誉/奖项类型

export type AwardType =
  | 'match_mvp'
  | 'league_team_of_season'
  | 'league_best_fw' | 'league_best_mf' | 'league_best_df' | 'league_best_gk'
  | 'league_golden_boot' | 'league_playmaker' | 'league_golden_glove' | 'league_golden_wall'
  | 'cup_golden_boot' | 'cup_playmaker' | 'cup_golden_glove' | 'cup_golden_wall'
  | 'season_best_player'
  | 'season_best_fw' | 'season_best_mf' | 'season_best_df' | 'season_best_gk'
  | 'season_golden_boot' | 'season_playmaker' | 'season_golden_glove' | 'season_golden_wall'

export type AwardLevel = 'match' | 'league' | 'cup' | 'season'

export interface AwardMetadata {
  rating?: number
  matches?: number
  goals?: number
  assists?: number
  clean_sheets?: number
  tackles?: number
  interceptions?: number
  saves?: number
  championships?: number
  mvp_count?: number
  primary_value?: number
  position_rank?: number
  team?: string
  opponent?: string
  match_result?: string
  cup_name?: string
}

export interface PlayerAward {
  id: string
  player_id: string
  player_name?: string
  player_avatar_url?: string
  player_position?: string
  season_id: string
  season_number: number
  award_type: AwardType
  award_level: AwardLevel
  league_id?: string
  league_name?: string
  cup_id?: string
  cup_name?: string
  fixture_id?: string
  position?: 'FW' | 'MF' | 'DF' | 'GK'
  metadata?: AwardMetadata
  description?: string
  created_at: string
}

export interface PlayerAwardSummary {
  total_awards: number
  mvp_count: number
  team_of_season_count: number
  best_position_count: number
  golden_boot_count: number
  playmaker_count: number
  golden_glove_count: number
  golden_wall_count: number
  season_best_player_count: number
}

export interface SeasonAwards {
  season_id: string
  season_number: number
  best_player?: PlayerAward
  best_fw?: PlayerAward
  best_mf?: PlayerAward
  best_df?: PlayerAward
  best_gk?: PlayerAward
  golden_boot?: PlayerAward
  playmaker?: PlayerAward
  golden_glove?: PlayerAward
  golden_wall?: PlayerAward
}

export interface LeagueAwards {
  league_id: string
  season_id: string
  season_number: number
  team_of_season: PlayerAward[]
  best_fw?: PlayerAward
  best_mf?: PlayerAward
  best_df?: PlayerAward
  best_gk?: PlayerAward
  golden_boot?: PlayerAward
  playmaker?: PlayerAward
  golden_glove?: PlayerAward
  golden_wall?: PlayerAward
}

export interface CupAwards {
  cup_id: string
  season_id: string
  season_number: number
  golden_boot?: PlayerAward
  playmaker?: PlayerAward
  golden_glove?: PlayerAward
  golden_wall?: PlayerAward
}

export const AWARD_LABELS: Record<AwardType, string> = {
  match_mvp: '本场最佳',
  league_team_of_season: '联赛最佳阵容',
  league_best_fw: '联赛最佳前锋',
  league_best_mf: '联赛最佳中场',
  league_best_df: '联赛最佳后卫',
  league_best_gk: '联赛最佳门将',
  league_golden_boot: '联赛金靴奖',
  league_playmaker: '联赛助攻王',
  league_golden_glove: '联赛金手套奖',
  league_golden_wall: '联赛金墙奖',
  cup_golden_boot: '杯赛金靴奖',
  cup_playmaker: '杯赛助攻王',
  cup_golden_glove: '杯赛金手套奖',
  cup_golden_wall: '杯赛金墙奖',
  season_best_player: '闪电足球先生',
  season_best_fw: '年度最佳前锋',
  season_best_mf: '年度最佳中场',
  season_best_df: '年度最佳后卫',
  season_best_gk: '年度最佳门将',
  season_golden_boot: '赛季金靴奖',
  season_playmaker: '赛季助攻王',
  season_golden_glove: '赛季金手套奖',
  season_golden_wall: '赛季金墙奖',
}

export const AWARD_ICONS: Record<AwardType, string> = {
  match_mvp: '⚽',
  league_team_of_season: '⭐',
  league_best_fw: '🔥',
  league_best_mf: '🔥',
  league_best_df: '🛡️',
  league_best_gk: '🧤',
  league_golden_boot: '🥾',
  league_playmaker: '👟',
  league_golden_glove: '🧤',
  league_golden_wall: '🧱',
  cup_golden_boot: '🥾',
  cup_playmaker: '👟',
  cup_golden_glove: '🧤',
  cup_golden_wall: '🧱',
  season_best_player: '👑',
  season_best_fw: '🔥',
  season_best_mf: '🔥',
  season_best_df: '🛡️',
  season_best_gk: '🧤',
  season_golden_boot: '🥾',
  season_playmaker: '👟',
  season_golden_glove: '🧤',
  season_golden_wall: '🧱',
}

export const AWARD_COLORS: Record<AwardType, string> = {
  match_mvp: 'text-amber-400',
  league_team_of_season: 'text-cyan-400',
  league_best_fw: 'text-red-400',
  league_best_mf: 'text-emerald-400',
  league_best_df: 'text-blue-400',
  league_best_gk: 'text-amber-400',
  league_golden_boot: 'text-yellow-400',
  league_playmaker: 'text-green-400',
  league_golden_glove: 'text-sky-400',
  league_golden_wall: 'text-orange-400',
  cup_golden_boot: 'text-yellow-400',
  cup_playmaker: 'text-green-400',
  cup_golden_glove: 'text-sky-400',
  cup_golden_wall: 'text-orange-400',
  season_best_player: 'text-[#C6F135]',
  season_best_fw: 'text-red-400',
  season_best_mf: 'text-emerald-400',
  season_best_df: 'text-blue-400',
  season_best_gk: 'text-amber-400',
  season_golden_boot: 'text-yellow-400',
  season_playmaker: 'text-green-400',
  season_golden_glove: 'text-sky-400',
  season_golden_wall: 'text-orange-400',
}
