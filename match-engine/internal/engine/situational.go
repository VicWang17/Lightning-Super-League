package engine

import (
	"match-engine/internal/domain"
)

// goalDiffForTeam returns the score difference from the team's perspective.
func goalDiffForTeam(team *domain.TeamRuntime, ms *domain.MatchState) int {
	if team == ms.HomeTeam {
		return ms.Score.Home - ms.Score.Away
	}
	return ms.Score.Away - ms.Score.Home
}

// teamStaminaAvg returns the average current stamina of active on-field players.
func teamStaminaAvg(team *domain.TeamRuntime) float64 {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return 100
	}
	var total float64
	for _, p := range players {
		total += p.CurrentStamina
	}
	return total / float64(len(players))
}

// conditionMatches checks whether a single rule condition is satisfied.
func conditionMatches(c domain.SituationalRuleCondition, team *domain.TeamRuntime, ms *domain.MatchState) bool {
	minute := int(ms.Minute)
	if c.MinuteGte != nil && minute < *c.MinuteGte {
		return false
	}
	if c.MinuteLt != nil && minute >= *c.MinuteLt {
		return false
	}
	if c.GoalDiffLte != nil && goalDiffForTeam(team, ms) > *c.GoalDiffLte {
		return false
	}
	if c.GoalDiffGte != nil && goalDiffForTeam(team, ms) < *c.GoalDiffGte {
		return false
	}
	if c.TeamStaminaAvgLte != nil && teamStaminaAvg(team) > float64(*c.TeamStaminaAvgLte) {
		return false
	}
	return true
}

// applyOverride mutates the provided TeamInstructions in place, applying all
// non-nil override fields. Callers must pass a copy if they want to preserve
// the original instructions.
func applyOverride(base *domain.TeamInstructions, o domain.SituationalRuleOverride) {
	if o.Tempo != nil {
		base.InPossession.Tempo = clampInt(*o.Tempo, 0, 4)
	}
	if o.Width != nil {
		base.InPossession.Width = clampInt(*o.Width, 0, 4)
	}
	if o.PassingRisk != nil {
		base.InPossession.PassingRisk = clampInt(*o.PassingRisk, 0, 4)
	}
	if o.CrossingFrequency != nil {
		base.InPossession.CrossingFrequency = clampInt(*o.CrossingFrequency, 0, 4)
	}
	if o.ShootingFrequency != nil {
		base.InPossession.ShootingFrequency = clampInt(*o.ShootingFrequency, 0, 4)
	}
	if o.BuildUpStyle != nil {
		base.InPossession.BuildUpStyle = *o.BuildUpStyle
	}
	if o.ChanceCreation != nil {
		base.InPossession.ChanceCreation = *o.ChanceCreation
	}
	if o.DefensiveLineHeight != nil {
		base.OutOfPossession.DefensiveLineHeight = clampInt(*o.DefensiveLineHeight, 0, 4)
	}
	if o.PressingIntensity != nil {
		base.OutOfPossession.PressingIntensity = clampInt(*o.PressingIntensity, 0, 4)
	}
	if o.AfterPossessionWon != nil {
		base.Transition.AfterPossessionWon = *o.AfterPossessionWon
	}
	if o.AfterPossessionLost != nil {
		base.Transition.AfterPossessionLost = *o.AfterPossessionLost
	}
}

// ComputeEffectiveInstructions evaluates all situational rules for a team and
// returns the resulting instructions together with the IDs of triggered rules.
func ComputeEffectiveInstructions(team *domain.TeamRuntime, ms *domain.MatchState) (domain.TeamInstructions, []string) {
	var base domain.TeamInstructions
	if team.TeamInstructions != nil {
		// Start from the stored instructions so we don't double-apply derived defaults.
		base = domain.NormalizeTeamInstructions(*team.TeamInstructions)
	} else {
		base = domain.NormalizeTeamInstructions(team.Instructions())
	}

	var triggered []string
	for _, rule := range base.SituationalRules {
		if !rule.Enabled {
			continue
		}
		if conditionMatches(rule.Condition, team, ms) {
			applyOverride(&base, rule.Override)
			triggered = append(triggered, rule.ID)
		}
	}
	return domain.NormalizeTeamInstructions(base), triggered
}

func clampInt(v, min, max int) int {
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}
