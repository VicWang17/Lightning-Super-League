package engine

import (
	"fmt"
	"math"
	"runtime"
	"sync"
	"testing"
	"time"

	"match-engine/internal/domain"
)

// runMatchesParallel runs count matches concurrently using workers goroutines.
func runMatchesParallel(count int, home, away domain.TeamSetup, workers int) []domain.SimulateResult {
	if workers <= 0 {
		workers = runtime.NumCPU()
	}
	results := make([]domain.SimulateResult, count)
	var wg sync.WaitGroup
	sem := make(chan struct{}, workers)

	for i := 0; i < count; i++ {
		wg.Add(1)
		sem <- struct{}{}
		go func(idx int) {
			defer wg.Done()
			req := domain.SimulateRequest{
				MatchID:       fmt.Sprintf("m%d", idx),
				HomeTeam:      home,
				AwayTeam:      away,
				HomeAdvantage: true,
			}
			sim := NewSimulator(uint64(idx) + uint64(time.Now().UnixNano()))
			results[idx] = sim.Simulate(req)
			<-sem
		}(i)
	}
	wg.Wait()
	return results
}

// statInt collects integer stats from match results.
func statInt(results []domain.SimulateResult, fn func(domain.SimulateResult) int) []int {
	vals := make([]int, len(results))
	for i, r := range results {
		vals[i] = fn(r)
	}
	return vals
}

// statFloat collects float64 stats from match results.
func statFloat(results []domain.SimulateResult, fn func(domain.SimulateResult) float64) []float64 {
	vals := make([]float64, len(results))
	for i, r := range results {
		vals[i] = fn(r)
	}
	return vals
}

func meanInt(arr []int) float64 {
	var sum int
	for _, v := range arr {
		sum += v
	}
	return float64(sum) / float64(len(arr))
}

func stdInt(arr []int) float64 {
	m := meanInt(arr)
	var sq float64
	for _, v := range arr {
		d := float64(v) - m
		sq += d * d
	}
	return math.Sqrt(sq / float64(len(arr)))
}

func meanFloat(arr []float64) float64 {
	var sum float64
	for _, v := range arr {
		sum += v
	}
	return sum / float64(len(arr))
}

func stdFloat(arr []float64) float64 {
	m := meanFloat(arr)
	var sq float64
	for _, v := range arr {
		d := v - m
		sq += d * d
	}
	return math.Sqrt(sq / float64(len(arr)))
}

func cvInt(arr []int) float64 {
	m := meanInt(arr)
	if m == 0 {
		return 0
	}
	return stdInt(arr) / m * 100
}

func cvFloat(arr []float64) float64 {
	m := meanFloat(arr)
	if m == 0 {
		return 0
	}
	return stdFloat(arr) / m * 100
}

func printStat(t *testing.T, name string, arr []int) {
	m := meanInt(arr)
	s := stdInt(arr)
	cv := cvInt(arr)
	t.Logf("%-28s mean=%6.2f std=%6.2f (CV=%5.1f%%)", name, m, s, cv)
}

func printStatF(t *testing.T, name string, arr []float64) {
	m := meanFloat(arr)
	s := stdFloat(arr)
	cv := cvFloat(arr)
	t.Logf("%-28s mean=%6.2f std=%6.2f (CV=%5.1f%%)", name, m, s, cv)
}

func assertRange(t *testing.T, name string, val float64, min, max float64) {
	if val < min || val > max {
		t.Errorf("FAIL %s = %.2f, expected [%.2f, %.2f]", name, val, min, max)
	}
}

func assertMax(t *testing.T, name string, val float64, max float64) {
	if val > max {
		t.Errorf("FAIL %s = %.2f, exceeds max %.2f", name, val, max)
	}
}

