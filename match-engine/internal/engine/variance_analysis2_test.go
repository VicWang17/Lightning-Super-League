package engine

import (
	"fmt"
	"math"
	"sort"
	"testing"

	"match-engine/internal/domain"
)

func TestVarianceDeepAnalysis(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())

	type MatchStats struct {
		HG, AG, HS, AS, HSoT, ASoT int
		HP, AP int
		HPK, APK int
		HSaveRate, ASaveRate float64
		ShotsDiff int
	}
	var matches []MatchStats

	for i := 0; i < 200; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("v%d", i),
			HomeTeam:      home,
			AwayTeam:      away,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)

		// Count PK goals from events
		hpk, apk := 0, 0
		for _, ev := range result.Events {
			if ev.Type == "free_kick" && ev.Detail == "penalty" && ev.Result == "goal" {
				if ev.Team == "home" { hpk++ } else { apk++ }
			}
		}

		// Approximate save rate: ShotsOnTarget - Goals / ShotsOnTarget
		var hsr, asr float64
		if result.Stats.ShotsOnTargetHome > 0 {
			hsr = float64(result.Stats.ShotsOnTargetHome-result.Score.Home) / float64(result.Stats.ShotsOnTargetHome)
		}
		if result.Stats.ShotsOnTargetAway > 0 {
			asr = float64(result.Stats.ShotsOnTargetAway-result.Score.Away) / float64(result.Stats.ShotsOnTargetAway)
		}

		ms := MatchStats{
			HG: result.Score.Home, AG: result.Score.Away,
			HS: result.Stats.ShotsHome, AS: result.Stats.ShotsAway,
			HSoT: result.Stats.ShotsOnTargetHome, ASoT: result.Stats.ShotsOnTargetAway,
			HP: result.Stats.PassesHome, AP: result.Stats.PassesAway,
			HPK: hpk, APK: apk,
			HSaveRate: hsr, ASaveRate: asr,
			ShotsDiff: result.Stats.ShotsHome - result.Stats.ShotsAway,
		}
		matches = append(matches, ms)
	}

	// Shot conversion rate per match
	var hConv, aConv []float64
	var totalGoals, totalShots int
	for _, m := range matches {
		if m.HS > 0 { hConv = append(hConv, float64(m.HG)/float64(m.HS)) }
		if m.AS > 0 { aConv = append(aConv, float64(m.AG)/float64(m.AS)) }
		totalGoals += m.HG + m.AG
		totalShots += m.HS + m.AS
	}

	avgConv := float64(totalGoals) / float64(totalShots)

	stats := func(name string, arr []float64) {
		var sum float64
		for _, v := range arr { sum += v }
		mean := sum / float64(len(arr))
		var sq float64
		for _, v := range arr {
			d := v - mean
			sq += d * d
		}
		std := math.Sqrt(sq / float64(len(arr)))
		t.Logf("%s: mean=%.1f%% std=%.1f%% CV=%.1f%% n=%d", name, mean*100, std*100, std/mean*100, len(arr))
	}

	t.Logf("=== DEEP VARIANCE ANALYSIS (200 matches) ===")
	stats("Home Shot Conversion", hConv)
	stats("Away Shot Conversion", aConv)
	t.Logf("Overall shot conversion: %.1f%%", avgConv*100)

	// Save rate stats
	var hSaves, aSaves []float64
	for _, m := range matches {
		if m.HSoT > 0 { hSaves = append(hSaves, m.HSaveRate) }
		if m.ASoT > 0 { aSaves = append(aSaves, m.ASaveRate) }
	}
	stats("Home Save Rate", hSaves)
	stats("Away Save Rate", aSaves)

	// PK contribution
	var pkGoals int
	for _, m := range matches { pkGoals += m.HPK + m.APK }
	t.Logf("PK goals per match: %.2f (%d/%d total goals = %.1f%%)", float64(pkGoals)/200, pkGoals, totalGoals, float64(pkGoals)*100/float64(totalGoals))

	// Distribution of shot conversion
	sort.Float64s(hConv)
	t.Logf("Home conversion percentiles: P10=%.0f%% P25=%.0f%% P50=%.0f%% P75=%.0f%% P90=%.0f%%",
		hConv[len(hConv)*10/100]*100, hConv[len(hConv)*25/100]*100,
		hConv[len(hConv)*50/100]*100, hConv[len(hConv)*75/100]*100,
		hConv[len(hConv)*90/100]*100)

	// Blowout correlation with shot difference
	var blowoutShotsDiff []int
	for _, m := range matches {
		if math.Abs(float64(m.HG-m.AG)) >= 4 {
			blowoutShotsDiff = append(blowoutShotsDiff, m.ShotsDiff)
		}
	}
	if len(blowoutShotsDiff) > 0 {
		var sum int
		for _, d := range blowoutShotsDiff { sum += d }
		t.Logf("Blowouts (>=4): %d. Avg shot diff in blowouts: %.1f", len(blowoutShotsDiff), float64(sum)/float64(len(blowoutShotsDiff)))
	}

	// Identify extreme matches
	t.Logf("\n=== EXTREME MATCHES ===")
	for _, m := range matches {
		if m.HG >= 10 || m.AG >= 10 || math.Abs(float64(m.HG-m.AG)) >= 7 {
			t.Logf("Score %d-%d | Shots %d-%d | SoT %d-%d | Conv %.0f%%-%.0f%% | Saves %.0f%%-%.0f%% | Passes %d-%d | PK %d-%d",
				m.HG, m.AG, m.HS, m.AS, m.HSoT, m.ASoT,
				float64(m.HG)*100/float64(max(1,m.HS)), float64(m.AG)*100/float64(max(1,m.AS)),
				m.HSaveRate*100, m.ASaveRate*100, m.HP, m.AP, m.HPK, m.APK)
		}
	}
}

func max(a, b int) int { if a > b { return a }; return b }
