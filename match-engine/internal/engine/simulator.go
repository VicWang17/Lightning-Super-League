package engine

import (
	"fmt"
	"math"
	"math/rand/v2"
	"strings"
	"time"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// Simulator is the match engine
type Simulator struct {
	r                *rand.Rand
	ng               *NarrativeGenerator
	lastCrossQuality float64
}

func NewSimulator(seed uint64) *Simulator {
	if seed == 0 {
		seed = uint64(time.Now().UnixNano())
	}
	return &Simulator{
		r:  rand.New(rand.NewPCG(seed, seed+777)),
		ng: NewNarrativeGenerator(seed + 333),
	}
}

func newTacticalTracking() domain.TacticalTracking {
	return domain.TacticalTracking{
		RouteUsage:              make(map[string]int),
		EventCounts:             make(map[string]int),
		InstructionTriggers:     make(map[string]int),
		SituationalRuleTriggers: make(map[string]int),
	}
}

func (sim *Simulator) Simulate(req domain.SimulateRequest) domain.SimulateResult {
	start := time.Now()

	// Init state
	ms := &domain.MatchState{
		MatchID:      req.MatchID,
		Minute:       0,
		Half:         1,
		Score:        domain.Score{},
		Possession:   domain.SideHome,
		ActiveZone:   [2]int{1, 1},
		HomeTeam:     domain.NewTeamRuntime(req.HomeTeam),
		AwayTeam:     domain.NewTeamRuntime(req.AwayTeam),
		HomeTactical: newTacticalTracking(),
		AwayTactical: newTacticalTracking(),
	}

	// Set initial ball holder (home team kickoff taker)
	ms.BallHolder = sim.selectKickoffTaker(ms.HomeTeam)

	// Pre-match broadcast
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventPreMatch,
		Team:         ms.HomeTeam.Name,
		OpponentName: ms.AwayTeam.Name,
	})
	// Kickoff
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.HomeTeam.Name,
		OpponentName: ms.AwayTeam.Name,
		PlayerName:   ms.BallHolder.Name,
	})

	// Main loop
	prevMinute := ms.Minute
	for ms.Half <= 2 {
		// Advantage play: don't blow whistle during dangerous attack in front zone
		if ms.Half == 1 && ms.Minute >= 25.0 {
			if ms.ActiveZone[0] == 0 && ms.Minute < 26.5 {
				// Allow up to 1.5 extra minutes for dangerous attack
			} else {
				sim.handleHalftime(ms)
				continue
			}
		}
		if ms.Half == 2 && ms.Minute >= 50.0 {
			// Announce added time once when crossing 50 min
			if !ms.AddedTimeAnnounced {
				ms.AddedTimeAnnounced = true
				sim.addEvent(ms, domain.MatchEvent{
					Type:       config.EventAddedTime,
					ExtraValue: ms.AddedTime,
					Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
				})
			}
			limit := 50.0 + ms.AddedTime
			if ms.ActiveZone[0] == 0 && ms.Minute < limit+1.5 {
				// Allow up to 1.5 extra minutes for dangerous attack beyond added time
			} else if ms.Minute >= limit {
				break
			}
		}

		// Compute control
		ms.ControlMatrix = ComputeControlMatrix(ms)
		ApplyStaminaDecay(ms)

		// Momentum decay: global momentum fades over time
		sim.decayGlobalMomentum(ms)

		// Control shift decay: inactive zones drift back to natural baseline
		decayControlShift(ms)

		// Counter boost decay: each event reduces remaining counter boost by 1
		for i := 0; i < 2; i++ {
			if ms.CounterBoostRemaining[i] > 0 {
				ms.CounterBoostRemaining[i]--
			}
		}

		// Track possession
		ms.PossessionTicks[ms.Possession]++
		if ms.Possession == domain.SideHome {
			ms.HomeTactical.PossessionByZone[ms.ActiveZone[0]][ms.ActiveZone[1]]++
		} else {
			ms.AwayTactical.PossessionByZone[ms.ActiveZone[0]][ms.ActiveZone[1]]++
		}

		// Pick and process next event
		_, _ = sim.processEvent(ms)

		// Substitutions only on dead ball
		if len(ms.Events) > 0 {
			last := ms.Events[len(ms.Events)-1]
			if isDeadBallEvent(last.Type) {
				sim.checkSubstitutions(ms)
			}
		}

		// Advance clock (slower pace for more realistic build-up)
		baseSec := 4.0 + sim.r.Float64()*3.5
		ms.AdvanceClock(baseSec)

		// Apply per-minute wear to all on-field players
		if int(ms.Minute) > int(prevMinute) {
			sim.applyMinuteWear(ms)
		}

		// Fast recovery skill: every 5 minutes
		if int(ms.Minute/5) > int(prevMinute/5) {
			ApplyFastRecovery(ms)
		}
		prevMinute = ms.Minute
	}

	resolution := "draw"
	if ms.Score.Home != ms.Score.Away {
		resolution = "regular"
	} else if req.RequiresWinner {
		resolution = sim.runExtraTime(ms)
	}

	var penaltyScore *domain.Score
	if req.RequiresWinner && ms.Score.Home == ms.Score.Away {
		resolution = "penalties"
		penaltyScore = sim.runPenaltyShootout(ms)
	}

	winnerTeamID := ""
	if ms.Score.Home > ms.Score.Away {
		winnerTeamID = ms.HomeTeam.TeamID
	} else if ms.Score.Away > ms.Score.Home {
		winnerTeamID = ms.AwayTeam.TeamID
	} else if penaltyScore != nil {
		if penaltyScore.Home > penaltyScore.Away {
			winnerTeamID = ms.HomeTeam.TeamID
		} else {
			winnerTeamID = ms.AwayTeam.TeamID
		}
	}

	// Fulltime
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventFulltime,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})

	// Build result
	result := sim.buildResult(ms)
	result.Resolution = resolution
	result.WinnerTeamID = winnerTeamID
	result.PenaltyScore = penaltyScore
	result.DurationMs = time.Since(start).Milliseconds()
	return result
}

func (sim *Simulator) runExtraTime(ms *domain.MatchState) string {
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventExtraTimeStart,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})
	ms.Half = 3
	ms.Minute = 50.0

	prevMinute := ms.Minute
	secondPeriodAnnounced := false
	for ms.Minute < 70.0 {
		if !secondPeriodAnnounced && ms.Minute >= 60.0 {
			secondPeriodAnnounced = true
			ms.Half = 4
			sim.addEvent(ms, domain.MatchEvent{
				Type:  config.EventExtraTimeSecondHalfStart,
				Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
			})
		}

		ms.ControlMatrix = ComputeControlMatrix(ms)
		ApplyStaminaDecay(ms)
		sim.decayGlobalMomentum(ms)
		decayControlShift(ms)
		for i := 0; i < 2; i++ {
			if ms.CounterBoostRemaining[i] > 0 {
				ms.CounterBoostRemaining[i]--
			}
		}
		ms.PossessionTicks[ms.Possession]++
		if ms.Possession == domain.SideHome {
			ms.HomeTactical.PossessionByZone[ms.ActiveZone[0]][ms.ActiveZone[1]]++
		} else {
			ms.AwayTactical.PossessionByZone[ms.ActiveZone[0]][ms.ActiveZone[1]]++
		}
		_, _ = sim.processEvent(ms)
		if len(ms.Events) > 0 {
			last := ms.Events[len(ms.Events)-1]
			if isDeadBallEvent(last.Type) {
				sim.checkSubstitutions(ms)
			}
		}

		baseSec := 4.0 + sim.r.Float64()*3.5
		ms.AdvanceClock(baseSec)

		// Apply per-minute wear to all on-field players
		if int(ms.Minute) > int(prevMinute) {
			sim.applyMinuteWear(ms)
		}

		if int(ms.Minute/5) > int(prevMinute/5) {
			ApplyFastRecovery(ms)
		}
		prevMinute = ms.Minute
	}

	if ms.Score.Home != ms.Score.Away {
		return "extra_time"
	}
	return "draw"
}

func (sim *Simulator) runPenaltyShootout(ms *domain.MatchState) *domain.Score {
	homeGoals := 0
	awayGoals := 0
	homeTaken := 0
	awayTaken := 0

	for i := 0; i < 5 || homeGoals == awayGoals; i++ {
		homeTaken++
		if sim.r.Float64() < sim.penaltyShootoutChance(ms.HomeTeam, ms.AwayTeam) {
			homeGoals++
		}
		awayTaken++
		if sim.r.Float64() < sim.penaltyShootoutChance(ms.AwayTeam, ms.HomeTeam) {
			awayGoals++
		}
		if i >= 4 && homeGoals != awayGoals {
			break
		}
		if i > 12 {
			break
		}
	}

	if homeGoals == awayGoals {
		if sim.r.Float64() < 0.5 {
			homeGoals++
		} else {
			awayGoals++
		}
	}

	score := &domain.Score{Home: homeGoals, Away: awayGoals}
	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventPenaltyShootout,
		Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		ExtraValue: float64(homeTaken + awayTaken),
		Narrative:  fmt.Sprintf("Penalty shootout finished %d-%d", homeGoals, awayGoals),
	})
	return score
}

func (sim *Simulator) penaltyShootoutChance(attacking, defending *domain.TeamRuntime) float64 {
	takers := attacking.GetActivePlayers()
	keeper := defending.GetGK()
	if len(takers) == 0 || keeper == nil {
		return 0.72
	}
	taker := takers[sim.r.IntN(len(takers))]
	setPiece := taker.GetAttrByName("SET")
	shooting := taker.GetAttrByName("SHO")
	composure := taker.GetAttrByName("COM")
	keeperValue := keeper.GetAttrByName("SAV")*0.35 + keeper.GetAttrByName("REF")*0.35 + keeper.GetAttrByName("POS")*0.2 + keeper.GetAttrByName("COM")*0.1
	attackValue := setPiece*0.45 + shooting*0.3 + composure*0.25
	chance := 0.72 + (attackValue-keeperValue)*0.015
	if chance < 0.55 {
		chance = 0.55
	}
	if chance > 0.9 {
		chance = 0.9
	}
	return chance
}

