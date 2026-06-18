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
	pSuccess := sigmoid(delta / 4.0)

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
	if holder.Position == config.PosMF {
		base += 0.3
	}
	return applySkillAttack(holder, base)
}

func CalcPassDefense(pressure *domain.PlayerRuntime, zoneControl float64) float64 {
	base := pressure.GetAttrByName("DEF")*0.25 +
		pressure.GetAttrByName("TKL")*0.15 +
		pressure.GetAttrByName("SPD")*0.10 +
		(1.0-zoneControl)*1.0
	return applySkillDefense(pressure, base)
}

// Dribble / Breakthrough
func CalcDribbleAttack(dribbler *domain.PlayerRuntime) float64 {
	base := dribbler.GetAttrByName("DRI")*0.45 +
		dribbler.GetAttrByName("SPD")*0.25 +
		dribbler.GetAttrByName("ACC")*0.15 +
		dribbler.GetAttrByName("BAL")*0.15
	return applySkillAttack(dribbler, base)
}

func CalcDribbleDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.40 +
		defender.GetAttrByName("TKL")*0.30 +
		defender.GetAttrByName("SPD")*0.30
	return applySkillDefense(defender, base)
}

// Shot
func CalcShotAttack(shooter *domain.PlayerRuntime, distance string) float64 {
	if distance == "long" {
		base := shooter.GetAttrByName("FIN")*0.45 +
			shooter.GetAttrByName("SHO")*0.30 +
			shooter.GetAttrByName("STR")*0.15 +
			shooter.GetAttrByName("BAL")*0.10
		return applySkillAttack(shooter, base)
	}
	base := shooter.GetAttrByName("SHO")*0.50 +
		shooter.GetAttrByName("FIN")*0.20 +
		shooter.GetAttrByName("STR")*0.15 +
		shooter.GetAttrByName("ACC")*0.10
	return applySkillAttack(shooter, base)
}

func CalcSaveDefense(keeper *domain.PlayerRuntime, distance string) float64 {
	if distance == "long" {
		base := keeper.GetAttrByName("SAV")*0.15 +
			keeper.GetAttrByName("POS")*0.10 +
			keeper.GetAttrByName("REF")*0.10 +
			5.0 // keeper advantage + positioning
		return applySkillDefense(keeper, base)
	}
	base := keeper.GetAttrByName("SAV")*0.20 +
		keeper.GetAttrByName("REF")*0.15 +
		keeper.GetAttrByName("POS")*0.10 +
		5.0 // keeper advantage in close range
	return applySkillDefense(keeper, base)
}

// Header / Aerial
func CalcHeaderAttack(attacker *domain.PlayerRuntime) float64 {
	base := attacker.GetAttrByName("HEA")*0.5 +
		attacker.GetAttrByName("STR")*0.3 +
		attacker.GetAttrByName("SPD")*0.2
	return applySkillAttack(attacker, base)
}

func CalcHeaderDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("STR")*0.3 +
		defender.GetAttrByName("DEF")*0.2
	return applySkillDefense(defender, base)
}

// Tackle / Intercept
func CalcTackleAttack(tackler *domain.PlayerRuntime) float64 {
	base := tackler.GetAttrByName("TKL")*0.5 +
		tackler.GetAttrByName("DEF")*0.3 +
		tackler.GetAttrByName("STR")*0.2
	return applySkillAttack(tackler, base)
}

func CalcTackleDefense(holder *domain.PlayerRuntime) float64 {
	base := holder.GetAttrByName("DRI")*0.25 +
		holder.GetAttrByName("CON")*0.25 +
		holder.GetAttrByName("STR")*0.25 +
		holder.GetAttrByName("BAL")*0.25
	return applySkillDefense(holder, base)
}

func CalcInterceptAttack(interceptor *domain.PlayerRuntime) float64 {
	base := interceptor.GetAttrByName("DEF")*0.40 +
		interceptor.GetAttrByName("POS")*0.30 +
		interceptor.GetAttrByName("DEC")*0.20 +
		interceptor.GetAttrByName("ACC")*0.10
	return applySkillAttack(interceptor, base)
}

