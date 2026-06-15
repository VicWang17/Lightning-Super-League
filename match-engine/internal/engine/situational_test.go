package engine

import (
	"testing"

	"match-engine/internal/domain"
)

func TestSituationalRuleOverridesInstructions(t *testing.T) {
	base := domain.DefaultTeamInstructions()
	base.SituationalRules = []domain.SituationalRule{
		{
			ID:      "chase",
			Name:    "落后追分",
			Enabled: true,
			Condition: domain.SituationalRuleCondition{
				MinuteGte:   ptrInt(40),
				GoalDiffLte: ptrInt(-1),
			},
			Override: domain.SituationalRuleOverride{
				Tempo:             ptrInt(4),
				ShootingFrequency: ptrInt(4),
			},
		},
	}

	setup := buildRealisticTeam("Home", false)
	setup.TeamInstructions = &base
	team := domain.NewTeamRuntime(setup)

	ms := &domain.MatchState{
		Score:      domain.Score{Home: 0, Away: 1},
		Minute:     55,
		HomeTeam:   team,
		AwayTeam:   domain.NewTeamRuntime(buildRealisticTeam("Away", false)),
		Possession: domain.SideHome,
	}

	eff, triggered := ComputeEffectiveInstructions(team, ms)
	if len(triggered) != 1 || triggered[0] != "chase" {
		t.Errorf("expected chase rule triggered, got %v", triggered)
	}
	if eff.InPossession.Tempo != 4 {
		t.Errorf("expected tempo 4, got %d", eff.InPossession.Tempo)
	}
	if eff.InPossession.ShootingFrequency != 4 {
		t.Errorf("expected shooting_frequency 4, got %d", eff.InPossession.ShootingFrequency)
	}

	// Base instructions should remain unchanged.
	if base.InPossession.Tempo != 2 {
		t.Errorf("base tempo mutated: %d", base.InPossession.Tempo)
	}
}

func TestSituationalRuleDoesNotTriggerWhenDisabled(t *testing.T) {
	base := domain.DefaultTeamInstructions()
	base.SituationalRules = []domain.SituationalRule{
		{
			ID:      "protect",
			Name:    "领先稳守",
			Enabled: false,
			Condition: domain.SituationalRuleCondition{
				MinuteGte:   ptrInt(40),
				GoalDiffGte: ptrInt(1),
			},
			Override: domain.SituationalRuleOverride{
				DefensiveLineHeight: ptrInt(0),
			},
		},
	}

	setup := buildRealisticTeam("Home", false)
	setup.TeamInstructions = &base
	team := domain.NewTeamRuntime(setup)

	ms := &domain.MatchState{
		Score:      domain.Score{Home: 2, Away: 1},
		Minute:     70,
		HomeTeam:   team,
		AwayTeam:   domain.NewTeamRuntime(buildRealisticTeam("Away", false)),
		Possession: domain.SideHome,
	}

	eff, triggered := ComputeEffectiveInstructions(team, ms)
	if len(triggered) != 0 {
		t.Errorf("expected no triggers, got %v", triggered)
	}
	if eff.OutOfPossession.DefensiveLineHeight != 2 {
		t.Errorf("expected unchanged defensive_line_height, got %d", eff.OutOfPossession.DefensiveLineHeight)
	}
}

func TestSituationalRuleStaminaCondition(t *testing.T) {
	base := domain.DefaultTeamInstructions()
	base.SituationalRules = []domain.SituationalRule{
		{
			ID:      "tired",
			Name:    "体能低谷回收",
			Enabled: true,
			Condition: domain.SituationalRuleCondition{
				TeamStaminaAvgLte: ptrInt(50),
			},
			Override: domain.SituationalRuleOverride{
				PressingIntensity:   ptrInt(0),
				DefensiveLineHeight: ptrInt(0),
			},
		},
	}

	setup := buildRealisticTeam("Home", false)
	setup.TeamInstructions = &base
	team := domain.NewTeamRuntime(setup)
	for _, p := range team.PlayerRuntimes {
		p.CurrentStamina = 30
	}

	ms := &domain.MatchState{
		Score:      domain.Score{},
		Minute:     10,
		HomeTeam:   team,
		AwayTeam:   domain.NewTeamRuntime(buildRealisticTeam("Away", false)),
		Possession: domain.SideHome,
	}

	eff, triggered := ComputeEffectiveInstructions(team, ms)
	if len(triggered) != 1 {
		t.Errorf("expected stamina rule triggered, got %v", triggered)
	}
	if eff.OutOfPossession.PressingIntensity != 0 {
		t.Errorf("expected pressing_intensity 0, got %d", eff.OutOfPossession.PressingIntensity)
	}
}

func ptrInt(v int) *int {
	return &v
}
