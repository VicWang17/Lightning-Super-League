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

	// Kickoff
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.HomeTeam.Name,
		OpponentName: ms.AwayTeam.Name,
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

		// Momentum decay: recent event effects fade over time
		sim.decayMomentum(ms)

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

func (sim *Simulator) processEvent(ms *domain.MatchState) {
	ctrl := ms.ControlMatrix[ms.ActiveZone[0]][ms.ActiveZone[1]]
	zone := ms.ActiveZone
	possTeam := ms.Team(ms.Possession)
	oppTeam := ms.OppTeam(ms.Possession)

	// Determine available events based on zone and control
	var candidates []candidateEvent

	// Always available: passing events
	candidates = append(candidates, candidateEvent{typ: config.EventShortPass, weight: 20})

	if zone[0] == 2 { // back zone
		candidates = append(candidates, candidateEvent{typ: config.EventBackPass, weight: 25})
		candidates = append(candidates, candidateEvent{typ: config.EventLongPass, weight: 8})
	}
	if zone[0] == 1 { // mid zone
		candidates = append(candidates, candidateEvent{typ: config.EventMidPass, weight: 28})
		candidates = append(candidates, candidateEvent{typ: config.EventThroughBall, weight: 10})
	}
	if zone[0] == 0 { // front zone
		candidates = append(candidates, candidateEvent{typ: config.EventCloseShot, weight: 10})
		candidates = append(candidates, candidateEvent{typ: config.EventCross, weight: 12})
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
		candidates = append(candidates, candidateEvent{typ: config.EventLongShot, weight: 4})
	}

	// Defensive events — expanded trigger range and higher weights
	if ctrl < 0.2 {
		candidates = append(candidates, candidateEvent{typ: config.EventTackle, weight: 18})
		candidates = append(candidates, candidateEvent{typ: config.EventIntercept, weight: 14})
		if zone[0] <= 1 {
			candidates = append(candidates, candidateEvent{typ: config.EventClearance, weight: 10})
		}
	}

	// Header duel available in front zone
	if zone[0] == 0 {
		candidates = append(candidates, candidateEvent{typ: config.EventHeader, weight: 6})
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
	sim.executeEvent(ms, selected)
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
	ctrl := ms.ControlMatrix[zone[0]][zone[1]]

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
	holder := SelectPlayerByZone(possTeam, zone, sim.r)
	pressure := SelectDefender(oppTeam, zone, sim.r)
	target := SelectPassTarget(possTeam, zone, sim.r)

	atkVal := CalcPassAttack(holder, ctrl)
	defVal := CalcPassDefense(pressure, ctrl)
	// Slightly boost pass defense to reduce easy progression
	defVal += 0.6
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(holder, StaminaCost(passType))
	ConsumeStamina(pressure, StaminaCost(passType)*0.5)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = zone // stays roughly same area
		sim.flipMomentumOnTurnover(ms)
	} else {
		sim.boostMomentum(ms, ms.ActiveZone, 0.06)
	}

	// Update stats
	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
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
	})

	// Advance zone on success
	if success {
		if target.Position == config.PosST && zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		} else if sim.r.Float64() < 0.3 && zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		} else if sim.r.Float64() < 0.3 && zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] + 1, zone[1]}
		}
	}
}

func (sim *Simulator) doLongPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	holder := SelectPlayerByZone(possTeam, zone, sim.r)
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcLongPassAttack(holder)
	defVal := CalcLongPassDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(holder, StaminaCost(config.EventLongPass))

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
	}

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventLongPass,
		Team:         ms.Possession.String(),
		PlayerID:     holder.PlayerID,
		PlayerName:   holder.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})

	if success {
		// Jump to front zone
		newCol := sim.r.IntN(3)
		ms.ActiveZone = [2]int{0, newCol}
		sim.boostMomentum(ms, ms.ActiveZone, 0.08)
	} else {
		sim.flipMomentumOnTurnover(ms)
	}
}

func (sim *Simulator) doWingBreakEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	dribbler := SelectPlayerByZone(possTeam, zone, sim.r)
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
		sim.flipMomentumOnTurnover(ms)
	} else {
		sim.boostMomentum(ms, zone, 0.10)
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
		ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
	}
}

