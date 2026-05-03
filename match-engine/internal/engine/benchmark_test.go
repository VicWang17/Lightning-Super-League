package engine

import (
	"fmt"
	"math"
	"runtime"
	"sort"
	"strings"
	"sync"
	"testing"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ==================== 辅助函数 ====================

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
		PlayerID:   id,
		Name:       id,
		Position:   pos,
		Attributes: playerAttrs,
		Stamina:    95.0,
		Height:     180,
		Foot:       "right",
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
	return domain.TeamSetup{
		TeamID:      name,
		Name:        name,
		FormationID: "F01",
		Players:     players,
		Bench:       bench,
		Tactics:     tactics,
	}
}

func defaultTactics() domain.TacticalSetup {
	return domain.TacticalSetup{
		PassingStyle:         2, AttackWidth: 2, AttackTempo: 2,
		DefensiveLineHeight:  2, CrossingStrategy: 2, ShootingMentality: 2,
		PlaymakerFocus:       0, PressingIntensity: 2, DefensiveCompactness: 1,
		MarkingStrategy:      0, OffsideTrap: 0, TacklingAggression: 1,
	}
}

func cloneAttrs(base map[string]int) map[string]int {
	m := make(map[string]int)
	for k, v := range base {
		m[k] = v
	}
	return m
}

// modifyAttr returns a copy of attrs with specified attr changed by delta for all players
func modifyTeamAttr(team domain.TeamSetup, attr string, delta int) domain.TeamSetup {
	for i := range team.Players {
		if _, ok := team.Players[i].Attributes[attr]; ok {
			team.Players[i].Attributes[attr] += delta
			if team.Players[i].Attributes[attr] < 1 {
				team.Players[i].Attributes[attr] = 1
			}
			if team.Players[i].Attributes[attr] > 20 {
				team.Players[i].Attributes[attr] = 20
			}
		}
	}
	for i := range team.Bench {
		if _, ok := team.Bench[i].Attributes[attr]; ok {
			team.Bench[i].Attributes[attr] += delta
			if team.Bench[i].Attributes[attr] < 1 {
				team.Bench[i].Attributes[attr] = 1
			}
			if team.Bench[i].Attributes[attr] > 20 {
				team.Bench[i].Attributes[attr] = 20
			}
		}
	}
	return team
}

// modifyTactics returns a copy with one tactic field changed
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

// ==================== 批量运行 ====================

type BatchResult struct {
	Total          int
	HomeWins       int
	Draws          int
	AwayWins       int
	HomeGoals      []int
	AwayGoals      []int
	TotalHomeGoals int
	TotalAwayGoals int
	
	// Stats aggregates
	AvgPossHome    float64
	AvgPossAway    float64
	AvgShotsHome   float64
	AvgShotsAway   float64
	AvgShotsOnHome float64
	AvgShotsOnAway float64
	AvgPassesHome  float64
	AvgPassesAway  float64
	AvgPassAccHome float64
	AvgPassAccAway float64
	AvgTacklesHome float64
	AvgTacklesAway float64
	AvgCornersHome float64
	AvgCornersAway float64
	AvgFoulsHome   float64
	AvgFoulsAway   float64
	AvgYellowHome  float64
	AvgYellowAway  float64
	AvgRedHome     float64
	AvgRedAway     float64
	AvgFKHome      float64
	AvgFKAway      float64
	AvgFKGoalHome  float64
	AvgFKGoalAway  float64
	AvgPKHome      float64
	AvgPKAway      float64
	AvgPKGoalHome  float64
	AvgPKGoalAway  float64
	
	// Event coverage
	EventCounts map[string]int
	
	// Player ratings
	AllRatings []float64
	RatingByPos map[string][]float64
	
	// Control vs result
	HomeCtrlWins int // home had >50% control and won
	HomeCtrlLoss int // home had >50% control and lost
	
	// Free kick / penalty
	FKAttempts   int
	FKGoals      int
	PKAttempts   int
	PKGoals      int
	
	// Narratives sample
	NarrativeSamples []string
}

