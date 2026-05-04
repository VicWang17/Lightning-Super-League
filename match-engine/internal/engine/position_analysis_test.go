package engine

import (
	"testing"
)

// TestPositionRatings runs 1000 matches and analyzes per-position stats.
func TestPositionRatings(t *testing.T) {
	attrs := baseAttrs()
	home := buildTeam("Home", attrs, defaultTactics())
	away := buildTeam("Away", attrs, defaultTactics())

	results := runMatchesParallel(1000, home, away, 8)

	// Accumulate stats per position
	type posStats struct {
		count   int
		ratingSum float64
		goals   int
		shots   int
		sot     int
		passes  int
		passSucc int
		tackles int
		tackSucc int
		saves   int
		dribbles int
		dribSucc int
		headers int
		headSucc int
		crosses int
		crossSucc int
		fouls   int
		assists int
		keyPasses int
		clearances int
		blocks  int
		interceptions int
		yellowCards int
		redCards int
		freeKicks int
		penalties int
		penaltyGoals int
		freeKickGoals int
		offsides int
		touches  int
		turnovers int
	}

	posData := make(map[string]*posStats)
	for _, pos := range []string{"GK", "CB", "SB", "DMF", "CMF", "AMF", "WF", "ST"} {
		posData[pos] = &posStats{}
	}

	var totalShots, totalSoT, totalSaves, totalGoals int

	for _, r := range results {
		totalShots += r.Stats.ShotsHome + r.Stats.ShotsAway
		totalSoT += r.Stats.ShotsOnTargetHome + r.Stats.ShotsOnTargetAway
		totalSaves += r.Stats.SavesHome + r.Stats.SavesAway
		totalGoals += r.Score.Home + r.Score.Away

		for _, ps := range r.PlayerStats {
			p := ps.Position
			if _, ok := posData[p]; !ok {
				continue
			}
			s := posData[p]
			s.count++
			s.ratingSum += ps.Rating
			s.goals += ps.Goals
			s.shots += ps.Shots
			s.sot += ps.ShotsOnTarget
			s.passes += ps.Passes
			tmpAcc := int(float64(ps.Passes) * ps.PassAccuracy / 100)
			s.passSucc += tmpAcc
			s.tackles += ps.Tackles
			tmpTackAcc := int(float64(ps.Tackles) * ps.TackleAccuracy / 100)
			s.tackSucc += tmpTackAcc
			s.saves += ps.Saves
			s.dribbles += ps.Dribbles
			tmpDribAcc := int(float64(ps.Dribbles) * ps.DribbleAccuracy / 100)
			s.dribSucc += tmpDribAcc
			s.headers += ps.Headers
			tmpHeadAcc := int(float64(ps.Headers) * ps.HeaderAccuracy / 100)
			s.headSucc += tmpHeadAcc
			s.crosses += ps.Crosses
			tmpCrossAcc := int(float64(ps.Crosses) * ps.CrossAccuracy / 100)
			s.crossSucc += tmpCrossAcc
			s.fouls += ps.Fouls
			s.assists += ps.Assists
			s.keyPasses += ps.KeyPasses
			s.clearances += ps.Clearances
			s.blocks += ps.Blocks
			s.interceptions += ps.Interceptions
			s.yellowCards += ps.YellowCards
			s.redCards += ps.RedCards
			s.freeKicks += ps.FreeKicks
			s.penalties += ps.Penalties
			s.penaltyGoals += ps.PenaltyGoals
			s.freeKickGoals += ps.FreeKickGoals
			s.offsides += ps.Offsides
			s.touches += ps.Touches
			s.turnovers += ps.Turnovers
		}
	}

	t.Log("\n========== POSITION ANALYSIS (1000 matches) ==========")

	t.Log("\n--- OVERALL SHOOTING ---")
	if totalShots > 0 {
		t.Logf("Total Shots: %d | SoT: %d | Saves: %d | Goals: %d", totalShots, totalSoT, totalSaves, totalGoals)
		t.Logf("Shot On Target Rate: %.1f%%", float64(totalSoT)/float64(totalShots)*100)
	}
	if totalSoT > 0 {
		t.Logf("Goal Conversion (of SoT): %.1f%%", float64(totalGoals)/float64(totalSoT)*100)
		t.Logf("Save Rate (of SoT): %.1f%%", float64(totalSaves)/float64(totalSoT)*100)
	}
	if totalShots > 0 {
		t.Logf("Overall Conversion (shots→goals): %.1f%%", float64(totalGoals)/float64(totalShots)*100)
	}

	t.Log("\n--- PER POSITION ---")
	for _, pos := range []string{"GK", "CB", "SB", "DMF", "CMF", "AMF", "WF", "ST"} {
		s := posData[pos]
		if s.count == 0 {
			continue
		}
		avgRating := s.ratingSum / float64(s.count)
		t.Logf("\n%s (n=%d) Rating=%.2f", pos, s.count, avgRating)
		t.Logf("  Goals=%d Shots=%d SoT=%d Conv=%.1f%%",
			s.goals, s.shots, s.sot, safePct(s.goals, s.sot))
		t.Logf("  Passes=%d Acc=%.1f%% | Tackles=%d Acc=%.1f%% | Dribbles=%d Acc=%.1f%%",
			s.passes, safePct(s.passSucc, s.passes),
			s.tackles, safePct(s.tackSucc, s.tackles),
			s.dribbles, safePct(s.dribSucc, s.dribbles))
		t.Logf("  Headers=%d Acc=%.1f%% | Crosses=%d Acc=%.1f%% | Saves=%d",
			s.headers, safePct(s.headSucc, s.headers),
			s.crosses, safePct(s.crossSucc, s.crosses),
			s.saves)
		t.Logf("  Fouls=%d | Assists=%d | KeyP=%d | Clear=%d | Blocks=%d | Inter=%d",
			s.fouls, s.assists, s.keyPasses, s.clearances, s.blocks, s.interceptions)
		t.Logf("  YC=%d RC=%d | FK=%d FKG=%d | PK=%d PKG=%d | Off=%d | Touches=%d | TO=%d",
			s.yellowCards, s.redCards, s.freeKicks, s.freeKickGoals,
			s.penalties, s.penaltyGoals, s.offsides, s.touches, s.turnovers)
	}

	// Assertions
	t.Log("\n--- ASSERTIONS ---")
	gk := posData["GK"]
	st := posData["ST"]
	if gk != nil && gk.count > 0 {
		avgRating := gk.ratingSum / float64(gk.count)
		if avgRating > 7.5 {
			t.Errorf("GK average rating %.2f too high (expected ≤7.5)", avgRating)
		}
		if gk.saves > 0 && totalSoT > 0 {
			gkSaveRate := float64(gk.saves) / float64(totalSoT) * 100
			if gkSaveRate > 80 {
				t.Errorf("GK save rate %.1f%% too high (expected ≤80%%)", gkSaveRate)
			}
		}
	}
	if st != nil && st.count > 0 {
		avgRating := st.ratingSum / float64(st.count)
		if avgRating < 6.0 {
			t.Errorf("ST average rating %.2f too low (expected ≥6.0)", avgRating)
		}
		if st.shots > 0 {
			conv := float64(st.goals) / float64(st.shots) * 100
			if conv < 8 {
				t.Errorf("ST shot conversion %.1f%% too low (expected ≥8%%)", conv)
			}
		}
	}
	if totalSoT > 0 {
		saveRate := float64(totalSaves) / float64(totalSoT) * 100
		if saveRate > 70 {
			t.Errorf("Overall save rate %.1f%% too high (expected ≤70%%)", saveRate)
		}
	}
	if totalShots > 0 {
		sotRate := float64(totalSoT) / float64(totalShots) * 100
		if sotRate < 35 {
			t.Errorf("Overall SoT rate %.1f%% too low (expected ≥35%%)", sotRate)
		}
		if sotRate > 55 {
			t.Errorf("Overall SoT rate %.1f%% too high (expected ≤55%%)", sotRate)
		}
	}
}

func safePct(num, den int) float64 {
	if den == 0 {
		return 0
	}
	return float64(num) / float64(den) * 100
}
