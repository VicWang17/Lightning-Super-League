package engine

import (
	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ============================================================
// Phase 1: Simple 1v1 Event Handlers
// ============================================================

// doSwitchPlayEvent — lateral transfer across the field (B05 横传调度)
func (sim *Simulator) doSwitchPlayEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	holder := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcSwitchPlayAttack(holder)
	defVal := CalcSwitchPlayDefense(defender)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*2.0, defVal, sim.r, holder.GetAttrByName("COM"))

	ConsumeStamina(holder, StaminaCost(config.EventSwitchPlay))
	holder.Stats.Passes++

	var target *domain.PlayerRuntime
	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		defender.Stats.RatingBase += 0.1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.06)
	} else {
		// Switch to opposite wing
		newCol := 2 - zone[1]
		ms.ActiveZone = [2]int{zone[0], newCol}
		target = SelectPlayerByZone(possTeam, ms.ActiveZone, sim.r)
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.03)
	}

	ev := domain.MatchEvent{
		Type:         config.EventSwitchPlay,
		Team:         possTeam.Name,
		PlayerID:     holder.PlayerID,
		PlayerName:   holder.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	}
	if target != nil {
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}
	sim.addEvent(ms, ev)
}

// doLobPassEvent — chip/lob over defense (C04 挑传身后)
func (sim *Simulator) doLobPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	passer := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcLobPassAttack(passer)
	defVal := CalcLobPassDefense(defender)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*2.0, defVal, sim.r, passer.GetAttrByName("COM"))

	ConsumeStamina(passer, StaminaCost(config.EventLobPass))
	passer.Stats.Passes++

	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		defender.Stats.RatingBase += 0.1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.06)
	} else {
		// Ball reaches front zone center; chain to header or close shot
		ms.ActiveZone = [2]int{0, 1}
		target := SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.05)
		// Emit lob pass event with target before chaining to header
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventLobPass,
			Team:         possTeam.Name,
			PlayerID:     passer.PlayerID,
			PlayerName:   passer.Name,
			OpponentID:   defender.PlayerID,
			OpponentName: defender.Name,
			Player2ID:    target.PlayerID,
			Player2Name:  target.Name,
			Zone:         zoneStr(zone),
			Result:       result,
		})
		// Chain to header duel
		sim.doHeaderDuel(ms, possTeam, oppTeam)
		return
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventLobPass,
		Team:         possTeam.Name,
		PlayerID:     passer.PlayerID,
		PlayerName:   passer.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doPassOverTopEvent — high ball over the defense (C05 过顶球)
func (sim *Simulator) doPassOverTopEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	passer := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcPassOverTopAttack(passer)
	defVal := CalcPassOverTopDefense(defender)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*2.0, defVal, sim.r, passer.GetAttrByName("COM"))

	ConsumeStamina(passer, StaminaCost(config.EventPassOverTop))
	passer.Stats.Passes++

	var target *domain.PlayerRuntime
	result := "success"
	if !success {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		defender.Stats.RatingBase += 0.1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.06)
	} else {
		// Ball reaches front zone; select new attacker
		passer.Stats.KeyPasses++
		if possTeam == ms.HomeTeam {
			ms.HomeStats.KeyPasses++
		} else {
			ms.AwayStats.KeyPasses++
		}
		ms.ActiveZone = [2]int{0, 1}
		target = SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.05)
	}

	ev := domain.MatchEvent{
		Type:         config.EventPassOverTop,
		Team:         possTeam.Name,
		PlayerID:     passer.PlayerID,
		PlayerName:   passer.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	}
	if target != nil {
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}
	sim.addEvent(ms, ev)
}

