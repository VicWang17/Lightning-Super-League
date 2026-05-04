package engine

import (
	"fmt"
	"testing"

	"match-engine/internal/domain"
)

// buildRealisticTeam creates a team with position-specific elite attributes.
func buildRealisticTeam(name string, isElite bool) domain.TeamSetup {
	baseAttrs := map[string]int{
		"SHO": 10, "PAS": 10, "DRI": 10, "SPD": 10, "STR": 10, "STA": 10,
		"DEF": 10, "HEA": 10, "VIS": 10, "TKL": 10, "ACC": 10, "CRO": 10,
		"CON": 10, "FIN": 10, "BAL": 10, "COM": 10, "SAV": 10, "REF": 10,
		"POS": 10, "SET": 10, "DEC": 10,
	}

	positions := []string{"GK", "CB", "CB", "SB", "DMF", "CMF", "CMF", "AMF", "WF", "ST", "SB"}
	players := make([]domain.PlayerSetup, len(positions))
	for i, pos := range positions {
		attrs := make(map[string]int)
		for k, v := range baseAttrs {
			attrs[k] = v
		}
		if isElite {
			switch pos {
			case "GK":
				attrs["SAV"] = 16; attrs["REF"] = 16; attrs["POS"] = 14; attrs["COM"] = 13
			case "CB":
				attrs["DEF"] = 15; attrs["TKL"] = 14; attrs["HEA"] = 14; attrs["STR"] = 13; attrs["POS"] = 13
			case "SB":
				attrs["DEF"] = 13; attrs["SPD"] = 14; attrs["CRO"] = 13; attrs["STA"] = 13
			case "DMF":
				attrs["DEF"] = 14; attrs["TKL"] = 13; attrs["PAS"] = 13; attrs["STR"] = 12; attrs["POS"] = 12
			case "CMF":
				attrs["PAS"] = 15; attrs["VIS"] = 14; attrs["DRI"] = 12; attrs["STA"] = 13; attrs["CON"] = 12
			case "AMF":
				attrs["PAS"] = 14; attrs["VIS"] = 14; attrs["SHO"] = 13; attrs["DRI"] = 12; attrs["FIN"] = 12
			case "WF":
				attrs["SPD"] = 15; attrs["DRI"] = 14; attrs["CRO"] = 13; attrs["SHO"] = 12; attrs["FIN"] = 12
			case "ST":
				attrs["SHO"] = 16; attrs["FIN"] = 15; attrs["HEA"] = 13; attrs["STR"] = 13; attrs["COM"] = 13
			}
		}
		players[i] = domain.PlayerSetup{
			PlayerID:   fmt.Sprintf("%s_%s%d", name, pos, i),
			Name:       fmt.Sprintf("%s_%s%d", name, pos, i),
			Position:   pos,
			Attributes: attrs,
			Stamina:    100,
			Height:     180,
			Foot:       "right",
		}
	}
	return domain.TeamSetup{
		Name:    name,
		Players: players,
		Tactics: defaultTactics(),
	}
}

func TestRealisticTeamMatchup(t *testing.T) {
	elite := buildRealisticTeam("精英队", true)
	common := buildRealisticTeam("平民队", false)

	n := 500
	var eliteWins, draws, commonWins int
	var eliteGoals, commonGoals int
	var eliteShots, commonShots int
	var elitePoss, commonPoss float64
	var elitePassAcc, commonPassAcc float64
	var eliteSaves, commonSaves int

	for i := 0; i < n; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("real_%d", i),
			HomeTeam:      elite,
			AwayTeam:      common,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)
		s := result.Stats

		if result.Score.Home > result.Score.Away {
			eliteWins++
		} else if result.Score.Home == result.Score.Away {
			draws++
		} else {
			commonWins++
		}
		eliteGoals += result.Score.Home
		commonGoals += result.Score.Away
		eliteShots += s.ShotsHome
		commonShots += s.ShotsAway
		elitePoss += s.PossessionHome
		commonPoss += s.PossessionAway
		elitePassAcc += s.PassAccuracyHome
		commonPassAcc += s.PassAccuracyAway
		eliteSaves += s.SavesHome
		commonSaves += s.SavesAway
	}

	fn := float64(n)
	t.Log("\n========== 真实阵容对决（精英 vs 平民，500场） ==========")
	t.Logf("胜率: 精英 %.1f%% | 平局 %.1f%% | 平民 %.1f%%",
		float64(eliteWins)/fn*100, float64(draws)/fn*100, float64(commonWins)/fn*100)
	t.Logf("场均进球: 精英 %.2f | 平民 %.2f", float64(eliteGoals)/fn, float64(commonGoals)/fn)
	t.Logf("场均射门: 精英 %.1f | 平民 %.1f", float64(eliteShots)/fn, float64(commonShots)/fn)
	t.Logf("控球率: 精英 %.1f%% | 平民 %.1f%%", elitePoss/fn, commonPoss/fn)
	t.Logf("传球准确率: 精英 %.1f%% | 平民 %.1f%%", elitePassAcc/fn, commonPassAcc/fn)
	t.Logf("场均扑救: 精英 %.1f | 平民 %.1f", float64(eliteSaves)/fn, float64(commonSaves)/fn)
}

