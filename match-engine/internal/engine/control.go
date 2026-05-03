package engine

import (
	"math"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ComputeControlMatrix calculates zone control in ABSOLUTE reference frame.
// Positive = home team advantage, Negative = away team advantage.
func ComputeControlMatrix(m *domain.MatchState) [3][3]float64 {
	home := m.HomeTeam
	away := m.AwayTeam

	var result [3][3]float64

	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			deltaForm := formationDelta(home.FormationID, away.FormationID, r, c)
			deltaPlayer := playerDelta(home, away, r, c)
			deltaTactic := tacticDelta(home.Tactics, away.Tactics, r, c)
			deltaDynamic := dynamicDelta(m, r, c)

			// Global momentum: tiny influence, capped
			momentum := m.GlobalMomentum

			// Natural control raw value
			raw := 0.28*deltaForm + 0.40*deltaPlayer + 0.18*deltaTactic + 0.03*deltaDynamic + 0.01*momentum

			result[r][c] = math.Tanh(raw * 2.0)
		}
	}
	return result
}

// decayControlShift drifts inactive zones back toward 0
func decayControlShift(m *domain.MatchState) {
	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			if r == m.ActiveZone[0] && c == m.ActiveZone[1] {
				// Active zone: mild decay
				m.ControlShift[r][c] *= 0.92
			} else {
				// Inactive zones: drift back to 0 much faster
				m.ControlShift[r][c] *= 0.60
			}
			// Clamp
			if m.ControlShift[r][c] > 0.5 {
				m.ControlShift[r][c] = 0.5
			} else if m.ControlShift[r][c] < -0.5 {
				m.ControlShift[r][c] = -0.5
			}
			// Snap to 0 when very small
			if m.ControlShift[r][c] < 0.01 && m.ControlShift[r][c] > -0.01 {
				m.ControlShift[r][c] = 0
			}
		}
	}
}

// resetControlShift zeros out all control shifts on dead ball / restart
func resetControlShift(m *domain.MatchState) {
	for r := 0; r < 3; r++ {
		for c := 0; c < 3; c++ {
			m.ControlShift[r][c] = 0
		}
	}
}

// ComputeRiskIndex returns team's risk-taking appetite [0,1] based on tactics
func ComputeRiskIndex(tactics domain.TacticalSetup) float64 {
	idx := (4.0-float64(tactics.PassingStyle))*0.20 +
		float64(tactics.AttackTempo)*0.20 +
		float64(tactics.ShootingMentality)*0.20 +
		float64(tactics.TacklingAggression)*0.15 +
		(2.0-float64(tactics.MarkingStrategy))*0.10 +
		(4.0-float64(tactics.DefensiveLineHeight))*0.15
	idx /= 4.0 // normalize to roughly [0,1]
	if idx > 1.0 {
		idx = 1.0
	}
	if idx < 0.0 {
		idx = 0.0
	}
	return idx
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

// ControlBreakdown explains why control changed for a specific zone
type ControlBreakdown struct {
	Formation     float64 `json:"formation"`
	Player        float64 `json:"player"`
	Tactic        float64 `json:"tactic"`
	Dynamic       float64 `json:"dynamic"`
	Momentum      float64 `json:"momentum"`
	CounterBoost  float64 `json:"counter_boost"`
	Raw           float64 `json:"raw"`
	Final         float64 `json:"final"`
}

func ComputeControlBreakdown(m *domain.MatchState, zone [2]int) ControlBreakdown {
	home := m.HomeTeam
	away := m.AwayTeam
	r, c := zone[0], zone[1]

	deltaForm := formationDelta(home.FormationID, away.FormationID, r, c)
	deltaPlayer := playerDelta(home, away, r, c)
	deltaTactic := tacticDelta(home.Tactics, away.Tactics, r, c)
	deltaDynamic := dynamicDelta(m, r, c)
	momentum := m.GlobalMomentum
	shift := m.ControlShift[r][c]

	raw := 0.28*deltaForm + 0.40*deltaPlayer + 0.18*deltaTactic + 0.03*deltaDynamic + 0.01*momentum

	cb := ControlBreakdown{
		Formation: 0.28 * deltaForm,
		Player:    0.40 * deltaPlayer,
		Tactic:    0.18 * deltaTactic,
		Dynamic:   0.03 * deltaDynamic,
		Momentum:  0.02 * momentum,
		Raw:       raw,
		Final:     math.Tanh(raw*2.0) + shift,
	}

	return cb
}

func dynamicDelta(m *domain.MatchState, r, c int) float64 {
	var delta float64

	// Score factor: trailing team gets boost (absolute reference: home perspective)
	if m.Score.Home < m.Score.Away {
		delta += 0.06
	} else if m.Score.Home > m.Score.Away {
		delta -= 0.02
	}

	// Home advantage
	delta += 0.04

	return delta
}
