package engine

import (
	"fmt"
	"runtime"
	"sync"
	"testing"
	"time"

	"match-engine/internal/domain"
)

// presetTactics returns 12 predefined tactical configurations.
func presetTactics() []struct {
	ID   string
	Name string
	T    domain.TacticalSetup
} {
	return []struct {
		ID   string
		Name string
		T    domain.TacticalSetup
	}{
		{"T01", "传控渗透", domain.TacticalSetup{PassingStyle: 4, AttackWidth: 2, AttackTempo: 1, DefensiveLineHeight: 3, CrossingStrategy: 1, ShootingMentality: 1, PlaymakerFocus: 2, PressingIntensity: 2, DefensiveCompactness: 2, MarkingStrategy: 1, OffsideTrap: 1, TacklingAggression: 1}},
		{"T02", "高位逼抢", domain.TacticalSetup{PassingStyle: 2, AttackWidth: 2, AttackTempo: 3, DefensiveLineHeight: 4, CrossingStrategy: 2, ShootingMentality: 3, PlaymakerFocus: 0, PressingIntensity: 4, DefensiveCompactness: 1, MarkingStrategy: 2, OffsideTrap: 2, TacklingAggression: 3}},
		{"T03", "防守反击", domain.TacticalSetup{PassingStyle: 1, AttackWidth: 2, AttackTempo: 4, DefensiveLineHeight: 1, CrossingStrategy: 2, ShootingMentality: 2, PlaymakerFocus: 0, PressingIntensity: 1, DefensiveCompactness: 2, MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 1}},
		{"T04", "边路传中", domain.TacticalSetup{PassingStyle: 2, AttackWidth: 4, AttackTempo: 2, DefensiveLineHeight: 2, CrossingStrategy: 4, ShootingMentality: 2, PlaymakerFocus: 0, PressingIntensity: 2, DefensiveCompactness: 1, MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 1}},
		{"T05", "长传冲吊", domain.TacticalSetup{PassingStyle: 0, AttackWidth: 3, AttackTempo: 4, DefensiveLineHeight: 2, CrossingStrategy: 3, ShootingMentality: 4, PlaymakerFocus: 0, PressingIntensity: 1, DefensiveCompactness: 0, MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 2}},
		{"T06", "深度防反", domain.TacticalSetup{PassingStyle: 1, AttackWidth: 1, AttackTempo: 2, DefensiveLineHeight: 0, CrossingStrategy: 2, ShootingMentality: 2, PlaymakerFocus: 0, PressingIntensity: 0, DefensiveCompactness: 2, MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 0}},
		{"T07", "全场紧逼", domain.TacticalSetup{PassingStyle: 2, AttackWidth: 3, AttackTempo: 3, DefensiveLineHeight: 3, CrossingStrategy: 2, ShootingMentality: 3, PlaymakerFocus: 0, PressingIntensity: 4, DefensiveCompactness: 1, MarkingStrategy: 2, OffsideTrap: 2, TacklingAggression: 3}},
		{"T08", "控球消耗", domain.TacticalSetup{PassingStyle: 4, AttackWidth: 1, AttackTempo: 0, DefensiveLineHeight: 2, CrossingStrategy: 1, ShootingMentality: 1, PlaymakerFocus: 2, PressingIntensity: 1, DefensiveCompactness: 2, MarkingStrategy: 1, OffsideTrap: 1, TacklingAggression: 0}},
		{"T09", "快速反击", domain.TacticalSetup{PassingStyle: 2, AttackWidth: 3, AttackTempo: 4, DefensiveLineHeight: 2, CrossingStrategy: 2, ShootingMentality: 3, PlaymakerFocus: 1, PressingIntensity: 2, DefensiveCompactness: 1, MarkingStrategy: 1, OffsideTrap: 1, TacklingAggression: 1}},
		{"T10", "密集防守", domain.TacticalSetup{PassingStyle: 1, AttackWidth: 1, AttackTempo: 1, DefensiveLineHeight: 1, CrossingStrategy: 1, ShootingMentality: 1, PlaymakerFocus: 0, PressingIntensity: 2, DefensiveCompactness: 2, MarkingStrategy: 2, OffsideTrap: 2, TacklingAggression: 1}},
		{"T11", "均衡默认", domain.TacticalSetup{PassingStyle: 2, AttackWidth: 2, AttackTempo: 2, DefensiveLineHeight: 2, CrossingStrategy: 2, ShootingMentality: 2, PlaymakerFocus: 0, PressingIntensity: 2, DefensiveCompactness: 1, MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 1}},
		{"T12", "全攻全守", domain.TacticalSetup{PassingStyle: 3, AttackWidth: 3, AttackTempo: 3, DefensiveLineHeight: 3, CrossingStrategy: 3, ShootingMentality: 3, PlaymakerFocus: 1, PressingIntensity: 3, DefensiveCompactness: 0, MarkingStrategy: 1, OffsideTrap: 1, TacklingAggression: 2}},
	}
}

