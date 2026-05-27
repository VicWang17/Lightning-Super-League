package engine

import (
	"strings"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// SkillQuality 技能品质等级
type SkillQuality int

const (
	QualityCommon    SkillQuality = iota // 普通 (白色)
	QualityGood                          // 优秀 (蓝色)
	QualityElite                         // 精英 (紫色)
	QualityLegendary                     // 传奇 (红色)
)

// PlayerSkill 球员携带的技能（含品质）
type PlayerSkill struct {
	Name    string       // 技能名称
	Quality SkillQuality // 品质等级
}

// SkillBonus 技能对当前事件的数值修正
type SkillBonus struct {
	AttackMod       float64 // 攻击力修正 (+/-)
	DefenseMod      float64 // 防御力修正 (+/-)
	ProbMod         float64 // 独立概率修正 (+/-)
	WeightMod       float64 // 选择权重修正 (乘数，如 1.10 = +10%)
	ControlMod      float64 // 区域控制度修正 (+/-)
	StaminaMod      float64 // 体力消耗比例修正 (乘数，如 0.85 = -15%)
	AttrMultiplier  float64 // 全属性临时修正系数 (乘数，如 1.08 = +8%)
	NarrativeSuffix string  // 技能触发叙事后缀
}

// SkillContext 技能判断的上下文
type SkillContext struct {
	EventType  string
	Player     *domain.PlayerRuntime
	Opponent   *domain.PlayerRuntime
	Zone       [2]int
	Minute     float64
	Half       int
	IsHome     bool
	MatchState *domain.MatchState
}

// qualityMultiplier 品质对基础加成的放大系数
var qualityMultiplier = []float64{
	QualityCommon:    0.6,
	QualityGood:      0.8,
	QualityElite:     1.0,
	QualityLegendary: 1.3,
}

// ParseSkills 将字符串数组解析为 PlayerSkill 列表
// 支持格式: "技能名" 或 "技能名|品质"
// 品质映射: 普通/Common/白 -> 0, 优秀/Good/蓝 -> 1, 精英/Elite/紫 -> 2, 名人堂/传奇/Legendary/红 -> 3
func ParseSkills(raw []string) []PlayerSkill {
	result := make([]PlayerSkill, 0, len(raw))
	for _, s := range raw {
		parts := strings.Split(s, "|")
		name := strings.TrimSpace(parts[0])
		if name == "" {
			continue
		}
		quality := QualityElite // 默认精英
		if len(parts) > 1 {
			q := strings.TrimSpace(parts[1])
			switch q {
			case "普通", "Common", "白", "white", "0":
				quality = QualityCommon
			case "优秀", "Good", "蓝", "blue", "1":
				quality = QualityGood
			case "精英", "Elite", "紫", "purple", "2":
				quality = QualityElite
			case "名人堂", "传奇", "HallOfFame", "Legendary", "红", "red", "3":
				quality = QualityLegendary
			}
		}
		result = append(result, PlayerSkill{Name: name, Quality: quality})
	}
	return result
}

func maxFloat64(a, b float64) float64 {
	if a > b {
		return a
	}
	return b
}

// ComputeSkillBonus 汇总某球员在特定上下文中的所有技能加成
func ComputeSkillBonus(ctx SkillContext) SkillBonus {
	if ctx.Player == nil || len(ctx.Player.Skills) == 0 {
		return SkillBonus{}
	}

	var total SkillBonus
	skillMap := ParseSkills(ctx.Player.Skills)

	for _, ps := range skillMap {
		handler, ok := skillHandlers[ps.Name]
		if !ok {
			continue
		}
		base := handler(ctx)
		mul := qualityMultiplier[ps.Quality]

		// 同一球员多个技能影响同一事件时取最大值（负面技能除外）
		if ps.Name == "玻璃体质" {
			// 负面技能直接叠加
			total.ProbMod += base.ProbMod * mul
		} else {
			total.AttackMod = maxFloat64(total.AttackMod, base.AttackMod*mul)
			total.DefenseMod = maxFloat64(total.DefenseMod, base.DefenseMod*mul)
			if base.ProbMod < 0 {
				total.ProbMod += base.ProbMod * mul
			} else {
				total.ProbMod = maxFloat64(total.ProbMod, base.ProbMod*mul)
			}
			total.WeightMod = maxFloat64(total.WeightMod, base.WeightMod*mul)
			total.ControlMod = maxFloat64(total.ControlMod, base.ControlMod*mul)
			if base.StaminaMod != 0 {
				if total.StaminaMod == 0 {
					total.StaminaMod = 1.0
				}
				total.StaminaMod *= base.StaminaMod // 乘数类用乘法
			}
			if base.AttrMultiplier != 0 {
				total.AttrMultiplier = maxFloat64(total.AttrMultiplier, base.AttrMultiplier*mul)
			}
		}

		if base.NarrativeSuffix != "" && total.NarrativeSuffix == "" {
			total.NarrativeSuffix = base.NarrativeSuffix
		}
	}

	return total
}

// ComputeTeamSkillBonus 汇总全队技能加成（用于光环类技能，如领导力）
func ComputeTeamSkillBonus(players []*domain.PlayerRuntime, ctx SkillContext) SkillBonus {
	var bestLeadership SkillBonus
	var bestLeadershipQuality SkillQuality = -1

	for _, p := range players {
		if p == nil || len(p.Skills) == 0 {
			continue
		}
		for _, ps := range ParseSkills(p.Skills) {
			if ps.Name == "领导力" {
				if ps.Quality > bestLeadershipQuality {
					bestLeadershipQuality = ps.Quality
					ctx.Player = p
					bestLeadership = skillHandlers["领导力"](ctx)
				}
			}
		}
	}

	if bestLeadershipQuality >= 0 {
		mul := qualityMultiplier[bestLeadershipQuality]
		bestLeadership.ControlMod *= mul
	}
	return bestLeadership
}

// skillHandlers 技能名 -> 效果计算函数（返回基础加成，不含品质系数）
var skillHandlers = map[string]func(ctx SkillContext) SkillBonus{
	// ===== 通用类 =====
	"铁人":         calcIronMan,
	"领导力":       calcLeadership,
	"玻璃体质":     calcGlassBody,
	"大场面先生":   calcClutchPlayer,
	"快速恢复":     calcFastRecovery,

	// ===== FW 类 =====
	"禁区幽灵":     calcZoneGhost,
	"抢点专家":     calcPoacher,
	"远射重炮":     calcLongShotExpert,
	"边路尖刀":     calcSpeedDemon,
	"盘带大师":     calcDribbleMaster,
	"致命直塞":     calcKillerPass,
	"内切杀手":     calcCutInsideExpert,
	"点球专家":     calcPenaltyExpert,
	"补射猎手":     calcReboundHunter,
	"花式魔术师":   calcDribbleMagician,

	// ===== MF 类 =====
	"手术刀传球":   calcSurgicalPass,
	"节拍器":       calcMetronome,
	"全能中场":     calcBoxToBox,
	"长传调度":     calcLongPassExpert,
	"拦截专家":     calcInterceptExpert,
	"组织核心":     calcPlaymaker,
	"定位球大师":   calcSetPieceMaster,
	"绞肉机":       calcDestroyer,

	// ===== DF 类 =====
	"铁壁":         calcIronWall,
	"铲球专家":     calcTackleExpert,
	"预判大师":     calcAnticipationMaster,
	"盯人专家":     calcMarkingExpert,
	"空中堡垒":     calcAerialFortress,
	"边路屏障":     calcWingBarrier,
	"清道夫":       calcSweeper,

	// ===== GK 类 =====
	"神反应":       calcDivineReflexes,
	"门线技术":     calcGoalLineTech,
	"出击果断":     calcRushOutExpert,
	"手抛球反击":   calcQuickThrow,
	"点球克星":     calcPenaltyKiller,
}

// ============================================================================
// 通用类技能
// ============================================================================

func calcIronMan(ctx SkillContext) SkillBonus {
	return SkillBonus{StaminaMod: 0.85, ProbMod: -0.08, NarrativeSuffix: "【铁人触发】"}
}

func calcLeadership(ctx SkillContext) SkillBonus {
	return SkillBonus{ControlMod: 0.03}
}

func calcGlassBody(ctx SkillContext) SkillBonus {
	return SkillBonus{ProbMod: 0.08, NarrativeSuffix: "【玻璃体质触发】"}
}

func calcClutchPlayer(ctx SkillContext) SkillBonus {
	if ctx.Minute >= 40 && ctx.Half == 2 {
		return SkillBonus{AttrMultiplier: 1.08}
	}
	return SkillBonus{}
}

func calcFastRecovery(ctx SkillContext) SkillBonus {
	// 每5分钟恢复1% -> 在主循环中处理
	return SkillBonus{}
}

// ============================================================================
// FW 类技能
// ============================================================================

func calcZoneGhost(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventCloseShot && ctx.Zone[0] == 0 {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【禁区幽灵触发】"}
	}
	return SkillBonus{}
}

func calcPoacher(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventHeader {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【抢点专家触发】"}
	}
	return SkillBonus{}
}

func calcLongShotExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventLongShot {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【远射重炮触发】"}
	}
	return SkillBonus{}
}