func (sim *Simulator) processEvent(ms *domain.MatchState) (string, []candidateEvent) {
	ctrl := ms.EffectiveControl(ms.ActiveZone)
	zone := ms.ActiveZone
	possTeam := ms.Team(ms.Possession)
	oppTeam := ms.OppTeam(ms.Possession)

	// V4: compute situational rule overrides for both teams at event start.
	// These are cached on TeamRuntime and used by all Instructions() callers.
	homeEff, homeTriggered := ComputeEffectiveInstructions(ms.HomeTeam, ms)
	awayEff, awayTriggered := ComputeEffectiveInstructions(ms.AwayTeam, ms)
	ms.HomeTeam.EffectiveInstructions = &homeEff
	ms.AwayTeam.EffectiveInstructions = &awayEff

	// Track which situational rules influenced this event.
	for _, id := range homeTriggered {
		ms.HomeTactical.SituationalRuleTriggers[id]++
	}
	for _, id := range awayTriggered {
		ms.AwayTactical.SituationalRuleTriggers[id]++
	}

	// Determine available events based on zone and control
	var candidates []candidateEvent

	// === Tactical weight modifiers ===
	passingStyle := possTeam.Tactics.PassingStyle
	crossingStrategy := possTeam.Tactics.CrossingStrategy
	playFromBack := possTeam.Tactics.DefensiveLineHeight >= 2 && possTeam.Tactics.PassingStyle <= 1

	// Always available: passing events (base weight modified by passing style)
	shortPassWeight := 28
	backPassWeight := 25
	midPassWeight := 36
	longPassWeight := 8
	throughWeight := 10

	// Passing style adjustments
	switch passingStyle {
	case 0: // Long ball
		longPassWeight += 10
		shortPassWeight -= 5
		backPassWeight -= 5
	case 1: // Direct
		throughWeight += 5
		longPassWeight += 3
	case 3: // Short pass
		shortPassWeight += 8
		throughWeight += 3
	case 4: // Tiki-taka
		shortPassWeight += 12
		backPassWeight += 8
		midPassWeight += 5
	}

	candidates = append(candidates, candidateEvent{typ: config.EventShortPass, weight: shortPassWeight})

	if zone[0] == 2 { // back zone
		candidates = append(candidates, candidateEvent{typ: config.EventBackPass, weight: backPassWeight})
		if !playFromBack {
			candidates = append(candidates, candidateEvent{typ: config.EventLongPass, weight: longPassWeight})
		} else {
			// Play from back: prefer short passing, reduce long pass
			candidates = append(candidates, candidateEvent{typ: config.EventLongPass, weight: longPassWeight / 2})
		}
	}
	if zone[0] == 1 { // mid zone
		candidates = append(candidates, candidateEvent{typ: config.EventMidPass, weight: midPassWeight + 10})
		candidates = append(candidates, candidateEvent{typ: config.EventThroughBall, weight: throughWeight - 5}) // much harder to thread into box
	}
	if zone[0] == 0 { // front zone
		candidates = append(candidates, candidateEvent{typ: config.EventCloseShot, weight: 2})
		crossWeight := 5
		switch crossingStrategy {
		case 0: // Avoid crossing
			crossWeight -= 3
		case 1: // Low cross
			crossWeight += 2
		case 3: // High cross
			crossWeight += 3
		case 4: // Frequent cross
			crossWeight += 6
		}
		candidates = append(candidates, candidateEvent{typ: config.EventCross, weight: crossWeight})
		// Limited passing in front zone — players prioritize shooting
		candidates = append(candidates, candidateEvent{typ: config.EventShortPass, weight: 4})
		candidates = append(candidates, candidateEvent{typ: config.EventLongShot, weight: 6})
		// Hold ball in front zone: rare, only when control is very high
		if ctrl > 0.4 {
			candidates = append(candidates, candidateEvent{typ: config.EventHoldBall, weight: 3})
		}
	}

	// Wing zones
	if zone[1] == 0 || zone[1] == 2 {
		candidates = append(candidates, candidateEvent{typ: config.EventWingBreak, weight: 9})
		if zone[0] <= 1 {
			candidates = append(candidates, candidateEvent{typ: config.EventCutInside, weight: 7})
		}
		// Switch play (lateral transfer) available on wings
		candidates = append(candidates, candidateEvent{typ: config.EventSwitchPlay, weight: 8})
	}

	// Dribble past: available in mid/front zones across all channels
	if zone[0] <= 1 {
		candidates = append(candidates, candidateEvent{typ: config.EventDribblePast, weight: 10})
	}

	// Lob pass and pass over top in mid/front zones
	if zone[0] <= 1 {
		candidates = append(candidates, candidateEvent{typ: config.EventLobPass, weight: 2})
		candidates = append(candidates, candidateEvent{typ: config.EventPassOverTop, weight: 2})
	}

	// Block pass: defender anticipates pass route
	if ctrl < 0.3 {
		candidates = append(candidates, candidateEvent{typ: config.EventBlockPass, weight: 5})
	}

	// One on one: very rare, only when attacker has overwhelming control
	if zone[0] == 0 && ctrl > 0.7 {
		candidates = append(candidates, candidateEvent{typ: config.EventOneOnOne, weight: 2})
	}

	// Counter attack: boosted when counter boost is active or low control in opponent half
	// GK cannot carry out a dribbling counter-attack
	if ms.BallHolder.Position != config.PosGK {
		if ms.CounterBoostRemaining[int(ms.Possession)] > 0 {
			candidates = append(candidates, candidateEvent{typ: config.EventCounterAttack, weight: 15})
		} else if zone[0] <= 1 && ctrl < -0.1 {
			// Defensive team wins ball back in opponent half → counter opportunity
			candidates = append(candidates, candidateEvent{typ: config.EventCounterAttack, weight: 5})
		}
	}

	// Goalkeeper ball handling in back zone
	if zone[0] == 2 && ms.BallHolder.Position == config.PosGK {
		candidates = append(candidates, candidateEvent{typ: config.EventGoalKick, weight: 12})
		candidates = append(candidates, candidateEvent{typ: config.EventKeeperShortPass, weight: 10})
		candidates = append(candidates, candidateEvent{typ: config.EventKeeperThrow, weight: 5})

		// V2: goalkeeper distribution instructions adjust candidate weights
		gkInstr := possTeam.Instructions().GoalkeeperDistribution
		for i := range candidates {
			switch candidates[i].typ {
			case config.EventGoalKick, config.EventKeeperShortPass, config.EventKeeperThrow:
				candidates[i].weight = int(float64(candidates[i].weight) * gkDistributionWeightMod(gkInstr, candidates[i].typ))
				if candidates[i].weight < 1 {
					candidates[i].weight = 1
				}
			}
		}
	}

	// Throw-in on sidelines (low weight, simulates dead ball restarts)
	if zone[1] == 0 || zone[1] == 2 {
		candidates = append(candidates, candidateEvent{typ: config.EventThrowIn, weight: 3})
	}

	// Multi-player events (Phase 3)
	if zone[1] == 0 || zone[1] == 2 {
		// Overlap on wings
		candidates = append(candidates, candidateEvent{typ: config.EventOverlap, weight: 5})
	}
	if zone[0] <= 1 {
		// Triangle pass and one-two in mid/front zones
		candidates = append(candidates, candidateEvent{typ: config.EventTrianglePass, weight: 6})
		candidates = append(candidates, candidateEvent{typ: config.EventOneTwo, weight: 6})
	}
	if zone[0] == 0 {
		// Cross run in front zone
		candidates = append(candidates, candidateEvent{typ: config.EventCrossRun, weight: 4})
	}
	// Defensive multi-player events
	if ctrl < 0.2 && zone[0] <= 1 {
		candidates = append(candidates, candidateEvent{typ: config.EventDoubleTeam, weight: 4})
		candidates = append(candidates, candidateEvent{typ: config.EventPressTogether, weight: 3})
	}

	// Drop ball — very rare dead ball restart
	if sim.r.Float64() < 0.002 {
		candidates = append(candidates, candidateEvent{typ: config.EventDropBall, weight: 1})
	}

	// Long shot from mid
	if zone[0] == 1 && ctrl > 0.2 {
		longShotWeight := 2
		if possTeam.Tactics.ShootingMentality >= 3 {
			longShotWeight += 3
		} else if possTeam.Tactics.ShootingMentality <= 1 {
			longShotWeight -= 1
		}
		candidates = append(candidates, candidateEvent{typ: config.EventLongShot, weight: longShotWeight})
	}

	// Build-up events: patient back-line passing
	if zone[0] == 2 && ctrl > 0.05 {
		candidates = append(candidates, candidateEvent{typ: config.EventBuildUp, weight: 8})
	}

	// Hold ball: player shields and waits for support
	if zone[0] >= 1 && ctrl > 0.05 {
		candidates = append(candidates, candidateEvent{typ: config.EventHoldBall, weight: 16})
	}

	// Pivot pass: midfield lateral distribution (high-success, low-progression)
	if zone[0] == 1 {
		candidates = append(candidates, candidateEvent{typ: config.EventPivotPass, weight: 20})
		candidates = append(candidates, candidateEvent{typ: config.EventBuildUp, weight: 8})
	}

	// Defensive events — reduced weights for calmer rhythm
	clearanceWeight := 8
	if playFromBack && zone[0] == 2 {
		clearanceWeight = 2 // Play from back reduces clearance tendency
	}
	if ctrl < 0.25 {
		tackleWeight := 5
		interceptWeight := 4
		if zone[0] == 2 {
			tackleWeight = 3
			interceptWeight = 2
		} else if zone[0] == 1 {
			tackleWeight = 2
			interceptWeight = 2
		} else if zone[0] == 0 {
			tackleWeight = 5
			interceptWeight = 6
		}
		candidates = append(candidates, candidateEvent{typ: config.EventTackle, weight: tackleWeight})
		candidates = append(candidates, candidateEvent{typ: config.EventIntercept, weight: interceptWeight})
		// Clearance always available in front zone — defenders prioritize clearing danger
		if zone[0] == 0 {
			candidates = append(candidates, candidateEvent{typ: config.EventClearance, weight: clearanceWeight + 4})
		}
	}

	// Penalty area defense: defenders are always alert in front of goal
	if zone[0] == 0 {
		candidates = append(candidates, candidateEvent{typ: config.EventTackle, weight: 2})
		candidates = append(candidates, candidateEvent{typ: config.EventIntercept, weight: 3})
	}

	// Header duel available in front zone
	if zone[0] == 0 {
		headerWeight := 6
		if crossingStrategy >= 3 {
			headerWeight += 4 // High cross strategy boosts header attempts
		}
		candidates = append(candidates, candidateEvent{typ: config.EventHeader, weight: headerWeight})
	}

	// Foul: low probability anywhere, increased by aggression
	foulWeight := 1
	if possTeam.Tactics.TacklingAggression >= 2 {
		foulWeight += int(possTeam.Tactics.TacklingAggression) / 2
	}
	if oppTeam.Tactics.TacklingAggression >= 2 {
		foulWeight += int(oppTeam.Tactics.TacklingAggression) / 2
	}
	// Players are much more careful in the penalty area
	if zone[0] == 0 && zone[1] == 1 {
		foulWeight = int(float64(foulWeight) * 0.20)
	}
	if foulWeight < 1 {
		foulWeight = 1
	}
	candidates = append(candidates, candidateEvent{typ: config.EventFoul, weight: foulWeight})

	// Control factor boosts attacking events when control is high
	for i := range candidates {
		if candidates[i].typ == config.EventBackPass || candidates[i].typ == config.EventMidPass ||
			candidates[i].typ == config.EventShortPass || candidates[i].typ == config.EventLongPass {
			continue // passing always available
		}
		candidates[i].weight = int(float64(candidates[i].weight) * (1.0 + ctrl*0.4))
		if candidates[i].weight < 1 {
			candidates[i].weight = 1
		}
	}

	// Apply DEC (decision making) adjustment to candidate weights
	sim.adjustCandidatesByDEC(candidates, ms.BallHolder, ms, possTeam, oppTeam)

	// Playmaker focus: team-wide passing boost
	pf := possTeam.Tactics.PlaymakerFocus
	if pf > 0 {
		passBoost := 1.0 + float64(pf)*0.08
		shotReduce := 1.0 - float64(pf)*0.075
		throughBoost := 1.0 + float64(pf)*0.05
		for i := range candidates {
			switch candidates[i].typ {
			case config.EventShortPass, config.EventMidPass, config.EventBackPass:
				candidates[i].weight = int(float64(candidates[i].weight) * passBoost)
			case config.EventThroughBall:
				candidates[i].weight = int(float64(candidates[i].weight) * throughBoost)
			case config.EventLongShot:
				candidates[i].weight = int(float64(candidates[i].weight) * shotReduce)
			}
		}
	}

	// Chain-state adjustment based on previous event outcome
	candidates = sim.adjustCandidatesByLastEvent(candidates, ms)

	// V2: attack route modifies event weights for the possession team
	attackRoute := possTeam.Instructions().InPossession.AttackRoute
	if attackRoute != "mixed" {
		for i := range candidates {
			candidates[i].weight = int(float64(candidates[i].weight) * attackRouteWeightMod(attackRoute, candidates[i].typ))
			if candidates[i].weight < 1 {
				candidates[i].weight = 1
			}
		}
	}

	// V2: passing risk and build-up style modify pass/attack event weights
	instr := possTeam.Instructions().InPossession
	for i := range candidates {
		mod := passingRiskWeightMod(instr.PassingRisk, candidates[i].typ) *
			buildUpStyleWeightMod(instr.BuildUpStyle, candidates[i].typ)
		candidates[i].weight = int(float64(candidates[i].weight) * mod)
		if candidates[i].weight < 1 {
			candidates[i].weight = 1
		}
	}

	// V3: per-player instructions for the current ball holder
	for i := range candidates {
		candidates[i].weight = int(float64(candidates[i].weight) * playerInstructionWeight(ms.BallHolder, candidates[i].typ))
		if candidates[i].weight < 1 {
			candidates[i].weight = 1
		}
	}

	// Skill-based event weight adjustments (speed demon, killer pass, playmaker)
	for i := range candidates {
		ctx := SkillContext{
			EventType: candidates[i].typ,
			Player:    ms.BallHolder,
			Zone:      zone,
			Minute:    ms.Minute,
			Half:      ms.Half,
		}
		bonus := ComputeSkillBonus(ctx)
		if bonus.WeightMod > 0 {
			candidates[i].weight = int(float64(candidates[i].weight) * bonus.WeightMod)
			if candidates[i].weight < 1 {
				candidates[i].weight = 1
			}
		}
	}

	// Select event
	selected := sim.pickEvent(candidates)
	possBefore := ms.Possession
	holderBefore := ms.BallHolder

	// === Cover Defense interrupt: high-control attacks may be broken up by defensive cover ===
	highRiskEvents := map[string]bool{
		config.EventOneOnOne:  true,
		config.EventCross:     true,
		config.EventWingBreak: true,
		config.EventCutInside: true,
		config.EventCloseShot: true,
	}
	if highRiskEvents[selected] && sim.shouldTriggerCoverDefense(ms, oppTeam, zone) {
		sim.doCoverDefenseEvent(ms, possTeam, oppTeam, zone)
		// After cover defense, if possession changed, handle turnover
		if ms.Possession != possBefore {
			sim.addEvent(ms, domain.MatchEvent{
				Type:         config.EventTurnover,
				Team:         ms.Team(ms.Possession).Name,
				PlayerID:     ms.BallHolder.PlayerID,
				PlayerName:   ms.BallHolder.Name,
				OpponentName: ms.Team(possBefore).Name,
			})
			sim.flipControlShiftOnTurnover(ms, zone)
		}
		return selected, candidates
	}

	// Set skill context for the ball holder before event execution
	setSkillContext(ms.BallHolder, selected, zone, ms.Minute, ms.Half)

	ms.BallHolder.Stats.Touches++
	sim.executeEvent(ms, selected)

	// Track tactical signals
	sim.trackEvent(ms, selected, possBefore, zone)

	// === Post-event tactical effects ===
	isAttackingEvent := selected != config.EventTackle && selected != config.EventIntercept && selected != config.EventClearance
	if ms.Possession != possBefore && isAttackingEvent {
		holderBefore.Stats.Turnovers++
		// Skip turnover if the last event already narrated the possession change
		skipTurnover := false
		if len(ms.Events) > 0 {
			last := ms.Events[len(ms.Events)-1]
			if last.Result == "fail" || last.Result == "blocked" || last.Result == "saved" || last.Result == "missed" || last.Result == "woodwork" {
				skipTurnover = true
			}
			if last.Type == config.EventTackle || last.Type == config.EventIntercept || last.Type == config.EventClearance || last.Type == config.EventBlockPass {
				skipTurnover = true
			}
			// Dead-ball restarts already transition possession naturally
			if last.Type == config.EventKickoff || last.Type == config.EventGoalKick || last.Type == config.EventCorner ||
				last.Type == config.EventThrowIn || last.Type == config.EventDropBall || last.Type == config.EventKeeperShortPass ||
				last.Type == config.EventKeeperThrow {
				skipTurnover = true
			}
		}
		if !skipTurnover {
			// Turnover occurred: emit transition event
			sim.addEvent(ms, domain.MatchEvent{
				Type:         config.EventTurnover,
				Team:         ms.Team(ms.Possession).Name,
				PlayerID:     ms.BallHolder.PlayerID,
				PlayerName:   ms.BallHolder.Name,
				OpponentName: ms.Team(possBefore).Name,
			})
		}

		// Flip control shift in the zone where it happened
		sim.flipControlShiftOnTurnover(ms, zone)

		// V2: apply transition instructions (counter / hold_shape / counter_press / regroup)
		sim.applyTransitionInstructions(ms, possBefore, zone)
	}

	return selected, candidates
}

// trackEvent updates per-side tactical counters used in the post-match summary.
func (sim *Simulator) trackEvent(ms *domain.MatchState, eventType string, possBefore domain.Side, zone [2]int) {
	track := func(side domain.Side) *domain.TacticalTracking {
		if side == domain.SideHome {
			return &ms.HomeTactical
		}
		return &ms.AwayTactical
	}

	// Event frequency by type
	track(ms.Possession).EventCounts[eventType]++

	// V3: track when a non-default player instruction influences an event.
	trackInstructionTrigger(track(ms.Possession), ms.BallHolder, eventType)

	// Attack route usage for possession team's attacking events
	attackingEvents := map[string]bool{
		config.EventShortPass:     true,
		config.EventMidPass:       true,
		config.EventLongPass:      true,
		config.EventThroughBall:   true,
		config.EventCross:         true,
		config.EventWingBreak:     true,
		config.EventCutInside:     true,
		config.EventSwitchPlay:    true,
		config.EventOverlap:       true,
		config.EventTrianglePass:  true,
		config.EventOneTwo:        true,
		config.EventPivotPass:     true,
		config.EventBuildUp:       true,
		config.EventCounterAttack: true,
		config.EventCloseShot:     true,
		config.EventLongShot:      true,
		config.EventOneOnOne:      true,
		config.EventHeader:        true,
		config.EventDribblePast:   true,
		config.EventLobPass:       true,
		config.EventPassOverTop:   true,
	}
	if attackingEvents[eventType] {
		route := ms.Team(ms.Possession).Instructions().InPossession.AttackRoute
		track(ms.Possession).RouteUsage[route]++
	}

	// Shots by zone
	if eventType == config.EventCloseShot || eventType == config.EventLongShot || eventType == config.EventOneOnOne {
		track(ms.Possession).ShotsByZone[zone[0]][zone[1]]++
	}

	// Counter attacks
	if eventType == config.EventCounterAttack {
		track(ms.Possession).CounterAttacks++
	}

	// Goalkeeper distributions (when GK has the ball in back zone)
	if zone[0] == 2 && ms.BallHolder != nil && ms.BallHolder.Position == config.PosGK {
		switch eventType {
		case config.EventKeeperShortPass, config.EventKeeperThrow:
			track(ms.Possession).GkShortDistributions++
		case config.EventGoalKick, config.EventLongPass:
			track(ms.Possession).GkLongDistributions++
		}
		// Track distribution target preference usage
		gkInstr := ms.Team(ms.Possession).Instructions().GoalkeeperDistribution
		key := "gk_" + gkInstr.DistributionTarget
		track(ms.Possession).RouteUsage[key]++
	}

	// Turnovers: possession changed due to an attacking event failure
	isDefensiveEvent := eventType == config.EventTackle || eventType == config.EventIntercept ||
		eventType == config.EventClearance || eventType == config.EventBlockPass
	if ms.Possession != possBefore {
		track(possBefore).TurnoversByZone[zone[0]][zone[1]]++

		// High press recovery: possession won back in opponent half by a team using high press
		winnerTeam := ms.Team(ms.Possession)
		if zone[0] <= 1 && winnerTeam.Tactics.DefensiveLineHeight >= 3 && winnerTeam.Tactics.PressingIntensity >= 3 {
			track(ms.Possession).HighPressRecoveries++
		}
	} else if isDefensiveEvent {
		// Defensive win without full turnover still counts as press win
		track(ms.Possession).PressWinsByZone[zone[0]][zone[1]]++
	}
}

type candidateEvent struct {
	typ    string
	weight int
}

func setSkillContext(player *domain.PlayerRuntime, eventType string, zone [2]int, minute float64, half int) {
	if player != nil {
		player.SkillEventType = eventType
		player.SkillZone = zone
		player.SkillMinute = minute
		player.SkillHalf = half
	}
}

func (sim *Simulator) pickEvent(candidates []candidateEvent) string {
	var total int
	for _, c := range candidates {
		total += c.weight
	}
	pick := sim.r.IntN(total)
	cum := 0
	for _, c := range candidates {
		cum += c.weight
		if pick < cum {
			return c.typ
		}
	}
	return candidates[0].typ
}

// computeExpectedGain calculates the expected value of choosing a particular event type,
// considering the ball holder's abilities vs opponent defenders/keeper and current match situation.
func (sim *Simulator) computeExpectedGain(evType string, holder *domain.PlayerRuntime, ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime) float64 {
	ctrl := ms.EffectiveControl(ms.ActiveZone)
	zone := ms.ActiveZone

	switch evType {
	case config.EventCloseShot:
		keeper := oppTeam.GetGK()
		keeperStr := keeper.GetAttrByName("SAV")*0.15 + keeper.GetAttrByName("REF")*0.10 + keeper.GetAttrByName("POS")*0.05 + 3.5
		nearestDef := SelectDefender(oppTeam, zone, sim.r)
		defStr := nearestDef.GetAttrByName("DEF")*0.4 + nearestDef.GetAttrByName("TKL")*0.3 + nearestDef.GetAttrByName("HEA")*0.3
		shotStr := holder.GetAttrByName("SHO")*0.45 + holder.GetAttrByName("FIN")*0.35 + holder.GetAttrByName("COM")*0.20
		return shotStr - keeperStr*0.4 - defStr*0.3 + ctrl*5.0

	case config.EventLongShot:
		keeper := oppTeam.GetGK()
		keeperStr := keeper.GetAttrByName("SAV")*0.15 + keeper.GetAttrByName("POS")*0.05 + keeper.GetAttrByName("REF")*0.05 + 3.5
		shotStr := holder.GetAttrByName("FIN")*0.45 + holder.GetAttrByName("SHO")*0.30 + holder.GetAttrByName("STR")*0.15 + holder.GetAttrByName("BAL")*0.10
		return shotStr - keeperStr*0.3 - 2.0 + ctrl*3.0

	case config.EventShortPass, config.EventMidPass:
		passStr := holder.GetAttrByName("PAS")*0.5 + holder.GetAttrByName("VIS")*0.3 + holder.GetAttrByName("CON")*0.2
		zonePressure := 0.0
		if zone[0] == 0 {
			zonePressure = 2.0
		}
		return passStr + ctrl*3.0 - zonePressure

	case config.EventBackPass:
		passStr := holder.GetAttrByName("PAS")*0.4 + holder.GetAttrByName("CON")*0.4 + holder.GetAttrByName("VIS")*0.2
		return passStr + 1.5 + ctrl*2.0

	case config.EventCross:
		crossStr := holder.GetAttrByName("CRO")*0.5 + holder.GetAttrByName("PAS")*0.3 + holder.GetAttrByName("DRI")*0.2
		return crossStr + ctrl*2.0

	case config.EventWingBreak, config.EventCutInside:
		dribbleStr := holder.GetAttrByName("DRI")*0.4 + holder.GetAttrByName("SPD")*0.3 + holder.GetAttrByName("ACC")*0.3
		nearestDef := SelectDefender(oppTeam, zone, sim.r)
		defStr := nearestDef.GetAttrByName("DEF")*0.4 + nearestDef.GetAttrByName("TKL")*0.3 + nearestDef.GetAttrByName("SPD")*0.3
		return dribbleStr - defStr + ctrl*3.0

	case config.EventThroughBall:
		passStr := holder.GetAttrByName("PAS")*0.5 + holder.GetAttrByName("VIS")*0.4 + holder.GetAttrByName("ACC")*0.1
		offsidePenalty := float64(oppTeam.Tactics.OffsideTrap) * 0.5
		return passStr + ctrl*4.0 - offsidePenalty

	case config.EventHeader:
		headerStr := holder.GetAttrByName("HEA")*0.5 + holder.GetAttrByName("STR")*0.3 + holder.GetAttrByName("SPD")*0.2
		return headerStr + ctrl*2.0

	case config.EventLongPass:
		passStr := holder.GetAttrByName("PAS")*0.5 + holder.GetAttrByName("STR")*0.2 + holder.GetAttrByName("VIS")*0.3
		return passStr + ctrl*2.0 - 1.0

	case config.EventTackle, config.EventIntercept:
		// Defensive events from attacker's perspective: negative value
		return -3.0 + ctrl*2.0

	case config.EventClearance:
		// From attacker's perspective: very negative (loses possession)
		return -5.0 + ctrl*2.0

	case config.EventFoul:
		// Foul against attacker: results in free kick for attacker (positive!)
		return 2.0 + ctrl*2.0

	default:
		return 0.0
	}
}

// adjustCandidatesByDEC modifies event candidate weights based on the ball holder's DEC (decision making).
// High DEC biases weights toward higher expected-gain options; low DEC biases toward lower expected-gain options.
func (sim *Simulator) adjustCandidatesByDEC(candidates []candidateEvent, holder *domain.PlayerRuntime, ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime) {
	dec := holder.GetAttrByName("DEC")
	if dec <= 0 {
		return
	}

	// Linear factor: DEC=10 -> 0, DEC=20 -> +0.18, DEC=1 -> -0.18 (sensitivity=0.36)
	decFactor := (dec - 10.0) / 20.0 * 0.36

	// Compute expected gain for each candidate
	gains := make([]float64, len(candidates))
	var avgGain float64
	for i, c := range candidates {
		gains[i] = sim.computeExpectedGain(c.typ, holder, ms, possTeam, oppTeam)
		avgGain += gains[i]
	}
	avgGain /= float64(len(gains))

	// Find max deviation for normalization
	maxDev := 0.1
	for _, g := range gains {
		dev := math.Abs(g - avgGain)
		if dev > maxDev {
			maxDev = dev
		}
	}

	// Adjust weights
	for i := range candidates {
		normalizedGain := (gains[i] - avgGain) / maxDev // -1 ~ +1
		adjustment := 1.0 + decFactor*normalizedGain
		if adjustment < 0.75 {
			adjustment = 0.75
		}
		if adjustment > 1.25 {
			adjustment = 1.25
		}
		candidates[i].weight = int(float64(candidates[i].weight) * adjustment)
		if candidates[i].weight < 1 {
			candidates[i].weight = 1
		}
	}
}

