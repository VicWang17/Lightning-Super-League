package main

import (
	"fmt"
	"sort"
	"strings"
	"sync"

	"match-engine/internal/config"
	"match-engine/internal/domain"
	"match-engine/internal/engine"
)

func baseAttrs() map[string]int {
	return map[string]int{
		"SHO": 10, "PAS": 10, "DRI": 10, "SPD": 10, "STR": 10,
		"STA": 10, "DEF": 10, "HEA": 10, "VIS": 10, "TKL": 10,
		"ACC": 10, "CRO": 10, "CON": 10, "FIN": 10, "BAL": 10,
		"COM": 10, "SAV": 10, "REF": 10, "POS": 10, "FK": 10,
		"PK": 10, "RUS": 10, "DEC": 10,
	}
}

func positionBoost(pos string, attrs map[string]int) {
	switch pos {
	case "GK":
		attrs["SAV"] = 16; attrs["REF"] = 15; attrs["POS"] = 14; attrs["COM"] = 13; attrs["RUS"] = 12; attrs["DEC"] = 12
	case "CB":
		attrs["DEF"] = 16; attrs["HEA"] = 15; attrs["STR"] = 14; attrs["TKL"] = 13; attrs["COM"] = 12; attrs["DEC"] = 11
	case "SB":
		attrs["SPD"] = 15; attrs["CRO"] = 14; attrs["DEF"] = 12; attrs["STA"] = 14; attrs["DEC"] = 11
	case "DMF":
		attrs["DEF"] = 14; attrs["TKL"] = 14; attrs["PAS"] = 13; attrs["STA"] = 14; attrs["DEC"] = 13
	case "CMF":
		attrs["PAS"] = 15; attrs["VIS"] = 14; attrs["STA"] = 14; attrs["CON"] = 13; attrs["FK"] = 13; attrs["DEC"] = 13
	case "AMF":
		attrs["PAS"] = 15; attrs["VIS"] = 15; attrs["DRI"] = 14; attrs["SHO"] = 12; attrs["FK"] = 13; attrs["DEC"] = 13
	case "WF":
		attrs["SPD"] = 16; attrs["DRI"] = 14; attrs["CRO"] = 14; attrs["ACC"] = 14; attrs["DEC"] = 11
	case "ST":
		attrs["SHO"] = 16; attrs["HEA"] = 14; attrs["STR"] = 14; attrs["SPD"] = 13; attrs["PK"] = 13; attrs["DEC"] = 10
	}
}

func makeTestPlayer(id, pos string, attrs map[string]int) domain.PlayerSetup {
	playerAttrs := make(map[string]int)
	for k, v := range attrs {
		playerAttrs[k] = v
	}
	positionBoost(pos, playerAttrs)
	return domain.PlayerSetup{
		PlayerID:   id, Name: id, Position: pos,
		Attributes: playerAttrs, Stamina: 95.0, Height: 180, Foot: "right",
	}
}

func buildTeam(name string, attrs map[string]int, tactics domain.TacticalSetup) domain.TeamSetup {
	players := []domain.PlayerSetup{
		makeTestPlayer(name+"_GK", "GK", attrs),
		makeTestPlayer(name+"_CB1", "CB", attrs),
		makeTestPlayer(name+"_CB2", "CB", attrs),
		makeTestPlayer(name+"_SB", "SB", attrs),
		makeTestPlayer(name+"_DMF", "DMF", attrs),
		makeTestPlayer(name+"_CMF1", "CMF", attrs),
		makeTestPlayer(name+"_CMF2", "CMF", attrs),
		makeTestPlayer(name+"_ST", "ST", attrs),
	}
	bench := []domain.PlayerSetup{
		makeTestPlayer(name+"_WF", "WF", attrs),
		makeTestPlayer(name+"_AMF", "AMF", attrs),
		makeTestPlayer(name+"_CBb", "CB", attrs),
	}
	return domain.TeamSetup{TeamID: name, Name: name, FormationID: "F01", Players: players, Bench: bench, Tactics: tactics}
}

func defaultTactics() domain.TacticalSetup {
	return domain.TacticalSetup{
		PassingStyle: 2, AttackWidth: 2, AttackTempo: 2,
		DefensiveLineHeight: 2, CrossingStrategy: 2, ShootingMentality: 2,
		PlaymakerFocus: 0, PressingIntensity: 2, DefensiveCompactness: 1,
		MarkingStrategy: 0, OffsideTrap: 0, TacklingAggression: 1,
	}
}

func extractPosition(playerName string) string {
	parts := strings.Split(playerName, "_")
	if len(parts) < 2 { return "Unknown" }
	pos := parts[len(parts)-1]
	for len(pos) > 0 && pos[len(pos)-1] >= '0' && pos[len(pos)-1] <= '9' {
		pos = pos[:len(pos)-1]
	}
	if strings.HasSuffix(pos, "b") { pos = pos[:len(pos)-1] }
	return pos
}

