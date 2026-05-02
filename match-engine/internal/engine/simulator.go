package engine

import (
	"fmt"
	"math/rand/v2"
	"time"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// Simulator is the match engine
type Simulator struct {
	r *rand.Rand
	ng *NarrativeGenerator
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

func (sim *Simulator) Simulate(req domain.SimulateRequest) domain.SimulateResult {
	start := time.Now()

	// Init state
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

	// Set initial ball holder (home team kickoff taker)
	ms.BallHolder = sim.selectKickoffTaker(ms.HomeTeam)

	// Kickoff
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.HomeTeam.Name,
		OpponentName: ms.AwayTeam.Name,
		PlayerName:   ms.BallHolder.Name,
	})

	// Main loop
	for ms.Half <= 2 {
		if ms.Half == 1 && ms.Minute >= 25.0 {
			sim.handleHalftime(ms)
			continue
		}
		if ms.Half == 2 && ms.Minute >= 50.0 {
			break
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

		// Check substitutions at specific windows
		sim.checkSubstitutions(ms)

		// Track possession
		ms.PossessionTicks[ms.Possession]++

		// Pick and process next event
		sim.processEvent(ms)

		// Advance clock (average ~5-8 seconds per event for denser action)
		baseSec := 3.5 + sim.r.Float64()*5.0
		ms.AdvanceClock(baseSec)
	}

	// Fulltime
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventFulltime,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})

	// Build result
	result := sim.buildResult(ms)
	result.DurationMs = time.Since(start).Milliseconds()
	return result
}

