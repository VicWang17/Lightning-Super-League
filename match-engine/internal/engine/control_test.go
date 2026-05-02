package engine

import (
	"testing"
	"match-engine/internal/domain"
)

func TestControlShiftDirection(t *testing.T) {
	sim := NewSimulator(42)
	req := domain.SimulateRequest{
		HomeTeam: domain.TeamSetup{
			TeamID: "h", Name: "H", FormationID: "F01",
			Players: []domain.PlayerSetup{
				{PlayerID: "h1", Name: "GK", Position: "GK", Attributes: map[string]int{"SHO":10,"PAS":10,"DRI":10,"SPD":10,"STR":10,"STA":10,"DEF":10,"HEA":10,"VIS":10,"TKL":10,"ACC":10,"CRO":10,"CON":10,"FIN":10,"BAL":10,"COM":10,"SAV":16,"REF":15,"POS":14,"FK":10,"PK":10}, Skills: []string{}, Stamina: 100, Height: 180, Foot: "right"},
				{PlayerID: "h2", Name: "CB", Position: "CB", Attributes: map[string]int{"SHO":10,"PAS":10,"DRI":10,"SPD":10,"STR":14,"STA":10,"DEF":16,"HEA":15,"VIS":10,"TKL":13,"ACC":10,"CRO":10,"CON":10,"FIN":10,"BAL":10,"COM":10,"SAV":10,"REF":10,"POS":10,"FK":10,"PK":10}, Skills: []string{}, Stamina: 100, Height: 185, Foot: "right"},
			},
			Tactics: domain.TacticalSetup{PassingStyle: 1, AttackWidth: 2, AttackTempo: 4, DefensiveLineHeight: 3, CrossingStrategy: 2, ShootingMentality: 3, PlaymakerFocus: 0, PressingIntensity: 3, DefensiveCompactness: 2, MarkingStrategy: 1, OffsideTrap: 1, TacklingAggression: 2},
		},
		AwayTeam: domain.TeamSetup{
			TeamID: "a", Name: "A", FormationID: "F02",
			Players: []domain.PlayerSetup{
				{PlayerID: "a1", Name: "GK", Position: "GK", Attributes: map[string]int{"SHO":10,"PAS":10,"DRI":10,"SPD":10,"STR":10,"STA":10,"DEF":10,"HEA":10,"VIS":10,"TKL":10,"ACC":10,"CRO":10,"CON":10,"FIN":10,"BAL":10,"COM":10,"SAV":16,"REF":15,"POS":14,"FK":10,"PK":10}, Skills: []string{}, Stamina: 100, Height: 180, Foot: "right"},
				{PlayerID: "a2", Name: "CB", Position: "CB", Attributes: map[string]int{"SHO":10,"PAS":10,"DRI":10,"SPD":10,"STR":14,"STA":10,"DEF":16,"HEA":15,"VIS":10,"TKL":13,"ACC":10,"CRO":10,"CON":10,"FIN":10,"BAL":10,"COM":10,"SAV":10,"REF":10,"POS":10,"FK":10,"PK":10}, Skills: []string{}, Stamina: 100, Height: 185, Foot: "right"},
			},
			Tactics: domain.TacticalSetup{PassingStyle: 4, AttackWidth: 2, AttackTempo: 2, DefensiveLineHeight: 1, CrossingStrategy: 3, ShootingMentality: 2, PlaymakerFocus: 1, PressingIntensity: 1, DefensiveCompactness: 2, MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 1},
		},
		HomeAdvantage: true,
	}

	ms := sim.InitMatchState(req)
	_ = ms

	// Test: home team in possession, apply positive shift
	ms.Possession = domain.SideHome
	ms.ActiveZone = [2]int{1,1}
	oldShift := ms.ControlShift[1][1]
	sim.applyControlShift(ms, [2]int{1,1}, 0.10)
	if ms.ControlShift[1][1] <= oldShift {
		t.Errorf("Home possession: ControlShift should increase, got %v -> %v", oldShift, ms.ControlShift[1][1])
	}

	// Test: away team in possession, apply positive shift
	ms.Possession = domain.SideAway
	oldShift = ms.ControlShift[1][1]
	sim.applyControlShift(ms, [2]int{1,1}, 0.10)
	if ms.ControlShift[1][1] >= oldShift {
		t.Errorf("Away possession: ControlShift should decrease, got %v -> %v", oldShift, ms.ControlShift[1][1])
	}

	// Test: turnover flip
	ms.ControlShift[1][1] = 0.20
	sim.flipControlShiftOnTurnover(ms, [2]int{1,1})
	expected := -0.10
	if ms.ControlShift[1][1] < expected-0.01 || ms.ControlShift[1][1] > expected+0.01 {
		t.Errorf("Turnover flip: expected ~%v, got %v", expected, ms.ControlShift[1][1])
	}
}