func runBatch(home, away domain.TeamSetup, n int, collectNarratives bool) BatchResult {
	br := BatchResult{
		Total:       n,
		EventCounts: make(map[string]int),
		RatingByPos: make(map[string][]float64),
	}
	
	var possHomeSum, possAwaySum float64
	var shotsHomeSum, shotsAwaySum float64
	var shotsOnHomeSum, shotsOnAwaySum float64
	var passesHomeSum, passesAwaySum float64
	var passAccHomeSum, passAccAwaySum float64
	var tacklesHomeSum, tacklesAwaySum float64
	var cornersHomeSum, cornersAwaySum float64
	var foulsHomeSum, foulsAwaySum float64
	var yellowHomeSum, yellowAwaySum float64
	var redHomeSum, redAwaySum float64
	var fkHomeSum, fkAwaySum float64
	var fkGoalHomeSum, fkGoalAwaySum float64
	var pkHomeSum, pkAwaySum float64
	var pkGoalHomeSum, pkGoalAwaySum float64
	
	for i := 0; i < n; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("batch_%d", i),
			HomeTeam:      home,
			AwayTeam:      away,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)
		
		br.HomeGoals = append(br.HomeGoals, result.Score.Home)
		br.AwayGoals = append(br.AwayGoals, result.Score.Away)
		br.TotalHomeGoals += result.Score.Home
		br.TotalAwayGoals += result.Score.Away
		
		if result.Score.Home > result.Score.Away {
			br.HomeWins++
		} else if result.Score.Home == result.Score.Away {
			br.Draws++
		} else {
			br.AwayWins++
		}
		
		possHomeSum += result.Stats.PossessionHome
		possAwaySum += result.Stats.PossessionAway
		shotsHomeSum += float64(result.Stats.ShotsHome)
		shotsAwaySum += float64(result.Stats.ShotsAway)
		shotsOnHomeSum += float64(result.Stats.ShotsOnTargetHome)
		shotsOnAwaySum += float64(result.Stats.ShotsOnTargetAway)
		passesHomeSum += float64(result.Stats.PassesHome)
		passesAwaySum += float64(result.Stats.PassesAway)
		passAccHomeSum += result.Stats.PassAccuracyHome
		passAccAwaySum += result.Stats.PassAccuracyAway
		tacklesHomeSum += float64(result.Stats.TacklesHome)
		tacklesAwaySum += float64(result.Stats.TacklesAway)
		cornersHomeSum += float64(result.Stats.CornersHome)
		cornersAwaySum += float64(result.Stats.CornersAway)
		foulsHomeSum += float64(result.Stats.FoulsHome)
		foulsAwaySum += float64(result.Stats.FoulsAway)
		yellowHomeSum += float64(result.Stats.YellowCardsHome)
		yellowAwaySum += float64(result.Stats.YellowCardsAway)
		redHomeSum += float64(result.Stats.RedCardsHome)
		redAwaySum += float64(result.Stats.RedCardsAway)
		fkHomeSum += float64(result.Stats.FreeKicksHome)
		fkAwaySum += float64(result.Stats.FreeKicksAway)
		fkGoalHomeSum += float64(result.Stats.FreeKickGoalsHome)
		fkGoalAwaySum += float64(result.Stats.FreeKickGoalsAway)
		pkHomeSum += float64(result.Stats.PenaltiesHome)
		pkAwaySum += float64(result.Stats.PenaltiesAway)
		pkGoalHomeSum += float64(result.Stats.PenaltyGoalsHome)
		pkGoalAwaySum += float64(result.Stats.PenaltyGoalsAway)
		
		// Control correlation
		if result.Stats.PossessionHome > 50.0 {
			if result.Score.Home > result.Score.Away {
				br.HomeCtrlWins++
			} else if result.Score.Home < result.Score.Away {
				br.HomeCtrlLoss++
			}
		}
		
		// Events
		for _, ev := range result.Events {
			br.EventCounts[ev.Type]++
		}
		
		// Player ratings
		for _, ps := range result.PlayerStats {
			br.AllRatings = append(br.AllRatings, ps.Rating)
			br.RatingByPos[ps.Position] = append(br.RatingByPos[ps.Position], ps.Rating)
		}
		
		// FK/PK — only count shot attempts for FK conversion
		for _, ev := range result.Events {
			if ev.Type == config.EventFreeKick {
				if ev.Detail == "shot" {
					br.FKAttempts++
					if ev.Result == "goal" {
						br.FKGoals++
					}
				}
				if ev.Detail == "penalty" {
					br.PKAttempts++
					if ev.Result == "goal" {
						br.PKGoals++
					}
				}
			}
		}
		
		// Narrative samples
		if collectNarratives && i < 20 {
			br.NarrativeSamples = append(br.NarrativeSamples,
				fmt.Sprintf("=== Match %d: %s %d-%d %s ===", i, result.HomeTeam, result.Score.Home, result.Score.Away, result.AwayTeam))
			for _, n := range result.Narratives {
				br.NarrativeSamples = append(br.NarrativeSamples, "  "+n)
			}
		}
	}
	
	fn := float64(n)
	br.AvgPossHome = possHomeSum / fn
	br.AvgPossAway = possAwaySum / fn
	br.AvgShotsHome = shotsHomeSum / fn
	br.AvgShotsAway = shotsAwaySum / fn
	br.AvgShotsOnHome = shotsOnHomeSum / fn
	br.AvgShotsOnAway = shotsOnAwaySum / fn
	br.AvgPassesHome = passesHomeSum / fn
	br.AvgPassesAway = passesAwaySum / fn
	br.AvgPassAccHome = passAccHomeSum / fn
	br.AvgPassAccAway = passAccAwaySum / fn
	br.AvgTacklesHome = tacklesHomeSum / fn
	br.AvgTacklesAway = tacklesAwaySum / fn
	br.AvgCornersHome = cornersHomeSum / fn
	br.AvgCornersAway = cornersAwaySum / fn
	br.AvgFoulsHome = foulsHomeSum / fn
	br.AvgFoulsAway = foulsAwaySum / fn
	br.AvgYellowHome = yellowHomeSum / fn
	br.AvgYellowAway = yellowAwaySum / fn
	br.AvgRedHome = redHomeSum / fn
	br.AvgRedAway = redAwaySum / fn
	br.AvgFKHome = fkHomeSum / fn
	br.AvgFKAway = fkAwaySum / fn
	br.AvgFKGoalHome = fkGoalHomeSum / fn
	br.AvgFKGoalAway = fkGoalAwaySum / fn
	br.AvgPKHome = pkHomeSum / fn
	br.AvgPKAway = pkAwaySum / fn
	br.AvgPKGoalHome = pkGoalHomeSum / fn
	br.AvgPKGoalAway = pkGoalAwaySum / fn
	
	return br
}

