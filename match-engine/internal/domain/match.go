package domain

// Side represents home or away
type Side int

const (
	SideHome Side = iota
	SideAway
)

func (s Side) String() string {
	if s == SideHome {
		return "home"
	}
	return "away"
}

func (s Side) Opponent() Side {
	if s == SideHome {
		return SideAway
	}
	return SideHome
}

// MatchState holds the full running state
type MatchState struct {
	MatchID    string
	Minute     float64
	Half       int
	Score      Score
	Possession Side
	ActiveZone [2]int // [row, col]

	HomeTeam *TeamRuntime
	AwayTeam *TeamRuntime

	ControlMatrix [3][3]float64 // from possession team's perspective
	ZoneMomentum  [3][3]float64 // dynamic control shift from recent events

	PossessionTicks [2]int // home, away

	LastEventType string
	ChainState    string // none, ongoing, goal, turnover, set_piece

	EventCounter int
	Events       []MatchEvent

	HomeStats struct {
		Shots, ShotsOnTarget, Passes, PassesSucc, Tackles, TacklesSucc int
		Corners, Fouls, YellowCards, RedCards int
	}
	AwayStats struct {
		Shots, ShotsOnTarget, Passes, PassesSucc, Tackles, TacklesSucc int
		Corners, Fouls, YellowCards, RedCards int
	}
}

func (m *MatchState) Team(side Side) *TeamRuntime {
	if side == SideHome {
		return m.HomeTeam
	}
	return m.AwayTeam
	}

func (m *MatchState) OppTeam(side Side) *TeamRuntime {
	if side == SideHome {
		return m.AwayTeam
	}
	return m.HomeTeam
}

func (m *MatchState) AddEvent(ev MatchEvent) {
	ev.ID = m.EventCounter
	m.EventCounter++
	m.Events = append(m.Events, ev)
}

func (m *MatchState) AdvanceClock(baseSeconds float64) {
	// Attack tempo affects clock speed
	tempo := m.Team(m.Possession).Tactics.AttackTempo
	speed := 1.0
	switch tempo {
	case 0:
		speed = 0.8
	case 1:
		speed = 0.9
	case 3:
		speed = 1.15
	case 4:
		speed = 1.3
	}
	m.Minute += baseSeconds * speed / 60.0
}
