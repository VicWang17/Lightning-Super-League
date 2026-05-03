package engine

import (
	"math"
	"math/rand/v2"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// DuelResult is the outcome of a duel
// com values reduce randomness: higher COM = more stable outcomes
// Single-roll design: no delta noise, COM deterministically stabilizes probability
func ResolveDuel(attackValue, defenseValue float64, r *rand.Rand, com ...float64) bool {
	delta := attackValue - defenseValue
	pSuccess := sigmoid(delta / 6.0)

	if len(com) > 0 {
		avgCom := 0.0
		for _, c := range com {
			avgCom += c
		}
		avgCom /= float64(len(com))
		// COM stabilizes outcome: high COM pushes probability away from 0.5
		// low COM pulls it toward 0.5 (more random)
		stability := math.Min(1.0, avgCom/15.0)
		pSuccess = 0.5 + (pSuccess-0.5)*(0.5+0.5*stability)
	}

	if pSuccess < 0.03 {
		pSuccess = 0.03
	}
	if pSuccess > 0.97 {
		pSuccess = 0.97
	}
	return r.Float64() < pSuccess
}

func sigmoid(x float64) float64 {
	return 1.0 / (1.0 + math.Exp(-x))
}

// CalculatePassAttack for passing events
func CalcPassAttack(holder *domain.PlayerRuntime, zoneControl float64) float64 {
	base := holder.GetAttrByName("PAS")*0.55 +
		holder.GetAttrByName("VIS")*0.35 +
		holder.GetAttrByName("CON")*0.15 +
		zoneControl*2.5 // scale control to attribute range
	// Midfield orchestrators get a natural passing bonus
	if holder.Position == config.PosCMF || holder.Position == config.PosDMF {
		base += 0.3
	}
	return base
}

func CalcPassDefense(pressure *domain.PlayerRuntime, zoneControl float64) float64 {
	return pressure.GetAttrByName("DEF")*0.25 +
		pressure.GetAttrByName("TKL")*0.15 +
		pressure.GetAttrByName("SPD")*0.10 +
		(1.0-zoneControl)*1.0
}

// Dribble / Breakthrough
func CalcDribbleAttack(dribbler *domain.PlayerRuntime) float64 {
	return dribbler.GetAttrByName("DRI")*0.45 +
		dribbler.GetAttrByName("SPD")*0.25 +
		dribbler.GetAttrByName("ACC")*0.15 +
		dribbler.GetAttrByName("BAL")*0.15
}

func CalcDribbleDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.40 +
		defender.GetAttrByName("TKL")*0.30 +
		defender.GetAttrByName("SPD")*0.30
}

// Shot
func CalcShotAttack(shooter *domain.PlayerRuntime, distance string) float64 {
	if distance == "long" {
		return shooter.GetAttrByName("FIN")*0.45 +
			shooter.GetAttrByName("SHO")*0.30 +
			shooter.GetAttrByName("STR")*0.15 +
			shooter.GetAttrByName("BAL")*0.10
	}
	return shooter.GetAttrByName("SHO")*0.50 +
		shooter.GetAttrByName("FIN")*0.20 +
		shooter.GetAttrByName("STR")*0.15 +
		shooter.GetAttrByName("ACC")*0.10
}

func CalcSaveDefense(keeper *domain.PlayerRuntime, distance string) float64 {
	if distance == "long" {
		return keeper.GetAttrByName("SAV")*0.15 +
			keeper.GetAttrByName("POS")*0.10 +
			keeper.GetAttrByName("REF")*0.10 +
			5.0 // keeper advantage + positioning
	}
	return keeper.GetAttrByName("SAV")*0.20 +
		keeper.GetAttrByName("REF")*0.15 +
		keeper.GetAttrByName("POS")*0.10 +
		5.0 // keeper advantage in close range
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
	return holder.GetAttrByName("DRI")*0.25 +
		holder.GetAttrByName("CON")*0.25 +
		holder.GetAttrByName("STR")*0.25 +
		holder.GetAttrByName("BAL")*0.25
}

