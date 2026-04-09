// Team types

export interface Team {
  id: string
  name: string
  short_name?: string
  logo_url?: string
  stadium?: string
  city?: string
  founded_year?: number
  reputation: number
  overall_rating: number
  status: 'active' | 'inactive' | 'suspended'
  user_id: string
  league_id?: string
  season_id?: string
  created_at: string
  updated_at: string
}

export interface TeamFinancials {
  balance: number
  weekly_wages: number
  stadium_capacity: number
  ticket_price: number
}

export interface TeamStats {
  matches_played: number
  wins: number
  draws: number
  losses: number
  goals_for: number
  goals_against: number
  points: number
  league_position?: number
}

export interface TeamDetail extends Team {
  financials?: TeamFinancials
  stats?: TeamStats
}

export interface TeamSummary {
  id: string
  name: string
  short_name?: string
  logo_url?: string
  overall_rating: number
  league_position?: number
}