// doBlockPassEvent — block passing route before ball is played (D11 堵截传球路线)
func (sim *Simulator) doBlockPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	// This event is triggered from the defending team's perspective
	// but we keep possession team as the "attacking" context for event recording
	blocker := SelectDefender(oppTeam, zone, sim.r)
	holder := ms.BallHolder

	atkVal := CalcBlockPassAttack(blocker)
	defVal := CalcBlockPassDefense(holder)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal, defVal+ctrl*1.5, sim.r)

	ConsumeStamina(blocker, StaminaCost(config.EventBlockPass))

	result := "success"
	if success {
		// Blocker intercepts the intended pass
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = blocker
		blocker.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		blocker.Stats.RatingBase += 0.2
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.08)
		sim.boostGlobalMomentum(ms, 0.02)
	} else {
		result = "fail"
		// Pass still goes through, but less accurate — reduce control
		sim.applyControlShift(ms, zone, -0.03)
		holder.Stats.RatingBase += 0.05
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventBlockPass,
		Team:         oppTeam.Name,
		PlayerID:     blocker.PlayerID,
		PlayerName:   blocker.Name,
		OpponentID:   holder.PlayerID,
		OpponentName: holder.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doOneOnOneEvent — special shot scenario: attacker 1v1 vs keeper (C13 单刀球)
func (sim *Simulator) doOneOnOneEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	shooter := ms.BallHolder
	keeper := oppTeam.GetGK()

	atkVal := CalcOneOnOneAttack(shooter)
	defVal := CalcOneOnOneDefense(keeper)

	com := shooter.GetAttrByName("COM")
	success := ResolveDuel(atkVal, defVal+0.3, sim.r, com)

	ConsumeStamina(shooter, StaminaCost(config.EventOneOnOne))
	shooter.Stats.Shots++

	if ms.Possession == domain.SideHome {
		ms.HomeStats.Shots++
	} else {
		ms.AwayStats.Shots++
	}

	result := "saved"
	if success {
		result = "goal"
		shooter.Stats.Goals++
		shooter.Stats.ShotsOnTarget++
		shooter.Stats.RatingBase += 1.2
		keeper.Stats.RatingBase -= 0.6
		if ms.Possession == domain.SideHome {
			ms.Score.Home++
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.Score.Away++
			ms.AwayStats.ShotsOnTarget++
		}
		sim.applyControlShift(ms, zone, 0.15)
		sim.boostGlobalMomentum(ms, 0.04)
	} else {
		keeper.Stats.Saves++
		if ms.Possession == domain.SideHome {
			ms.AwayStats.Saves++
		} else {
			ms.HomeStats.Saves++
		}
		keeper.Stats.RatingBase += 0.4
		shooter.Stats.ShotsOnTarget++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.ShotsOnTarget++
		} else {
			ms.AwayStats.ShotsOnTarget++
		}
		sim.applyControlShift(ms, zone, 0.05)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventOneOnOne,
		Team:         possTeam.Name,
		PlayerID:     shooter.PlayerID,
		PlayerName:   shooter.Name,
		OpponentID:   keeper.PlayerID,
		OpponentName: keeper.Name,
		Zone:         zoneStr(zone),
		Result:       result,
		Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
	})

	if result == "goal" {
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventGoal,
			Team:         possTeam.Name,
			PlayerID:     shooter.PlayerID,
			PlayerName:   shooter.Name,
			Score:        &domain.Score{Home: ms.Score.Home, Away: ms.Score.Away},
		})
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{1, 1}
		ms.BallHolder = sim.selectKickoffTaker(ms.Team(ms.Possession))
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKickoff,
			Team:         ms.Team(ms.Possession).Name,
			OpponentName: ms.OppTeam(ms.Possession).Name,
			PlayerName:   ms.BallHolder.Name,
		})
	} else {
		// Keeper save after 1v1
		sim.addEvent(ms, domain.MatchEvent{
			Type:         config.EventKeeperSave,
			Team:         oppTeam.Name,
			PlayerID:     keeper.PlayerID,
			PlayerName:   keeper.Name,
			OpponentID:   shooter.PlayerID,
			OpponentName: shooter.Name,
		})
		ms.Possession = ms.Possession.Opponent()
		ms.ActiveZone = [2]int{2, 1}
		ms.BallHolder = keeper
	}
}