func getPossessionAfterEvent(ev domain.MatchEvent, currentTeam string) string {
	switch ev.Type {
	case config.EventKickoff, config.EventSecondHalfStart,
		config.EventGoalKick, config.EventCorner, config.EventThrowIn,
		config.EventDropBall, config.EventKeeperShortPass, config.EventKeeperThrow:
		return ev.Team
	case config.EventTurnover:
		return ev.Team
	case config.EventTackle:
		if ev.Result == "success" { return ev.Team }
		if ev.Team == "home" { return "away" }
		return "home"
	case config.EventIntercept:
		return ev.Team
	case config.EventClearance:
		if ev.Team == "home" { return "away" }
		return "home"
	case config.EventGoal:
		if ev.Team == "home" { return "away" }
		return "home"
	case config.EventOwnGoal:
		if ev.Team == "home" { return "away" }
		return "home"
	case config.EventKeeperSave, config.EventKeeperClaim, config.EventShotBlock:
		return ev.Team
	case config.EventCloseShot, config.EventLongShot:
		if ev.Result == "goal" { return ev.Team }
		if ev.Team == "home" { return "away" }
		return "home"
	case config.EventFoul:
		if ev.Result == "no_call" {
			if ev.Team == "home" { return "away" }
			return "home"
		}
		if ev.Team == "home" { return "away" }
		return "home"
	case config.EventFreeKick:
		return ev.Team
	default:
		return ev.Team
	}
}

func calcPossessionLengths(events []domain.MatchEvent) []int {
	var lengths []int
	currentTeam := ""
	currentLen := 0
	for _, ev := range events {
		newTeam := getPossessionAfterEvent(ev, currentTeam)
		if newTeam != currentTeam && currentTeam != "" && newTeam != "" {
			lengths = append(lengths, currentLen)
			currentLen = 0
		}
		currentTeam = newTeam
		currentLen++
	}
	if currentLen > 0 { lengths = append(lengths, currentLen) }
	return lengths
}

type MatchStats struct {
	PassEvents, PassSuccess, Turnovers int
	Tackles, Intercepts, Clearances int
	AggressivePasses, AggressiveSuccess int
	SafePasses, SafeSuccess int
	PosPassCount map[string]int
	ZonePassCount map[string]int
	PossessionLengths []int
	EventCounts map[string]int
	FirstPassAfterTurnover map[string]int // event type -> count
}

func analyzeMatch(result domain.SimulateResult) MatchStats {
	ms := MatchStats{
		PosPassCount: make(map[string]int),
		ZonePassCount: make(map[string]int),
		EventCounts: make(map[string]int),
		FirstPassAfterTurnover: make(map[string]int),
	}
	var lastWasTurnover bool
	for _, ev := range result.Events {
		ms.EventCounts[ev.Type]++
		switch ev.Type {
		case config.EventShortPass, config.EventMidPass, config.EventLongPass, config.EventBackPass:
			ms.PassEvents++
			if ev.Result == "success" { ms.PassSuccess++ }
			if ev.Detail == "aggressive" {
				ms.AggressivePasses++
				if ev.Result == "success" { ms.AggressiveSuccess++ }
			} else {
				ms.SafePasses++
				if ev.Result == "success" { ms.SafeSuccess++ }
			}
			ms.PosPassCount[extractPosition(ev.PlayerName)]++
			ms.ZonePassCount[ev.Zone]++
			if lastWasTurnover {
				ms.FirstPassAfterTurnover[ev.Type]++
			}
			lastWasTurnover = false
		case config.EventTurnover:
			ms.Turnovers++
			lastWasTurnover = true
		case config.EventTackle:
			ms.Tackles++
			lastWasTurnover = false
		case config.EventIntercept:
			ms.Intercepts++
			lastWasTurnover = false
		case config.EventClearance:
			ms.Clearances++
			lastWasTurnover = false
		default:
			lastWasTurnover = false
		}
	}
	ms.PossessionLengths = calcPossessionLengths(result.Events)
	return ms
}

func aggregate(all []MatchStats) AggregatedStats {
	a := AggregatedStats{PosPassCount: make(map[string]int), ZonePassCount: make(map[string]int),
		EventCounts: make(map[string]int), FirstPassAfterTurnover: make(map[string]int)}
	a.TotalMatches = len(all)
	for _, ms := range all {
		a.TotalPassEvents += ms.PassEvents; a.TotalPassSuccess += ms.PassSuccess
		a.TotalTurnovers += ms.Turnovers; a.TotalTackles += ms.Tackles
		a.TotalIntercepts += ms.Intercepts; a.TotalClearances += ms.Clearances
		a.TotalAggressive += ms.AggressivePasses; a.TotalAggressiveSuccess += ms.AggressiveSuccess
		a.TotalSafe += ms.SafePasses; a.TotalSafeSuccess += ms.SafeSuccess
		for k, v := range ms.PosPassCount { a.PosPassCount[k] += v }
		for k, v := range ms.ZonePassCount { a.ZonePassCount[k] += v }
		for k, v := range ms.EventCounts { a.EventCounts[k] += v }
		for k, v := range ms.FirstPassAfterTurnover { a.FirstPassAfterTurnover[k] += v }
		a.AllPossessionLens = append(a.AllPossessionLens, ms.PossessionLengths...)
	}
	return a
}

