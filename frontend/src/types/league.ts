// League types

export interface LeagueSystem {
  id: string
  name: string
  code: string
  description?: string
  max_teams_per_league: number
}

export interface League {
  id: string
  name: string
  level: number
  system_id: string
  system_code: string
  system_name: string
  max_teams: number
  promotion_spots: number
  relegation_spots: number
  has_promotion_playoff: boolean
  has_relegation_playoff: boolean
  teams_count: number
}

export interface Season {
  id: string
  season_number: number
  name: string
  start_date: string
  end_date?: string
  status: 'upcoming' | 'ongoing' | 'completed'
}

export interface StandingTeam {
  id: string
  name: string
  short_name?: string
}

export interface LeagueStanding {
  position: number
  team: StandingTeam
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  form?: string
  is_promotion_zone: boolean
  is_relegation_zone: boolean
}

export interface MatchTeam {
  id: string
  name: string
  short_name?: string
}

export interface Match {
  id: string
  matchday: number
  home_team: MatchTeam
  away_team: MatchTeam
  home_score?: number
  away_score?: number
  status: 'scheduled' | 'ongoing' | 'finished' | 'postponed' | 'cancelled'
  scheduled_at: string
}

export interface LeagueDetail extends League {
  current_season?: Season
  standings: LeagueStanding[]
  recent_matches: Match[]
  upcoming_matches: Match[]
}

export interface TopScorer {
  rank: number
  player_id: string
  player_name: string
  team_name: string
  goals: number
  matches: number
}

export interface TopAssist {
  rank: number
  player_id: string
  player_name: string
  team_name: string
  assists: number
  matches: number
}

export interface CleanSheet {
  rank: number
  player_id: string
  player_name: string
  team_name: string
  clean_sheets: number
  matches: number
}