// adjustCandidatesByLastEvent modifies candidate weights based on the previous event type
// and chain state, enforcing narrative consistency rules.
func (sim *Simulator) adjustCandidatesByLastEvent(candidates []candidateEvent, ms *domain.MatchState) []candidateEvent {
	zone := ms.ActiveZone
	lastEvent := ms.LastEventType

	// Rule 3 (cross chain): after a successful cross (low or high) that did NOT
	// immediately produce a shot, the next event in the attacking zone must be
	// a finishing action. Only direct shooting events are allowed (no second header).
	if ms.ChainState == "cross_chain" && zone[0] == 0 {
		ms.ChainState = "" // consume the state
		for i := range candidates {
			switch candidates[i].typ {
			case config.EventCloseShot, config.EventLongShot, config.EventOneOnOne:
				// keep original weight
			default:
				// Ban all non-shooting events to prevent infinite header loops
				candidates[i].weight = 0
			}
		}
		return candidates
	}

	// Clear stale chain state if zone moved away from front
	if ms.ChainState == "cross_chain" && zone[0] != 0 {
		ms.ChainState = ""
	}

	// Rule 1: through ball success into front zone -> boost shot/1v1, ban back pass, reduce cross/pass
	if lastEvent == config.EventThroughBall && zone[0] == 0 {
		for i := range candidates {
			switch candidates[i].typ {
			case config.EventCloseShot, config.EventOneOnOne:
				candidates[i].weight *= 3
			case config.EventBackPass:
				candidates[i].weight = 0
			case config.EventCross, config.EventShortPass, config.EventMidPass,
				config.EventLongPass, config.EventLobPass, config.EventSwitchPlay,
				config.EventTrianglePass, config.EventPivotPass, config.EventBuildUp:
				candidates[i].weight /= 5
				if candidates[i].weight < 1 {
					candidates[i].weight = 1
				}
			}
		}
	}

	// Rule 4: one-two success -> ban consecutive one-two
	if lastEvent == config.EventOneTwo {
		for i := range candidates {
			if candidates[i].typ == config.EventOneTwo {
				candidates[i].weight = 0
			}
		}
	}

	// Rule 5: wing break / cut inside / dribble past success into front zone -> shot weight x2
	if (lastEvent == config.EventWingBreak || lastEvent == config.EventCutInside ||
		lastEvent == config.EventDribblePast) && zone[0] == 0 {
		for i := range candidates {
			if candidates[i].typ == config.EventCloseShot || candidates[i].typ == config.EventOneOnOne ||
				candidates[i].typ == config.EventLongShot {
				candidates[i].weight *= 2
			}
		}
	}

	return candidates
}

// handlePassFailure checks if a failed pass goes out of play instead of being intercepted.
// Returns true if out-of-play was handled (caller should skip normal fail logic).
// Returns false if the defender intercepted normally.
func (sim *Simulator) handlePassFailure(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, passType string, defender *domain.PlayerRuntime, isForward bool) bool {
	outChance := 0.0
	isWing := zone[1] == 0 || zone[1] == 2

	if isWing {
		outChance += 0.30
	}
	if isForward && zone[0] <= 1 {
		outChance += 0.15
	}
	if passType == config.EventLongPass || passType == config.EventThroughBall ||
		passType == config.EventLobPass || passType == config.EventPassOverTop {
		outChance += 0.06
	}

	if outChance > 0.70 {
		outChance = 0.70
	}
	if outChance < 0.05 {
		outChance = 0.05
	}

	if sim.r.Float64() >= outChance {
		return false
	}

	// Record pass stats (failed attempt still counts)
	holder := ms.BallHolder
	holder.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
	} else {
		ms.AwayStats.Passes++
	}

	// Ball went out of play — record the failed pass
	sim.addEvent(ms, domain.MatchEvent{
		Type:         passType,
		Team:         possTeam.Name,
		PlayerID:     ms.BallHolder.PlayerID,
		PlayerName:   ms.BallHolder.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       "fail",
	})

	// Record out-of-play event
	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventPassOut,
		Team:       possTeam.Name,
		PlayerID:   ms.BallHolder.PlayerID,
		PlayerName: ms.BallHolder.Name,
		Zone:       zoneStr(zone),
		Result:     "out",
	})

	// Switch possession to opponent for restart
	ms.Possession = ms.Possession.Opponent()

	// Consume time for ball retrieval (less than full restart since we're chaining)
	ms.AdvanceClock(0.5 + sim.r.Float64()*1.0)

	if isWing {
		// Side line → throw-in by opponent
		ms.BallHolder = SelectPlayerByZone(oppTeam, zone, sim.r)
		sim.doThrowInEvent(ms, oppTeam, possTeam, zone)
	} else {
		// Goal line
		if isForward {
			// Forward pass over goal line → goal kick for opponent
			ms.BallHolder = oppTeam.GetGK()
			sim.doGoalKickEvent(ms, oppTeam, possTeam, zone)
		} else {
			// Backward pass over own goal line → corner for opponent
			sim.doCornerEvent(ms, oppTeam, possTeam)
		}
	}

	return true
}

func (sim *Simulator) executeEvent(ms *domain.MatchState, evType string) {
	possTeam := ms.Team(ms.Possession)
	oppTeam := ms.OppTeam(ms.Possession)
	zone := ms.ActiveZone
	ctrl := ms.EffectiveControl(zone)

	switch evType {
	case config.EventBackPass, config.EventMidPass, config.EventShortPass:
		sim.doPassEvent(ms, evType, possTeam, oppTeam, zone, ctrl)
	case config.EventLongPass:
		sim.doLongPassEvent(ms, possTeam, oppTeam, zone)
	case config.EventWingBreak:
		sim.doWingBreakEvent(ms, possTeam, oppTeam, zone)
	case config.EventCutInside:
		sim.doCutInsideEvent(ms, possTeam, oppTeam, zone)
	case config.EventDribblePast:
		sim.doDribblePastEvent(ms, possTeam, oppTeam, zone)
	case config.EventThroughBall:
		sim.doThroughBallEvent(ms, possTeam, oppTeam, zone)
	case config.EventCross:
		sim.doCrossEvent(ms, possTeam, oppTeam, zone)
	case config.EventCloseShot:
		sim.doShotEvent(ms, possTeam, oppTeam, zone, "close")
	case config.EventLongShot:
		sim.doShotEvent(ms, possTeam, oppTeam, zone, "long")
	case config.EventCorner:
		sim.doCornerEvent(ms, possTeam, oppTeam)
	case config.EventTackle:
		sim.doTackleEvent(ms, possTeam, oppTeam, zone)
	case config.EventIntercept:
		sim.doInterceptEvent(ms, possTeam, oppTeam, zone)
	case config.EventClearance:
		sim.doClearanceEvent(ms, possTeam, oppTeam, zone)
	case config.EventFoul:
		sim.doFoulEvent(ms, possTeam, oppTeam, zone)
	case config.EventHeader:
		sim.doHeaderDuel(ms, possTeam, oppTeam)
	case config.EventSwitchPlay:
		sim.doSwitchPlayEvent(ms, possTeam, oppTeam, zone)
	case config.EventLobPass:
		sim.doLobPassEvent(ms, possTeam, oppTeam, zone)
	case config.EventPassOverTop:
		sim.doPassOverTopEvent(ms, possTeam, oppTeam, zone)
	case config.EventBlockPass:
		sim.doBlockPassEvent(ms, possTeam, oppTeam, zone)
	case config.EventOneOnOne:
		sim.doOneOnOneEvent(ms, possTeam, oppTeam, zone)
	case config.EventCoverDefense:
		sim.doCoverDefenseEvent(ms, possTeam, oppTeam, zone)
	case config.EventGoalKick:
		sim.doGoalKickEvent(ms, possTeam, oppTeam, zone)
	case config.EventThrowIn:
		sim.doThrowInEvent(ms, possTeam, oppTeam, zone)
	case config.EventKeeperShortPass:
		sim.doKeeperShortPassEvent(ms, possTeam, oppTeam, zone)
	case config.EventKeeperThrow:
		sim.doKeeperThrowEvent(ms, possTeam, oppTeam, zone)
	case config.EventCounterAttack:
		sim.doCounterAttackEvent(ms, possTeam, oppTeam, zone)
	case config.EventOverlap:
		sim.doOverlapEvent(ms, possTeam, oppTeam, zone)
	case config.EventTrianglePass:
		sim.doTrianglePassEvent(ms, possTeam, oppTeam, zone)
	case config.EventOneTwo:
		sim.doOneTwoEvent(ms, possTeam, oppTeam, zone)
	case config.EventCrossRun:
		sim.doCrossRunEvent(ms, possTeam, oppTeam, zone)
	case config.EventDoubleTeam:
		sim.doDoubleTeamEvent(ms, possTeam, oppTeam, zone)
	case config.EventPressTogether:
		sim.doPressTogetherEvent(ms, possTeam, oppTeam, zone)
	case config.EventDropBall:
		sim.doDropBallEvent(ms, possTeam, oppTeam, zone)
	case config.EventHoldBall:
		sim.doHoldBallEvent(ms, possTeam, zone)
	case config.EventPivotPass:
		sim.doPivotPassEvent(ms, possTeam, oppTeam, zone)
	case config.EventBuildUp:
		sim.doBuildUpEvent(ms, possTeam, oppTeam, zone)
	}
	ms.LastEventType = evType
}

func (sim *Simulator) doPassEvent(ms *domain.MatchState, passType string, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, ctrl float64) {
	holder := ms.BallHolder
	target := SelectPassTarget(possTeam, zone, sim.r, oppTeam)
	// Safety guard: GK should not receive passes in attacking or midfield zones
	if target.Position == config.PosGK && zone[0] < 2 {
		for _, p := range possTeam.GetActivePlayers() {
			if p.Position != config.PosGK && p.PlayerID != holder.PlayerID {
				target = p
				break
			}
		}
	}

	// === No-pressure pass system ===
	// Not every pass faces direct defensive challenge.
	// Back-zone passes are often unpressured; front-zone passes almost always are.
	noPressureBase := 0.0
	switch zone[0] {
	case 2: // back zone
		noPressureBase = 0.55
	case 1: // mid zone
		noPressureBase = 0.40
	case 0: // front zone
		noPressureBase = 0.02
	}
	noPressureProb := noPressureBase + ctrl*0.30 + holder.GetAttrByName("VIS")*0.005
	if noPressureProb < 0.05 {
		noPressureProb = 0.05
	}
	if noPressureProb > 0.80 {
		noPressureProb = 0.80
	}
	hasPressure := sim.r.Float64() >= noPressureProb

	// === Aggressiveness branching (only when under pressure) ===
	passDetail := "safe"
	var pressure *domain.PlayerRuntime
	var atkVal, defVal float64
	var success bool

	if hasPressure {
		pressure = SelectDefender(oppTeam, zone, sim.r)
		riskIdx := ComputeRiskIndex(possTeam.Tactics)
		aggroProb := sigmoid(riskIdx*3.0+ctrl*1.5-2.0) * 0.6
		if aggroProb < 0.05 {
			aggroProb = 0.05
		}
		if aggroProb > 0.80 {
			aggroProb = 0.80
		}
		isAggressive := sim.r.Float64() < aggroProb

		atkVal = CalcPassAttack(holder, ctrl)
		defVal = CalcPassDefense(pressure, ctrl)
		defVal += 0.30 // moderate pressure on passing
		// Front zone: dense defense makes passing much harder
		if zone[0] == 0 {
			defVal += 0.60
		}
		if oppTeam.Tactics.DefensiveCompactness >= 2 {
			defVal += 0.3
		}

		if isAggressive {
			passDetail = "aggressive"
			atkVal -= 0.20 // increased penalty from 0.10
		} else {
			atkVal += 0.25 // increased bonus from 0.15
		}

		success = ResolveDuel(atkVal, defVal, sim.r)
		ConsumeStamina(holder, StaminaCost(passType))
		ConsumeStamina(pressure, StaminaCost(passType)*0.5)
	} else {
		// Unpressured pass: automatic success
		success = true
		ConsumeStamina(holder, StaminaCost(passType)*0.5)
	}

	result := "success"
	if !success {
		if pressure != nil && sim.handlePassFailure(ms, possTeam, oppTeam, zone, passType, pressure, passType != config.EventBackPass) {
			return
		}
		sim.clearAssistCandidate(ms)
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = zone
		ms.BallHolder = pressure // defender wins possession
		sim.flipGlobalMomentum(ms)
	} else {
		if passDetail == "aggressive" {
			sim.applyControlShift(ms, ms.ActiveZone, 0.08)
		} else {
			sim.applyControlShift(ms, ms.ActiveZone, 0.02)
		}
		sim.clearAssistCandidate(ms)
		sim.boostGlobalMomentum(ms, 0.01)
	}

	// Update stats
	holder.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
			holder.Stats.PassesSucc++
			holder.Stats.RatingBase += 0.02
		} else {
			holder.Stats.RatingBase -= 0.02
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
			holder.Stats.PassesSucc++
			holder.Stats.RatingBase += 0.02
		} else {
			holder.Stats.RatingBase -= 0.02
		}
	}

	ev := domain.MatchEvent{
		Type:        passType,
		Team:        ms.Possession.String(),
		PlayerID:    holder.PlayerID,
		PlayerName:  holder.Name,
		Player2ID:   target.PlayerID,
		Player2Name: target.Name,
		Zone:        zoneStr(zone),
		Result:      result,
		Detail:      passDetail,
	}
	if pressure != nil {
		ev.OpponentID = pressure.PlayerID
		ev.OpponentName = pressure.Name
	}
	sim.addEvent(ms, ev)

	// Advance zone on success
	if success {
		passQuality := holder.GetAttrByName("PAS")*0.5 +
			holder.GetAttrByName("VIS")*0.3 +
			holder.GetAttrByName("CON")*0.2
		receiveQuality := target.GetAttrByName("SPD")*0.3 +
			target.GetAttrByName("ACC")*0.3 +
			target.GetAttrByName("POS")*0.4

		// Successful midfield passing should make measurable progress instead of
		// repeatedly recycling possession in the same zone.
		passBonus := (holder.GetAttrByName("PAS") - 10.0) * 0.0015
		forwardProb := 0.02 + sigmoid((passQuality+receiveQuality-20.0+ctrl*3.0)/5.0)*0.14 + passBonus
		if zone[0] == 1 {
			forwardProb += 0.04
		}
		if forwardProb < 0.01 {
			forwardProb = 0.01
		}
		if forwardProb > 0.22 {
			forwardProb = 0.22
		}

		// Backward chance
		backwardProb := 0.10 + sigmoid((20.0-passQuality-receiveQuality-ctrl*5.0)/5.0)*0.30
		if backwardProb < 0.05 {
			backwardProb = 0.05
		}
		if backwardProb > 0.40 {
			backwardProb = 0.40
		}

		// Unpressured passes move less (patient build-up)
		if !hasPressure {
			forwardProb *= 0.4
			backwardProb *= 0.4
		}

		// FW target always gets a forward bonus
		if target.Position == config.PosFW && zone[0] > 0 {
			forwardProb += 0.15
		}

		roll := sim.r.Float64()
		if roll < forwardProb && zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		} else if roll < forwardProb+backwardProb && zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] + 1, zone[1]}
		}
		// else: stay in same zone
		ms.BallHolder = target
	}
}

// doHoldBallEvent — player shields the ball and waits for support (no duel, no zone change)
func (sim *Simulator) doHoldBallEvent(ms *domain.MatchState, possTeam *domain.TeamRuntime, zone [2]int) {
	holder := ms.BallHolder
	ConsumeStamina(holder, 0.3)
	sim.applyControlShift(ms, zone, 0.01)
	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventHoldBall,
		Team:       possTeam.Name,
		PlayerID:   holder.PlayerID,
		PlayerName: holder.Name,
		Zone:       zoneStr(zone),
		Result:     "success",
	})
}

// doPivotPassEvent — midfield lateral distribution, high success, low progression
func (sim *Simulator) doPivotPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	holder := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventPivotPass, zone, ms.Minute, ms.Half)
	target := SelectPassTarget(possTeam, zone, sim.r, oppTeam)

	// Pivot pass gets a natural bonus for midfield orchestrators
	atkVal := CalcPassAttack(holder, ms.EffectiveControl(zone)) + 0.4
	defVal := CalcPassDefense(defender, ms.EffectiveControl(zone)) + 0.25

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(holder, StaminaCost(config.EventMidPass))
	ConsumeStamina(defender, StaminaCost(config.EventMidPass)*0.5)

	result := "success"
	if !success {
		if sim.handlePassFailure(ms, possTeam, oppTeam, zone, config.EventPivotPass, defender, false) {
			return
		}
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		// Pivot play remains patient, but it should occasionally break the midfield line.
		if sim.r.Float64() < 0.14 && zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		} else if sim.r.Float64() < 0.20 && zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] + 1, zone[1]}
		}
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.02)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventPivotPass,
		Team:         ms.Possession.String(),
		PlayerID:     holder.PlayerID,
		PlayerName:   holder.Name,
		Player2ID:    target.PlayerID,
		Player2Name:  target.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doBuildUpEvent — back-line passing sequence, 2-3 players, single duel check
func (sim *Simulator) doBuildUpEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	p1 := ms.BallHolder
	p2 := SelectPassTarget(possTeam, zone, sim.r, oppTeam)
	if p2.PlayerID == p1.PlayerID {
		for _, p := range possTeam.GetActivePlayers() {
			if p.PlayerID != p1.PlayerID && p.Position != config.PosGK {
				p2 = p
				break
			}
		}
	}
	p3 := SelectPassTarget(possTeam, zone, sim.r, oppTeam)
	if p3.PlayerID == p1.PlayerID || p3.PlayerID == p2.PlayerID {
		for _, p := range possTeam.GetActivePlayers() {
			if p.PlayerID != p1.PlayerID && p.PlayerID != p2.PlayerID && p.Position != config.PosGK {
				p3 = p
				break
			}
		}
	}
	setSkillContext(p3, config.EventBuildUp, zone, ms.Minute, ms.Half)
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventBuildUp, zone, ms.Minute, ms.Half)

	atkVal := CalcBuildUpAttack(p1, p2, p3) + ms.EffectiveControl(zone)*2.0
	defVal := CalcBuildUpDefense(defender) + 0.25

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(p1, 0.4)
	ConsumeStamina(p2, 0.3)
	ConsumeStamina(p3, 0.3)

	result := "success"
	if !success {
		if sim.handlePassFailure(ms, possTeam, oppTeam, zone, config.EventBuildUp, defender, false) {
			return
		}
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		// Build-up rarely leaves back zone
		if sim.r.Float64() < 0.15 && zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		}
		ms.BallHolder = p3
		sim.applyControlShift(ms, zone, 0.03)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventBuildUp,
		Team:         ms.Possession.String(),
		PlayerID:     p1.PlayerID,
		PlayerName:   p1.Name,
		Player2ID:    p3.PlayerID,
		Player2Name:  p3.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       p2.Name, // intermediate passer stored in Detail
	})
}

