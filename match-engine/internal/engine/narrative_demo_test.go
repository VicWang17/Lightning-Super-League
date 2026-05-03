package engine

import (
	"fmt"
	"testing"

	"match-engine/internal/domain"
)

func TestNarrativeDemo(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())

	req := domain.SimulateRequest{
		MatchID:       "demo",
		HomeTeam:      home,
		AwayTeam:      away,
		HomeAdvantage: false,
	}
	sim := NewSimulator(42)
	result := sim.Simulate(req)

	fmt.Printf("\n========== MATCH NARRATIVE ==========\n")
	fmt.Printf("Final Score: %d-%d\n\n", result.Score.Home, result.Score.Away)

	for _, ev := range result.Events {
		min := int(ev.Minute)
		sec := int((ev.Minute - float64(min)) * 60)
		fmt.Printf("%2d:%02d | %-22s | %s\n", min, sec, ev.Type, ev.Narrative)
	}
}