func calcSpeedDemon(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventCounterAttack || ctx.EventType == config.EventWingBreak {
		return SkillBonus{WeightMod: 1.10, NarrativeSuffix: "【边路尖刀触发】"}
	}
	return SkillBonus{}
}

func calcDribbleMaster(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventWingBreak || ctx.EventType == config.EventCutInside {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【盘带大师触发】"}
	}
	return SkillBonus{}
}

func calcKillerPass(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventThroughBall {
		return SkillBonus{AttackMod: 1.3, WeightMod: 1.10, NarrativeSuffix: "【致命直塞触发】"}
	}
	return SkillBonus{}
}

func calcCutInsideExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventCloseShot && (ctx.Zone[1] == 0 || ctx.Zone[1] == 2) {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【内切杀手触发】"}
	}
	return SkillBonus{}
}

func calcPenaltyExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventPenalty {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【点球专家触发】"}
	}
	return SkillBonus{}
}

func calcReboundHunter(ctx SkillContext) SkillBonus {
	// 补射选择权重加成 -> 在 selector 中处理
	return SkillBonus{WeightMod: 1.10}
}

func calcDribbleMagician(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventDribblePast {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【花式魔术师触发】"}
	}
	return SkillBonus{}
}

// ============================================================================
// MF 类技能
// ============================================================================