func (sim *Simulator) doLongPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	holder := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventLongPass, zone, ms.Minute, ms.Half)

	atkVal := CalcLongPassAttack(holder)
	defVal := CalcLongPassDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(holder, StaminaCost(config.EventLongPass))

	result := "success"
	if !success {
		if sim.handlePassFailure(ms, possTeam, oppTeam, zone, config.EventLongPass, defender, true) {
			return
		}
		sim.clearAssistCandidate(ms)
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
	} else {
		sim.clearAssistCandidate(ms)
	}

	holder.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
			holder.Stats.PassesSucc++
			holder.Stats.RatingBase += 0.03
		} else {
			holder.Stats.RatingBase -= 0.02
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
			holder.Stats.PassesSucc++
			holder.Stats.RatingBase += 0.03
		} else {
			holder.Stats.RatingBase -= 0.02
		}
	}
	ev := domain.MatchEvent{
		Type:         config.EventLongPass,
		Team:         ms.Possession.String(),
		PlayerID:     holder.PlayerID,
		PlayerName:   holder.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	}

	if success {
		// Jump to front zone
		newCol := sim.r.IntN(3)
		ms.ActiveZone = [2]int{0, newCol}
		target := SelectPlayerByZone(possTeam, ms.ActiveZone, sim.r)
		ms.BallHolder = target
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}

	sim.addEvent(ms, ev)

	if success {
		sim.applyControlShift(ms, ms.ActiveZone, 0.08)
		sim.boostGlobalMomentum(ms, 0.02)
	} else {
		sim.flipGlobalMomentum(ms)
	}
}

func (sim *Simulator) doWingBreakEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	dribbler := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventWingBreak, zone, ms.Minute, ms.Half)

	atkVal := CalcDribbleAttack(dribbler)
	defVal := CalcDribbleDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(dribbler, StaminaCost(config.EventWingBreak))
	ConsumeStamina(defender, StaminaCost(config.EventWingBreak)*0.6)
	sim.applyWearForAction(dribbler, "sprint")
	sim.applyWearForAction(defender, "direction_change")
	if dribbler.CurrentStamina < 30 {
		sim.maybeApplyInjury(ms, dribbler, "sprint_fatigue", defender)
	}

	dribbler.Stats.Dribbles++
	if possTeam == ms.HomeTeam {
		ms.HomeStats.Dribbles++
		if success {
			ms.HomeStats.DribblesSucc++
			dribbler.Stats.DribblesSucc++
		}
	} else {
		ms.AwayStats.Dribbles++
		if success {
			ms.AwayStats.DribblesSucc++
			dribbler.Stats.DribblesSucc++
		}
	}

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		sim.applyControlShift(ms, zone, 0.10)
		sim.boostGlobalMomentum(ms, 0.03)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventWingBreak,
		Team:         ms.Possession.String(),
		PlayerID:     dribbler.PlayerID,
		PlayerName:   dribbler.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})

	if success && zone[0] > 0 {
		// Breakthrough advances one zone, creating better passing angles
		ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
	}
}

func (sim *Simulator) doCutInsideEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	dribbler := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventCutInside, zone, ms.Minute, ms.Half)

	atkVal := dribbler.GetAttrByName("DRI")*0.4 + dribbler.GetAttrByName("SHO")*0.2 +
		dribbler.GetAttrByName("ACC")*0.2 + dribbler.GetAttrByName("SPD")*0.2
	defVal := defender.GetAttrByName("DEF")*0.4 + defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("POS")*0.3

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(dribbler, StaminaCost(config.EventCutInside))
	sim.applyWearForAction(dribbler, "direction_change")

	dribbler.Stats.Dribbles++
	if possTeam == ms.HomeTeam {
		ms.HomeStats.Dribbles++
		if success {
			ms.HomeStats.DribblesSucc++
			dribbler.Stats.DribblesSucc++
		}
	} else {
		ms.AwayStats.Dribbles++
		if success {
			ms.AwayStats.DribblesSucc++
			dribbler.Stats.DribblesSucc++
		}
	}

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		sim.applyControlShift(ms, zone, 0.10)
		sim.boostGlobalMomentum(ms, 0.03)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventCutInside,
		Team:         ms.Possession.String(),
		PlayerID:     dribbler.PlayerID,
		PlayerName:   dribbler.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})

	if success {
		// Dynamic advance based on gap between dribbler and defender
		gap := atkVal - defVal
		if gap > 2.5 {
			ms.ActiveZone = [2]int{0, 1} // fully beat defender, into box
		} else if zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, 1} // partial advance
		}
	}
}

func (sim *Simulator) doDribblePastEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	dribbler := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventDribblePast, zone, ms.Minute, ms.Half)

	atkVal := CalcDribbleAttack(dribbler)
	defVal := CalcDribbleDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(dribbler, StaminaCost(config.EventDribblePast))
	ConsumeStamina(defender, StaminaCost(config.EventDribblePast)*0.6)
	sim.applyWearForAction(dribbler, "sprint")
	sim.applyWearForAction(defender, "direction_change")
	if dribbler.CurrentStamina < 30 {
		sim.maybeApplyInjury(ms, dribbler, "sprint_fatigue", defender)
	}

	dribbler.Stats.Dribbles++
	if possTeam == ms.HomeTeam {
		ms.HomeStats.Dribbles++
		if success {
			ms.HomeStats.DribblesSucc++
			dribbler.Stats.DribblesSucc++
		}
	} else {
		ms.AwayStats.Dribbles++
		if success {
			ms.AwayStats.DribblesSucc++
			dribbler.Stats.DribblesSucc++
		}
	}

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		sim.applyControlShift(ms, zone, 0.10)
		sim.boostGlobalMomentum(ms, 0.03)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventDribblePast,
		Team:         ms.Possession.String(),
		PlayerID:     dribbler.PlayerID,
		PlayerName:   dribbler.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})

	if success {
		// Dribble past primarily boosts control; only sometimes advances zone
		if zone[0] > 0 && sim.r.Float64() < 0.15 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		}
	}
}

func (sim *Simulator) doThroughBallEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	passer := ms.BallHolder
	target := SelectPassTarget(possTeam, [2]int{0, 1}, sim.r, oppTeam)
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)
	setSkillContext(defender, config.EventThroughBall, [2]int{0, 1}, ms.Minute, ms.Half)

	atkVal := CalcThroughAttack(passer)
	defVal := CalcThroughDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(passer, StaminaCost(config.EventThroughBall))

	result := "success"
	if !success {
		if sim.handlePassFailure(ms, possTeam, oppTeam, zone, config.EventThroughBall, defender, true) {
			return
		}
		sim.clearAssistCandidate(ms)
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
	}

	passer.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
			passer.Stats.PassesSucc++
			passer.Stats.RatingBase += 0.08
			sim.setAssistCandidate(ms, passer, config.EventThroughBall)
		} else {
			passer.Stats.RatingBase -= 0.03
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
			passer.Stats.PassesSucc++
			passer.Stats.RatingBase += 0.08
			sim.setAssistCandidate(ms, passer, config.EventThroughBall)
		} else {
			passer.Stats.RatingBase -= 0.03
		}
	}
	if success {
		passer.Stats.KeyPasses++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.KeyPasses++
		} else {
			ms.AwayStats.KeyPasses++
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventThroughBall,
		Team:         ms.Possession.String(),
		PlayerID:     passer.PlayerID,
		PlayerName:   passer.Name,
		Player2ID:    target.PlayerID,
		Player2Name:  target.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})

	if success {
		// Offside check for through ball
		offsideTrap := oppTeam.Tactics.OffsideTrap
		offsideChance := 0.08 - float64(offsideTrap)*0.025
		if offsideChance < 0.01 {
			offsideChance = 0.01
		}
		if sim.r.Float64() < offsideChance {
			// Offside!
			target.Stats.Offsides++
			if possTeam == ms.HomeTeam {
				ms.HomeStats.Offsides++
			} else {
				ms.AwayStats.Offsides++
			}
			sim.addEvent(ms, domain.MatchEvent{
				Type:       config.EventOffside,
				Team:       possTeam.Name,
				PlayerID:   target.PlayerID,
				PlayerName: target.Name,
				Zone:       zoneStr([2]int{0, 1}),
			})
			ms.Possession = ms.Possession.Opponent()
			ms.ActiveZone = [2]int{2, 1}
			ms.BallHolder = sim.selectKickoffTaker(oppTeam)
			sim.flipGlobalMomentum(ms)
			return
		}
		ms.ActiveZone = [2]int{0, 1}
		ms.BallHolder = target
		sim.applyControlShift(ms, ms.ActiveZone, 0.12)
		sim.boostGlobalMomentum(ms, 0.03)
	} else {
		sim.flipGlobalMomentum(ms)
	}
}

func (sim *Simulator) doCrossEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	crosser := ms.BallHolder
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)
	setSkillContext(defender, config.EventCross, [2]int{0, 1}, ms.Minute, ms.Half)

	atkVal := CalcCrossAttack(crosser)
	defVal := CalcCrossDefense(defender)

	// Crossing strategy affects cross quality
	crossingStrategy := possTeam.Tactics.CrossingStrategy
	switch crossingStrategy {
	case 0: // Avoid crossing — when forced, lower quality
		atkVal -= 0.8
	case 1: // Low cross — better precision
		atkVal += 0.3
	case 3: // High cross — more aerial threat
		atkVal += 0.2
	case 4: // Frequent cross — slightly lower quality due to volume
		atkVal -= 0.2
	}

	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(crosser, StaminaCost(config.EventCross))

	crosser.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
	} else {
		ms.AwayStats.Passes++
	}

	crosser.Stats.Crosses++
	if possTeam == ms.HomeTeam {
		ms.HomeStats.Crosses++
	} else {
		ms.AwayStats.Crosses++
	}

	result := "success"
	if !success {
		result = "fail"
		sim.clearAssistCandidate(ms)
		// Dynamic corner chance based on cross quality vs defender positioning
		crossQuality := crosser.GetAttrByName("CRO")*0.5 +
			crosser.GetAttrByName("PAS")*0.3 +
			crosser.GetAttrByName("DRI")*0.2
		defendQuality := defender.GetAttrByName("HEA")*0.4 +
			defender.GetAttrByName("DEF")*0.3 +
			defender.GetAttrByName("POS")*0.3
		ctrl := ms.EffectiveControl(zone)
		cornerDelta := crossQuality - defendQuality + ctrl*2.5
		cornerChance := 0.15 + sigmoid(cornerDelta/5.0)*0.45
		if cornerChance < 0.10 {
			cornerChance = 0.10
		}
		if cornerChance > 0.60 {
			cornerChance = 0.60
		}
		if sim.r.Float64() < cornerChance {
			if ms.Possession == domain.SideHome {
				ms.HomeStats.Corners++
			} else {
				ms.AwayStats.Corners++
			}
			// Continue to corner event
			sim.doCornerEvent(ms, possTeam, oppTeam)
			return
		}
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
		crosser.Stats.RatingBase -= 0.03
	} else {
		crosser.Stats.RatingBase += 0.08
		sim.setAssistCandidate(ms, crosser, config.EventCross)
		sim.applyControlShift(ms, [2]int{0, 1}, 0.08)
		sim.boostGlobalMomentum(ms, 0.02)
		crosser.Stats.CrossesSucc++
		crosser.Stats.KeyPasses++
		if possTeam == ms.HomeTeam {
			ms.HomeStats.CrossesSucc++
			ms.HomeStats.KeyPasses++
		} else {
			ms.AwayStats.CrossesSucc++
			ms.AwayStats.KeyPasses++
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventCross,
		Team:         ms.Possession.String(),
		PlayerID:     crosser.PlayerID,
		PlayerName:   crosser.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})

	if success {
		ms.ActiveZone = [2]int{0, 1}
		crossQuality := crosser.GetAttrByName("CRO")*0.5 + crosser.GetAttrByName("PAS")*0.3 + crosser.GetAttrByName("DRI")*0.2
		sim.lastCrossQuality = crossQuality

		if crossingStrategy == 1 {
			// Low cross: ball rolls on the ground to a runner in the box
			receiver := SelectShooterByZone(possTeam, [2]int{0, 1}, "close", sim.r)
			ms.BallHolder = receiver
			sim.setAssistCandidate(ms, crosser, config.EventCross)
			// Ground shot chance based on receiver finishing + cross quality
			shotTendency := receiver.GetAttrByName("FIN")*0.5 +
				receiver.GetAttrByName("SHO")*0.3 +
				crossQuality*0.2
			ctrl := ms.EffectiveControl([2]int{0, 1})
			if ctrl > 0.3 {
				shotTendency += 1.0
			}
			shotChance := 0.10 + sigmoid((shotTendency-12.0)/4.0)*0.30
			if shotChance < 0.10 {
				shotChance = 0.10
			}
			if shotChance > 0.50 {
				shotChance = 0.50
			}
			if sim.r.Float64() < shotChance {
				sim.doShotEvent(ms, possTeam, oppTeam, [2]int{0, 1}, "close")
			} else {
				// Low cross succeeded but no immediate shot: one flick-on pass then must shoot
				flickTarget := SelectPassTarget(possTeam, [2]int{0, 1}, sim.r)
				if flickTarget.PlayerID == receiver.PlayerID {
					players := possTeam.GetActivePlayers()
					for _, p := range players {
						if p.PlayerID != receiver.PlayerID && p.Position != config.PosGK {
							flickTarget = p
							break
						}
					}
				}
				sim.addEvent(ms, domain.MatchEvent{
					Type:        config.EventShortPass,
					Team:        possTeam.Name,
					PlayerID:    receiver.PlayerID,
					PlayerName:  receiver.Name,
					Player2ID:   flickTarget.PlayerID,
					Player2Name: flickTarget.Name,
					Zone:        zoneStr([2]int{0, 1}),
					Result:      "success",
					Detail:      "flick_on",
				})
				ms.BallHolder = flickTarget
				// After the flick-on, next event MUST be a finishing action
				ms.ChainState = "cross_chain"
			}
		} else {
			// High cross / default: header duel
			if !sim.maybeKeeperRush(ms, possTeam, oppTeam, crosser, crossQuality) {
				sim.doHeaderDuel(ms, possTeam, oppTeam)
			}
		}
	}
}

func (sim *Simulator) doHeaderDuel(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime) {
	attacker := SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)
	setSkillContext(attacker, config.EventHeader, [2]int{0, 1}, ms.Minute, ms.Half)
	setSkillContext(defender, config.EventHeader, [2]int{0, 1}, ms.Minute, ms.Half)

	atkVal := CalcHeaderAttack(attacker)
	defVal := CalcHeaderDefense(defender)

	// Cross quality bonus from previous cross
	if sim.lastCrossQuality > 0 {
		atkVal += sim.lastCrossQuality * 0.15
		sim.lastCrossQuality = 0
	}

	// High cross strategy boosts header duel attack value
	if possTeam.Tactics.CrossingStrategy >= 3 {
		atkVal += 0.4
	}

	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(attacker, 1.5)
	ConsumeStamina(defender, 1.5)
	sim.applyWearForAction(attacker, "header")
	sim.applyWearForAction(defender, "header")
	sim.maybeApplyInjury(ms, attacker, "aerial_clash", defender)
	sim.maybeApplyInjury(ms, defender, "aerial_clash", attacker)

	attacker.Stats.Headers++
	defender.Stats.Headers++
	if possTeam == ms.HomeTeam {
		ms.HomeStats.Headers++
		ms.AwayStats.Headers++
		if success {
			ms.HomeStats.HeaderWins++
			attacker.Stats.HeaderWins++
		} else {
			ms.AwayStats.HeaderWins++
			defender.Stats.HeaderWins++
		}
	} else {
		ms.AwayStats.Headers++
		ms.HomeStats.Headers++
		if success {
			ms.AwayStats.HeaderWins++
			attacker.Stats.HeaderWins++
		} else {
			ms.HomeStats.HeaderWins++
			defender.Stats.HeaderWins++
		}
	}

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		sim.applyControlShift(ms, [2]int{0, 1}, 0.07)
		sim.boostGlobalMomentum(ms, 0.02)
	}

	ev := domain.MatchEvent{
		Type:         config.EventHeader,
		Team:         ms.Possession.String(),
		PlayerID:     attacker.PlayerID,
		PlayerName:   attacker.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr([2]int{0, 1}),
		Result:       result,
	}

	if success {
		target := SelectPassTarget(possTeam, [2]int{0, 1}, sim.r, oppTeam)
		if target.PlayerID == attacker.PlayerID {
			players := possTeam.GetActivePlayers()
			for _, p := range players {
				// Skip attacker and GK — GK should not be a pass target in the attacking zone
				if p.PlayerID != attacker.PlayerID && p.Position != config.PosGK {
					target = p
					break
				}
			}
			// If every other player is GK (shouldn't happen), fall back to any non-attacker
			if target.PlayerID == attacker.PlayerID {
				for _, p := range players {
					if p.PlayerID != attacker.PlayerID {
						target = p
						break
					}
				}
			}
		}
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
		// The target receives the header, becoming the new ball holder
		ms.BallHolder = target
	}

	sim.addEvent(ms, ev)

	if success {
		// Dynamic shot chance after header based on attacker's aerial threat + finishing
		shotTendency := attacker.GetAttrByName("HEA")*0.3 +
			attacker.GetAttrByName("SHO")*0.4 +
			attacker.GetAttrByName("FIN")*0.3
		ctrl := ms.EffectiveControl([2]int{0, 1})
		if ctrl > 0.3 {
			shotTendency += 1.0
		}
		shotChance := 0.05 + sigmoid((shotTendency-12.0)/4.0)*0.25
		if shotChance < 0.05 {
			shotChance = 0.05
		}
		if shotChance > 0.45 {
			shotChance = 0.45
		}
		if sim.r.Float64() < shotChance {
			sim.doShotEvent(ms, possTeam, oppTeam, [2]int{0, 1}, "close")
		} else {
			// Header won but no immediate shot: the header itself counts as the one extra pass
			// Next event MUST be a finishing action
			ms.ChainState = "cross_chain"
		}
	}
}