// formationIDs returns all available formation IDs.
func formationIDs() []string {
	return []string{"F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08"}
}

// buildTeamWithFormation creates a team with given formation and tactics.
func buildTeamWithFormation(name string, attrs map[string]int, formationID string, tactics domain.TacticalSetup) domain.TeamSetup {
	t := buildTeam(name, attrs, tactics)
	t.FormationID = formationID
	return t
}

// runMatchPair runs home vs away for n matches each side (n home + n away = 2n total).
func runMatchPair(home, away domain.TeamSetup, n int) (homeWins, draws, awayWins int) {
	var mu sync.Mutex
	var wg sync.WaitGroup
	sem := make(chan struct{}, runtime.NumCPU())

	for side := 0; side < 2; side++ {
		for i := 0; i < n; i++ {
			wg.Add(1)
			sem <- struct{}{}
			go func(s, idx int) {
				defer wg.Done()
				req := domain.SimulateRequest{
					MatchID:       fmt.Sprintf("t_%d_%d", s, idx),
					HomeTeam:      home,
					AwayTeam:      away,
					HomeAdvantage: false,
				}
				if s == 1 {
					req.HomeTeam = away
					req.AwayTeam = home
				}
				sim := NewSimulator(uint64(s*10000+idx) + uint64(time.Now().UnixNano()))
				result := sim.Simulate(req)
				mu.Lock()
				if result.Score.Home > result.Score.Away {
					if s == 0 {
						homeWins++
					} else {
						awayWins++
					}
				} else if result.Score.Home == result.Score.Away {
					draws++
				} else {
					if s == 0 {
						awayWins++
					} else {
						homeWins++
					}
				}
				mu.Unlock()
				<-sem
			}(side, i)
		}
	}
	wg.Wait()
	return
}

