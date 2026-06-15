package domain

// TacticalSetup from design doc (simplified MVP)
type TacticalSetup struct {
	PassingStyle         int `json:"passing_style"`         // 0-4
	AttackWidth          int `json:"attack_width"`          // 0-4
	AttackTempo          int `json:"attack_tempo"`          // 0-4
	DefensiveLineHeight  int `json:"defensive_line_height"` // 0-4
	CrossingStrategy     int `json:"crossing_strategy"`     // 0-4
	ShootingMentality    int `json:"shooting_mentality"`    // 0-4
	PlaymakerFocus       int `json:"playmaker_focus"`       // 0-4
	PressingIntensity    int `json:"pressing_intensity"`    // 0-4
	DefensiveCompactness int `json:"defensive_compactness"` // 0-2
	MarkingStrategy      int `json:"marking_strategy"`      // 0-2
	OffsideTrap          int `json:"offside_trap"`          // 0-2
	TacklingAggression   int `json:"tackling_aggression"`   // 0-3
}

// InPossessionInstructions holds team instructions when in possession.
type InPossessionInstructions struct {
	BuildUpStyle      string `json:"build_up_style"`     // short / balanced / direct / long_ball
	ChanceCreation    string `json:"chance_creation"`    // patient / balanced / early_shot / work_into_box
	AttackRoute       string `json:"attack_route"`       // left / center / right / both_wings / mixed
	Width             int    `json:"width"`              // 0-4
	Tempo             int    `json:"tempo"`              // 0-4
	PassingRisk       int    `json:"passing_risk"`       // 0-4
	CrossingFrequency int    `json:"crossing_frequency"` // 0-4
	DribbleFrequency  int    `json:"dribble_frequency"`  // 0-4
	ShootingFrequency int    `json:"shooting_frequency"` // 0-4
}

// TransitionInstructions holds team instructions during transitions.
type TransitionInstructions struct {
	AfterPossessionLost string `json:"after_possession_lost"` // counter_press / balanced / regroup
	AfterPossessionWon  string `json:"after_possession_won"`  // counter / balanced / hold_shape
	CounterDirectness   int    `json:"counter_directness"`    // 0-4
	ResetUnderPressure  int    `json:"reset_under_pressure"`  // 0-4
}

// OutOfPossessionInstructions holds team instructions when out of possession.
type OutOfPossessionInstructions struct {
	DefensiveLineHeight int    `json:"defensive_line_height"` // 0-4
	PressingIntensity   int    `json:"pressing_intensity"`    // 0-4
	PressingTrigger     string `json:"pressing_trigger"`      // passive / bad_touch / wide_trap / center_trap / always
	Compactness         int    `json:"compactness"`           // 0-4
	Marking             string `json:"marking"`               // zonal / mixed / man
	TacklingAggression  int    `json:"tackling_aggression"`   // 0-3
	OffsideTrap         int    `json:"offside_trap"`          // 0-2
}

// GoalkeeperDistributionInstructions controls goalkeeper distribution.
type GoalkeeperDistributionInstructions struct {
	DistributionTarget string `json:"distribution_target"` // center_backs / fullbacks / midfield / target_forward / mixed
	DistributionLength string `json:"distribution_length"` // short / balanced / long
	ReleaseSpeed       string `json:"release_speed"`       // slow / balanced / quick
}

// PlayerInstruction holds per-player tactical instructions.
type PlayerInstruction struct {
	PlayerID          string `json:"player_id"`
	CarryBall         int    `json:"carry_ball"`
	PassingRisk       int    `json:"passing_risk"`
	ShootingFrequency int    `json:"shooting_frequency"`
	CrossingFrequency int    `json:"crossing_frequency"`
	PressingIntensity int    `json:"pressing_intensity"`
	HoldPosition      int    `json:"hold_position"`
	ForwardRuns       int    `json:"forward_runs"`
}

// DefaultPlayerInstruction returns the neutral default instruction.
func DefaultPlayerInstruction() PlayerInstruction {
	return PlayerInstruction{
		CarryBall:         2,
		PassingRisk:       2,
		ShootingFrequency: 2,
		CrossingFrequency: 2,
		PressingIntensity: 2,
		HoldPosition:      2,
		ForwardRuns:       2,
	}
}

// SituationalRuleCondition defines when a situational rule triggers.
type SituationalRuleCondition struct {
	MinuteGte         *int `json:"minute_gte,omitempty"`
	MinuteLt          *int `json:"minute_lt,omitempty"`
	GoalDiffLte       *int `json:"goal_diff_lte,omitempty"`
	GoalDiffGte       *int `json:"goal_diff_gte,omitempty"`
	TeamStaminaAvgLte *int `json:"team_stamina_avg_lte,omitempty"`
}

