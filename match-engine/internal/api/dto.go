package api

import "match-engine/internal/domain"

type SimulateRequest struct {
	MatchID       string           `json:"match_id"`
	HomeTeam      domain.TeamSetup `json:"home_team"`
	AwayTeam      domain.TeamSetup `json:"away_team"`
	HomeAdvantage bool             `json:"home_advantage"`
}

type SimulateResponse struct {
	Result domain.SimulateResult `json:"result"`
}
