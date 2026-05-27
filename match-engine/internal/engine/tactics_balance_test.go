package engine

import (
	"fmt"
	"math"
	"sort"
	"testing"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ==================== 战术平衡性深度测试 ====================
// 本测试旨在检测：
// 1. 是否存在绝对好/坏的战术参数选项
// 2. 是否存在版本强势/弱势的战术配置
// 3. 战术参数之间的协同/拮抗效应
// 4. 阵型与战术的匹配度

func TestTacticsAbsoluteStrength(t *testing.T) {
	attrs := baseAttrs()
	base := defaultTactics()
	awayBase := buildTeam("Away", attrs, base)

	fmt.Printf("\n========== 绝对强度测试：单参数遍历 vs 基准 ==========\n")
	// 对每个战术参数，遍历所有合法值，其他参数保持默认
	fields := []struct {
		name string
		min  int
		max  int
	}{
		{"PassingStyle", 0, 4},
		{"AttackWidth", 0, 4},
		{"AttackTempo", 0, 4},
		{"DefensiveLineHeight", 0, 4},
		{"CrossingStrategy", 0, 4},
		{"ShootingMentality", 0, 4},
		{"PlaymakerFocus", 0, 4},
		{"PressingIntensity", 0, 4},
		{"DefensiveCompactness", 0, 2},
		{"MarkingStrategy", 0, 2},
		{"OffsideTrap", 0, 2},
		{"TacklingAggression", 0, 3},
	}

	for _, f := range fields {
		var results []struct {
			val     int
			winRate float64
			goalsF  float64
			goalsA  float64
			poss    float64
			shots   float64
		}

		for v := f.min; v <= f.max; v++ {
			tactics := modifyTactics(base, f.name, v)
			home := buildTeam("Home", cloneAttrs(attrs), tactics)
			br := runBatchParallel(home, awayBase, 100, false)
			winRate := float64(br.HomeWins) * 100 / float64(br.Total)
			results = append(results, struct {
				val     int
				winRate float64
				goalsF  float64
				goalsA  float64
				poss    float64
				shots   float64
			}{
				val:     v,
				winRate: winRate,
				goalsF:  float64(br.TotalHomeGoals) / float64(br.Total),
				goalsA:  float64(br.TotalAwayGoals) / float64(br.Total),
				poss:    br.AvgPossHome,
				shots:   br.AvgShotsHome,
			})
		}

		// 分析极差
		minWR, maxWR := results[0].winRate, results[0].winRate
		var minVal, maxVal int
		for _, r := range results {
			if r.winRate < minWR {
				minWR = r.winRate
				minVal = r.val
			}
			if r.winRate > maxWR {
				maxWR = r.winRate
				maxVal = r.val
			}
		}
		swing := maxWR - minWR

		row := fmt.Sprintf("%s: ", f.name)
		for _, r := range results {
			row += fmt.Sprintf("%d=%.1f%% ", r.val, r.winRate)
		}
		fmt.Println(row)
		fmt.Printf("  >> SWING=%.1f%% (best=%d:%.1f%% worst=%d:%.1f%%)\n", swing, maxVal, maxWR, minVal, minWR)

		// 判断是否存在"绝对好"或"绝对坏"
		// 如果某个极端值显著优于/劣于相邻值，可能存在失衡
		if swing < 3.0 {
			fmt.Printf("  [BALANCED] 差异过小，该参数几乎无影响\n")
		} else if maxWR > 60.0 && minWR < 40.0 {
			fmt.Printf("  [UNBALANCED] 存在明显优劣值\n")
		}
	}
}

func TestTacticsCombinatorialExplosion(t *testing.T) {
	attrs := baseAttrs()
	base := defaultTactics()
	awayBase := buildTeam("Away", attrs, base)

	fmt.Printf("\n========== 组合强度测试：关键参数配对 ==========\n")
	// 测试若干关键两两组合
	pairs := []struct {
		f1   string
		f2   string
		vals [][2]int
	}{
		{"PressingIntensity", "DefensiveLineHeight",
			[][2]int{{0, 0}, {0, 2}, {0, 4}, {2, 2}, {2, 4}, {4, 2}, {4, 4}}},
		{"AttackTempo", "DefensiveLineHeight",
			[][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
		{"PassingStyle", "AttackTempo",
			[][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
		{"CrossingStrategy", "AttackWidth",
			[][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
		{"ShootingMentality", "AttackTempo",
			[][2]int{{0, 0}, {0, 4}, {4, 0}, {4, 4}, {2, 2}}},
	}

	for _, p := range pairs {
		fmt.Printf("\n-- %s x %s --\n", p.f1, p.f2)
		var bestWR, worstWR float64
		var bestCfg, worstCfg [2]int
		for _, v := range p.vals {
			tactics := modifyTactics(base, p.f1, v[0])
			tactics = modifyTactics(tactics, p.f2, v[1])
			home := buildTeam("Home", cloneAttrs(attrs), tactics)
			br := runBatchParallel(home, awayBase, 120, false)
			winRate := float64(br.HomeWins) * 100 / float64(br.Total)
			goalsF := float64(br.TotalHomeGoals) / float64(br.Total)
			goalsA := float64(br.TotalAwayGoals) / float64(br.Total)
			t.Logf("  %s=%d %s=%d -> Win=%.1f%% GF=%.2f GA=%.2f Poss=%.1f%%",
				p.f1, v[0], p.f2, v[1], winRate, goalsF, goalsA, br.AvgPossHome)
			if bestCfg == [2]int{0, 0} || winRate > bestWR {
				bestWR = winRate
				bestCfg = v
			}
			if worstCfg == [2]int{0, 0} || winRate < worstWR {
				worstWR = winRate
				worstCfg = v
			}
		}
		fmt.Printf("  >> BEST: %s=%d %s=%d (%.1f%%) | WORST: %s=%d %s=%d (%.1f%%) | SWING=%.1f%%\n",
			p.f1, bestCfg[0], p.f2, bestCfg[1], bestWR,
			p.f1, worstCfg[0], p.f2, worstCfg[1], worstWR,
			bestWR-worstWR)
	}
}

func TestFormationTacticsSynergy(t *testing.T) {
	attrs := baseAttrs()
	base := defaultTactics()
	awayBase := buildTeamWithFormation("Away", attrs, "F01", base)

	t.Logf("\n========== 阵型×战术协同效应 ==========")
	formations := []string{"F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08"}

	// 定义几套极端战术
	extremeTactics := []struct {
		name    string
		tactics domain.TacticalSetup
	}{
		{"均衡", base},
		{"高位逼抢", modifyTactics(modifyTactics(base, "PressingIntensity", 4), "DefensiveLineHeight", 4)},
		{"深度防反", modifyTactics(modifyTactics(base, "DefensiveLineHeight", 0), "DefensiveCompactness", 2)},
		{"全攻", modifyTactics(modifyTactics(modifyTactics(base, "AttackTempo", 4), "ShootingMentality", 4), "AttackWidth", 4)},
		{"传控", modifyTactics(modifyTactics(base, "PassingStyle", 4), "AttackTempo", 0)},
	}

	for _, et := range extremeTactics {
		t.Logf("\n-- 战术: %s --", et.name)
		var bestWR, worstWR float64
		var bestF, worstF string
		for _, fid := range formations {
			home := buildTeamWithFormation("Home", attrs, fid, et.tactics)
			br := runBatchParallel(home, awayBase, 100, false)
			winRate := float64(br.HomeWins) * 100 / float64(br.Total)
			t.Logf("  %s -> Win=%.1f%% GF=%.2f GA=%.2f", fid, winRate,
				float64(br.TotalHomeGoals)/float64(br.Total),
				float64(br.TotalAwayGoals)/float64(br.Total))
			if bestF == "" || winRate > bestWR {
				bestWR = winRate
				bestF = fid
			}
			if worstF == "" || winRate < worstWR {
				worstWR = winRate
				worstF = fid
			}
		}
		t.Logf("  >> BEST=%s(%.1f%%) WORST=%s(%.1f%%) SWING=%.1f%%", bestF, bestWR, worstF, worstWR, bestWR-worstWR)
		if bestWR-worstWR > 15.0 {
			fmt.Printf("  [WARNING] 阵型差异过大，该战术对阵型极度敏感\n")
		}
	}
}

func TestPresetTacticsRockPaperScissors(t *testing.T) {
	attrs := baseAttrs()
	tactics := presetTactics()

	fmt.Printf("\n========== 预设战术石头剪刀布测试 ==========\n")
	n := 12 // 每对12场主客 = 24场

	// 胜率矩阵
	winRates := make([][]float64, len(tactics))
	for i := range winRates {
		winRates[i] = make([]float64, len(tactics))
	}

	for i, ti := range tactics {
		for j, tj := range tactics {
			if i == j {
				continue
			}
			home := buildTeamWithFormation(ti.ID, attrs, "F01", ti.T)
			away := buildTeamWithFormation(tj.ID, attrs, "F01", tj.T)
			hw, dr, aw := runMatchPair(home, away, n)
			total := hw + dr + aw
			if total > 0 {
				winRates[i][j] = float64(hw) / float64(total) * 100
			}
		}
	}

	// 打印矩阵
	header := "      "
	for _, tj := range tactics {
		header += fmt.Sprintf(" %5s", tj.ID)
	}
	// t.Log(header) // 太长，略过

	// 计算每个战术的平均胜率和Elo-like评分
	type tacticScore struct {
		id      string
		name    string
		avgWR   float64
		minWR   float64
		maxWR   float64
		consistency float64 // 标准差
	}
	scores := make([]tacticScore, len(tactics))

	for i, ti := range tactics {
		var sum, min, max float64
		var vals []float64
		count := 0
		for j := range tactics {
			if i == j {
				continue
			}
			wr := winRates[i][j]
			sum += wr
			vals = append(vals, wr)
			if count == 0 || wr < min {
				min = wr
			}
			if count == 0 || wr > max {
				max = wr
			}
			count++
		}
		avg := sum / float64(count)
		var sq float64
		for _, v := range vals {
			d := v - avg
			sq += d * d
		}
		std := math.Sqrt(sq / float64(count))
		scores[i] = tacticScore{id: ti.ID, name: ti.Name, avgWR: avg, minWR: min, maxWR: max, consistency: std}
	}

	// 排序：按平均胜率
	sort.Slice(scores, func(i, j int) bool {
		return scores[i].avgWR > scores[j].avgWR
	})

	fmt.Printf("\n排名 | 战术ID | 名称 | 平均胜率 | 最低胜率 | 最高胜率 | 波动(Std)\n")
	for idx, s := range scores {
		fmt.Printf("%3d  | %s   | %s | %6.1f%% | %6.1f%% | %6.1f%% | %.1f\n",
			idx+1, s.id, s.name, s.avgWR, s.minWR, s.maxWR, s.consistency)
	}

	// 检查是否存在统治级战术
	if scores[0].avgWR-scores[len(scores)-1].avgWR > 20.0 {
		t.Logf("\n[CRITICAL] 战术间胜率差异超过20%%，存在明显统治级/废物战术")
	} else if scores[0].avgWR-scores[len(scores)-1].avgWR > 10.0 {
		t.Logf("\n[WARNING] 战术间胜率差异超过10%%，平衡性可能需要调整")
	} else {
		t.Logf("\n[OK] 战术间胜率差异在合理范围内")
	}

	// 检查是否有战术对所有其他战术都超过55%胜率（统治级）
	for _, s := range scores {
		if s.minWR > 55.0 {
			t.Logf("[DOMINANT] %s(%s) 对所有对手胜率均>55%%，疑似过强", s.id, s.name)
		}
		if s.maxWR < 45.0 {
			t.Logf("[WEAK] %s(%s) 对所有对手胜率均<45%%，疑似过弱", s.id, s.name)
		}
	}
}

func TestExtremeTacticsRobustness(t *testing.T) {
	attrs := baseAttrs()
	base := defaultTactics()

	t.Logf("\n========== 极端战术鲁棒性测试 ==========")
	// 测试极端战术配置在对抗不同实力对手时的表现

	extremes := []struct {
		name    string
		tactics domain.TacticalSetup
	}{
		{"全部最小", domain.TacticalSetup{
			PassingStyle: 0, AttackWidth: 0, AttackTempo: 0, DefensiveLineHeight: 0,
			CrossingStrategy: 0, ShootingMentality: 0, PlaymakerFocus: 0,
			PressingIntensity: 0, DefensiveCompactness: 0, MarkingStrategy: 0,
			OffsideTrap: 0, TacklingAggression: 0,
		}},
		{"全部最大", domain.TacticalSetup{
			PassingStyle: 4, AttackWidth: 4, AttackTempo: 4, DefensiveLineHeight: 4,
			CrossingStrategy: 4, ShootingMentality: 4, PlaymakerFocus: 4,
			PressingIntensity: 4, DefensiveCompactness: 2, MarkingStrategy: 2,
			OffsideTrap: 2, TacklingAggression: 3,
		}},
		{"均衡", base},
	}

	for _, et := range extremes {
		t.Logf("\n-- %s --", et.name)
		for _, attrVal := range []int{8, 10, 12, 14, 16} {
			modAttrs := make(map[string]int)
			for k := range attrs {
				modAttrs[k] = attrVal
			}
			strongOpp := buildTeam("Strong", modAttrs, base)
			weakOpp := buildTeam("Weak", baseAttrs(), base)
			self := buildTeam("Self", baseAttrs(), et.tactics)

			// vs 均衡同级
			br1 := runBatchParallel(self, weakOpp, 200, false)
			// vs 强敌
			br2 := runBatchParallel(self, strongOpp, 200, false)

			t.Logf("  对手attr=%d: vs均衡 Win=%.1f%% GF=%.2f GA=%.2f | vs强敌 Win=%.1f%% GF=%.2f GA=%.2f",
				attrVal,
				float64(br1.HomeWins)*100/float64(br1.Total),
				float64(br1.TotalHomeGoals)/float64(br1.Total),
				float64(br1.TotalAwayGoals)/float64(br1.Total),
				float64(br2.HomeWins)*100/float64(br2.Total),
				float64(br2.TotalHomeGoals)/float64(br2.Total),
				float64(br2.TotalAwayGoals)/float64(br2.Total),
			)
		}
	}
}

func TestMarkingStrategyBugCheck(t *testing.T) {
	attrs := baseAttrs()
	base := defaultTactics()
	awayBase := buildTeam("Away", attrs, base)

	t.Logf("\n========== MarkingStrategy 一致性检查 ==========")
	// MarkingStrategy: 0=区域, 1=混合, 2=人盯人
	// selector.go 中 manMarking := team.Tactics.MarkingStrategy == 1
	// tactical.go 中 ManMarkingActive: tac.MarkingStrategy >= 2
	// 这明显不一致！

	for _, ms := range []int{0, 1, 2} {
		tactics := modifyTactics(base, "MarkingStrategy", ms)
		home := buildTeam("Home", cloneAttrs(attrs), tactics)
		br := runBatchParallel(home, awayBase, 500, false)
		winRate := float64(br.HomeWins) * 100 / float64(br.Total)
		t.Logf("MarkingStrategy=%d: Win=%.1f%% Tackles=%.1f/match Fouls=%.1f/match",
			ms, winRate, br.AvgTacklesHome+br.AvgTacklesAway, br.AvgFoulsHome+br.AvgFoulsAway)
	}
}

func TestTacticalFlagsCoverage(t *testing.T) {
	attrs := baseAttrs()
	base := defaultTactics()
	awayBase := buildTeam("Away", attrs, base)

	t.Logf("\n========== 战术标记触发覆盖率 ==========")
	// 测试各 TacticalFlags 在实际比赛中被触发的频率

	flagTests := []struct {
		name    string
		tactics domain.TacticalSetup
		flag    string
	}{
		{"HighPress", modifyTactics(modifyTactics(base, "DefensiveLineHeight", 4), "PressingIntensity", 4), "HighPressActive"},
		{"DeepDefense", modifyTactics(modifyTactics(base, "DefensiveLineHeight", 0), "DefensiveCompactness", 2), "DeepDefenseActive"},
		{"OffsideTrap", modifyTactics(modifyTactics(base, "OffsideTrap", 2), "DefensiveLineHeight", 2), "OffsideTrapActive"},
		{"ManMarking", modifyTactics(base, "MarkingStrategy", 2), "ManMarkingActive"},
		{"PlayFromBack", modifyTactics(modifyTactics(base, "PassingStyle", 0), "DefensiveLineHeight", 2), "PlayFromBackActive"},
		{"CounterFocus", modifyTactics(base, "AttackTempo", 4), "CounterFocusActive"},
	}

	for _, ft := range flagTests {
		home := buildTeam("Home", cloneAttrs(attrs), ft.tactics)
		br := runBatchParallel(home, awayBase, 300, false)
		winRate := float64(br.HomeWins) * 100 / float64(br.Total)
		// 检查相关事件频率作为标记生效的代理指标
		counterCount := br.EventCounts[config.EventCounterAttack]
		pressCount := br.EventCounts[config.EventPressTogether]
		turnoverCount := br.EventCounts[config.EventTurnover]
		t.Logf("%s: Win=%.1f%% | Counter=%.2f/match PressTogether=%.2f/match Turnover=%.2f/match",
			ft.name, winRate,
			float64(counterCount)/float64(br.Total),
			float64(pressCount)/float64(br.Total),
			float64(turnoverCount)/float64(br.Total))
	}
}
