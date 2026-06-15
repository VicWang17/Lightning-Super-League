package engine

import (
	"testing"

	"match-engine/internal/domain"
)

// TestV4FeaturesAreActive verifies that player instructions, situational rules,
// and their post-match diagnostics all work in a full match simulation.
func TestV4FeaturesAreActive(t *testing.T) {
	homeSetup := buildRealisticTeam("Home", false)
	awaySetup := buildRealisticTeam("Away", false)

	homeInstr := domain.DefaultTeamInstructions()
	homeInstr.PlayerInstructions = []domain.PlayerInstruction{
		{
			PlayerID:          homeSetup.Players[0].PlayerID,
			CarryBall:         4,
			ShootingFrequency: 4,
			PressingIntensity: 4,
		},
	}
	// A rule that fires immediately and stays active for the whole match.
	homeInstr.SituationalRules = []domain.SituationalRule{
		{
			ID:      "always-fast",
			Name:    "始终快节奏",
			Enabled: true,
			Condition: domain.SituationalRuleCondition{
				MinuteGte: ptrInt(0),
			},
			Override: domain.SituationalRuleOverride{
				Tempo:   ptrInt(4),
				PassingRisk: ptrInt(3),
			},
		},
	}
	homeSetup.TeamInstructions = &homeInstr

	awayInstr := domain.DefaultTeamInstructions()
	awayInstr.SituationalRules = []domain.SituationalRule{
		{
			ID:      "ahead-defend",
			Name:    "领先稳守",
			Enabled: true,
			Condition: domain.SituationalRuleCondition{
				MinuteGte:   ptrInt(40),
				GoalDiffGte: ptrInt(1),
			},
			Override: domain.SituationalRuleOverride{
				Tempo:               ptrInt(1),
				DefensiveLineHeight: ptrInt(0),
			},
		},
	}
	awaySetup.TeamInstructions = &awayInstr

	req := domain.SimulateRequest{
		MatchID:        "v4_integration",
		HomeAdvantage:  false,
		RequiresWinner: false,
		HomeTeam:       homeSetup,
		AwayTeam:       awaySetup,
	}

	sim := NewSimulator(12345)
	result := sim.Simulate(req)

	if result.TacticalSummaries[0].InstructionTriggers == nil {
		t.Errorf("home InstructionTriggers map should be initialized")
	}
	if result.TacticalSummaries[0].SituationalRuleTriggers == nil {
		t.Errorf("home SituationalRuleTriggers map should be initialized")
	}

	if result.TacticalSummaries[0].SituationalRuleTriggers["always-fast"] == 0 {
		t.Errorf("always-fast rule should have triggered at least once")
	}

	// Base instructions should not have been mutated by situational overrides.
	if homeInstr.InPossession.Tempo != 2 {
		t.Errorf("base tempo mutated by effective instructions: got %d", homeInstr.InPossession.Tempo)
	}
	if homeInstr.InPossession.PassingRisk != 2 {
		t.Errorf("base passing_risk mutated by effective instructions: got %d", homeInstr.InPossession.PassingRisk)
	}

	// The match should have produced a reasonable number of events.
	if len(result.Events) < 50 {
		t.Errorf("match produced too few events: %d", len(result.Events))
	}
}
