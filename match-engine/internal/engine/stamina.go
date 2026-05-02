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
	case config.EventWingBreak, config.EventCutInside:
		return 2.2
	case config.EventCross:
		return 1.8
	case config.EventCloseShot, config.EventLongShot, config.EventHeader:
		return 2.5
	case config.EventTackle, config.EventIntercept, config.EventClearance:
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