func (sim *Simulator) processEvent(ms *domain.MatchState) (string, []candidateEvent) {
	ctrl := ms.EffectiveControl(ms.ActiveZone)
	zone := ms.ActiveZone
	possTeam := ms.Team(ms.Possession)
	oppTeam := ms.OppTeam(ms.Possession)

	// Determine available events based on zone and control
	var candidates []candidateEvent

	// === Tactical weight modifiers ===
	passingStyle := possTeam.Tactics.PassingStyle
	crossingStrategy := possTeam.Tactics.CrossingStrategy
	playFromBack := possTeam.Tactics.DefensiveLineHeight >= 2 && possTeam.Tactics.PassingStyle <= 1

	// Always available: passing events (base weight modified by passing style)
	shortPassWeight := 20
	backPassWeight := 25
	midPassWeight := 28
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
		candidates = append(candidates, candidateEvent{typ: config.EventMidPass, weight: midPassWeight})
		candidates = append(candidates, candidateEvent{typ: config.EventThroughBall, weight: throughWeight})
	}
	if zone[0] == 0 { // front zone
		candidates = append(candidates, candidateEvent{typ: config.EventCloseShot, weight: 10})
		crossWeight := 12
		switch crossingStrategy {
		case 0: // Avoid crossing
			crossWeight -= 8
		case 1: // Low cross
			crossWeight += 3
		case 3: // High cross
			crossWeight += 5
		case 4: // Frequent cross
			crossWeight += 10
		}
		candidates = append(candidates, candidateEvent{typ: config.EventCross, weight: crossWeight})
		// More passing options in front zone to reduce shooting
		candidates = append(candidates, candidateEvent{typ: config.EventShortPass, weight: 12})
	}

	// Wing zones
	if zone[1] == 0 || zone[1] == 2 {
		candidates = append(candidates, candidateEvent{typ: config.EventWingBreak, weight: 12})
		if zone[0] <= 1 {
			candidates = append(candidates, candidateEvent{typ: config.EventCutInside, weight: 8})
		}
	}

	// Long shot from mid
	if zone[0] == 1 && ctrl > 0.2 {
		longShotWeight := 4
		if possTeam.Tactics.ShootingMentality >= 3 {
			longShotWeight += 4
		} else if possTeam.Tactics.ShootingMentality <= 1 {
			longShotWeight -= 2
		}
		candidates = append(candidates, candidateEvent{typ: config.EventLongShot, weight: longShotWeight})
	}

	// Defensive events — expanded trigger range and higher weights
	clearanceWeight := 10
	if playFromBack && zone[0] == 2 {
		clearanceWeight = 3 // Play from back reduces clearance tendency
	}
	if ctrl < 0.2 {
		candidates = append(candidates, candidateEvent{typ: config.EventTackle, weight: 18})
		candidates = append(candidates, candidateEvent{typ: config.EventIntercept, weight: 14})
		if zone[0] <= 1 {
			candidates = append(candidates, candidateEvent{typ: config.EventClearance, weight: clearanceWeight})
		}
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
		foulWeight += int(possTeam.Tactics.TacklingAggression)
	}
	if oppTeam.Tactics.TacklingAggression >= 2 {
		foulWeight += int(oppTeam.Tactics.TacklingAggression)
	}
	candidates = append(candidates, candidateEvent{typ: config.EventFoul, weight: foulWeight})

	// Control factor boosts attacking events when control is high
	for i := range candidates {
		if candidates[i].typ == config.EventBackPass || candidates[i].typ == config.EventMidPass ||
			candidates[i].typ == config.EventShortPass || candidates[i].typ == config.EventLongPass {
			continue // passing always available
		}
		candidates[i].weight = int(float64(candidates[i].weight) * (1.0 + ctrl*0.4))
		if candidates[i].weight < 2 {
			candidates[i].weight = 2
		}
	}

	// Select event
	selected := sim.pickEvent(candidates)
	possBefore := ms.Possession
	sim.executeEvent(ms, selected)

	// === Post-event tactical effects ===
	if ms.Possession != possBefore {
		// Turnover occurred: emit transition event
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventTurnover,
			Team:         ms.Team(ms.Possession).Name,
			PlayerID:     ms.BallHolder.PlayerID,
			PlayerName:   ms.BallHolder.Name,
			OpponentName: ms.Team(possBefore).Name,
		})

		// Flip control shift in the zone where it happened
		sim.flipControlShiftOnTurnover(ms, zone)

		newPossTeam := ms.Team(ms.Possession)
		lostPossTeam := ms.Team(possBefore)

		// Counter focus: new possession team gets temporary speed/precision boost
		if newPossTeam.Tactics.AttackTempo == 4 {
			sim.applyCounterBoost(ms, ms.Possession)
		}

		// High press: turnover in opponent half may immediately advance zone
		if lostPossTeam.Tactics.DefensiveLineHeight >= 3 && lostPossTeam.Tactics.PressingIntensity >= 3 {
			if zone[0] <= 1 { // turnover occurred in opponent's half or midfield
				if sim.r.Float64() < 0.35 {
					// High press: immediate forward push after winning back ball
					if ms.ActiveZone[0] < 2 {
						ms.ActiveZone[0]++
					}
					// Boost momentum for pressing team
					sim.applyControlShift(ms, ms.ActiveZone, 0.12)
					sim.boostGlobalMomentum(ms, 0.03)
				}
			}
		}
	}

	return selected, candidates
}

type candidateEvent struct {
	typ    string
	weight int
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
	}
}

