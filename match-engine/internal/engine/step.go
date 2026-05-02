package engine

import (
	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// CandidateInfo represents a possible next event with its weight
type CandidateInfo struct {
	Type        string  `json:"type"`
	Weight      int     `json:"weight"`
	Probability float64 `json:"probability"`
}

// PlayerSnapshot represents a player's current state
type PlayerSnapshot struct {
	ID       string  `json:"id"`
	Name     string  `json:"name"`
	Position string  `json:"position"`
	Stamina  float64 `json:"stamina"`
	OnField  bool    `json:"on_field"`
}

// MatchSnapshot captures the match state at a point in time
type MatchSnapshot struct {
	Score           domain.Score      `json:"score"`
	Minute          float64           `json:"minute"`
	Half            int               `json:"half"`
	Possession      string            `json:"possession"`
	ActiveZone      [2]int            `json:"active_zone"`
	ControlMatrix   [3][3]float64     `json:"control_matrix"`
	ZoneMomentum    [3][3]float64     `json:"zone_momentum"`
	GlobalMomentum  float64           `json:"global_momentum"`
	ControlShift    [3][3]float64     `json:"control_shift"`
	PossessionTicks [2]int            `json:"possession_ticks"`
	CounterBoost    [2]int            `json:"counter_boost"`
	Control         float64           `json:"control"`
	Momentum        float64           `json:"momentum"`
	HomeFlags       domain.TacticalFlags `json:"home_flags"`
	AwayFlags       domain.TacticalFlags `json:"away_flags"`
	HomePlayers     []PlayerSnapshot  `json:"home_players"`
	AwayPlayers     []PlayerSnapshot  `json:"away_players"`
	ControlBreakdown ControlBreakdown  `json:"control_breakdown"`
}

// StepInfo contains everything about a single simulation step
type StepInfo struct {
	PreState      MatchSnapshot     `json:"pre_state"`
	Candidates    []CandidateInfo   `json:"candidates"`
	SelectedIndex int               `json:"selected_index"`
	EventType     string            `json:"event_type"`
	Event         domain.MatchEvent `json:"event"`
	Events        []domain.MatchEvent `json:"events"`
	PostState     MatchSnapshot     `json:"post_state"`
}

// Step executes one iteration of the main simulation loop and returns detailed info.
// The caller is responsible for initializing the MatchState (e.g. via InitMatchState).
func (sim *Simulator) Step(ms *domain.MatchState) (*StepInfo, bool) {
	// Check end conditions
	if ms.Half > 2 {
		return nil, false
	}
	if ms.Half == 1 && ms.Minute >= 25.0 {
		sim.handleHalftime(ms)
		info := &StepInfo{
			EventType: config.EventHalftime,
			Event: domain.MatchEvent{
				Type:  config.EventHalftime,
				Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
			},
			PreState:  buildSnapshot(ms),
			PostState: buildSnapshot(ms),
		}
		return info, true
	}
	if ms.Half == 2 && ms.Minute >= 50.0 {
		sim.addEvent(ms, domain.MatchEvent{
			Type:  config.EventFulltime,
			Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		info := &StepInfo{
			EventType: config.EventFulltime,
			Event: domain.MatchEvent{
				Type:  config.EventFulltime,
				Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
			},
			PreState:  buildSnapshot(ms),
			PostState: buildSnapshot(ms),
		}
		return info, false
	}

	// Pre-step snapshot
	pre := buildSnapshot(ms)

	// Record event count before this step
	eventCountBefore := len(ms.Events)

	// Compute control
	ms.ControlMatrix = ComputeControlMatrix(ms)
	ApplyStaminaDecay(ms)

	// Momentum decay
	sim.decayGlobalMomentum(ms)

	// Control shift decay: inactive zones drift back to natural baseline
	decayControlShift(ms)

	// Counter boost decay
	for i := 0; i < 2; i++ {
		if ms.CounterBoostRemaining[i] > 0 {
			ms.CounterBoostRemaining[i]--
		}
	}

	// Check substitutions
	sim.checkSubstitutions(ms)

	// Track possession
	ms.PossessionTicks[ms.Possession]++

	// Pick and process next event
	selected, candidates := sim.processEvent(ms)

	// Advance clock
	baseSec := 3.5 + sim.r.Float64()*5.0
	ms.AdvanceClock(baseSec)

	// Build candidate info
	var totalWeight int
	for _, c := range candidates {
		totalWeight += c.weight
	}
	cinfos := make([]CandidateInfo, len(candidates))
	selectedIdx := 0
	for i, c := range candidates {
		cinfos[i] = CandidateInfo{
			Type:        c.typ,
			Weight:      c.weight,
			Probability: float64(c.weight) / float64(totalWeight),
		}
		if c.typ == selected {
			selectedIdx = i
		}
	}

	// Collect all events produced in this step
	var stepEvents []domain.MatchEvent
	var ev domain.MatchEvent
	if len(ms.Events) > eventCountBefore {
		stepEvents = ms.Events[eventCountBefore:]
		ev = stepEvents[len(stepEvents)-1]
	}

	post := buildSnapshot(ms)

	return &StepInfo{
		PreState:      pre,
		Candidates:    cinfos,
		SelectedIndex: selectedIdx,
		EventType:     selected,
		Event:         ev,
		Events:        stepEvents,
		PostState:     post,
	}, true
}

// InitMatchState creates a fresh match state from a request
func (sim *Simulator) InitMatchState(req domain.SimulateRequest) *domain.MatchState {
	ms := &domain.MatchState{
		MatchID:    req.MatchID,
		Minute:     0,
		Half:       1,
		Score:      domain.Score{},
		Possession: domain.SideHome,
		ActiveZone: [2]int{1, 1},
		HomeTeam:   domain.NewTeamRuntime(req.HomeTeam),
		AwayTeam:   domain.NewTeamRuntime(req.AwayTeam),
	}

	// Set initial ball holder
	ms.BallHolder = sim.selectKickoffTaker(ms.HomeTeam)

	// Compute initial control matrix so preview shows real values from start
	ms.ControlMatrix = ComputeControlMatrix(ms)

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.HomeTeam.Name,
		OpponentName: ms.AwayTeam.Name,
		PlayerName:   ms.BallHolder.Name,
	})

	return ms
}

func buildSnapshot(ms *domain.MatchState) MatchSnapshot {
	zone := ms.ActiveZone
	return MatchSnapshot{
		Score:            ms.Score,
		Minute:           ms.Minute,
		Half:             ms.Half,
		Possession:       ms.Possession.String(),
		ActiveZone:       zone,
		ControlMatrix:    ms.ControlMatrix,
		ZoneMomentum:     [3][3]float64{},
		GlobalMomentum:   ms.GlobalMomentum,
		ControlShift:     ms.ControlShift,
		PossessionTicks:  ms.PossessionTicks,
		CounterBoost:     ms.CounterBoostRemaining,
		Control:          ms.EffectiveControl(zone),
		Momentum:         ms.GlobalMomentum,
		HomeFlags:        ms.HomeTeam.ComputeTacticalFlags(),
		AwayFlags:        ms.AwayTeam.ComputeTacticalFlags(),
		HomePlayers:      buildPlayerSnapshots(ms.HomeTeam),
		AwayPlayers:      buildPlayerSnapshots(ms.AwayTeam),
		ControlBreakdown: ComputeControlBreakdown(ms, zone),
	}
}

func buildPlayerSnapshots(team *domain.TeamRuntime) []PlayerSnapshot {
	var result []PlayerSnapshot
	for _, p := range team.PlayerRuntimes {
		result = append(result, PlayerSnapshot{
			ID:       p.PlayerID,
			Name:     p.Name,
			Position: p.Position,
			Stamina:  p.CurrentStamina,
			OnField:  true,
		})
	}
	for _, p := range team.BenchRuntimes {
		result = append(result, PlayerSnapshot{
			ID:       p.PlayerID,
			Name:     p.Name,
			Position: p.Position,
			Stamina:  p.CurrentStamina,
			OnField:  false,
		})
	}
	return result
}
