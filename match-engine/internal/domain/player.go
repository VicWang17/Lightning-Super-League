package domain

// BodyWear tracks wear/fatigue for each body part (0-100 scale)
type BodyWear struct {
	Hamstring  float64 `json:"hamstring"`
	Quadriceps float64 `json:"quadriceps"`
	Calf       float64 `json:"calf"`
	Groin      float64 `json:"groin"`
	Ankle      float64 `json:"ankle"`
	Knee       float64 `json:"knee"`
	Achilles   float64 `json:"achilles"`
	Foot       float64 `json:"foot"`
	Back       float64 `json:"back"`
	Ribs       float64 `json:"ribs"`
	Shoulder   float64 `json:"shoulder"`
	Fingers    float64 `json:"fingers"`
	Head       float64 `json:"head"`
}

// ActiveInjury represents a currently active injury on a player
type ActiveInjury struct {
	BodyPart      string             `json:"body_part"`
	InjuryName    string             `json:"injury_name"`
	Severity      int                `json:"severity"` // 1=minor, 2=medium, 3=major
	RemainingDays int                `json:"remaining_days"`
	AttrImpact    map[string]float64 `json:"attr_impact"` // only for minor injuries during match
}

// CareerStats tracks a player's career totals injected from the backend.
// The engine uses these to generate real-time milestone narratives.
type CareerStats struct {
	Goals       int `json:"goals"`
	Assists     int `json:"assists"`
	Appearances int `json:"appearances"`
}

// PlayerSetup represents input player data
type PlayerSetup struct {
	PlayerID    string         `json:"player_id"`
	Name        string         `json:"name"`
	Position    string         `json:"position"`   // GK/FW/MF/DF
	Number      int            `json:"number"`     // jersey number
	Attributes  map[string]int `json:"attributes"` // 21 attrs 1-20
	Skills      []string       `json:"skills"`
	Stamina     float64        `json:"stamina"` // initial stamina 0-100
	Height      int            `json:"height"`
	Foot        string         `json:"foot"`      // left/right/both
	BodyWear    BodyWear       `json:"body_wear"` // wear per body part
	Traits      []string       `json:"traits"`    // e.g. "铁人", "玻璃体质"
	Age         int            `json:"age"`
	CareerStats CareerStats    `json:"career_stats"`
}

// PlayerRuntime is the in-match mutable state of a player
type PlayerRuntime struct {
	PlayerSetup
	CurrentStamina float64
	EffectiveAttrs [21]float64

	// Match stats
	Stats PlayerMatchStats

	// Cards / status / injury
	YellowCards    int
	RedCard        bool
	Injured        bool
	InjurySeverity int // 0=none, 1=minor, 2=major (deprecated, use MatchInjury)
	Substituted    bool

	// Match injury info (new system)
	MatchInjury *ActiveInjury // nil = healthy, set when injury occurs during match

	// Instruction holds per-player tactical instructions. Defaults are applied if unset.
	Instruction PlayerInstruction

	// Skill context (set by simulator, read by resolver)
	SkillEventType string
	SkillZone      [2]int
	SkillMinute    float64
	SkillHalf      int

	// LastSkillSuffix is set by applySkillAttack/Defense when a skill triggers,
	// and consumed by addEvent to append to the event narrative.
	LastSkillSuffix string

	// Wear accumulation counters during match (for post-match output)
	MatchWear BodyWear
}

// PlayerMatchStats accumulates during match
type PlayerMatchStats struct {
	Goals         int
	OwnGoals      int
	Assists       int
	Shots         int
	ShotsOnTarget int
	Passes        int
	PassesSucc    int
	KeyPasses     int
	Crosses       int
	CrossesSucc   int
	Dribbles      int
	DribblesSucc  int
	Tackles       int
	TacklesSucc   int
	Intercepts    int
	Clearances    int
	Blocks        int
	Headers       int
	HeaderWins    int
	Saves         int
	Fouls         int
	FoulsDrawn    int
	Offsides      int
	YellowCards   int
	RedCards      int
	FreeKicks     int
	FreeKickGoals int
	Penalties     int
	PenaltyGoals  int
	Turnovers     int
	Touches       int
	RatingBase    float64 // starts at 6.0
}

func (p *PlayerRuntime) GetAttr(idx int) float64 {
	if idx < 0 || idx >= 24 {
		return 0
	}
	return p.EffectiveAttrs[idx]
}

func (p *PlayerRuntime) GetAttrByName(name string) float64 {
	switch name {
	case "SHO":
		return p.GetAttr(0)
	case "PAS":
		return p.GetAttr(1)
	case "DRI":
		return p.GetAttr(2)
	case "SPD":
		return p.GetAttr(3)
	case "STR":
		return p.GetAttr(4)
	case "STA":
		return p.GetAttr(5)
	case "DEF":
		return p.GetAttr(6)
	case "HEA":
		return p.GetAttr(7)
	case "VIS":
		return p.GetAttr(8)
	case "TKL":
		return p.GetAttr(9)
	case "ACC":
		return p.GetAttr(10)
	case "CRO":
		return p.GetAttr(11)
	case "CON":
		return p.GetAttr(12)
	case "FIN":
		return p.GetAttr(13)
	case "BAL":
		return p.GetAttr(14)
	case "COM":
		return p.GetAttr(15)
	case "SAV":
		return p.GetAttr(16)
	case "REF":
		return p.GetAttr(17)
	case "POS":
		return p.GetAttr(18)
	case "SET":
		return p.GetAttr(19)
	case "DEC":
		return p.GetAttr(20)
	}
	return 0
}

func NewPlayerRuntime(p PlayerSetup) *PlayerRuntime {
	pr := &PlayerRuntime{
		PlayerSetup:    p,
		CurrentStamina: p.Stamina,
	}
	// Initialize effective attrs from input
	idx := 0
	for _, name := range []string{"SHO", "PAS", "DRI", "SPD", "STR", "STA", "DEF", "HEA", "VIS", "TKL", "ACC", "CRO", "CON", "FIN", "BAL", "COM", "SAV", "REF", "POS", "SET", "DEC"} {
		if v, ok := p.Attributes[name]; ok {
			pr.EffectiveAttrs[idx] = float64(v)
		}
		idx++
	}
	pr.Stats.RatingBase = 6.0
	return pr
}