func (sim *Simulator) doPassEvent(ms *domain.MatchState, passType string, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, ctrl float64) {
	holder := ms.BallHolder
	pressure := SelectDefender(oppTeam, zone, sim.r)
	target := SelectPassTarget(possTeam, zone, sim.r)

	// === Aggressiveness branching ===
	riskIdx := ComputeRiskIndex(possTeam.Tactics)
	aggroProb := sigmoid(riskIdx*3.0 + ctrl*1.5 - 2.0) * 0.6
	if aggroProb < 0.05 {
		aggroProb = 0.05
	}
	if aggroProb > 0.80 {
		aggroProb = 0.80
	}
	isAggressive := sim.r.Float64() < aggroProb

	atkVal := CalcPassAttack(holder, ctrl)
	defVal := CalcPassDefense(pressure, ctrl)
	// Slightly boost pass defense to reduce easy progression
	defVal += 0.6

	passDetail := "safe"
	if isAggressive {
		passDetail = "aggressive"
		atkVal -= 0.10 // aggressive pass is riskier
	} else {
		atkVal += 0.15 // safe pass is more reliable
	}

	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(holder, StaminaCost(passType))
	ConsumeStamina(pressure, StaminaCost(passType)*0.5)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = zone // stays roughly same area
		ms.BallHolder = pressure // defender wins possession
		sim.flipGlobalMomentum(ms)
	} else {
		if isAggressive {
			sim.applyControlShift(ms, ms.ActiveZone, 0.08)
		} else {
			sim.applyControlShift(ms, ms.ActiveZone, 0.02)
		}
		sim.boostGlobalMomentum(ms, 0.01)
	}

	// Update stats
	holder.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
			holder.Stats.PassesSucc++
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
			holder.Stats.PassesSucc++
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         passType,
		Team:         ms.Possession.String(),
		PlayerID:     holder.PlayerID,
		PlayerName:   holder.Name,
		Player2ID:    target.PlayerID,
		Player2Name:  target.Name,
		OpponentID:   pressure.PlayerID,
		OpponentName: pressure.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       passDetail,
	})

	// Advance zone on success — dynamic based on pass quality and receiver movement
	if success {
		passQuality := holder.GetAttrByName("PAS")*0.5 +
			holder.GetAttrByName("VIS")*0.3 +
			holder.GetAttrByName("CON")*0.2
		receiveQuality := target.GetAttrByName("SPD")*0.3 +
			target.GetAttrByName("ACC")*0.3 +
			target.GetAttrByName("POS")*0.4

		// Forward chance: better pass + better receiver + high control
		forwardProb := 0.15 + sigmoid((passQuality+receiveQuality-20.0+ctrl*5.0)/5.0)*0.50
		if forwardProb < 0.10 {
			forwardProb = 0.10
		}
		if forwardProb > 0.70 {
			forwardProb = 0.70
		}

		// Backward chance: low quality or under pressure
		backwardProb := 0.10 + sigmoid((20.0-passQuality-receiveQuality-ctrl*5.0)/5.0)*0.30
		if backwardProb < 0.05 {
			backwardProb = 0.05
		}
		if backwardProb > 0.40 {
			backwardProb = 0.40
		}

		// ST target always gets a forward bonus
		if target.Position == config.PosST && zone[0] > 0 {
			forwardProb += 0.15
		}

		roll := sim.r.Float64()
		if roll < forwardProb && zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		} else if roll < forwardProb+backwardProb && zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] + 1, zone[1]}
		}
		// else: stay in same zone
		ms.BallHolder = target // receiver becomes new ball holder
	}
}

func (sim *Simulator) doLongPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	holder := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcLongPassAttack(holder)
	defVal := CalcLongPassDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(holder, StaminaCost(config.EventLongPass))

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
	}

	holder.Stats.Passes++
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
			holder.Stats.PassesSucc++
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
			holder.Stats.PassesSucc++
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

	atkVal := CalcDribbleAttack(dribbler)
	defVal := CalcDribbleDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(dribbler, StaminaCost(config.EventWingBreak))
	ConsumeStamina(defender, StaminaCost(config.EventWingBreak)*0.6)

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

	atkVal := dribbler.GetAttrByName("DRI")*0.4 + dribbler.GetAttrByName("SHO")*0.2 +
		dribbler.GetAttrByName("ACC")*0.2 + dribbler.GetAttrByName("SPD")*0.2
	defVal := defender.GetAttrByName("DEF")*0.4 + defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("POS")*0.3

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(dribbler, StaminaCost(config.EventCutInside))

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

func (sim *Simulator) doThroughBallEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	passer := ms.BallHolder
	target := SelectPassTarget(possTeam, [2]int{0, 1}, sim.r)
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)

	atkVal := CalcThroughAttack(passer)
	defVal := CalcThroughDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(passer, StaminaCost(config.EventThroughBall))

	result := "success"
	if !success {
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
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
			passer.Stats.PassesSucc++
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

	result := "success"
	if !success {
		result = "fail"
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
	} else {
		sim.applyControlShift(ms, [2]int{0, 1}, 0.08)
		sim.boostGlobalMomentum(ms, 0.02)
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
		// Chain to header duel
		ms.ActiveZone = [2]int{0, 1}
		sim.doHeaderDuel(ms, possTeam, oppTeam)
	}
}