// doCoverDefenseEvent — positional cover when attack has high control (D07 补位防守)
// This is triggered as an interrupt when control is very high.
func (sim *Simulator) doCoverDefenseEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	defender := SelectDefender(oppTeam, zone, sim.r)
	attacker := ms.BallHolder

	atkVal := CalcCoverDefenseAttack(defender)
	defVal := CalcCoverDefenseDefense(attacker)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal, defVal+ctrl*2.0, sim.r, defender.GetAttrByName("COM"))

	ConsumeStamina(defender, StaminaCost(config.EventCoverDefense))

	result := "success"
	if success {
		// Cover succeeds: drastically reduce attacker's control
		sim.applyControlShift(ms, zone, -0.4)
		defender.Stats.RatingBase += 0.25
		sim.boostGlobalMomentum(ms, -0.03)
	} else {
		result = "fail"
		// Cover fails: attacker maintains high control, gets slight boost
		sim.applyControlShift(ms, zone, 0.1)
		attacker.Stats.RatingBase += 0.1
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventCoverDefense,
		Team:         oppTeam.Name,
		PlayerID:     defender.PlayerID,
		PlayerName:   defender.Name,
		OpponentID:   attacker.PlayerID,
		OpponentName: attacker.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doShotBlockEvent — defender blocks a shot (D02 封堵射门)
// This is emitted independently from within doShotEvent when a block occurs.
func (sim *Simulator) doShotBlockEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int, blocker, shooter *domain.PlayerRuntime) {
	ConsumeStamina(blocker, StaminaCost(config.EventShotBlock))

	blocker.Stats.RatingBase += 0.3
	blocker.Stats.Blocks++
	if ms.Possession == domain.SideHome {
		ms.AwayStats.Tackles++
		ms.AwayStats.TacklesSucc++
		ms.AwayStats.Blocks++
	} else {
		ms.HomeStats.Tackles++
		ms.HomeStats.TacklesSucc++
		ms.HomeStats.Blocks++
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventShotBlock,
		Team:         oppTeam.Name,
		PlayerID:     blocker.PlayerID,
		PlayerName:   blocker.Name,
		OpponentID:   shooter.PlayerID,
		OpponentName: shooter.Name,
		Zone:         zoneStr(zone),
		Result:       "success",
	})

	// After block, ball often goes out or becomes contested
	// 60% chance: defender clears / gains possession
	// 40% chance: ball remains in play, possession switches
	if sim.r.Float64() < 0.6 {
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = blocker
		// Ball stays in current zone or drops back slightly
		if zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] + 1, zone[1]}
		}
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.1)
	} else {
		// Scramble: random possession
		if sim.r.Float64() < 0.5 {
			ms.Possession = ms.Possession.Opponent()
			ms.BallHolder = blocker
		} else {
			ms.BallHolder = SelectPlayerByZone(possTeam, zone, sim.r)
		}
		sim.applyControlShift(ms, zone, 0.02)
	}
}

// ============================================================
// Helper for cover defense trigger probability
// ============================================================

func (sim *Simulator) shouldTriggerCoverDefense(ms *domain.MatchState, oppTeam *domain.TeamRuntime, zone [2]int) bool {
	ctrl := ms.EffectiveControl(zone)
	if ctrl < 0.6 {
		return false
	}
	// Trigger probability scales with opponent DEC + DEF
	defender := SelectDefender(oppTeam, zone, sim.r)
	coverSkill := defender.GetAttrByName("DEC")*0.4 + defender.GetAttrByName("DEF")*0.6
	baseProb := 0.15 + (coverSkill-10.0)/30.0*0.25
	if baseProb < 0.05 {
		baseProb = 0.05
	}
	if baseProb > 0.50 {
		baseProb = 0.50
	}
	return sim.r.Float64() < baseProb
}

// ============================================================
// Phase 2: Medium Complexity Event Handlers
// ============================================================

// doGoalKickEvent — goalkeeper kicks from goal area (A02 球门球)
func (sim *Simulator) doGoalKickEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	resetControlShift(ms)
	keeper := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	// Setup phase: keeper places ball, organizes defense
	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventGoalKickSetup,
		Team:       possTeam.Name,
		PlayerID:   keeper.PlayerID,
		PlayerName: keeper.Name,
		Zone:       zoneStr(zone),
	})
	ms.AdvanceClock(2.0 + sim.r.Float64()*2.0)

	// Goal kick: keeper passes/kicks to teammates
	atkVal := keeper.GetAttrByName("PAS")*0.5 +
		keeper.GetAttrByName("STR")*0.3 +
		keeper.GetAttrByName("SAV")*0.2
	defVal := defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("STR")*0.3 +
		defender.GetAttrByName("SPD")*0.2

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(keeper, StaminaCost(config.EventGoalKick))

	var target *domain.PlayerRuntime
	result := "success"
	if success {
		// Ball reaches midfield or back zone
		if sim.r.Float64() < 0.6 {
			ms.ActiveZone = [2]int{1, 1}
		} else {
			ms.ActiveZone = [2]int{2, 1}
		}
		target = SelectPlayerByZone(possTeam, ms.ActiveZone, sim.r)
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.03)
	} else {
		result = "fail"
		// Goal kick intercepted or goes out
		if sim.r.Float64() < 0.5 {
			ms.Possession = ms.Possession.Opponent()
			ms.BallHolder = defender
			sim.flipGlobalMomentum(ms)
			sim.applyControlShift(ms, zone, 0.05)
		} else {
			// Ball stays in play, re-select attacker in back
			ms.ActiveZone = [2]int{2, 1}
			target = SelectPlayerByZone(possTeam, ms.ActiveZone, sim.r)
			ms.BallHolder = target
		}
	}

	ev := domain.MatchEvent{
		Type:         config.EventGoalKick,
		Team:         possTeam.Name,
		PlayerID:     keeper.PlayerID,
		PlayerName:   keeper.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	}
	if target != nil {
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}
	sim.addEvent(ms, ev)
}