func (sim *Simulator) doCutInsideEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	dribbler := SelectPlayerByZone(possTeam, zone, sim.r)
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
		sim.flipMomentumOnTurnover(ms)
	} else {
		sim.boostMomentum(ms, zone, 0.10)
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
		ms.ActiveZone = [2]int{0, 1} // move to center front
	}
}

func (sim *Simulator) doThroughBallEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	passer := SelectPlayerByZone(possTeam, zone, sim.r)
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
	}

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
		if success {
			ms.HomeStats.PassesSucc++
		}
	} else {
		ms.AwayStats.Passes++
		if success {
			ms.AwayStats.PassesSucc++
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
			sim.flipMomentumOnTurnover(ms)
			return
		}
		ms.ActiveZone = [2]int{0, 1}
		sim.boostMomentum(ms, ms.ActiveZone, 0.12)
	} else {
		sim.flipMomentumOnTurnover(ms)
	}
}

func (sim *Simulator) doCrossEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	crosser := SelectPlayerByZone(possTeam, zone, sim.r)
	defender := SelectDefender(oppTeam, [2]int{0, 1}, sim.r)

	atkVal := CalcCrossAttack(crosser)
	defVal := CalcCrossDefense(defender)
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(crosser, StaminaCost(config.EventCross))

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Passes++
	} else {
		ms.AwayStats.Passes++
	}

	result := "success"
	if !success {
		result = "fail"
		// Out for corner
		if sim.r.Float64() < 0.4 {
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
		sim.flipMomentumOnTurnover(ms)
	} else {
		sim.boostMomentum(ms, [2]int{0, 1}, 0.08)
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
	success := ResolveDuel(atkVal, defVal, sim.r)

	ConsumeStamina(attacker, 1.5)
	ConsumeStamina(defender, 1.5)

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		sim.flipMomentumOnTurnover(ms)
	} else {
		sim.boostMomentum(ms, [2]int{0, 1}, 0.07)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventHeader,
		Team:         ms.Possession.String(),
		PlayerID:     attacker.PlayerID,
		PlayerName:   attacker.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr([2]int{0, 1}),
		Result:       result,
	})

	if success {
		// Chance for shot after header
		if sim.r.Float64() < 0.35 {
			sim.doShotEvent(ms, possTeam, oppTeam, [2]int{0, 1}, "close")
		}
	}
}

func (sim *Simulator) doShotEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, distance string) {
	shooter := SelectPlayerByZone(possTeam, zone, sim.r)
	keeper := oppTeam.GetGK()

	atkVal := CalcShotAttack(shooter, distance)
	defVal := CalcSaveDefense(keeper, distance)

	// Shooting mentality affects shot quality
	mentality := possTeam.Tactics.ShootingMentality
	if mentality >= 3 {
		atkVal += 0.5 // more aggressive shooting
	}

	// First: is the shot on target?
	onTarget := ResolveDuel(atkVal, defVal-4.5, sim.r)
	// Second: if on target, does it beat the keeper?
	success := false
	if onTarget {
		success = ResolveDuel(atkVal, defVal+0.2, sim.r)
	}

	ConsumeStamina(shooter, StaminaCost(config.EventCloseShot))

	// Stats
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
		keeper.Stats.RatingBase -= 0.8
		shooter.Stats.RatingBase += 1.0
		sim.boostMomentum(ms, zone, 0.15)
	} else if onTarget {
		// Shot was on target but didn't go in
		roll := sim.r.Float64()
		if roll < 0.50 {
			shotResult = "saved"
			keeper.Stats.Saves++
			keeper.Stats.RatingBase += 0.25
			if ms.Possession == domain.SideHome {
				ms.HomeStats.ShotsOnTarget++
			} else {
				ms.AwayStats.ShotsOnTarget++
			}
			sim.boostMomentum(ms, zone, 0.05)
		} else if roll < 0.75 {
			shotResult = "blocked"
			// Find a defender to credit
			defender := SelectDefender(oppTeam, zone, sim.r)
			defender.Stats.RatingBase += 0.1
			ms.ZoneMomentum[zone[0]][zone[1]] -= 0.03
		} else {
			shotResult = "woodwork"
			if ms.Possession == domain.SideHome {
				ms.HomeStats.ShotsOnTarget++
			} else {
				ms.AwayStats.ShotsOnTarget++
			}
			sim.boostMomentum(ms, zone, 0.03)
		}
	} else {
		// Not on target — clear miss
		ms.ZoneMomentum[zone[0]][zone[1]] -= 0.05
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
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
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
	}
}

