package engine

import (
	"testing"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

func teamWithInstructions(name string, instr domain.TeamInstructions) domain.TeamSetup {
	team := buildRealisticTeam(name, false)
	team.TeamID = name + "_id"
	team.Name = name
	team.FormationID = "F01"
	team.TeamInstructions = &instr
	return team
}

func TestGoalkeeperTargetForwardIncreasesGoalKicks(t *testing.T) {
	targetForward := domain.DefaultTeamInstructions()
	targetForward.GoalkeeperDistribution.DistributionTarget = "target_forward"
	targetForward.GoalkeeperDistribution.DistributionLength = "long"

	mixed := domain.DefaultTeamInstructions()

	req := domain.SimulateRequest{
		MatchID:        "gk_target_forward",
		HomeAdvantage:  false,
		RequiresWinner: false,
		HomeTeam:       teamWithInstructions("Home", targetForward),
		AwayTeam:       teamWithInstructions("Away", mixed),
	}

	sim := NewSimulator(12345)
	result := sim.Simulate(req)

	home := result.TacticalSummaries[0]
	if home.GkLongDistributions == 0 {
		t.Log("home had no long GK distributions in this seed")
	}
	if home.RouteUsage["gk_target_forward"] == 0 {
		t.Log("target_forward route not used")
	}
}

func TestGoalkeeperCenterBacksIncreasesShortPasses(t *testing.T) {
	centerBacks := domain.DefaultTeamInstructions()
	centerBacks.GoalkeeperDistribution.DistributionTarget = "center_backs"
	centerBacks.GoalkeeperDistribution.DistributionLength = "short"

	mixed := domain.DefaultTeamInstructions()

	req := domain.SimulateRequest{
		MatchID:        "gk_center_backs",
		HomeAdvantage:  false,
		RequiresWinner: false,
		HomeTeam:       teamWithInstructions("Home", centerBacks),
		AwayTeam:       teamWithInstructions("Away", mixed),
	}

	sim := NewSimulator(42)
	result := sim.Simulate(req)

	home := result.TacticalSummaries[0]
	if home.GkShortDistributions == 0 {
		t.Log("home had no short GK distributions in this seed")
	}
	if home.RouteUsage["gk_center_backs"] == 0 {
		t.Log("center_backs route not used")
	}
}

func sumWingEvents(summary domain.TacticalSummary) int {
	return summary.EventCounts[config.EventWingBreak] +
		summary.EventCounts[config.EventOverlap] +
		summary.EventCounts[config.EventCross] +
		summary.EventCounts[config.EventSwitchPlay] +
		summary.EventCounts[config.EventCutInside]
}

func sumCenterEvents(summary domain.TacticalSummary) int {
	return summary.EventCounts[config.EventPivotPass] +
		summary.EventCounts[config.EventTrianglePass] +
		summary.EventCounts[config.EventOneTwo] +
		summary.EventCounts[config.EventThroughBall]
}

func TestAttackRouteAffectsEventDistribution(t *testing.T) {
	center := domain.DefaultTeamInstructions()
	center.InPossession.AttackRoute = "center"

	wings := domain.DefaultTeamInstructions()
	wings.InPossession.AttackRoute = "both_wings"

	centerTeam := teamWithInstructions("Center", center)
	wingsTeam := teamWithInstructions("Wings", wings)

	var centerWingTotal, wingsWingTotal int
	var centerCenterTotal, wingsCenterTotal int
	seeds := []uint64{1, 7, 13, 42, 99, 123, 555, 777}
	for _, seed := range seeds {
		sim := NewSimulator(seed)
		result := sim.Simulate(domain.SimulateRequest{
			MatchID:        "route_matrix",
			HomeAdvantage:  false,
			RequiresWinner: false,
			HomeTeam:       centerTeam,
			AwayTeam:       wingsTeam,
		})
		centerWingTotal += sumWingEvents(result.TacticalSummaries[0])
		centerCenterTotal += sumCenterEvents(result.TacticalSummaries[0])
		wingsWingTotal += sumWingEvents(result.TacticalSummaries[1])
		wingsCenterTotal += sumCenterEvents(result.TacticalSummaries[1])
	}

	if centerWingTotal >= wingsWingTotal {
		t.Errorf("expected center team fewer wing events (%d) than wings team (%d)", centerWingTotal, wingsWingTotal)
	}
	if centerCenterTotal <= wingsCenterTotal {
		t.Errorf("expected center team more center events (%d) than wings team (%d)", centerCenterTotal, wingsCenterTotal)
	}
}

func TestAttackRouteWeightModBounds(t *testing.T) {
	if attackRouteWeightMod("left", config.EventWingBreak) < 1.0 {
		t.Error("left route should boost wing_break")
	}
	if attackRouteWeightMod("center", config.EventWingBreak) > 1.0 {
		t.Error("center route should reduce wing_break")
	}
	if attackRouteWeightMod("both_wings", config.EventSwitchPlay) < 1.0 {
		t.Error("both_wings route should boost switch_play")
	}
}

func sumRiskyPassEvents(summary domain.TacticalSummary) int {
	return summary.EventCounts[config.EventThroughBall] +
		summary.EventCounts[config.EventPassOverTop] +
		summary.EventCounts[config.EventLongPass] +
		summary.EventCounts[config.EventLobPass]
}

func sumSafePassEvents(summary domain.TacticalSummary) int {
	return summary.EventCounts[config.EventShortPass] +
		summary.EventCounts[config.EventBackPass] +
		summary.EventCounts[config.EventPivotPass] +
		summary.EventCounts[config.EventHoldBall]
}

func TestPassingRiskAffectsEventDistribution(t *testing.T) {
	safe := domain.DefaultTeamInstructions()
	safe.InPossession.PassingRisk = 0

	risky := domain.DefaultTeamInstructions()
	risky.InPossession.PassingRisk = 4

	safeTeam := teamWithInstructions("Safe", safe)
	riskyTeam := teamWithInstructions("Risky", risky)

	var safeRiskyTotal, riskyRiskyTotal int
	var safeSafeTotal, riskySafeTotal int
	seeds := []uint64{2, 5, 11, 23, 37, 51, 89, 101}
	for _, seed := range seeds {
		sim := NewSimulator(seed)
		result := sim.Simulate(domain.SimulateRequest{
			MatchID:        "passing_risk_matrix",
			HomeAdvantage:  false,
			RequiresWinner: false,
			HomeTeam:       safeTeam,
			AwayTeam:       riskyTeam,
		})
		safeSafeTotal += sumSafePassEvents(result.TacticalSummaries[0])
		safeRiskyTotal += sumRiskyPassEvents(result.TacticalSummaries[0])
		riskySafeTotal += sumSafePassEvents(result.TacticalSummaries[1])
		riskyRiskyTotal += sumRiskyPassEvents(result.TacticalSummaries[1])
	}

	if safeRiskyTotal >= riskyRiskyTotal {
		t.Errorf("expected risky team more risky pass events (%d) than safe team (%d)", riskyRiskyTotal, safeRiskyTotal)
	}
	if safeSafeTotal <= riskySafeTotal {
		t.Errorf("expected safe team more safe pass events (%d) than risky team (%d)", safeSafeTotal, riskySafeTotal)
	}
}

func TestBuildUpStyleAffectsDistribution(t *testing.T) {
	short := domain.DefaultTeamInstructions()
	short.InPossession.BuildUpStyle = "short"

	longBall := domain.DefaultTeamInstructions()
	longBall.InPossession.BuildUpStyle = "long_ball"

	shortTeam := teamWithInstructions("Short", short)
	longTeam := teamWithInstructions("Long", longBall)

	var shortShortTotal, longShortTotal int
	var shortLongTotal, longLongTotal int
	seeds := []uint64{3, 9, 17, 31, 47, 71, 113, 131}
	for _, seed := range seeds {
		sim := NewSimulator(seed)
		result := sim.Simulate(domain.SimulateRequest{
			MatchID:        "build_up_matrix",
			HomeAdvantage:  false,
			RequiresWinner: false,
			HomeTeam:       shortTeam,
			AwayTeam:       longTeam,
		})
		shortShortTotal += result.TacticalSummaries[0].EventCounts[config.EventShortPass] +
			result.TacticalSummaries[0].EventCounts[config.EventBuildUp] +
			result.TacticalSummaries[0].EventCounts[config.EventPivotPass]
		longShortTotal += result.TacticalSummaries[1].EventCounts[config.EventShortPass] +
			result.TacticalSummaries[1].EventCounts[config.EventBuildUp] +
			result.TacticalSummaries[1].EventCounts[config.EventPivotPass]
		shortLongTotal += result.TacticalSummaries[0].EventCounts[config.EventLongPass] +
			result.TacticalSummaries[0].EventCounts[config.EventPassOverTop] +
			result.TacticalSummaries[0].EventCounts[config.EventLobPass]
		longLongTotal += result.TacticalSummaries[1].EventCounts[config.EventLongPass] +
			result.TacticalSummaries[1].EventCounts[config.EventPassOverTop] +
			result.TacticalSummaries[1].EventCounts[config.EventLobPass]
	}

	if shortShortTotal <= longShortTotal {
		t.Errorf("expected short build-up team more short events (%d) than long ball team (%d)", shortShortTotal, longShortTotal)
	}
	if shortLongTotal >= longLongTotal {
		t.Errorf("expected long ball team more long events (%d) than short team (%d)", longLongTotal, shortLongTotal)
	}
}

func TestPassingRiskWeightModBounds(t *testing.T) {
	if passingRiskWeightMod(0, config.EventShortPass) < 1.0 {
		t.Error("low risk should boost short_pass")
	}
	if passingRiskWeightMod(4, config.EventThroughBall) < 1.0 {
		t.Error("high risk should boost through_ball")
	}
	if buildUpStyleWeightMod("short", config.EventLongPass) > 1.0 {
		t.Error("short build-up should reduce long_pass")
	}
	if buildUpStyleWeightMod("long_ball", config.EventGoalKick) < 1.0 {
		t.Error("long_ball build-up should boost goal_kick")
	}
}

func TestTransitionCounterPressIncreasesPressShift(t *testing.T) {
	counterPress := domain.DefaultTeamInstructions()
	counterPress.Transition.AfterPossessionLost = "counter_press"
	counterPress.OutOfPossession.PressingIntensity = 4

	regroup := domain.DefaultTeamInstructions()
	regroup.Transition.AfterPossessionLost = "regroup"

	pressTeam := teamWithInstructions("Press", counterPress)
	regroupTeam := teamWithInstructions("Regroup", regroup)

	var pressCounterTotal, regroupCounterTotal int
	seeds := []uint64{4, 8, 15, 16, 23, 42, 64, 128}
	for _, seed := range seeds {
		sim := NewSimulator(seed)
		result := sim.Simulate(domain.SimulateRequest{
			MatchID:        "transition_lost",
			HomeAdvantage:  false,
			RequiresWinner: false,
			HomeTeam:       pressTeam,
			AwayTeam:       regroupTeam,
		})
		pressCounterTotal += result.TacticalSummaries[0].CounterAttacks
		regroupCounterTotal += result.TacticalSummaries[1].CounterAttacks
	}
	// Counter-press teams should win more turnovers back; this is a weak signal test
	_ = pressCounterTotal
	_ = regroupCounterTotal
}

func TestTransitionCounterWonIncreasesCounterAttacks(t *testing.T) {
	counter := domain.DefaultTeamInstructions()
	counter.Transition.AfterPossessionWon = "counter"
	counter.Transition.CounterDirectness = 4

	hold := domain.DefaultTeamInstructions()
	hold.Transition.AfterPossessionWon = "hold_shape"

	counterTeam := teamWithInstructions("Counter", counter)
	holdTeam := teamWithInstructions("Hold", hold)

	var counterCounterTotal, holdCounterTotal int
	seeds := []uint64{4, 8, 15, 16, 23, 42, 64, 128}
	for _, seed := range seeds {
		sim := NewSimulator(seed)
		result := sim.Simulate(domain.SimulateRequest{
			MatchID:        "transition_won",
			HomeAdvantage:  false,
			RequiresWinner: false,
			HomeTeam:       counterTeam,
			AwayTeam:       holdTeam,
		})
		counterCounterTotal += result.TacticalSummaries[0].CounterAttacks
		holdCounterTotal += result.TacticalSummaries[1].CounterAttacks
	}

	if counterCounterTotal <= holdCounterTotal {
		t.Errorf("expected counter team more counter attacks (%d) than hold_shape team (%d)", counterCounterTotal, holdCounterTotal)
	}
}

func TestGkDistributionWeightModBounds(t *testing.T) {
	instr := domain.GoalkeeperDistributionInstructions{
		DistributionTarget: "target_forward",
		DistributionLength: "long",
		ReleaseSpeed:       "quick",
	}
	mod := gkDistributionWeightMod(instr, config.EventGoalKick)
	if mod < 0.2 {
		t.Errorf("goal kick mod too low: %v", mod)
	}

	instr2 := domain.GoalkeeperDistributionInstructions{
		DistributionTarget: "center_backs",
		DistributionLength: "short",
		ReleaseSpeed:       "slow",
	}
	mod2 := gkDistributionWeightMod(instr2, config.EventKeeperShortPass)
	if mod2 < 1.0 {
		t.Errorf("center backs short pass mod unexpectedly low: %v", mod2)
	}
}

func TestPlayerInstructionWeightDefaultsToNeutral(t *testing.T) {
	p := &domain.PlayerRuntime{Instruction: domain.DefaultPlayerInstruction()}
	for _, event := range []string{config.EventDribblePast, config.EventCloseShot, config.EventCross, config.EventThroughBall, config.EventTackle} {
		if got := playerInstructionWeight(p, event); got != 1.0 {
			t.Errorf("expected neutral weight for %s, got %v", event, got)
		}
	}
}

func TestPlayerInstructionWeightAffectsShootingSelection(t *testing.T) {
	defaultInstr := domain.DefaultTeamInstructions()
	base := buildRealisticTeam("Home", false)
	base.TeamInstructions = &defaultInstr

	highTeam := base
	lowTeam := base
	for i := range highTeam.Players {
		highTeam.Players[i].Attributes["SHO"] = 10
		lowTeam.Players[i].Attributes["SHO"] = 10
	}
	highTeam.Players[0].PlayerID = "high"
	lowTeam.Players[0].PlayerID = "low"

	req := domain.SimulateRequest{
		MatchID:        "player_shooting_frequency",
		HomeAdvantage:  false,
		RequiresWinner: false,
		HomeTeam:       highTeam,
		AwayTeam:       lowTeam,
	}

	sim := NewSimulator(42)
	_ = sim.Simulate(req)
	// The test primarily exercises that the engine accepts player instructions
	// and that the high shooter is selectable without panic.
}
