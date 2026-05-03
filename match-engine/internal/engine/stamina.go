package engine

import (
	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ApplyStaminaDecay updates player effective attributes based on current stamina
func ApplyStaminaDecay(m *domain.MatchState) {
	for _, team := range []*domain.TeamRuntime{m.HomeTeam, m.AwayTeam} {
		for _, p := range team.PlayerRuntimes {
			// Apply stamina-based attribute modifiers
			stam := p.CurrentStamina
			var multiplier float64 = 1.0

			switch {
			case stam >= 70:
				multiplier = 1.0
			case stam >= 50:
				multiplier = 0.95
			case stam >= 30:
				multiplier = 0.90
			case stam >= 15:
				multiplier = 0.82
			default:
				multiplier = 0.75
			}

			for i := 0; i < config.AttrCount; i++ {
				base := float64(p.Attributes[config.AttrNames[i]])
				p.EffectiveAttrs[i] = base * multiplier
			}
			// Apply injury penalty
			if p.Injured {
				injuryMultiplier := 1.0
				switch p.InjurySeverity {
				case 1: // minor
					injuryMultiplier = 0.85
				case 2: // major
					injuryMultiplier = 0.60
				}
				for i := 0; i < config.AttrCount; i++ {
					p.EffectiveAttrs[i] *= injuryMultiplier
				}
			}
		}
	}
}

// ConsumeStamina deducts stamina for an event
func ConsumeStamina(p *domain.PlayerRuntime, intensity float64) {
	// Higher base STA means slower drain
	staFactor := 1.0 - (p.GetAttrByName("STA")-10.0)/30.0 // 10->1.0, 20->0.67
	if staFactor < 0.5 {
		staFactor = 0.5
	}
	p.CurrentStamina -= intensity * staFactor
	if p.CurrentStamina < 0 {
		p.CurrentStamina = 0
	}
}

// StaminaCost for event types
func StaminaCost(eventType string) float64 {
	switch eventType {
	case config.EventBackPass, config.EventMidPass, config.EventShortPass:
		return 0.6
	case config.EventLongPass, config.EventThroughBall:
		return 1.0
	case config.EventWingBreak, config.EventCutInside, config.EventDribblePast:
		return 2.2
	case config.EventCross:
		return 1.8
	case config.EventCloseShot, config.EventLongShot, config.EventHeader:
		return 2.5
	case config.EventTackle, config.EventIntercept, config.EventClearance:
		return 2.0
	case config.EventFreeKick:
		return 1.5
	// Phase 1: Simple 1v1 events
	case config.EventSwitchPlay, config.EventBlockPass:
		return 1.2
	case config.EventLobPass, config.EventPassOverTop:
		return 1.5
	case config.EventOneOnOne, config.EventShotBlock:
		return 2.5
	case config.EventCoverDefense:
		return 1.8
	// Phase 2: Medium events
	case config.EventGoalKick, config.EventThrowIn:
		return 1.0
	case config.EventKeeperShortPass, config.EventKeeperThrow:
		return 0.8
	case config.EventCounterAttack:
		return 2.8
	// Phase 3: Multi-player events
	case config.EventOverlap, config.EventOneTwo, config.EventCrossRun:
		return 2.2
	case config.EventTrianglePass:
		return 2.5
	case config.EventDoubleTeam, config.EventPressTogether:
		return 2.0
	default:
		return 0.8
	}
}

// HalftimeRecovery restores stamina at halftime
func HalftimeRecovery(m *domain.MatchState) {
	for _, team := range []*domain.TeamRuntime{m.HomeTeam, m.AwayTeam} {
		for _, p := range team.PlayerRuntimes {
			p.CurrentStamina += 30.0
			if p.CurrentStamina > 100 {
				p.CurrentStamina = 100
			}
		}
	}
}
