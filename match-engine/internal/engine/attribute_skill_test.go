package engine

import (
	"fmt"
	"testing"

	"match-engine/internal/domain"
)

// runAttributeBatch runs n matches with home having attr+delta and returns aggregated stats.
func runAttributeBatch(home, away domain.TeamSetup, n int) struct {
	HomeWins, Draws, AwayWins int
	HomeGoals, AwayGoals      float64
	HomeShots, AwayShots      float64
	HomePasses, AwayPasses    float64
	HomePassAcc, AwayPassAcc  float64
	HomeDrib, AwayDrib        float64
	HomeDribAcc, AwayDribAcc  float64
	HomeTack, AwayTack        float64
	HomeTackAcc, AwayTackAcc  float64
	HomePoss                  float64
} {
	var r struct {
		HomeWins, Draws, AwayWins int
		HomeGoals, AwayGoals      float64
		HomeShots, AwayShots      float64
		HomePasses, AwayPasses    float64
		HomePassAcc, AwayPassAcc  float64
		HomeDrib, AwayDrib        float64
		HomeDribAcc, AwayDribAcc  float64
		HomeTack, AwayTack        float64
		HomeTackAcc, AwayTackAcc  float64
		HomePoss                  float64
	}
	for i := 0; i < n; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("attr_%d", i),
			HomeTeam:      home,
			AwayTeam:      away,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)
		s := result.Stats

		if result.Score.Home > result.Score.Away {
			r.HomeWins++
		} else if result.Score.Home == result.Score.Away {
			r.Draws++
		} else {
			r.AwayWins++
		}
		r.HomeGoals += float64(result.Score.Home)
		r.AwayGoals += float64(result.Score.Away)
		r.HomeShots += float64(s.ShotsHome)
		r.AwayShots += float64(s.ShotsAway)
		r.HomePasses += float64(s.PassesHome)
		r.AwayPasses += float64(s.PassesAway)
		r.HomePassAcc += s.PassAccuracyHome
		r.AwayPassAcc += s.PassAccuracyAway
		r.HomeDrib += float64(s.DribblesHome)
		r.AwayDrib += float64(s.DribblesAway)
		r.HomeDribAcc += s.DribbleAccuracyHome
		r.AwayDribAcc += s.DribbleAccuracyAway
		r.HomeTack += float64(s.TacklesHome)
		r.AwayTack += float64(s.TacklesAway)
		r.HomeTackAcc += s.TackleAccuracyHome
		r.AwayTackAcc += s.TackleAccuracyAway
		r.HomePoss += s.PossessionHome
	}
	fn := float64(n)
	r.HomeGoals /= fn
	r.AwayGoals /= fn
	r.HomeShots /= fn
	r.AwayShots /= fn
	r.HomePasses /= fn
	r.AwayPasses /= fn
	r.HomePassAcc /= fn
	r.AwayPassAcc /= fn
	r.HomeDrib /= fn
	r.AwayDrib /= fn
	r.HomeDribAcc /= fn
	r.AwayDribAcc /= fn
	r.HomeTack /= fn
	r.AwayTack /= fn
	r.HomeTackAcc /= fn
	r.AwayTackAcc /= fn
	r.HomePoss /= fn
	return r
}