type AggregatedStats struct {
	TotalMatches int
	TotalPassEvents, TotalPassSuccess int
	TotalTurnovers, TotalTackles, TotalIntercepts, TotalClearances int
	TotalAggressive, TotalAggressiveSuccess, TotalSafe, TotalSafeSuccess int
	PosPassCount, ZonePassCount map[string]int
	EventCounts map[string]int
	FirstPassAfterTurnover map[string]int
	AllPossessionLens []int
}

func medianInt(arr []int) int {
	if len(arr) == 0 { return 0 }
	sorted := make([]int, len(arr)); copy(sorted, arr); sort.Ints(sorted)
	mid := len(sorted)/2
	if len(sorted)%2==0 { return (sorted[mid-1]+sorted[mid])/2 }
	return sorted[mid]
}

func main() {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())
	const n = 100

	var all []MatchStats
	var mu sync.Mutex
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			req := domain.SimulateRequest{MatchID: fmt.Sprintf("s%d", idx), HomeTeam: home, AwayTeam: away, HomeAdvantage: false}
			result := engine.NewSimulator(uint64(idx+1)).Simulate(req)
			mu.Lock(); all = append(all, analyzeMatch(result)); mu.Unlock()
		}(i)
	}
	wg.Wait()
	agg := aggregate(all)
	fn := float64(n)

	fmt.Println("========================================")
	fmt.Println("   Match Engine Stats (100 matches)")
	fmt.Println("========================================\n")

	fmt.Printf("1. 平均每场传球次数: %.2f\n", float64(agg.TotalPassEvents)/fn)
	fmt.Printf("2. 传球成功率: %.2f%% (%d / %d)\n", float64(agg.TotalPassSuccess)/float64(agg.TotalPassEvents)*100, agg.TotalPassSuccess, agg.TotalPassEvents)
	fmt.Printf("3. 平均每场 turnover: %.2f\n", float64(agg.TotalTurnovers)/fn)
	fmt.Printf("4. 防守事件场均: tackle=%.2f, intercept=%.2f, clearance=%.2f\n",
		float64(agg.TotalTackles)/fn, float64(agg.TotalIntercepts)/fn, float64(agg.TotalClearances)/fn)

	fmt.Printf("5. Safe pass 成功率: %.2f%% (%d/%d)\n", float64(agg.TotalSafeSuccess)/float64(agg.TotalSafe)*100, agg.TotalSafeSuccess, agg.TotalSafe)
	fmt.Printf("   Aggressive pass 成功率: %.2f%% (%d/%d)\n", float64(agg.TotalAggressiveSuccess)/float64(agg.TotalAggressive)*100, agg.TotalAggressiveSuccess, agg.TotalAggressive)
	fmt.Printf("   Aggressive 占比: %.2f%%\n", float64(agg.TotalAggressive)/float64(agg.TotalPassEvents)*100)

	fmt.Println("\n6. 各位置传球占比:")
	var positions []string
	for p := range agg.PosPassCount { positions = append(positions, p) }
	sort.Strings(positions)
	for _, p := range positions {
		cnt := agg.PosPassCount[p]
		fmt.Printf("   %-5s: %6d (%.2f%%, 场均 %.2f)\n", p, cnt, float64(cnt)/float64(agg.TotalPassEvents)*100, float64(cnt)/fn)
	}

	fmt.Println("\n7. 各区域传球占比:")
	var zones []string
	for z := range agg.ZonePassCount { zones = append(zones, z) }
	sort.Strings(zones)
	for _, z := range zones {
		cnt := agg.ZonePassCount[z]
		fmt.Printf("   %-8s: %6d (%.2f%%)\n", z, cnt, float64(cnt)/float64(agg.TotalPassEvents)*100)
	}

	fmt.Println("\n8. 各事件类型场均出现次数 (top 20):")
	type kv struct{ k string; v int }
	var evList []kv
	for k, v := range agg.EventCounts { evList = append(evList, kv{k, v}) }
	sort.Slice(evList, func(i, j int) bool { return evList[i].v > evList[j].v })
	for i := 0; i < len(evList) && i < 20; i++ {
		fmt.Printf("   %-22s: %.2f\n", evList[i].k, float64(evList[i].v)/fn)
	}

	var totalPossEvents int
	for _, l := range agg.AllPossessionLens { totalPossEvents += l }
	fmt.Printf("\n9. 平均 possession 长度: %.2f (中位数 %d, 总次数 %d)\n",
		float64(totalPossEvents)/float64(len(agg.AllPossessionLens)), medianInt(agg.AllPossessionLens), len(agg.AllPossessionLens))

	fmt.Println("\n10. Turnover 后的第一个事件分布:")
	var fpList []kv
	for k, v := range agg.FirstPassAfterTurnover { fpList = append(fpList, kv{k, v}) }
	sort.Slice(fpList, func(i, j int) bool { return fpList[i].v > fpList[j].v })
	for _, kv := range fpList {
		fmt.Printf("   %-22s: %d (%.1f%%)\n", kv.k, kv.v, float64(kv.v)/float64(agg.TotalTurnovers)*100)
	}

	fmt.Println("\n========================================")
}
