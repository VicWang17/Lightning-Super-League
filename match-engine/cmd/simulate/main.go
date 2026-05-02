package main

import (
	"flag"
	"fmt"
	"os"
	"strings"

	"match-engine/internal/domain"
	"match-engine/internal/engine"
)

func main() {
	var seed uint64
	flag.Uint64Var(&seed, "seed", 0, "random seed (0 = random)")
	flag.Parse()

	// Create two demo teams
	home := buildDemoTeam("雷霆 FC", "F01", true)
	away := buildDemoTeam("闪电联", "F02", false)

	req := domain.SimulateRequest{
		MatchID:       "demo_match_001",
		HomeTeam:      home,
		AwayTeam:      away,
		HomeAdvantage: true,
	}

	sim := engine.NewSimulator(seed)
	result := sim.Simulate(req)

	// Terminal output
	printMatch(result)
}

func buildDemoTeam(name, formation string, isHome bool) domain.TeamSetup {
	players := []domain.PlayerSetup{
		makePlayer("GK", "门将"),
		makePlayer("CB", "中卫A"),
		makePlayer("CB", "中卫B"),
		makePlayer("SB", "边卫"),
		makePlayer("DMF", "后腰"),
		makePlayer("CMF", "中场A"),
		makePlayer("CMF", "中场B"),
		makePlayer("ST", "前锋"),
	}
	if formation == "F02" {
		// 2-2-3: remove DMF, add WF and AMF
		players = []domain.PlayerSetup{
			makePlayer("GK", "门将"),
			makePlayer("CB", "中卫A"),
			makePlayer("CB", "中卫B"),
			makePlayer("CMF", "中场A"),
			makePlayer("CMF", "中场B"),
			makePlayer("AMF", "前腰"),
			makePlayer("WF", "边锋"),
			makePlayer("ST", "前锋"),
		}
	}

	// Prefix team name
	for i := range players {
		players[i].PlayerID = fmt.Sprintf("%s_%d", strings.ReplaceAll(name, " ", "_"), i)
		players[i].Name = name + " " + players[i].Name
	}

	// Bench players for substitutions
	bench := []domain.PlayerSetup{
		makePlayer("WF", "替补边锋"),
		makePlayer("CMF", "替补中场"),
		makePlayer("CB", "替补中卫"),
	}
	for i := range bench {
		bench[i].PlayerID = fmt.Sprintf("%s_bench_%d", strings.ReplaceAll(name, " ", "_"), i)
		bench[i].Name = name + " " + bench[i].Name
	}

	// Different tactics to showcase the tactical system
	var tactics domain.TacticalSetup
	if isHome {
		// 雷霆 FC: High press, man marking, counter-attack focus, direct play
		tactics = domain.TacticalSetup{
			PassingStyle:         1, // Direct
			AttackWidth:          2,
			AttackTempo:          4, // Counter focus active
			DefensiveLineHeight:  3, // High press active
			CrossingStrategy:     2,
			ShootingMentality:    3,
			PlaymakerFocus:       0,
			PressingIntensity:    3, // High press + pressing zone bonus
			DefensiveCompactness: 2,
			MarkingStrategy:      1, // Man marking active
			OffsideTrap:          1, // Offside trap active
			TacklingAggression:   2,
		}
	} else {
		// 闪电联: Possession, short passing, deep defense, play from back
		tactics = domain.TacticalSetup{
			PassingStyle:         4, // Tiki-taka
			AttackWidth:          2,
			AttackTempo:          2,
			DefensiveLineHeight:  1, // Deep defense active
			CrossingStrategy:     3, // High cross
			ShootingMentality:    2,
			PlaymakerFocus:       1,
			PressingIntensity:    1,
			DefensiveCompactness: 2, // Deep defense active
			MarkingStrategy:      0, // Zonal marking
			OffsideTrap:          0,
			TacklingAggression:   1,
		}
	}

	return domain.TeamSetup{
		TeamID:      strings.ReplaceAll(name, " ", "_"),
		Name:        name,
		FormationID: formation,
		Players:     players,
		Bench:       bench,
		Tactics:     tactics,
	}
}

func makePlayer(pos, suffix string) domain.PlayerSetup {
	attrs := map[string]int{
		"SHO": 10, "PAS": 10, "DRI": 10, "SPD": 10, "STR": 10,
		"STA": 10, "DEF": 10, "HEA": 10, "VIS": 10, "TKL": 10,
		"ACC": 10, "CRO": 10, "CON": 10, "FIN": 10, "BAL": 10,
		"COM": 10, "SAV": 10, "REF": 10, "POS": 10, "FK": 10, "PK": 10,
	}

	// Position-specific bias
	switch pos {
	case "GK":
		attrs["SAV"] = 16
		attrs["REF"] = 15
		attrs["POS"] = 14
		attrs["COM"] = 13
	case "CB":
		attrs["DEF"] = 16
		attrs["HEA"] = 15
		attrs["STR"] = 14
		attrs["TKL"] = 13
		attrs["COM"] = 12
	case "SB":
		attrs["SPD"] = 15
		attrs["CRO"] = 14
		attrs["DEF"] = 12
		attrs["STA"] = 14
	case "DMF":
		attrs["DEF"] = 14
		attrs["TKL"] = 14
		attrs["PAS"] = 13
		attrs["STA"] = 14
	case "CMF":
		attrs["PAS"] = 15
		attrs["VIS"] = 14
		attrs["STA"] = 14
		attrs["CON"] = 13
		attrs["FK"] = 13
	case "AMF":
		attrs["PAS"] = 15
		attrs["VIS"] = 15
		attrs["DRI"] = 14
		attrs["SHO"] = 12
		attrs["FK"] = 13
	case "WF":
		attrs["SPD"] = 16
		attrs["DRI"] = 14
		attrs["CRO"] = 14
		attrs["ACC"] = 14
	case "ST":
		attrs["SHO"] = 16
		attrs["HEA"] = 14
		attrs["STR"] = 14
		attrs["SPD"] = 13
		attrs["PK"] = 13
	}

	name := pos + " " + suffix
	return domain.PlayerSetup{
		PlayerID:   name,
		Name:       name,
		Position:   pos,
		Attributes: attrs,
		Stamina:    95.0,
		Height:     180,
		Foot:       "right",
	}
}

