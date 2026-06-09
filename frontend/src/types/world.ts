// World page types

export interface WorldRanking {
  rank: number
  team_id: string
  team_name: string
  total_score: number
  league_score: number
  cup_score: number
  cup_titles: number
}

export interface TopPlayer {
  rank: number
  player_id: string
  player_name: string
  avatar_url?: string
  position: string
  age: number
  ovr: number
  team_name: string
  team_id: string
}

export interface TeamHonor {
  season_number: number
  honor_type: 'league_champion' | 'cup_champion'
  competition_name: string
  competition_level: number | null
}

export interface TeamHonorsResponse {
  honors: TeamHonor[]
  total_league_titles: number
  total_cup_titles: number
}