// maybeKeeperRush decides whether the keeper should rush out to intercept a cross/corner.
// Returns true if the keeper handled the situation (success or failure), false to proceed to header duel.
func (sim *Simulator) maybeKeeperRush(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, crosser *domain.PlayerRuntime, crossQuality float64) bool {
	keeper := oppTeam.GetGK()
	attacker := SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
	ctrl := ms.EffectiveControl([2]int{0, 1})

	// Keeper decision value: judgment + execution + reflexes
	rushDecision := keeper.GetAttrByName("DEC")*0.35 + keeper.GetAttrByName("DEC")*0.35 + keeper.GetAttrByName("REF")*0.30

	// Threat level: cross quality + aerial threat + control
	headerThreat := attacker.GetAttrByName("HEA")*0.5 + attacker.GetAttrByName("STR")*0.3 + attacker.GetAttrByName("SPD")*0.2
	threatLevel := crossQuality*0.4 + headerThreat*0.4 + ctrl*3.0

	rushValue := rushDecision - threatLevel*0.4
	threshold := 12.0 + sim.r.Float64()*5.0

	if rushValue > threshold {
		return sim.doKeeperRushEvent(ms, possTeam, oppTeam, keeper, attacker)
	}
	return false
}

// doKeeperRushEvent resolves a keeper rushing out to intercept a cross/corner.
// Returns true if the situation was resolved (no need for header duel).
func (sim *Simulator) doKeeperRushEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, keeper, attacker *domain.PlayerRuntime) bool {
	// Rush duel: keeper execution vs attacker aerial ability
	rushAtk := keeper.GetAttrByName("DEC")*0.5 + keeper.GetAttrByName("REF")*0.3 + keeper.GetAttrByName("SAV")*0.2
	aerialDef := attacker.GetAttrByName("HEA")*0.4 + attacker.GetAttrByName("STR")*0.3 + attacker.GetAttrByName("BAL")*0.3

	com := keeper.GetAttrByName("COM")
	success := ResolveDuel(rushAtk, aerialDef, sim.r, com)

	ConsumeStamina(keeper, 2.0)
	sim.applyWearForAction(keeper, "keeper_dive")
	sim.maybeApplyInjury(ms, keeper, "keeper_dive", attacker)

	if success {
		// Rush success: keeper claims the ball
		keeper.Stats.Saves++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.Saves++
		} else {
			ms.HomeStats.Saves++
		}
		keeper.Stats.RatingBase += 0.4
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)
		return true
	}

	// Rush failure: keeper beaten, attacker gets an excellent close-range chance
	keeper.Stats.RatingBase -= 0.5
	ms.BallHolder = attacker
	// Trigger a close shot with keeper out of position (keeper defense reduced)
	sim.doShotEventWithKeeperOut(ms, possTeam, oppTeam, [2]int{0, 1}, keeper)
	return true
}

// doShotEventWithKeeperOut is a variant of doShotEvent where the keeper is out of position.
func (sim *Simulator) doShotEventWithKeeperOut(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, keeper *domain.PlayerRuntime) {
	shooter := ms.BallHolder
	setSkillContext(shooter, config.EventCloseShot, zone, ms.Minute, ms.Half)
	setSkillContext(keeper, config.EventCloseShot, zone, ms.Minute, ms.Half)

	atkVal := CalcShotAttack(shooter, "close")
	// Keeper is out of position: reduced save ability
	defVal := keeper.GetAttrByName("SAV")*0.2 + keeper.GetAttrByName("REF")*0.3 + 0.5

	com := shooter.GetAttrByName("COM")
	success := ResolveDuel(atkVal, defVal+0.2, sim.r, com)

	ConsumeStamina(shooter, StaminaCost(config.EventCloseShot))
	sim.applyWearForAction(shooter, "shot")
	sim.applyWearForAction(keeper, "keeper_dive")
	sim.maybeApplyInjury(ms, keeper, "keeper_dive", shooter)

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Shots++
	} else {
		ms.AwayStats.Shots++
	}

	shotResult := "missed"
	if success {
		shotResult = "goal"
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.Score.Away++
			ms.AwayStats.ShotsOnTarget++
		}
		shooter.Stats.Goals++
		keeper.Stats.RatingBase -= 0.4
		shooter.Stats.RatingBase += 1.2
		assistMilestones, assister := sim.recordAssist(ms, shooter, possTeam)
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)

		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventCloseShot,
			Team:         ms.Possession.String(),
			PlayerID:     shooter.PlayerID,
			PlayerName:   shooter.Name,
			Player2ID:    playerIDOrEmpty(assister),
			Player2Name:  playerNameOrEmpty(assister),
			OpponentID:   keeper.PlayerID,
			OpponentName: keeper.Name,
			Zone:         zoneStr(zone),
			Result:       shotResult,
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
			Milestones:   mergeMilestones(buildGoalMilestones(shooter, ms.Minute), assistMilestones),
		})
	} else {
		// Out of position keeper still might save it, but less likely
		keeper.Stats.Saves++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.Saves++
		} else {
			ms.HomeStats.Saves++
		}
		keeper.Stats.RatingBase += 0.4
		if ms.Possession == domain.SideHome {
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.AwayStats.ShotsOnTarget++
		}
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)

		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventCloseShot,
			Team:         ms.Possession.String(),
			PlayerID:     shooter.PlayerID,
			PlayerName:   shooter.Name,
			OpponentID:   keeper.PlayerID,
			OpponentName: keeper.Name,
			Zone:         zoneStr(zone),
			Result:       shotResult,
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
	}

	shooter.Stats.Shots++
	if shotResult == "saved" || shotResult == "goal" {
		shooter.Stats.ShotsOnTarget++
	}

	if shotResult == "goal" {
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoal,
			Team:       ms.Possession.String(),
			PlayerID:   shooter.PlayerID,
			PlayerName: shooter.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Celebration event immediately after goal
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoalCelebration,
			Team:       ms.Possession.String(),
			PlayerID:   shooter.PlayerID,
			PlayerName: shooter.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Celebration consumes 20-30 seconds before restart
		ms.AdvanceClock(20.0 + sim.r.Float64()*10.0)
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{1, 1}
		ms.BallHolder = sim.selectKickoffTaker(ms.Team(ms.Possession))
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
			PlayerName:   ms.BallHolder.Name,
		})
	}
}

func (sim *Simulator) doShotEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, distance string) {
	shooter := ms.BallHolder
	if zone[0] <= 1 {
		shooter = SelectShooterByZone(possTeam, zone, distance, sim.r)
		ms.BallHolder = shooter
	}
	keeper := oppTeam.GetGK()
	setSkillContext(keeper, config.EventCloseShot, zone, ms.Minute, ms.Half)
	// Emit shot windup narrative before resolution
	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventShotWindup,
		Team:       ms.Possession.String(),
		PlayerID:   shooter.PlayerID,
		PlayerName: shooter.Name,
		Zone:       zoneStr(zone),
	})

	atkVal := CalcShotAttack(shooter, distance)
	defVal := CalcSaveDefense(keeper, distance)

	// Shooting mentality affects shot quality
	mentality := possTeam.Tactics.ShootingMentality
	if mentality >= 3 {
		atkVal += 0.5
	}

	ctrl := ms.EffectiveControl(zone)

	// === Step 1: Defender block attempt ===
	// The nearest defender tries to block the shot BEFORE it reaches the keeper
	nearestDefender := SelectDefender(oppTeam, zone, sim.r)
	blockAtk := nearestDefender.GetAttrByName("DEF")*0.4 +
		nearestDefender.GetAttrByName("TKL")*0.3 +
		nearestDefender.GetAttrByName("HEA")*0.2 +
		nearestDefender.GetAttrByName("POS")*0.1
	// Zone defensive pressure: backline DEF compresses shooting space
	zoneDefense := 0.0
	zoneDefCount := 0
	for _, p := range oppTeam.GetActivePlayers() {
		if p.Position == config.PosDF || p.Position == config.PosMF {
			zoneDefense += p.GetAttrByName("DEF") * 0.04
			zoneDefCount++
		}
	}
	if zoneDefCount > 0 {
		blockAtk += zoneDefense / float64(zoneDefCount)
	}
	blockDef := shooter.GetAttrByName("SHO")*0.3 +
		shooter.GetAttrByName("ACC")*0.3 +
		shooter.GetAttrByName("FIN")*0.2 +
		shooter.GetAttrByName("STR")*0.2

	// Shooting mentality gives the shooter composure under pressure
	if mentality >= 3 {
		blockDef += 0.8
	} else if mentality >= 2 {
		blockDef += 0.3
	}

	blockDelta := blockAtk - blockDef + ctrl*3.0
	blockChance := sigmoid(blockDelta/5.0) * 0.55

	// Defensive compactness always boosts block chance
	blockChance += float64(oppTeam.Tactics.DefensiveCompactness) * 0.12

	// Deep defense active: +25% shot block chance in own penalty area
	if oppTeam.Tactics.DefensiveLineHeight <= 1 && oppTeam.Tactics.DefensiveCompactness >= 2 {
		if zone[0] >= 2 { // shot taken from deep defense team's penalty area
			blockChance += 0.25
		}
	}

	if blockChance < 0.05 {
		blockChance = 0.05
	}
	if blockChance > 0.50 {
		blockChance = 0.50
	}

	// === Step 2: Is the shot blocked? ===
	blocked := sim.r.Float64() < blockChance

	// === Step 3: If blocked, emit independent shot_block event ===
	if blocked {
		// Emit shot first (with blocked result), then shot_block event, then handle aftermath
		shooter.Stats.Shots++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Shots++
		} else {
			ms.AwayStats.Shots++
		}

		evType := config.EventCloseShot
		if distance == "long" {
			evType = config.EventLongShot
		}
		sim.addEvent(ms, domain.MatchEvent{
			Type:         evType,
			Team:         ms.Possession.String(),
			PlayerID:     shooter.PlayerID,
			PlayerName:   shooter.Name,
			OpponentID:   keeper.PlayerID,
			OpponentName: keeper.Name,
			Zone:         zoneStr(zone),
			Result:       "blocked",
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})

		// Emit independent shot_block event and handle aftermath
		sim.doShotBlockEvent(ms, possTeam, oppTeam, zone, nearestDefender, shooter)
		return
	}

	// === Step 4: On-target check ===
	// Even if not blocked, the shot might miss the goal entirely
	onTargetProb := 0.60 + sigmoid((shooter.GetAttrByName("SHO")+shooter.GetAttrByName("FIN")-20.0)/5.0)*0.20
	if onTargetProb < 0.45 {
		onTargetProb = 0.45
	}
	if onTargetProb > 0.80 {
		onTargetProb = 0.80
	}

	if sim.r.Float64() >= onTargetProb {
		// Shot misses the goal
		ConsumeStamina(shooter, StaminaCost(config.EventCloseShot))

		shooter.Stats.Shots++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Shots++
		} else {
			ms.AwayStats.Shots++
		}

		evType := config.EventCloseShot
		if distance == "long" {
			evType = config.EventLongShot
		}
		sim.addEvent(ms, domain.MatchEvent{
			Type:         evType,
			Team:         ms.Possession.String(),
			PlayerID:     shooter.PlayerID,
			PlayerName:   shooter.Name,
			OpponentID:   keeper.PlayerID,
			OpponentName: keeper.Name,
			Zone:         zoneStr(zone),
			Result:       "missed",
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})

		// Missed shot results in goal kick (keeper gets ball)
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)
		sim.doGoalKickEvent(ms, oppTeam, possTeam, zone)
		return
	}

	// === Step 5: If on target, keeper makes the save ===
	com := shooter.GetAttrByName("COM")
	success := ResolveDuel(atkVal, defVal+2.5, sim.r, com)

	ConsumeStamina(shooter, StaminaCost(config.EventCloseShot))
	sim.applyWearForAction(shooter, "shot")

	// Stats
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Shots++
	} else {
		ms.AwayStats.Shots++
	}

	shotResult := "missed"
	var assistMilestones []string
	var assister *domain.PlayerRuntime
	if success {
		shotResult = "goal"
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.Score.Away++
			ms.AwayStats.ShotsOnTarget++
		}
		shooter.Stats.Goals++
		keeper.Stats.RatingBase -= 0.4
		shooter.Stats.RatingBase += 1.5
		assistMilestones, assister = sim.recordAssist(ms, shooter, possTeam)
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)
	} else {
		// Shot was on target (not blocked) but keeper saved it
		// Determine saved vs woodwork based on keeper quality
		saveQuality := keeper.GetAttrByName("SAV")*0.6 + keeper.GetAttrByName("REF")*0.4
		stability := saveQuality / 20.0
		woodworkChance := (1.0 - stability) * 0.4
		if woodworkChance < 0.05 {
			woodworkChance = 0.05
		}
		if sim.r.Float64() < woodworkChance {
			shotResult = "woodwork"
			if ms.Possession == domain.SideHome {
				ms.HomeStats.ShotsOnTarget++
			} else {
				ms.AwayStats.ShotsOnTarget++
			}
			sim.applyControlShift(ms, zone, 0.03)
			sim.boostGlobalMomentum(ms, 0.01)
		} else {
			shotResult = "saved"
			keeper.Stats.Saves++
			if ms.Possession == domain.SideHome {
				ms.AwayStats.Saves++
			} else {
				ms.HomeStats.Saves++
			}
			keeper.Stats.RatingBase += 0.6
			if ms.Possession == domain.SideHome {
				ms.HomeStats.ShotsOnTarget++
			} else {
				ms.AwayStats.ShotsOnTarget++
			}
			sim.applyControlShift(ms, zone, 0.05)
			sim.boostGlobalMomentum(ms, 0.01)
		}
	}

	shooter.Stats.Shots++
	if shotResult == "saved" || shotResult == "goal" || shotResult == "woodwork" {
		shooter.Stats.ShotsOnTarget++
	}

	evType := config.EventCloseShot
	if distance == "long" {
		evType = config.EventLongShot
	}
	// Emit shot event
	shotEvent := domain.MatchEvent{
		Type:         evType,
		Team:         ms.Possession.String(),
		PlayerID:     shooter.PlayerID,
		PlayerName:   shooter.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       shotResult,
		Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	}
	if shotResult == "goal" {
		shotEvent.Player2ID = playerIDOrEmpty(assister)
		shotEvent.Player2Name = playerNameOrEmpty(assister)
		shotEvent.Milestones = mergeMilestones(buildGoalMilestones(shooter, ms.Minute), assistMilestones)
	}
	sim.addEvent(ms, shotEvent)

	// Chain to specific result events
	if shotResult == "goal" {
		// Independent Goal event
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoal,
			Team:       ms.Possession.String(),
			PlayerID:   shooter.PlayerID,
			PlayerName: shooter.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Celebration event immediately after goal
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoalCelebration,
			Team:       ms.Possession.String(),
			PlayerID:   shooter.PlayerID,
			PlayerName: shooter.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Celebration consumes 20-30 seconds before restart
		ms.AdvanceClock(20.0 + sim.r.Float64()*10.0)
		// Kickoff by conceding team
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{1, 1}
		ms.BallHolder = sim.selectKickoffTaker(ms.Team(ms.Possession))
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
			PlayerName:   ms.BallHolder.Name,
		})
	} else if shotResult == "saved" {
		// Keeper save event
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKeeperSave,
			Team:         oppTeam.Name,
			PlayerID:     keeper.PlayerID,
			PlayerName:   keeper.Name,
			OpponentID:   shooter.PlayerID,
			OpponentName: shooter.Name,
		})

		// Keeper spill chance (rebound opportunity)
		spillChance := 0.12
		keeperRef := keeper.GetAttrByName("REF")
		if keeperRef < 10 {
			spillChance += 0.10
		} else if keeperRef < 15 {
			spillChance += 0.05
		}
		if sim.r.Float64() < spillChance {
			// Keeper spills the ball!
			sim.addEvent(ms, domain.MatchEvent{
				Type:       config.EventKeeperClaim,
				Team:       oppTeam.Name,
				PlayerID:   keeper.PlayerID,
				PlayerName: keeper.Name,
				Result:     "spill",
			})
			rebounder := SelectReboundAttacker(possTeam, zone, sim.r)
			setSkillContext(rebounder, config.EventCloseShot, [2]int{0, 1}, ms.Minute, ms.Half)
			ms.BallHolder = rebounder
			ms.ActiveZone = [2]int{0, 1}
			sim.doShotEvent(ms, possTeam, oppTeam, [2]int{0, 1}, "close")
			return
		}

		// Keeper claims ball
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventKeeperClaim,
			Team:       oppTeam.Name,
			PlayerID:   keeper.PlayerID,
			PlayerName: keeper.Name,
		})
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper // goalkeeper holds the ball after save
	} else {
		// Missed or blocked — keeper gets ball or goal kick
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventKeeperClaim,
			Team:       oppTeam.Name,
			PlayerID:   keeper.PlayerID,
			PlayerName: keeper.Name,
		})
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper // goalkeeper holds the ball after claim
	}
}