func printMatch(result domain.SimulateResult) {
	w := os.Stdout

	fmt.Fprintln(w, strings.Repeat("=", 60))
	fmt.Fprintf(w, "⚡ 闪电超级联赛 — 比赛模拟\n")
	fmt.Fprintf(w, "Match ID: %s\n", result.MatchID)
	fmt.Fprintln(w, strings.Repeat("=", 60))

	fmt.Fprintf(w, "\n%s  %d - %d  %s\n", result.HomeTeam, result.Score.Home, result.Score.Away, result.AwayTeam)
	fmt.Fprintln(w, strings.Repeat("-", 60))

	fmt.Fprintf(w, "\n📺 比赛直播:\n")
	for _, narr := range result.Narratives {
		fmt.Fprintf(w, "  %s\n", narr)
	}

	fmt.Fprintln(w, strings.Repeat("-", 60))
	fmt.Fprintf(w, "\n📊 赛后统计:\n")
	fmt.Fprintf(w, "  控球率:   %s %.0f%%  -  %s %.0f%%\n",
		result.HomeTeam, result.Stats.PossessionHome,
		result.AwayTeam, result.Stats.PossessionAway)
	fmt.Fprintf(w, "  射门:     %s %d(%d)  -  %s %d(%d)\n",
		result.HomeTeam, result.Stats.ShotsHome, result.Stats.ShotsOnTargetHome,
		result.AwayTeam, result.Stats.ShotsAway, result.Stats.ShotsOnTargetAway)
	fmt.Fprintf(w, "  传球:     %s %d (%.0f%%)  -  %s %d (%.0f%%)\n",
		result.HomeTeam, result.Stats.PassesHome, result.Stats.PassAccuracyHome,
		result.AwayTeam, result.Stats.PassesAway, result.Stats.PassAccuracyAway)
	fmt.Fprintf(w, "  角球:     %s %d  -  %s %d\n",
		result.HomeTeam, result.Stats.CornersHome,
		result.AwayTeam, result.Stats.CornersAway)
	fmt.Fprintf(w, "  任意球:   %s %d(%d)  -  %s %d(%d)\n",
		result.HomeTeam, result.Stats.FreeKicksHome, result.Stats.FreeKickGoalsHome,
		result.AwayTeam, result.Stats.FreeKicksAway, result.Stats.FreeKickGoalsAway)
	fmt.Fprintf(w, "  点球:     %s %d(%d)  -  %s %d(%d)\n",
		result.HomeTeam, result.Stats.PenaltiesHome, result.Stats.PenaltyGoalsHome,
		result.AwayTeam, result.Stats.PenaltiesAway, result.Stats.PenaltyGoalsAway)

	fmt.Fprintf(w, "\n⭐ 球员详细数据:\n")
	fmt.Fprintf(w, "  %-24s %-5s %-5s %-10s %-8s %-10s %-8s %s\n",
		"球员", "位置", "进球", "传球", "成功率", "抢断", "成功率", "评分")
	fmt.Fprintln(w, strings.Repeat("-", 80))
	for _, ps := range result.PlayerStats {
		teamPrefix := "[主]"
		if ps.Team == "away" {
			teamPrefix = "[客]"
		}
		name := teamPrefix + " " + ps.Name

		passStr := "-"
		passAccStr := "-"
		if ps.Passes > 0 {
			passSucc := int(float64(ps.Passes) * ps.PassAccuracy / 100.0)
			passStr = fmt.Sprintf("%d/%d", passSucc, ps.Passes)
			passAccStr = fmt.Sprintf("%.0f%%", ps.PassAccuracy)
		}

		tackleStr := "-"
		tackleAccStr := "-"
		if ps.Tackles > 0 {
			tackleSucc := int(float64(ps.Tackles) * ps.TackleAccuracy / 100.0)
			tackleStr = fmt.Sprintf("%d/%d", tackleSucc, ps.Tackles)
			tackleAccStr = fmt.Sprintf("%.0f%%", ps.TackleAccuracy)
		}

		fmt.Fprintf(w, "  %-24s %-5s %-5d %-10s %-8s %-10s %-8s %.1f\n",
			name, ps.Position, ps.Goals,
			passStr, passAccStr,
			tackleStr, tackleAccStr,
			ps.Rating)
	}

	fmt.Fprintf(w, "\n⏱️  模拟耗时: %d ms\n", result.DurationMs)
	fmt.Fprintln(w, strings.Repeat("=", 60))
}