// runBatchParallel runs n matches in parallel using goroutines
func runBatchParallel(home, away domain.TeamSetup, n int, collectNarratives bool) BatchResult {
	br := BatchResult{
		Total:       n,
		EventCounts: make(map[string]int),
		RatingByPos: make(map[string][]float64),
	}

	numCPU := runtime.NumCPU()
	if numCPU < 2 {
		return runBatch(home, away, n, collectNarratives)
	}

	// Each goroutine gets its own partial result
	type partial struct {
		homeGoals      []int
		awayGoals      []int
		totalHomeGoals int
		totalAwayGoals int
		homeWins       int
		draws          int
		awayWins       int
		possHomeSum    float64
		possAwaySum    float64
		shotsHomeSum   float64
		shotsAwaySum   float64
		shotsOnHomeSum float64
		shotsOnAwaySum float64
		passesHomeSum  float64
		passesAwaySum  float64
		passAccHomeSum float64
		passAccAwaySum float64
		tacklesHomeSum float64
		tacklesAwaySum float64
		cornersHomeSum float64
		cornersAwaySum float64
		foulsHomeSum   float64
		foulsAwaySum   float64
		yellowHomeSum  float64
		yellowAwaySum  float64
		redHomeSum     float64
		redAwaySum     float64
		fkHomeSum      float64
		fkAwaySum      float64
		fkGoalHomeSum  float64
		fkGoalAwaySum  float64
		pkHomeSum      float64
		pkAwaySum      float64
		pkGoalHomeSum  float64
		pkGoalAwaySum  float64
		homeCtrlWins   int
		homeCtrlLoss   int
		eventCounts    map[string]int
		allRatings     []float64
		ratingByPos    map[string][]float64
		fkAttempts     int
		fkGoals        int
		pkAttempts     int
		pkGoals        int
		narratives     []string
	}

	var wg sync.WaitGroup
	results := make([]partial, numCPU)
	chunkSize := n / numCPU
	remainder := n % numCPU

	for i := 0; i < numCPU; i++ {
		wg.Add(1)
		start := i*chunkSize + min(i, remainder)
		count := chunkSize
		if i < remainder {
			count++
		}
		go func(idx, s, c int) {
			defer wg.Done()
			p := partial{
				eventCounts: make(map[string]int),
				ratingByPos: make(map[string][]float64),
			}
			for j := 0; j < c; j++ {
				matchIdx := s + j
				req := domain.SimulateRequest{
					MatchID:       fmt.Sprintf("batch_%d", matchIdx),
					HomeTeam:      home,
					AwayTeam:      away,
					HomeAdvantage: false,
				}
				sim := NewSimulator(uint64(matchIdx + 1))
				result := sim.Simulate(req)

				p.homeGoals = append(p.homeGoals, result.Score.Home)
				p.awayGoals = append(p.awayGoals, result.Score.Away)
				p.totalHomeGoals += result.Score.Home
				p.totalAwayGoals += result.Score.Away

				if result.Score.Home > result.Score.Away {
					p.homeWins++
				} else if result.Score.Home == result.Score.Away {
					p.draws++
				} else {
					p.awayWins++
				}

				p.possHomeSum += result.Stats.PossessionHome
				p.possAwaySum += result.Stats.PossessionAway
				p.shotsHomeSum += float64(result.Stats.ShotsHome)
				p.shotsAwaySum += float64(result.Stats.ShotsAway)
				p.shotsOnHomeSum += float64(result.Stats.ShotsOnTargetHome)
				p.shotsOnAwaySum += float64(result.Stats.ShotsOnTargetAway)
				p.passesHomeSum += float64(result.Stats.PassesHome)
				p.passesAwaySum += float64(result.Stats.PassesAway)
				p.passAccHomeSum += result.Stats.PassAccuracyHome
				p.passAccAwaySum += result.Stats.PassAccuracyAway
				p.tacklesHomeSum += float64(result.Stats.TacklesHome)
				p.tacklesAwaySum += float64(result.Stats.TacklesAway)
				p.cornersHomeSum += float64(result.Stats.CornersHome)
				p.cornersAwaySum += float64(result.Stats.CornersAway)
				p.foulsHomeSum += float64(result.Stats.FoulsHome)
				p.foulsAwaySum += float64(result.Stats.FoulsAway)
				p.yellowHomeSum += float64(result.Stats.YellowCardsHome)
				p.yellowAwaySum += float64(result.Stats.YellowCardsAway)
				p.redHomeSum += float64(result.Stats.RedCardsHome)
				p.redAwaySum += float64(result.Stats.RedCardsAway)
				p.fkHomeSum += float64(result.Stats.FreeKicksHome)
				p.fkAwaySum += float64(result.Stats.FreeKicksAway)
				p.fkGoalHomeSum += float64(result.Stats.FreeKickGoalsHome)
				p.fkGoalAwaySum += float64(result.Stats.FreeKickGoalsAway)
				p.pkHomeSum += float64(result.Stats.PenaltiesHome)
				p.pkAwaySum += float64(result.Stats.PenaltiesAway)
				p.pkGoalHomeSum += float64(result.Stats.PenaltyGoalsHome)
				p.pkGoalAwaySum += float64(result.Stats.PenaltyGoalsAway)

				if result.Stats.PossessionHome > 50.0 {
					if result.Score.Home > result.Score.Away {
						p.homeCtrlWins++
					} else if result.Score.Home < result.Score.Away {
						p.homeCtrlLoss++
					}
				}

				for _, ev := range result.Events {
					p.eventCounts[ev.Type]++
				}
				for _, ps := range result.PlayerStats {
					p.allRatings = append(p.allRatings, ps.Rating)
					p.ratingByPos[ps.Position] = append(p.ratingByPos[ps.Position], ps.Rating)
				}
				for _, ev := range result.Events {
					if ev.Type == config.EventFreeKick {
						if ev.Detail == "shot" {
							p.fkAttempts++
							if ev.Result == "goal" {
								p.fkGoals++
							}
						}
						if ev.Detail == "penalty" {
							p.pkAttempts++
							if ev.Result == "goal" {
								p.pkGoals++
							}
						}
					}
				}
				if collectNarratives && matchIdx < 20 {
					p.narratives = append(p.narratives,
						fmt.Sprintf("=== Match %d: %s %d-%d %s ===", matchIdx, result.HomeTeam, result.Score.Home, result.Score.Away, result.AwayTeam))
					for _, n := range result.Narratives {
						p.narratives = append(p.narratives, "  "+n)
					}
				}
			}
			results[idx] = p
		}(i, start, count)
	}
	wg.Wait()

	// Merge partial results
	for _, p := range results {
		br.HomeGoals = append(br.HomeGoals, p.homeGoals...)
		br.AwayGoals = append(br.AwayGoals, p.awayGoals...)
		br.TotalHomeGoals += p.totalHomeGoals
		br.TotalAwayGoals += p.totalAwayGoals
		br.HomeWins += p.homeWins
		br.Draws += p.draws
		br.AwayWins += p.awayWins
		br.HomeCtrlWins += p.homeCtrlWins
		br.HomeCtrlLoss += p.homeCtrlLoss
		br.FKAttempts += p.fkAttempts
		br.FKGoals += p.fkGoals
		br.PKAttempts += p.pkAttempts
		br.PKGoals += p.pkGoals
		br.AllRatings = append(br.AllRatings, p.allRatings...)
		br.NarrativeSamples = append(br.NarrativeSamples, p.narratives...)

		for k, v := range p.eventCounts {
			br.EventCounts[k] += v
		}
		for k, v := range p.ratingByPos {
			br.RatingByPos[k] = append(br.RatingByPos[k], v...)
		}
		br.AvgPossHome += p.possHomeSum
		br.AvgPossAway += p.possAwaySum
		br.AvgShotsHome += p.shotsHomeSum
		br.AvgShotsAway += p.shotsAwaySum
		br.AvgShotsOnHome += p.shotsOnHomeSum
		br.AvgShotsOnAway += p.shotsOnAwaySum
		br.AvgPassesHome += p.passesHomeSum
		br.AvgPassesAway += p.passesAwaySum
		br.AvgPassAccHome += p.passAccHomeSum
		br.AvgPassAccAway += p.passAccAwaySum
		br.AvgTacklesHome += p.tacklesHomeSum
		br.AvgTacklesAway += p.tacklesAwaySum
		br.AvgCornersHome += p.cornersHomeSum
		br.AvgCornersAway += p.cornersAwaySum
		br.AvgFoulsHome += p.foulsHomeSum
		br.AvgFoulsAway += p.foulsAwaySum
		br.AvgYellowHome += p.yellowHomeSum
		br.AvgYellowAway += p.yellowAwaySum
		br.AvgRedHome += p.redHomeSum
		br.AvgRedAway += p.redAwaySum
		br.AvgFKHome += p.fkHomeSum
		br.AvgFKAway += p.fkAwaySum
		br.AvgFKGoalHome += p.fkGoalHomeSum
		br.AvgFKGoalAway += p.fkGoalAwaySum
		br.AvgPKHome += p.pkHomeSum
		br.AvgPKAway += p.pkAwaySum
		br.AvgPKGoalHome += p.pkGoalHomeSum
		br.AvgPKGoalAway += p.pkGoalAwaySum
	}

	fn := float64(n)
	br.AvgPossHome /= fn
	br.AvgPossAway /= fn
	br.AvgShotsHome /= fn
	br.AvgShotsAway /= fn
	br.AvgShotsOnHome /= fn
	br.AvgShotsOnAway /= fn
	br.AvgPassesHome /= fn
	br.AvgPassesAway /= fn
	br.AvgPassAccHome /= fn
	br.AvgPassAccAway /= fn
	br.AvgTacklesHome /= fn
	br.AvgTacklesAway /= fn
	br.AvgCornersHome /= fn
	br.AvgCornersAway /= fn
	br.AvgFoulsHome /= fn
	br.AvgFoulsAway /= fn
	br.AvgYellowHome /= fn
	br.AvgYellowAway /= fn
	br.AvgRedHome /= fn
	br.AvgRedAway /= fn
	br.AvgFKHome /= fn
	br.AvgFKAway /= fn
	br.AvgFKGoalHome /= fn
	br.AvgFKGoalAway /= fn
	br.AvgPKHome /= fn
	br.AvgPKAway /= fn
	br.AvgPKGoalHome /= fn
	br.AvgPKGoalAway /= fn

	return br
}