// doThrowInEvent — sideline throw-in (A03 界外球)
func (sim *Simulator) doThrowInEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	resetControlShift(ms)
	// Throw-in taker: usually SB or WF on that side
	thrower := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	// Setup phase: retrieving ball, teammates positioning
	sim.addEvent(ms, domain.MatchEvent{
		Type:       config.EventThrowInSetup,
		Team:       possTeam.Name,
		PlayerID:   thrower.PlayerID,
		PlayerName: thrower.Name,
		Zone:       zoneStr(zone),
	})
	ms.AdvanceClock(1.5 + sim.r.Float64()*1.5)

	atkVal := thrower.GetAttrByName("PAS")*0.4 +
		thrower.GetAttrByName("STR")*0.4 +
		thrower.GetAttrByName("SPD")*0.2
	defVal := defender.GetAttrByName("HEA")*0.4 +
		defender.GetAttrByName("SPD")*0.4 +
		defender.GetAttrByName("STR")*0.2

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(thrower, StaminaCost(config.EventThrowIn))

	var target *domain.PlayerRuntime
	result := "success"
	if success {
		// Ball reaches teammate in same or adjacent zone
		target = SelectPlayerByZone(possTeam, zone, sim.r)
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.03)
	} else {
		result = "fail"
		// Throw-in intercepted or goes to opponent
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.05)
	}

	ev := domain.MatchEvent{
		Type:         config.EventThrowIn,
		Team:         possTeam.Name,
		PlayerID:     thrower.PlayerID,
		PlayerName:   thrower.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	}
	if target != nil {
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}
	sim.addEvent(ms, ev)
}

