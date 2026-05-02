package engine

import (
	"math"
	"math/rand/v2"

	"match-engine/internal/domain"
)

// DuelResult is the outcome of a duel
func ResolveDuel(attackValue, defenseValue float64, r *rand.Rand) bool {
	delta := attackValue - defenseValue
	// Add randomness ±1.0
	delta += (r.Float64()*2.0 - 1.0)
	pSuccess := sigmoid(delta / 5.0)
	return r.Float64() < pSuccess
}

func sigmoid(x float64) float64 {
	return 1.0 / (1.0 + math.Exp(-x))
}

// CalculatePassAttack for passing events
func CalcPassAttack(holder *domain.PlayerRuntime, zoneControl float64) float64 {
	return holder.GetAttrByName("PAS")*0.6 +
		holder.GetAttrByName("VIS")*0.25 +
		holder.GetAttrByName("CON")*0.15 +
		zoneControl*2.5 // scale control to attribute range
}

func CalcPassDefense(pressure *domain.PlayerRuntime, zoneControl float64) float64 {
	return pressure.GetAttrByName("DEF")*0.25 +
		pressure.GetAttrByName("TKL")*0.15 +
		pressure.GetAttrByName("SPD")*0.10 +
		(1.0-zoneControl)*1.0
}

// Dribble / Breakthrough
func CalcDribbleAttack(dribbler *domain.PlayerRuntime) float64 {
	return dribbler.GetAttrByName("DRI")*0.5 +
		dribbler.GetAttrByName("SPD")*0.25 +
		dribbler.GetAttrByName("ACC")*0.25
}

func CalcDribbleDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("TKL")*0.3 +
		defender.GetAttrByName("SPD")*0.3
}

// Shot
func CalcShotAttack(shooter *domain.PlayerRuntime, distance string) float64 {
	if distance == "long" {
		return shooter.GetAttrByName("FIN")*0.55 +
			shooter.GetAttrByName("SHO")*0.25 +
			shooter.GetAttrByName("STR")*0.20
	}
	return shooter.GetAttrByName("SHO")*0.6 +
		shooter.GetAttrByName("ACC")*0.2 +
		shooter.GetAttrByName("STR")*0.2
}

func CalcSaveDefense(keeper *domain.PlayerRuntime, distance string) float64 {
	if distance == "long" {
		return keeper.GetAttrByName("SAV")*0.5 +
			keeper.GetAttrByName("POS")*0.3 +
			keeper.GetAttrByName("REF")*0.2 +
			1.0 // keeper advantage
	}
	return keeper.GetAttrByName("SAV")*0.45 +
		keeper.GetAttrByName("REF")*0.35 +
		keeper.GetAttrByName("POS")*0.2 +
		1.5 // keeper advantage in close range
}

// Header / Aerial
func CalcHeaderAttack(attacker *domain.PlayerRuntime) float64 {
	return attacker.GetAttrByName("HEA")*0.5 +
		attacker.GetAttrByName("STR")*0.3 +
		attacker.GetAttrByName("SPD")*0.2
}

func CalcHeaderDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("STR")*0.3 +
		defender.GetAttrByName("DEF")*0.2
}

// Tackle / Intercept
func CalcTackleAttack(tackler *domain.PlayerRuntime) float64 {
	return tackler.GetAttrByName("TKL")*0.5 +
		tackler.GetAttrByName("DEF")*0.3 +
		tackler.GetAttrByName("STR")*0.2
}

func CalcTackleDefense(holder *domain.PlayerRuntime) float64 {
	return holder.GetAttrByName("DRI")*0.35 +
		holder.GetAttrByName("CON")*0.35 +
		holder.GetAttrByName("STR")*0.3
}

// Cross
func CalcCrossAttack(crosser *domain.PlayerRuntime) float64 {
	return crosser.GetAttrByName("CRO")*0.5 +
		crosser.GetAttrByName("PAS")*0.3 +
		crosser.GetAttrByName("DRI")*0.2
}

func CalcCrossDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("HEA")*0.3
}

// Through ball
func CalcThroughAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.5 +
		passer.GetAttrByName("VIS")*0.4 +
		passer.GetAttrByName("ACC")*0.1
}

func CalcThroughDefense(defense *domain.PlayerRuntime) float64 {
	return defense.GetAttrByName("DEF")*0.5 +
		defense.GetAttrByName("SPD")*0.3 +
		defense.GetAttrByName("POS")*0.2
}

// Long pass
func CalcLongPassAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.5 +
		passer.GetAttrByName("STR")*0.2 +
		passer.GetAttrByName("VIS")*0.3
}

func CalcLongPassDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("HEA")*0.4 +
		defender.GetAttrByName("SPD")*0.4 +
		defender.GetAttrByName("POS")*0.2
}
