package config

// Position types (aligned with web game: 4 major positions)
const (
	PosGK = "GK"
	PosFW = "FW"
	PosMF = "MF"
	PosDF = "DF"
)

// Attribute indices
const (
	AttrSHO = iota // Shooting
	AttrPAS        // Passing
	AttrDRI        // Dribbling
	AttrSPD        // Speed
	AttrSTR        // Strength
	AttrSTA        // Stamina
	AttrDEF        // Defense
	AttrHEA        // Heading
	AttrVIS        // Vision
	AttrTKL        // Tackling
	AttrACC        // Acceleration
	AttrCRO        // Crossing
	AttrCON        // Control
	AttrFIN        // Finishing (long shots)
	AttrBAL        // Balance
	AttrCOM        // Composure (calmness under pressure)
	AttrSAV        // Saving
	AttrREF        // Reflexes
	AttrPOS        // Positioning (keeper)
	AttrSET        // Set piece (free kick + penalty)
	AttrDEC        // Decision making (football IQ)
	AttrCount
)

var AttrNames = []string{
	"SHO", "PAS", "DRI", "SPD", "STR", "STA", "DEF", "HEA", "VIS", "TKL",
	"ACC", "CRO", "CON", "FIN", "BAL", "COM", "SAV", "REF", "POS", "SET", "DEC",
}

// AttrIndex returns the index for a given attribute name, or -1 if not found
func AttrIndex(name string) int {
	for i, n := range AttrNames {
		if n == name {
			return i
		}
	}
	return -1
}

// Event types (MVP subset)
const (
	EventKickoff      = "kickoff"
	EventBackPass     = "back_pass"
	EventMidPass      = "mid_pass"
	EventShortPass    = "short_pass"
	EventLongPass     = "long_pass"
	EventWingBreak    = "wing_break"
	EventCutInside    = "cut_inside"
	EventDribblePast  = "dribble_past"
	EventThroughBall  = "through_ball"
	EventCross        = "cross"
	EventHeader       = "header"
	EventCloseShot    = "close_shot"
	EventLongShot     = "long_shot"
	EventTackle       = "tackle"
	EventIntercept    = "intercept"
	EventClearance    = "clearance"
	EventKeeperSave   = "keeper_save"
	EventKeeperClaim  = "keeper_claim"
	EventKeeperRush   = "keeper_rush"
	EventCorner       = "corner"
	EventGoal         = "goal"
	EventOwnGoal      = "own_goal"
	EventFoul         = "foul"
	EventFreeKick     = "free_kick"
	EventYellowCard   = "yellow_card"
	EventRedCard      = "red_card"
	EventOffside      = "offside"
	EventPreMatch     = "pre_match"
	EventHalftime     = "halftime"
	EventFulltime     = "fulltime"
	EventAddedTime    = "added_time"
	EventSubstitution = "substitution"
	EventTurnover     = "turnover"

	// Phase 1: Simple 1v1 events
	EventSwitchPlay   = "switch_play"
	EventLobPass      = "lob_pass"
	EventPassOverTop  = "pass_over_top"
	EventShotBlock    = "shot_block"
	EventBlockPass    = "block_pass"
	EventOneOnOne     = "one_on_one"
	EventCoverDefense = "cover_defense"

	// Phase 2: Medium complexity events
	EventGoalKick                 = "goal_kick"
	EventThrowIn                  = "throw_in"
	EventKeeperShortPass          = "keeper_short_pass"
	EventKeeperThrow              = "keeper_throw"
	EventCounterAttack            = "counter_attack"
	EventMidBreak                 = "mid_break"
	EventSecondHalfStart          = "second_half_start"
	EventExtraTimeStart           = "extra_time_start"
	EventExtraTimeSecondHalfStart = "extra_time_second_half_start"
	EventPenaltyShootout          = "penalty_shootout"

	// Phase 3: Multi-player events
	EventOverlap       = "overlap"
	EventTrianglePass  = "triangle_pass"
	EventOneTwo        = "one_two"
	EventCrossRun      = "cross_run"
	EventDoubleTeam    = "double_team"
	EventPressTogether = "press_together"

	// Phase 3.5: Build-up / possession events
	EventHoldBall  = "hold_ball"
	EventPivotPass = "pivot_pass"
	EventBuildUp   = "build_up"

	// Phase 4: Injury events
	EventMinorInjury = "minor_injury"
	EventMajorInjury = "major_injury"

	// Body parts for injury/wear system
	PartHamstring  = "hamstring"
	PartQuadriceps = "quadriceps"
	PartCalf       = "calf"
	PartGroin      = "groin"
	PartAnkle      = "ankle"
	PartKnee       = "knee"
	PartAchilles   = "achilles"
	PartFoot       = "foot"
	PartBack       = "back"
	PartRibs       = "ribs"
	PartShoulder   = "shoulder"
	PartFingers    = "fingers"
	PartHead       = "head"

	// Phase 5: Rare dead ball
	EventDropBall = "drop_ball"

	// Pass went out of play (sideline or goal line)
	EventPassOut = "pass_out"

	// Penalty kick event
	EventPenalty = "penalty"

	// Narrative stage events (no gameplay effect, for commentary flow)
	EventPenaltySetup    = "penalty_setup"
	EventPenaltyFocus    = "penalty_focus"
	EventFreeKickSetup   = "free_kick_setup"
	EventFreeKickFocus   = "free_kick_focus"
	EventCornerSetup     = "corner_setup"
	EventThrowInSetup    = "throw_in_setup"
	EventGoalKickSetup   = "goal_kick_setup"
	EventShotWindup      = "shot_windup"
	EventGoalCelebration = "goal_celebration"
)