func (sim *Simulator) doTackleEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	// Tackle: defending team tries to win ball from possession team
	tackler := SelectTackler(oppTeam, zone, sim.r)
	setSkillContext(tackler, config.EventTackle, zone, ms.Minute, ms.Half)
	holder := ms.BallHolder

	atkVal := CalcTackleAttack(tackler)
	defVal := CalcTackleDefense(holder)
	// Boost tackle success to make defense more effective
	atkVal += 1.2
	switch zone[0] {
	case 0: // defending team's back line
		atkVal += 0.45
	case 1: // midfield challenges are less decisive
		atkVal -= 0.45
	}
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeDefensiveStamina(tackler, config.EventTackle)
	ConsumeStamina(holder, StaminaCost(config.EventTackle)*0.5)

	result := "success"
	if success {
		ms.Possession = ms.Possession.Opponent()
		sim.clearAssistCandidate(ms)
		ms.ActiveZone = zone
		ms.BallHolder = tackler
		tackler.Stats.Tackles++
		tackler.Stats.TacklesSucc++
		tackler.Stats.RatingBase += 0.15
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Tackles++
			ms.HomeStats.TacklesSucc++
		} else {
			ms.AwayStats.Tackles++
			ms.AwayStats.TacklesSucc++
		}
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.03)
		// Grant counter-attack boost for next 2 events
		if ms.Possession == domain.SideHome {
			ms.CounterBoostRemaining[0] = 2
		} else {
			ms.CounterBoostRemaining[1] = 2
		}
	} else {
		result = "fail"
		tackler.Stats.Tackles++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.Tackles++
		} else {
			ms.HomeStats.Tackles++
		}
		holder.Stats.RatingBase += 0.05
		sim.applyControlShift(ms, zone, 0.03)
		sim.boostGlobalMomentum(ms, 0.01)
	}

	// === Wear accumulation from tackle ===
	wearMult := GetStaminaWearMultiplier(holder.CurrentStamina)
	ApplyMatchWear(holder, "tackle", wearMult)
	ApplyMatchWear(tackler, "tackle", wearMult)

	// === Injury check from hard tackle (new wear-driven system) ===
	if holder.MatchInjury == nil && success {
		tackleIntensity := tackler.GetAttrByName("TKL")*0.5 + tackler.GetAttrByName("STR")*0.3
		action := "brutal_tackle"
		if tackleIntensity <= 14 {
			action = "tackle" // use brutal_tackle only for intensity > 14
		}
		if tackleIntensity > 12 {
			occurred, part, severity := CheckInjury(sim.r, holder, action)
			if occurred {
				sim.applyInjury(ms, holder, part, severity, tackler)
			}
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventTackle,
		Team:         oppTeam.Name, // defending team
		PlayerID:     tackler.PlayerID,
		PlayerName:   tackler.Name,
		OpponentID:   holder.PlayerID,
		OpponentName: holder.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

func (sim *Simulator) doInterceptEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	interceptor := SelectInterceptor(oppTeam, zone, sim.r)
	setSkillContext(interceptor, config.EventIntercept, zone, ms.Minute, ms.Half)
	passer := ms.BallHolder

	ConsumeDefensiveStamina(interceptor, config.EventIntercept)

	atkVal := CalcInterceptAttack(interceptor)
	defVal := CalcInterceptDefense(passer)
	switch zone[0] {
	case 0: // defensive third: defenders read dangerous passing lanes better
		atkVal += 1.20
	case 1: // midfield interceptions should not stop most progression
		atkVal -= 0.40
	case 2: // high pressing interceptions are possible but less reliable
		atkVal -= 0.60
	}
	success := ResolveDuel(atkVal, defVal, sim.r, interceptor.GetAttrByName("COM"))

	result := "fail"
	if success {
		result = "success"
		ms.Possession = ms.Possession.Opponent()
		sim.clearAssistCandidate(ms)
		ms.ActiveZone = zone
		ms.BallHolder = interceptor
		interceptor.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		interceptor.Stats.RatingBase += 0.12
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.12)
		sim.boostGlobalMomentum(ms, 0.02)
		// Grant counter-attack boost for next 2 events
		if ms.Possession == domain.SideHome {
			ms.CounterBoostRemaining[0] = 2
		} else {
			ms.CounterBoostRemaining[1] = 2
		}
	} else {
		passer.Stats.RatingBase += 0.03
		sim.applyControlShift(ms, zone, 0.04)
		sim.boostGlobalMomentum(ms, 0.01)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventIntercept,
		Team:         ms.Possession.String(),
		PlayerID:     interceptor.PlayerID,
		PlayerName:   interceptor.Name,
		OpponentID:   passer.PlayerID,
		OpponentName: passer.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

func (sim *Simulator) decayGlobalMomentum(ms *domain.MatchState) {
	ms.GlobalMomentum *= 0.70
	if ms.GlobalMomentum < 0.01 && ms.GlobalMomentum > -0.01 {
		ms.GlobalMomentum = 0
	}
}

func (sim *Simulator) boostGlobalMomentum(ms *domain.MatchState, amount float64) {
	ms.GlobalMomentum += amount
	if ms.GlobalMomentum > 0.3 {
		ms.GlobalMomentum = 0.3
	} else if ms.GlobalMomentum < -0.3 {
		ms.GlobalMomentum = -0.3
	}
}

func (sim *Simulator) flipGlobalMomentum(ms *domain.MatchState) {
	ms.GlobalMomentum *= -0.5
}

// selectKickoffTaker chooses a central midfielder or striker for kickoff
func (sim *Simulator) selectKickoffTaker(team *domain.TeamRuntime) *domain.PlayerRuntime {
	// Prefer MF for kickoff
	for _, p := range team.PlayerRuntimes {
		if p.Position == config.PosMF {
			return p
		}
	}
	for _, p := range team.PlayerRuntimes {
		if p.Position == config.PosFW {
			return p
		}
	}
	// Fallback: any outfield player
	for _, p := range team.PlayerRuntimes {
		if p.Position != config.PosGK {
			return p
		}
	}
	return team.PlayerRuntimes[0]
}

// flipControlShiftOnTurnover inverts the control shift in the given zone
// when possession changes hands. The old advantage becomes disadvantage.
func (sim *Simulator) flipControlShiftOnTurnover(ms *domain.MatchState, zone [2]int) {
	ms.ControlShift[zone[0]][zone[1]] *= -0.5
	if ms.ControlShift[zone[0]][zone[1]] < 0.005 && ms.ControlShift[zone[0]][zone[1]] > -0.005 {
		ms.ControlShift[zone[0]][zone[1]] = 0
	}
}

// applyControlShift adds an event-driven offset to ControlShift.
// amount is from the possession team's perspective (positive = possession team advantage).
// ControlShift is stored in absolute reference (positive = home advantage), so the
// sign is flipped when the away team is in possession.
func (sim *Simulator) applyControlShift(ms *domain.MatchState, zone [2]int, amount float64) {
	actualAmount := amount
	if ms.Possession == domain.SideAway {
		actualAmount = -amount
	}
	ms.ControlShift[zone[0]][zone[1]] += actualAmount + (sim.r.Float64()*0.04 - 0.02)
	if ms.ControlShift[zone[0]][zone[1]] > 0.5 {
		ms.ControlShift[zone[0]][zone[1]] = 0.5
	} else if ms.ControlShift[zone[0]][zone[1]] < -0.5 {
		ms.ControlShift[zone[0]][zone[1]] = -0.5
	}
}

func (sim *Simulator) applyCounterBoost(ms *domain.MatchState, side domain.Side) {
	idx := 0
	if side == domain.SideAway {
		idx = 1
	}
	ms.CounterBoostRemaining[idx] = 3
	// Counter boost gives a modest global momentum bump
	sim.boostGlobalMomentum(ms, 0.12)
}

// applyTransitionInstructions applies V2 transition instructions after a turnover.
// possBefore is the side that just lost possession.
func (sim *Simulator) applyTransitionInstructions(ms *domain.MatchState, possBefore domain.Side, zone [2]int) {
	newSide := ms.Possession
	lostSide := possBefore
	newTeam := ms.Team(newSide)
	lostTeam := ms.Team(lostSide)

	// After possession won
	switch newTeam.Instructions().Transition.AfterPossessionWon {
	case "counter":
		sim.applyCounterBoost(ms, newSide)
		// Higher counter_directness extends the boost duration
		directness := newTeam.Instructions().Transition.CounterDirectness
		extra := directness / 2
		idx := int(newSide)
		ms.CounterBoostRemaining[idx] += extra
	case "hold_shape":
		// Reset tempo: drop the ball to a safer zone if currently advanced
		if zone[0] <= 1 && sim.r.Float64() < 0.5 {
			if ms.ActiveZone[0] < 2 {
				ms.ActiveZone[0]++
			}
		}
	}

	// After possession lost
	switch lostTeam.Instructions().Transition.AfterPossessionLost {
	case "counter_press":
		// Lost ball in opponent half -> attempt immediate press
		if zone[0] <= 1 {
			pressIntensity := lostTeam.Instructions().OutOfPossession.PressingIntensity
			if sim.r.Float64() < 0.15+float64(pressIntensity)*0.05 {
				sim.applyControlShift(ms, zone, 0.08)
				sim.boostGlobalMomentum(ms, 0.02)
			}
		}
	case "regroup":
		// Recover defensive shape: bolster back-zone control
		backZone := [2]int{2, 1}
		if lostSide == domain.SideHome {
			sim.applyControlShift(ms, backZone, 0.06)
		} else {
			sim.applyControlShift(ms, backZone, -0.06)
		}
	}
}

func isDeadBallEvent(evType string) bool {
	switch evType {
	case config.EventGoal, config.EventHalftime, config.EventFulltime,
		config.EventFoul, config.EventGoalKick, config.EventCorner,
		config.EventThrowIn, config.EventDropBall, config.EventKickoff,
		config.EventKeeperClaim, config.EventKeeperSave,
		config.EventFreeKickSetup, config.EventGoalKickSetup,
		config.EventCornerSetup, config.EventPenaltySetup,
		config.EventSubstitution:
		return true
	}
	return false
}

func (sim *Simulator) checkSubstitutions(ms *domain.MatchState) {
	// Substitution windows: 30', 35', 40' (game minute)
	windows := []float64{30.0, 35.0, 40.0}
	for _, window := range windows {
		for _, team := range []*domain.TeamRuntime{ms.HomeTeam, ms.AwayTeam} {
			if len(team.BenchRuntimes) == 0 {
				continue
			}
			// Check if we already subbed near this window
			alreadySubbed := false
			for _, ev := range ms.Events {
				if ev.Type == config.EventSubstitution && ev.Team == team.Name {
					if ev.Minute >= window-1.0 && ev.Minute <= window+1.0 {
						alreadySubbed = true
						break
					}
				}
			}
			if alreadySubbed {
				continue
			}
			if ms.Minute >= window && ms.Minute < window+1.0 {
				// Substitution likelihood based on team stamina state
				// More tired players = higher chance to sub
				tiredCount := 0
				for _, p := range team.PlayerRuntimes {
					if p.Position != "GK" && !p.RedCard && !p.Substituted && p.CurrentStamina < 60 {
						tiredCount++
					}
				}
				subChance := 0.2 + float64(tiredCount)*0.15
				if subChance > 0.8 {
					subChance = 0.8
				}
				if sim.r.Float64() < subChance {
					sim.doSubstitution(ms, team)
				}
			}
		}
	}
}

func (sim *Simulator) doSubstitution(ms *domain.MatchState, team *domain.TeamRuntime) {
	// Find most tired on-field player (non-GK, not carded)
	var tiredPlayer *domain.PlayerRuntime
	minStamina := 999.0
	for _, p := range team.PlayerRuntimes {
		if p.Position == "GK" || p.RedCard || p.Substituted {
			continue
		}
		if p.CurrentStamina < minStamina {
			minStamina = p.CurrentStamina
			tiredPlayer = p
		}
	}
	if tiredPlayer == nil || minStamina > 75 {
		return // no one tired enough
	}

	// Find best bench player (prefer same position, then any)
	var subPlayer *domain.PlayerRuntime
	for _, p := range team.BenchRuntimes {
		if p.Substituted && !p.RedCard {
			if subPlayer == nil || p.Position == tiredPlayer.Position {
				subPlayer = p
				if p.Position == tiredPlayer.Position {
					break
				}
			}
		}
	}
	if subPlayer == nil {
		return
	}

	// Perform swap
	tiredPlayer.Substituted = true
	subPlayer.Substituted = false

	// Add bench player to PlayerRuntimes and keep tired on bench
	team.PlayerRuntimes = append(team.PlayerRuntimes, subPlayer)
	// Note: tiredPlayer stays in PlayerRuntimes for stat tracking but is marked substituted

	sim.addEvent(ms, domain.MatchEvent{
		Type:        config.EventSubstitution,
		Team:        team.Name,
		PlayerID:    subPlayer.PlayerID,
		PlayerName:  subPlayer.Name,
		Player2ID:   tiredPlayer.PlayerID,
		Player2Name: tiredPlayer.Name,
		Result:      "success",
	})
}

func (sim *Simulator) doClearanceEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	// Clearance: defending team clears the ball under pressure in their own final third.
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventClearance, zone, ms.Minute, ms.Half)
	ConsumeDefensiveStamina(defender, config.EventClearance)

	defender.Stats.Clearances++
	defender.Stats.RatingBase += 0.1
	if defender.Position == "GK" {
		defender.Stats.RatingBase += 0.1
	}

	// Dynamic own goal chance based on defender composure, decision making, pressure, and stamina
	clearanceQuality := defender.GetAttrByName("COM")*0.3 +
		defender.GetAttrByName("DEC")*0.3 +
		defender.GetAttrByName("PAS")*0.2 +
		defender.GetAttrByName("DEF")*0.2

	pressureFactor := 0.0
	ctrl := ms.EffectiveControl(zone)
	if ctrl < 0 {
		pressureFactor = -ctrl * 2.0
	}

	staminaPenalty := 0.0
	if defender.CurrentStamina < 30 {
		staminaPenalty = 3.0
	}

	ownGoalDelta := clearanceQuality - 15.0 - pressureFactor - staminaPenalty
	ownGoalChance := 0.001 + sigmoid(-ownGoalDelta/3.0)*0.03
	if ownGoalChance < 0.001 {
		ownGoalChance = 0.001
	}
	if ownGoalChance > 0.035 {
		ownGoalChance = 0.035
	}
	if sim.r.Float64() < ownGoalChance {
		// Own goal!
		if ms.Possession == domain.SideHome {
			ms.Score.Away++
		} else {
			ms.Score.Home++
		}
		defender.Stats.OwnGoals++
		defender.Stats.RatingBase -= 1.5
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventOwnGoal,
			Team:       oppTeam.Name,
			PlayerID:   defender.PlayerID,
			PlayerName: defender.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Kickoff by scoring team (original possession team)
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{1, 1}
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
		})
		return
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventClearance,
		Team:       oppTeam.Name,
		PlayerID:   defender.PlayerID,
		PlayerName: defender.Name,
		Zone:       zoneStr(zone),
		Result:     "success",
	})

	// The clearing side is the defending team (opposite of current possession).
	if ms.Possession == domain.SideHome {
		ms.AwayStats.Clearances++
	} else {
		ms.HomeStats.Clearances++
	}
	sim.flipGlobalMomentum(ms)
	sim.boostGlobalMomentum(ms, 0.01)

	// Determine where the cleared ball goes
	r := sim.r.Float64()
	if r < 0.50 {
		// Ball goes out over the goal line → corner kick for the clearing team
		// (since they cleared from front zone toward opponent's goal line)
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{0, 1}
		ms.BallHolder = SelectPlayerByZone(ms.Team(ms.Possession), [2]int{0, 1}, sim.r)
		sim.doCornerEvent(ms, ms.Team(ms.Possession), ms.OppTeam(ms.Possession))
	} else if r < 0.75 {
		// Ball goes out over the side line → throw-in by opponent
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = SelectPlayerByZone(ms.Team(ms.Possession), zone, sim.r)
		sim.doThrowInEvent(ms, ms.Team(ms.Possession), ms.OppTeam(ms.Possession), zone)
	} else {
		// Ball recovered by opponent in back zone
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = SelectPlayerByZone(ms.Team(ms.Possession), [2]int{2, 1}, sim.r)
		sim.applyControlShift(ms, [2]int{2, 1}, 0.05)
	}
}

func (sim *Simulator) doFoulEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	// Determine fouler (from defending team) and victim
	// GK can only foul in their own box (when attack is in front zone)
	var fouler *domain.PlayerRuntime
	for attempts := 0; attempts < 8; attempts++ {
		candidate := SelectDefender(oppTeam, zone, sim.r)
		if candidate.Position != "GK" || zone[0] == 0 {
			fouler = candidate
			break
		}
	}
	setSkillContext(fouler, config.EventFoul, zone, ms.Minute, ms.Half)
	if fouler == nil {
		fouler = SelectDefender(oppTeam, zone, sim.r)
	}
	victim := SelectPlayerByZone(possTeam, zone, sim.r)

	ConsumeStamina(fouler, 1.5)

	fouler.Stats.Fouls++
	if ms.Possession == domain.SideHome {
		ms.AwayStats.Fouls++
	} else {
		ms.HomeStats.Fouls++
	}
	victim.Stats.FoulsDrawn++
	if possTeam == ms.HomeTeam {
		ms.HomeStats.FoulsDrawn++
	} else {
		ms.AwayStats.FoulsDrawn++
	}
	fouler.Stats.RatingBase -= 0.15

	// === Dynamic card check based on foul severity ===
	cardResult := ""

	// Severity factors
	foulSeverity := fouler.GetAttrByName("TKL")*0.3 + fouler.GetAttrByName("STR")*0.3 - fouler.GetAttrByName("DEC")*0.15
	// Higher aggression tactic = more dangerous tackles
	aggressionBonus := float64(oppTeam.Tactics.TacklingAggression) * 2.0

	// Context: fouls in attacking zone are more dangerous (break up attacks)
	victimContext := 0.0
	if zone[0] == 0 {
		victimContext = 3.0 // front zone: likely stopped a shot/dribble
	} else if zone[0] == 1 {
		victimContext = 1.5 // mid zone: stopped a through ball
	}

	// Card history: already carded players get closer to second yellow
	cardHistory := float64(fouler.YellowCards) * 2.0

	severityScore := foulSeverity + aggressionBonus + victimContext - cardHistory

	// Dynamic thresholds with randomness
	yellowThreshold := 10.0 + sim.r.Float64()*4.0
	redThreshold := 16.0 + sim.r.Float64()*3.0

	yellowJustIssued := false

	if !fouler.RedCard && severityScore > redThreshold {
		fouler.RedCard = true
		fouler.Stats.RedCards++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.RedCards++
		} else {
			ms.HomeStats.RedCards++
		}
		cardResult = "red"
		fouler.Stats.RatingBase -= 2.0
	} else if !fouler.RedCard && fouler.YellowCards < 2 && severityScore > yellowThreshold {
		fouler.YellowCards++
		fouler.Stats.YellowCards++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.YellowCards++
		} else {
			ms.HomeStats.YellowCards++
		}
		cardResult = "yellow"
		yellowJustIssued = true
		fouler.Stats.RatingBase -= 0.5
		if fouler.YellowCards >= 2 {
			fouler.RedCard = true
			fouler.Stats.RedCards++
			if ms.Possession == domain.SideHome {
				ms.AwayStats.RedCards++
			} else {
				ms.HomeStats.RedCards++
			}
			cardResult = "red"
			fouler.Stats.RatingBase -= 2.0
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventFoul,
		Team:         oppTeam.Name,
		PlayerID:     fouler.PlayerID,
		PlayerName:   fouler.Name,
		OpponentID:   victim.PlayerID,
		OpponentName: victim.Name,
		Zone:         zoneStr(zone),
		Result:       cardResult,
	})

	if yellowJustIssued {
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventYellowCard,
			Team:       oppTeam.Name,
			PlayerID:   fouler.PlayerID,
			PlayerName: fouler.Name,
		})
	}
	if cardResult == "red" {
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventRedCard,
			Team:       oppTeam.Name,
			PlayerID:   fouler.PlayerID,
			PlayerName: fouler.Name,
		})
	}

	// === Wear accumulation from foul ===
	wearMult := GetStaminaWearMultiplier(victim.CurrentStamina)
	ApplyMatchWear(victim, "tackle", wearMult)

	// === Injury check (new wear-driven system) ===
	if victim.MatchInjury == nil {
		action := "dangerous_foul"
		if cardResult != "red" && severityScore <= yellowThreshold {
			action = "" // only check for dangerous fouls
		}
		if action != "" {
			occurred, part, severity := CheckInjury(sim.r, victim, action)
			if occurred {
				sim.applyInjury(ms, victim, part, severity, fouler)
			}
		}
	}

	// Foul disrupts attacking momentum
	foulShift := 0.03
	if cardResult == "yellow" || cardResult == "red" {
		foulShift = 0.06
	}
	sim.applyControlShift(ms, zone, foulShift)
	sim.boostGlobalMomentum(ms, 0.01)

	// === Referee discretion ===
	// Penalty area fouls are often not called (dive, minor contact, blocked view)
	isPenaltyArea := zone[0] == 0 && zone[1] == 1
	if isPenaltyArea {
		callChance := 0.25
		if cardResult == "yellow" || cardResult == "red" {
			callChance = 0.50 // obvious/dangerous fouls more likely to be called
		}
		if sim.r.Float64() > callChance {
			// No call — play continues, attacking team keeps possession
			sim.addEvent(ms, domain.MatchEvent{
				Type:         config.EventFoul,
				Team:         oppTeam.Name,
				PlayerID:     fouler.PlayerID,
				PlayerName:   fouler.Name,
				OpponentID:   victim.PlayerID,
				OpponentName: victim.Name,
				Zone:         zoneStr(zone),
				Result:       "no_call",
			})
			return
		}
	}

	// After foul, trigger free kick / penalty
	sim.doFreeKickEvent(ms, possTeam, oppTeam, zone)
}

