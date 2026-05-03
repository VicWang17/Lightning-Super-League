package domain

// MatchEvent represents a single event in the match
type MatchEvent struct {
	ID          int     `json:"id"`
	Minute      float64 `json:"minute"`
	Type        string  `json:"type"`
	Team        string  `json:"team,omitempty"`        // "home" or "away"
	PlayerID    string  `json:"player_id,omitempty"`
	PlayerName  string  `json:"player_name,omitempty"`
	Player2ID   string  `json:"player2_id,omitempty"`  // secondary player
	Player2Name string  `json:"player2_name,omitempty"`
	OpponentID  string  `json:"opponent_id,omitempty"`
	OpponentName string `json:"opponent_name,omitempty"`
	Zone        string  `json:"zone,omitempty"`
	Result      string  `json:"result,omitempty"`      // success / fail / goal / saved / blocked / offside / corner / etc
	Detail      string  `json:"detail,omitempty"`      // aggressive / safe / etc
	Score       *Score  `json:"score,omitempty"`
	Narrative   string  `json:"narrative,omitempty"`
}

// Score represents the current score
type Score struct {
	Home int `json:"home"`
	Away int `json:"away"`
}

// MatchStats final statistics
type MatchStats struct {
	PossessionHome float64 `json:"possession_home"`
	PossessionAway float64 `json:"possession_away"`
	ShotsHome      int     `json:"shots_home"`
	ShotsAway      int     `json:"shots_away"`
	ShotsOnTargetHome int  `json:"shots_on_target_home"`
	ShotsOnTargetAway int  `json:"shots_on_target_away"`
	PassesHome     int     `json:"passes_home"`
	PassesAway     int     `json:"passes_away"`
	PassAccuracyHome float64 `json:"pass_accuracy_home"`
	PassAccuracyAway float64 `json:"pass_accuracy_away"`
	KeyPassesHome  int     `json:"key_passes_home"`
	KeyPassesAway  int     `json:"key_passes_away"`
	CrossesHome    int     `json:"crosses_home"`
	CrossesAway    int     `json:"crosses_away"`
	CrossAccuracyHome float64 `json:"cross_accuracy_home"`
	CrossAccuracyAway float64 `json:"cross_accuracy_away"`
	DribblesHome   int     `json:"dribbles_home"`
	DribblesAway   int     `json:"dribbles_away"`
	DribbleAccuracyHome float64 `json:"dribble_accuracy_home"`
	DribbleAccuracyAway float64 `json:"dribble_accuracy_away"`
	TacklesHome    int     `json:"tackles_home"`
	TacklesAway    int     `json:"tackles_away"`
	TackleAccuracyHome float64 `json:"tackle_accuracy_home"`
	TackleAccuracyAway float64 `json:"tackle_accuracy_away"`
	InterceptionsHome int  `json:"interceptions_home"`
	InterceptionsAway int  `json:"interceptions_away"`
	ClearancesHome int     `json:"clearances_home"`
	ClearancesAway int     `json:"clearances_away"`
	BlocksHome     int     `json:"blocks_home"`
	BlocksAway     int     `json:"blocks_away"`
	HeadersHome    int     `json:"headers_home"`
	HeadersAway    int     `json:"headers_away"`
	HeaderAccuracyHome float64 `json:"header_accuracy_home"`
	HeaderAccuracyAway float64 `json:"header_accuracy_away"`
	SavesHome      int     `json:"saves_home"`
	SavesAway      int     `json:"saves_away"`
	CornersHome    int     `json:"corners_home"`
	CornersAway    int     `json:"corners_away"`
	FoulsHome      int     `json:"fouls_home"`
	FoulsAway      int     `json:"fouls_away"`
	FoulsDrawnHome int     `json:"fouls_drawn_home"`
	FoulsDrawnAway int     `json:"fouls_drawn_away"`
	OffsidesHome   int     `json:"offsides_home"`
	OffsidesAway   int     `json:"offsides_away"`
	YellowCardsHome int    `json:"yellow_cards_home"`
	YellowCardsAway int    `json:"yellow_cards_away"`
	RedCardsHome   int     `json:"red_cards_home"`
	RedCardsAway   int     `json:"red_cards_away"`
	FreeKicksHome      int     `json:"free_kicks_home"`
	FreeKicksAway      int     `json:"free_kicks_away"`
	FreeKickGoalsHome  int     `json:"free_kick_goals_home"`
	FreeKickGoalsAway  int     `json:"free_kick_goals_away"`
	PenaltiesHome      int     `json:"penalties_home"`
	PenaltiesAway      int     `json:"penalties_away"`
	PenaltyGoalsHome   int     `json:"penalty_goals_home"`
	PenaltyGoalsAway   int     `json:"penalty_goals_away"`
}

// PlayerResultStat per-player output
type PlayerResultStat struct {
	PlayerID       string  `json:"player_id"`
	Name           string  `json:"name"`
	Position       string  `json:"position"`
	Team           string  `json:"team"`
	Goals          int     `json:"goals"`
	Assists        int     `json:"assists"`
	Shots          int     `json:"shots"`
	ShotsOnTarget  int     `json:"shots_on_target"`
	Passes         int     `json:"passes"`
	PassAccuracy   float64 `json:"pass_accuracy"`
	KeyPasses      int     `json:"key_passes"`
	Crosses        int     `json:"crosses"`
	CrossAccuracy  float64 `json:"cross_accuracy"`
	Dribbles       int     `json:"dribbles"`
	DribbleAccuracy float64 `json:"dribble_accuracy"`
	Tackles        int     `json:"tackles"`
	TackleAccuracy float64 `json:"tackle_accuracy"`
	Interceptions  int     `json:"interceptions"`
	Clearances     int     `json:"clearances"`
	Blocks         int     `json:"blocks"`
	Headers        int     `json:"headers"`
	HeaderAccuracy float64 `json:"header_accuracy"`
	Saves          int     `json:"saves"`
	Fouls          int     `json:"fouls"`
	FoulsDrawn     int     `json:"fouls_drawn"`
	Offsides       int     `json:"offsides"`
	YellowCards    int     `json:"yellow_cards"`
	RedCards       int     `json:"red_cards"`
	FreeKicks      int     `json:"free_kicks"`
	FreeKickGoals  int     `json:"free_kick_goals"`
	Penalties      int     `json:"penalties"`
	PenaltyGoals   int     `json:"penalty_goals"`
	Turnovers      int     `json:"turnovers"`
	Touches        int     `json:"touches"`
	Rating         float64 `json:"rating"`
}

// SimulateResult is the engine output
type SimulateResult struct {
	MatchID      string             `json:"match_id"`
	HomeTeam     string             `json:"home_team"`
	AwayTeam     string             `json:"away_team"`
	Score        Score              `json:"score"`
	Events       []MatchEvent       `json:"events"`
	Stats        MatchStats         `json:"stats"`
	PlayerStats  []PlayerResultStat `json:"player_stats"`
	Narratives   []string           `json:"narratives"`
	DurationMs   int64              `json:"duration_ms"`
}