func buildTeamWithRoleElite(name string, eliteRoles map[string]bool) domain.TeamSetup {
	baseAttrs := map[string]int{
		"SHO": 10, "PAS": 10, "DRI": 10, "SPD": 10, "STR": 10, "STA": 10,
		"DEF": 10, "HEA": 10, "VIS": 10, "TKL": 10, "ACC": 10, "CRO": 10,
		"CON": 10, "FIN": 10, "BAL": 10, "COM": 10, "SAV": 10, "REF": 10,
		"POS": 10, "SET": 10, "DEC": 10,
	}
	positions := []string{"GK", "CB", "CB", "SB", "DMF", "CMF", "CMF", "AMF", "WF", "ST", "SB"}
	players := make([]domain.PlayerSetup, len(positions))
	for i, pos := range positions {
		attrs := make(map[string]int)
		for k, v := range baseAttrs {
			attrs[k] = v
		}
		if eliteRoles[pos] {
			switch pos {
			case "GK":
				attrs["SAV"] = 16; attrs["REF"] = 16; attrs["POS"] = 14; attrs["COM"] = 13
			case "CB":
				attrs["DEF"] = 15; attrs["TKL"] = 14; attrs["HEA"] = 14; attrs["STR"] = 13; attrs["POS"] = 13
			case "SB":
				attrs["DEF"] = 13; attrs["SPD"] = 14; attrs["CRO"] = 13; attrs["STA"] = 13
			case "DMF":
				attrs["DEF"] = 14; attrs["TKL"] = 13; attrs["PAS"] = 13; attrs["STR"] = 12; attrs["POS"] = 12
			case "CMF":
				attrs["PAS"] = 15; attrs["VIS"] = 14; attrs["DRI"] = 12; attrs["STA"] = 13; attrs["CON"] = 12
			case "AMF":
				attrs["PAS"] = 14; attrs["VIS"] = 14; attrs["SHO"] = 13; attrs["DRI"] = 12; attrs["FIN"] = 12
			case "WF":
				attrs["SPD"] = 15; attrs["DRI"] = 14; attrs["CRO"] = 13; attrs["SHO"] = 12; attrs["FIN"] = 12
			case "ST":
				attrs["SHO"] = 16; attrs["FIN"] = 15; attrs["HEA"] = 13; attrs["STR"] = 13; attrs["COM"] = 13
			}
		}
		players[i] = domain.PlayerSetup{
			PlayerID:   fmt.Sprintf("%s_%s%d", name, pos, i),
			Name:       fmt.Sprintf("%s_%s%d", name, pos, i),
			Position:   pos,
			Attributes: attrs,
			Stamina:    100,
			Height:     180,
			Foot:       "right",
		}
	}
	return domain.TeamSetup{
		Name:    name,
		Players: players,
		Tactics: defaultTactics(),
	}
}

func runBatchSimple(home, away domain.TeamSetup, n int) (wins, draws, losses int, hg, ag float64) {
	for i := 0; i < n; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("b_%d", i),
			HomeTeam:      home,
			AwayTeam:      away,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)
		if result.Score.Home > result.Score.Away {
			wins++
		} else if result.Score.Home == result.Score.Away {
			draws++
		} else {
			losses++
		}
		hg += float64(result.Score.Home)
		ag += float64(result.Score.Away)
	}
	return wins, draws, losses, hg / float64(n), ag / float64(n)
}

func TestRealisticVariants(t *testing.T) {
	common := buildRealisticTeam("平民", false)
	elite := buildRealisticTeam("全精英", true)
	onlyGK := buildTeamWithRoleElite("门将强", map[string]bool{"GK": true})
	onlyST := buildTeamWithRoleElite("前锋强", map[string]bool{"ST": true})
	onlyCB := buildTeamWithRoleElite("后卫强", map[string]bool{"CB": true})
	onlyCMF := buildTeamWithRoleElite("中场强", map[string]bool{"CMF": true})
	noGK := buildTeamWithRoleElite("烂门将", map[string]bool{})
	for i := range noGK.Players {
		if noGK.Players[i].Position == "GK" {
			noGK.Players[i].Attributes["SAV"] = 6
			noGK.Players[i].Attributes["REF"] = 6
			noGK.Players[i].Attributes["POS"] = 6
		}
	}

	n := 200
	t.Log("\n========== 多组真实阵容对决（200场/组） ==========")
	cases := []struct {
		name string
		home domain.TeamSetup
		away domain.TeamSetup
	}{
		{"全精英 vs 平民", elite, common},
		{"门将强 vs 平民", onlyGK, common},
		{"前锋强 vs 平民", onlyST, common},
		{"后卫强 vs 平民", onlyCB, common},
		{"中场强 vs 平民", onlyCMF, common},
		{"全精英 vs 门将强", elite, onlyGK},
		{"全精英 vs 前锋强", elite, onlyST},
		{"平民 vs 烂门将", common, noGK},
	}
	for _, c := range cases {
		w, d, l, hg, ag := runBatchSimple(c.home, c.away, n)
		t.Logf("%-18s | 胜 %.1f%% | 平 %.1f%% | 负 %.1f%% | 进球 %.2f-%.2f",
			c.name, float64(w)/float64(n)*100, float64(d)/float64(n)*100,
			float64(l)/float64(n)*100, hg, ag)
	}
}