func (sim *Simulator) doHeaderDuel(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime) {
	attacker := SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)

	atkVal := CalcHeaderAttack(attacker)
	defVal := CalcHeaderDefense(defender)

	// High cross strategy boosts header duel attack value
	if possTeam.Tactics.CrossingStrategy >= 3 {
		atkVal += 0.4
	}

	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(attacker, 1.5)
	ConsumeStamina(defender, 1.5)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
	} else {
		ms.BallHolder = attacker
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
		target := SelectPassTarget(possTeam, [2]int{0, 1}, sim.r)
		if target.PlayerID == attacker.PlayerID {
			players := possTeam.GetActivePlayers()
			for _, p := range players {
				if p.PlayerID != attacker.PlayerID {
					target = p
					break
				}
			}
		}
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}

	sim.addEvent(ms, ev)

	if success {
		// Dynamic shot chance after header based on attacker's aerial threat + finishing
		shotTendency := attacker.GetAttrByName("HEA")*0.3 +
			attacker.GetAttrByName("SHO")*0.4 +
			attacker.GetAttrByName("FIN")*0.3
		ctrl := ms.EffectiveControl([2]int{0, 1})
		if ctrl > 0.3 {
			shotTendency += 2.0
		}
		shotChance := sigmoid((shotTendency-12.0)/4.0) * 0.7
		if shotChance < 0.15 {
			shotChance = 0.15
		}
		if shotChance > 0.75 {
			shotChance = 0.75
		}
		if sim.r.Float64() < shotChance {
			sim.doShotEvent(ms, possTeam, oppTeam, [2]int{0, 1}, "close")
		}
	}
}

