package domain

import "testing"

func TestNormalizeTeamInstructionsRepairsCorruptedValues(t *testing.T) {
	base := DeriveTeamInstructions(TacticalSetup{
		PassingStyle:         2,
		AttackWidth:          2,
		AttackTempo:          2,
		DefensiveLineHeight:  2,
		CrossingStrategy:     2,
		ShootingMentality:    2,
		PlaymakerFocus:       0,
		PressingIntensity:    2,
		DefensiveCompactness: 1,
		MarkingStrategy:      0,
		OffsideTrap:          0,
		TacklingAggression:   1,
	})
	base.InPossession.BuildUpStyle = "invalid"
	base.InPossession.Tempo = 99
	base.InPossession.Width = -5
	base.Transition.AfterPossessionLost = ""
	base.OutOfPossession.Marking = "man_marking"
	base.OutOfPossession.TacklingAggression = 10
	base.GoalkeeperDistribution.DistributionLength = "far"
	base.PlayerInstructions = []PlayerInstruction{
		{PlayerID: "p1", CarryBall: 9, PassingRisk: -1},
	}

	n := NormalizeTeamInstructions(base)

	if n.InPossession.BuildUpStyle != "balanced" {
		t.Errorf("build_up_style got %q, want balanced", n.InPossession.BuildUpStyle)
	}
	if n.InPossession.Tempo != 4 {
		t.Errorf("tempo got %d, want 4", n.InPossession.Tempo)
	}
	if n.InPossession.Width != 0 {
		t.Errorf("width got %d, want 0", n.InPossession.Width)
	}
	if n.Transition.AfterPossessionLost != "balanced" {
		t.Errorf("after_possession_lost got %q, want balanced", n.Transition.AfterPossessionLost)
	}
	if n.OutOfPossession.Marking != "mixed" {
		t.Errorf("marking got %q, want mixed", n.OutOfPossession.Marking)
	}
	if n.OutOfPossession.TacklingAggression != 3 {
		t.Errorf("tackling_aggression got %d, want 3", n.OutOfPossession.TacklingAggression)
	}
	if n.GoalkeeperDistribution.DistributionLength != "balanced" {
		t.Errorf("distribution_length got %q, want balanced", n.GoalkeeperDistribution.DistributionLength)
	}
	if len(n.PlayerInstructions) != 1 {
		t.Fatalf("expected 1 player instruction, got %d", len(n.PlayerInstructions))
	}
	pi := n.PlayerInstructions[0]
	if pi.CarryBall != 4 {
		t.Errorf("player carry_ball got %d, want 4", pi.CarryBall)
	}
	if pi.PassingRisk != 0 {
		t.Errorf("player passing_risk got %d, want 0", pi.PassingRisk)
	}
}

func TestNormalizeTeamInstructionsKeepsValidValues(t *testing.T) {
	base := DeriveTeamInstructions(TacticalSetup{
		PassingStyle:         4,
		AttackWidth:          1,
		AttackTempo:          3,
		DefensiveLineHeight:  0,
		CrossingStrategy:     4,
		ShootingMentality:    4,
		PlaymakerFocus:       0,
		PressingIntensity:    4,
		DefensiveCompactness: 2,
		MarkingStrategy:      2,
		OffsideTrap:          2,
		TacklingAggression:   3,
	})
	n := NormalizeTeamInstructions(base)
	if n.InPossession.BuildUpStyle != "short" {
		t.Errorf("build_up_style got %q, want short", n.InPossession.BuildUpStyle)
	}
	if n.InPossession.AttackRoute != "center" {
		t.Errorf("attack_route got %q, want center", n.InPossession.AttackRoute)
	}
	if n.OutOfPossession.Marking != "man" {
		t.Errorf("marking got %q, want man", n.OutOfPossession.Marking)
	}
}