// ==================== 统计输出 ====================

func scoreDistribution(goals []int) string {
	counts := make(map[int]int)
	for _, g := range goals {
		counts[g]++
	}
	var keys []int
	for k := range counts {
		keys = append(keys, k)
	}
	sort.Ints(keys)
	var parts []string
	for _, k := range keys {
		parts = append(parts, fmt.Sprintf("%d:%d", k, counts[k]))
	}
	return strings.Join(parts, ", ")
}

func meanStd(arr []float64) (float64, float64) {
	if len(arr) == 0 {
		return 0, 0
	}
	var sum float64
	for _, v := range arr {
		sum += v
	}
	mean := sum / float64(len(arr))
	var sq float64
	for _, v := range arr {
		d := v - mean
		sq += d * d
	}
	std := math.Sqrt(sq / float64(len(arr)))
	return mean, std
}

func printBatchResult(t *testing.T, name string, br BatchResult) {
	t.Logf("\n========== %s ==========", name)
	t.Logf("Total matches: %d", br.Total)
	t.Logf("Home wins: %d (%.1f%%) | Draws: %d (%.1f%%) | Away wins: %d (%.1f%%)",
		br.HomeWins, float64(br.HomeWins)*100/float64(br.Total),
		br.Draws, float64(br.Draws)*100/float64(br.Total),
		br.AwayWins, float64(br.AwayWins)*100/float64(br.Total))
	t.Logf("Total goals: Home=%d, Away=%d | Avg: Home=%.2f, Away=%.2f",
		br.TotalHomeGoals, br.TotalAwayGoals,
		float64(br.TotalHomeGoals)/float64(br.Total), float64(br.TotalAwayGoals)/float64(br.Total))
	t.Logf("Home score distribution: %s", scoreDistribution(br.HomeGoals))
	t.Logf("Away score distribution: %s", scoreDistribution(br.AwayGoals))
	t.Logf("Possession: Home=%.1f%% Away=%.1f%%", br.AvgPossHome, br.AvgPossAway)
	t.Logf("Shots: Home=%.1f(%.1f on target) Away=%.1f(%.1f on target)",
		br.AvgShotsHome, br.AvgShotsOnHome, br.AvgShotsAway, br.AvgShotsOnAway)
	t.Logf("Passes: Home=%.1f (%.1f%%) Away=%.1f (%.1f%%)",
		br.AvgPassesHome, br.AvgPassAccHome, br.AvgPassesAway, br.AvgPassAccAway)
	t.Logf("Tackles: Home=%.1f Away=%.1f | Corners: Home=%.1f Away=%.1f",
		br.AvgTacklesHome, br.AvgTacklesAway, br.AvgCornersHome, br.AvgCornersAway)
	t.Logf("Fouls: Home=%.1f Away=%.1f | Yellow: Home=%.1f Away=%.1f | Red: Home=%.1f Away=%.1f",
		br.AvgFoulsHome, br.AvgFoulsAway, br.AvgYellowHome, br.AvgYellowAway, br.AvgRedHome, br.AvgRedAway)
	t.Logf("Free Kicks: Home=%.1f(%.1f goals) Away=%.1f(%.1f goals) | PK: Home=%.1f(%.1f goals) Away=%.1f(%.1f goals)",
		br.AvgFKHome, br.AvgFKGoalHome, br.AvgFKAway, br.AvgFKGoalAway,
		br.AvgPKHome, br.AvgPKGoalHome, br.AvgPKAway, br.AvgPKGoalAway)
	t.Logf("FK conversion rate: %.2f%% (%d/%d) | PK conversion rate: %.2f%% (%d/%d)",
		float64(br.FKGoals)*100/math.Max(1, float64(br.FKAttempts)), br.FKGoals, br.FKAttempts,
		float64(br.PKGoals)*100/math.Max(1, float64(br.PKAttempts)), br.PKGoals, br.PKAttempts)
	t.Logf("Control correlation: Home>50%% ctrl & won=%d, Home>50%% ctrl & lost=%d",
		br.HomeCtrlWins, br.HomeCtrlLoss)
	
	// Rating distribution
	mean, std := meanStd(br.AllRatings)
	t.Logf("Player ratings: mean=%.2f, std=%.2f, n=%d", mean, std, len(br.AllRatings))
	for pos, ratings := range br.RatingByPos {
		m, s := meanStd(ratings)
		t.Logf("  %s: mean=%.2f std=%.2f n=%d", pos, m, s, len(ratings))
	}
	
	// Event coverage
	t.Logf("Event coverage (%d unique types):", len(br.EventCounts))
	var evTypes []string
	for et := range br.EventCounts {
		evTypes = append(evTypes, et)
	}
	sort.Strings(evTypes)
	for _, et := range evTypes {
		avg := float64(br.EventCounts[et]) / float64(br.Total)
		t.Logf("  %s: %.2f per match (total=%d)", et, avg, br.EventCounts[et])
	}
}

