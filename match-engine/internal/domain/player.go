package domain

// PlayerSetup represents input player data
type PlayerSetup struct {
	PlayerID   string         `json:"player_id"`
	Name       string         `json:"name"`
	Position   string         `json:"position"`    // GK/ST/WF/AMF/CMF/DMF/CB/SB
	Attributes map[string]int `json:"attributes"`  // 21 attrs 1-20
	Skills     []string       `json:"skills"`
	Stamina    float64        `json:"stamina"`     // initial stamina 0-100
	Height     int            `json:"height"`
	Foot       string         `json:"foot"`        // left/right/both
}

// PlayerRuntime is the in-match mutable state of a player
type PlayerRuntime struct {
	PlayerSetup
	CurrentStamina float64
	EffectiveAttrs [22]float64

	// Match stats
	Stats PlayerMatchStats

	// Cards / status
	YellowCards int
	RedCard     bool
	Injured     bool
	Substituted bool
}

// PlayerMatchStats accumulates during match
type PlayerMatchStats struct {
	Goals         int
	OwnGoals      int
	Assists       int
	Shots         int
	ShotsOnTarget int
	Passes        int
	PassesSucc   int
	Tackles      int
	TacklesSucc  int
	Intercepts   int
	Clearances   int
	Saves        int
	Fouls        int
	YellowCards  int
	RedCards     int
	FreeKicks    int
	FreeKickGoals int
	Penalties    int
	PenaltyGoals int
	RatingBase   float64 // starts at 6.0
}

func (p *PlayerRuntime) GetAttr(idx int) float64 {
	if idx < 0 || idx >= 22 {
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
	case "FK":
		return p.GetAttr(19)
	case "PK":
		return p.GetAttr(20)
	case "RUS":
		return p.GetAttr(21)
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
	for _, name := range []string{"SHO", "PAS", "DRI", "SPD", "STR", "STA", "DEF", "HEA", "VIS", "TKL", "ACC", "CRO", "CON", "FIN", "BAL", "COM", "SAV", "REF", "POS", "FK", "PK", "RUS"} {
		if v, ok := p.Attributes[name]; ok {
			pr.EffectiveAttrs[idx] = float64(v)
		}
		idx++
	}
	pr.Stats.RatingBase = 6.0
	return pr
}