// SituationalRuleOverride defines the instruction overrides applied when the
// rule triggers. Optional pointers distinguish "unset" from "set to zero".
type SituationalRuleOverride struct {
	Tempo               *int    `json:"tempo,omitempty"`
	ShootingFrequency   *int    `json:"shooting_frequency,omitempty"`
	DefensiveLineHeight *int    `json:"defensive_line_height,omitempty"`
	PressingIntensity   *int    `json:"pressing_intensity,omitempty"`
	PassingRisk         *int    `json:"passing_risk,omitempty"`
	CrossingFrequency   *int    `json:"crossing_frequency,omitempty"`
	Width               *int    `json:"width,omitempty"`
	AfterPossessionWon  *string `json:"after_possession_won,omitempty"`
	AfterPossessionLost *string `json:"after_possession_lost,omitempty"`
	BuildUpStyle        *string `json:"build_up_style,omitempty"`
	ChanceCreation      *string `json:"chance_creation,omitempty"`
}

// SituationalRule is a user-defined match situation override.
type SituationalRule struct {
	ID        string                   `json:"id"`
	Name      string                   `json:"name"`
	Enabled   bool                     `json:"enabled"`
	Condition SituationalRuleCondition `json:"condition"`
	Override  SituationalRuleOverride  `json:"override"`
}

// TeamInstructions is the V2 phase-based team instructions container.
type TeamInstructions struct {
	LegacyTeamSliders      TacticalSetup                      `json:"legacy_team_sliders"`
	InPossession           InPossessionInstructions           `json:"in_possession"`
	Transition             TransitionInstructions             `json:"transition"`
	OutOfPossession        OutOfPossessionInstructions        `json:"out_of_possession"`
	GoalkeeperDistribution GoalkeeperDistributionInstructions `json:"goalkeeper_distribution"`
	PlayerInstructions     []PlayerInstruction                `json:"player_instructions"`
	SituationalRules       []SituationalRule                  `json:"situational_rules"`
}

// DefaultTeamInstructions returns a balanced default.
func DefaultTeamInstructions() TeamInstructions {
	return TeamInstructions{
		LegacyTeamSliders: TacticalSetup{},
		InPossession: InPossessionInstructions{
			BuildUpStyle:      "balanced",
			ChanceCreation:    "balanced",
			AttackRoute:       "mixed",
			Width:             2,
			Tempo:             2,
			PassingRisk:       2,
			CrossingFrequency: 2,
			DribbleFrequency:  2,
			ShootingFrequency: 2,
		},
		Transition: TransitionInstructions{
			AfterPossessionLost: "balanced",
			AfterPossessionWon:  "balanced",
			CounterDirectness:   2,
			ResetUnderPressure:  2,
		},
		OutOfPossession: OutOfPossessionInstructions{
			DefensiveLineHeight: 2,
			PressingIntensity:   2,
			PressingTrigger:     "bad_touch",
			Compactness:         1,
			Marking:             "mixed",
			TacklingAggression:  1,
			OffsideTrap:         0,
		},
		GoalkeeperDistribution: GoalkeeperDistributionInstructions{
			DistributionTarget: "mixed",
			DistributionLength: "balanced",
			ReleaseSpeed:       "balanced",
		},
	}
}

// TeamSetup is the input for one team
type TeamSetup struct {
	TeamID           string            `json:"team_id"`
	Name             string            `json:"name"`
	FormationID      string            `json:"formation_id"` // F01-F08
	Players          []PlayerSetup     `json:"players"`      // starting XI (8 for 8v8)
	Bench            []PlayerSetup     `json:"bench"`        // substitutes
	Tactics          TacticalSetup     `json:"tactics"`
	TeamInstructions *TeamInstructions `json:"team_instructions,omitempty"`
}

// TeamRuntime is mutable team state during match
type TeamRuntime struct {
	TeamSetup
	PlayerRuntimes        []*PlayerRuntime
	BenchRuntimes         []*PlayerRuntime
	EffectiveInstructions *TeamInstructions // situational override cache, set per event
}

// Instructions returns the effective team instructions. If a situational
// override has been computed for the current event, use it; otherwise fall back
// to the stored team instructions or derive them from legacy TacticalSetup.
func (t *TeamRuntime) Instructions() TeamInstructions {
	if t.EffectiveInstructions != nil {
		return *t.EffectiveInstructions
	}
	if t.TeamInstructions != nil {
		return *t.TeamInstructions
	}
	return DeriveTeamInstructions(t.Tactics)
}

