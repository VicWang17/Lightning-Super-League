export enum RecordScope {
  WORLD = 'world',
  LEAGUE = 'league',
  TEAM = 'team',
}

export enum RecordCategory {
  TEAM = 'team',
  PLAYER = 'player',
  MATCH = 'match',
}

export enum RecordType {
  CAREER_GOALS = 'career_goals',
  CAREER_ASSISTS = 'career_assists',
  CAREER_APPEARANCES = 'career_appearances',
  CAREER_YELLOW_CARDS = 'career_yellow_cards',
  CAREER_RED_CARDS = 'career_red_cards',
  CAREER_RATING = 'career_rating',
  SEASON_GOALS = 'season_goals',
  SEASON_ASSISTS = 'season_assists',
  SEASON_RATING = 'season_rating',
  MATCH_GOALS = 'match_goals',
  MATCH_ASSISTS = 'match_assists',
  FASTEST_GOAL = 'fastest_goal',
  YOUNGEST_SCORER = 'youngest_scorer',
  OLDEST_SCORER = 'oldest_scorer',
  HAT_TRICKS = 'hat_tricks',
  SCORING_STREAK = 'scoring_streak',
  ASSIST_STREAK = 'assist_streak',
  SEASON_TEAM_GOALS = 'season_team_goals',
  SEASON_TEAM_GOALS_AGAINST = 'season_team_goals_against',
  SEASON_TEAM_POINTS = 'season_team_points',
  SEASON_TEAM_WINS = 'season_team_wins',
  SEASON_CLEAN_SHEETS = 'season_clean_sheets',
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

export interface RecordsByCategory {
  team: RecordItem[]
  player: RecordItem[]
  match: RecordItem[]
}

export const RECORD_TYPE_LABELS: Record<RecordType, string> = {
  [RecordType.CAREER_GOALS]: '生涯总进球最多',
  [RecordType.CAREER_ASSISTS]: '生涯总助攻最多',
  [RecordType.CAREER_APPEARANCES]: '生涯出场最多',
  [RecordType.CAREER_YELLOW_CARDS]: '生涯黄牌最多',
  [RecordType.CAREER_RED_CARDS]: '生涯红牌最多',
  [RecordType.CAREER_RATING]: '生涯最高场均评分',
  [RecordType.SEASON_GOALS]: '单赛季进球最多',
  [RecordType.SEASON_ASSISTS]: '单赛季助攻最多',
  [RecordType.SEASON_RATING]: '单赛季最高场均评分',
  [RecordType.MATCH_GOALS]: '单场进球最多',
  [RecordType.MATCH_ASSISTS]: '单场助攻最多',
  [RecordType.FASTEST_GOAL]: '最快进球',
  [RecordType.YOUNGEST_SCORER]: '最年轻进球者',
  [RecordType.OLDEST_SCORER]: '最年长进球者',
  [RecordType.HAT_TRICKS]: '帽子戏法次数',
  [RecordType.SCORING_STREAK]: '连续进球场次',
  [RecordType.ASSIST_STREAK]: '连续助攻场次',
  [RecordType.SEASON_TEAM_GOALS]: '单赛季进球最多',
  [RecordType.SEASON_TEAM_GOALS_AGAINST]: '单赛季失球最少',
  [RecordType.SEASON_TEAM_POINTS]: '单赛季积分最高',
  [RecordType.SEASON_TEAM_WINS]: '单赛季胜场最多',
  [RecordType.SEASON_CLEAN_SHEETS]: '单赛季零封最多',
  [RecordType.BIGGEST_WIN_MARGIN]: '最大比分胜利',
  [RecordType.BIGGEST_DEFEAT_MARGIN]: '最大比分失利',
  [RecordType.MOST_GOALS_IN_MATCH]: '单场总进球最多',
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
}
