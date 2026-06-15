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
		case config.PosFW:
			if zone[0] == 2 {
				realismFactor = 0.08 // forwards rarely in back zone
			} else if zone[0] == 1 {
				realismFactor = 0.4
			}
		case config.PosMF:
			if zone[0] == 2 {
				realismFactor = 0.25
			} else if zone[0] == 0 {
				realismFactor = 0.25
			}
		case config.PosDF:
			if zone[0] == 0 {
				realismFactor = 0.15
			} else if zone[0] == 1 {
				realismFactor = 0.25
			}
		case config.PosGK:
			if zone[0] < 2 {
				realismFactor = 0.01
			}
		}

		weights[i] = zw * staminaFactor * realismFactor
		if p.Position == config.PosGK {
			weights[i] *= 0.05 // GK very rarely initiates plays
			// Additionally, GK should almost never be selected in attacking zones
			if zone[0] < 2 {
				weights[i] *= 0.01
			}
		}
	}

	return weightedSelect(players, weights, r)
}

// SelectShooterByZone picks the likely shooter from the current attacking zone.
// It still respects positional realism, but finishing attributes decide who gets
// the chance more strongly than generic zone presence.
func SelectShooterByZone(team *domain.TeamRuntime, zone [2]int, distance string, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		if p.Position == config.PosGK {
			weights[i] = 0.01
			continue
		}

		zw := zoneWeight(p.Position, zone[0], zone[1])
		staminaFactor := 0.4 + 0.6*(p.CurrentStamina/100.0)
		if p.CurrentStamina < 20 {
			staminaFactor *= 0.5
		}

		positionBonus := 1.0
		switch p.Position {
		case config.PosFW:
			positionBonus = 2.2
		case config.PosMF:
			positionBonus = 1.15
		case config.PosDF:
			positionBonus = 0.35
			if zone[0] == 0 {
				positionBonus = 0.22
			}
		}

		shotScore := p.GetAttrByName("SHO")*0.35 +
			p.GetAttrByName("FIN")*0.30 +
			p.GetAttrByName("DEC")*0.20 +
			p.GetAttrByName("COM")*0.15
		if distance == "long" {
			shotScore = p.GetAttrByName("SHO")*0.45 +
				p.GetAttrByName("FIN")*0.20 +
				p.GetAttrByName("DEC")*0.20 +
				p.GetAttrByName("COM")*0.15
		}
		qualityFactor := 0.35 + shotScore/20.0

		weights[i] = zw * staminaFactor * positionBonus * qualityFactor
	}

	return weightedSelect(players, weights, r)
}

// SelectDefender picks a defender from opponent team
func SelectDefender(team *domain.TeamRuntime, zone [2]int, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	// Exclude GK from most defensive actions unless they're the only option
	var outfieldPlayers []*domain.PlayerRuntime
	for _, p := range players {
		if p.Position != config.PosGK {
			outfieldPlayers = append(outfieldPlayers, p)
		}
	}
	if len(outfieldPlayers) > 0 {
		players = outfieldPlayers
	}

	manMarking := team.Tactics.MarkingStrategy >= 2

	weights := make([]float64, len(players))
	for i, p := range players {
		zw := zoneWeight(p.Position, zone[0], zone[1])
		defBonus := 1.0
		if p.Position == config.PosDF {
			// 后卫应主导后场防守，中场只在中前场高压时补位。
			defBonus = 3.0
			if zone[0] == 2 {
				defBonus = 5.0
			} else if zone[0] == 1 {
				defBonus = 3.6
			}
			if manMarking {
				defBonus *= 1.25
			}
		} else if p.Position == config.PosMF {
			defBonus = 0.65
			if zone[0] == 1 {
				defBonus = 0.85
			} else if zone[0] == 2 {
				defBonus = 0.35
			}
			if manMarking {
				defBonus *= 1.1
			}
		} else if p.Position == config.PosFW {
			// 前锋极少深度参与纯防守动作
			defBonus = 0.5
		}
		staminaFactor := 0.4 + 0.6*(p.CurrentStamina/100.0)
		weights[i] = zw * defBonus * staminaFactor
	}

	return weightedSelect(players, weights, r)
}

// SelectPassTarget picks a teammate to receive a pass
func SelectPassTarget(team *domain.TeamRuntime, fromZone [2]int, r *rand.Rand, markingTeam ...*domain.TeamRuntime) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) == 0 {
		return team.PlayerRuntimes[0]
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		// GK should never be a pass target in attacking or midfield zones
		if p.Position == config.PosGK && fromZone[0] < 2 {
			weights[i] = 0.0
			continue
		}
		// Prefer forward zones slightly
		zw := zoneWeight(p.Position, fromZone[0], fromZone[1])
		if p.Position == config.PosFW {
			zw += 0.3
		}
		staminaFactor := 0.5 + 0.5*(p.CurrentStamina/100.0)
		weights[i] = zw * staminaFactor
	}

	// Man marking expert: reduce pass target weight for forwards when opponent uses man marking
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

// SelectReboundAttacker picks an attacker for a rebound chance after keeper spill
func SelectReboundAttacker(team *domain.TeamRuntime, zone [2]int, r *rand.Rand) *domain.PlayerRuntime {
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
		weights[i] = zw * staminaFactor

		// 补射猎手 bonus
		if len(p.Skills) > 0 {
			ctx := SkillContext{EventType: config.EventCloseShot, Player: p, Zone: zone}
			bonus := ComputeSkillBonus(ctx)
			if bonus.WeightMod > 0 {
				weights[i] *= bonus.WeightMod
			}
		}
	}

	return weightedSelect(players, weights, r)
}

// SelectSecondAttacker picks a teammate different from primary for multi-player events
func SelectSecondAttacker(team *domain.TeamRuntime, primary *domain.PlayerRuntime, zone [2]int, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) <= 1 {
		return primary
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		if p.PlayerID == primary.PlayerID {
			weights[i] = 0 // exclude primary
			continue
		}
		zw := zoneWeight(p.Position, zone[0], zone[1])
		staminaFactor := 0.4 + 0.6*(p.CurrentStamina/100.0)
		if p.CurrentStamina < 20 {
			staminaFactor *= 0.5
		}
		// FW/MF preferred for multi-player attacks
		positionBonus := 1.0
		switch p.Position {
		case config.PosFW:
			positionBonus = 1.2
		case config.PosMF:
			positionBonus = 1.2
		}
		weights[i] = zw * staminaFactor * positionBonus
	}

	return weightedSelect(players, weights, r)
}

// SelectSecondDefender picks a defender different from primary for multi-defender events
func SelectSecondDefender(team *domain.TeamRuntime, primary *domain.PlayerRuntime, zone [2]int, r *rand.Rand) *domain.PlayerRuntime {
	players := team.GetActivePlayers()
	if len(players) <= 1 {
		return primary
	}

	weights := make([]float64, len(players))
	for i, p := range players {
		if p.PlayerID == primary.PlayerID {
			weights[i] = 0 // exclude primary
			continue
		}
		zw := zoneWeight(p.Position, zone[0], zone[1])
		defBonus := 1.0
		if p.Position == config.PosDF {
			// 第二防守人也优先是后卫
			defBonus = 2.5
		} else if p.Position == config.PosMF {
			defBonus = 0.8
		} else if p.Position == config.PosFW || p.Position == config.PosGK {
			defBonus = 0.4
		}
		staminaFactor := 0.4 + 0.6*(p.CurrentStamina/100.0)
		weights[i] = zw * defBonus * staminaFactor
	}

	return weightedSelect(players, weights, r)
}