// DeriveTeamInstructions creates V2 instructions from legacy TacticalSetup.
func DeriveTeamInstructions(t TacticalSetup) TeamInstructions {
	buildUp := "balanced"
	if t.PassingStyle >= 3 {
		buildUp = "short"
	} else if t.PassingStyle <= 1 {
		buildUp = "direct"
	}

	attackRoute := "mixed"
	if t.AttackWidth >= 3 {
		attackRoute = "both_wings"
	} else if t.AttackWidth <= 1 {
		attackRoute = "center"
	}

	afterLost := "balanced"
	if t.PressingIntensity >= 3 {
		afterLost = "counter_press"
	}

	afterWon := "balanced"
	if t.AttackTempo >= 3 {
		afterWon = "counter"
	} else if t.AttackTempo <= 1 {
		afterWon = "hold_shape"
	}

	marking := "mixed"
	if t.MarkingStrategy == 0 {
		marking = "zonal"
	} else if t.MarkingStrategy >= 2 {
		marking = "man"
	}

	return TeamInstructions{
		LegacyTeamSliders: t,
		InPossession: InPossessionInstructions{
			BuildUpStyle:      buildUp,
			ChanceCreation:    "balanced",
			AttackRoute:       attackRoute,
			Width:             t.AttackWidth,
			Tempo:             t.AttackTempo,
			PassingRisk:       2,
			CrossingFrequency: t.CrossingStrategy,
			DribbleFrequency:  2,
			ShootingFrequency: t.ShootingMentality,
		},
		Transition: TransitionInstructions{
			AfterPossessionLost: afterLost,
			AfterPossessionWon:  afterWon,
			CounterDirectness:   t.AttackTempo,
			ResetUnderPressure:  2,
		},
		OutOfPossession: OutOfPossessionInstructions{
			DefensiveLineHeight: t.DefensiveLineHeight,
			PressingIntensity:   t.PressingIntensity,
			PressingTrigger:     "bad_touch",
			Compactness:         t.DefensiveCompactness,
			Marking:             marking,
			TacklingAggression:  t.TacklingAggression,
			OffsideTrap:         t.OffsideTrap,
		},
		GoalkeeperDistribution: GoalkeeperDistributionInstructions{
			DistributionTarget: "mixed",
			DistributionLength: "balanced",
			ReleaseSpeed:       "balanced",
		},
	}
}

func NewTeamRuntime(ts TeamSetup) *TeamRuntime {
	tr := &TeamRuntime{TeamSetup: ts}

	instrMap := make(map[string]PlayerInstruction)
	if ts.TeamInstructions != nil {
		for _, ins := range ts.TeamInstructions.PlayerInstructions {
			instrMap[ins.PlayerID] = ins
		}
	}

	for _, p := range ts.Players {
		pr := NewPlayerRuntime(p)
		if ins, ok := instrMap[p.PlayerID]; ok {
			pr.Instruction = ins
		} else {
			pr.Instruction = DefaultPlayerInstruction()
		}
		tr.PlayerRuntimes = append(tr.PlayerRuntimes, pr)
	}
	for _, p := range ts.Bench {
		benchPlayer := NewPlayerRuntime(p)
		benchPlayer.Substituted = true // mark as on bench initially
		if ins, ok := instrMap[p.PlayerID]; ok {
			benchPlayer.Instruction = ins
		} else {
			benchPlayer.Instruction = DefaultPlayerInstruction()
		}
		tr.BenchRuntimes = append(tr.BenchRuntimes, benchPlayer)
	}
	return tr
}

func (t *TeamRuntime) GetGK() *PlayerRuntime {
	for _, p := range t.PlayerRuntimes {
		if p.Position == "GK" {
			return p
		}
	}
	return t.PlayerRuntimes[0]
}

func (t *TeamRuntime) GetOnFieldOutfield() []*PlayerRuntime {
	var out []*PlayerRuntime
	for _, p := range t.PlayerRuntimes {
		if p.Position != "GK" && !p.RedCard && !p.Substituted {
			out = append(out, p)
		}
	}
	return out
}

func (t *TeamRuntime) GetActivePlayers() []*PlayerRuntime {
	var out []*PlayerRuntime
	for _, p := range t.PlayerRuntimes {
		if !p.RedCard && !p.Substituted {
			out = append(out, p)
		}
	}
	return out
}
