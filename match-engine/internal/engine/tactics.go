package engine

import (
	"math/rand/v2"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// attackRouteControlDelta returns the control matrix delta for a given route.
// Positive values favor the route's preferred columns.
func attackRouteControlDelta(route string, c int) float64 {
	switch route {
	case "left":
		if c == 0 {
			return 0.08
		}
		if c == 2 {
			return -0.04
		}
	case "right":
		if c == 2 {
			return 0.08
		}
		if c == 0 {
			return -0.04
		}
	case "center":
		if c == 1 {
			return 0.08
		}
		return -0.03
	case "both_wings":
		if c == 0 || c == 2 {
			return 0.06
		}
		return -0.04
	}
	return 0.0
}

// instructionControlDelta adds control matrix influence from team instructions,
// primarily attack route. Home route adds positive delta; away route subtracts.
func instructionControlDelta(home, away *domain.TeamRuntime, r, c int) float64 {
	delta := 0.0
	if home != nil {
		delta += attackRouteControlDelta(home.Instructions().InPossession.AttackRoute, c)
	}
	if away != nil {
		delta -= attackRouteControlDelta(away.Instructions().InPossession.AttackRoute, c)
	}
	return delta
}

// attackRouteWeightMod adjusts candidate event weights for the possession team's
// attack route.
func attackRouteWeightMod(route string, eventType string) float64 {
	wingEvents := map[string]bool{
		config.EventWingBreak:  true,
		config.EventOverlap:    true,
		config.EventCross:      true,
		config.EventSwitchPlay: true,
		config.EventCutInside:  true,
	}
	centerEvents := map[string]bool{
		config.EventPivotPass:    true,
		config.EventTrianglePass: true,
		config.EventOneTwo:       true,
		config.EventThroughBall:  true,
		config.EventBuildUp:      true,
	}

	switch route {
	case "left", "right":
		if wingEvents[eventType] {
			return 1.3
		}
		if centerEvents[eventType] {
			return 0.85
		}
	case "center":
		if centerEvents[eventType] {
			return 1.3
		}
		if wingEvents[eventType] {
			return 0.85
		}
	case "both_wings":
		if wingEvents[eventType] || eventType == config.EventSwitchPlay {
			return 1.25
		}
		if centerEvents[eventType] {
			return 0.9
		}
	}
	return 1.0
}

// passingRiskWeightMod adjusts candidate weights based on passing_risk.
// risk 0 = very safe, risk 4 = very risky.
func passingRiskWeightMod(risk int, eventType string) float64 {
	safeEvents := map[string]bool{
		config.EventShortPass: true,
		config.EventBackPass:  true,
		config.EventPivotPass: true,
		config.EventHoldBall:  true,
	}
	riskyEvents := map[string]bool{
		config.EventThroughBall: true,
		config.EventPassOverTop: true,
		config.EventLongPass:    true,
		config.EventLobPass:     true,
	}

	if risk <= 1 {
		if safeEvents[eventType] {
			return 1.0 + float64(1-risk)*0.15 + 0.1
		}
		if riskyEvents[eventType] {
			return 1.0 - float64(1-risk)*0.15 - 0.15
		}
	}
	if risk >= 3 {
		if riskyEvents[eventType] {
			return 1.0 + float64(risk-3)*0.15 + 0.2
		}
		if safeEvents[eventType] {
			return 1.0 - float64(risk-3)*0.15 - 0.1
		}
	}
	return 1.0
}

// buildUpStyleWeightMod adjusts candidate weights based on build_up_style.
func buildUpStyleWeightMod(style string, eventType string) float64 {
	switch style {
	case "short":
		switch eventType {
		case config.EventKeeperShortPass, config.EventShortPass, config.EventBuildUp, config.EventPivotPass:
			return 1.25
		case config.EventLongPass, config.EventPassOverTop, config.EventThroughBall:
			return 0.85
		}
	case "direct":
		switch eventType {
		case config.EventMidPass, config.EventThroughBall, config.EventPassOverTop:
			return 1.25
		case config.EventShortPass, config.EventBackPass, config.EventBuildUp:
			return 0.9
		}
	case "long_ball":
		switch eventType {
		case config.EventGoalKick, config.EventLongPass, config.EventPassOverTop, config.EventLobPass:
			return 1.6
		case config.EventHeader:
			return 1.2
		case config.EventShortPass, config.EventBuildUp, config.EventPivotPass:
			return 0.65
		}
	}
	return 1.0
}

// instructionValueMod maps a 0-4 instruction value to a multiplier around the
// neutral default of 2. Lower values suppress an action, higher values boost it.
func instructionValueMod(value int) float64 {
	switch value {
	case 0:
		return 0.7
	case 1:
		return 0.85
	case 2:
		return 1.0
	case 3:
		return 1.15
	case 4:
		return 1.3
	}
	return 1.0
}

// inverseInstructionValueMod rewards lower instruction values and penalises higher ones.
func inverseInstructionValueMod(value int) float64 {
	switch value {
	case 0:
		return 1.3
	case 1:
		return 1.15
	case 2:
		return 1.0
	case 3:
		return 0.85
	case 4:
		return 0.7
	}
	return 1.0
}

// playerInstructionWeight applies per-player instructions to candidate event
// weights. It is used both in the main simulator loop and in player selectors.
func playerInstructionWeight(player *domain.PlayerRuntime, eventType string) float64 {
	if player == nil {
		return 1.0
	}
	ins := player.Instruction

	switch eventType {
	// Dribble / carry actions are driven by carry_ball.
	case config.EventDribblePast, config.EventWingBreak, config.EventCutInside,
		config.EventOverlap, config.EventCrossRun:
		return instructionValueMod(ins.CarryBall)

	// Shooting actions are driven by shooting_frequency.
	case config.EventCloseShot, config.EventLongShot, config.EventHeader, config.EventShotWindup:
		return instructionValueMod(ins.ShootingFrequency)

	// Crossing actions are driven by crossing_frequency.
	case config.EventCross, config.EventSwitchPlay:
		return instructionValueMod(ins.CrossingFrequency)

	// Risky passes are boosted by higher passing_risk; safe passes are suppressed.
	case config.EventThroughBall, config.EventPassOverTop, config.EventLongPass,
		config.EventLobPass, config.EventMidBreak, config.EventCounterAttack:
		return instructionValueMod(ins.PassingRisk)
	case config.EventShortPass, config.EventBackPass, config.EventPivotPass,
		config.EventBuildUp, config.EventHoldBall:
		// Holding shape / possession is also driven by hold_position.
		return inverseInstructionValueMod(ins.PassingRisk) * instructionValueMod(ins.HoldPosition)

	// Defensive actions are driven by pressing_intensity.
	case config.EventTackle, config.EventIntercept, config.EventDoubleTeam,
		config.EventPressTogether, config.EventBlockPass, config.EventShotBlock,
		config.EventClearance:
		return instructionValueMod(ins.PressingIntensity)

	// Forward runs are driven by forward_runs.
	case config.EventOneTwo, config.EventTrianglePass:
		return instructionValueMod(ins.ForwardRuns)
	}
	return 1.0
}

// gkDistributionWeightMod adjusts GK event candidate weights based on
// goalkeeper distribution instructions.
func gkDistributionWeightMod(instr domain.GoalkeeperDistributionInstructions, eventType string) float64 {
	mod := 1.0

	switch eventType {
	case config.EventGoalKick:
		switch instr.DistributionTarget {
		case "target_forward":
			mod += 0.6
		case "midfield":
			mod += 0.2
		case "center_backs":
			mod -= 0.4
		case "fullbacks":
			mod -= 0.2
		}
		switch instr.DistributionLength {
		case "long":
			mod += 0.4
		case "short":
			mod -= 0.4
		}
		if instr.ReleaseSpeed == "quick" {
			mod -= 0.2
		} else if instr.ReleaseSpeed == "slow" {
			mod += 0.1
		}

	case config.EventKeeperShortPass:
		switch instr.DistributionTarget {
		case "center_backs", "midfield":
			mod += 0.5
		case "fullbacks":
			mod += 0.2
		case "target_forward":
			mod -= 0.5
		}
		switch instr.DistributionLength {
		case "short":
			mod += 0.3
		case "long":
			mod -= 0.4
		}
		if instr.ReleaseSpeed == "quick" {
			mod += 0.2
		} else if instr.ReleaseSpeed == "slow" {
			mod -= 0.2
		}

	case config.EventKeeperThrow:
		switch instr.DistributionTarget {
		case "fullbacks":
			mod += 0.7
		case "midfield":
			mod += 0.3
		case "center_backs":
			mod += 0.2
		case "target_forward":
			mod -= 0.3
		}
		if instr.ReleaseSpeed == "quick" {
			mod += 0.4
		} else if instr.ReleaseSpeed == "slow" {
			mod -= 0.3
		}
	}

	if mod < 0.2 {
		mod = 0.2
	}
	return mod
}

// gkTargetPreference returns a position preference string for goalkeeper
// distribution target. Empty means no preference.
func gkTargetPreference(instr domain.GoalkeeperDistributionInstructions) string {
	switch instr.DistributionTarget {
	case "center_backs":
		return config.PosDF
	case "fullbacks":
		return config.PosDF
	case "midfield":
		return config.PosMF
	case "target_forward":
		return config.PosFW
	default:
		return ""
	}
}

// SelectPassTargetForDistribution picks a pass target biased by the goalkeeper
// distribution target. It falls back to the normal selector when target is mixed
// or unavailable.
func SelectPassTargetForDistribution(
	team *domain.TeamRuntime,
	fromZone [2]int,
	instr domain.GoalkeeperDistributionInstructions,
	r *rand.Rand,
	markingTeam ...*domain.TeamRuntime,
) *domain.PlayerRuntime {
	pref := gkTargetPreference(instr)
	if pref == "" {
		return SelectPassTarget(team, fromZone, r, markingTeam...)
	}

	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		if p.Position == config.PosGK && fromZone[0] < 2 {
			weights[i] = 0
			continue
		}
		zw := zoneWeight(p.Position, fromZone[0], fromZone[1])
		if p.Position == config.PosFW {
			zw += 0.3
		}
		// Fullbacks preference: boost side zones
		if instr.DistributionTarget == "fullbacks" && p.Position == config.PosDF {
			if fromZone[1] == 0 || fromZone[1] == 2 {
				zw += 0.5
			} else {
				zw += 0.2
			}
		}
		// Apply explicit position preference
		if p.Position == pref {
			zw += 0.8
		}
		staminaFactor := 0.5 + 0.5*(p.CurrentStamina/100.0)
		weights[i] = zw * staminaFactor
	}

	// Apply man marking penalty if provided
	if len(markingTeam) > 0 && markingTeam[0] != nil {
		opp := markingTeam[0]
		if opp.Tactics.MarkingStrategy >= 2 {
			var markingPenalty float64 = 1.0
			for _, p := range opp.GetActivePlayers() {
				for _, ps := range ParseSkills(p.Skills) {
					if ps.Name == "盯人专家" {
						ctx := SkillContext{Player: p}
						bonus := skillHandlers["盯人专家"](ctx)
						mul := qualityMultiplier[ps.Quality]
						mod := bonus.WeightMod * mul
						if mod > 0 && mod < markingPenalty {
							markingPenalty = mod
						}
					}
				}
			}
			if markingPenalty < 1.0 {
				for i, p := range players {
					if p.Position == config.PosFW {
						weights[i] *= markingPenalty
					}
				}
			}
		}
	}

	return weightedSelect(players, weights, r)
}
