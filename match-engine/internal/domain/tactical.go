package domain

// TacticalFlags represents active tactical states derived from team tactics
type TacticalFlags struct {
	HighPressActive    bool                `json:"high_press_active"`    // 防线高度≥3且逼抢强度≥3
	DeepDefenseActive  bool                `json:"deep_defense_active"`  // 防线高度≤1且防线收缩=深度回收
	OffsideTrapActive  bool                `json:"offside_trap_active"`  // 越位陷阱≥1且防线高度≥2
	ManMarkingActive   bool                `json:"man_marking_active"`   // 盯人策略=人盯人
	PlayFromBackActive bool                `json:"play_from_back_active"` // CB出球=参与组织且传球倾向=短传
	CounterFocusActive bool                `json:"counter_focus_active"` // 进攻节奏=极速反击
	PressingZoneBonus  [3][3]float64       `json:"pressing_zone_bonus"`  // 逼抢带来的各区域额外控制度
	MarkingTargets     map[string]string   `json:"marking_targets"`      // defender_id -> attacker_id
}

// ComputeTacticalFlags derives active flags from tactical setup
func (t *TeamRuntime) ComputeTacticalFlags() TacticalFlags {
	tac := t.Tactics
	flags := TacticalFlags{
		MarkingTargets: make(map[string]string),
	}

	// High press: defensive_line_height ≥ 3 AND pressing_intensity ≥ 3
	if tac.DefensiveLineHeight >= 3 && tac.PressingIntensity >= 3 {
		flags.HighPressActive = true
	}

	// Deep defense: defensive_line_height ≤ 1 AND defensive_compactness = 2
	if tac.DefensiveLineHeight <= 1 && tac.DefensiveCompactness >= 2 {
		flags.DeepDefenseActive = true
	}

	// Offside trap: offside_trap ≥ 1 AND defensive_line_height ≥ 2
	if tac.OffsideTrap >= 1 && tac.DefensiveLineHeight >= 2 {
		flags.OffsideTrapActive = true
	}

	// Man marking: marking_strategy = 2 (人盯人)
	if tac.MarkingStrategy >= 2 {
		flags.ManMarkingActive = true
	}

	// Play from back: passing_style ≤ 1 (短传倾向) AND defensive_line_height ≥ 2
	if tac.PassingStyle <= 1 && tac.DefensiveLineHeight >= 2 {
		flags.PlayFromBackActive = true
	}

	// Counter focus: attack_tempo = 4 (极速反击)
	if tac.AttackTempo >= 4 {
		flags.CounterFocusActive = true
	}

	// Pressing zone bonus based on pressing intensity
	pressBonus := float64(tac.PressingIntensity) * 0.04
	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			if r == 0 { // front zone gets highest bonus
				flags.PressingZoneBonus[r][c] = pressBonus * 1.5
			} else if r == 1 {
				flags.PressingZoneBonus[r][c] = pressBonus * 0.8
			} else {
				flags.PressingZoneBonus[r][c] = pressBonus * 0.3
			}
		}
	}

	// Build marking targets based on man marking strategy
	if flags.ManMarkingActive {
		// Simple heuristic: CBs mark opposing ST/WF, DMF marks AMF
		for _, def := range t.GetActivePlayers() {
			if def.Position == "CB" {
				// Will be populated during match based on opponent lineup
				flags.MarkingTargets[def.PlayerID] = ""
			}
		}
	}

	return flags
}

// GetPlaymaker returns the player with highest playmaker focus weight
func (t *TeamRuntime) GetPlaymaker() *PlayerRuntime {
	var playmaker *PlayerRuntime
	maxWeight := 0.0
	for _, p := range t.GetActivePlayers() {
		weight := 0.0
		switch p.Position {
		case "ST":
			weight = 1.0
		case "AMF":
			weight = 0.9
		case "CMF":
			weight = 0.7
		case "WF":
			weight = 0.6
		}
		// Playmaker focus boosts certain positions
		if t.Tactics.PlaymakerFocus >= 3 && p.Position == "ST" {
			weight += 0.3
		}
		if t.Tactics.PlaymakerFocus >= 2 && p.Position == "AMF" {
			weight += 0.2
		}
		if weight > maxWeight {
			maxWeight = weight
			playmaker = p
		}
	}
	return playmaker
}