func (sim *Simulator) handleHalftime(ms *domain.MatchState) {
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventHalftime,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})
	// Mid-break event
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventMidBreak,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})
	ms.Half = 2
	ms.Minute = 25.0
	// Generate stoppage time: 1-3 minutes
	ms.AddedTime = 1.0 + sim.r.Float64()*2.0
	HalftimeRecovery(ms)
	// Halftime is a dead ball — check substitutions
	sim.checkSubstitutions(ms)
	ms.Possession = domain.SideAway // away team kicks off 2nd half
	ms.ActiveZone = [2]int{1, 1}
	ms.BallHolder = sim.selectKickoffTaker(ms.AwayTeam)
	// Second half start
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventSecondHalfStart,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})
	// 2nd half kickoff
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.AwayTeam.Name,
		OpponentName: ms.HomeTeam.Name,
		PlayerName:   ms.BallHolder.Name,
	})
}

func (sim *Simulator) doFreeKickEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	resetControlShift(ms)
	taker := SelectPlayerByZone(possTeam, zone, sim.r)
	setSkillContext(taker, config.EventFreeKick, zone, ms.Minute, ms.Half)

	// Penalty: skip free kick setup, go straight to penalty drama
	isPenalty := zone[0] == 0 && zone[1] == 1
	if !isPenalty {
		// Setup phase: placing ball, wall positioning
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventFreeKickSetup,
			Team:       ms.Possession.String(),
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Zone:       zoneStr(zone),
		})
		ms.AdvanceClock(3.0 + sim.r.Float64()*2.0)
		// Taker preparation / focus phase
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventFreeKickFocus,
			Team:       possTeam.Name,
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Zone:       zoneStr(zone),
		})
		ms.AdvanceClock(2.0 + sim.r.Float64()*2.0)
	}

	ConsumeStamina(taker, StaminaCost(config.EventFreeKick))

	if ms.Possession == domain.SideHome {
		ms.HomeStats.FreeKicks++
	} else {
		ms.AwayStats.FreeKicks++
	}
	taker.Stats.FreeKicks++

	ctrl := ms.EffectiveControl(zone)

	switch {
	case isPenalty:
		// Penalty kick — multi-step drama for narrative tension
		keeper := oppTeam.GetGK()
		// Step 1: referee points to the spot
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventPenaltySetup,
			Team:         possTeam.Name,
			PlayerID:     taker.PlayerID,
			PlayerName:   taker.Name,
			OpponentID:   keeper.PlayerID,
			OpponentName: keeper.Name,
			Zone:         zoneStr(zone),
		})
		ms.AdvanceClock(2.0 + sim.r.Float64()*2.0)
		// Step 2: taker walks up, keeper tries to distract
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventPenaltyFocus,
			Team:         possTeam.Name,
			PlayerID:     taker.PlayerID,
			PlayerName:   taker.Name,
			OpponentID:   keeper.PlayerID,
			OpponentName: keeper.Name,
			Zone:         zoneStr(zone),
		})
		ms.AdvanceClock(3.0 + sim.r.Float64()*2.0)
		// Step 3: run-up
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventShotWindup,
			Team:       possTeam.Name,
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Zone:       zoneStr(zone),
		})
		ms.AdvanceClock(1.0 + sim.r.Float64()*1.0)
		// Step 4: the kick
		sim.doPenaltyKick(ms, possTeam, oppTeam, zone, taker, ctrl)
	case zone[0] == 0 && zone[1] == 1:
		// Front center free kick → 50% shot, 50% pass
		if sim.r.Float64() < 0.5 {
			sim.doFreeKickShot(ms, possTeam, oppTeam, zone, taker, ctrl)
		} else {
			sim.doFreeKickPass(ms, possTeam, oppTeam, zone, taker, ctrl, config.EventShortPass)
		}
	case zone[0] == 0 && (zone[1] == 0 || zone[1] == 2):
		// Front wing free kick → 30% shot, 70% cross
		if sim.r.Float64() < 0.3 {
			sim.doFreeKickShot(ms, possTeam, oppTeam, zone, taker, ctrl)
		} else {
			sim.doFreeKickCross(ms, possTeam, oppTeam, zone, taker, ctrl)
		}
	case zone[0] == 1 && zone[1] == 1:
		// Mid center free kick → 30% shot, 70% pass
		if sim.r.Float64() < 0.3 {
			sim.doFreeKickShot(ms, possTeam, oppTeam, zone, taker, ctrl)
		} else {
			sim.doFreeKickPass(ms, possTeam, oppTeam, zone, taker, ctrl, config.EventShortPass)
		}
	case zone[0] == 1 && (zone[1] == 0 || zone[1] == 2):
		// Mid wing free kick → long pass
		sim.doFreeKickPass(ms, possTeam, oppTeam, zone, taker, ctrl, config.EventLongPass)
	default:
		// Back zone free kick → short pass
		sim.doFreeKickPass(ms, possTeam, oppTeam, zone, taker, ctrl, config.EventShortPass)
	}
}

func (sim *Simulator) doPenaltyKick(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, taker *domain.PlayerRuntime, ctrl float64) {
	keeper := oppTeam.GetGK()
	setSkillContext(taker, config.EventPenalty, zone, ms.Minute, ms.Half)
	setSkillContext(keeper, config.EventPenalty, zone, ms.Minute, ms.Half)
	com := taker.GetAttrByName("COM")

	atkVal := taker.GetAttrByName("SET")*0.60 +
		taker.GetAttrByName("SHO")*0.30 +
		taker.GetAttrByName("FIN")*0.10 +
		4.3
	defVal := keeper.GetAttrByName("SAV")*0.30 +
		keeper.GetAttrByName("REF")*0.20 +
		keeper.GetAttrByName("POS")*0.15 -
		1.3
	defVal = applySkillDefense(keeper, defVal)

	success := ResolveDuel(atkVal, defVal, sim.r, com)

	result := "goal"
	if !success {
		result = "saved"
		if sim.r.Float64() < 0.05 {
			result = "fail"
		}
	}

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Penalties++
		ms.HomeStats.Shots++
	} else {
		ms.AwayStats.Penalties++
		ms.AwayStats.Shots++
	}
	taker.Stats.Penalties++
	taker.Stats.Shots++

	if result == "goal" {
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.PenaltyGoals++
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.Score.Away++
			ms.AwayStats.PenaltyGoals++
			ms.AwayStats.ShotsOnTarget++
		}
		taker.Stats.PenaltyGoals++
		taker.Stats.Goals++
		taker.Stats.ShotsOnTarget++
		taker.Stats.RatingBase += 1.5
		keeper.Stats.RatingBase -= 0.4
		ms.BallHolder = taker
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)
	} else if result == "saved" {
		keeper.Stats.Saves++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.Saves++
		} else {
			ms.HomeStats.Saves++
		}
		keeper.Stats.RatingBase += 0.4
		if ms.Possession == domain.SideHome {
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.AwayStats.ShotsOnTarget++
		}
		taker.Stats.ShotsOnTarget++
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)
	} else {
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)
	}

	penaltyEvent := domain.MatchEvent{
		Type:         config.EventFreeKick,
		Team:         ms.Possession.String(),
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       "penalty",
	}
	if result == "goal" {
		penaltyEvent.Milestones = buildGoalMilestones(taker, ms.Minute)
	}
	sim.addEvent(ms, penaltyEvent)

	if result == "goal" {
		// Goal event
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoal,
			Team:       ms.Possession.String(),
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Celebration
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoalCelebration,
			Team:       ms.Possession.String(),
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		ms.AdvanceClock(20.0 + sim.r.Float64()*10.0)
		// Kickoff
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{1, 1}
		ms.BallHolder = sim.selectKickoffTaker(ms.Team(ms.Possession))
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
			PlayerName:   ms.BallHolder.Name,
		})
	}
}

func (sim *Simulator) doFreeKickCross(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, taker *domain.PlayerRuntime, ctrl float64) {
	defender := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(defender, config.EventFreeKick, zone, ms.Minute, ms.Half)
	com := taker.GetAttrByName("COM")

	atkVal := taker.GetAttrByName("SET")*0.55 +
		taker.GetAttrByName("CRO")*0.25 +
		taker.GetAttrByName("PAS")*0.20
	defVal := defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("HEA")*0.3

	success := ResolveDuel(atkVal, defVal, sim.r, com)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		sim.applyControlShift(ms, [2]int{0, 1}, 0.08)
		sim.boostGlobalMomentum(ms, 0.02)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventFreeKick,
		Team:         ms.Possession.String(),
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       "cross",
	})

	if success {
		ms.ActiveZone = [2]int{0, 1}
		sim.doHeaderDuel(ms, possTeam, oppTeam)
	}
}

func (sim *Simulator) doFreeKickShot(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, taker *domain.PlayerRuntime, ctrl float64) {
	keeper := oppTeam.GetGK()
	setSkillContext(keeper, config.EventFreeKick, zone, ms.Minute, ms.Half)
	com := taker.GetAttrByName("COM")

	// Wall defense: fixed obstacle reduces shot quality
	wallDef := 2.5
	atkVal := taker.GetAttrByName("SET")*0.50 +
		taker.GetAttrByName("SHO")*0.25 +
		taker.GetAttrByName("FIN")*0.15 +
		1.5
	defVal := keeper.GetAttrByName("SAV")*0.30 +
		keeper.GetAttrByName("REF")*0.20 +
		keeper.GetAttrByName("POS")*0.10 +
		wallDef

	success := ResolveDuel(atkVal, defVal, sim.r, com)

	result := "goal"
	if !success {
		result = "saved"
		if sim.r.Float64() < 0.15 {
			result = "fail"
		}
	}

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Shots++
	} else {
		ms.AwayStats.Shots++
	}
	taker.Stats.Shots++

	if result == "goal" {
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.FreeKickGoals++
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.Score.Away++
			ms.AwayStats.FreeKickGoals++
			ms.AwayStats.ShotsOnTarget++
		}
		taker.Stats.FreeKickGoals++
		taker.Stats.Goals++
		taker.Stats.ShotsOnTarget++
		taker.Stats.RatingBase += 1.5
		keeper.Stats.RatingBase -= 0.4
		ms.BallHolder = taker
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)
	} else if result == "saved" {
		keeper.Stats.Saves++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.Saves++
		} else {
			ms.HomeStats.Saves++
		}
		keeper.Stats.RatingBase += 0.4
		if ms.Possession == domain.SideHome {
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.AwayStats.ShotsOnTarget++
		}
		taker.Stats.ShotsOnTarget++
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)
	} else {
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
		sim.flipGlobalMomentum(ms)
	}

	freeKickEvent := domain.MatchEvent{
		Type:         config.EventFreeKick,
		Team:         ms.Possession.String(),
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       "shot",
	}
	if result == "goal" {
		freeKickEvent.Milestones = buildGoalMilestones(taker, ms.Minute)
	}
	sim.addEvent(ms, freeKickEvent)

	if result == "goal" {
		// Goal event
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoal,
			Team:       ms.Possession.String(),
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		// Celebration
		sim.addEvent(ms, domain.MatchEvent{
			Type:       config.EventGoalCelebration,
			Team:       ms.Possession.String(),
			PlayerID:   taker.PlayerID,
			PlayerName: taker.Name,
			Score:      &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		ms.AdvanceClock(20.0 + sim.r.Float64()*10.0)
		// Kickoff
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{1, 1}
		ms.BallHolder = sim.selectKickoffTaker(ms.Team(ms.Possession))
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
			PlayerName:   ms.BallHolder.Name,
		})
	}
}

func (sim *Simulator) doFreeKickPass(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, taker *domain.PlayerRuntime, ctrl float64, passType string) {
	target := SelectPassTarget(possTeam, zone, sim.r)
	pressure := SelectDefender(oppTeam, zone, sim.r)
	setSkillContext(pressure, config.EventFreeKick, zone, ms.Minute, ms.Half)
	com := taker.GetAttrByName("COM")

	var atkVal, defVal float64
	if passType == config.EventLongPass {
		atkVal = taker.GetAttrByName("PAS")*0.5 +
			taker.GetAttrByName("VIS")*0.3 +
			taker.GetAttrByName("CON")*0.2 +
			0.3
		defVal = pressure.GetAttrByName("DEF")*0.5 +
			pressure.GetAttrByName("SPD")*0.3 +
			pressure.GetAttrByName("POS")*0.2 +
			0.5
	} else {
		atkVal = taker.GetAttrByName("PAS")*0.5 +
			taker.GetAttrByName("CON")*0.3 +
			taker.GetAttrByName("VIS")*0.2 +
			0.2
		defVal = pressure.GetAttrByName("DEF")*0.4 +
			pressure.GetAttrByName("TKL")*0.3 +
			pressure.GetAttrByName("SPD")*0.3 +
			0.3
	}

	success := ResolveDuel(atkVal, defVal, sim.r, com)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = pressure
		sim.flipGlobalMomentum(ms)
	} else {
		ms.BallHolder = target
		if passType == config.EventLongPass {
			newCol := sim.r.IntN(3)
			ms.ActiveZone = [2]int{0, newCol}
			sim.applyControlShift(ms, ms.ActiveZone, 0.08)
		} else {
			if zone[0] > 0 {
				ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
			}
			sim.applyControlShift(ms, ms.ActiveZone, 0.02)
		}
		sim.boostGlobalMomentum(ms, 0.02)
	}

	detail := "pass"
	if passType == config.EventLongPass {
		detail = "long_pass"
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventFreeKick,
		Team:         ms.Possession.String(),
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		Player2ID:    target.PlayerID,
		Player2Name:  target.Name,
		OpponentID:   pressure.PlayerID,
		OpponentName: pressure.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       detail,
	})
}

func (sim *Simulator) doCornerEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime) {
	// Corner kick taker
	taker := SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
	setSkillContext(taker, config.EventCorner, [2]int{0, 1}, ms.Minute, ms.Half)
	ConsumeStamina(taker, 1.0)

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Corners++
	} else {
		ms.AwayStats.Corners++
	}

	// Cross-like resolution
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)
	setSkillContext(defender, config.EventCorner, [2]int{0, 1}, ms.Minute, ms.Half)
	atkVal := CalcCrossAttack(taker)
	defVal := CalcCrossDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventCorner,
		Team:         ms.Team(ms.Possession).Name,
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr([2]int{0, 1}),
		Result:       result,
	})

	if success {
		// Chain to header (with possible keeper rush)
		ms.ActiveZone = [2]int{0, 1}
		sim.setAssistCandidate(ms, taker, config.EventCorner)
		crossQuality := taker.GetAttrByName("CRO")*0.5 + taker.GetAttrByName("PAS")*0.3 + taker.GetAttrByName("DRI")*0.2
		if !sim.maybeKeeperRush(ms, possTeam, oppTeam, taker, crossQuality) {
			sim.doHeaderDuel(ms, possTeam, oppTeam)
		}
	}
}

func (sim *Simulator) addEvent(ms *domain.MatchState, ev domain.MatchEvent) {
	ev.Minute = ms.Minute
	// Ensure no two events share the exact same timestamp (prevents simultaneous push)
	if len(ms.Events) > 0 {
		lastEv := ms.Events[len(ms.Events)-1]
		if ev.Minute <= lastEv.Minute+0.001 {
			ev.Minute = lastEv.Minute + 0.033 // ~2 seconds offset
		}
	}
	if ev.Team == "" && ev.Type != config.EventHalftime && ev.Type != config.EventFulltime {
		ev.Team = ms.Possession.String()
	}
	// Attach current score to every event so narratives can reference it
	if ev.Score == nil {
		ev.Score = &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away}
	}
	// Auto-fill jersey numbers from player runtimes
	for _, p := range ms.HomeTeam.PlayerRuntimes {
		if p.PlayerID == ev.PlayerID {
			ev.PlayerNumber = p.Number
		}
		if p.PlayerID == ev.Player2ID {
			ev.Player2Number = p.Number
		}
		if p.PlayerID == ev.OpponentID {
			ev.OpponentNumber = p.Number
		}
	}
	for _, p := range ms.AwayTeam.PlayerRuntimes {
		if p.PlayerID == ev.PlayerID {
			ev.PlayerNumber = p.Number
		}
		if p.PlayerID == ev.Player2ID {
			ev.Player2Number = p.Number
		}
		if p.PlayerID == ev.OpponentID {
			ev.OpponentNumber = p.Number
		}
	}
	// Generate narrative with control/momentum context
	ctrl := ms.EffectiveControl(ms.ActiveZone)
	ev.Narrative = sim.ng.GenerateWithContext(ev, ctrl, ms.GlobalMomentum, ms.ActiveZone)

	// Append skill suffixes from involved players
	var suffixes []string
	for _, p := range ms.HomeTeam.PlayerRuntimes {
		if (p.PlayerID == ev.PlayerID || p.PlayerID == ev.OpponentID) && p.LastSkillSuffix != "" {
			suffixes = append(suffixes, p.LastSkillSuffix)
			p.LastSkillSuffix = ""
		}
	}
	for _, p := range ms.AwayTeam.PlayerRuntimes {
		if (p.PlayerID == ev.PlayerID || p.PlayerID == ev.OpponentID) && p.LastSkillSuffix != "" {
			suffixes = append(suffixes, p.LastSkillSuffix)
			p.LastSkillSuffix = ""
		}
	}
	if len(suffixes) > 0 {
		ev.Narrative += strings.Join(suffixes, "")
	}

	ms.AddEvent(ev)
}

func zoneStr(z [2]int) string {
	return fmt.Sprintf("[%d,%d]", z[0], z[1])
}

