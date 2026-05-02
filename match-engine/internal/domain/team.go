package domain

// TacticalSetup from design doc (simplified MVP)
type TacticalSetup struct {
	PassingStyle         int                       `json:"passing_style"`          // 0-4
	AttackWidth          int                       `json:"attack_width"`           // 0-4
	AttackTempo          int                       `json:"attack_tempo"`           // 0-4
	DefensiveLineHeight  int                       `json:"defensive_line_height"`  // 0-4
	CrossingStrategy     int                       `json:"crossing_strategy"`      // 0-4
	ShootingMentality    int                       `json:"shooting_mentality"`     // 0-4
	PlaymakerFocus       int                       `json:"playmaker_focus"`        // 0-4
	PressingIntensity    int                       `json:"pressing_intensity"`     // 0-4
	DefensiveCompactness int                       `json:"defensive_compactness"`  // 0-2
	MarkingStrategy      int                       `json:"marking_strategy"`       // 0-2
	OffsideTrap          int                       `json:"offside_trap"`           // 0-2
	TacklingAggression   int                       `json:"tackling_aggression"`    // 0-3
}

// TeamSetup is the input for one team
type TeamSetup struct {
	TeamID      string         `json:"team_id"`
	Name        string         `json:"name"`
	FormationID string         `json:"formation_id"` // F01-F08
	Players     []PlayerSetup  `json:"players"`      // starting XI (8 for 8v8)
	Bench       []PlayerSetup  `json:"bench"`        // substitutes
	Tactics     TacticalSetup  `json:"tactics"`
}

// TeamRuntime is mutable team state during match
type TeamRuntime struct {
	TeamSetup
	PlayerRuntimes []*PlayerRuntime
	BenchRuntimes  []*PlayerRuntime
}

func NewTeamRuntime(ts TeamSetup) *TeamRuntime {
	tr := &TeamRuntime{TeamSetup: ts}
	for _, p := range ts.Players {
		tr.PlayerRuntimes = append(tr.PlayerRuntimes, NewPlayerRuntime(p))
	}
	for _, p := range ts.Bench {
		benchPlayer := NewPlayerRuntime(p)
		benchPlayer.Substituted = true // mark as on bench initially
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