// Zones [row][col]
const (
	ZoneFrontLeft   = "[0,0]"
	ZoneFrontCenter = "[0,1]"
	ZoneFrontRight  = "[0,2]"
	ZoneMidLeft     = "[1,0]"
	ZoneMidCenter   = "[1,1]"
	ZoneMidRight    = "[1,2]"
	ZoneBackLeft    = "[2,0]"
	ZoneBackCenter  = "[2,1]"
	ZoneBackRight   = "[2,2]"
)

// Formation base control weights (attack perspective)
// These are the FormationBase values from the design doc
var FormationBase = map[string][3][3]float64{
	"F01": { // Standard Balance 2-3-2
		{0.25, 0.35, 0.25},
		{0.35, 0.45, 0.35},
		{0.25, 0.15, 0.25},
	},
	"F02": { // Front Press 2-2-3
		{0.35, 0.45, 0.35},
		{0.30, 0.35, 0.30},
		{0.15, 0.10, 0.15},
	},
	"F03": { // Attack Storm 1-3-3
		{0.45, 0.55, 0.45},
		{0.40, 0.50, 0.40},
		{0.05, -0.10, 0.05},
	},
	"F04": { // Iron Wall 3-2-2
		{0.15, 0.25, 0.15},
		{0.20, 0.30, 0.20},
		{0.35, 0.45, 0.35},
	},
	"F05": { // All Out 1-2-4
		{0.50, 0.60, 0.50},
		{0.35, 0.40, 0.35},
		{-0.15, -0.25, -0.15},
	},
	"F06": { // Deep Defense 3-3-1
		{0.05, 0.15, 0.05},
		{0.20, 0.30, 0.20},
		{0.45, 0.55, 0.45},
	},
	"F07": { // Diamond Control 2-4-1
		{0.20, 0.30, 0.20},
		{0.45, 0.55, 0.45},
		{0.20, 0.30, 0.20},
	},
	"F08": { // Dual Wing 1-2-2-2
		{0.40, 0.30, 0.40},
		{0.30, 0.35, 0.30},
		{0.05, 0.15, 0.05},
	},
}

// ZoneWeight for each position (base, without tactical modifiers)
// Merged from 8 positions to 4 major positions (FW/MF/DF/GK)
var ZoneWeight = map[string][3][3]float64{
	PosFW: {
		{0.6, 0.7, 0.6},
		{0.5, 0.5, 0.5},
		{0.05, 0.1, 0.05},
	},
	PosMF: {
		{0.2, 0.5, 0.2},
		{0.6, 0.8, 0.6},
		{0.2, 0.5, 0.2},
	},
	PosDF: {
		{0.15, 0.15, 0.15},
		{0.35, 0.25, 0.35},
		{0.6, 0.65, 0.6},
	},
	PosGK: {
		{0.0, 0.0, 0.0},
		{0.0, 0.1, 0.0},
		{0.2, 1.0, 0.2},
	},
}

// Position attribute weights for PlayerStrength calculation per zone
// Merged from 8 positions to 4 major positions (FW/MF/DF/GK)
var PositionAttrWeight = map[string][AttrCount]float64{
	PosFW: {
		14, 6, 15, 18, 7, 5, 0, 5, 2, 0, 11, 9, 3, 5, 3, 0, 0, 0, 0, 4, 5,
	},
	PosMF: {
		3, 14, 8, 7, 6, 12, 9, 1, 10, 5, 4, 0, 11, 6, 4, 0, 0, 0, 0, 3, 9,
	},
	PosDF: {
		0, 10, 4, 12, 9, 10, 18, 8, 2, 7, 0, 6, 4, 1, 5, 0, 0, 0, 0, 1, 6,
	},
	PosGK: {
		0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 35, 25, 20, 10, 15,
	},
}
