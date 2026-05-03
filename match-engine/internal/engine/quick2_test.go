package engine

import (
	"fmt"
	"testing"

	"match-engine/internal/domain"
)

func TestQuick2(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("雷霆FC", attrs, defaultTactics())
	away := buildTeam("闪电联", attrs, defaultTactics())

	req := domain.SimulateRequest{
		MatchID:       "q2",
		HomeTeam:      home,
		AwayTeam:      away,
		HomeAdvantage: false,
	}
	sim := NewSimulator(6)
	result := sim.Simulate(req)

	for i := 0; i < len(result.Events)-1; i++ {
		ev := result.Events[i]
		next := result.Events[i+1]
		if ev.Type == "header" && ev.Result == "success" {
			fmt.Printf("header: %s (player=%s p2=%s)\n", ev.Narrative, ev.PlayerName, ev.Player2Name)
			fmt.Printf("  next: %s (player=%s)\n", next.Narrative, next.PlayerName)
		}
	}
}
