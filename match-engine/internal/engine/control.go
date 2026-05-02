package engine

import (
	"math"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ComputeControlMatrix calculates zone control for the possession team
func ComputeControlMatrix(m *domain.MatchState) [3][3]float64 {
	attack := m.Team(m.Possession)
	defense := m.OppTeam(m.Possession)

	var result [3][3]float64

	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			deltaForm := formationDelta(attack.FormationID, defense.FormationID, r, c)
			deltaPlayer := playerDelta(attack, defense, r, c)
			deltaTactic := tacticDelta(attack.Tactics, defense.Tactics, r, c)
			deltaDynamic := dynamicDelta(m, r, c)

			// Zone momentum: recent successful passes/dribbles boost control
			momentum := m.ZoneMomentum[r][c]

			raw := 0.28*deltaForm + 0.40*deltaPlayer + 0.18*deltaTactic + 0.09*deltaDynamic + 0.05*momentum
			result[r][c] = math.Tanh(raw * 2.0)
		}
	}
	return result
}

func formationDelta(atkForm, defForm string, r, c int) float64 {
	aBase := config.FormationBase[atkForm]
	dBase := config.FormationBase[defForm]
	return aBase[r][c] - dBase[r][c]
}

func playerDelta(atk, def *domain.TeamRuntime, r, c int) float64 {
	var atkSum, defSum float64

	// Attack team contribution
	for _, p := range atk.GetActivePlayers() {
		zw := zoneWeight(p.Position, r, c)
		if zw <= 0 {
			continue
		}
		strength := playerStrength(p, r, c)
		// stamina factor
		staminaFactor := 0.3 + 0.7*(p.CurrentStamina/100.0)
		if p.CurrentStamina < 30 {
			staminaFactor *= 0.7
		}
		atkSum += zw * strength * staminaFactor
	}

	// Defense team contribution
	for _, p := range def.GetActivePlayers() {
		zw := zoneWeight(p.Position, r, c)
		if zw <= 0 {
			continue
		}
		strength := playerStrength(p, r, c)
		staminaFactor := 0.3 + 0.7*(p.CurrentStamina/100.0)
		if p.CurrentStamina < 30 {
			staminaFactor *= 0.7
		}
		defSum += zw * strength * staminaFactor
	}

	return atkSum - defSum
}

func zoneWeight(position string, r, c int) float64 {
	w, ok := config.ZoneWeight[position]
	if !ok {
		return 0.2
	}
	return w[r][c]
}

func playerStrength(p *domain.PlayerRuntime, r, c int) float64 {
	// Use position-specific attribute weights
	weights, ok := config.PositionAttrWeight[p.Position]
	if !ok {
		return 0.5
	}
	var sum float64
	for i := 0; i < config.AttrCount; i++ {
		attrVal := p.GetAttr(i)
		if attrVal > 20 {
			attrVal = 20
		}
		sum += (attrVal / 20.0) * weights[i]
	}
	// GK has specialized weights already
	if p.Position == config.PosGK {
		return sum
	}
	// Normalize roughly to 0-1 range (weights sum to 100)
	return sum / 100.0
}

func tacticDelta(atkT, defT domain.TacticalSetup, r, c int) float64 {
	var delta float64

	// Attack width: affects side zones
	if atkT.AttackWidth >= 3 {
		if c == 0 || c == 2 {
			delta += 0.10
		} else {
			delta -= 0.05
		}
	} else if atkT.AttackWidth <= 1 {
		if c == 1 {
			delta += 0.08
		} else {
			delta -= 0.04
		}
	}

	// Defensive line height
	if atkT.DefensiveLineHeight >= 3 {
		if r == 0 {
			delta += 0.10
		} else if r == 2 {
			delta -= 0.05
		}
	} else if atkT.DefensiveLineHeight <= 1 {
		if r == 2 {
			delta += 0.08
		} else if r == 0 {
			delta -= 0.05
		}
	}

	// Pressing intensity
	if atkT.PressingIntensity >= 3 {
		if r <= 1 {
			delta += 0.08
		}
	}

	// Defensive compactness
	if defT.DefensiveCompactness >= 2 {
		if r >= 1 {
			delta -= 0.10
		}
	}

	// Mirror for defense team
	if defT.AttackWidth >= 3 {
		if c == 0 || c == 2 {
			delta -= 0.10
		} else {
			delta += 0.05
		}
	}

	return delta
}

func dynamicDelta(m *domain.MatchState, r, c int) float64 {
	var delta float64

	// Time factor: slight increase for attacking side late in match
	timeFactor := (m.Minute - 25.0) / 50.0 * 0.1
	delta += timeFactor

	// Score factor: trailing team gets boost
	if m.Possession == domain.SideHome {
		if m.Score.Home < m.Score.Away {
			delta += 0.08
		} else if m.Score.Home > m.Score.Away {
			delta -= 0.03
		}
	} else {
		if m.Score.Away < m.Score.Home {
			delta += 0.08
		} else if m.Score.Away > m.Score.Home {
			delta -= 0.03
		}
	}

	// Home advantage
	if m.Possession == domain.SideHome {
		delta += 0.05
	}

	return delta
}
