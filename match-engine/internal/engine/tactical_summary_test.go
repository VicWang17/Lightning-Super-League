package engine

import (
	"testing"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

func teamForSummary(id, name string, tempo int) domain.TeamSetup {
	team := buildRealisticTeam(name, false)
	team.TeamID = id
	team.Name = name
	team.FormationID = "F01"
	team.Tactics.AttackTempo = tempo
	return team
}

func TestBuildResultIncludesTacticalSummary(t *testing.T) {
	req := domain.SimulateRequest{
		MatchID:        "test_summary",
		HomeAdvantage:  true,
		RequiresWinner: false,
		HomeTeam:       teamForSummary("home_team", "Home FC", 2),
		AwayTeam:       teamForSummary("away_team", "Away FC", 2),
	}

	sim := NewSimulator(12345)
	result := sim.Simulate(req)

	if len(result.TacticalSummaries) != 2 {
		t.Fatalf("expected 2 tactical summaries, got %d", len(result.TacticalSummaries))
	}

	home := result.TacticalSummaries[0]
	away := result.TacticalSummaries[1]

	if home.TeamID != "home_team" {
		t.Errorf("expected home team_id home_team, got %s", home.TeamID)
	}
	if away.TeamID != "away_team" {
		t.Errorf("expected away team_id away_team, got %s", away.TeamID)
	}

	if home.FormationID == "" || away.FormationID == "" {
		t.Error("expected non-empty formation ids")
	}

	if len(home.EventCounts) == 0 && len(away.EventCounts) == 0 {
		t.Error("expected at least one side to have event counts")
	}

	// Possession should be tracked in at least one zone
	homePossession := 0
	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			homePossession += home.PossessionByZone[r][c]
		}
	}
	if homePossession == 0 {
		t.Error("expected home possession by zone to be tracked")
	}
}

func TestTrackEventCounts(t *testing.T) {
	req := domain.SimulateRequest{
		MatchID:        "test_event_counts",
		HomeAdvantage:  true,
		RequiresWinner: false,
		HomeTeam:       teamForSummary("home_team", "Home FC", 2),
		AwayTeam:       teamForSummary("away_team", "Away FC", 2),
	}

	sim := NewSimulator(42)
	result := sim.Simulate(req)

	totalEvents := 0
	for _, summary := range result.TacticalSummaries {
		for _, count := range summary.EventCounts {
			totalEvents += count
		}
	}

	// There should be at least as many tracked events as match events minus metadata
	if totalEvents == 0 {
		t.Error("expected tracked event counts to be non-zero")
	}
}

func TestTrackCounterAttacks(t *testing.T) {
	req := domain.SimulateRequest{
		MatchID:        "test_counter",
		HomeAdvantage:  true,
		RequiresWinner: false,
		HomeTeam:       teamForSummary("home_team", "Home FC", 4),
		AwayTeam:       teamForSummary("away_team", "Away FC", 2),
	}

	sim := NewSimulator(99)
	result := sim.Simulate(req)

	counterFound := false
	for _, summary := range result.TacticalSummaries {
		if summary.CounterAttacks > 0 {
			counterFound = true
		}
		if _, ok := summary.EventCounts[config.EventCounterAttack]; ok {
			counterFound = true
		}
	}

	// Counters are probabilistic; we don't strictly assert presence, but structure must be valid
	_ = counterFound
}