// ==================== 测试用例 ====================

func TestSameTeam(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())
	br := runBatch(home, away, 2000, true)
	printBatchResult(t, "1. SAME TEAM (2000 matches)", br)
	
	for _, n := range br.NarrativeSamples {
		t.Log(n)
	}
}

func TestSkillGap(t *testing.T) {
	// Weak (all 8) vs Medium (all 12) vs Strong (all 16)
	weakAttrs := baseAttrs()
	for k := range weakAttrs {
		weakAttrs[k] = 8
	}
	medAttrs := baseAttrs()
	for k := range medAttrs {
		medAttrs[k] = 12
	}
	strongAttrs := baseAttrs()
	for k := range strongAttrs {
		strongAttrs[k] = 16
	}
	
	weak := buildTeam("Weak", weakAttrs, defaultTactics())
	med := buildTeam("Med", medAttrs, defaultTactics())
	strong := buildTeam("Strong", strongAttrs, defaultTactics())
	
	br1 := runBatch(weak, med, 1000, false)
	printBatchResult(t, "2a. WEAK vs MEDIUM (1000)", br1)

	br2 := runBatch(med, strong, 1000, false)
	printBatchResult(t, "2b. MEDIUM vs STRONG (1000)", br2)

	br3 := runBatch(weak, strong, 1000, false)
	printBatchResult(t, "2c. WEAK vs STRONG (1000)", br3)
}