// doKeeperShortPassEvent — goalkeeper short pass from back (B10 门将短传组织)
func (sim *Simulator) doKeeperShortPassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	keeper := ms.BallHolder
	pressure := SelectDefender(oppTeam, zone, sim.r)
	target := SelectPlayerByZone(possTeam, zone, sim.r)

	atkVal := keeper.GetAttrByName("PAS")*0.5 +
		keeper.GetAttrByName("ACC")*0.3 +
		keeper.GetAttrByName("DEC")*0.2
	defVal := pressure.GetAttrByName("SPD")*0.4 +
		pressure.GetAttrByName("TKL")*0.4 +
		pressure.GetAttrByName("STA")*0.2

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(keeper, StaminaCost(config.EventKeeperShortPass))

	result := "success"
	if success {
		keeper.Stats.Passes++
		keeper.Stats.PassesSucc++
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.03)
	} else {
		result = "fail"
		keeper.Stats.Passes++
		// Pressure intercepts or forces error
		if sim.r.Float64() < 0.6 {
			ms.Possession = ms.Possession.Opponent()
			ms.BallHolder = pressure
			pressure.Stats.Intercepts++
			if ms.Possession == domain.SideHome {
				ms.HomeStats.Interceptions++
			} else {
				ms.AwayStats.Interceptions++
			}
			pressure.Stats.RatingBase += 0.15
			sim.flipGlobalMomentum(ms)
			sim.applyControlShift(ms, zone, 0.08)
		} else {
			// Scramble: random possession in back
			if sim.r.Float64() < 0.5 {
				ms.BallHolder = SelectPlayerByZone(possTeam, zone, sim.r)
			} else {
				ms.Possession = ms.Possession.Opponent()
				ms.BallHolder = pressure
				sim.flipGlobalMomentum(ms)
			}
			sim.applyControlShift(ms, zone, 0.04)
		}
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventKeeperShortPass,
		Team:         possTeam.Name,
		PlayerID:     keeper.PlayerID,
		PlayerName:   keeper.Name,
		OpponentID:   pressure.PlayerID,
		OpponentName: pressure.Name,
		Player2ID:    target.PlayerID,
		Player2Name:  target.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doKeeperThrowEvent — goalkeeper quick hand throw (B11 门将手抛球)
func (sim *Simulator) doKeeperThrowEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	keeper := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := keeper.GetAttrByName("PAS")*0.4 +
		keeper.GetAttrByName("REF")*0.2 +
		keeper.GetAttrByName("DEC")*0.4
	defVal := defender.GetAttrByName("SPD")*0.5 +
		defender.GetAttrByName("STA")*0.3 +
		defender.GetAttrByName("DEF")*0.2

	success := ResolveDuel(atkVal, defVal, sim.r)
	ConsumeStamina(keeper, StaminaCost(config.EventKeeperThrow))

	var target *domain.PlayerRuntime
	result := "success"
	if success {
		keeper.Stats.Passes++
		keeper.Stats.PassesSucc++
		// Hand throw advances to midfield quickly
		ms.ActiveZone = [2]int{1, 1}
		target = SelectPlayerByZone(possTeam, ms.ActiveZone, sim.r)
		ms.BallHolder = target
		sim.applyControlShift(ms, zone, 0.05)
	} else {
		result = "fail"
		keeper.Stats.Passes++
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		defender.Stats.RatingBase += 0.1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.06)
	}

	ev := domain.MatchEvent{
		Type:         config.EventKeeperThrow,
		Team:         possTeam.Name,
		PlayerID:     keeper.PlayerID,
		PlayerName:   keeper.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	}
	if target != nil {
		ev.Player2ID = target.PlayerID
		ev.Player2Name = target.Name
	}
	sim.addEvent(ms, ev)
}

// doCounterAttackEvent — rapid forward push on counter (C14 快速反击推进)
func (sim *Simulator) doCounterAttackEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	carrier := ms.BallHolder
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := carrier.GetAttrByName("DRI")*0.35 +
		carrier.GetAttrByName("SPD")*0.35 +
		carrier.GetAttrByName("BAL")*0.15 +
		carrier.GetAttrByName("PAS")*0.15
	defVal := defender.GetAttrByName("DEF")*0.35 +
		defender.GetAttrByName("SPD")*0.30 +
		defender.GetAttrByName("TKL")*0.25 +
		defender.GetAttrByName("STR")*0.10

	success := ResolveDuel(atkVal, defVal, sim.r, carrier.GetAttrByName("COM"))
	ConsumeStamina(carrier, StaminaCost(config.EventCounterAttack))

	result := "success"
	if success {
		// Rapid zone advancement
		if zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
			if ms.ActiveZone[0] < 0 {
				ms.ActiveZone[0] = 0
			}
		}
		// Carrier maintains possession after successful counter
		carrier.Stats.RatingBase += 0.15
		// Counter boost decays
		ms.CounterBoostRemaining[int(ms.Possession)]--
		if ms.CounterBoostRemaining[int(ms.Possession)] < 0 {
			ms.CounterBoostRemaining[int(ms.Possession)] = 0
		}
		sim.applyControlShift(ms, zone, 0.1)
		sim.boostGlobalMomentum(ms, 0.03)
	} else {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Tackles++
		defender.Stats.TacklesSucc++
		defender.Stats.RatingBase += 0.2
		ms.CounterBoostRemaining[int(ms.Possession)] = 0 // counter broken
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.08)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventCounterAttack,
		Team:         possTeam.Name,
		PlayerID:     carrier.PlayerID,
		PlayerName:   carrier.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// ============================================================
// Phase 3: Multi-Player Event Handlers
// ============================================================

