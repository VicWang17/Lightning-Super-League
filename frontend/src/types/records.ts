export enum RecordScope {
  WORLD = 'world',
  LEAGUE = 'league',
  TEAM = 'team',
  CUP = 'cup',
}

export enum RecordCategory {
  TEAM = 'team',
  PLAYER = 'player',
  MATCH = 'match',
}

export enum RecordType {
  // 生涯累计
  CAREER_GOALS = 'career_goals',
  CAREER_ASSISTS = 'career_assists',
  CAREER_APPEARANCES = 'career_appearances',
  CAREER_YELLOW_CARDS = 'career_yellow_cards',
  CAREER_RED_CARDS = 'career_red_cards',
  CAREER_RATING = 'career_rating',
  CAREER_PASSES = 'career_passes',
  CAREER_KEY_PASSES = 'career_key_passes',
  CAREER_TACKLES = 'career_tackles',
  CAREER_INTERCEPTIONS = 'career_interceptions',
  CAREER_CLEARANCES = 'career_clearances',
  CAREER_SHOTS = 'career_shots',
  CAREER_SHOTS_ON_TARGET = 'career_shots_on_target',
  CAREER_SAVES = 'career_saves',
  CAREER_CLEAN_SHEETS = 'career_clean_sheets',
  CAREER_FOULS = 'career_fouls',
  CAREER_OFFSIDES = 'career_offsides',

  // 单赛季
  SEASON_GOALS = 'season_goals',
  SEASON_ASSISTS = 'season_assists',
  SEASON_RATING = 'season_rating',
  SEASON_PASSES = 'season_passes',
  SEASON_KEY_PASSES = 'season_key_passes',
  SEASON_TACKLES = 'season_tackles',
  SEASON_INTERCEPTIONS = 'season_interceptions',
  SEASON_CLEARANCES = 'season_clearances',
  SEASON_SHOTS = 'season_shots',
  SEASON_SHOTS_ON_TARGET = 'season_shots_on_target',
  SEASON_SAVES = 'season_saves',
  SEASON_CLEAN_SHEETS = 'season_clean_sheets',
  SEASON_FOULS = 'season_fouls',
  SEASON_OFFSIDES = 'season_offsides',

  // 单场 / 球员单场
  MATCH_GOALS = 'match_goals',
  MATCH_ASSISTS = 'match_assists',
  MATCH_PASSES = 'match_passes',
  MATCH_KEY_PASSES = 'match_key_passes',
  MATCH_TACKLES = 'match_tackles',
  MATCH_INTERCEPTIONS = 'match_interceptions',
  MATCH_SHOTS = 'match_shots',
  MATCH_SHOTS_ON_TARGET = 'match_shots_on_target',
  MATCH_SAVES = 'match_saves',
  MATCH_FOULS = 'match_fouls',
  MATCH_OFFSIDES = 'match_offsides',
  FASTEST_GOAL = 'fastest_goal',
  YOUNGEST_SCORER = 'youngest_scorer',
  OLDEST_SCORER = 'oldest_scorer',
  HAT_TRICKS = 'hat_tricks',
  SCORING_STREAK = 'scoring_streak',
  ASSIST_STREAK = 'assist_streak',

  // 球队
  SEASON_TEAM_GOALS = 'season_team_goals',
  SEASON_TEAM_GOALS_AGAINST = 'season_team_goals_against',
  SEASON_TEAM_POINTS = 'season_team_points',
  SEASON_TEAM_WINS = 'season_team_wins',
  SEASON_TEAM_CLEAN_SHEETS = 'season_team_clean_sheets',
  BIGGEST_WIN_MARGIN = 'biggest_win_margin',
  BIGGEST_DEFEAT_MARGIN = 'biggest_defeat_margin',
  MOST_GOALS_IN_MATCH = 'most_goals_in_match',
  LONGEST_WIN_STREAK = 'longest_win_streak',
  LONGEST_UNBEATEN = 'longest_unbeaten',
  LONGEST_LOSING_STREAK = 'longest_losing_streak',
}

