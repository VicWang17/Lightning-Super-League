package engine

import (
	"math"
	"math/rand/v2"
	"testing"
)

func TestPenaltyRatesByAttributes(t *testing.T) {
	// Test different taker/keeper attribute combinations
	// Using theoretical formula from doPenaltyKick logic:
	// atkVal = SET*0.60 + SHO*0.30 + FIN*0.10 + 4.3
	// defVal = SAV*0.30 + REF*0.20 + POS*0.15 - 1.3
	// pWin = sigmoid(delta/4.0), stabilized by COM
	// finalRate = pWin * 0.95 (5% miss even if keeper doesn't save)

	type combo struct {
		set, sho, fin, com float64 // taker
		sav, ref, pos        float64 // keeper
		desc                 string
	}

	combos := []combo{
		// Balanced matchups
		{8, 8, 8, 8, 8, 8, 8, "低SET(8) vs 低SAV(8)"},
		{10, 10, 10, 10, 10, 10, 10, "中SET(10) vs 中SAV(10)"},
		{12, 12, 12, 12, 12, 12, 12, "中高SET(12) vs 中高SAV(12)"},
		{14, 14, 14, 14, 14, 14, 14, "高SET(14) vs 高SAV(14)"},
		{16, 16, 16, 16, 16, 16, 16, "顶级SET(16) vs 顶级SAV(16)"},

		// Mismatched: good taker vs weak keeper
		{14, 14, 14, 14, 8, 8, 8, "高SET(14) vs 低SAV(8)"},
		{16, 16, 16, 16, 8, 8, 8, "顶级SET(16) vs 低SAV(8)"},

		// Mismatched: weak taker vs good keeper
		{8, 8, 8, 8, 14, 14, 14, "低SET(8) vs 高SAV(14)"},
		{8, 8, 8, 8, 16, 16, 16, "低SET(8) vs 顶级SAV(16)"},

		// COM impact tests (same stats, different COM)
		{12, 12, 12, 5, 12, 12, 12, "中SET(12),低COM(5) vs 中SAV(12)"},
		{12, 12, 12, 15, 12, 12, 12, "中SET(12),高COM(15) vs 中SAV(12)"},
		{12, 12, 12, 18, 12, 12, 12, "中SET(12),顶级COM(18) vs 中SAV(12)"},
	}

	t.Logf("%-50s | atkVal | defVal | delta  | rawWin | stabilized | finalRate", "Combination")
	t.Logf("%s", string(make([]byte, 100)))

	for _, c := range combos {
		atkVal := c.set*0.60 + c.sho*0.30 + c.fin*0.10 + 4.3
		defVal := c.sav*0.30 + c.ref*0.20 + c.pos*0.15 - 1.3
		delta := atkVal - defVal

		rawWin := sigmoid(delta / 4.0)

		// COM stabilization
		stability := math.Min(1.0, c.com/15.0)
		pWin := 0.5 + (rawWin-0.5)*(0.5+0.5*stability)

		if pWin < 0.03 {
			pWin = 0.03
		}
		if pWin > 0.97 {
			pWin = 0.97
		}

		finalRate := pWin * 0.95 // 5% miss probability

		t.Logf("%-50s | %6.2f | %6.2f | %6.2f | %6.2f%% | %6.2f%% | %6.2f%%",
			c.desc, atkVal, defVal, delta, rawWin*100, pWin*100, finalRate*100)
	}
}

func TestPenaltyMonteCarlo(t *testing.T) {
	// Monte Carlo simulation to verify theoretical rates
	const n = 100000

	type scenario struct {
		set, sho, fin, com float64
		sav, ref, pos        float64
		desc                 string
	}

	scenarios := []scenario{
		{12, 12, 12, 12, 12, 12, 12, "平衡对决 SET(12) vs SAV(12)"},
		{16, 16, 16, 16, 8, 8, 8, "强罚点手 vs 弱门将"},
		{8, 8, 8, 8, 16, 16, 16, "弱罚点手 vs 强门将"},
		{14, 14, 14, 14, 14, 14, 14, "强强对决 SET(14) vs SAV(14)"},
	}

	for _, s := range scenarios {
		goals := 0
		for i := 0; i < n; i++ {
			atkVal := s.set*0.60 + s.sho*0.30 + s.fin*0.10 + 4.3
			defVal := s.sav*0.30 + s.ref*0.20 + s.pos*0.15 - 1.3
			delta := atkVal - defVal

			rawWin := sigmoid(delta / 4.0)
			stability := math.Min(1.0, s.com/15.0)
			pWin := 0.5 + (rawWin-0.5)*(0.5+0.5*stability)
			if pWin < 0.03 {
				pWin = 0.03
			}
			if pWin > 0.97 {
				pWin = 0.97
			}

			// Simulate
			r := rand.New(rand.NewPCG(uint64(i), uint64(i*7+13)))
			if r.Float64() < pWin {
				if r.Float64() >= 0.05 {
					goals++
				}
			}
		}

		rate := float64(goals) / float64(n) * 100
		t.Logf("%-40s | 模拟 %d 次 | 命中率: %.2f%%", s.desc, n, rate)
	}
}