func TestAttributeImpact(t *testing.T) {
	t.Logf("\n========== 3. ATTRIBUTE IMPACT (each +5, 500 matches) ==========")
	base := baseAttrs()
	homeBase := buildTeam("Home", base, defaultTactics())
	awayBase := buildTeam("Away", base, defaultTactics())
	
	// Baseline
	brBase := runBatchParallel(homeBase, awayBase, 500, false)
	t.Logf("BASELINE: Home win %.1f%%", float64(brBase.HomeWins)*100/float64(brBase.Total))
	
	attrNames := []string{"SHO", "PAS", "DRI", "SPD", "STR", "STA", "DEF", "HEA", "VIS", "TKL",
		"ACC", "CRO", "CON", "FIN", "BAL", "COM", "SAV", "REF", "POS", "FK", "PK", "RUS", "DEC"}
	
	for _, attr := range attrNames {
		homeMod := buildTeam("Home", cloneAttrs(base), defaultTactics())
		homeMod = modifyTeamAttr(homeMod, attr, +5)
		br := runBatchParallel(homeMod, awayBase, 300, false)
		winRate := float64(br.HomeWins) * 100 / float64(br.Total)
		baseWinRate := float64(brBase.HomeWins) * 100 / float64(brBase.Total)
		t.Logf("  %s +5: Home win %.1f%% (delta %.1f%%) | Avg goals %.2f-%.2f",
			attr, winRate, winRate-baseWinRate,
			float64(br.TotalHomeGoals)/float64(br.Total),
			float64(br.TotalAwayGoals)/float64(br.Total))
	}
}

