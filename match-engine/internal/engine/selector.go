package engine

import (
	"math/rand/v2"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// SelectPlayerByZone picks a player from team weighted by zone relevance, stamina, and position realism
func SelectPlayerByZone(team *domain.TeamRuntime, zone [2]int, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		zw := zoneWeight(p.Position, zone[0], zone[1])
		staminaFactor := 0.4 + 0.6*(p.CurrentStamina/100.0)
		if p.CurrentStamina < 20 {
			staminaFactor *= 0.5
		}

		// Position realism penalty
		realismFactor := 1.0
		switch p.Position {
		case config.PosST:
			if zone[0] == 2 {
				realismFactor = 0.05 // striker almost never in back zone
			} else if zone[0] == 1 {
				realismFactor = 0.3
			}
		case config.PosWF:
			if zone[0] == 2 {
				realismFactor = 0.1
			} else if zone[0] == 1 {
				realismFactor = 0.5
			}
		case config.PosAMF:
			if zone[0] == 2 {
				realismFactor = 0.05
			} else if zone[0] == 1 {
				realismFactor = 0.8
			}
		case config.PosCMF:
			if zone[0] == 2 {
				realismFactor = 0.3
			} else if zone[0] == 0 {
				realismFactor = 0.4
			}
		case config.PosDMF:
			if zone[0] == 0 {
				realismFactor = 0.1
			}
		case config.PosCB:
			if zone[0] == 0 {
				realismFactor = 0.02
			} else if zone[0] == 1 {
				realismFactor = 0.2
			}
		case config.PosSB:
			if zone[0] == 0 {
				realismFactor = 0.3
			}
		case config.PosGK:
			if zone[0] < 2 {
				realismFactor = 0.01
			}
		}

		weights[i] = zw * staminaFactor * realismFactor
		if p.Position == config.PosGK {
			weights[i] *= 0.05 // GK very rarely initiates plays
		}
	}

	return weightedSelect(players, weights, r)
}

// SelectDefender picks a defender from opponent team
func SelectDefender(team *domain.TeamRuntime, zone [2]int, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	manMarking := team.Tactics.MarkingStrategy == 1

	weights := make([]float64, len(players))
	for i, p := range players {
		zw := zoneWeight(p.Position, zone[0], zone[1])
		defBonus := 1.0
		if p.Position == config.PosCB || p.Position == config.PosDMF {
			defBonus = 1.5
			if manMarking {
				defBonus = 2.2 // Man marking boosts CB/DMF selection significantly
			}
		}
		if manMarking && (p.Position == config.PosSB || p.Position == config.PosCMF) {
			defBonus = 1.3 // Wide and central midfielders also involved in marking
		}
		staminaFactor := 0.4 + 0.6*(p.CurrentStamina/100.0)
		weights[i] = zw * defBonus * staminaFactor
	}

	return weightedSelect(players, weights, r)
}

// SelectPassTarget picks a teammate to receive a pass
func SelectPassTarget(team *domain.TeamRuntime, fromZone [2]int, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		// Prefer forward zones slightly
		zw := zoneWeight(p.Position, fromZone[0], fromZone[1])
		if p.Position == config.PosST {
			zw += 0.3
		}
		staminaFactor := 0.5 + 0.5*(p.CurrentStamina/100.0)
		weights[i] = zw * staminaFactor
	}

	return weightedSelect(players, weights, r)
}

func weightedSelect[T any](items []T, weights []float64, r *rand.Rand) T {
	var total float64
	for _, w := range weights {
		if w < 0 {
			w = 0
		}
		total += w
	}

	var zero T
	if total <= 0 {
		if len(items) > 0 {
			return items[r.IntN(len(items))]
		}
		return zero
	}

	pick := r.Float64() * total
	var cum float64
	for i, w := range weights {
		cum += w
		if pick <= cum {
			return items[i]
		}
	}
	return items[len(items)-1]
}