// TestRegression runs 500 matches and validates all statistical metrics.
func TestRegression(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())

	results := runMatchesParallel(500, home, away, runtime.NumCPU())

	// ----- collect basic arrays -----
	hg := statInt(results, func(r domain.SimulateResult) int { return r.Score.Home })
	ag := statInt(results, func(r domain.SimulateResult) int { return r.Score.Away })
	hs := statInt(results, func(r domain.SimulateResult) int { return r.Stats.ShotsHome })
	as := statInt(results, func(r domain.SimulateResult) int { return r.Stats.ShotsAway })
	hsot := statInt(results, func(r domain.SimulateResult) int { return r.Stats.ShotsOnTargetHome })
	asot := statInt(results, func(r domain.SimulateResult) int { return r.Stats.ShotsOnTargetAway })
	hpa := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.PassAccuracyHome })
	apa := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.PassAccuracyAway })
	hkp := statInt(results, func(r domain.SimulateResult) int { return r.Stats.KeyPassesHome })
	akp := statInt(results, func(r domain.SimulateResult) int { return r.Stats.KeyPassesAway })
	hc := statInt(results, func(r domain.SimulateResult) int { return r.Stats.CrossesHome })
	ac := statInt(results, func(r domain.SimulateResult) int { return r.Stats.CrossesAway })
	hca := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.CrossAccuracyHome })
	aca := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.CrossAccuracyAway })
	hd := statInt(results, func(r domain.SimulateResult) int { return r.Stats.DribblesHome })
	ad := statInt(results, func(r domain.SimulateResult) int { return r.Stats.DribblesAway })
	hda := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.DribbleAccuracyHome })
	ada := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.DribbleAccuracyAway })
	ht := statInt(results, func(r domain.SimulateResult) int { return r.Stats.TacklesHome })
	at := statInt(results, func(r domain.SimulateResult) int { return r.Stats.TacklesAway })
	hta := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.TackleAccuracyHome })
	ata := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.TackleAccuracyAway })
	hi := statInt(results, func(r domain.SimulateResult) int { return r.Stats.InterceptionsHome })
	ai := statInt(results, func(r domain.SimulateResult) int { return r.Stats.InterceptionsAway })
	hcl := statInt(results, func(r domain.SimulateResult) int { return r.Stats.ClearancesHome })
	acl := statInt(results, func(r domain.SimulateResult) int { return r.Stats.ClearancesAway })
	hb := statInt(results, func(r domain.SimulateResult) int { return r.Stats.BlocksHome })
	ab := statInt(results, func(r domain.SimulateResult) int { return r.Stats.BlocksAway })
	hh := statInt(results, func(r domain.SimulateResult) int { return r.Stats.HeadersHome })
	ah := statInt(results, func(r domain.SimulateResult) int { return r.Stats.HeadersAway })
	hha := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.HeaderAccuracyHome })
	hsa := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.HeaderAccuracyAway })
	hsv := statInt(results, func(r domain.SimulateResult) int { return r.Stats.SavesHome })
	asv := statInt(results, func(r domain.SimulateResult) int { return r.Stats.SavesAway })
	hco := statInt(results, func(r domain.SimulateResult) int { return r.Stats.CornersHome })
	aco := statInt(results, func(r domain.SimulateResult) int { return r.Stats.CornersAway })
	hf := statInt(results, func(r domain.SimulateResult) int { return r.Stats.FoulsHome })
	af := statInt(results, func(r domain.SimulateResult) int { return r.Stats.FoulsAway })
	hfd := statInt(results, func(r domain.SimulateResult) int { return r.Stats.FoulsDrawnHome })
	afd := statInt(results, func(r domain.SimulateResult) int { return r.Stats.FoulsDrawnAway })
	ho := statInt(results, func(r domain.SimulateResult) int { return r.Stats.OffsidesHome })
	ao := statInt(results, func(r domain.SimulateResult) int { return r.Stats.OffsidesAway })
	hyc := statInt(results, func(r domain.SimulateResult) int { return r.Stats.YellowCardsHome })
	ayc := statInt(results, func(r domain.SimulateResult) int { return r.Stats.YellowCardsAway })
	hrc := statInt(results, func(r domain.SimulateResult) int { return r.Stats.RedCardsHome })
	arc := statInt(results, func(r domain.SimulateResult) int { return r.Stats.RedCardsAway })
	hpos := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.PossessionHome })
	apos := statFloat(results, func(r domain.SimulateResult) float64 { return r.Stats.PossessionAway })

	// ----- derived -----
	totalGoals := make([]int, len(results))
	goalDiff := make([]int, len(results))
	var draws, blowouts, homeWins int
	var totalPK, totalPKG, totalFK, totalFKG int
	for i, r := range results {
		totalGoals[i] = r.Score.Home + r.Score.Away
		goalDiff[i] = r.Score.Home - r.Score.Away
		if r.Score.Home == r.Score.Away {
			draws++
		}
		if r.Score.Home > r.Score.Away {
			homeWins++
		}
		if math.Abs(float64(goalDiff[i])) >= 4 {
			blowouts++
		}
		totalPK += r.Stats.PenaltiesHome + r.Stats.PenaltiesAway
		totalPKG += r.Stats.PenaltyGoalsHome + r.Stats.PenaltyGoalsAway
		totalFK += r.Stats.FreeKicksHome + r.Stats.FreeKicksAway
		totalFKG += r.Stats.FreeKickGoalsHome + r.Stats.FreeKickGoalsAway
	}

	t.Log("\n========== REGRESSION REPORT (500 matches) ==========")

	t.Log("\n--- SCORE ---")
	printStat(t, "Home Goals", hg)
	printStat(t, "Away Goals", ag)
	printStat(t, "Total Goals", totalGoals)
	t.Logf("Draws: %d/500 = %.1f%%", draws, float64(draws)/5.0)
	t.Logf("Home Wins: %d/500 = %.1f%%", homeWins, float64(homeWins)/5.0)
	t.Logf("Blowouts (>=4 diff): %d/500 = %.1f%%", blowouts, float64(blowouts)/5.0)

	t.Log("\n--- ATTACKING ---")
	printStat(t, "Home Shots", hs)
	printStat(t, "Away Shots", as)
	printStat(t, "Home SoT", hsot)
	printStat(t, "Away SoT", asot)
	printStatF(t, "Home PassAcc", hpa)
	printStatF(t, "Away PassAcc", apa)
	printStat(t, "Home KeyPass", hkp)
	printStat(t, "Away KeyPass", akp)
	printStat(t, "Home Crosses", hc)
	printStat(t, "Away Crosses", ac)
	printStatF(t, "Home CrossAcc", hca)
	printStatF(t, "Away CrossAcc", aca)
	printStat(t, "Home Dribbles", hd)
	printStat(t, "Away Dribbles", ad)
	printStatF(t, "Home DribAcc", hda)
	printStatF(t, "Away DribAcc", ada)
	printStat(t, "Home Corners", hco)
	printStat(t, "Away Corners", aco)
	printStat(t, "Home Offsides", ho)
	printStat(t, "Away Offsides", ao)

	t.Log("\n--- DEFENSIVE ---")
	printStat(t, "Home Tackles", ht)
	printStat(t, "Away Tackles", at)
	printStatF(t, "Home TackAcc", hta)
	printStatF(t, "Away TackAcc", ata)
	printStat(t, "Home Interceptions", hi)
	printStat(t, "Away Interceptions", ai)
	printStat(t, "Home Clearances", hcl)
	printStat(t, "Away Clearances", acl)
	printStat(t, "Home Blocks", hb)
	printStat(t, "Away Blocks", ab)
	printStat(t, "Home Headers", hh)
	printStat(t, "Away Headers", ah)
	printStatF(t, "Home HeadAcc", hha)
	printStatF(t, "Away HeadAcc", hsa)
	printStat(t, "Home Saves", hsv)
	printStat(t, "Away Saves", asv)
	printStat(t, "Home Fouls", hf)
	printStat(t, "Away Fouls", af)
	printStat(t, "Home FoulsDrawn", hfd)
	printStat(t, "Away FoulsDrawn", afd)
	printStat(t, "Home YellowCards", hyc)
	printStat(t, "Away YellowCards", ayc)
	printStat(t, "Home RedCards", hrc)
	printStat(t, "Away RedCards", arc)

	t.Log("\n--- SPECIAL RATES ---")
	pkRate := 0.0
	if totalPK > 0 {
		pkRate = float64(totalPKG) / float64(totalPK) * 100
	}
	fkRate := 0.0
	if totalFK > 0 {
		fkRate = float64(totalFKG) / float64(totalFK) * 100
	}
	t.Logf("Penalty Rate:   %d/%d = %.1f%%", totalPKG, totalPK, pkRate)
	t.Logf("FreeKick Rate:  %d/%d = %.1f%%", totalFKG, totalFK, fkRate)

	t.Log("\n--- POSSESSION ---")
	printStatF(t, "Home Possession", hpos)
	printStatF(t, "Away Possession", apos)

	t.Log("\n--- ASSERTIONS ---")
	// Score
	assertRange(t, "Home Goals mean", meanInt(hg), 1.2, 2.8)
	assertRange(t, "Away Goals mean", meanInt(ag), 1.2, 2.8)
	assertMax(t, "Home Goals CV", cvInt(hg), 95)
	assertMax(t, "Away Goals CV", cvInt(ag), 100)
	assertMax(t, "Blowouts %", float64(blowouts)/5.0, 15)

	// Attack
	assertRange(t, "Home Shots mean", meanInt(hs), 8, 17)
	assertRange(t, "Away Shots mean", meanInt(as), 8, 17)
	assertMax(t, "Home Shots CV", cvInt(hs), 50)
	assertMax(t, "Away Shots CV", cvInt(as), 50)
	assertRange(t, "PassAcc mean", meanFloat(hpa), 70, 82)
	assertMax(t, "PassAcc CV", cvFloat(hpa), 10)
	assertRange(t, "Home Dribbles mean", meanInt(hd), 8, 15)
	assertRange(t, "Away Dribbles mean", meanInt(ad), 8, 15)
	assertMax(t, "Home DribAcc CV", cvFloat(hda), 40)
	assertMax(t, "Away DribAcc CV", cvFloat(ada), 40)

	// Defense
	assertRange(t, "Home Tackles mean", meanInt(ht), 12, 22)
	assertRange(t, "Away Tackles mean", meanInt(at), 12, 22)
	assertRange(t, "TackAcc mean", meanFloat(hta), 60, 78)
	assertMax(t, "TackAcc CV", cvFloat(hta), 25)
	assertRange(t, "Home Interceptions mean", meanInt(hi), 18, 28)
	assertRange(t, "Away Interceptions mean", meanInt(ai), 18, 28)

	// Special rates
	assertRange(t, "Penalty Rate", pkRate, 70, 85)
	assertRange(t, "FreeKick Rate", fkRate, 4, 15)

	// Possession balance
	assertRange(t, "Home Possession mean", meanFloat(hpos), 48, 52)
}