export interface RecordItem {
  id: string
  scope: RecordScope
  category: RecordCategory
  record_type: RecordType
  record_type_label: string
  holder_name: string
  holder_id: string
  holder_avatar_url?: string
  holder_team_name?: string
  holder_team_id?: string
  record_value: string
  record_value_numeric: number
  season_number?: number
  match_date?: string
  fixture_id?: string
  context: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface TeamSeasonHistoryItem {
  season_number: number
  league_name: string
  league_level: number
  position: number
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  top_scorer_name?: string
  top_scorer_goals: number
}

export interface TeamHistoryResponse {
  seasons: TeamSeasonHistoryItem[]
  record_count: number
  trophies: Array<{
    season_number: number
    honor_type: string
    competition_name: string
    competition_level: number | null
  }>
}

export interface RecordsByCategory {
  team: RecordItem[]
  player: RecordItem[]
  match: RecordItem[]
}

export const RECORD_TYPE_LABELS: Record<RecordType, string> = {
  [RecordType.CAREER_GOALS]: '生涯总进球',
  [RecordType.CAREER_ASSISTS]: '生涯总助攻',
  [RecordType.CAREER_APPEARANCES]: '生涯出场',
  [RecordType.CAREER_YELLOW_CARDS]: '生涯黄牌',
  [RecordType.CAREER_RED_CARDS]: '生涯红牌',
  [RecordType.CAREER_RATING]: '生涯场均评分',
  [RecordType.CAREER_PASSES]: '生涯传球',
  [RecordType.CAREER_KEY_PASSES]: '生涯关键传球',
  [RecordType.CAREER_TACKLES]: '生涯抢断',
  [RecordType.CAREER_INTERCEPTIONS]: '生涯拦截',
  [RecordType.CAREER_CLEARANCES]: '生涯解围',
  [RecordType.CAREER_SHOTS]: '生涯射门',
  [RecordType.CAREER_SHOTS_ON_TARGET]: '生涯射正',
  [RecordType.CAREER_SAVES]: '生涯扑救',
  [RecordType.CAREER_CLEAN_SHEETS]: '生涯零封',
  [RecordType.CAREER_FOULS]: '生涯犯规',
  [RecordType.CAREER_OFFSIDES]: '生涯越位',

  [RecordType.SEASON_GOALS]: '单赛季进球',
  [RecordType.SEASON_ASSISTS]: '单赛季助攻',
  [RecordType.SEASON_RATING]: '单赛季场均评分',
  [RecordType.SEASON_PASSES]: '单赛季传球',
  [RecordType.SEASON_KEY_PASSES]: '单赛季关键传球',
  [RecordType.SEASON_TACKLES]: '单赛季抢断',
  [RecordType.SEASON_INTERCEPTIONS]: '单赛季拦截',
  [RecordType.SEASON_CLEARANCES]: '单赛季解围',
  [RecordType.SEASON_SHOTS]: '单赛季射门',
  [RecordType.SEASON_SHOTS_ON_TARGET]: '单赛季射正',
  [RecordType.SEASON_SAVES]: '单赛季扑救',
  [RecordType.SEASON_CLEAN_SHEETS]: '单赛季零封',
  [RecordType.SEASON_FOULS]: '单赛季犯规',
  [RecordType.SEASON_OFFSIDES]: '单赛季越位',

  [RecordType.MATCH_GOALS]: '单场进球',
  [RecordType.MATCH_ASSISTS]: '单场助攻',
  [RecordType.MATCH_PASSES]: '单场传球',
  [RecordType.MATCH_KEY_PASSES]: '单场关键传球',
  [RecordType.MATCH_TACKLES]: '单场抢断',
  [RecordType.MATCH_INTERCEPTIONS]: '单场拦截',
  [RecordType.MATCH_SHOTS]: '单场射门',
  [RecordType.MATCH_SHOTS_ON_TARGET]: '单场射正',
  [RecordType.MATCH_SAVES]: '单场扑救',
  [RecordType.MATCH_FOULS]: '单场犯规',
  [RecordType.MATCH_OFFSIDES]: '单场越位',
  [RecordType.FASTEST_GOAL]: '最快进球',
  [RecordType.YOUNGEST_SCORER]: '最年轻进球者',
  [RecordType.OLDEST_SCORER]: '最年长进球者',
  [RecordType.HAT_TRICKS]: '帽子戏法',
  [RecordType.SCORING_STREAK]: '连续进球场次',
  [RecordType.ASSIST_STREAK]: '连续助攻场次',

  [RecordType.SEASON_TEAM_GOALS]: '单赛季进球',
  [RecordType.SEASON_TEAM_GOALS_AGAINST]: '单赛季失球',
  [RecordType.SEASON_TEAM_POINTS]: '单赛季积分',
  [RecordType.SEASON_TEAM_WINS]: '单赛季胜场',
  [RecordType.SEASON_TEAM_CLEAN_SHEETS]: '单赛季零封',
  [RecordType.BIGGEST_WIN_MARGIN]: '最大比分胜利',
  [RecordType.BIGGEST_DEFEAT_MARGIN]: '最大比分失利',
  [RecordType.MOST_GOALS_IN_MATCH]: '单场总进球',
  [RecordType.LONGEST_WIN_STREAK]: '最长连胜',
  [RecordType.LONGEST_UNBEATEN]: '最长不败',
  [RecordType.LONGEST_LOSING_STREAK]: '最长连败',
}

export const RECORD_CATEGORY_LABELS: Record<RecordCategory, string> = {
  [RecordCategory.TEAM]: '球队纪录',
  [RecordCategory.PLAYER]: '球员纪录',
  [RecordCategory.MATCH]: '比赛纪录',
}

export const RECORD_SCOPE_LABELS: Record<RecordScope, string> = {
  [RecordScope.WORLD]: '世界纪录',
  [RecordScope.LEAGUE]: '联赛纪录',
  [RecordScope.TEAM]: '队伍纪录',
  [RecordScope.CUP]: '杯赛纪录',
}

export const RECORD_TYPES_BY_CATEGORY: Record<RecordCategory, RecordType[]> = {
  [RecordCategory.TEAM]: [
    RecordType.SEASON_TEAM_GOALS,
    RecordType.SEASON_TEAM_GOALS_AGAINST,
    RecordType.SEASON_TEAM_POINTS,
    RecordType.SEASON_TEAM_WINS,
    RecordType.SEASON_TEAM_CLEAN_SHEETS,
    RecordType.LONGEST_WIN_STREAK,
    RecordType.LONGEST_UNBEATEN,
    RecordType.LONGEST_LOSING_STREAK,
  ],
  [RecordCategory.PLAYER]: [
    RecordType.CAREER_GOALS,
    RecordType.CAREER_ASSISTS,
    RecordType.CAREER_APPEARANCES,
    RecordType.CAREER_RATING,
    RecordType.CAREER_YELLOW_CARDS,
    RecordType.CAREER_RED_CARDS,
    RecordType.CAREER_PASSES,
    RecordType.CAREER_KEY_PASSES,
    RecordType.CAREER_TACKLES,
    RecordType.CAREER_INTERCEPTIONS,
    RecordType.CAREER_CLEARANCES,
    RecordType.CAREER_SHOTS,
    RecordType.CAREER_SHOTS_ON_TARGET,
    RecordType.CAREER_SAVES,
    RecordType.CAREER_CLEAN_SHEETS,
    RecordType.CAREER_FOULS,
    RecordType.CAREER_OFFSIDES,
    RecordType.SEASON_GOALS,
    RecordType.SEASON_ASSISTS,
    RecordType.SEASON_RATING,
    RecordType.SEASON_PASSES,
    RecordType.SEASON_KEY_PASSES,
    RecordType.SEASON_TACKLES,
    RecordType.SEASON_INTERCEPTIONS,
    RecordType.SEASON_CLEARANCES,
    RecordType.SEASON_SHOTS,
    RecordType.SEASON_SHOTS_ON_TARGET,
    RecordType.SEASON_SAVES,
    RecordType.SEASON_CLEAN_SHEETS,
    RecordType.SEASON_FOULS,
    RecordType.SEASON_OFFSIDES,
    RecordType.MATCH_GOALS,
    RecordType.MATCH_ASSISTS,
    RecordType.MATCH_PASSES,
    RecordType.MATCH_KEY_PASSES,
    RecordType.MATCH_TACKLES,
    RecordType.MATCH_INTERCEPTIONS,
    RecordType.MATCH_SHOTS,
    RecordType.MATCH_SHOTS_ON_TARGET,
    RecordType.MATCH_SAVES,
    RecordType.MATCH_FOULS,
    RecordType.MATCH_OFFSIDES,
    RecordType.FASTEST_GOAL,
    RecordType.YOUNGEST_SCORER,
    RecordType.OLDEST_SCORER,
    RecordType.HAT_TRICKS,
    RecordType.SCORING_STREAK,
    RecordType.ASSIST_STREAK,
  ],
  [RecordCategory.MATCH]: [
    RecordType.MOST_GOALS_IN_MATCH,
    RecordType.BIGGEST_WIN_MARGIN,
    RecordType.BIGGEST_DEFEAT_MARGIN,
  ],
}