// doOverlapEvent — fullback overlaps with winger (B06 边后卫套边短传)
func (sim *Simulator) doOverlapEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	primary := ms.BallHolder
	secondary := SelectSecondAttacker(possTeam, primary, zone, sim.r)
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcOverlapAttack(primary, secondary)
	defVal := CalcOverlapDefense(defender)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*1.5, defVal, sim.r)
	ConsumeStamina(primary, StaminaCost(config.EventOverlap)*0.6)
	ConsumeStamina(secondary, StaminaCost(config.EventOverlap)*0.6)

	result := "success"
	if success {
		primary.Stats.Passes++
		primary.Stats.PassesSucc++
		// Control boost for successful overlap
		sim.applyControlShift(ms, zone, 0.3)
		// Chain to cross or close shot
		if sim.r.Float64() < 0.6 {
			ms.BallHolder = secondary
			// Emit the overlap event before chaining to cross
			sim.addEvent(ms, domain.MatchEvent{
				Type:         config.EventOverlap,
				Team:         possTeam.Name,
				PlayerID:     primary.PlayerID,
				PlayerName:   primary.Name,
				Player2ID:    secondary.PlayerID,
				Player2Name:  secondary.Name,
				OpponentID:   defender.PlayerID,
				OpponentName: defender.Name,
				Zone:         zoneStr(zone),
				Result:       result,
			})
			sim.doCrossEvent(ms, possTeam, oppTeam, zone)
			return
		} else {
			ms.ActiveZone = [2]int{0, 1}
			ms.BallHolder = SelectPlayerByZone(possTeam, [2]int{0, 1}, sim.r)
			// Emit the overlap event before chaining to shot
			sim.addEvent(ms, domain.MatchEvent{
				Type:         config.EventOverlap,
				Team:         possTeam.Name,
				PlayerID:     primary.PlayerID,
				PlayerName:   primary.Name,
				Player2ID:    secondary.PlayerID,
				Player2Name:  secondary.Name,
				OpponentID:   defender.PlayerID,
				OpponentName: defender.Name,
				Zone:         zoneStr(zone),
				Result:       result,
			})
			sim.doShotEvent(ms, possTeam, oppTeam, [2]int{0, 1}, "close")
			return
		}
	} else {
		result = "fail"
		// High penalty: too many attackers committed
		sim.applyControlShift(ms, zone, -0.3)
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Tackles++
		defender.Stats.TacklesSucc++
		defender.Stats.RatingBase += 0.2
		sim.flipGlobalMomentum(ms)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventOverlap,
		Team:         possTeam.Name,
		PlayerID:     primary.PlayerID,
		PlayerName:   primary.Name,
		Player2ID:    secondary.PlayerID,
		Player2Name:  secondary.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doTrianglePassEvent — three-player triangle passing (B07 三角传递配合)
func (sim *Simulator) doTrianglePassEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	p1 := ms.BallHolder
	p2 := SelectSecondAttacker(possTeam, p1, zone, sim.r)
	p3 := SelectSecondAttacker(possTeam, p2, zone, sim.r)
	if p3.PlayerID == p1.PlayerID {
		p3 = p2
	}

	d1 := SelectDefender(oppTeam, zone, sim.r)
	d2 := SelectSecondDefender(oppTeam, d1, zone, sim.r)

	atkVal := CalcTriangleAttack(p1, p2, p3)
	defVal := CalcTriangleDefense(d1, d2)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*1.5, defVal, sim.r)
	ConsumeStamina(p1, StaminaCost(config.EventTrianglePass)*0.4)
	ConsumeStamina(p2, StaminaCost(config.EventTrianglePass)*0.4)
	ConsumeStamina(p3, StaminaCost(config.EventTrianglePass)*0.4)

	result := "success"
	if success {
		p1.Stats.Passes++
		p1.Stats.PassesSucc++
		p2.Stats.Passes++
		p2.Stats.PassesSucc++
		// Advance 2 zones forward
		newRow := zone[0] - 2
		if newRow < 0 {
			newRow = 0
		}
		ms.ActiveZone = [2]int{newRow, 1}
		ms.BallHolder = p3
		sim.applyControlShift(ms, zone, 0.25)
	} else {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = d1
		d1.Stats.Intercepts++
		if ms.Possession == domain.SideHome {
			ms.HomeStats.Interceptions++
		} else {
			ms.AwayStats.Interceptions++
		}
		d1.Stats.RatingBase += 0.2
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, -0.3)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventTrianglePass,
		Team:         possTeam.Name,
		PlayerID:     p1.PlayerID,
		PlayerName:   p1.Name,
		Player2ID:    p3.PlayerID,
		Player2Name:  p3.Name,
		OpponentID:   d1.PlayerID,
		OpponentName: d1.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doOneTwoEvent — give-and-go passing (C06 二过一配合)