func CalcInterceptDefense(passer *domain.PlayerRuntime) float64 {
	base := passer.GetAttrByName("PAS")*0.45 +
		passer.GetAttrByName("VIS")*0.35 +
		passer.GetAttrByName("COM")*0.20
	return applySkillDefense(passer, base)
}

// Cross
func CalcCrossAttack(crosser *domain.PlayerRuntime) float64 {
	base := crosser.GetAttrByName("CRO")*0.45 +
		crosser.GetAttrByName("PAS")*0.30 +
		crosser.GetAttrByName("DRI")*0.25
	return applySkillAttack(crosser, base)
}

func CalcCrossDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("HEA")*0.3
	return applySkillDefense(defender, base)
}

// Through ball
func CalcThroughAttack(passer *domain.PlayerRuntime) float64 {
	base := passer.GetAttrByName("PAS")*0.40 +
		passer.GetAttrByName("VIS")*0.50 +
		passer.GetAttrByName("ACC")*0.10
	return applySkillAttack(passer, base)
}

func CalcThroughDefense(defense *domain.PlayerRuntime) float64 {
	base := defense.GetAttrByName("DEF")*0.5 +
		defense.GetAttrByName("SPD")*0.3 +
		defense.GetAttrByName("POS")*0.2
	return applySkillDefense(defense, base)
}

// Long pass
func CalcLongPassAttack(passer *domain.PlayerRuntime) float64 {
	base := passer.GetAttrByName("PAS")*0.45 +
		passer.GetAttrByName("STR")*0.20 +
		passer.GetAttrByName("VIS")*0.35
	return applySkillAttack(passer, base)
}

func CalcLongPassDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("HEA")*0.4 +
		defender.GetAttrByName("SPD")*0.4 +
		defender.GetAttrByName("POS")*0.2
	return applySkillDefense(defender, base)
}

// BuildUp (back-line passing sequence)
func CalcBuildUpAttack(p1, p2, p3 *domain.PlayerRuntime) float64 {
	base := p1.GetAttrByName("PAS")*0.25 +
		p2.GetAttrByName("PAS")*0.25 +
		p3.GetAttrByName("CON")*0.2 +
		math.Min(p1.GetAttrByName("COM"), math.Min(p2.GetAttrByName("COM"), p3.GetAttrByName("COM")))*0.3
	return applySkillAttack(p3, base)
}

func CalcBuildUpDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.4 +
		defender.GetAttrByName("POS")*0.3 +
		defender.GetAttrByName("SPD")*0.3
	return applySkillDefense(defender, base)
}

// === Phase 1: Simple 1v1 events ===

// SwitchPlay (lateral transfer)
func CalcSwitchPlayAttack(passer *domain.PlayerRuntime) float64 {
	base := passer.GetAttrByName("PAS")*0.5 +
		passer.GetAttrByName("VIS")*0.3 +
		passer.GetAttrByName("STR")*0.2
	return applySkillAttack(passer, base)
}

func CalcSwitchPlayDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("HEA")*0.4 +
		defender.GetAttrByName("SPD")*0.4 +
		defender.GetAttrByName("POS")*0.2
	return applySkillDefense(defender, base)
}

// LobPass (chip over defense)
func CalcLobPassAttack(passer *domain.PlayerRuntime) float64 {
	base := passer.GetAttrByName("PAS")*0.4 +
		passer.GetAttrByName("VIS")*0.4 +
		passer.GetAttrByName("ACC")*0.2
	return applySkillAttack(passer, base)
}

func CalcLobPassDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("POS")*0.3 +
		defender.GetAttrByName("SPD")*0.2
	return applySkillDefense(defender, base)
}

// PassOverTop (high ball over defense)
func CalcPassOverTopAttack(passer *domain.PlayerRuntime) float64 {
	base := passer.GetAttrByName("PAS")*0.5 +
		passer.GetAttrByName("STR")*0.2 +
		passer.GetAttrByName("VIS")*0.3
	return applySkillAttack(passer, base)
}

func CalcPassOverTopDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("HEA")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("POS")*0.2
	return applySkillDefense(defender, base)
}

// BlockPass (intercept pass route before played)
func CalcBlockPassAttack(blocker *domain.PlayerRuntime) float64 {
	base := blocker.GetAttrByName("DEF")*0.5 +
		blocker.GetAttrByName("SPD")*0.3 +
		blocker.GetAttrByName("TKL")*0.2
	return applySkillAttack(blocker, base)
}

func CalcBlockPassDefense(holder *domain.PlayerRuntime) float64 {
	base := holder.GetAttrByName("PAS")*0.4 +
		holder.GetAttrByName("VIS")*0.4 +
		holder.GetAttrByName("CON")*0.2
	return applySkillDefense(holder, base)
}

// OneOnOne (1v1 vs keeper)
func CalcOneOnOneAttack(shooter *domain.PlayerRuntime) float64 {
	base := shooter.GetAttrByName("SHO")*0.5 +
		shooter.GetAttrByName("DRI")*0.3 +
		shooter.GetAttrByName("COM")*0.2
	return applySkillAttack(shooter, base)
}

func CalcOneOnOneDefense(keeper *domain.PlayerRuntime) float64 {
	base := keeper.GetAttrByName("REF")*0.30 +
		keeper.GetAttrByName("SAV")*0.25 +
		keeper.GetAttrByName("POS")*0.10 +
		0.2
	return applySkillDefense(keeper, base)
}

// CoverDefense (positional cover)
func CalcCoverDefenseAttack(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.6 +
		defender.GetAttrByName("POS")*0.2 +
		defender.GetAttrByName("STA")*0.2
	return applySkillAttack(defender, base)
}

func CalcCoverDefenseDefense(attacker *domain.PlayerRuntime) float64 {
	base := attacker.GetAttrByName("DRI")*0.4 +
		attacker.GetAttrByName("VIS")*0.3 +
		attacker.GetAttrByName("SPD")*0.3
	return applySkillDefense(attacker, base)
}

// ShotBlock (block a shot)
func CalcShotBlockAttack(blocker *domain.PlayerRuntime) float64 {
	base := blocker.GetAttrByName("DEF")*0.4 +
		blocker.GetAttrByName("TKL")*0.3 +
		blocker.GetAttrByName("STR")*0.3
	return applySkillAttack(blocker, base)
}

func CalcShotBlockDefense(shooter *domain.PlayerRuntime) float64 {
	base := shooter.GetAttrByName("SHO")*0.4 +
		shooter.GetAttrByName("STR")*0.4 +
		shooter.GetAttrByName("ACC")*0.2
	return applySkillDefense(shooter, base)
}

// === Phase 3: Multi-player events ===

// Overlap (fullback + winger vs defender)
func CalcOverlapAttack(sb, wf *domain.PlayerRuntime) float64 {
	base := sb.GetAttrByName("PAS")*0.3 +
		wf.GetAttrByName("DRI")*0.3 +
		math.Min(sb.GetAttrByName("STA"), wf.GetAttrByName("STA"))*0.4
	return applySkillAttack(wf, base)
}

func CalcOverlapDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("STA")*0.2
	return applySkillDefense(defender, base)
}

// TrianglePass (3 attackers vs 2 defenders)
func CalcTriangleAttack(p1, p2, p3 *domain.PlayerRuntime) float64 {
	base := p1.GetAttrByName("PAS")*0.25 +
		p2.GetAttrByName("PAS")*0.25 +
		p3.GetAttrByName("DRI")*0.2 +
		math.Min(p1.GetAttrByName("COM"), math.Min(p2.GetAttrByName("COM"), p3.GetAttrByName("COM")))*0.3
	return applySkillAttack(p3, base)
}

func CalcTriangleDefense(d1, d2 *domain.PlayerRuntime) float64 {
	base := d1.GetAttrByName("DEF")*0.4 +
		d2.GetAttrByName("DEF")*0.3 +
		math.Min(d1.GetAttrByName("COM"), d2.GetAttrByName("COM"))*0.3
	return applySkillDefense(d2, base)
}

