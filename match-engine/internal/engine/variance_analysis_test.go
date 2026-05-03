package engine

import (
	"fmt"
	"math"
	"testing"

	"match-engine/internal/domain"
)

func TestVarianceAnalysis(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())

	type MatchData struct {
		HG, AG int
		HS, AS int
		HSoT, ASoT int
		HP, AP int
		HPS, APS float64
		HKeyP, AKeyP int
		HCross, ACross int
		HCrossA, ACrossA float64
		HDrib, ADrib int
		HDribA, ADribA float64
		HTack, ATack int
		HTackA, ATackA float64
		HInter, AInter int
		HClear, AClear int
		HBlock, ABlock int
		HHead, AHead int
		HHeadA, AHeadA float64
		HSave, ASave int
		HCorner, ACorner int
		HFoul, AFoul int
		HFD, AFD int
		HOff, AOff int
		HYC, AYC int
		HRC, ARC int
		HFK, AFK int
		HFKG, AFKG int
		HPK, APK int
		HPKG, APKG int
		HPoss, APoss float64
		Diff int
	}
	var matches []MatchData

	for i := 0; i < 50; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("v%d", i),
			HomeTeam:      home,
			AwayTeam:      away,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)
		s := result.Stats
		matches = append(matches, MatchData{
			HG: result.Score.Home, AG: result.Score.Away,
			HS: s.ShotsHome, AS: s.ShotsAway,
			HSoT: s.ShotsOnTargetHome, ASoT: s.ShotsOnTargetAway,
			HP: s.PassesHome, AP: s.PassesAway,
			HPS: s.PassAccuracyHome, APS: s.PassAccuracyAway,
			HKeyP: s.KeyPassesHome, AKeyP: s.KeyPassesAway,
			HCross: s.CrossesHome, ACross: s.CrossesAway,
			HCrossA: s.CrossAccuracyHome, ACrossA: s.CrossAccuracyAway,
			HDrib: s.DribblesHome, ADrib: s.DribblesAway,
			HDribA: s.DribbleAccuracyHome, ADribA: s.DribbleAccuracyAway,
			HTack: s.TacklesHome, ATack: s.TacklesAway,
			HTackA: s.TackleAccuracyHome, ATackA: s.TackleAccuracyAway,
			HInter: s.InterceptionsHome, AInter: s.InterceptionsAway,
			HClear: s.ClearancesHome, AClear: s.ClearancesAway,
			HBlock: s.BlocksHome, ABlock: s.BlocksAway,
			HHead: s.HeadersHome, AHead: s.HeadersAway,
			HHeadA: s.HeaderAccuracyHome, AHeadA: s.HeaderAccuracyAway,
			HSave: s.SavesHome, ASave: s.SavesAway,
			HCorner: s.CornersHome, ACorner: s.CornersAway,
			HFoul: s.FoulsHome, AFoul: s.FoulsAway,
			HFD: s.FoulsDrawnHome, AFD: s.FoulsDrawnAway,
			HOff: s.OffsidesHome, AOff: s.OffsidesAway,
			HYC: s.YellowCardsHome, AYC: s.YellowCardsAway,
			HRC: s.RedCardsHome, ARC: s.RedCardsAway,
			HFK: s.FreeKicksHome, AFK: s.FreeKicksAway,
			HFKG: s.FreeKickGoalsHome, AFKG: s.FreeKickGoalsAway,
			HPK: s.PenaltiesHome, APK: s.PenaltiesAway,
			HPKG: s.PenaltyGoalsHome, APKG: s.PenaltyGoalsAway,
			HPoss: s.PossessionHome, APoss: s.PossessionAway,
			Diff: result.Score.Home - result.Score.Away,
		})
	}

	mean := func(arr []int) float64 {
		var sum int
		for _, v := range arr { sum += v }
		return float64(sum) / float64(len(arr))
	}
	std := func(arr []int) float64 {
		m := mean(arr)
		var sq float64
		for _, v := range arr {
			d := float64(v) - m
			sq += d * d
		}
		return math.Sqrt(sq / float64(len(arr)))
	}
	meanF := func(arr []float64) float64 {
		var sum float64
		for _, v := range arr { sum += v }
		return sum / float64(len(arr))
	}
	stdF := func(arr []float64) float64 {
		m := meanF(arr)
		var sq float64
		for _, v := range arr {
			d := v - m
			sq += d * d
		}
		return math.Sqrt(sq / float64(len(arr)))
	}
	collect := func(fn func(MatchData) int) []int {
		var r []int
		for _, m := range matches { r = append(r, fn(m)) }
		return r
	}
	collectF := func(fn func(MatchData) float64) []float64 {
		var r []float64
		for _, m := range matches { r = append(r, fn(m)) }
		return r
	}

	t.Logf("Match-by-match (50 matches):")
	t.Logf("Match | Score | Shots(SoT) | Passes(Acc) | KeyP | Cross | Drib | Tack | Inter | Clear | Block | Head | Save | Corner | Foul | Offs | YC | Diff")
	for i, m := range matches {
		t.Logf("  %2d  | %2d-%2d | %2d-%2d(%2d-%2d) | %3d-%3d(%.0f-%.0f) | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %2d-%2d | %+d",
			i+1, m.HG, m.AG,
			m.HS, m.AS, m.HSoT, m.ASoT,
			m.HP, m.AP, m.HPS, m.APS,
			m.HKeyP, m.AKeyP,
			m.HCross, m.ACross,
			m.HDrib, m.ADrib,
			m.HTack, m.ATack,
			m.HInter, m.AInter,
			m.HClear, m.AClear,
			m.HBlock, m.ABlock,
			m.HHead, m.AHead,
			m.HSave, m.ASave,
			m.HCorner, m.ACorner,
			m.HFoul, m.AFoul,
			m.HOff, m.AOff,
			m.HYC, m.AYC,
			m.Diff)
	}

	logStat := func(name string, arr []int) {
		if len(arr) == 0 { return }
		m := mean(arr)
		s := std(arr)
		t.Logf("%s: mean=%.2f std=%.2f (CV=%.1f%%)", name, m, s, s/m*100)
	}
	logStatF := func(name string, arr []float64) {
		if len(arr) == 0 { return }
		m := meanF(arr)
		s := stdF(arr)
		t.Logf("%s: mean=%.2f std=%.2f (CV=%.1f%%)", name, m, s, s/m*100)
	}

	t.Logf("\n=== ATTACKING STATS ===")
	logStat("Home Goals", collect(func(m MatchData) int { return m.HG }))
	logStat("Away Goals", collect(func(m MatchData) int { return m.AG }))
	logStat("Home Shots", collect(func(m MatchData) int { return m.HS }))
	logStat("Away Shots", collect(func(m MatchData) int { return m.AS }))
	logStat("Home SoT", collect(func(m MatchData) int { return m.HSoT }))
	logStat("Away SoT", collect(func(m MatchData) int { return m.ASoT }))
	logStat("Home Passes", collect(func(m MatchData) int { return m.HP }))
	logStat("Away Passes", collect(func(m MatchData) int { return m.AP }))
	logStatF("Home PassAcc%%", collectF(func(m MatchData) float64 { return m.HPS }))
	logStatF("Away PassAcc%%", collectF(func(m MatchData) float64 { return m.APS }))
	logStat("Home KeyPasses", collect(func(m MatchData) int { return m.HKeyP }))
	logStat("Away KeyPasses", collect(func(m MatchData) int { return m.AKeyP }))
	logStat("Home Crosses", collect(func(m MatchData) int { return m.HCross }))
	logStat("Away Crosses", collect(func(m MatchData) int { return m.ACross }))
	logStatF("Home CrossAcc%%", collectF(func(m MatchData) float64 { return m.HCrossA }))
	logStatF("Away CrossAcc%%", collectF(func(m MatchData) float64 { return m.ACrossA }))
	logStat("Home Dribbles", collect(func(m MatchData) int { return m.HDrib }))
	logStat("Away Dribbles", collect(func(m MatchData) int { return m.ADrib }))
	logStatF("Home DribAcc%%", collectF(func(m MatchData) float64 { return m.HDribA }))
	logStatF("Away DribAcc%%", collectF(func(m MatchData) float64 { return m.ADribA }))
	logStat("Home Headers", collect(func(m MatchData) int { return m.HHead }))
	logStat("Away Headers", collect(func(m MatchData) int { return m.AHead }))
	logStatF("Home HeadAcc%%", collectF(func(m MatchData) float64 { return m.HHeadA }))
	logStatF("Away HeadAcc%%", collectF(func(m MatchData) float64 { return m.AHeadA }))
	logStat("Home Corners", collect(func(m MatchData) int { return m.HCorner }))
	logStat("Away Corners", collect(func(m MatchData) int { return m.ACorner }))
	logStat("Home Offsides", collect(func(m MatchData) int { return m.HOff }))
	logStat("Away Offsides", collect(func(m MatchData) int { return m.AOff }))

	t.Logf("\n=== DEFENSIVE STATS ===")
	logStat("Home Tackles", collect(func(m MatchData) int { return m.HTack }))
	logStat("Away Tackles", collect(func(m MatchData) int { return m.ATack }))
	logStatF("Home TackAcc%%", collectF(func(m MatchData) float64 { return m.HTackA }))
	logStatF("Away TackAcc%%", collectF(func(m MatchData) float64 { return m.ATackA }))
	logStat("Home Interceptions", collect(func(m MatchData) int { return m.HInter }))
	logStat("Away Interceptions", collect(func(m MatchData) int { return m.AInter }))
	logStat("Home Clearances", collect(func(m MatchData) int { return m.HClear }))
	logStat("Away Clearances", collect(func(m MatchData) int { return m.AClear }))
	logStat("Home Blocks", collect(func(m MatchData) int { return m.HBlock }))
	logStat("Away Blocks", collect(func(m MatchData) int { return m.ABlock }))
	logStat("Home Saves", collect(func(m MatchData) int { return m.HSave }))
	logStat("Away Saves", collect(func(m MatchData) int { return m.ASave }))
	logStat("Home Fouls", collect(func(m MatchData) int { return m.HFoul }))
	logStat("Away Fouls", collect(func(m MatchData) int { return m.AFoul }))
	logStat("Home FoulsDrawn", collect(func(m MatchData) int { return m.HFD }))
	logStat("Away FoulsDrawn", collect(func(m MatchData) int { return m.AFD }))
	logStat("Home YellowCards", collect(func(m MatchData) int { return m.HYC }))
	logStat("Away YellowCards", collect(func(m MatchData) int { return m.AYC }))
	logStat("Home RedCards", collect(func(m MatchData) int { return m.HRC }))
	logStat("Away RedCards", collect(func(m MatchData) int { return m.ARC }))
	logStat("Home FreeKicks", collect(func(m MatchData) int { return m.HFK }))
	logStat("Away FreeKicks", collect(func(m MatchData) int { return m.AFK }))
	logStat("Home Penalties", collect(func(m MatchData) int { return m.HPK }))
	logStat("Away Penalties", collect(func(m MatchData) int { return m.APK }))

	t.Logf("\n=== OVERVIEW ===")
	logStatF("Possession", collectF(func(m MatchData) float64 { return m.HPoss }))
	logStatF("PassAcc", collectF(func(m MatchData) float64 { return (m.HPS + m.APS) / 2 }))
	logStatF("TackleAcc", collectF(func(m MatchData) float64 { return (m.HTackA + m.ATackA) / 2 }))
	logStatF("CrossAcc", collectF(func(m MatchData) float64 { return (m.HCrossA + m.ACrossA) / 2 }))
	logStatF("HeaderAcc", collectF(func(m MatchData) float64 { return (m.HHeadA + m.AHeadA) / 2 }))

	blowouts := 0
	for _, m := range matches {
		if math.Abs(float64(m.Diff)) >= 4 { blowouts++ }
	}
	t.Logf("Blowouts (>=4 goal diff): %d/50 = %.0f%%", blowouts, float64(blowouts)*100/50)

	count := make(map[int]int)
	for _, m := range matches { count[m.Diff]++ }
	t.Logf("Goal diff distribution:")
	for d := -8; d <= 8; d++ {
		if count[d] > 0 {
			t.Logf("  %+d: %d matches", d, count[d])
		}
	}
}