func (sim *Simulator) doOneTwoEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	p1 := ms.BallHolder
	p2 := SelectSecondAttacker(possTeam, p1, zone, sim.r)
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcOneTwoAttack(p1, p2)
	defVal := CalcOneTwoDefense(defender)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*1.5, defVal, sim.r)
	ConsumeStamina(p1, StaminaCost(config.EventOneTwo)*0.5)
	ConsumeStamina(p2, StaminaCost(config.EventOneTwo)*0.5)

	result := "success"
	if success {
		p1.Stats.Passes++
		p1.Stats.PassesSucc++
		// Control boost
		sim.applyControlShift(ms, zone, 0.3)
		// Chain to close shot or through ball
		if zone[0] == 0 {
			ms.BallHolder = p2
			// Emit the one-two event before chaining to shot
			sim.addEvent(ms, domain.MatchEvent{
				Type:         config.EventOneTwo,
				Team:         possTeam.Name,
				PlayerID:     p1.PlayerID,
				PlayerName:   p1.Name,
				Player2ID:    p2.PlayerID,
				Player2Name:  p2.Name,
				OpponentID:   defender.PlayerID,
				OpponentName: defender.Name,
				Zone:         zoneStr(zone),
				Result:       result,
			})
			sim.doShotEvent(ms, possTeam, oppTeam, zone, "close")
			return
		} else {
			ms.ActiveZone = [2]int{zone[0] - 1, zone[1]}
			if ms.ActiveZone[0] < 0 {
				ms.ActiveZone[0] = 0
			}
			ms.BallHolder = p2
			sim.applyControlShift(ms, zone, 0.1)
		}
	} else {
		result = "fail"
		// High penalty
		sim.applyControlShift(ms, zone, -0.4)
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Tackles++
		defender.Stats.TacklesSucc++
		defender.Stats.RatingBase += 0.2
		sim.flipGlobalMomentum(ms)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventOneTwo,
		Team:         possTeam.Name,
		PlayerID:     p1.PlayerID,
		PlayerName:   p1.Name,
		Player2ID:    p2.PlayerID,
		Player2Name:  p2.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doCrossRunEvent — two attackers swap positions (C07 交叉跑位)
func (sim *Simulator) doCrossRunEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	p1 := ms.BallHolder
	p2 := SelectSecondAttacker(possTeam, p1, zone, sim.r)
	defender := SelectDefender(oppTeam, zone, sim.r)

	atkVal := CalcCrossRunAttack(p1, p2)
	defVal := CalcCrossRunDefense(defender)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal+ctrl*1.5, defVal, sim.r)
	ConsumeStamina(p1, StaminaCost(config.EventCrossRun)*0.5)
	ConsumeStamina(p2, StaminaCost(config.EventCrossRun)*0.5)

	result := "success"
	if success {
		// Confusion bonus: next shot gets boosted
		ms.BallHolder = p2
		// Set a flag for next shot bonus (we use a simple field on simulator)
		// Since we can't easily pass state between events, apply immediate control boost
		sim.applyControlShift(ms, zone, 0.35)
		sim.boostGlobalMomentum(ms, 0.02)
	} else {
		result = "fail"
		// High penalty
		sim.applyControlShift(ms, zone, -0.5)
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = defender
		defender.Stats.Tackles++
		defender.Stats.TacklesSucc++
		defender.Stats.RatingBase += 0.2
		sim.flipGlobalMomentum(ms)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventCrossRun,
		Team:         possTeam.Name,
		PlayerID:     p1.PlayerID,
		PlayerName:   p1.Name,
		Player2ID:    p2.PlayerID,
		Player2Name:  p2.Name,
		OpponentID:   defender.PlayerID,
		OpponentName: defender.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doDoubleTeamEvent — two defenders double-team attacker (D03 包夹防守)
func (sim *Simulator) doDoubleTeamEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	d1 := SelectDefender(oppTeam, zone, sim.r)
	d2 := SelectSecondDefender(oppTeam, d1, zone, sim.r)
	attacker := ms.BallHolder

	atkVal := CalcDoubleTeamAttack(d1, d2)
	defVal := CalcDoubleTeamDefense(attacker)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal, defVal+ctrl*1.0, sim.r)
	ConsumeStamina(d1, StaminaCost(config.EventDoubleTeam)*0.5)
	ConsumeStamina(d2, StaminaCost(config.EventDoubleTeam)*0.5)

	result := "success"
	if success {
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = d1
		d1.Stats.Tackles++
		d1.Stats.TacklesSucc++
		d1.Stats.RatingBase += 0.2
		d2.Stats.RatingBase += 0.1
		attacker.Stats.RatingBase -= 0.1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.1)
	} else {
		result = "fail"
		// Attacker escapes double team — big boost
		attacker.Stats.RatingBase += 0.25
		sim.applyControlShift(ms, zone, 0.25)
		sim.boostGlobalMomentum(ms, 0.03)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventDoubleTeam,
		Team:         oppTeam.Name,
		PlayerID:     d1.PlayerID,
		PlayerName:   d1.Name,
		Player2ID:    d2.PlayerID,
		Player2Name:  d2.Name,
		OpponentID:   attacker.PlayerID,
		OpponentName: attacker.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// doPressTogetherEvent — two defenders press together (D09 协同逼抢)
func (sim *Simulator) doPressTogetherEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	d1 := SelectDefender(oppTeam, zone, sim.r)
	d2 := SelectSecondDefender(oppTeam, d1, zone, sim.r)
	holder := ms.BallHolder

	atkVal := CalcPressTogetherAttack(d1, d2)
	defVal := CalcPressTogetherDefense(holder)

	ctrl := ms.EffectiveControl(zone)
	success := ResolveDuel(atkVal, defVal+ctrl*1.0, sim.r)
	ConsumeStamina(d1, StaminaCost(config.EventPressTogether)*0.5)
	ConsumeStamina(d2, StaminaCost(config.EventPressTogether)*0.5)

	result := "success"
	if success {
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = d1
		d1.Stats.Tackles++
		d1.Stats.TacklesSucc++
		d1.Stats.RatingBase += 0.15
		d2.Stats.RatingBase += 0.1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.08)
	} else {
		result = "fail"
		// Holder escapes press
		holder.Stats.RatingBase += 0.15
		// Forced back pass
		if zone[0] < 2 {
			ms.ActiveZone = [2]int{zone[0] + 1, zone[1]}
		}
		sim.applyControlShift(ms, zone, 0.15)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventPressTogether,
		Team:         oppTeam.Name,
		PlayerID:     d1.PlayerID,
		PlayerName:   d1.Name,
		Player2ID:    d2.PlayerID,
		Player2Name:  d2.Name,
		OpponentID:   holder.PlayerID,
		OpponentName: holder.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}