// OneTwo (give-and-go, 2 attackers vs 1 defender)
func CalcOneTwoAttack(p1, p2 *domain.PlayerRuntime) float64 {
	base := p1.GetAttrByName("PAS")*0.35 +
		p2.GetAttrByName("DRI")*0.35 +
		p2.GetAttrByName("ACC")*0.3
	return applySkillAttack(p2, base)
}

func CalcOneTwoDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("TKL")*0.2
	return applySkillDefense(defender, base)
}

// CrossRun (2 attackers swap positions)
func CalcCrossRunAttack(p1, p2 *domain.PlayerRuntime) float64 {
	base := p1.GetAttrByName("DRI")*0.3 +
		p2.GetAttrByName("SPD")*0.3 +
		math.Max(p1.GetAttrByName("VIS"), p2.GetAttrByName("VIS"))*0.4
	return applySkillAttack(p2, base)
}

func CalcCrossRunDefense(defender *domain.PlayerRuntime) float64 {
	base := defender.GetAttrByName("DEF")*0.5 +
		defender.GetAttrByName("SPD")*0.3 +
		defender.GetAttrByName("POS")*0.2
	return applySkillDefense(defender, base)
}

// DoubleTeam (2 defenders vs 1 attacker)
func CalcDoubleTeamAttack(d1, d2 *domain.PlayerRuntime) float64 {
	base := d1.GetAttrByName("DEF")*0.3 +
		d1.GetAttrByName("TKL")*0.2 +
		d2.GetAttrByName("DEF")*0.3 +
		d2.GetAttrByName("TKL")*0.2
	return applySkillAttack(d2, base)
}

func CalcDoubleTeamDefense(attacker *domain.PlayerRuntime) float64 {
	base := attacker.GetAttrByName("DRI")*0.4 +
		attacker.GetAttrByName("CON")*0.3 +
		attacker.GetAttrByName("STR")*0.3
	return applySkillDefense(attacker, base)
}

// PressTogether (2 defenders pressing together)
func CalcPressTogetherAttack(d1, d2 *domain.PlayerRuntime) float64 {
	base := d1.GetAttrByName("STA")*0.3 +
		d1.GetAttrByName("TKL")*0.2 +
		d2.GetAttrByName("STA")*0.3 +
		d2.GetAttrByName("TKL")*0.2
	return applySkillAttack(d2, base)
}

func CalcPressTogetherDefense(holder *domain.PlayerRuntime) float64 {
	base := holder.GetAttrByName("PAS")*0.3 +
		holder.GetAttrByName("CON")*0.3 +
		holder.GetAttrByName("COM")*0.4
	return applySkillDefense(holder, base)
}

// applySkillAttack adds skill attack bonus to a base value
func applySkillAttack(player *domain.PlayerRuntime, base float64) float64 {
	if player == nil {
		return base
	}
	ctx := SkillContext{EventType: player.SkillEventType, Player: player, Zone: player.SkillZone, Minute: player.SkillMinute, Half: player.SkillHalf}
	bonus := ComputeSkillBonus(ctx)
	if bonus.AttackMod != 0 && bonus.NarrativeSuffix != "" {
		player.LastSkillSuffix = bonus.NarrativeSuffix
	}
	return base + bonus.AttackMod
}

// applySkillDefense adds skill defense bonus to a base value
func applySkillDefense(player *domain.PlayerRuntime, base float64) float64 {
	if player == nil {
		return base
	}
	ctx := SkillContext{EventType: player.SkillEventType, Player: player, Zone: player.SkillZone, Minute: player.SkillMinute, Half: player.SkillHalf}
	bonus := ComputeSkillBonus(ctx)
	if bonus.DefenseMod != 0 && bonus.NarrativeSuffix != "" {
		player.LastSkillSuffix = bonus.NarrativeSuffix
	}
	return base + bonus.DefenseMod
}