// Cross
func CalcCrossAttack(crosser *domain.PlayerRuntime) float64 {
	return crosser.GetAttrByName("CRO")*0.45 +
		crosser.GetAttrByName("PAS")*0.30 +
		crosser.GetAttrByName("DRI")*0.25
}

func CalcCrossDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("HEA")*0.3
}

// Through ball
func CalcThroughAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.40 +
		passer.GetAttrByName("VIS")*0.50 +
		passer.GetAttrByName("ACC")*0.10
}

func CalcThroughDefense(defense *domain.PlayerRuntime) float64 {
	return defense.GetAttrByName("DEF")*0.5 +
		defense.GetAttrByName("SPD")*0.3 +
		defense.GetAttrByName("POS")*0.2
}

// Long pass
func CalcLongPassAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.45 +
		passer.GetAttrByName("STR")*0.20 +
		passer.GetAttrByName("VIS")*0.35
}

func CalcLongPassDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("HEA")*0.4 +
		defender.GetAttrByName("SPD")*0.4 +
		defender.GetAttrByName("POS")*0.2
}

// BuildUp (back-line passing sequence)
func CalcBuildUpAttack(p1, p2, p3 *domain.PlayerRuntime) float64 {
	return p1.GetAttrByName("PAS")*0.25 +
		p2.GetAttrByName("PAS")*0.25 +
		p3.GetAttrByName("CON")*0.2 +
		math.Min(p1.GetAttrByName("COM"), math.Min(p2.GetAttrByName("COM"), p3.GetAttrByName("COM")))*0.3
}

func CalcBuildUpDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("POS")*0.3 +
		defender.GetAttrByName("SPD")*0.3
}

// === Phase 1: Simple 1v1 events ===

// SwitchPlay (lateral transfer)
func CalcSwitchPlayAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.5 +
		passer.GetAttrByName("VIS")*0.3 +
		passer.GetAttrByName("STR")*0.2
}

func CalcSwitchPlayDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("HEA")*0.4 +
		defender.GetAttrByName("SPD")*0.4 +
		defender.GetAttrByName("POS")*0.2
}

// LobPass (chip over defense)
func CalcLobPassAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.4 +
		passer.GetAttrByName("VIS")*0.4 +
		passer.GetAttrByName("ACC")*0.2
}

func CalcLobPassDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("POS")*0.3 +
		defender.GetAttrByName("SPD")*0.2
}

// PassOverTop (high ball over defense)
func CalcPassOverTopAttack(passer *domain.PlayerRuntime) float64 {
	return passer.GetAttrByName("PAS")*0.5 +
		passer.GetAttrByName("STR")*0.2 +
		passer.GetAttrByName("VIS")*0.3
}

func CalcPassOverTopDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("POS")*0.2
}

// BlockPass (intercept pass route before played)
func CalcBlockPassAttack(blocker *domain.PlayerRuntime) float64 {
	return blocker.GetAttrByName("DEF")*0.5 +
		blocker.GetAttrByName("SPD")*0.3 +
		blocker.GetAttrByName("TKL")*0.2
}

func CalcBlockPassDefense(holder *domain.PlayerRuntime) float64 {
	return holder.GetAttrByName("PAS")*0.4 +
		holder.GetAttrByName("VIS")*0.4 +
		holder.GetAttrByName("CON")*0.2
}

// OneOnOne (1v1 vs keeper)
func CalcOneOnOneAttack(shooter *domain.PlayerRuntime) float64 {
	return shooter.GetAttrByName("SHO")*0.5 +
		shooter.GetAttrByName("DRI")*0.3 +
		shooter.GetAttrByName("COM")*0.2
}

func CalcOneOnOneDefense(keeper *domain.PlayerRuntime) float64 {
	return keeper.GetAttrByName("REF")*0.30 +
		keeper.GetAttrByName("SAV")*0.25 +
		keeper.GetAttrByName("POS")*0.10 +
		0.2
}

// CoverDefense (positional cover)
func CalcCoverDefenseAttack(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.6 +
		defender.GetAttrByName("POS")*0.2 +
		defender.GetAttrByName("STA")*0.2
}

func CalcCoverDefenseDefense(attacker *domain.PlayerRuntime) float64 {
	return attacker.GetAttrByName("DRI")*0.4 +
		attacker.GetAttrByName("VIS")*0.3 +
		attacker.GetAttrByName("SPD")*0.3
}

