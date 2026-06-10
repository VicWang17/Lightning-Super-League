// Leaderboard types

export type LeaderboardType =
  | 'goals'
  | 'assists'
  | 'clean_sheets'
  | 'saves'
  | 'tackles'
  | 'interceptions'
  | 'clearances'
  | 'blocks'
  | 'shots'
  | 'shots_on_target'
  | 'key_passes'
  | 'passes'
  | 'crosses'
  | 'dribbles'
  | 'yellow_cards'
  | 'red_cards'
  | 'fouls'
  | 'offsides'
  | 'touches'
  | 'free_kick_goals'
  | 'penalty_goals'
  | 'minutes'
  | 'appearances'
  | 'rating'
  | 'shot_accuracy'
  | 'pass_accuracy'
  | 'tackle_accuracy'
  | 'dribble_accuracy'
  | 'cross_accuracy'
  | 'header_accuracy'
  | 'goals_per_game'
  | 'assists_per_game'

export interface LeaderboardItem {
  rank: number
  player_id: string
  player_name: string
  avatar_url?: string
  position: string
  team_name: string
  team_id: string
  value: number
  value_label: string
  matches: number
}

export interface LeaderboardConfig {
  type: LeaderboardType
  label: string
  icon: string
}