func (sim *Simulator) doShotEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, distance string) {
	shooter := ms.BallHolder
	keeper := oppTeam.GetGK()

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
	blockChance := sigmoid(blockDelta/5.0) * 0.6

	// Deep defense active: +25% shot block chance in own penalty area
	if oppTeam.Tactics.DefensiveLineHeight <= 1 && oppTeam.Tactics.DefensiveCompactness >= 2 {
		if zone[0] >= 2 { // shot taken from deep defense team's penalty area
			blockChance += 0.25
		}
	}

	if blockChance < 0.05 {
		blockChance = 0.05
	}
	if blockChance > 0.75 {
		blockChance = 0.75
	}

	// === Step 2: Is the shot blocked? ===
	blocked := sim.r.Float64() < blockChance

	// === Step 3: If not blocked, keeper makes the save ===
	com := shooter.GetAttrByName("COM")
	success := false
	if !blocked {
		success = ResolveDuel(atkVal, defVal+0.2, sim.r, com)
	}

	ConsumeStamina(shooter, StaminaCost(config.EventCloseShot))

	// Stats
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Shots++
	} else {
		ms.AwayStats.Shots++
	}

	shotResult := "missed"
	if blocked {
		shotResult = "blocked"
		nearestDefender.Stats.RatingBase += 0.15
	} else if success {
		shotResult = "goal"
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.Score.Away++
			ms.AwayStats.ShotsOnTarget++
		}
		shooter.Stats.Goals++
		keeper.Stats.RatingBase -= 0.8
		shooter.Stats.RatingBase += 1.0
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
			keeper.Stats.RatingBase += 0.25
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
	sim.addEvent(ms, domain.MatchEvent{
		Type:         evType,
		Team:         ms.Possession.String(),
		PlayerID:     shooter.PlayerID,
		PlayerName:   shooter.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       shotResult,
		Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})

	// Chain to specific result events
	if shotResult == "goal" {
		// Independent Goal event
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventGoal,
			Team:         ms.Possession.String(),
			PlayerID:     shooter.PlayerID,
			PlayerName:   shooter.Name,
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
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
	tackler := SelectDefender(oppTeam, zone, sim.r)
	holder := ms.BallHolder

	atkVal := CalcTackleAttack(tackler)
	defVal := CalcTackleDefense(holder)
	// Boost tackle success to make defense more effective
	atkVal += 1.2
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(tackler, StaminaCost(config.EventTackle))
	ConsumeStamina(holder, StaminaCost(config.EventTackle)*0.5)

	result := "success"
	if success {
		ms.Possession = ms.Possession.Opponent()
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
		sim.applyControlShift(ms, zone, 0.08)
		sim.boostGlobalMomentum(ms, 0.02)
	} else {
		result = "fail"
		tackler.Stats.Tackles++
		holder.Stats.RatingBase += 0.05
		sim.applyControlShift(ms, zone, 0.03)
		sim.boostGlobalMomentum(ms, 0.01)
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
	// Interception: turnover
	interceptor := SelectDefender(oppTeam, zone, sim.r)
	passer := ms.BallHolder

	ConsumeStamina(interceptor, StaminaCost(config.EventIntercept))

	ms.Possession = ms.Possession.Opponent()
	ms.ActiveZone = zone
	ms.BallHolder = interceptor
	interceptor.Stats.Intercepts++
	interceptor.Stats.RatingBase += 0.12
	sim.flipGlobalMomentum(ms)
	sim.applyControlShift(ms, zone, 0.06)
	sim.boostGlobalMomentum(ms, 0.01)

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventIntercept,
		Team:         ms.Possession.String(),
		PlayerID:     interceptor.PlayerID,
		PlayerName:   interceptor.Name,
		OpponentID:   passer.PlayerID,
		OpponentName: passer.Name,
		Zone:         zoneStr(zone),
		Result:       "success",
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
	// Prefer CMF/AMF for kickoff
	for _, p := range team.PlayerRuntimes {
		if p.Position == config.PosCMF || p.Position == config.PosAMF {
			return p
		}
	}
	for _, p := range team.PlayerRuntimes {
		if p.Position == config.PosST {
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
		Type:         config.EventSubstitution,
		Team:         team.Name,
		PlayerID:     subPlayer.PlayerID,
		PlayerName:   subPlayer.Name,
		Player2ID:    tiredPlayer.PlayerID,
		Player2Name:  tiredPlayer.Name,
		Result:       "success",
	})
}

func (sim *Simulator) doClearanceEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	// Clearance: defending team clears the ball
	defender := SelectDefender(oppTeam, zone, sim.r)
	ConsumeStamina(defender, StaminaCost(config.EventClearance))

	defender.Stats.Clearances++
	defender.Stats.RatingBase += 0.1

	// Dynamic own goal chance based on defender composure, pressure, and stamina
	clearanceQuality := defender.GetAttrByName("COM")*0.5 +
		defender.GetAttrByName("PAS")*0.3 +
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
			Type:         config.EventOwnGoal,
			Team:         oppTeam.Name,
			PlayerID:     defender.PlayerID,
			PlayerName:   defender.Name,
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
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

	// Ball goes to back zone of defending team
	ms.Possession = ms.Possession.Opponent()
	ms.ActiveZone = [2]int{2, 1}
	ms.BallHolder = SelectPlayerByZone(ms.Team(ms.Possession), [2]int{2, 1}, sim.r)
	sim.flipGlobalMomentum(ms)
	sim.applyControlShift(ms, [2]int{2, 1}, 0.05)
	sim.boostGlobalMomentum(ms, 0.01)
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
	fouler.Stats.RatingBase -= 0.15

	// === Dynamic card check based on foul severity ===
	cardResult := ""

	// Severity factors
	foulSeverity := fouler.GetAttrByName("TKL")*0.3 + fouler.GetAttrByName("STR")*0.3
	// Higher aggression tactic = more dangerous tackles
	aggressionBonus := float64(4-oppTeam.Tactics.TacklingAggression) * 1.5

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

	// Foul disrupts attacking momentum
	foulShift := 0.03
	if cardResult == "yellow" || cardResult == "red" {
		foulShift = 0.06
	}
	sim.applyControlShift(ms, zone, foulShift)
	sim.boostGlobalMomentum(ms, 0.01)

	// After foul, trigger free kick / penalty
	sim.doFreeKickEvent(ms, possTeam, oppTeam, zone)
}

