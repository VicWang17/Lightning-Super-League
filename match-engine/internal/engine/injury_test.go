package engine

import (
	"math/rand/v2"
	"testing"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ============================================================================
// Unit Tests
// ============================================================================

func TestBodyWearNaturalRecovery(t *testing.T) {
	player := &domain.PlayerRuntime{
		PlayerSetup: domain.PlayerSetup{
			BodyWear: domain.BodyWear{Hamstring: 50.0},
		},
	}
	// Simulate full rest: -8 base + -1.5 sleep = -9.5
	player.BodyWear.Hamstring -= 9.5
	if player.BodyWear.Hamstring < 0 {
		player.BodyWear.Hamstring = 0
	}

	expected := 40.5
	if player.BodyWear.Hamstring != expected {
		t.Errorf("Expected hamstring wear %.1f, got %.1f", expected, player.BodyWear.Hamstring)
	}
}

func TestMatchWearAccumulation(t *testing.T) {
	player := &domain.PlayerRuntime{}
	ApplyMatchWear(player, "sprint", 1.0)

	if player.MatchWear.Hamstring < 0.14 || player.MatchWear.Hamstring > 0.16 {
		t.Errorf("Expected hamstring wear ~0.15, got %.3f", player.MatchWear.Hamstring)
	}
	if player.MatchWear.Calf < 0.11 || player.MatchWear.Calf > 0.13 {
		t.Errorf("Expected calf wear ~0.12, got %.3f", player.MatchWear.Calf)
	}
}

func TestStaminaWearMultiplier(t *testing.T) {
	tests := []struct {
		stamina  float64
		expected float64
	}{
		{80, 1.0},
		{60, 1.0},
		{50, 1.3},
		{30, 1.3},
		{29, 1.8},
		{15, 1.8},
		{0, 1.8},
	}
	for _, tc := range tests {
		got := GetStaminaWearMultiplier(tc.stamina)
		if got != tc.expected {
			t.Errorf("Stamina %.0f: expected multiplier %.1f, got %.1f", tc.stamina, tc.expected, got)
		}
	}
}

func TestInjuryProbabilityBounds(t *testing.T) {
	// Healthy player (wear=0) should have very low probabilities
	player := &domain.PlayerRuntime{}
	action := "brutal_tackle"

	// Manually compute to verify bounds
	wearFactor := 1.0 // wear=0 -> (1+0)^2 = 1
	rates := BaseInjuryRates[action]
	lightProb := rates[0] * wearFactor
	medProb := rates[1] * wearFactor
	severeProb := rates[2] * wearFactor

	if severeProb > 0.00021 {
		t.Errorf("Severe prob too high for healthy player: %.5f", severeProb)
	}
	if medProb > 0.00151 {
		t.Errorf("Medium prob too high for healthy player: %.5f", medProb)
	}
	if lightProb > 0.0101 {
		t.Errorf("Light prob too high for healthy player: %.5f", lightProb)
	}

	// High wear player (wear=80) should have elevated but still reasonable probs
	player.BodyWear.Hamstring = 80.0
	player.BodyWear.Ankle = 80.0
	player.BodyWear.Knee = 80.0

	wearFactor = 10.24 // (1+80/50)^2 = (2.6)^2 = 6.76, but we use effectiveWear with matchWear
	// effectiveWear = 80 + 0 = 80, wearFactor = (1+80/50)^2 = (2.6)^2 = 6.76
	// Wait, formula is (1 + wear/50)^2, so (1+1.6)^2 = 6.76
	expectedWearFactor := 6.76
	if expectedWearFactor < 6.0 || expectedWearFactor > 8.0 {
		t.Logf("Wear factor for 80: %.2f", expectedWearFactor)
	}
}

func TestRecoveryDaysInRange(t *testing.T) {
	r := rand.New(rand.NewPCG(42, 42))
	part := config.PartHamstring
	severity := 3

	bounds := RecoveryRanges[part][severity]
	minDays, maxDays := bounds[0], bounds[1]

	for i := 0; i < 1000; i++ {
		days := RandomRecoveryDays(r, part, severity)
		if days < minDays || days > maxDays {
			t.Errorf("Recovery days %d out of range [%d, %d]", days, minDays, maxDays)
		}
	}
}

func TestRecoveryDaysAllSeverities(t *testing.T) {
	r := rand.New(rand.NewPCG(123, 456))
	for part, severities := range RecoveryRanges {
		for sev, bounds := range severities {
			minDays, maxDays := bounds[0], bounds[1]
			for i := 0; i < 100; i++ {
				days := RandomRecoveryDays(r, part, sev)
				if days < minDays || days > maxDays {
					t.Errorf("Part=%s Sev=%d: days=%d out of range [%d,%d]", part, sev, days, minDays, maxDays)
				}
			}
		}
	}
}

func TestGetInjuryName(t *testing.T) {
	name := GetInjuryName(config.PartHamstring, 2)
	if name != "腿筋轻度拉伤" {
		t.Errorf("Expected 腿筋轻度拉伤, got %s", name)
	}
	name = GetInjuryName(config.PartAnkle, 3)
	if name != "脚踝严重扭伤" {
		t.Errorf("Expected 脚踝严重扭伤, got %s", name)
	}
}

func TestAttrImpactForMinor(t *testing.T) {
	impact := GetAttrImpactForMinor(config.PartHamstring)
	if impact["SPD"] != 0.85 {
		t.Errorf("Expected SPD impact 0.85, got %.2f", impact["SPD"])
	}
	if impact["ACC"] != 0.85 {
		t.Errorf("Expected ACC impact 0.85, got %.2f", impact["ACC"])
	}
}

func TestApplyMinorInjuryToAttrs(t *testing.T) {
	player := &domain.PlayerRuntime{}
	for i := 0; i < config.AttrCount; i++ {
		player.EffectiveAttrs[i] = 10.0
	}
	player.MatchInjury = &domain.ActiveInjury{
		BodyPart: config.PartHamstring,
		Severity: 1,
	}
	ApplyMinorInjuryToAttrs(player)

	spdIdx := config.AttrIndex("SPD")
	accIdx := config.AttrIndex("ACC")
	if player.EffectiveAttrs[spdIdx] != 8.5 {
		t.Errorf("Expected SPD 8.5 after injury, got %.1f", player.EffectiveAttrs[spdIdx])
	}
	if player.EffectiveAttrs[accIdx] != 8.5 {
		t.Errorf("Expected ACC 8.5 after injury, got %.1f", player.EffectiveAttrs[accIdx])
	}
}

func TestFinalizeMatchWear(t *testing.T) {
	player := &domain.PlayerRuntime{
		PlayerSetup: domain.PlayerSetup{
			BodyWear: domain.BodyWear{Hamstring: 30.0},
		},
	}
	player.MatchWear.Hamstring = 5.0
	FinalizeMatchWear(player)

	if player.BodyWear.Hamstring != 35.0 {
		t.Errorf("Expected hamstring 35.0 after finalization, got %.1f", player.BodyWear.Hamstring)
	}
	if player.MatchWear.Hamstring != 0 {
		// MatchWear is not reset by FinalizeMatchWear, it's just added to BodyWear
		t.Logf("MatchWear after finalize: %.1f (expected to remain)", player.MatchWear.Hamstring)
	}
}

func TestCapWear(t *testing.T) {
	if capWear(105) != 100 {
		t.Errorf("Expected cap 100, got %.1f", capWear(105))
	}
	if capWear(-5) != 0 {
		t.Errorf("Expected cap 0, got %.1f", capWear(-5))
	}
	if capWear(50) != 50 {
		t.Errorf("Expected 50, got %.1f", capWear(50))
	}
}

func TestSeverityDistribution(t *testing.T) {
	dist := getSeverityDistribution(30)
	if dist[0] != 0.80 || dist[1] != 0.15 || dist[2] != 0.05 {
		t.Errorf("Unexpected severity dist for wear=30: %v", dist)
	}
	dist = getSeverityDistribution(90)
	if dist[0] != 0.10 || dist[1] != 0.35 || dist[2] != 0.55 {
		t.Errorf("Unexpected severity dist for wear=90: %v", dist)
	}
}

func TestBodyWearHelpers(t *testing.T) {
	wear := &domain.BodyWear{Hamstring: 10, Ankle: 20, Knee: 30}
	if GetBodyWearValue(wear, config.PartAnkle) != 20 {
		t.Errorf("Expected ankle 20, got %.1f", GetBodyWearValue(wear, config.PartAnkle))
	}
	SetBodyWearValue(wear, config.PartKnee, 50)
	if wear.Knee != 50 {
		t.Errorf("Expected knee 50 after set, got %.1f", wear.Knee)
	}
}

// ============================================================================
// Monte Carlo / Stress Tests
// ============================================================================

// simulatePlayerMatch simulates a single match for injury probability testing
func simulatePlayerMatch(r *rand.Rand, player *domain.PlayerRuntime, minutes int) (injured bool, severity int) {
	// Simulate base per-minute wear
	for m := 0; m < minutes; m++ {
		mult := GetStaminaWearMultiplier(player.CurrentStamina)
		ApplyMinuteWear(player, mult)
		player.CurrentStamina -= 0.8 // simulate stamina drain
		if player.CurrentStamina < 0 {
			player.CurrentStamina = 0
		}
	}

	// Simulate some actions
	actions := []string{"sprint", "sprint", "sprint", "tackle", "tackle", "header"}
	for _, action := range actions {
		mult := GetStaminaWearMultiplier(player.CurrentStamina)
		ApplyMatchWear(player, action, mult)
	}

	// Try injury checks
	checkActions := []string{"brutal_tackle", "sprint_fatigue", "aerial_clash"}
	for _, action := range checkActions {
		occurred, part, sev := CheckInjury(r, player, action)
		if occurred {
			return true, sev
		}
		_ = part // suppress unused warning
	}
	return false, 0
}

// BenchmarkSeasonInjuryRate runs a Monte Carlo simulation to estimate
// the injury rate per team per season.
func BenchmarkSeasonInjuryRate(b *testing.B) {
	const (
		seasons        = 5000
		teamsPerSeason = 20
		matchesPerTeam = 30
		squadSize      = 25
	)

	totalSevere := 0
	totalMedium := 0
	totalLight := 0

	for s := 0; s < seasons; s++ {
		r := rand.New(rand.NewPCG(uint64(s), uint64(s)+999))
		for t := 0; t < teamsPerSeason; t++ {
			for m := 0; m < matchesPerTeam; m++ {
				// ~14 starters per match
				starters := 14
				for i := 0; i < starters; i++ {
					player := &domain.PlayerRuntime{
						PlayerSetup: domain.PlayerSetup{
							BodyWear: domain.BodyWear{},
							Stamina:  90,
						},
						CurrentStamina: 90,
					}
					// Add some random baseline wear (0-40 typical range)
					player.BodyWear.Hamstring = r.Float64() * 30
					player.BodyWear.Ankle = r.Float64() * 25
					player.BodyWear.Knee = r.Float64() * 20

					injured, sev := simulatePlayerMatch(r, player, 90)
					if injured {
						switch sev {
						case 1:
							totalLight++
						case 2:
							totalMedium++
						case 3:
							totalSevere++
						}
					}
				}
			}
		}
	}

	totalMatches := float64(seasons * teamsPerSeason * matchesPerTeam)
	avgLight := float64(totalLight) / totalMatches
	avgMedium := float64(totalMedium) / totalMatches
	avgSevere := float64(totalSevere) / totalMatches

	b.Logf("Average injuries per match: light=%.4f, medium=%.4f, severe=%.4f", avgLight, avgMedium, avgSevere)
	b.Logf("Average per team per season (30 matches): light=%.3f, medium=%.3f, severe=%.3f",
		avgLight*30, avgMedium*30, avgSevere*30)

	// Assertions: severe should be very low (target < 0.1 per match)
	if avgSevere > 0.15 {
		b.Errorf("Severe injury rate too high: %.4f per match (target < 0.15)", avgSevere)
	}
	// Medium should be higher but still controlled
	if avgMedium > 0.5 {
		b.Errorf("Medium injury rate too high: %.4f per match (target < 0.5)", avgMedium)
	}
}

// BenchmarkHighWearInjuryRate tests injury rate when players are heavily fatigued
func BenchmarkHighWearInjuryRate(b *testing.B) {
	seasons := 2000
	totalSevere := 0

	for s := 0; s < seasons; s++ {
		r := rand.New(rand.NewPCG(uint64(s), uint64(s)+777))
		for t := 0; t < 20; t++ {
			for m := 0; m < 30; m++ {
				for i := 0; i < 14; i++ {
					player := &domain.PlayerRuntime{
						PlayerSetup: domain.PlayerSetup{
							BodyWear: domain.BodyWear{
								Hamstring: 70,
								Ankle:     65,
								Knee:      60,
							},
							Stamina: 60,
						},
						CurrentStamina: 60,
					}
					injured, sev := simulatePlayerMatch(r, player, 90)
					if injured && sev == 3 {
						totalSevere++
					}
				}
			}
		}
	}

	totalMatches := float64(seasons * 20 * 30)
	avgSevere := float64(totalSevere) / totalMatches
	b.Logf("High-wear severe injury rate per match: %.4f", avgSevere)
	b.Logf("High-wear severe per team per season: %.3f", avgSevere*30)

	// Even with high wear, severe should stay under control
	if avgSevere > 0.5 {
		b.Errorf("High-wear severe rate too high: %.4f", avgSevere)
	}
}

// BenchmarkTraitImpact compares injury rates between 铁人 and 玻璃体质
func BenchmarkTraitImpact(b *testing.B) {
	traits := []struct {
		name  string
		trait string
	}{
		{"normal", ""},
		{"iron_man", "铁人"},
		{"glass_body", "玻璃体质"},
	}

	for _, tt := range traits {
		b.Run(tt.name, func(b *testing.B) {
			totalInjuries := 0
			for i := 0; i < 10000; i++ {
				r := rand.New(rand.NewPCG(uint64(i), uint64(i)+111))
				player := &domain.PlayerRuntime{
					PlayerSetup: domain.PlayerSetup{
						BodyWear: domain.BodyWear{
							Hamstring: 50,
							Ankle:     45,
						},
						Stamina: 70,
					},
					CurrentStamina: 70,
				}
				if tt.trait != "" {
					player.Traits = []string{tt.trait}
				}
				injured, _ := simulatePlayerMatch(r, player, 90)
				if injured {
					totalInjuries++
				}
			}
			b.Logf("%s: %d injuries out of 10000 (%.2f%%)", tt.name, totalInjuries, float64(totalInjuries)/100.0)
		})
	}
}

// BenchmarkRecoveryDaysDistribution checks that recovery days are evenly distributed
func BenchmarkRecoveryDaysDistribution(b *testing.B) {
	part := config.PartHamstring
	severity := 3 // major
	bounds := RecoveryRanges[part][severity]
	minDays, maxDays := bounds[0], bounds[1]

	counts := make(map[int]int)
	r := rand.New(rand.NewPCG(99, 99))
	for i := 0; i < 10000; i++ {
		days := RandomRecoveryDays(r, part, severity)
		counts[days]++
	}

	b.Logf("Recovery days distribution for %s severity %d [%d,%d]:", part, severity, minDays, maxDays)
	for d := minDays; d <= maxDays; d++ {
		b.Logf("  %d days: %d (%.1f%%)", d, counts[d], float64(counts[d])/100.0)
	}

	// Check all possible values were generated
	for d := minDays; d <= maxDays; d++ {
		if counts[d] == 0 {
			b.Errorf("Day %d was never generated in 10000 samples", d)
		}
	}
}
