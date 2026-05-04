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

	ControlMatrix [3][3]float64 // absolute reference: positive = home advantage
	ControlShift  [3][3]float64 // event-driven offset from natural control, decays in inactive zones
	GlobalMomentum float64       // global scalar momentum, range [-0.3, 0.3]

	BallHolder *PlayerRuntime // current player with the ball
	LastPasser *PlayerRuntime  // last successful passer on the possession team (for assist tracking)

	PossessionTicks [2]int // home, away

	CounterBoostRemaining [2]int // remaining events with counter-attack boost (home, away)

	LastEventType string
	ChainState    string // none, ongoing, goal, turnover, set_piece
	AddedTime     float64 // stoppage time for second half (in minutes)
	AddedTimeAnnounced bool

	EventCounter int
	Events       []MatchEvent

	HomeStats struct {
		Shots, ShotsOnTarget, Passes, PassesSucc, KeyPasses int
		Crosses, CrossesSucc, Dribbles, DribblesSucc int
		Tackles, TacklesSucc, Interceptions, Clearances, Blocks int
		Headers, HeaderWins, Saves int
		Corners, Fouls, FoulsDrawn, Offsides int
		YellowCards, RedCards int
		FreeKicks, FreeKickGoals, Penalties, PenaltyGoals int
	}
	AwayStats struct {
		Shots, ShotsOnTarget, Passes, PassesSucc, KeyPasses int
		Crosses, CrossesSucc, Dribbles, DribblesSucc int
		Tackles, TacklesSucc, Interceptions, Clearances, Blocks int
		Headers, HeaderWins, Saves int
		Corners, Fouls, FoulsDrawn, Offsides int
		YellowCards, RedCards int
		FreeKicks, FreeKickGoals, Penalties, PenaltyGoals int
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

// EffectiveControl returns control from the possession team's perspective.
// It combines the natural ControlMatrix with the event-driven ControlShift.
func (m *MatchState) EffectiveControl(zone [2]int) float64 {
	v := m.ControlMatrix[zone[0]][zone[1]] + m.ControlShift[zone[0]][zone[1]]
	// Front zone naturally favors defense — it's much harder to maintain
	// control in the penalty area due to compact defending and high stakes
	if zone[0] == 0 {
		v *= 0.65
	}
	if m.Possession == SideAway {
		return -v
	}
	return v
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
