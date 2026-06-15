package engine

import (
	"fmt"

	"match-engine/internal/domain"
)

// Career milestone thresholds for goals and assists.
var (
	goalMilestoneThresholds   = []int{1, 10, 25, 50, 75, 100, 150, 200, 250, 300, 400, 500}
	assistMilestoneThresholds = []int{1, 10, 25, 50, 75, 100, 150, 200, 250, 300, 400, 500}
)

// buildGoalMilestones returns milestone tags for a goal scored by player at minute.
// It combines career goal milestones, hat-trick, and late-goal tags.
func buildGoalMilestones(player *domain.PlayerRuntime, minute float64) []string {
	if player == nil {
		return nil
	}
	var ms []string

	totalGoals := player.CareerStats.Goals + player.Stats.Goals
	if tag := careerGoalMilestoneTag(totalGoals); tag != "" {
		ms = append(ms, tag)
	}

	if player.Stats.Goals == 3 {
		ms = append(ms, "hat_trick")
	}

	ms = append(ms, lateGoalMilestones(minute)...)

	return ms
}

// buildAssistMilestones returns milestone tags for an assist credited to player.
func buildAssistMilestones(player *domain.PlayerRuntime) []string {
	if player == nil {
		return nil
	}
	totalAssists := player.CareerStats.Assists + player.Stats.Assists
	if tag := careerAssistMilestoneTag(totalAssists); tag != "" {
		return []string{tag}
	}
	return nil
}

func careerGoalMilestoneTag(total int) string {
	for _, t := range goalMilestoneThresholds {
		if total == t {
			if t == 1 {
				return "first_goal"
			}
			return fmt.Sprintf("%d_goals", t)
		}
	}
	return ""
}

func careerAssistMilestoneTag(total int) string {
	for _, t := range assistMilestoneThresholds {
		if total == t {
			if t == 1 {
				return "first_assist"
			}
			return fmt.Sprintf("%d_assists", t)
		}
	}
	return ""
}

// lateGoalMilestones tags goals scored late in the second half.
// The engine uses 25 minutes per half; second half runs from minute 25 to 50+.
func lateGoalMilestones(minute float64) []string {
	if minute >= 49.0 {
		return []string{"last_minute_goal"}
	}
	if minute >= 45.0 {
		return []string{"late_goal"}
	}
	return nil
}

func mergeMilestones(a, b []string) []string {
	if len(a) == 0 {
		return b
	}
	if len(b) == 0 {
		return a
	}
	return append(a, b...)
}

func playerIDOrEmpty(p *domain.PlayerRuntime) string {
	if p == nil {
		return ""
	}
	return p.PlayerID
}

func playerNameOrEmpty(p *domain.PlayerRuntime) string {
	if p == nil {
		return ""
	}
	return p.Name
}
