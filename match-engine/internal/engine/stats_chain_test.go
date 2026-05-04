package engine

import (
	"fmt"
	"runtime"
	"sort"
	"testing"
)

func TestStatsChain(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())

	results := runMatchesParallel(500, home, away, runtime.NumCPU())

	var totalTurnovers, totalBoxEntries, totalShots, totalSOT, totalGoals int
	boxEntrySources := make(map[string]int)
	zoneCounts := make(map[string]int)
	passForwardCounts := make(map[string]int)
	n := len(results)

	for ri, res := range results {
		turnovers := 0
		boxEntries := 0
		lastZone := ""
		lastEventType := ""
		for _, ev := range res.Events {
			if ev.Type == "turnover" {
				turnovers++
			}
			if ev.Zone == "[0,1]" && lastZone != "[0,1]" {
				boxEntries++
				key := lastEventType
				if key == "" {
					key = "start"
				}
				boxEntrySources[key]++
			}
			zoneCounts[ev.Zone]++
			if (ev.Type == "short_pass" || ev.Type == "mid_pass") && ev.Result == "success" {
				passForwardCounts[ev.Type]++
			}
			lastZone = ev.Zone
			lastEventType = ev.Type
		}
		if ri == 0 {
			fmt.Printf("\n===== SAMPLE MATCH =====\n")
			fmt.Printf("Total events: %d\n", len(res.Events))
			fmt.Printf("Turnovers: %d\n", turnovers)
			fmt.Printf("Box Entries: %d\n", boxEntries)
			fmt.Printf("Goals: %d\n", res.Score.Home+res.Score.Away)
			// Print zone distribution for first match
			matchZones := make(map[string]int)
			for _, ev := range res.Events {
				matchZones[ev.Zone]++
			}
			var zpairs []struct{ z string; c int }
			for z, c := range matchZones {
				zpairs = append(zpairs, struct{ z string; c int }{z, c})
			}
			sort.Slice(zpairs, func(i, j int) bool { return zpairs[i].c > zpairs[j].c })
			for _, p := range zpairs {
				fmt.Printf("  Zone %s: %d events\n", p.z, p.c)
			}
		}
		totalTurnovers += turnovers
		totalBoxEntries += boxEntries
		totalShots += res.Stats.ShotsHome + res.Stats.ShotsAway
		totalSOT += res.Stats.ShotsOnTargetHome + res.Stats.ShotsOnTargetAway
		totalGoals += res.Score.Home + res.Score.Away
	}

	avgTurnovers := float64(totalTurnovers) / float64(n)
	avgBoxEntries := float64(totalBoxEntries) / float64(n)
	avgShots := float64(totalShots) / float64(n)
	avgSOTRate := float64(totalSOT) / float64(totalShots) * 100
	avgGoals := float64(totalGoals) / float64(n)

	fmt.Printf("\n===== STATS CHAIN (avg per match, n=%d) =====\n", n)
	fmt.Printf("Turnovers (进攻回合数)     : %.1f\n", avgTurnovers)
	fmt.Printf("Box Entries (进入禁区次数) : %.1f\n", avgBoxEntries)
	fmt.Printf("Shots (射门次数)           : %.1f\n", avgShots)
	fmt.Printf("Shot Accuracy (射正率)     : %.1f%%\n", avgSOTRate)
	fmt.Printf("Goals (总进球数)           : %.1f\n", avgGoals)
	fmt.Printf("\n===== RATIOS =====\n")
	fmt.Printf("Box Entry / Turnover       : %.1f%%\n", avgBoxEntries/avgTurnovers*100)
	fmt.Printf("Shot / Box Entry           : %.1f%%\n", avgShots/avgBoxEntries*100)
	fmt.Printf("Shot on Target / Shot      : %.1f%%\n", avgSOTRate)
	fmt.Printf("Goal / Shot on Target      : %.1f%%\n", avgGoals/(avgShots*avgSOTRate/100)*100)
	fmt.Printf("Goal / Shot                : %.1f%%\n", avgGoals/avgShots*100)
	fmt.Printf("Goal / Box Entry           : %.1f%%\n", avgGoals/avgBoxEntries*100)

	fmt.Printf("\n===== BOX ENTRY SOURCES =====\n")
	type pair struct {
		key   string
		count int
	}
	var pairs []pair
	for k, v := range boxEntrySources {
		pairs = append(pairs, pair{k, v})
	}
	sort.Slice(pairs, func(i, j int) bool {
		return pairs[i].count > pairs[j].count
	})
	for _, p := range pairs {
		avg := float64(p.count) / float64(n)
		pct := float64(p.count) / float64(totalBoxEntries) * 100
		fmt.Printf("%-20s : %5.1f (%4.1f%%)\n", p.key, avg, pct)
	}

	fmt.Printf("\n===== ZONE DISTRIBUTION (all matches) =====\n")
	var zpairs []pair
	for k, v := range zoneCounts {
		zpairs = append(zpairs, pair{k, v})
	}
	sort.Slice(zpairs, func(i, j int) bool {
		return zpairs[i].count > zpairs[j].count
	})
	for _, p := range zpairs {
		avg := float64(p.count) / float64(n)
		fmt.Printf("%-10s : %5.1f\n", p.key, avg)
	}
}