// TestAttributeImpact validates that each attribute change produces measurable impact.
func TestAttributeImpact(t *testing.T) {
	attrs := baseAttrs()
	baseHome := buildTeam("Home", attrs, defaultTactics())
	baseAway := buildTeam("Away", attrs, defaultTactics())

	t.Log("\n========== ATTRIBUTE IMPACT (+3, 200 matches each) ==========")

	attrTests := []struct {
		Attr     string
		Delta    int
		Expect   string
		MinWin   float64 // minimum acceptable win rate %
		Check    func(base, mod struct{
			HomeWins, Draws, AwayWins int
			HomeGoals, AwayGoals      float64
			HomeShots, AwayShots      float64
			HomePasses, AwayPasses    float64
			HomePassAcc, AwayPassAcc  float64
			HomeDrib, AwayDrib        float64
			HomeDribAcc, AwayDribAcc  float64
			HomeTack, AwayTack        float64
			HomeTackAcc, AwayTackAcc  float64
			HomePoss                  float64
		}) bool
		CheckMsg string
	}{
		{"SHO", +3, "射门数↑", 52, nil, ""},
		{"PAS", +3, "传球准确率↑", 52, nil, ""},
		{"DRI", +3, "过人尝试↑", 52, nil, ""},
		{"SPD", +3, "控球率↑", 52, nil, ""},
		{"STR", +3, "身体对抗优势", 52, nil, ""},
		{"DEF", +3, "被射门数↓", 52, nil, ""},
		{"HEA", +3, "头球优势", 52, nil, ""},
		{"FIN", +3, "射门转化率↑", 55, nil, ""},
		{"BAL", +3, "平衡性优势", 52, nil, ""},
		{"ACC", +3, "加速度优势", 52, nil, ""},
		{"CRO", +3, "传中优势", 52, nil, ""},
		{"CON", +3, "体能优势", 52, nil, ""},
		{"VIS", +3, "视野/关键传球↑", 52, nil, ""},
		{"TKL", +3, "抢断优势", 52, nil, ""},
		{"COM", +3, "冷静度优势", 52, nil, ""},
		{"POS", +3, "站位优势", 52, nil, ""},
		{"FK", +3, "任意球优势", 52, nil, ""},
		{"PK", +3, "点球优势", 52, nil, ""},
		{"RUS", +3, "出击优势(GK)", 52, nil, ""},
		{"DEC", +3, "决策优势", 52, nil, ""},
	}

	// Baseline
	baseResult := runAttributeBatch(baseHome, baseAway, 200)
	baseWinRate := float64(baseResult.HomeWins) / 200.0 * 100
	t.Logf("BASELINE: Win %.1f%% | Goals %.2f-%.2f | Shots %.1f-%.1f | PassAcc %.1f-%.1f | Drib %.1f-%.1f | Tack %.1f-%.1f | Poss %.1f",
		baseWinRate, baseResult.HomeGoals, baseResult.AwayGoals,
		baseResult.HomeShots, baseResult.AwayShots,
		baseResult.HomePassAcc, baseResult.AwayPassAcc,
		baseResult.HomeDrib, baseResult.AwayDrib,
		baseResult.HomeTack, baseResult.AwayTack,
		baseResult.HomePoss)

	// Test each attribute
	for _, at := range attrTests {
		modHome := buildTeam("Home", cloneAttrs(attrs), defaultTactics())
		modHome = modifyTeamAttr(modHome, at.Attr, at.Delta)
		modResult := runAttributeBatch(modHome, baseAway, 200)
		winRate := float64(modResult.HomeWins) / 200.0 * 100
		winDelta := winRate - baseWinRate

		t.Logf("%-3s +%d: Win %.1f%% (delta %+.1f%%) | Goals %.2f-%.2f | Shots %.1f-%.1f | PassAcc %.1f-%.1f | Drib %.1f-%.1f | Tack %.1f-%.1f | Poss %.1f",
			at.Attr, at.Delta, winRate, winDelta,
			modResult.HomeGoals, modResult.AwayGoals,
			modResult.HomeShots, modResult.AwayShots,
			modResult.HomePassAcc, modResult.AwayPassAcc,
			modResult.HomeDrib, modResult.AwayDrib,
			modResult.HomeTack, modResult.AwayTack,
			modResult.HomePoss)

		if winRate < at.MinWin {
			t.Errorf("%s +%d: win rate %.1f%% below minimum %.1f%% — attribute may be ineffective", at.Attr, at.Delta, winRate, at.MinWin)
		}
	}

	// GK-specific test
	t.Log("\n--- GK ATTRIBUTE TEST ---")
	for _, gkAttr := range []string{"SAV", "REF", "POS"} {
		modHome := buildTeam("Home", cloneAttrs(attrs), defaultTactics())
		modHome = modifyTeamAttr(modHome, gkAttr, +5)
		modResult := runAttributeBatch(modHome, baseAway, 200)
		winRate := float64(modResult.HomeWins) / 200.0 * 100
		t.Logf("GK %-3s +5: Win %.1f%% | Conceded %.2f", gkAttr, winRate, modResult.AwayGoals)
		if winRate < 55 {
			t.Errorf("GK %s +5: win rate %.1f%% below 55%%", gkAttr, winRate)
		}
	}
}

// TestSkillImpact validates that skills produce measurable impact (placeholder for future skills).
func TestSkillImpact(t *testing.T) {
	t.Skip("Skill system not yet implemented with measurable impact stats")
}
