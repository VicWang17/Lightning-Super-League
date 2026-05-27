package main

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	engineapi "match-engine/internal/api"
	"match-engine/internal/domain"
	"match-engine/internal/engine"
)

type simulateResponse struct {
	Result domain.SimulateResult `json:"result"`
}

func main() {
	var req engineapi.SimulateRequest
	if err := json.NewDecoder(os.Stdin).Decode(&req); err != nil {
		fmt.Fprintf(os.Stderr, "decode request: %v\n", err)
		os.Exit(1)
	}
	if req.MatchID == "" {
		req.MatchID = "process_match"
	}
	seed := req.Seed
	if seed == 0 {
		seed = uint64(time.Now().UnixNano())
	}

	result := engine.NewSimulator(seed).Simulate(domain.SimulateRequest{
		MatchID:        req.MatchID,
		HomeTeam:       req.HomeTeam,
		AwayTeam:       req.AwayTeam,
		HomeAdvantage:  req.HomeAdvantage,
		RequiresWinner: req.RequiresWinner,
	})

	if err := json.NewEncoder(os.Stdout).Encode(simulateResponse{Result: result}); err != nil {
		fmt.Fprintf(os.Stderr, "encode response: %v\n", err)
		os.Exit(1)
	}
}