func TestTacticsImpact(t *testing.T) {
	t.Logf("\n========== 4. TACTICS IMPACT (each config, 500 matches) ==========")
	base := baseAttrs()
	homeBase := buildTeam("Home", base, defaultTactics())
	awayBase := buildTeam("Away", base, defaultTactics())
	
	brBase := runBatch(homeBase, awayBase, 500, false)
	baseWinRate := float64(brBase.HomeWins) * 100 / float64(brBase.Total)
	t.Logf("BASELINE: Home win %.1f%%", baseWinRate)
	
	tacticFields := []struct {
		name   string
		min    int
		max    int
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
	
	for _, tf := range tacticFields {
		var bestWinRate, worstWinRate float64
		var bestVal, worstVal int
		for v := tf.min; v <= tf.max; v++ {
			tactics := modifyTactics(defaultTactics(), tf.name, v)
			homeMod := buildTeam("Home", cloneAttrs(base), tactics)
			br := runBatch(homeMod, awayBase, 200, false)
			winRate := float64(br.HomeWins) * 100 / float64(br.Total)
			if v == tf.min || winRate > bestWinRate {
				bestWinRate = winRate
				bestVal = v
			}
			if v == tf.min || winRate < worstWinRate {
				worstWinRate = winRate
				worstVal = v
			}
			t.Logf("  %s=%d: Home win %.1f%% (delta %.1f%%)", tf.name, v, winRate, winRate-baseWinRate)
		}
		t.Logf("  >> %s BEST=%d(%.1f%%) WORST=%d(%.1f%%) SWING=%.1f%%",
			tf.name, bestVal, bestWinRate, worstVal, worstWinRate, bestWinRate-worstWinRate)
	}
}

func TestFreeKickSpecialist(t *testing.T) {
	t.Logf("\n========== 6. FREE KICK SPECIALIST ==========")
	base := baseAttrs()
	
	// Test different FK levels
	for _, fk := range []int{8, 12, 16, 18} {
		attrs := cloneAttrs(base)
		attrs["FK"] = fk
		home := buildTeam("Home", attrs, defaultTactics())
		away := buildTeam("Away", base, defaultTactics())
		br := runBatch(home, away, 1000, false)
		t.Logf("FK=%d: FK conversion %.2f%% (%d/%d) | Home win %.1f%% | Avg FK per match %.2f",
			fk,
			float64(br.FKGoals)*100/math.Max(1, float64(br.FKAttempts)), br.FKGoals, br.FKAttempts,
			float64(br.HomeWins)*100/float64(br.Total),
			br.AvgFKHome+br.AvgFKAway)
	}
}

func TestPenaltyRate(t *testing.T) {
	t.Logf("\n========== 7. PENALTY RATE ==========")
	base := baseAttrs()
	home := buildTeam("Home", base, defaultTactics())
	away := buildTeam("Away", base, defaultTactics())
	br := runBatch(home, away, 2000, false)
	t.Logf("Overall PK conversion: %.2f%% (%d/%d)",
		float64(br.PKGoals)*100/math.Max(1, float64(br.PKAttempts)), br.PKGoals, br.PKAttempts)
	
	// Test different PK levels
	for _, pk := range []int{8, 12, 16, 18} {
		attrs := cloneAttrs(base)
		attrs["PK"] = pk
		home := buildTeam("Home", attrs, defaultTactics())
		br := runBatch(home, away, 1000, false)
		t.Logf("PK=%d: PK conversion %.2f%% (%d/%d)",
			pk,
			float64(br.PKGoals)*100/math.Max(1, float64(br.PKAttempts)), br.PKGoals, br.PKAttempts)
	}
}

func TestControlCorrelation(t *testing.T) {
	t.Logf("\n========== 8. CONTROL vs WIN RATE ==========")
	base := baseAttrs()
	away := buildTeam("Away", base, defaultTactics())
	
	// Vary home team overall strength to get different control scenarios
	strengths := []int{8, 10, 12, 14, 16}
	for _, s := range strengths {
		attrs := baseAttrs()
		for k := range attrs {
			attrs[k] = s
		}
		homeMod := buildTeam("Home", attrs, defaultTactics())
		br := runBatch(homeMod, away, 1000, false)
		t.Logf("Home all-attr=%d: Possession=%.1f%% | WinRate=%.1f%% | HomeCtrlWins=%d HomeCtrlLoss=%d",
			s, br.AvgPossHome,
			float64(br.HomeWins)*100/float64(br.Total),
			br.HomeCtrlWins, br.HomeCtrlLoss)
	}
}

func TestEventCoverage(t *testing.T) {
	t.Logf("\n========== 9. EVENT COVERAGE ==========")
	base := baseAttrs()
	home := buildTeam("Home", base, defaultTactics())
	away := buildTeam("Away", base, defaultTactics())
	br := runBatchParallel(home, away, 5000, false)
	
	allEvents := []string{
		config.EventKickoff, config.EventBackPass, config.EventMidPass,
		config.EventShortPass, config.EventLongPass, config.EventWingBreak,
		config.EventCutInside, config.EventThroughBall, config.EventCross,
		config.EventHeader, config.EventCloseShot, config.EventLongShot,
		config.EventTackle, config.EventIntercept, config.EventClearance,
		config.EventKeeperSave, config.EventKeeperClaim, config.EventCorner,
		config.EventGoal, config.EventOwnGoal, config.EventFoul,
		config.EventFreeKick, config.EventYellowCard, config.EventRedCard,
		config.EventOffside, config.EventHalftime, config.EventFulltime,
		config.EventSubstitution, config.EventTurnover,
		// Phase 1: Simple 1v1 events
		config.EventSwitchPlay, config.EventLobPass, config.EventPassOverTop,
		config.EventShotBlock, config.EventBlockPass, config.EventOneOnOne,
		config.EventCoverDefense,
		// Phase 2: Medium events
		config.EventGoalKick, config.EventThrowIn, config.EventKeeperShortPass,
		config.EventKeeperThrow, config.EventCounterAttack, config.EventMidBreak,
		config.EventSecondHalfStart,
		// Phase 3: Multi-player events
		config.EventOverlap, config.EventTrianglePass, config.EventOneTwo,
		config.EventCrossRun, config.EventDoubleTeam, config.EventPressTogether,
		// Phase 4: Injury events
		config.EventMinorInjury, config.EventMajorInjury,
		// Phase 5: Rare dead ball
		config.EventDropBall,
	}
	
	for _, ev := range allEvents {
		count := br.EventCounts[ev]
		avg := float64(count) / float64(br.Total)
		status := "OK"
		if count == 0 {
			status = "MISSING"
		} else if avg < 0.01 {
			status = "RARE"
		}
		t.Logf("  %-20s: %.3f/match (total=%5d) [%s]", ev, avg, count, status)
	}
}
