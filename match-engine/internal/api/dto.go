package api

import "match-engine/internal/domain"

type SimulateRequest struct {
	MatchID        string           `json:"match_id"`
	HomeTeam       domain.TeamSetup `json:"home_team"`
	AwayTeam       domain.TeamSetup `json:"away_team"`
	HomeAdvantage  bool             `json:"home_advantage"`
	RequiresWinner bool             `json:"requires_winner"`
	Mode           string           `json:"mode"`
	TickIntervalMs int              `json:"tick_interval_ms"`
	Seed           uint64           `json:"seed"`
}

type SimulateResponse struct {
	Result domain.SimulateResult `json:"result"`
}