func (sim *Simulator) handleHalftime(ms *domain.MatchState) {
	sim.addEvent(ms, domain.MatchEvent{
		Type:  config.EventHalftime,
		Score: &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})
	ms.Half = 2
	ms.Minute = 25.0
	HalftimeRecovery(ms)
	ms.Possession = domain.SideAway // away team kicks off 2nd half
	ms.ActiveZone = [2]int{1, 1}
	ms.BallHolder = sim.selectKickoffTaker(ms.AwayTeam)
	// 2nd half kickoff
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.AwayTeam.Name,
		OpponentName: ms.HomeTeam.Name,
		PlayerName:   ms.BallHolder.Name,
	})
}

func (sim *Simulator) doFreeKickEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	taker := SelectPlayerByZone(possTeam, zone, sim.r)
	ConsumeStamina(taker, StaminaCost(config.EventFreeKick))

	if ms.Possession == domain.SideHome {
		ms.HomeStats.FreeKicks++
	} else {
		ms.AwayStats.FreeKicks++
	}
	taker.Stats.FreeKicks++

	ctrl := ms.EffectiveControl(zone)

	switch {
	case zone[0] == 0 && zone[1] == 1:
		// Penalty kick
		sim.doPenaltyKick(ms, possTeam, oppTeam, zone, taker, ctrl)
	case zone[0] == 0 && (zone[1] == 0 || zone[1] == 2):
		// Front wing free kick → cross
		sim.doFreeKickCross(ms, possTeam, oppTeam, zone, taker, ctrl)
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
	com := taker.GetAttrByName("COM")

	atkVal := taker.GetAttrByName("PK")*0.5 +
		taker.GetAttrByName("SHO")*0.3 +
		taker.GetAttrByName("FIN")*0.2 +
		0.3
	defVal := keeper.GetAttrByName("SAV")*0.5 +
		keeper.GetAttrByName("REF")*0.3 +
		keeper.GetAttrByName("POS")*0.2 +
		1.0

	success := ResolveDuel(atkVal, defVal, sim.r, com)

	result := "goal"
	if !success {
		result = "saved"
		if sim.r.Float64() < 0.3 {
			result = "fail"
		}
	}

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Penalties++
	} else {
		ms.AwayStats.Penalties++
	}
	taker.Stats.Penalties++

	if result == "goal" {
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.PenaltyGoals++
		} else {
			ms.Score.Away++
			ms.AwayStats.PenaltyGoals++
		}
		taker.Stats.PenaltyGoals++
		taker.Stats.Goals++
		taker.Stats.RatingBase += 1.0
		keeper.Stats.RatingBase -= 0.8
		ms.BallHolder = taker
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)
	} else if result == "saved" {
		keeper.Stats.Saves++
		keeper.Stats.RatingBase += 0.3
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

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventFreeKick,
		Team:         ms.Possession.String(),
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       "penalty",
	})
}

func (sim *Simulator) doFreeKickCross(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, taker *domain.PlayerRuntime, ctrl float64) {
	defender := SelectDefender(oppTeam, zone, sim.r)
	com := taker.GetAttrByName("COM")

	atkVal := taker.GetAttrByName("FK")*0.5 +
		taker.GetAttrByName("CRO")*0.3 +
		taker.GetAttrByName("PAS")*0.2
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
	com := taker.GetAttrByName("COM")

	atkVal := taker.GetAttrByName("FK")*0.4 +
		taker.GetAttrByName("SHO")*0.4 +
		taker.GetAttrByName("FIN")*0.2 +
		0.5
	defVal := keeper.GetAttrByName("SAV")*0.45 +
		keeper.GetAttrByName("REF")*0.35 +
		keeper.GetAttrByName("POS")*0.2 +
		1.0

	success := ResolveDuel(atkVal, defVal, sim.r, com)

	result := "goal"
	if !success {
		result = "saved"
		if sim.r.Float64() < 0.25 {
			result = "fail"
		}
	}

	if result == "goal" {
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.FreeKickGoals++
		} else {
			ms.Score.Away++
			ms.AwayStats.FreeKickGoals++
		}
		taker.Stats.FreeKickGoals++
		taker.Stats.Goals++
		taker.Stats.RatingBase += 1.0
		keeper.Stats.RatingBase -= 0.8
		ms.BallHolder = taker
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)
	} else if result == "saved" {
		keeper.Stats.Saves++
		keeper.Stats.RatingBase += 0.3
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

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventFreeKick,
		Team:         ms.Possession.String(),
		PlayerID:     taker.PlayerID,
		PlayerName:   taker.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Detail:       "shot",
	})
}

