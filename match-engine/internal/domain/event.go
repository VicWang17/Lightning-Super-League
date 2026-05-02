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
	TacklesHome    int     `json:"tackles_home"`
	TacklesAway    int     `json:"tackles_away"`
	CornersHome    int     `json:"corners_home"`
	CornersAway    int     `json:"corners_away"`
	FoulsHome      int     `json:"fouls_home"`
	FoulsAway      int     `json:"fouls_away"`
	YellowCardsHome int    `json:"yellow_cards_home"`
	YellowCardsAway int    `json:"yellow_cards_away"`
	RedCardsHome   int     `json:"red_cards_home"`
	RedCardsAway   int     `json:"red_cards_away"`
}

// PlayerResultStat per-player output
type PlayerResultStat struct {
	PlayerID      string  `json:"player_id"`
	Name          string  `json:"name"`
	Position      string  `json:"position"`
	Team          string  `json:"team"`
	Goals         int     `json:"goals"`
	Assists       int     `json:"assists"`
	Shots         int     `json:"shots"`
	ShotsOnTarget int     `json:"shots_on_target"`
	Passes        int     `json:"passes"`
	PassAccuracy  float64 `json:"pass_accuracy"`
	Tackles       int     `json:"tackles"`
	Interceptions int     `json:"interceptions"`
	Saves         int     `json:"saves"`
	Fouls         int     `json:"fouls"`
	YellowCards   int     `json:"yellow_cards"`
	RedCards      int     `json:"red_cards"`
	Rating        float64 `json:"rating"`
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