// ShotBlock (block a shot)
func CalcShotBlockAttack(blocker *domain.PlayerRuntime) float64 {
	return blocker.GetAttrByName("DEF")*0.4 +
		blocker.GetAttrByName("TKL")*0.3 +
		blocker.GetAttrByName("STR")*0.3
}

func CalcShotBlockDefense(shooter *domain.PlayerRuntime) float64 {
	return shooter.GetAttrByName("SHO")*0.4 +
		shooter.GetAttrByName("STR")*0.4 +
		shooter.GetAttrByName("ACC")*0.2
}

// === Phase 3: Multi-player events ===

// Overlap (fullback + winger vs defender)
func CalcOverlapAttack(sb, wf *domain.PlayerRuntime) float64 {
	return sb.GetAttrByName("PAS")*0.3 +
		wf.GetAttrByName("DRI")*0.3 +
		math.Min(sb.GetAttrByName("STA"), wf.GetAttrByName("STA"))*0.4
}

func CalcOverlapDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("STA")*0.2
}

// TrianglePass (3 attackers vs 2 defenders)
func CalcTriangleAttack(p1, p2, p3 *domain.PlayerRuntime) float64 {
	return p1.GetAttrByName("PAS")*0.25 +
		p2.GetAttrByName("PAS")*0.25 +
		p3.GetAttrByName("DRI")*0.2 +
		math.Min(p1.GetAttrByName("COM"), math.Min(p2.GetAttrByName("COM"), p3.GetAttrByName("COM")))*0.3
}

func CalcTriangleDefense(d1, d2 *domain.PlayerRuntime) float64 {
	return d1.GetAttrByName("DEF")*0.4 +
		d2.GetAttrByName("DEF")*0.3 +
		math.Min(d1.GetAttrByName("COM"), d2.GetAttrByName("COM"))*0.3
}

// OneTwo (give-and-go, 2 attackers vs 1 defender)
func CalcOneTwoAttack(p1, p2 *domain.PlayerRuntime) float64 {
	return p1.GetAttrByName("PAS")*0.35 +
		p2.GetAttrByName("DRI")*0.35 +
		p2.GetAttrByName("ACC")*0.3
}

func CalcOneTwoDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("TKL")*0.2
}

// CrossRun (2 attackers swap positions)
func CalcCrossRunAttack(p1, p2 *domain.PlayerRuntime) float64 {
	return p1.GetAttrByName("DRI")*0.3 +
		p2.GetAttrByName("SPD")*0.3 +
		math.Max(p1.GetAttrByName("VIS"), p2.GetAttrByName("VIS"))*0.4
}

func CalcCrossRunDefense(defender *domain.PlayerRuntime) float64 {
	return defender.GetAttrByName("DEF")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("POS")*0.2
}

// DoubleTeam (2 defenders vs 1 attacker)
func CalcDoubleTeamAttack(d1, d2 *domain.PlayerRuntime) float64 {
	return d1.GetAttrByName("DEF")*0.3 +
		d1.GetAttrByName("TKL")*0.2 +
		d2.GetAttrByName("DEF")*0.3 +
		d2.GetAttrByName("TKL")*0.2
}

func CalcDoubleTeamDefense(attacker *domain.PlayerRuntime) float64 {
	return attacker.GetAttrByName("DRI")*0.4 +
		attacker.GetAttrByName("CON")*0.3 +
		attacker.GetAttrByName("STR")*0.3
}

// PressTogether (2 defenders pressing together)
func CalcPressTogetherAttack(d1, d2 *domain.PlayerRuntime) float64 {
	return d1.GetAttrByName("STA")*0.3 +
		d1.GetAttrByName("TKL")*0.2 +
		d2.GetAttrByName("STA")*0.3 +
		d2.GetAttrByName("TKL")*0.2
}

func CalcPressTogetherDefense(holder *domain.PlayerRuntime) float64 {
	return holder.GetAttrByName("PAS")*0.3 +
		holder.GetAttrByName("CON")*0.3 +
		holder.GetAttrByName("COM")*0.4
}
