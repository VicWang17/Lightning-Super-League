package main

import (
	"fmt"
	"math"
	"runtime"
	"sort"
	"sync"
	"time"

	"match-engine/internal/domain"
	"match-engine/internal/engine"
)

func baseAttrs() map[string]int {
	return map[string]int{
		"SHO": 10, "PAS": 10, "DRI": 10, "SPD": 10, "STR": 10,
		"STA": 10, "DEF": 10, "HEA": 10, "VIS": 10, "TKL": 10,
		"ACC": 10, "CRO": 10, "CON": 10, "FIN": 10, "BAL": 10,
		"COM": 10, "SAV": 10, "REF": 10, "POS": 10, "SET": 10,
		"DEC": 10,
	}
}

func positionBoost(pos string, attrs map[string]int) {
	switch pos {
	case "GK":
		attrs["SAV"] = 16; attrs["REF"] = 15; attrs["POS"] = 14; attrs["COM"] = 13; attrs["DEC"] = 12
	case "DF":
		attrs["DEF"] = 16; attrs["HEA"] = 15; attrs["STR"] = 14; attrs["TKL"] = 13; attrs["COM"] = 12; attrs["DEC"] = 11
	case "MF":
		attrs["PAS"] = 15; attrs["VIS"] = 14; attrs["STA"] = 14; attrs["CON"] = 13; attrs["DEC"] = 13
	case "FW":
		attrs["SHO"] = 16; attrs["SPD"] = 14; attrs["DRI"] = 14; attrs["ACC"] = 14; attrs["DEC"] = 11
	}
}

func makePlayer(id, pos string, attrs map[string]int) domain.PlayerSetup {
	pa := make(map[string]int)
	for k, v := range attrs {
		pa[k] = v
	}
	positionBoost(pos, pa)
	return domain.PlayerSetup{
		PlayerID:   id, Name: id, Position: pos,
		Attributes: pa, Stamina: 95.0, Height: 180, Foot: "right",
	}
}

func defaultTactics() domain.TacticalSetup {
	return domain.TacticalSetup{
		PassingStyle: 2, AttackWidth: 2, AttackTempo: 2,
		DefensiveLineHeight: 2, CrossingStrategy: 2, ShootingMentality: 2,
		PlaymakerFocus: 0, PressingIntensity: 2, DefensiveCompactness: 1,
		MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 1,
	}
}

func buildTeam(name string, attrs map[string]int, tactics domain.TacticalSetup, formationID string) domain.TeamSetup {
	players := []domain.PlayerSetup{
		makePlayer(name+"_GK", "GK", attrs),
		makePlayer(name+"_DF1", "DF", attrs),
		makePlayer(name+"_DF2", "DF", attrs),
		makePlayer(name+"_DF3", "DF", attrs),
		makePlayer(name+"_MF1", "MF", attrs),
		makePlayer(name+"_MF2", "MF", attrs),
		makePlayer(name+"_MF3", "MF", attrs),
		makePlayer(name+"_FW1", "FW", attrs),
	}
	bench := []domain.PlayerSetup{
		makePlayer(name+"_FW2", "FW", attrs),
		makePlayer(name+"_MF4", "MF", attrs),
		makePlayer(name+"_DFb", "DF", attrs),
	}
	if formationID == "" {
		formationID = "F01"
	}
	return domain.TeamSetup{
		TeamID: name, Name: name, FormationID: formationID,
		Players: players, Bench: bench, Tactics: tactics,
	}
}

func modifyTactics(t domain.TacticalSetup, field string, value int) domain.TacticalSetup {
	switch field {
	case "PassingStyle": t.PassingStyle = value
	case "AttackWidth": t.AttackWidth = value
	case "AttackTempo": t.AttackTempo = value
	case "DefensiveLineHeight": t.DefensiveLineHeight = value
	case "CrossingStrategy": t.CrossingStrategy = value
	case "ShootingMentality": t.ShootingMentality = value
	case "PlaymakerFocus": t.PlaymakerFocus = value
	case "PressingIntensity": t.PressingIntensity = value
	case "DefensiveCompactness": t.DefensiveCompactness = value
	case "MarkingStrategy": t.MarkingStrategy = value
	case "OffsideTrap": t.OffsideTrap = value
	case "TacklingAggression": t.TacklingAggression = value
	}
	return t
}