func (sim *Simulator) buildResult(ms *domain.MatchState) domain.SimulateResult {
	result := domain.SimulateResult{
		MatchID:  ms.MatchID,
		HomeTeam: ms.HomeTeam.Name,
		AwayTeam: ms.AwayTeam.Name,
		Score:    ms.Score,
		Events:   ms.Events,
	}

	// Possession
	totalTicks := ms.PossessionTicks[0] + ms.PossessionTicks[1]
	if totalTicks > 0 {
		result.Stats.PossessionHome = float64(ms.PossessionTicks[0]) / float64(totalTicks) * 100
		result.Stats.PossessionAway = float64(ms.PossessionTicks[1]) / float64(totalTicks) * 100
	}
	result.Stats.ShotsHome = ms.HomeStats.Shots
	result.Stats.ShotsAway = ms.AwayStats.Shots
	result.Stats.ShotsOnTargetHome = ms.HomeStats.ShotsOnTarget
	result.Stats.ShotsOnTargetAway = ms.AwayStats.ShotsOnTarget
	result.Stats.PassesHome = ms.HomeStats.Passes
	result.Stats.PassesAway = ms.AwayStats.Passes
	if ms.HomeStats.Passes > 0 {
		result.Stats.PassAccuracyHome = float64(ms.HomeStats.PassesSucc) / float64(ms.HomeStats.Passes) * 100
	}
	if ms.AwayStats.Passes > 0 {
		result.Stats.PassAccuracyAway = float64(ms.AwayStats.PassesSucc) / float64(ms.AwayStats.Passes) * 100
	}
	result.Stats.KeyPassesHome = ms.HomeStats.KeyPasses
	result.Stats.KeyPassesAway = ms.AwayStats.KeyPasses
	result.Stats.CrossesHome = ms.HomeStats.Crosses
	result.Stats.CrossesAway = ms.AwayStats.Crosses
	if ms.HomeStats.Crosses > 0 {
		result.Stats.CrossAccuracyHome = float64(ms.HomeStats.CrossesSucc) / float64(ms.HomeStats.Crosses) * 100
	}
	if ms.AwayStats.Crosses > 0 {
		result.Stats.CrossAccuracyAway = float64(ms.AwayStats.CrossesSucc) / float64(ms.AwayStats.Crosses) * 100
	}
	result.Stats.DribblesHome = ms.HomeStats.Dribbles
	result.Stats.DribblesAway = ms.AwayStats.Dribbles
	if ms.HomeStats.Dribbles > 0 {
		result.Stats.DribbleAccuracyHome = float64(ms.HomeStats.DribblesSucc) / float64(ms.HomeStats.Dribbles) * 100
	}
	if ms.AwayStats.Dribbles > 0 {
		result.Stats.DribbleAccuracyAway = float64(ms.AwayStats.DribblesSucc) / float64(ms.AwayStats.Dribbles) * 100
	}
	result.Stats.TacklesHome = ms.HomeStats.Tackles
	result.Stats.TacklesAway = ms.AwayStats.Tackles
	if ms.HomeStats.Tackles > 0 {
		result.Stats.TackleAccuracyHome = float64(ms.HomeStats.TacklesSucc) / float64(ms.HomeStats.Tackles) * 100
	}
	if ms.AwayStats.Tackles > 0 {
		result.Stats.TackleAccuracyAway = float64(ms.AwayStats.TacklesSucc) / float64(ms.AwayStats.Tackles) * 100
	}
	result.Stats.InterceptionsHome = ms.HomeStats.Interceptions
	result.Stats.InterceptionsAway = ms.AwayStats.Interceptions
	result.Stats.ClearancesHome = ms.HomeStats.Clearances
	result.Stats.ClearancesAway = ms.AwayStats.Clearances
	result.Stats.BlocksHome = ms.HomeStats.Blocks
	result.Stats.BlocksAway = ms.AwayStats.Blocks
	result.Stats.HeadersHome = ms.HomeStats.Headers
	result.Stats.HeadersAway = ms.AwayStats.Headers
	if ms.HomeStats.Headers > 0 {
		result.Stats.HeaderAccuracyHome = float64(ms.HomeStats.HeaderWins) / float64(ms.HomeStats.Headers) * 100
	}
	if ms.AwayStats.Headers > 0 {
		result.Stats.HeaderAccuracyAway = float64(ms.AwayStats.HeaderWins) / float64(ms.AwayStats.Headers) * 100
	}
	result.Stats.SavesHome = ms.HomeStats.Saves
	result.Stats.SavesAway = ms.AwayStats.Saves
	result.Stats.CornersHome = ms.HomeStats.Corners
	result.Stats.CornersAway = ms.AwayStats.Corners
	result.Stats.FoulsHome = ms.HomeStats.Fouls
	result.Stats.FoulsAway = ms.AwayStats.Fouls
	result.Stats.FoulsDrawnHome = ms.HomeStats.FoulsDrawn
	result.Stats.FoulsDrawnAway = ms.AwayStats.FoulsDrawn
	result.Stats.OffsidesHome = ms.HomeStats.Offsides
	result.Stats.OffsidesAway = ms.AwayStats.Offsides
	result.Stats.YellowCardsHome = ms.HomeStats.YellowCards
	result.Stats.YellowCardsAway = ms.AwayStats.YellowCards
	result.Stats.RedCardsHome = ms.HomeStats.RedCards
	result.Stats.RedCardsAway = ms.AwayStats.RedCards
	result.Stats.FreeKicksHome = ms.HomeStats.FreeKicks
	result.Stats.FreeKicksAway = ms.AwayStats.FreeKicks
	result.Stats.FreeKickGoalsHome = ms.HomeStats.FreeKickGoals
	result.Stats.FreeKickGoalsAway = ms.AwayStats.FreeKickGoals
	result.Stats.PenaltiesHome = ms.HomeStats.Penalties
	result.Stats.PenaltiesAway = ms.AwayStats.Penalties
	result.Stats.PenaltyGoalsHome = ms.HomeStats.PenaltyGoals
	result.Stats.PenaltyGoalsAway = ms.AwayStats.PenaltyGoals

	// Player stats
	for _, team := range []*domain.TeamRuntime{ms.HomeTeam, ms.AwayTeam} {
		for _, p := range team.PlayerRuntimes {
			side := "home"
			if team == ms.AwayTeam {
				side = "away"
			}
			ps := p.Stats
			passAcc := 0.0
			if ps.Passes > 0 {
				passAcc = float64(ps.PassesSucc) / float64(ps.Passes) * 100
			}
			crossAcc := 0.0
			if ps.Crosses > 0 {
				crossAcc = float64(ps.CrossesSucc) / float64(ps.Crosses) * 100
			}
			dribbleAcc := 0.0
			if ps.Dribbles > 0 {
				dribbleAcc = float64(ps.DribblesSucc) / float64(ps.Dribbles) * 100
			}
			tackleAcc := 0.0
			if ps.Tackles > 0 {
				tackleAcc = float64(ps.TacklesSucc) / float64(ps.Tackles) * 100
			}
			headerAcc := 0.0
			if ps.Headers > 0 {
				headerAcc = float64(ps.HeaderWins) / float64(ps.Headers) * 100
			}
			// Clamp rating 3.0 - 10.0, then apply post-match statistical adjustment
			rating := ps.RatingBase + CalculatePostMatchRating(&ps, p.Position)
			if rating > 10.0 {
				rating = 10.0
			}
			if rating < 3.0 {
				rating = 3.0
			}
			if p.CurrentStamina < 10 {
				sim.maybeApplyInjury(ms, p, "post_overuse", nil)
			}
			stat := domain.PlayerResultStat{
				PlayerID:        p.PlayerID,
				Name:            p.Name,
				Position:        p.Position,
				Team:            side,
				Goals:           ps.Goals,
				Assists:         ps.Assists,
				Shots:           ps.Shots,
				ShotsOnTarget:   ps.ShotsOnTarget,
				Passes:          ps.Passes,
				PassAccuracy:    passAcc,
				KeyPasses:       ps.KeyPasses,
				Crosses:         ps.Crosses,
				CrossAccuracy:   crossAcc,
				Dribbles:        ps.Dribbles,
				DribbleAccuracy: dribbleAcc,
				Tackles:         ps.Tackles,
				TackleAccuracy:  tackleAcc,
				Interceptions:   ps.Intercepts,
				Clearances:      ps.Clearances,
				Blocks:          ps.Blocks,
				Headers:         ps.Headers,
				HeaderAccuracy:  headerAcc,
				Saves:           ps.Saves,
				Fouls:           ps.Fouls,
				FoulsDrawn:      ps.FoulsDrawn,
				Offsides:        ps.Offsides,
				YellowCards:     ps.YellowCards,
				RedCards:        ps.RedCards,
				FreeKicks:       ps.FreeKicks,
				FreeKickGoals:   ps.FreeKickGoals,
				Penalties:       ps.Penalties,
				PenaltyGoals:    ps.PenaltyGoals,
				Turnovers:       ps.Turnovers,
				Touches:         ps.Touches,
				Rating:          round(rating, 1),
				MatchWear:       p.MatchWear,
			}
			if p.MatchInjury != nil {
				stat.InjuryBodyPart = p.MatchInjury.BodyPart
				stat.InjuryName = p.MatchInjury.InjuryName
				stat.InjurySeverity = p.MatchInjury.Severity
				stat.InjuryDays = p.MatchInjury.RemainingDays
			}
			result.PlayerStats = append(result.PlayerStats, stat)
		}
	}

	// Tactical summaries (V1)
	result.TacticalSummaries = []domain.TacticalSummary{
		sim.buildTacticalSummary(ms.HomeTeam, ms.HomeTactical),
		sim.buildTacticalSummary(ms.AwayTeam, ms.AwayTactical),
	}

	// Narratives
	for _, ev := range ms.Events {
		narr := sim.ng.Generate(ev)
		if narr != "" {
			result.Narratives = append(result.Narratives, fmt.Sprintf("%s  %s", FormatMinute(ev.Minute), narr))
		}
	}

	return result
}

// trackInstructionTrigger records which player-level instruction dimensions were
// active for the current event. Only non-default values (!= 2) are counted.
func trackInstructionTrigger(tracking *domain.TacticalTracking, player *domain.PlayerRuntime, eventType string) {
	if player == nil {
		return
	}
	ins := player.Instruction
	if ins == (domain.PlayerInstruction{}) {
		return
	}

	record := func(key string, value int) {
		if value != 2 {
			tracking.InstructionTriggers[key]++
		}
	}

	switch eventType {
	case config.EventDribblePast, config.EventWingBreak, config.EventCutInside,
		config.EventOverlap, config.EventCrossRun:
		record("carry_ball", ins.CarryBall)
	case config.EventCloseShot, config.EventLongShot, config.EventHeader, config.EventShotWindup:
		record("shooting_frequency", ins.ShootingFrequency)
	case config.EventCross, config.EventSwitchPlay:
		record("crossing_frequency", ins.CrossingFrequency)
	case config.EventThroughBall, config.EventPassOverTop, config.EventLongPass,
		config.EventLobPass, config.EventMidBreak, config.EventCounterAttack:
		record("passing_risk", ins.PassingRisk)
	case config.EventShortPass, config.EventBackPass, config.EventPivotPass,
		config.EventBuildUp, config.EventHoldBall:
		record("passing_risk", ins.PassingRisk)
		record("hold_position", ins.HoldPosition)
	case config.EventTackle, config.EventIntercept, config.EventDoubleTeam,
		config.EventPressTogether, config.EventBlockPass, config.EventShotBlock,
		config.EventClearance:
		record("pressing_intensity", ins.PressingIntensity)
	case config.EventOneTwo, config.EventTrianglePass:
		record("forward_runs", ins.ForwardRuns)
	}
}

func (sim *Simulator) buildTacticalSummary(team *domain.TeamRuntime, tracking domain.TacticalTracking) domain.TacticalSummary {
	return domain.TacticalSummary{
		TeamID:                  team.TeamID,
		FormationID:             team.FormationID,
		RouteUsage:              tracking.RouteUsage,
		EventCounts:             tracking.EventCounts,
		PossessionByZone:        tracking.PossessionByZone,
		ShotsByZone:             tracking.ShotsByZone,
		TurnoversByZone:         tracking.TurnoversByZone,
		PressWinsByZone:         tracking.PressWinsByZone,
		CounterAttacks:          tracking.CounterAttacks,
		HighPressRecoveries:     tracking.HighPressRecoveries,
		GkShortDistributions:    tracking.GkShortDistributions,
		GkLongDistributions:     tracking.GkLongDistributions,
		InstructionTriggers:     tracking.InstructionTriggers,
		SituationalRuleTriggers: tracking.SituationalRuleTriggers,
	}
}

func round(v float64, decimals int) float64 {
	pow := 1.0
	for i := 0; i < decimals; i++ {
		pow *= 10
	}
	return float64(int(v*pow+0.5)) / pow
}

// setAssistCandidate marks a direct chance creator. Routine circulation should
// not call this; otherwise assists become "last pass before goal" noise.
func (sim *Simulator) setAssistCandidate(ms *domain.MatchState, passer *domain.PlayerRuntime, eventType string) {
	if passer == nil {
		ms.AssistCandidate = nil
		return
	}
	ms.AssistCandidate = &domain.AssistCandidate{
		Player:     passer,
		EventType:  eventType,
		EventIndex: ms.EventCounter,
	}
}

func (sim *Simulator) clearAssistCandidate(ms *domain.MatchState) {
	ms.AssistCandidate = nil
}

// recordAssist credits only a fresh direct chance creator with an assist.
// It returns any milestone tags earned by the assister, plus the assister runtime.
func (sim *Simulator) recordAssist(ms *domain.MatchState, scorer *domain.PlayerRuntime, possTeam *domain.TeamRuntime) ([]string, *domain.PlayerRuntime) {
	candidate := ms.AssistCandidate
	defer sim.clearAssistCandidate(ms)
	if candidate == nil || candidate.Player == nil || candidate.Player.PlayerID == scorer.PlayerID {
		return nil, nil
	}
	if ms.EventCounter-candidate.EventIndex > 3 {
		return nil, nil
	}
	for _, p := range possTeam.PlayerRuntimes {
		if p.PlayerID == candidate.Player.PlayerID {
			p.Stats.Assists++
			p.Stats.RatingBase += 0.7
			return buildAssistMilestones(p), p
		}
	}
	return nil, nil
}

// applyInjury creates an injury event and sets player state.
// opponent may be nil for non-contact injuries.
func (sim *Simulator) applyInjury(ms *domain.MatchState, player *domain.PlayerRuntime, part string, severity int, opponent *domain.PlayerRuntime) {
	if player.MatchInjury != nil {
		return // already injured
	}

	days := RandomRecoveryDays(sim.r, part, severity)
	injuryName := GetInjuryName(part, severity)

	player.MatchInjury = &domain.ActiveInjury{
		BodyPart:      part,
		InjuryName:    injuryName,
		Severity:      severity,
		RemainingDays: days,
		AttrImpact:    BuildInjuryAttrImpact(part),
	}

	// Legacy flags for compatibility
	player.Injured = true
	player.InjurySeverity = severity

	// Determine event type
	evType := config.EventMinorInjury
	if severity >= 2 {
		evType = config.EventMajorInjury
	}

	var teamName string
	for _, t := range []*domain.TeamRuntime{ms.HomeTeam, ms.AwayTeam} {
		for _, pl := range t.PlayerRuntimes {
			if pl.PlayerID == player.PlayerID {
				teamName = t.Name
				break
			}
		}
		for _, pl := range t.BenchRuntimes {
			if pl.PlayerID == player.PlayerID {
				teamName = t.Name
				break
			}
		}
	}

	ev := domain.MatchEvent{
		Type:       evType,
		Team:       teamName,
		PlayerID:   player.PlayerID,
		PlayerName: player.Name,
		Zone:       zoneStr(ms.ActiveZone),
		Detail:     part + "|" + injuryName + "|" + fmt.Sprintf("%d", severity) + "|" + fmt.Sprintf("%d", days),
	}
	if opponent != nil {
		ev.OpponentID = opponent.PlayerID
		ev.OpponentName = opponent.Name
	}
	sim.addEvent(ms, ev)

	// Medium/Major injuries: attempt substitution if possible
	if severity >= 2 {
		sim.attemptInjurySubstitution(ms, player)
	}
}

// applyWearForAction applies match wear for a specific action to a player
func (sim *Simulator) applyWearForAction(p *domain.PlayerRuntime, action string) {
	mult := GetStaminaWearMultiplier(p.CurrentStamina)
	ApplyMatchWear(p, action, mult)
}

func (sim *Simulator) maybeApplyInjury(ms *domain.MatchState, player *domain.PlayerRuntime, action string, opponent *domain.PlayerRuntime) {
	if player == nil || player.MatchInjury != nil || player.Substituted || player.RedCard {
		return
	}
	occurred, part, severity := CheckInjury(sim.r, player, action)
	if occurred {
		sim.applyInjury(ms, player, part, severity, opponent)
	}
}

// attemptInjurySubstitution tries to substitute an injured player
func (sim *Simulator) attemptInjurySubstitution(ms *domain.MatchState, injured *domain.PlayerRuntime) {
	// Find the team
	var team *domain.TeamRuntime
	for _, t := range []*domain.TeamRuntime{ms.HomeTeam, ms.AwayTeam} {
		for _, p := range t.PlayerRuntimes {
			if p.PlayerID == injured.PlayerID {
				team = t
				break
			}
		}
	}
	if team == nil {
		return
	}

	// Find available substitute (same position preferred)
	var sub *domain.PlayerRuntime
	for _, b := range team.BenchRuntimes {
		if b.Substituted || b.RedCard || b.MatchInjury != nil {
			continue
		}
		if sub == nil {
			sub = b
		} else if b.Position == injured.Position {
			sub = b
			break
		}
	}

	if sub != nil {
		// Perform substitution
		injured.Substituted = true
		sub.Substituted = false
		// Replace in PlayerRuntimes
		for i, p := range team.PlayerRuntimes {
			if p.PlayerID == injured.PlayerID {
				team.PlayerRuntimes[i] = sub
				break
			}
		}
		// Add to bench
		team.BenchRuntimes = append(team.BenchRuntimes, injured)
		// Remove sub from bench
		newBench := make([]*domain.PlayerRuntime, 0, len(team.BenchRuntimes))
		for _, b := range team.BenchRuntimes {
			if b.PlayerID != sub.PlayerID {
				newBench = append(newBench, b)
			}
		}
		team.BenchRuntimes = newBench

		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventSubstitution,
			Team:         team.Name,
			PlayerID:     sub.PlayerID,
			PlayerName:   sub.Name,
			OpponentID:   injured.PlayerID,
			OpponentName: injured.Name,
		})
	}
}

// applyMinuteWear applies per-minute wear to all on-field players
func (sim *Simulator) applyMinuteWear(ms *domain.MatchState) {
	for _, team := range []*domain.TeamRuntime{ms.HomeTeam, ms.AwayTeam} {
		for _, p := range team.PlayerRuntimes {
			if p.Substituted || p.RedCard {
				continue
			}
			mult := GetStaminaWearMultiplier(p.CurrentStamina)
			ApplyMinuteWear(p, mult)
			if p.CurrentStamina < 15 {
				sim.maybeApplyInjury(ms, p, "fatigue_crit", nil)
			}
		}
	}
}
