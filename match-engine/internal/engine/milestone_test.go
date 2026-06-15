package engine

import (
	"testing"

	"match-engine/internal/domain"
)

func TestBuildGoalMilestones(t *testing.T) {
	p := &domain.PlayerRuntime{
		PlayerSetup: domain.PlayerSetup{
			Name: "Scorer",
			CareerStats: domain.CareerStats{
				Goals: 99,
			},
		},
	}
	p.Stats.Goals = 1 // this goal makes career total 100

	ms := buildGoalMilestones(p, 49.5)
	if !contains(ms, "100_goals") {
		t.Errorf("expected 100_goals milestone, got %v", ms)
	}
	if !contains(ms, "last_minute_goal") {
		t.Errorf("expected last_minute_goal tag, got %v", ms)
	}
}

func TestBuildGoalMilestonesFirstGoal(t *testing.T) {
	p := &domain.PlayerRuntime{
		PlayerSetup: domain.PlayerSetup{Name: "Scorer"},
	}
	p.Stats.Goals = 1 // this is the first career goal
	ms := buildGoalMilestones(p, 10.0)
	if !contains(ms, "first_goal") {
		t.Errorf("expected first_goal milestone, got %v", ms)
	}
}

func TestBuildGoalMilestonesHatTrick(t *testing.T) {
	p := &domain.PlayerRuntime{
		PlayerSetup: domain.PlayerSetup{Name: "Scorer"},
	}
	p.Stats.Goals = 3 // already completed hat-trick
	ms := buildGoalMilestones(p, 20.0)
	if !contains(ms, "hat_trick") {
		t.Errorf("expected hat_trick milestone, got %v", ms)
	}
}

func TestBuildAssistMilestones(t *testing.T) {
	p := &domain.PlayerRuntime{
		PlayerSetup: domain.PlayerSetup{
			Name: "Provider",
			CareerStats: domain.CareerStats{
				Assists: 49,
			},
		},
	}
	p.Stats.Assists = 1 // this assist makes career total 50
	ms := buildAssistMilestones(p)
	if !contains(ms, "50_assists") {
		t.Errorf("expected 50_assists milestone, got %v", ms)
	}
}

func TestMilestoneSuffixFormatting(t *testing.T) {
	ev := domain.MatchEvent{
		PlayerName: "Scorer",
		Player2Name: "Provider",
		Milestones: []string{"first_goal", "first_assist", "last_minute_goal"},
	}
	s := milestoneSuffix(ev)
	if s == "" {
		t.Fatal("expected non-empty suffix")
	}
	expectedSnippets := []string{"第一粒进球", "第一次助攻", "读秒破门"}
	for _, snippet := range expectedSnippets {
		if !containsSubstring(s, snippet) {
			t.Errorf("expected suffix to contain %q, got %q", snippet, s)
		}
	}
}

func contains(list []string, item string) bool {
	for _, s := range list {
		if s == item {
			return true
		}
	}
	return false
}

func containsSubstring(s, substr string) bool {
	return len(s) >= len(substr) && (s == substr || len(s) > 0 && containsSub(s, substr))
}

func containsSub(s, substr string) bool {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return true
		}
	}
	return false
}
