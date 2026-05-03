package engine

import (
	"fmt"
	"testing"

	"match-engine/internal/domain"
)

func TestQuick(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("雷霆FC", attrs, defaultTactics())
	away := buildTeam("闪电联", attrs, defaultTactics())

	req := domain.SimulateRequest{
		MatchID:       "quick",
		HomeTeam:      home,
		AwayTeam:      away,
		HomeAdvantage: false,
	}
	sim := NewSimulator(6)
	result := sim.Simulate(req)

	for _, ev := range result.Events {
		if ev.Type == "header" || ev.Type == "shot_windup" || ev.Type == "foul" || ev.Type == "turnover" {
			fmt.Printf("%s | %s | player=%s | p2=%s\n", ev.Type, ev.Narrative, ev.PlayerName, ev.Player2Name)
		}
	}
}
