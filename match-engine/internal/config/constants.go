package config

// Position types
const (
	PosGK  = "GK"
	PosST  = "ST"
	PosWF  = "WF"
	PosAMF = "AMF"
	PosCMF = "CMF"
	PosDMF = "DMF"
	PosCB  = "CB"
	PosSB  = "SB"
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
	AttrFK         // Free kick
	AttrPK         // Penalty kick
	AttrRUS        // Rushing (keeper coming out)
	AttrCount
)

var AttrNames = []string{
	"SHO", "PAS", "DRI", "SPD", "STR", "STA", "DEF", "HEA", "VIS", "TKL",
	"ACC", "CRO", "CON", "FIN", "BAL", "COM", "SAV", "REF", "POS", "FK", "PK", "RUS",
}

// Event types (MVP subset)
const (
	EventKickoff        = "kickoff"
	EventBackPass       = "back_pass"
	EventMidPass        = "mid_pass"
	EventShortPass      = "short_pass"
	EventLongPass       = "long_pass"
	EventWingBreak      = "wing_break"
	EventCutInside      = "cut_inside"
	EventThroughBall    = "through_ball"
	EventCross          = "cross"
	EventHeader         = "header"
	EventCloseShot      = "close_shot"
	EventLongShot       = "long_shot"
	EventTackle         = "tackle"
	EventIntercept      = "intercept"
	EventClearance      = "clearance"
	EventKeeperSave     = "keeper_save"
	EventKeeperClaim    = "keeper_claim"
	EventCorner         = "corner"
	EventGoal           = "goal"
	EventOwnGoal        = "own_goal"
	EventFoul           = "foul"
	EventFreeKick       = "free_kick"
	EventYellowCard     = "yellow_card"
	EventRedCard        = "red_card"
	EventOffside        = "offside"
	EventHalftime       = "halftime"
	EventFulltime       = "fulltime"
	EventSubstitution   = "substitution"
	EventTurnover       = "turnover"
)

// Zones [row][col]
const (
	ZoneFrontLeft  = "[0,0]"
	ZoneFrontCenter = "[0,1]"
	ZoneFrontRight = "[0,2]"
	ZoneMidLeft    = "[1,0]"
	ZoneMidCenter  = "[1,1]"
	ZoneMidRight   = "[1,2]"
	ZoneBackLeft   = "[2,0]"
	ZoneBackCenter = "[2,1]"
	ZoneBackRight  = "[2,2]"
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
var ZoneWeight = map[string][3][3]float64{
	PosST: {
		{0.2, 1.0, 0.2},
		{0.3, 0.6, 0.3},
		{0.0, 0.1, 0.0},
	},
	PosWF: {
		{1.0, 0.4, 0.2},
		{0.7, 0.3, 0.2},
		{0.1, 0.1, 0.1},
	},
	PosAMF: {
		{0.3, 0.9, 0.3},
		{0.6, 0.8, 0.6},
		{0.1, 0.2, 0.1},
	},
	PosCMF: {
		{0.2, 0.4, 0.2},
		{0.7, 0.9, 0.7},
		{0.3, 0.5, 0.3},
	},
	PosDMF: {
		{0.1, 0.2, 0.1},
		{0.4, 0.8, 0.4},
		{0.3, 0.7, 0.3},
	},
	PosCB: {
		{0.0, 0.1, 0.0},
		{0.1, 0.2, 0.1},
		{0.4, 0.9, 0.4},
	},
	PosSB: {
		{0.3, 0.2, 0.1},
		{0.6, 0.3, 0.2},
		{0.8, 0.4, 0.2},
	},
	PosGK: {
		{0.0, 0.0, 0.0},
		{0.0, 0.1, 0.0},
		{0.2, 1.0, 0.2},
	},
}

// Position attribute weights for PlayerStrength calculation per zone
// Simplified: each position values certain attributes more in certain zones
// We'll use a simplified global weight per position for now
var PositionAttrWeight = map[string][AttrCount]float64{
	PosST:  {
		20, 3, 15, 18, 10, 3, 0, 10, 0, 0, 10, 3, 0, 5, 3, 0, 0, 0, 0, 1, 3, 0,
	},
	PosWF:  {
		8, 8, 14, 17, 3, 7, 0, 0, 3, 0, 12, 15, 5, 5, 3, 0, 0, 0, 0, 2, 1, 0,
	},
	PosAMF: {
		9, 13, 9, 8, 5, 9, 0, 0, 16, 0, 8, 0, 10, 10, 3, 0, 0, 0, 0, 4, 1, 0,
	},
	PosCMF: {
		0, 20, 9, 7, 4, 12, 10, 0, 11, 5, 2, 0, 12, 5, 3, 0, 0, 0, 0, 2, 0, 0,
	},
	PosDMF: {
		0, 9, 5, 7, 9, 14, 18, 4, 4, 10, 2, 0, 10, 3, 5, 0, 0, 0, 0, 1, 0, 0,
	},
	PosCB:  {
		0, 8, 0, 6, 14, 10, 23, 16, 0, 9, 1, 0, 5, 0, 8, 0, 0, 0, 0, 0, 1, 0,
	},
	PosSB:  {
		0, 13, 9, 18, 4, 11, 14, 0, 5, 5, 0, 12, 3, 3, 3, 0, 0, 0, 0, 1, 0, 0,
	},
	PosGK:  {
		0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 35, 25, 20, 0, 0, 10,
	},
}
