package engine

import (
	"fmt"
	"strings"
	"testing"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ============================================================================
// Helpers
// ============================================================================

func makeTestPlayerWithSkills(id, pos string, attrs map[string]int, skills []string) domain.PlayerSetup {
	p := makeTestPlayer(id, pos, attrs)
	p.Skills = skills
	return p
}

// buildTeamWithSkill mounts a skill on a specific position index.
// posIdx: 0=GK, 1-3=DF, 4-6=MF, 7=FW (matches buildTeam order)
func buildTeamWithSkill(name string, attrs map[string]int, tactics domain.TacticalSetup, posIdx int, skill string) domain.TeamSetup {
	t := buildTeam(name, attrs, tactics)
	if posIdx >= 0 && posIdx < len(t.Players) {
		t.Players[posIdx].Skills = []string{skill}
	}
	return t
}

// buildTeamWithAllSkills mounts skills on every player (stress test)
func buildTeamWithAllSkills(name string, attrs map[string]int, tactics domain.TacticalSetup, skills []string) domain.TeamSetup {
	t := buildTeam(name, attrs, tactics)
	for i := range t.Players {
		t.Players[i].Skills = skills
	}
	for i := range t.Bench {
		t.Bench[i].Skills = skills
	}
	return t
}

// skillBatchResult holds aggregated stats for a batch of matches
type skillBatchResult struct {
	Matches                                                 int
	HomeWins, Draws, AwayWins                               int
	HomeGoals, AwayGoals                                    float64
	HomeShots, AwayShots                                    float64
	HomeShotsOnTarget, AwayShotsOnTarget                    float64
	HomePassAcc, AwayPassAcc                                float64
	HomeKeyPasses, AwayKeyPasses                            float64
	HomeDribAcc, AwayDribAcc                                float64
	HomeTackAcc, AwayTackAcc                                float64
	HomeHeaders, AwayHeaders                                float64
	HomeSaves, AwaySaves                                    float64
	HomeClearances, AwayClearances                          float64
	HomeFouls, AwayFouls                                    float64
	HomeInjuries, AwayInjuries                              int
	HomePoss                                                float64
	HomeAvgStamina, AwayAvgStamina                          float64
	SkillEventCount                                         int // events with skill narrative suffix
}

func runSkillBatch(home, away domain.TeamSetup, n int, skillName string) skillBatchResult {
	var r skillBatchResult
	r.Matches = n
	for i := 0; i < n; i++ {
		req := domain.SimulateRequest{
			MatchID:       fmt.Sprintf("skill_%d", i),
			HomeTeam:      home,
			AwayTeam:      away,
			HomeAdvantage: false,
		}
		sim := NewSimulator(uint64(i + 1))
		result := sim.Simulate(req)
		s := result.Stats

		if result.Score.Home > result.Score.Away {
			r.HomeWins++
		} else if result.Score.Home == result.Score.Away {
			r.Draws++
		} else {
			r.AwayWins++
		}
		r.HomeGoals += float64(result.Score.Home)
		r.AwayGoals += float64(result.Score.Away)
		r.HomeShots += float64(s.ShotsHome)
		r.AwayShots += float64(s.ShotsAway)
		r.HomeShotsOnTarget += float64(s.ShotsOnTargetHome)
		r.AwayShotsOnTarget += float64(s.ShotsOnTargetAway)
		r.HomePassAcc += s.PassAccuracyHome
		r.AwayPassAcc += s.PassAccuracyAway
		r.HomeKeyPasses += float64(s.KeyPassesHome)
		r.AwayKeyPasses += float64(s.KeyPassesAway)
		r.HomeDribAcc += s.DribbleAccuracyHome
		r.AwayDribAcc += s.DribbleAccuracyAway
		r.HomeTackAcc += s.TackleAccuracyHome
		r.AwayTackAcc += s.TackleAccuracyAway
		r.HomeHeaders += float64(s.HeadersHome)
		r.AwayHeaders += float64(s.HeadersAway)
		r.HomeSaves += float64(s.SavesHome)
		r.AwaySaves += float64(s.SavesAway)
		r.HomeClearances += float64(s.ClearancesHome)
		r.AwayClearances += float64(s.ClearancesAway)
		r.HomeFouls += float64(s.FoulsHome)
		r.AwayFouls += float64(s.FoulsAway)
		r.HomePoss += s.PossessionHome

		// Count injuries from events
		for _, ev := range result.Events {
			if ev.Type == config.EventMinorInjury || ev.Type == config.EventMajorInjury {
				if ev.Team == home.Name {
					r.HomeInjuries++
				} else {
					r.AwayInjuries++
				}
			}
			if skillName != "" && strings.Contains(ev.Narrative, skillName) {
				r.SkillEventCount++
			}
		}

	}
	fn := float64(n)
	r.HomeGoals /= fn
	r.AwayGoals /= fn
	r.HomeShots /= fn
	r.AwayShots /= fn
	r.HomeShotsOnTarget /= fn
	r.AwayShotsOnTarget /= fn
	r.HomePassAcc /= fn
	r.AwayPassAcc /= fn
	r.HomeKeyPasses /= fn
	r.AwayKeyPasses /= fn
	r.HomeDribAcc /= fn
	r.AwayDribAcc /= fn
	r.HomeTackAcc /= fn
	r.AwayTackAcc /= fn
	r.HomeHeaders /= fn
	r.AwayHeaders /= fn
	r.HomeSaves /= fn
	r.AwaySaves /= fn
	r.HomeClearances /= fn
	r.AwayClearances /= fn
	r.HomeFouls /= fn
	r.AwayFouls /= fn
	r.HomePoss /= fn

	return r
}

func formatSkillResult(label string, base, mod skillBatchResult) string {
	winDelta := (float64(mod.HomeWins)/float64(mod.Matches) - float64(base.HomeWins)/float64(base.Matches)) * 100
	goalDelta := (mod.HomeGoals - mod.AwayGoals) - (base.HomeGoals - base.AwayGoals)
	return fmt.Sprintf(
		"%-20s | Win %5.1f%% (Δ%+.1f%%) | GD %+.2f | Shots %.1f-%.1f | SoT %.1f-%.1f | PassAcc %.1f-%.1f | KeyP %.1f-%.1f | TackAcc %.1f-%.1f | Poss %.1f | Inj %d-%d | SkillEvt %d",
		label,
		float64(mod.HomeWins)/float64(mod.Matches)*100, winDelta,
		goalDelta,
		mod.HomeShots, mod.AwayShots,
		mod.HomeShotsOnTarget, mod.AwayShotsOnTarget,
		mod.HomePassAcc, mod.AwayPassAcc,
		mod.HomeKeyPasses, mod.AwayKeyPasses,
		mod.HomeTackAcc, mod.AwayTackAcc,
		mod.HomePoss,
		mod.HomeInjuries, mod.AwayInjuries,
		mod.SkillEventCount,
	)
}

// ============================================================================
// Category 1: Baseline
// ============================================================================

func TestSkillBaseline(t *testing.T) {
	attrs := baseAttrs()
	baseHome := buildTeam("Home", attrs, defaultTactics())
	baseAway := buildTeam("Away", attrs, defaultTactics())

	n := 50 // reduced for speed
	base := runSkillBatch(baseHome, baseAway, n, "")

	t.Logf("BASELINE (%d matches):", n)
	t.Logf("Win %.1f%% / Draw %.1f%% / Loss %.1f%%",
		float64(base.HomeWins)/float64(n)*100,
		float64(base.Draws)/float64(n)*100,
		float64(base.AwayWins)/float64(n)*100)
	t.Logf("Goals %.2f-%.2f | Shots %.1f-%.1f | PassAcc %.1f-%.1f | Poss %.1f",
		base.HomeGoals, base.AwayGoals,
		base.HomeShots, base.AwayShots,
		base.HomePassAcc, base.AwayPassAcc,
		base.HomePoss)

	// Sanity checks
	if base.HomeGoals < 0.5 || base.HomeGoals > 3.5 {
		t.Errorf("Baseline home goals %.2f out of reasonable range [0.5, 3.5]", base.HomeGoals)
	}
	if base.HomePassAcc < 60 || base.HomePassAcc > 95 {
		t.Errorf("Baseline home pass accuracy %.1f out of reasonable range [60, 95]", base.HomePassAcc)
	}
}

// ============================================================================
// Category 2: Individual Skill Effectiveness (Top 10 core skills)
// ============================================================================

func TestSkillIndividualImpact(t *testing.T) {
	attrs := baseAttrs()
	baseHome := buildTeam("Home", attrs, defaultTactics())
	baseAway := buildTeam("Away", attrs, defaultTactics())

	n := 100
	base := runSkillBatch(baseHome, baseAway, n, "")

	tests := []struct {
		Name            string
		Skill           string
		PosIdx          int  // position to mount skill
		ExpectWinUp     bool // if true, fail only if win rate drops >10%
		ExpectWinDown   bool // if true, fail only if win rate rises >10%
		CheckSkillEvents bool // if false, skip SkillEventCount check (for passive/global skills)
		MinSkillEvents  int   // minimum expected skill-triggered events
	}{
		{"禁区幽灵|精英", "禁区幽灵|精英", 7, true, false, true, 20},
		{"远射重炮|精英", "远射重炮|精英", 7, true, false, true, 5},
		{"抢点专家|精英", "抢点专家|精英", 7, true, false, true, 50},
		{"盘带大师|精英", "盘带大师|精英", 7, true, false, true, 20},
		{"花式魔术师|精英", "花式魔术师|精英", 7, true, false, true, 50},
		{"边路尖刀|精英", "边路尖刀|精英", 7, true, false, false, 0},
		{"致命直塞|精英", "致命直塞|精英", 4, true, false, true, 30},
		{"手术刀传球|精英", "手术刀传球|精英", 4, true, false, true, 100},
		{"铁壁|精英", "铁壁|精英", 1, false, false, true, 10}, // defense skill: modest win bump possible
		{"铲球专家|精英", "铲球专家|精英", 1, false, false, true, 100},
		{"神反应|精英", "神反应|精英", 0, false, false, true, 50},
		{"点球克星|精英", "点球克星|精英", 0, false, false, true, 5},
		{"铁人|精英", "铁人|精英", 4, false, false, true, 100}, // passive stamina skill
		{"玻璃体质|精英", "玻璃体质|精英", 4, false, true, false, 0}, // negative: may not trigger in 100 matches
		{"领导力|精英", "领导力|精英", 4, false, false, false, 0}, // global control skill, no per-event suffix
		{"大场面先生|精英", "大场面先生|精英", 4, false, false, false, 0}, // late-game passive
	}

	t.Logf("\n========== INDIVIDUAL SKILL IMPACT (%d matches each) ==========", n)
	t.Logf("BASELINE: Win %.1f%% | Goals %.2f-%.2f | PassAcc %.1f-%.1f | Poss %.1f",
		float64(base.HomeWins)/float64(n)*100,
		base.HomeGoals, base.AwayGoals,
		base.HomePassAcc, base.AwayPassAcc,
		base.HomePoss)

	for _, tt := range tests {
		modHome := buildTeamWithSkill("Home", attrs, defaultTactics(), tt.PosIdx, tt.Skill)
		mod := runSkillBatch(modHome, baseAway, n, strings.Split(tt.Skill, "|")[0])
		t.Log(formatSkillResult(tt.Name, base, mod))

		// Basic direction check: active attacking skills should not collapse win rate
		winRate := float64(mod.HomeWins) / float64(n) * 100
		baseWinRate := float64(base.HomeWins) / float64(n) * 100
		winDelta := winRate - baseWinRate

		if tt.ExpectWinUp && winDelta < -10 {
			t.Errorf("%s: expected win rate up, but dropped by %.1f%%", tt.Name, -winDelta)
		}
		if tt.ExpectWinDown && winDelta > 10 {
			t.Errorf("%s: expected win rate down, but rose by %.1f%%", tt.Name, winDelta)
		}

		// Skill trigger check
		if tt.CheckSkillEvents && mod.SkillEventCount < tt.MinSkillEvents {
			t.Errorf("%s: expected >=%d skill events, got %d", tt.Name, tt.MinSkillEvents, mod.SkillEventCount)
		}
	}
}

// ============================================================================
// Category 3: Quality Tier Scaling
// ============================================================================

func TestSkillQualityScaling(t *testing.T) {
	attrs := baseAttrs()
	baseAway := buildTeam("Away", attrs, defaultTactics())

	skillsToTest := []struct {
		Name            string
		Skill           string
		PosIdx          int
		Metric          string
		CheckSkillEvents bool
	}{
		{"禁区幽灵", "禁区幽灵", 7, "goals", true},
		{"抢点专家", "抢点专家", 7, "goals", true},
		{"手术刀传球", "手术刀传球", 4, "pass_acc", true},
		{"致命直塞", "致命直塞", 4, "key_passes", true},
		{"铲球专家", "铲球专家", 1, "tack_acc", true},
	}

	qualities := []string{"普通", "优秀", "精英", "传奇"}
	n := 100

	for _, st := range skillsToTest {
		t.Logf("\n========== %s 品级差异测试 ==========", st.Name)

		// baseline
		baseHome := buildTeam("Home", attrs, defaultTactics())
		base := runSkillBatch(baseHome, baseAway, n, st.Name)
		t.Logf("BASELINE | Win %.1f%% | Goals %.2f-%.2f | SkillEvt %d",
			float64(base.HomeWins)/float64(n)*100, base.HomeGoals, base.AwayGoals, base.SkillEventCount)

		var prevWinRate float64
		for i, q := range qualities {
			skillStr := st.Skill + "|" + q
			modHome := buildTeamWithSkill("Home", attrs, defaultTactics(), st.PosIdx, skillStr)
			mod := runSkillBatch(modHome, baseAway, n, st.Name)
			winRate := float64(mod.HomeWins) / float64(n) * 100
			t.Logf("%-6s | Win %.1f%% | Goals %.2f-%.2f | SkillEvt %d",
				q, winRate, mod.HomeGoals, mod.AwayGoals, mod.SkillEventCount)

			if i > 0 {
				// Win rate should not drop by more than 12% vs previous tier
				// (n=100 has high variance; we mainly check for gross anomalies)
				if winRate < prevWinRate-12 {
					t.Errorf("%s %s win rate (%.1f%%) dropped sharply vs previous tier (%.1f%%)",
						st.Name, q, winRate, prevWinRate)
				}
			}
			prevWinRate = winRate
		}
	}
}

// ============================================================================
// Category 4: Stacking & Synergy (brief)
// ============================================================================

func TestSkillStacking(t *testing.T) {
	attrs := baseAttrs()
	baseAway := buildTeam("Away", attrs, defaultTactics())
	n := 100

	// Baseline
	baseHome := buildTeam("Home", attrs, defaultTactics())
	base := runSkillBatch(baseHome, baseAway, n, "")

	// Single skill on FW
	singleHome := buildTeamWithSkill("Home", attrs, defaultTactics(), 7, "禁区幽灵|传奇")
	single := runSkillBatch(singleHome, baseAway, n, "禁区幽灵")

	// Same skill on FW + MF (stacking: multiple players with same skill)
	stackHome := buildTeam("Home", attrs, defaultTactics())
	stackHome.Players[7].Skills = []string{"禁区幽灵|传奇"}
	stackHome.Players[4].Skills = []string{"禁区幽灵|传奇"}
	stack := runSkillBatch(stackHome, baseAway, n, "禁区幽灵")

	// Multiple complementary skills on one player
	comboHome := buildTeam("Home", attrs, defaultTactics())
	comboHome.Players[7].Skills = []string{"禁区幽灵|传奇", "抢点专家|传奇", "花式魔术师|传奇"}
	combo := runSkillBatch(comboHome, baseAway, n, "")

	t.Logf("\n========== STACKING & SYNERGY (%d matches) ==========", n)
	t.Logf("BASELINE  | Win %.1f%% | Goals %.2f-%.2f", float64(base.HomeWins)/float64(n)*100, base.HomeGoals, base.AwayGoals)
	t.Logf("SINGLE    | Win %.1f%% | Goals %.2f-%.2f | SkillEvt %d", float64(single.HomeWins)/float64(n)*100, single.HomeGoals, single.AwayGoals, single.SkillEventCount)
	t.Logf("STACK(2pl)| Win %.1f%% | Goals %.2f-%.2f | SkillEvt %d", float64(stack.HomeWins)/float64(n)*100, stack.HomeGoals, stack.AwayGoals, stack.SkillEventCount)
	t.Logf("COMBO(3in1)| Win %.1f%% | Goals %.2f-%.2f | SkillEvt %d", float64(combo.HomeWins)/float64(n)*100, combo.HomeGoals, combo.AwayGoals, combo.SkillEventCount)

	// Sanity: combo should not be 2x stronger than single
	singleWin := float64(single.HomeWins) / float64(n) * 100
	comboWin := float64(combo.HomeWins) / float64(n) * 100
	if comboWin > singleWin+20 {
		t.Errorf("3-skill combo (%.1f%%) is >20%% above single skill (%.1f%%), possible overtuned stacking", comboWin, singleWin)
	}
}

// ============================================================================
// Category 5: Negative & Edge Cases
// ============================================================================

func TestSkillNegativeAndEdge(t *testing.T) {
	attrs := baseAttrs()
	baseAway := buildTeam("Away", attrs, defaultTactics())

	// Use larger sample for injury tests because injuries are rare
	nInjury := 200
	n := 100

	t.Logf("\n========== NEGATIVE & EDGE CASES ==========")

	// Glass body: injury rate should go UP
	glassHome := buildTeamWithSkill("Home", attrs, defaultTactics(), 4, "玻璃体质|传奇")
	glass := runSkillBatch(glassHome, baseAway, nInjury, "")
	baseHome := buildTeam("Home", attrs, defaultTactics())
	baseInjury := runSkillBatch(baseHome, baseAway, nInjury, "")
	t.Logf("玻璃体质|传奇 | Home Injuries %d vs Baseline %d (%d matches)", glass.HomeInjuries, baseInjury.HomeInjuries, nInjury)
	if baseInjury.HomeInjuries == 0 && glass.HomeInjuries == 0 {
		t.Logf("WARNING: both baseline and 玻璃体质 have 0 injuries in %d matches — sample still too small for reliable comparison", nInjury)
	} else if glass.HomeInjuries <= baseInjury.HomeInjuries {
		t.Errorf("玻璃体质 should increase injuries, but got %d vs baseline %d", glass.HomeInjuries, baseInjury.HomeInjuries)
	}

	// Iron man: injury rate should go DOWN (or equal if baseline is 0)
	ironHome := buildTeamWithSkill("Home", attrs, defaultTactics(), 4, "铁人|传奇")
	iron := runSkillBatch(ironHome, baseAway, nInjury, "铁人")
	t.Logf("铁人|传奇     | Home Injuries %d vs Baseline %d (%d matches) | SkillEvt %d", iron.HomeInjuries, baseInjury.HomeInjuries, nInjury, iron.SkillEventCount)
	if iron.SkillEventCount == 0 {
		t.Errorf("铁人 should produce skill events via stamina consumption, got 0")
	}
	if baseInjury.HomeInjuries == 0 && iron.HomeInjuries == 0 {
		t.Logf("WARNING: both baseline and 铁人 have 0 injuries in %d matches", nInjury)
	} else if iron.HomeInjuries > baseInjury.HomeInjuries {
		t.Errorf("铁人 should decrease injuries, but got %d vs baseline %d", iron.HomeInjuries, baseInjury.HomeInjuries)
	}

	// Position mismatch: GK with shooting skill should not boost GK
	baseHome2 := buildTeam("Home", attrs, defaultTactics())
	base2 := runSkillBatch(baseHome2, baseAway, n, "")
	gkShootHome := buildTeamWithSkill("Home", attrs, defaultTactics(), 0, "禁区幽灵|传奇")
	gkShoot := runSkillBatch(gkShootHome, baseAway, n, "禁区幽灵")
	t.Logf("GK挂禁区幽灵  | Win %.1f%% vs Baseline %.1f%%", float64(gkShoot.HomeWins)/float64(n)*100, float64(base2.HomeWins)/float64(n)*100)
	gkWinDelta := float64(gkShoot.HomeWins)/float64(n)*100 - float64(base2.HomeWins)/float64(n)*100
	if gkWinDelta > 5 {
		t.Logf("WARNING: GK with 禁区幽灵 win rate rose by %.1f%% — skill may be firing on wrong position", gkWinDelta)
	}

	// Malformed skill string
	malformedHome := buildTeam("Home", attrs, defaultTactics())
	malformedHome.Players[4].Skills = []string{"禁区幽灵|传奇", "铁人|不明品质", ""}
	malform := runSkillBatch(malformedHome, baseAway, n, "")
	t.Logf("Malformed    | Win %.1f%% vs Baseline %.1f%% (should be close)", float64(malform.HomeWins)/float64(n)*100, float64(base2.HomeWins)/float64(n)*100)
}