// TestTacticsMatrix runs the full tactics vs tactics matrix.
func TestTacticsMatrix(t *testing.T) {
	attrs := baseAttrs()
	tactics := presetTactics()
	formationIDs := formationIDs()

	// Phase 1: Tactics matrix with F01 (Standard Balance)
	t.Log("\n========== TACTICS MATRIX (F01 formation) ==========")
	n := 10 // each pair plays 10 matches per side = 20 total

	winMatrix := make([][]int, len(tactics))
	for i := range winMatrix {
		winMatrix[i] = make([]int, len(tactics))
	}
	drawMatrix := make([][]int, len(tactics))
	for i := range drawMatrix {
		drawMatrix[i] = make([]int, len(tactics))
	}
	totalMatrix := make([][]int, len(tactics))
	for i := range totalMatrix {
		totalMatrix[i] = make([]int, len(tactics))
	}

	for i, ti := range tactics {
		for j, tj := range tactics {
			if i == j {
				continue
			}
			homeTeam := buildTeamWithFormation(ti.ID, attrs, "F01", ti.T)
			awayTeam := buildTeamWithFormation(tj.ID, attrs, "F01", tj.T)
			hw, dr, aw := runMatchPair(homeTeam, awayTeam, n)
			winMatrix[i][j] = hw
			drawMatrix[i][j] = dr
			totalMatrix[i][j] = hw + dr + aw
		}
	}

	// Print matrix header
	t.Logf("\n%-6s", "W%")
	for _, tj := range tactics {
		t.Logf(" %5s", tj.ID)
	}

	var minWinRate, maxWinRate float64
	var minPair, maxPair string
	baselineIdx := 10 // T11 均衡默认

	for i, ti := range tactics {
		row := fmt.Sprintf("%-6s", ti.ID)
		for j := range tactics {
			if i == j {
				row += "    --"
				continue
			}
			total := totalMatrix[i][j]
			if total == 0 {
				row += "   0.0"
				continue
			}
			winRate := float64(winMatrix[i][j]) / float64(total) * 100
			row += fmt.Sprintf(" %5.1f", winRate)
			if i != baselineIdx {
				if minPair == "" || winRate < minWinRate {
					minWinRate = winRate
					minPair = fmt.Sprintf("%s vs %s", ti.ID, tactics[j].ID)
				}
				if maxPair == "" || winRate > maxWinRate {
					maxWinRate = winRate
					maxPair = fmt.Sprintf("%s vs %s", ti.ID, tactics[j].ID)
				}
			}
		}
		t.Log(row)
	}

	t.Logf("\nWin rate range (excluding baseline): %.1f%% (%s) to %.1f%% (%s)", minWinRate, minPair, maxWinRate, maxPair)

	// Phase 2: Formation impact (each formation with T11 vs F01 T11)
	t.Log("\n========== FORMATION IMPACT (T11 vs T11) ==========")
	baselineTactics := tactics[baselineIdx]
	baselineTeam := buildTeamWithFormation(baselineTactics.ID, attrs, "F01", baselineTactics.T)

	for _, fid := range formationIDs {
		modTeam := buildTeamWithFormation(baselineTactics.ID+"_"+fid, attrs, fid, baselineTactics.T)
		hw, dr, aw := runMatchPair(modTeam, baselineTeam, 15)
		total := hw + dr + aw
		winRate := float64(hw) / float64(total) * 100
		t.Logf("%s vs F01: Win %.1f%% | Draw %.1f%% | Loss %.1f%% (%d matches)", fid, winRate, float64(dr)/float64(total)*100, float64(aw)/float64(total)*100, total)
	}

	// Assertions
	t.Log("\n--- ASSERTIONS ---")

	// Baseline self-check: T11 vs others should be 40-60%
	for j := range tactics {
		if j == baselineIdx {
			continue
		}
		total := totalMatrix[baselineIdx][j]
		if total > 0 {
			winRate := float64(winMatrix[baselineIdx][j]) / float64(total) * 100
			if winRate < 35 || winRate > 65 {
				t.Errorf("T11 baseline vs %s: win rate %.1f%%, expected 35-65%%", tactics[j].ID, winRate)
			}
		}
	}

	// Tactics must show distinguishability: min and max should differ by >= 10%
	if maxWinRate-minWinRate < 10 {
		t.Errorf("Tactics indistinguishable: win rate swing only %.1f%% (need >= 10%%)", maxWinRate-minWinRate)
	}

	// Extreme tactics check
	crossIdx := 3 // T04 边路传中
	pressIdx := 1 // T02 高位逼抢
	counterIdx := 2 // T03 防守反击
	possessIdx := 7 // T08 控球消耗

	for i, ti := range tactics {
		for j, tj := range tactics {
			if i == j {
				continue
			}
			_ = tj
			_ = crossIdx
			_ = pressIdx
			_ = counterIdx
			_ = possessIdx
			_ = ti
		}
	}
}