func (sim *Simulator) doTackleEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	// Tackle: defending team tries to win ball from possession team
	tackler := SelectDefender(oppTeam, zone, sim.r)
	holder := SelectPlayerByZone(possTeam, zone, sim.r)

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
		sim.flipMomentumOnTurnover(ms)
		sim.boostMomentum(ms, zone, 0.08)
	} else {
		result = "fail"
		holder.Stats.RatingBase += 0.05
		sim.boostMomentum(ms, zone, 0.03)
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
	passer := SelectPlayerByZone(possTeam, zone, sim.r)

	ConsumeStamina(interceptor, StaminaCost(config.EventIntercept))

	ms.Possession = ms.Possession.Opponent()
	ms.ActiveZone = zone
	interceptor.Stats.Intercepts++
	interceptor.Stats.RatingBase += 0.12
	sim.flipMomentumOnTurnover(ms)
	sim.boostMomentum(ms, zone, 0.06)

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

func (sim *Simulator) decayMomentum(ms *domain.MatchState) {
	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			ms.ZoneMomentum[r][c] *= 0.82
			if ms.ZoneMomentum[r][c] < 0.01 && ms.ZoneMomentum[r][c] > -0.01 {
				ms.ZoneMomentum[r][c] = 0
			}
		}
	}
}

func (sim *Simulator) boostMomentum(ms *domain.MatchState, zone [2]int, amount float64) {
	ms.ZoneMomentum[zone[0]][zone[1]] += amount
	if ms.ZoneMomentum[zone[0]][zone[1]] > 1.5 {
		ms.ZoneMomentum[zone[0]][zone[1]] = 1.5
	}
}

func (sim *Simulator) flipMomentumOnTurnover(ms *domain.MatchState) {
	// When possession changes, momentum inverts (what was good for attacker is now bad)
	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			ms.ZoneMomentum[r][c] *= -0.5
		}
	}
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
				if sim.r.Float64() < 0.6 {
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

	// Small chance of own goal on bad clearance
	ownGoalChance := 0.005
	if defender.GetAttrByName("COM") < 10 {
		ownGoalChance = 0.015
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
	sim.flipMomentumOnTurnover(ms)
	sim.boostMomentum(ms, [2]int{2, 1}, 0.05)
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

	// Card check
	cardResult := ""
	aggression := oppTeam.Tactics.TacklingAggression
	yellowThreshold := 0.08 + float64(aggression)*0.04
	redThreshold := 0.01 + float64(aggression)*0.008

	roll := sim.r.Float64()
	if roll < redThreshold && !fouler.RedCard {
		fouler.RedCard = true
		fouler.Stats.RedCards++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.RedCards++
		} else {
			ms.HomeStats.RedCards++
		}
		cardResult = "red"
		fouler.Stats.RatingBase -= 2.0
	} else if roll < yellowThreshold && fouler.YellowCards < 2 && !fouler.RedCard {
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
	ms.ZoneMomentum[zone[0]][zone[1]] -= 0.04

	// After foul, free kick — possession stays, zone advances slightly
	if sim.r.Float64() < 0.7 {
		if zone[0] > 0 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
		}
	}
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
	// 2nd half kickoff
	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKickoff,
		Team:         ms.AwayTeam.Name,
		OpponentName: ms.HomeTeam.Name,
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
				Tackles:       ps.Tackles,
				Interceptions: ps.Intercepts,
				Saves:         ps.Saves,
				Fouls:         ps.Fouls,
				YellowCards:   ps.YellowCards,
				RedCards:      ps.RedCards,
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