func (sim *Simulator) doFreeKickPass(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, taker *domain.PlayerRuntime, ctrl float64, passType string) {
	target := SelectPassTarget(possTeam, zone, sim.r)
	pressure := SelectDefender(oppTeam, zone, sim.r)
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
	ConsumeStamina(taker, 1.0)

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Corners++
	} else {
		ms.AwayStats.Corners++
	}

	// Cross-like resolution
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)
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
		// Chain to header
		ms.ActiveZone = [2]int{0, 1}
		sim.doHeaderDuel(ms, possTeam, oppTeam)
	}
}

func (sim *Simulator) addEvent(ms *domain.MatchState, ev domain.MatchEvent) {
	ev.Minute = ms.Minute
	if ev.Team == "" && ev.Type != config.EventHalftime && ev.Type != config.EventFulltime {
		ev.Team = ms.Possession.String()
	}
	if ev.Score == nil && (ev.Type == config.EventGoal || ev.Type == config.EventHalftime || ev.Type == config.EventFulltime) {
		ev.Score = &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away}
	}
	// Generate narrative with control/momentum context
	ctrl := ms.EffectiveControl(ms.ActiveZone)
	ev.Narrative = sim.ng.GenerateWithContext(ev, ctrl, ms.GlobalMomentum, ms.ActiveZone)
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
	result.Stats.TacklesHome = ms.HomeStats.Tackles
	result.Stats.TacklesAway = ms.AwayStats.Tackles
	result.Stats.CornersHome = ms.HomeStats.Corners
	result.Stats.CornersAway = ms.AwayStats.Corners
	result.Stats.FoulsHome = ms.HomeStats.Fouls
	result.Stats.FoulsAway = ms.AwayStats.Fouls
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
			tackleAcc := 0.0
			if ps.Tackles > 0 {
				tackleAcc = float64(ps.TacklesSucc) / float64(ps.Tackles) * 100
			}
			// Clamp rating 3.0 - 10.0
			rating := ps.RatingBase
			if rating > 10.0 {
				rating = 10.0
			}
			if rating < 3.0 {
				rating = 3.0
			}
			result.PlayerStats = append(result.PlayerStats, domain.PlayerResultStat{
				PlayerID:      p.PlayerID,
				Name:          p.Name,
				Position:      p.Position,
				Team:          side,
				Goals:         ps.Goals,
				Assists:       ps.Assists,
				Shots:         ps.Shots,
				ShotsOnTarget: ps.ShotsOnTarget,
				Passes:        ps.Passes,
				PassAccuracy:  passAcc,
				Tackles:        ps.Tackles,
				TackleAccuracy: tackleAcc,
				Interceptions: ps.Intercepts,
				Saves:         ps.Saves,
				Fouls:         ps.Fouls,
				YellowCards:   ps.YellowCards,
				RedCards:      ps.RedCards,
				FreeKicks:     ps.FreeKicks,
				FreeKickGoals: ps.FreeKickGoals,
				Penalties:     ps.Penalties,
				PenaltyGoals:  ps.PenaltyGoals,
				Rating:        round(rating, 1),
			})
		}
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

func round(v float64, decimals int) float64 {
	pow := 1.0
	for i := 0; i < decimals; i++ {
		pow *= 10
	}
	return float64(int(v*pow+0.5)) / pow
}
