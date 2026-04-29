/**
 * 赛季相关类型定义
 */

export interface Season {
  id: string;
  season_number: number;
  status: 'pending' | 'ongoing' | 'finished';
  start_date: string;
  end_date?: string;
  current_day: number;
  current_league_round: number;
  current_cup_round: number;
  total_days: number;
}

export interface SeasonDetail extends Season {
  end_date?: string;
  league_days: number;
  cup_start_day: number;
  cup_interval: number;
  offseason_start: number;
}

export interface Fixture {
  id: string;
  fixture_type: 'league' | 'cup_lightning_group' | 'cup_lightning_knockout' | 'cup_jenny';
  season_day: number;
  round_number: number;
  home_team_id: string;
  away_team_id: string;
  home_score?: number;
  away_score?: number;
  status: 'scheduled' | 'ongoing' | 'finished';
  cup_stage?: string;
  cup_group?: string;
  scheduled_at: string;
}

export interface SeasonStatusForDisplay {
  season_number: number;
  current_day: number;
  total_days: number;
  progress_percent: number;
  
  // 今日比赛信息
  has_league: boolean;
  has_cup: boolean;
  league_round?: number;
  cup_round?: number;
  cup_stage?: string;
  total_fixtures_today: number;
  
  // 显示文本
  display_text: string;
}

export interface TodayFixturesResponse {
  season_number: number;
  current_day: number;
  fixtures: Fixture[];
}

export interface SeasonCalendarDay {
  day: number;
  date: string;
  fixtures: {
    id: string;
    type: string;
    round: number;
    home_team_id: string;
    away_team_id: string;
    home_team_name: string;
    away_team_name: string;
    home_score?: number;
    away_score?: number;
    status: string;
    cup_stage?: string;
    cup_group?: string;
  }[];
}

export interface SeasonCalendarResponse {
  season_number: number;
  team_id?: string;
  calendar: SeasonCalendarDay[];
}
