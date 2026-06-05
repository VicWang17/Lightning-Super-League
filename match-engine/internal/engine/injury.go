package engine

import (
	"math"
	"math/rand/v2"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// ============================================================================
// Recovery Ranges: [severity][part] = {minDays, maxDays}
// Severity: 1=minor, 2=medium, 3=major
// ============================================================================

var RecoveryRanges = map[string]map[int][2]int{
	config.PartHamstring: {
		1: {1, 2},
		2: {4, 6},
		3: {7, 12},
	},
	config.PartQuadriceps: {
		1: {1, 2},
		2: {4, 6},
		3: {7, 12},
	},
	config.PartCalf: {
		1: {1, 2},
		2: {4, 6},
		3: {7, 12},
	},
	config.PartGroin: {
		1: {1, 2},
		2: {5, 7},
		3: {7, 12},
	},
	config.PartAnkle: {
		1: {1, 2},
		2: {5, 8},
		3: {7, 12},
	},
	config.PartKnee: {
		1: {1, 2},
		2: {5, 8},
		3: {7, 12},
	},
	config.PartAchilles: {
		1: {1, 2},
		2: {5, 8},
		3: {8, 12},
	},
	config.PartFoot: {
		1: {1, 1},
		2: {5, 8},
		3: {7, 12},
	},
	config.PartBack: {
		1: {1, 2},
		2: {5, 8},
		3: {7, 12},
	},
	config.PartRibs: {
		1: {1, 2},
		2: {6, 9},
		3: {8, 12},
	},
	config.PartShoulder: {
		1: {1, 2},
		2: {5, 8},
		3: {7, 12},
	},
	config.PartFingers: {
		1: {1, 1},
		2: {4, 6},
		3: {7, 12},
	},
	config.PartHead: {
		1: {1, 1},
		2: {5, 8},
		3: {7, 12},
	},
}

// ============================================================================
// Base Injury Rates by trigger action
// [light, medium, severe] probabilities
// ============================================================================

type InjuryRates [3]float64

var BaseInjuryRates = map[string]InjuryRates{
	"brutal_tackle":  {0.005, 0.0007, 0.0001},   // 0.5%, 0.07%, 0.01%
	"dangerous_foul": {0.010, 0.0015, 0.0002},   // 1.0%, 0.15%, 0.02%
	"sprint_fatigue": {0.004, 0.0005, 0.00005},  // 0.4%, 0.05%, 0.005%
	"aerial_clash":   {0.0025, 0.0004, 0.00005}, // 0.25%, 0.04%, 0.005%
	"keeper_dive":    {0.0025, 0.0004, 0.00005}, // 0.25%, 0.04%, 0.005%
	"fatigue_crit":   {0.007, 0.0010, 0.0001},   // 0.7%, 0.10%, 0.01%
	"post_overuse":   {0.005, 0.0007, 0.00005},  // 0.5%, 0.07%, 0.005%
}

// ============================================================================
// Candidate body parts by trigger action (ordered by priority)
// ============================================================================

var CandidateParts = map[string][]string{
	"brutal_tackle":  {config.PartAnkle, config.PartKnee, config.PartHamstring, config.PartCalf, config.PartGroin},
	"dangerous_foul": {config.PartAnkle, config.PartKnee, config.PartHamstring, config.PartGroin, config.PartQuadriceps, config.PartCalf, config.PartRibs, config.PartHead},
	"sprint_fatigue": {config.PartHamstring, config.PartGroin, config.PartCalf, config.PartQuadriceps, config.PartAnkle},
	"aerial_clash":   {config.PartHead, config.PartShoulder, config.PartBack, config.PartRibs, config.PartKnee},
	"keeper_dive":    {config.PartShoulder, config.PartFingers, config.PartBack, config.PartHead, config.PartKnee},
	"fatigue_crit":   {config.PartHamstring, config.PartQuadriceps, config.PartCalf, config.PartGroin},
	"post_overuse":   {config.PartHamstring, config.PartQuadriceps, config.PartCalf, config.PartGroin, config.PartBack},
}

// ============================================================================
// Injury name mapping: part + severity -> Chinese name
// ============================================================================

var InjuryNames = map[string]map[int]string{
	config.PartHamstring: {
		1: "腿筋肌肉紧绷",
		2: "腿筋轻度拉伤",
		3: "腿筋中度拉伤",
	},
	config.PartQuadriceps: {
		1: "股四头肌酸痛",
		2: "股四头肌轻度拉伤",
		3: "股四头肌中度拉伤",
	},
	config.PartCalf: {
		1: "小腿肌肉紧绷",
		2: "小腿轻度拉伤",
		3: "小腿中度拉伤",
	},
	config.PartGroin: {
		1: "腹股沟紧绷",
		2: "腹股沟轻度拉伤",
		3: "腹股沟中度拉伤",
	},
	config.PartAnkle: {
		1: "脚踝轻度扭伤",
		2: "脚踝中度扭伤",
		3: "脚踝严重扭伤",
	},
	config.PartKnee: {
		1: "膝盖不适",
		2: "膝盖挫伤",
		3: "膝盖内侧副韧带扭伤",
	},
	config.PartAchilles: {
		1: "跟腱紧绷",
		2: "跟腱轻度炎症",
		3: "跟腱中度炎症",
	},
	config.PartFoot: {
		1: "脚趾不适",
		2: "足部瘀伤",
		3: "脚趾骨折",
	},
	config.PartBack: {
		1: "腰背僵硬",
		2: "腰部肌肉痉挛",
		3: "下背部拉伤",
	},
	config.PartRibs: {
		1: "肋部不适",
		2: "肋骨挫伤",
		3: "单根肋骨骨折",
	},
	config.PartShoulder: {
		1: "肩部僵硬",
		2: "肩袖轻度拉伤",
		3: "肩关节扭伤",
	},
	config.PartFingers: {
		1: "手指不适",
		2: "手指挫伤",
		3: "手指骨折",
	},
	config.PartHead: {
		1: "面部擦伤",
		2: "面部淤肿",
		3: "鼻骨骨折",
	},
}

// ============================================================================
// Attribute impact mapping for minor injuries during match
// Maps attr name -> multiplier for each body part
// ============================================================================

var MinorInjuryAttrImpact = map[string]map[string]float64{
	config.PartHamstring: {
		"SPD": 0.85, "ACC": 0.85, "STA": 0.90, "DRI": 0.92, "SHO": 0.92,
	},
	config.PartQuadriceps: {
		"SHO": 0.88, "HEA": 0.88, "ACC": 0.92, "DRI": 0.95, "PAS": 0.95,
	},
	config.PartCalf: {
		"SPD": 0.90, "STA": 0.90, "BAL": 0.90, "PAS": 0.95,
	},
	config.PartGroin: {
		"DRI": 0.85, "SHO": 0.85, "ACC": 0.90, "PAS": 0.92,
	},
	config.PartAnkle: {
		"DRI": 0.88, "BAL": 0.88, "PAS": 0.92, "SHO": 0.92,
	},
	config.PartKnee: {
		"SPD": 0.85, "HEA": 0.85, "STR": 0.85, "STA": 0.90, "SHO": 0.90,
	},
	config.PartAchilles: {
		"SPD": 0.88, "HEA": 0.88, "STA": 0.88, "DRI": 0.92,
	},
	config.PartFoot: {
		"PAS": 0.92, "DRI": 0.92, "SHO": 0.95, "SPD": 0.95,
	},
	config.PartBack: {
		"STR": 0.90, "HEA": 0.90, "PAS": 0.95, "SHO": 0.95,
	},
	config.PartRibs: {
		"STR": 0.90, "STA": 0.90, "HEA": 0.92,
	},
	config.PartShoulder: {
		"STR": 0.90, "HEA": 0.90,
	},
	config.PartFingers: {
		"SAV": 0.85, "BAL": 0.97,
	},
	config.PartHead: {
		"HEA": 0.95,
	},
}

// ============================================================================
// Wear accumulation during match
// ============================================================================

// ApplyMatchWear adds wear from a specific action
func ApplyMatchWear(p *domain.PlayerRuntime, action string, staminaMultiplier float64) {
	switch action {
	case "sprint":
		p.MatchWear.Hamstring += 0.15 * staminaMultiplier
		p.MatchWear.Calf += 0.12 * staminaMultiplier
		p.MatchWear.Groin += 0.08 * staminaMultiplier
		p.MatchWear.Quadriceps += 0.08 * staminaMultiplier
		p.MatchWear.Knee += 0.05 * staminaMultiplier
	case "direction_change":
		p.MatchWear.Ankle += 0.15 * staminaMultiplier
		p.MatchWear.Knee += 0.12 * staminaMultiplier
		p.MatchWear.Groin += 0.10 * staminaMultiplier
	case "shot":
		p.MatchWear.Quadriceps += 0.12 * staminaMultiplier
		p.MatchWear.Groin += 0.10 * staminaMultiplier
		p.MatchWear.Knee += 0.08 * staminaMultiplier
		p.MatchWear.Back += 0.05 * staminaMultiplier
	case "header":
		p.MatchWear.Back += 0.10 * staminaMultiplier
		p.MatchWear.Shoulder += 0.12 * staminaMultiplier
		p.MatchWear.Head += 0.08 * staminaMultiplier
		p.MatchWear.Knee += 0.05 * staminaMultiplier
	case "tackle", "tackled":
		p.MatchWear.Ankle += 0.20 * staminaMultiplier
		p.MatchWear.Knee += 0.18 * staminaMultiplier
		p.MatchWear.Hamstring += 0.10 * staminaMultiplier
		p.MatchWear.Calf += 0.08 * staminaMultiplier
		p.MatchWear.Groin += 0.05 * staminaMultiplier
	case "keeper_dive":
		p.MatchWear.Shoulder += 0.20 * staminaMultiplier
		p.MatchWear.Back += 0.15 * staminaMultiplier
		p.MatchWear.Fingers += 0.15 * staminaMultiplier
		p.MatchWear.Knee += 0.12 * staminaMultiplier
		p.MatchWear.Head += 0.08 * staminaMultiplier
	case "keeper_kick":
		p.MatchWear.Quadriceps += 0.10 * staminaMultiplier
		p.MatchWear.Groin += 0.08 * staminaMultiplier
		p.MatchWear.Back += 0.05 * staminaMultiplier
	}
}

// ApplyMinuteWear adds base per-minute wear
func ApplyMinuteWear(p *domain.PlayerRuntime, staminaMultiplier float64) {
	p.MatchWear.Hamstring += 0.03 * staminaMultiplier
	p.MatchWear.Quadriceps += 0.03 * staminaMultiplier
	p.MatchWear.Calf += 0.03 * staminaMultiplier
	p.MatchWear.Knee += 0.02 * staminaMultiplier
	p.MatchWear.Back += 0.01 * staminaMultiplier
}

// GetStaminaWearMultiplier returns the multiplier based on current stamina
func GetStaminaWearMultiplier(stamina float64) float64 {
	switch {
	case stamina >= 60:
		return 1.0
	case stamina >= 30:
		return 1.3
	default:
		return 1.8
	}
}

// ============================================================================
// Body wear helpers
// ============================================================================

// GetBodyWearValue returns the wear value for a named body part
func GetBodyWearValue(wear *domain.BodyWear, part string) float64 {
	switch part {
	case config.PartHamstring:
		return wear.Hamstring
	case config.PartQuadriceps:
		return wear.Quadriceps
	case config.PartCalf:
		return wear.Calf
	case config.PartGroin:
		return wear.Groin
	case config.PartAnkle:
		return wear.Ankle
	case config.PartKnee:
		return wear.Knee
	case config.PartAchilles:
		return wear.Achilles
	case config.PartFoot:
		return wear.Foot
	case config.PartBack:
		return wear.Back
	case config.PartRibs:
		return wear.Ribs
	case config.PartShoulder:
		return wear.Shoulder
	case config.PartFingers:
		return wear.Fingers
	case config.PartHead:
		return wear.Head
	}
	return 0
}

// SetBodyWearValue sets the wear value for a named body part
func SetBodyWearValue(wear *domain.BodyWear, part string, value float64) {
	switch part {
	case config.PartHamstring:
		wear.Hamstring = value
	case config.PartQuadriceps:
		wear.Quadriceps = value
	case config.PartCalf:
		wear.Calf = value
	case config.PartGroin:
		wear.Groin = value
	case config.PartAnkle:
		wear.Ankle = value
	case config.PartKnee:
		wear.Knee = value
	case config.PartAchilles:
		wear.Achilles = value
	case config.PartFoot:
		wear.Foot = value
	case config.PartBack:
		wear.Back = value
	case config.PartRibs:
		wear.Ribs = value
	case config.PartShoulder:
		wear.Shoulder = value
	case config.PartFingers:
		wear.Fingers = value
	case config.PartHead:
		wear.Head = value
	}
}

// ============================================================================
// Injury check logic
// ============================================================================

// CheckInjury performs an injury roll for a player after a trigger action.
// Returns (injuryOccurred bool, selectedPart string, severity int)
// If injuryOccurred is true, caller should create the ActiveInjury and event.
func CheckInjury(r *rand.Rand, player *domain.PlayerRuntime, action string) (bool, string, int) {
	candidates, ok := CandidateParts[action]
	if !ok || len(candidates) == 0 {
		return false, "", 0
	}

	// Find candidate with highest wear
	maxWear := -1.0
	selectedPart := ""
	for _, part := range candidates {
		wear := GetBodyWearValue(&player.BodyWear, part)
		if wear > maxWear {
			maxWear = wear
			selectedPart = part
		}
	}

	if selectedPart == "" {
		return false, "", 0
	}

	// Use match wear + body wear for dynamic probability during match
	matchWear := GetBodyWearValue(&player.MatchWear, selectedPart)
	effectiveWear := maxWear + matchWear*0.5
	if effectiveWear > 100 {
		effectiveWear = 100
	}

	// Wear factor: (1 + wear/50)^2
	wearFactor := math.Pow(1.0+effectiveWear/50.0, 2.0)

	// Trait modifier
	traitMod := 1.0
	for _, trait := range player.Traits {
		switch trait {
		case "铁人":
			traitMod *= 0.60
		case "玻璃体质":
			traitMod *= 1.50
		}
	}
	if player.Age > 32 {
		traitMod *= 1.20
	}

	rates := BaseInjuryRates[action]
	lightProb := rates[0] * wearFactor * traitMod
	medProb := rates[1] * wearFactor * traitMod
	severeProb := rates[2] * wearFactor * traitMod

	roll := r.Float64()

	// Severity distribution based on wear level
	sevDist := getSeverityDistribution(effectiveWear)

	// Roll for injury occurrence first, then severity
	if roll < severeProb {
		// Severe injury (direct hit on severe threshold)
		return true, selectedPart, 3
	}
	if roll < severeProb+medProb {
		// Medium injury
		return true, selectedPart, 2
	}
	if roll < severeProb+medProb+lightProb {
		// Light injury - check if it should be light based on wear
		severityRoll := r.Float64()
		if severityRoll < sevDist[0] {
			return true, selectedPart, 1
		} else if severityRoll < sevDist[0]+sevDist[1] {
			return true, selectedPart, 2
		} else {
			return true, selectedPart, 3
		}
	}

	return false, "", 0
}

// getSeverityDistribution returns [lightProb, mediumProb, severeProb] based on wear
func getSeverityDistribution(wear float64) [3]float64 {
	switch {
	case wear <= 40:
		return [3]float64{0.80, 0.15, 0.05}
	case wear <= 60:
		return [3]float64{0.50, 0.35, 0.15}
	case wear <= 80:
		return [3]float64{0.25, 0.45, 0.30}
	default:
		return [3]float64{0.10, 0.35, 0.55}
	}
}

// RandomRecoveryDays returns a random day count from the recovery range
func RandomRecoveryDays(r *rand.Rand, part string, severity int) int {
	ranges, ok := RecoveryRanges[part]
	if !ok {
		return 3
	}
	bounds, ok := ranges[severity]
	if !ok {
		return 3
	}
	minDays, maxDays := bounds[0], bounds[1]
	if maxDays < minDays {
		maxDays = minDays
	}
	return r.IntN(maxDays-minDays+1) + minDays
}

// GetInjuryName returns the Chinese name for an injury
func GetInjuryName(part string, severity int) string {
	if names, ok := InjuryNames[part]; ok {
		if name, ok := names[severity]; ok {
			return name
		}
	}
	return "未知伤病"
}

// GetAttrImpactForMinor returns attribute multipliers for a minor injury
func GetAttrImpactForMinor(part string) map[string]float64 {
	if impact, ok := MinorInjuryAttrImpact[part]; ok {
		return impact
	}
	return map[string]float64{}
}

// ApplyMinorInjuryToAttrs applies minor injury attribute penalties
func ApplyMinorInjuryToAttrs(p *domain.PlayerRuntime) {
	if p.MatchInjury == nil || p.MatchInjury.Severity != 1 {
		return
	}
	impact := GetAttrImpactForMinor(p.MatchInjury.BodyPart)
	for attrName, multiplier := range impact {
		idx := config.AttrIndex(attrName)
		if idx >= 0 && idx < config.AttrCount {
			p.EffectiveAttrs[idx] *= multiplier
		}
	}
}

// BuildInjuryAttrImpact builds the attr_impact map for storage
func BuildInjuryAttrImpact(part string) map[string]float64 {
	result := make(map[string]float64)
	if impact, ok := MinorInjuryAttrImpact[part]; ok {
		for k, v := range impact {
			result[k] = v
		}
	}
	return result
}

// ============================================================================
// Post-match wear output: merge match wear into body wear
// ============================================================================

// FinalizeMatchWear adds match wear to the player's body wear and caps at 100
func FinalizeMatchWear(p *domain.PlayerRuntime) {
	mergeWear(&p.BodyWear, &p.MatchWear)
}

func mergeWear(dest, src *domain.BodyWear) {
	dest.Hamstring = capWear(dest.Hamstring + src.Hamstring)
	dest.Quadriceps = capWear(dest.Quadriceps + src.Quadriceps)
	dest.Calf = capWear(dest.Calf + src.Calf)
	dest.Groin = capWear(dest.Groin + src.Groin)
	dest.Ankle = capWear(dest.Ankle + src.Ankle)
	dest.Knee = capWear(dest.Knee + src.Knee)
	dest.Achilles = capWear(dest.Achilles + src.Achilles)
	dest.Foot = capWear(dest.Foot + src.Foot)
	dest.Back = capWear(dest.Back + src.Back)
	dest.Ribs = capWear(dest.Ribs + src.Ribs)
	dest.Shoulder = capWear(dest.Shoulder + src.Shoulder)
	dest.Fingers = capWear(dest.Fingers + src.Fingers)
	dest.Head = capWear(dest.Head + src.Head)
}

func capWear(v float64) float64 {
	if v > 100 {
		return 100
	}
	if v < 0 {
		return 0
	}
	return v
}