// ============================================================
// Phase 4: Injury & Rare Events
// ============================================================

// doDropBallEvent — contested drop ball, very rare (A08 坠球恢复)
func (sim *Simulator) doDropBallEvent(ms *domain.MatchState, possTeam, oppTeam *domain.TeamRuntime, zone [2]int) {
	p1 := SelectPlayerByZone(possTeam, zone, sim.r)
	d1 := SelectDefender(oppTeam, zone, sim.r)

	// Simple duel: who gets to the ball first
	atkVal := p1.GetAttrByName("SPD")*0.35 + p1.GetAttrByName("STR")*0.25 + p1.GetAttrByName("HEA")*0.25 + p1.GetAttrByName("BAL")*0.15
	defVal := d1.GetAttrByName("SPD")*0.35 + d1.GetAttrByName("STR")*0.25 + d1.GetAttrByName("HEA")*0.25 + d1.GetAttrByName("BAL")*0.15

	success := ResolveDuel(atkVal, defVal, sim.r)

	result := "success"
	if success {
		ms.BallHolder = p1
		sim.applyControlShift(ms, zone, 0.02)
	} else {
		result = "fail"
		ms.Possession = ms.Possession.Opponent()
		ms.BallHolder = d1
		sim.flipGlobalMomentum(ms)
		sim.applyControlShift(ms, zone, 0.02)
	}

	sim.addEvent(ms, domain.MatchEvent{
		Type:         config.EventDropBall,
		Team:         possTeam.Name,
		PlayerID:     p1.PlayerID,
		PlayerName:   p1.Name,
		OpponentID:   d1.PlayerID,
		OpponentName: d1.Name,
		Zone:         zoneStr(zone),
		Result:       result,
	})
}