func runPair(home, away domain.TeamSetup, n int) (homeWins, draws, awayWins int) {
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
					MatchID:       fmt.Sprintf("p_%d_%d", s, idx),
					HomeAdvantage: false,
				}
				if s == 0 {
					req.HomeTeam = home
					req.AwayTeam = away
				} else {
					req.HomeTeam = away
					req.AwayTeam = home
				}
				sim := engine.NewSimulator(uint64(s*10000+idx) + uint64(time.Now().UnixNano()))
				res := sim.Simulate(req)
				mu.Lock()
				if res.Score.Home > res.Score.Away {
					if s == 0 {
						homeWins++
					} else {
						awayWins++
					}
				} else if res.Score.Home == res.Score.Away {
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

func cloneAttrs(base map[string]int) map[string]int {
	m := make(map[string]int)
	for k, v := range base {
		m[k] = v
	}
	return m
}

func main() {
	attrs := baseAttrs()
	base := defaultTactics()
	awayBase := buildTeam("Away", attrs, base, "F01")

	fmt.Println("========== 1. 单参数绝对强度测试 ==========")
	fields := []struct {
		name string
		min  int
		max  int
	}{
		{"PassingStyle", 0, 4}, {"AttackWidth", 0, 4}, {"AttackTempo", 0, 4},
		{"DefensiveLineHeight", 0, 4}, {"CrossingStrategy", 0, 4},
		{"ShootingMentality", 0, 4}, {"PlaymakerFocus", 0, 4},
		{"PressingIntensity", 0, 4}, {"DefensiveCompactness", 0, 2},
		{"MarkingStrategy", 0, 2}, {"OffsideTrap", 0, 2},
		{"TacklingAggression", 0, 3},
	}

	for _, f := range fields {
		var results []struct {
			val    int
			winPct float64
		}
		for v := f.min; v <= f.max; v++ {
			tactics := modifyTactics(base, f.name, v)
			home := buildTeam("Home", cloneAttrs(attrs), tactics, "F01")
			hw, dr, aw := runPair(home, awayBase, 20) // 20×2=40场
			total := hw + dr + aw
			winPct := float64(hw) / float64(total) * 100
			results = append(results, struct {
				val    int
				winPct float64
			}{v, winPct})
		}
		minW, maxW := results[0].winPct, results[0].winPct
		var minV, maxV int
		for _, r := range results {
			if r.winPct < minW {
				minW = r.winPct
				minV = r.val
			}
			if r.winPct > maxW {
				maxW = r.winPct
				maxV = r.val
			}
		}
		fmt.Printf("%s: ", f.name)
		for _, r := range results {
			fmt.Printf("%d=%.1f%% ", r.val, r.winPct)
		}
		fmt.Printf("| SWING=%.1f%% best=%d worst=%d\n", maxW-minW, maxV, minV)
	}

	fmt.Println("\n========== 2. 预设战术石头剪刀布 ==========")
	presetTactics := []struct {
		id   string
		name string
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
		{"T11", "均衡默认", base},
		{"T12", "全攻全守", domain.TacticalSetup{PassingStyle: 3, AttackWidth: 3, AttackTempo: 3, DefensiveLineHeight: 3, CrossingStrategy: 3, ShootingMentality: 3, PlaymakerFocus: 1, PressingIntensity: 3, DefensiveCompactness: 0, MarkingStrategy: 1, OffsideTrap: 1, TacklingAggression: 2}},
	}

	winMatrix := make([][]float64, len(presetTactics))
	for i := range winMatrix {
		winMatrix[i] = make([]float64, len(presetTactics))
	}

	for i, ti := range presetTactics {
		for j, tj := range presetTactics {
			if i == j {
				continue
			}
			home := buildTeam(ti.id, attrs, ti.T, "F01")
			away := buildTeam(tj.id, attrs, tj.T, "F01")
			hw, dr, aw := runPair(home, away, 15) // 15×2=30场
			total := hw + dr + aw
			winMatrix[i][j] = float64(hw) / float64(total) * 100
		}
	}

	type tscore struct {
		id   string
		name string
		avg  float64
		min  float64
		max  float64
		std  float64
	}
	scores := make([]tscore, len(presetTactics))
	for i, ti := range presetTactics {
		var sum, min, max float64
		var vals []float64
		cnt := 0
		for j := range presetTactics {
			if i == j {
				continue
			}
			v := winMatrix[i][j]
			sum += v
			vals = append(vals, v)
			if cnt == 0 || v < min {
				min = v
			}
			if cnt == 0 || v > max {
				max = v
			}
			cnt++
		}
		avg := sum / float64(cnt)
		var sq float64
		for _, v := range vals {
			d := v - avg
			sq += d * d
		}
		std := math.Sqrt(sq / float64(cnt))
		scores[i] = tscore{ti.id, ti.name, avg, min, max, std}
	}

	sort.Slice(scores, func(i, j int) bool {
		return scores[i].avg > scores[j].avg
	})

	fmt.Println("排名 | ID | 名称 | 平均胜率 | 最低 | 最高 | Std")
	for idx, s := range scores {
		fmt.Printf("%2d   | %s | %s | %6.1f%% | %5.1f%% | %5.1f%% | %.1f\n",
			idx+1, s.id, s.name, s.avg, s.min, s.max, s.std)
	}

	maxAvg := scores[0].avg
	minAvg := scores[len(scores)-1].avg
	fmt.Printf("\n战术间平均胜率极差: %.1f%%\n", maxAvg-minAvg)
	for _, s := range scores {
		if s.min > 55.0 {
			fmt.Printf("[DOMINANT] %s(%s) 对所有对手胜率均>55%%\n", s.id, s.name)
		}
		if s.max < 45.0 {
			fmt.Printf("[WEAK] %s(%s) 对所有对手胜率均<45%%\n", s.id, s.name)
		}
	}

	fmt.Println("\n========== 3. 关键组合测试 ==========")
	pairs := []struct {
		f1   string
		f2   string
		vals [][2]int
	}{
		{"PressingIntensity", "DefensiveLineHeight", [][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
		{"AttackTempo", "DefensiveLineHeight", [][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
		{"PassingStyle", "AttackTempo", [][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
		{"CrossingStrategy", "AttackWidth", [][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
	}

	for _, p := range pairs {
		fmt.Printf("\n-- %s x %s --\n", p.f1, p.f2)
		var bestWR, worstWR float64
		var bestCfg, worstCfg [2]int
		for _, v := range p.vals {
			tactics := modifyTactics(base, p.f1, v[0])
			tactics = modifyTactics(tactics, p.f2, v[1])
			home := buildTeam("Home", cloneAttrs(attrs), tactics, "F01")
			hw, dr, aw := runPair(home, awayBase, 15)
			total := hw + dr + aw
			winRate := float64(hw) / float64(total) * 100
			fmt.Printf("  %s=%d %s=%d -> Win=%.1f%%\n", p.f1, v[0], p.f2, v[1], winRate)
			if bestCfg == [2]int{0, 0} || winRate > bestWR {
				bestWR = winRate
				bestCfg = v
			}
			if worstCfg == [2]int{0, 0} || winRate < worstWR {
				worstWR = winRate
				worstCfg = v
			}
		}
		fmt.Printf("  >> SWING=%.1f%%\n", bestWR-worstWR)
	}

	fmt.Println("\n========== 4. 阵型×战术协同 ==========")
	formations := []string{"F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08"}
	extremeTactics := []struct {
		name    string
		tactics domain.TacticalSetup
	}{
		{"均衡", base},
		{"高位逼抢", modifyTactics(modifyTactics(base, "PressingIntensity", 4), "DefensiveLineHeight", 4)},
		{"深度防反", modifyTactics(modifyTactics(base, "DefensiveLineHeight", 0), "DefensiveCompactness", 2)},
		{"全攻", modifyTactics(modifyTactics(modifyTactics(base, "AttackTempo", 4), "ShootingMentality", 4), "AttackWidth", 4)},
	}

	for _, et := range extremeTactics {
		fmt.Printf("\n-- 战术: %s --\n", et.name)
		var bestWR, worstWR float64
		var bestF, worstF string
		for _, fid := range formations {
			home := buildTeam("Home", cloneAttrs(attrs), et.tactics, fid)
			hw, dr, aw := runPair(home, awayBase, 12)
			total := hw + dr + aw
			winRate := float64(hw) / float64(total) * 100
			fmt.Printf("  %s -> Win=%.1f%%\n", fid, winRate)
			if bestF == "" || winRate > bestWR {
				bestWR = winRate
				bestF = fid
			}
			if worstF == "" || winRate < worstWR {
				worstWR = winRate
				worstF = fid
			}
		}
		fmt.Printf("  >> SWING=%.1f%% (best=%s worst=%s)\n", bestWR-worstWR, bestF, worstF)
	}

	fmt.Println("\n========== 5. MarkingStrategy 修复后验证 ==========")
	for _, ms := range []int{0, 1, 2} {
		tactics := modifyTactics(base, "MarkingStrategy", ms)
		home := buildTeam("Home", cloneAttrs(attrs), tactics, "F01")
		hw, dr, aw := runPair(home, awayBase, 25)
		total := hw + dr + aw
		winRate := float64(hw) / float64(total) * 100
		fmt.Printf("MarkingStrategy=%d: Win=%.1f%%\n", ms, winRate)
	}

	fmt.Println("\n========== 6. 问题参数深度分析 ==========")
	// AttackTempo 详细分析
	fmt.Println("\n-- AttackTempo 详细分析 --")
	for _, at := range []int{0, 1, 2, 3, 4} {
		tactics := modifyTactics(base, "AttackTempo", at)
		home := buildTeam("Home", cloneAttrs(attrs), tactics, "F01")
		var shots, passes, tackles, counters, turnovers, goals int
		n := 50
		for i := 0; i < n; i++ {
			req := domain.SimulateRequest{
				MatchID:       fmt.Sprintf("at_%d_%d", at, i),
				HomeTeam:      home,
				AwayTeam:      awayBase,
				HomeAdvantage: false,
			}
			sim := engine.NewSimulator(uint64(i+1) + uint64(time.Now().UnixNano()))
			res := sim.Simulate(req)
			goals += res.Score.Home
			for _, ev := range res.Events {
				switch ev.Type {
				case "close_shot", "long_shot", "header":
					if ev.Team == home.Name {
						shots++
					}
				case "short_pass", "mid_pass", "long_pass", "back_pass", "through_ball":
					if ev.Team == home.Name {
						passes++
					}
				case "tackle", "intercept":
					if ev.Team == awayBase.Name {
						tackles++
					}
				case "counter_attack":
					if ev.Team == home.Name {
						counters++
					}
				case "turnover":
					if ev.Team == awayBase.Name { // home lost possession
						turnovers++
					}
				}
			}
		}
		fmt.Printf("AttackTempo=%d: Goals=%.2f/match Shots=%.1f Passes=%.1f TacklesFaced=%.1f Counters=%.1f TurnoversLost=%.1f\n",
			at, float64(goals)/float64(n), float64(shots)/float64(n), float64(passes)/float64(n),
			float64(tackles)/float64(n), float64(counters)/float64(n), float64(turnovers)/float64(n))
	}

	// PlaymakerFocus 详细分析
	fmt.Println("\n-- PlaymakerFocus 详细分析 --")
	for _, pf := range []int{0, 1, 2, 3, 4} {
		tactics := modifyTactics(base, "PlaymakerFocus", pf)
		home := buildTeam("Home", cloneAttrs(attrs), tactics, "F01")
		var shots, passes, throughs, goals int
		n := 50
		for i := 0; i < n; i++ {
			req := domain.SimulateRequest{
				MatchID:       fmt.Sprintf("pf_%d_%d", pf, i),
				HomeTeam:      home,
				AwayTeam:      awayBase,
				HomeAdvantage: false,
			}
			sim := engine.NewSimulator(uint64(i+1) + uint64(time.Now().UnixNano()))
			res := sim.Simulate(req)
			goals += res.Score.Home
			for _, ev := range res.Events {
				switch ev.Type {
				case "close_shot", "long_shot", "header":
					if ev.Team == home.Name {
						shots++
					}
				case "short_pass", "mid_pass", "long_pass", "back_pass":
					if ev.Team == home.Name {
						passes++
					}
				case "through_ball":
					if ev.Team == home.Name {
						throughs++
					}
				}
			}
		}
		fmt.Printf("PlaymakerFocus=%d: Goals=%.2f/match Shots=%.1f Passes=%.1f Throughs=%.1f\n",
			pf, float64(goals)/float64(n), float64(shots)/float64(n), float64(passes)/float64(n), float64(throughs)/float64(n))
	}
}
