package domain

// SimulateRequest is the input to the match engine
type SimulateRequest struct {
	MatchID       string   `json:"match_id"`
	HomeTeam      TeamSetup `json:"home_team"`
	AwayTeam      TeamSetup `json:"away_team"`
	HomeAdvantage bool     `json:"home_advantage"`
}