func calcSurgicalPass(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventShortPass || ctx.EventType == config.EventThroughBall {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【手术刀传球触发】"}
	}
	return SkillBonus{}
}

func calcMetronome(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventShortPass && ctx.Zone[0] == 1 {
		return SkillBonus{ControlMod: 0.03, NarrativeSuffix: "【节拍器触发】"}
	}
	return SkillBonus{}
}

func calcBoxToBox(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventShortPass || ctx.EventType == config.EventThroughBall {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【全能中场触发】"}
	}
	return SkillBonus{}
}

func calcLongPassExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventLongPass {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【长传调度触发】"}
	}
	return SkillBonus{}
}

func calcInterceptExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventIntercept {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【拦截专家触发】"}
	}
	return SkillBonus{}
}

func calcPlaymaker(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventThroughBall || ctx.EventType == config.EventCross {
		return SkillBonus{WeightMod: 1.10, NarrativeSuffix: "【组织核心触发】"}
	}
	return SkillBonus{}
}

func calcSetPieceMaster(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventFreeKick || ctx.EventType == config.EventCorner {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【定位球大师触发】"}
	}
	return SkillBonus{}
}

func calcDestroyer(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventTackle {
		return SkillBonus{AttackMod: 1.3, ProbMod: 0.03, NarrativeSuffix: "【绞肉机触发】"}
	}
	return SkillBonus{}
}

// ============================================================================
// DF 类技能
// ============================================================================

func calcIronWall(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventWingBreak || ctx.EventType == config.EventCutInside {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【铁壁触发】"}
	}
	return SkillBonus{}
}

func calcTackleExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventTackle {
		return SkillBonus{AttackMod: 1.3, NarrativeSuffix: "【铲球专家触发】"}
	}
	return SkillBonus{}
}

func calcAnticipationMaster(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventIntercept {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【预判大师触发】"}
	}
	return SkillBonus{}
}

func calcMarkingExpert(ctx SkillContext) SkillBonus {
	// 人盯人时降低被盯对象接球成功率 -> 在 selector 中处理
	return SkillBonus{WeightMod: 0.95}
}

func calcAerialFortress(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventHeader || ctx.EventType == config.EventClearance {
		return SkillBonus{AttackMod: 1.3, DefenseMod: 1.3, NarrativeSuffix: "【空中堡垒触发】"}
	}
	return SkillBonus{}
}

func calcWingBarrier(ctx SkillContext) SkillBonus {
	if (ctx.EventType == config.EventWingBreak || ctx.EventType == config.EventCross) &&
		(ctx.Zone[1] == 0 || ctx.Zone[1] == 2) {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【边路屏障触发】"}
	}
	return SkillBonus{}
}

func calcSweeper(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventCoverDefense {
		return SkillBonus{DefenseMod: 1.3, ControlMod: 0.03, NarrativeSuffix: "【清道夫触发】"}
	}
	return SkillBonus{}
}

// ============================================================================
// GK 类技能
// ============================================================================

func calcDivineReflexes(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventCloseShot {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【神反应触发】"}
	}
	return SkillBonus{}
}

func calcGoalLineTech(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventClearance || ctx.EventType == config.EventKeeperSave {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【门线技术触发】"}
	}
	return SkillBonus{}
}

func calcRushOutExpert(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventOneOnOne {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【出击果断触发】"}
	}
	return SkillBonus{}
}

func calcQuickThrow(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventKeeperShortPass || ctx.EventType == config.EventKeeperThrow {
		return SkillBonus{AttackMod: 1.3, WeightMod: 1.10, NarrativeSuffix: "【手抛球反击触发】"}
	}
	return SkillBonus{}
}

func calcPenaltyKiller(ctx SkillContext) SkillBonus {
	if ctx.EventType == config.EventPenalty {
		return SkillBonus{DefenseMod: 1.3, NarrativeSuffix: "【点球克星触发】"}
	}
	return SkillBonus{}
}
