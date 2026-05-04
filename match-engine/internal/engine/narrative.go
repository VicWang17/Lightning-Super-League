package engine

import (
	"fmt"
	"math/rand/v2"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// NarrativeGenerator produces commentary text
type NarrativeGenerator struct {
	r              *rand.Rand
	lastEvent      string // tracks previous event type for chain-aware narratives
	lastContextTag string // tracks last appended context to avoid repetition
}

func NewNarrativeGenerator(seed uint64) *NarrativeGenerator {
	return &NarrativeGenerator{r: rand.New(rand.NewPCG(seed, seed+1))}
}

func (ng *NarrativeGenerator) Generate(ev domain.MatchEvent) string {
	return ng.GenerateWithContext(ev, 0, 0, [2]int{1, 1})
}

func (ng *NarrativeGenerator) GenerateWithContext(ev domain.MatchEvent, ctrl float64, momentum float64, zone [2]int) string {
	base := ng.generateBase(ev)
	ng.lastEvent = ev.Type

	appendContext := func(tag string, options []string) {
		if tag == ng.lastContextTag {
			return // skip duplicate context
		}
		ng.lastContextTag = tag
		base += ng.pick(options)
	}

	// Add momentum flavor (no empty option — always triggers when threshold is met)
	if momentum > 0.15 {
		appendContext("momentum_pos", []string{" " + ev.Team + "势头正盛！", " " + ev.Team + "完全掌控了比赛节奏！", " " + ev.Team + "士气高涨！"})
	} else if momentum < -0.15 {
		appendContext("momentum_neg", []string{" " + ev.Team + "似乎有些力不从心。", " " + ev.Team + "需要振作起来。", " " + ev.Team + "的势头被压制了。"})
	}
	// Add control flavor for key zones (lowered threshold from 0.6 to 0.4)
	if ctrl > 0.4 && zone[0] == 1 {
		appendContext("ctrl_mid", []string{" " + ev.Team + "几乎控制了中场，从容组织进攻。", " " + ev.Team + "在中场占据绝对优势。", " " + ev.Team + "已经掌控了中场的节奏。"})
	}
	if ctrl > 0.4 && zone[0] == 0 {
		appendContext("ctrl_front", []string{" " + ev.Team + "在前场形成了围攻之势！", " " + ev.Team + "的攻势如潮水般涌来！", " " + ev.Team + "已经撕开了对手的防线！"})
	}
	if ctrl < -0.2 && zone[0] == 2 && ev.Result == "success" {
		appendContext("def_gap", []string{" 防线被撕扯开了，有机会！", " 后防空虚，这是机会！", " 防守球员的站位有问题！", " 对手防线出现了漏洞！"})
	}
	// Zone-specific tactical flavor
	if zone[0] == 0 && (ev.Type == config.EventCross || ev.Type == config.EventThroughBall || ev.Type == config.EventCloseShot) {
		appendContext("zone_danger", []string{" 禁区内的机会！", " 这个位置非常危险！", " 禁区里一片混乱！"})
	}
	// Attribute-based flavor for key events
	if ev.Type == config.EventCloseShot || ev.Type == config.EventLongShot || ev.Type == config.EventOneOnOne {
		appendContext("attribute", []string{" 这样的机会必须把握住！", " 射术精湛的球员，这种球不会放过！", " 门前的嗅觉太敏锐了！"})
	}
	// Comeback / score situation flavor for goals
	if ev.Type == config.EventGoal || (ev.Result == "goal" && (ev.Type == config.EventCloseShot || ev.Type == config.EventLongShot || ev.Type == config.EventHeader)) {
		if ev.Score != nil {
			h, a := ev.Score.Home, ev.Score.Away
			if h == a && h > 0 {
				appendContext("score_equal", []string{" 比分被扳平！", " 双方回到同一起跑线！", " 局势变得紧张了！"})
			}
			if (ev.Team == "home" && h-a == 1 && a > 0) || (ev.Team == "away" && a-h == 1 && h > 0) {
				appendContext("score_overtake", []string{" 比分被反超！", " 局势逆转了！", " 他们完成了反超！"})
			}
			if (ev.Team == "home" && h-a >= 2 && a > 0) || (ev.Team == "away" && a-h >= 2 && h > 0) {
				appendContext("score_extend", []string{" 优势进一步扩大了！", " 他们已经掌控了比赛！", " 比赛悬念正在消失！"})
			}
		}
	}
	// Random crowd reactions based on score and time
	if ev.Score != nil && ev.Minute > 5.0 {
		h, a := ev.Score.Home, ev.Score.Away
		diff := h - a
		if diff < 0 {
			diff = -diff
		}
		// One-sided blowout
		if diff >= 3 {
			appendContext("crowd_blowout", []string{"", " 看台上的球迷玩起了人浪！", " 球迷们开始享受这场一边倒的比赛。", " 看台上有些球迷提前离场了。"})
		}
		// Boring match (few goals, late in game)
		if diff == 0 && h <= 1 && ev.Minute > 20.0 {
			appendContext("crowd_boring", []string{"", " 看台上的球迷有些坐不住了。", " 比赛略显沉闷，球迷们希望看到进球。"})
		}
	}
	return base
}

// shootingAngle returns a random shooting angle description
func (ng *NarrativeGenerator) shootingAngle() string {
	return ng.pick([]string{"打近角", "打远角", "推射死角", "抽射上角", "低射下角", "挑射过顶", "爆杆劲射", "巧射空门"})
}

// scoreSituation generates a description based on the current score after a goal
func (ng *NarrativeGenerator) scoreSituation(ev domain.MatchEvent) string {
	if ev.Score == nil {
		return ""
	}
	h, a := ev.Score.Home, ev.Score.Away
	var diff int
	if ev.Team == "home" {
		diff = h - a
	} else {
		diff = a - h
	}

	if h+a == 1 {
		return "打破僵局！"
	}
	if diff == 0 {
		return ng.pick([]string{"扳平比分！", "再次扳平！", "双方回到同一起跑线！"})
	}
	if diff == 1 {
		if (ev.Team == "home" && h == 1 && a == 0) || (ev.Team == "away" && a == 1 && h == 0) {
			return ng.pick([]string{"取得领先！", "率先破门！"})
		}
		return ng.pick([]string{"反超比分！", "逆转了比分！", "比分被改写！"})
	}
	if diff == 2 {
		return ng.pick([]string{"扩大领先优势！", "两球领先！", "拉开差距！"})
	}
	if diff >= 3 {
		return fmt.Sprintf("%d球领先！优势巨大！", diff)
	}
	return ""
}

// goalAnalysis returns analytical commentary about what the goal means for the match
func (ng *NarrativeGenerator) goalAnalysis(ev domain.MatchEvent) string {
	if ev.Score == nil {
		return ""
	}
	h, a := ev.Score.Home, ev.Score.Away
	var diff int
	if ev.Team == "home" {
		diff = h - a
	} else {
		diff = a - h
	}
	// Use generic phrasing or derive from score context
	late := ev.Minute > 20.0

	if h+a == 1 {
		return ng.pick([]string{"僵局终于被打破！这场比赛的沉闷气氛一扫而空。", "第一粒进球来了！比赛将变得更加开放。", "首开纪录！谁先破门谁就能占据心理优势。"})
	}
	if diff == 0 {
		return ng.pick([]string{"双方回到同一起跑线，比赛的悬念又回来了！", "扳平比分！这下压力来到了领先一方。", "比分扳平！谁能笑到最后还很难说。"})
	}
	if diff == 1 {
		if (ev.Team == "home" && h == 1 && a == 0) || (ev.Team == "away" && a == 1 && h == 0) {
			return ng.pick([]string{"取得领先，他们现在可以更有耐心地控制比赛节奏了。", "率先破门！心理优势明显。", "1-0领先，比赛的主动权握在了他们手中。"})
		}
		if late {
			return ng.pick([]string{"关键时刻反超比分！比赛进入白热化阶段。", "最后时刻的进球！胜利的天平正在倾斜。", "逆转了比分！留给对手的时间不多了。"})
		}
		return ng.pick([]string{"比分被反超，落后的一方必须尽快作出回应！", "反超比分！谁能顶住压力还很难说。", "局势逆转了！这场比赛越来越精彩。"})
	}
	if diff == 2 {
		if late {
			return ng.pick([]string{"两球领先了，这下他们稳了不少。", "领先优势扩大到两球，胜利在望！", "2球差距，对手想要逆转难度很大。"})
		}
		return ng.pick([]string{"两球领先！他们的进攻火力全开。", "拉开差距了，对手必须加快进攻节奏。", "2球优势，比赛的主动权牢牢在握。"})
	}
	if diff >= 3 {
		if late {
			return ng.pick([]string{"大比分领先，这场比赛基本失去悬念了。", "领先这么多，对手只能为荣誉而战了。", "碾压级的表现！对手毫无还手之力。"})
		}
		return ng.pick([]string{"优势巨大，比赛悬念正在消失。", "大比分领先，他们可以开始轮换休息了。", "一边倒的比赛，对手需要好好反思了。"})
	}
	return ""
}

// comebackNarrative checks if this is a comeback situation
func (ng *NarrativeGenerator) comebackNarrative(ev domain.MatchEvent) string {
	if ev.Score == nil || ev.Type != config.EventGoal {
		return ""
	}
	h, a := ev.Score.Home, ev.Score.Away
	// Detect equalizer after trailing
	if ev.Team == "home" && h == a && a > 0 {
		return ng.pick([]string{"他们扳回一球！", "连追两球！士气大振！", "他们正在上演逆转好戏！"})
	}
	if ev.Team == "away" && h == a && h > 0 {
		return ng.pick([]string{"他们扳回一球！", "连追两球！士气大振！", "他们正在上演逆转好戏！"})
	}
	return ""
}

func (ng *NarrativeGenerator) generateBase(ev domain.MatchEvent) string {
	switch ev.Type {
	case config.EventPreMatch:
		return ng.pick([]string{
			fmt.Sprintf("杰尼电视台，杰尼电视台！这里是本场比赛的直播！比赛双方是 %s 对阵 %s，比赛即将开始！", ev.Team, ev.OpponentName),
			fmt.Sprintf("各位观众晚上好！杰尼电视台为您带来这场焦点大战！%s 对阵 %s！", ev.Team, ev.OpponentName),
			fmt.Sprintf("欢迎来到杰尼电视台！今天这场比赛看点十足！%s 迎战 %s！", ev.Team, ev.OpponentName),
		})
	case config.EventKickoff:
		return ng.pick([]string{
			fmt.Sprintf("中圈开球！%s重新组织进攻。", ev.Team),
			fmt.Sprintf("比赛继续进行！%s中圈开球。", ev.Team),
			fmt.Sprintf("%s从中圈开球，发动新一轮进攻。", ev.Team),
		})
	case config.EventTurnover:
		if ev.PlayerName != "" {
			return ng.pick([]string{
				fmt.Sprintf("球权来到%s队这边，%s拿球组织。", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s队展开反击，%s带球推进！", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s夺回球权，%s迅速转入进攻！", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s队重新掌控球权，%s在前场拿球。", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s断球成功，%s准备发动攻势。", ev.Team, ev.PlayerName),
				fmt.Sprintf("球权转换！%s的%s拿球了。", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s队夺回控球权，%s在寻找传球线路。", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s抢回球权，%s开始推进！", ev.Team, ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("球权来到%s队这边。", ev.Team),
			fmt.Sprintf("%s队展开反击。", ev.Team),
			fmt.Sprintf("%s夺回球权，迅速转入进攻！", ev.Team),
			fmt.Sprintf("%s队重新掌控球权。", ev.Team),
			fmt.Sprintf("球权转换！%s拿球了。", ev.Team),
			fmt.Sprintf("%s夺回控球权，准备发动攻势。", ev.Team),
			fmt.Sprintf("%s抢回球权，开始组织进攻。", ev.Team),
			fmt.Sprintf("%s队重新拿球，寻找机会。", ev.Team),
		})
	case config.EventBackPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s在后场稳稳拿住球。", ev.PlayerName),
				fmt.Sprintf("%s在后场控球观察局势。", ev.PlayerName),
				fmt.Sprintf("%s在后场护球，寻找出球线路。", ev.PlayerName),
				fmt.Sprintf("%s在后场拿球，队友正在跑位。", ev.PlayerName),
				fmt.Sprintf("%s在后场控制住皮球。", ev.PlayerName),
				fmt.Sprintf("%s在后场观察，等待队友接应。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s出人意料地送出一记向后的直传给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的传球角度刁钻，%s在后场稳稳拿住球。", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s大胆向后直塞，%s接球！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的向后传球找到%s，很有创意！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图送出刁钻的向后直传，但被%s识破拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险回传被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的向后传球被%s预判断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的回传意图被%s看穿！", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s的回传出现失误，被%s断球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在后场的传球被%s拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s回传力量太大，被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传球被%s识破，球权易手！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s在后场控球，稳稳地把球交给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s面对逼抢，冷静分球给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s在后场做着传导。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在后场耐心倒脚，将球传给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在后场护球，把球分给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s在后场做着安全的传递。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s观察后，将球回给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在后场拿球，选择传给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s从容地把球交给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在后场调度，把球传给%s。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventMidPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s在中场拿球观察。", ev.PlayerName),
				fmt.Sprintf("%s在中场控球寻找机会。", ev.PlayerName),
				fmt.Sprintf("%s在中场护球，等待队友跑位。", ev.PlayerName),
				fmt.Sprintf("%s在中场拿球，寻找出球线路。", ev.PlayerName),
				fmt.Sprintf("%s在中场控制住皮球。", ev.PlayerName),
				fmt.Sprintf("%s在中场观察局势。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s在中场送出一脚手术刀般的传球，%s接球转身！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的直塞穿透了中场防线，%s高速插上！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s送出精准直传，%s接球后转身推进！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的传球撕开了中场防线，%s拿到球了！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图直塞穿透防线，被%s精准预判拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险传球被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的直传被%s识破！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传球意图被%s看穿，球被断下！", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s在中场的传球被%s断下。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的分球出现失误，球权易手。", ev.PlayerName),
				fmt.Sprintf("%s的传球被%s拦截！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在中场丢球了！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s在中场控球，不断观察寻找传球线路。", ev.PlayerName),
			fmt.Sprintf("中场核心%s把球分给了%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s在中场进行着耐心的传递。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在中场拿球，分给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在中场从容调度，把球交给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s在中场做着传导。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s观察后选择传给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在中场护球，把球分给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在中场寻找空当，传给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s从容分球给%s。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventShortPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s在原地控球寻找队友。", ev.PlayerName),
				fmt.Sprintf("%s护住球等待支援。", ev.PlayerName),
				fmt.Sprintf("%s在原地控球观察。", ev.PlayerName),
				fmt.Sprintf("%s护球等待队友跑位。", ev.PlayerName),
				fmt.Sprintf("%s拿球在原地寻找机会。", ev.PlayerName),
				fmt.Sprintf("%s控制住皮球，等待支援。", ev.PlayerName),
			})
		}
		if ev.Detail == "flick_on" {
			return ng.pick([]string{
				fmt.Sprintf("%s轻轻一碰把球摆渡给%s！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s巧妙地一蹭，球来到%s脚下！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s头球后蹭，%s跟上接球！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s顺势一拨，球传给插上的%s！", ev.PlayerName, ev.Player2Name),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s送出一脚穿透性短传给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s在狭小空间里和%s完成了一脚精妙的短传配合！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的短传撕开了防线，%s接球！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s和%s在狭小空间里完成配合！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图送出穿透性短传，被%s贴身拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险短传被%s识破，球权丢失。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的短传被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传球被%s贴身拦截！", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s的短传被%s抢断。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传球出现失误，球落到对方脚下。", ev.PlayerName),
				fmt.Sprintf("%s的传球被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s传球失误，球权易手。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s选择了一个安全的短传，交给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("面对逼抢，%s冷静地把球回给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s做了一次简单的倒脚配合。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s一脚短传找到%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s与%s打出撞墙配合。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s做了脚短传配合。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s短传给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在原地把球传给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s进行了短传配合。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s分球给%s。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventLongPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s观察后选择长传转移。", ev.PlayerName),
				fmt.Sprintf("%s大脚调度寻找空当。", ev.PlayerName),
				fmt.Sprintf("%s选择长传转移。", ev.PlayerName),
				fmt.Sprintf("%s大脚寻找前场队友。", ev.PlayerName),
				fmt.Sprintf("%s观察后大脚长传。", ev.PlayerName),
				fmt.Sprintf("%s选择大范围转移。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s一脚大范围转移，%s在边路接球！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的精准长传找到了%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s长传调度，%s在边路拿球！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s大范围转移，精准找到%s！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的大范围转移被%s头球解围。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险长传飞出边线，球权易手。", ev.PlayerName),
				fmt.Sprintf("%s的长传被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的转移球被%s拦截。", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s的长传被%s预判解围。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的大脚长传落点不佳，被对方拿到。", ev.PlayerName),
				fmt.Sprintf("%s的长传被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s长传失误，球权易手。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s一记长传，试图把球直接送到前场找到%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s大脚长传调度，寻找前场的%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s试图用长传找到%s，撕开防线。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s大脚长传，寻找%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s长传转移，找前场的%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s大脚找到%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s长传寻找%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s大范围转移，%s在前场接应。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s长传找%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s大脚转移，%s准备接球。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventWingBreak:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s在边路带球突破，晃过了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("边路1v1！%s用速度强吃了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s一个漂亮的假动作，完全晃开了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在边路生吃%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s用速度突破了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在边路晃过%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s用假动作骗过了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在边路展现了惊人的爆发力，过掉了%s！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s试图突破%s，但被拦截了下来。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的过人尝试被%s识破了。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventCutInside:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s从边路内切，向禁区方向带球！", ev.PlayerName),
				fmt.Sprintf("%s标志性的内切！晃过边后卫朝球门杀去！", ev.PlayerName),
				fmt.Sprintf("%s内切了！朝球门杀去！", ev.PlayerName),
				fmt.Sprintf("%s从边路切进来了！", ev.PlayerName),
				fmt.Sprintf("%s标志性的内切！", ev.PlayerName),
				fmt.Sprintf("%s晃过边后卫内切！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s内切被%s卡住身位，球丢了。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventDribblePast:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s一个漂亮的盘带，过掉了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s展示出色脚下技术，晃过了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s带球推进，%s没能拦下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的过人了得！晃过了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s用脚下技术戏耍了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s漂亮的过人！%s被甩在身后！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s带球突破，%s拦不住！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s展现了惊人的盘带能力，过掉了%s！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s试图盘带过人，被%s断了下来。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的过人尝试被%s干净地拦截了。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventThroughBall:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s试图送出一脚直塞。", ev.PlayerName),
				fmt.Sprintf("%s寻找直传机会。", ev.PlayerName),
				fmt.Sprintf("%s在寻找直塞的机会。", ev.PlayerName),
				fmt.Sprintf("%s准备送出直传。", ev.PlayerName),
				fmt.Sprintf("%s在观察防线身后的空当。", ev.PlayerName),
			})
		}
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s送出一脚直塞球，试图找到前方的%s！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("手术刀般的直塞！%s的传球撕开了防线，%s单刀了！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s的直塞球撕开了防线！%s单刀了！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s精准直塞！%s获得单刀机会！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s的传球像手术刀一样精准！%s单刀了！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s一脚直塞找到%s！防线被撕开了！", ev.PlayerName, ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s试图直塞，但被%s预判拦截。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventCross:
		if ev.Result == "success" {
			// Chain-aware: if previous event was a wing break, add衔接
			if ng.lastEvent == config.EventWingBreak {
				return ng.pick([]string{
					fmt.Sprintf("突破后%s起脚传中！球飞向禁区！", ev.PlayerName),
					fmt.Sprintf("%s在突破后果断传中，球飞向禁区！", ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s起脚传中！球飞向禁区！", ev.PlayerName),
				fmt.Sprintf("%s在边路送出精准传中！", ev.PlayerName),
				fmt.Sprintf("%s传中！禁区内一片混乱！", ev.PlayerName),
				fmt.Sprintf("%s在边路起球传中！", ev.PlayerName),
				fmt.Sprintf("%s传中到禁区！前锋在等着！", ev.PlayerName),
				fmt.Sprintf("%s在底线附近送出传中！", ev.PlayerName),
				fmt.Sprintf("%s起球到禁区！", ev.PlayerName),
				fmt.Sprintf("%s在边路传中，球划出一道弧线！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s传中，被%s头球解围。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的传中被%s拦截。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventHeader:
		if ev.Result == "goal" {
			scoreStr := ""
			if ev.Score != nil {
				scoreStr = fmt.Sprintf("%d-%d！", ev.Score.Home, ev.Score.Away)
			}
			situation := ng.scoreSituation(ev)
			return ng.pick([]string{
				fmt.Sprintf("%s%s力压后卫头球攻门——球进了！！！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s头球！%s甩头攻门，球应声入网！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s高高跃起，一记势大力沉的头球破门！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s泰山压顶！头球砸进球门！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s狮子甩头！皮球应声入网！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s在人群中杀出，一记精准头球！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s力压防守球员，头球破门！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s鱼跃冲顶！球进了！%s", scoreStr, ev.PlayerName, situation),
			})
		}
		if ev.Result == "saved" {
			return fmt.Sprintf("%s头球攻门！门将%s做出精彩扑救！", ev.PlayerName, ev.OpponentName)
		}
		if ev.Result == "success" {
			// Chain-aware: if previous event was a cross or corner
			if ng.lastEvent == config.EventCross || ng.lastEvent == config.EventCorner {
				// Avoid "header to goalkeeper" which looks weird
				if ev.Player2Name != "" && len(ev.Player2Name) >= 2 && ev.Player2Name[len(ev.Player2Name)-2:] == "GK" {
					return ng.pick([]string{
						fmt.Sprintf("%s抢点成功，头球后蹭解围！", ev.PlayerName),
						fmt.Sprintf("%s高高跃起头球争顶，把球顶出危险区域！", ev.PlayerName),
					})
				}
				return ng.pick([]string{
					fmt.Sprintf("%s抢点成功，头球把球摆渡给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s高高跃起头球争顶，把球顶给插上的%s！", ev.PlayerName, ev.Player2Name),
				})
			}
			if ev.Player2Name != "" && len(ev.Player2Name) >= 2 && ev.Player2Name[len(ev.Player2Name)-2:] == "GK" {
				return fmt.Sprintf("%s头球争顶成功，把球顶出危险区域。", ev.PlayerName)
			}
			return fmt.Sprintf("%s头球争顶成功，把球摆渡给%s。", ev.PlayerName, ev.Player2Name)
		}
		return fmt.Sprintf("%s争顶失败，%s控制住了球权。", ev.PlayerName, ev.OpponentName)
	case config.EventShotWindup:
		return ng.pick([]string{
			fmt.Sprintf("%s起脚打门——！", ev.PlayerName),
			fmt.Sprintf("%s抡起右脚，一脚劲射！", ev.PlayerName),
			fmt.Sprintf("%s调整步点，直接射门！", ev.PlayerName),
			fmt.Sprintf("%s抓住机会，果断起脚！", ev.PlayerName),
			fmt.Sprintf("%s射门！", ev.PlayerName),
			fmt.Sprintf("%s一脚怒射！", ev.PlayerName),
			fmt.Sprintf("%s起脚了！", ev.PlayerName),
			fmt.Sprintf("%s拔脚射门！", ev.PlayerName),
			fmt.Sprintf("%s打门！", ev.PlayerName),
			fmt.Sprintf("%s起脚射门！", ev.PlayerName),
		})
	case config.EventCloseShot:
		if ev.Result == "goal" {
			scoreStr := ""
			if ev.Score != nil {
				scoreStr = fmt.Sprintf("%d-%d！", ev.Score.Home, ev.Score.Away)
			}
			situation := ng.scoreSituation(ev)
			angle := ng.shootingAngle()
			return ng.pick([]string{
				fmt.Sprintf("球进了！！！%s%s的射门%s洞穿网窝！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("进了！%s%s冷静%s破门！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("应声入网！%s%s%s让门将毫无反应！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("%s%s%s得手！比分改写！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("%s%s在禁区内%s，球进了！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("%s%s抓住机会%s！球应声入网！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("死角！%s%s%s，门将鞭长莫及！%s", scoreStr, ev.PlayerName, angle, situation),
				fmt.Sprintf("%s%s一记精准的%s，球进了！！！%s", scoreStr, ev.PlayerName, angle, situation),
			})
		}
		if ev.Result == "saved" {
			return ng.pick([]string{
				fmt.Sprintf("被%s扑出！太精彩了！", ev.OpponentName),
				fmt.Sprintf("%s神勇扑救！皮球被挡了出去！", ev.OpponentName),
				fmt.Sprintf("%s做出了精彩扑救！", ev.OpponentName),
				fmt.Sprintf("%s飞身扑救！球被挡出！", ev.OpponentName),
				fmt.Sprintf("%s反应神速！把球扑了出去！", ev.OpponentName),
				fmt.Sprintf("%s倒地扑救！化解了这次射门！", ev.OpponentName),
				fmt.Sprintf("%s用身体挡出了射门！", ev.OpponentName),
				fmt.Sprintf("%s表现出色！把球扑出底线！", ev.OpponentName),
			})
		}
		if ev.Result == "blocked" {
			return ng.pick([]string{
				fmt.Sprintf("被%s封堵了出去！", ev.OpponentName),
				fmt.Sprintf("%s奋不顾身地用身体挡住了射门！", ev.OpponentName),
				fmt.Sprintf("%s用身体挡住了射门！", ev.OpponentName),
				fmt.Sprintf("%s封堵了这次射门！", ev.OpponentName),
				fmt.Sprintf("%s挡出了射门！", ev.OpponentName),
				fmt.Sprintf("%s在门线上把球挡了出去！", ev.OpponentName),
			})
		}
		if ev.Result == "woodwork" {
			return ng.pick([]string{
				fmt.Sprintf("击中门框弹出！差之毫厘！"),
				fmt.Sprintf("哐当一声！皮球砸在立柱上弹了出来！"),
				fmt.Sprintf("击中门柱弹出！太可惜了！"),
				fmt.Sprintf("横梁拒绝了这次射门！"),
				fmt.Sprintf("立柱！皮球砸在柱子上弹出！"),
				fmt.Sprintf("门框拒绝了进球！差一点点！"),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("偏出了立柱..."),
			fmt.Sprintf("高出了横梁！"),
		})
	case config.EventLongShot:
		if ev.Result == "goal" {
			scoreStr := ""
			if ev.Score != nil {
				scoreStr = fmt.Sprintf("%d-%d！", ev.Score.Home, ev.Score.Away)
			}
			situation := ng.scoreSituation(ev)
			return ng.pick([]string{
				fmt.Sprintf("世界波！！！%s皮球直挂死角！%s！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("进了！！！%s%s这脚远射简直不可思议！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s禁区外突施冷箭，世界波！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s一脚石破天惊的远射！球进了！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s拔脚怒射！皮球像炮弹一样飞入网窝！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s的远射划出美妙弧线，直挂死角！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("不可思议的进球！%s%s的远射让全场沸腾！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s重炮轰门！门将只能望球兴叹！%s", scoreStr, ev.PlayerName, situation),
			})
		}
		if ev.Result == "saved" {
			return ng.pick([]string{
				fmt.Sprintf("%s飞身将球托出横梁！", ev.OpponentName),
				fmt.Sprintf("%s一个侧扑，把球挡了出去！", ev.OpponentName),
				fmt.Sprintf("%s飞身扑救！把球托出横梁！", ev.OpponentName),
				fmt.Sprintf("%s侧身扑救！化解了这次远射！", ev.OpponentName),
				fmt.Sprintf("%s腾空而起！把球扑出！", ev.OpponentName),
				fmt.Sprintf("%s做出了世界级的扑救！", ev.OpponentName),
			})
		}
		if ev.Result == "woodwork" {
			return ng.pick([]string{
				fmt.Sprintf("击中横梁弹出！太可惜了！"),
				fmt.Sprintf("哐！皮球狠狠砸在立柱上！"),
				fmt.Sprintf("远射击中横梁弹出！"),
				fmt.Sprintf("远射砸在立柱上！差一点点！"),
				fmt.Sprintf("门框再次拒绝了进球！"),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("远射高出横梁..."),
			fmt.Sprintf("这脚放了高射炮。"),
		})
	case config.EventTackle:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s干净利落地铲断了%s的带球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s上抢成功，从%s脚下断球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s精准放铲，断下%s的球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s一个漂亮的铲抢，从%s脚下夺得球权！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s铲球失败，%s继续推进。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的铲抢没有碰到球，%s轻松摆脱。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventIntercept:
			return ng.pick([]string{
				fmt.Sprintf("%s预判准确，拦截了对方的传球。", ev.PlayerName),
				fmt.Sprintf("%s机警地断下传球路线！", ev.PlayerName),
				fmt.Sprintf("%s抢先一步，将传球拦截下来。", ev.PlayerName),
				fmt.Sprintf("%s阅读比赛出色，成功拦截！", ev.PlayerName),
				fmt.Sprintf("%s精准预判，断下传球！", ev.PlayerName),
				fmt.Sprintf("%s拦截成功！", ev.PlayerName),
				fmt.Sprintf("%s识破了传球意图，断球成功！", ev.PlayerName),
				fmt.Sprintf("%s机警地拦截了传球！", ev.PlayerName),
				fmt.Sprintf("%s的预判太准确了！成功断球！", ev.PlayerName),
				fmt.Sprintf("%s抢在对方之前断下传球！", ev.PlayerName),
			})
	case config.EventClearance:
		return ng.pick([]string{
			fmt.Sprintf("%s大脚解围，化解了险情。", ev.PlayerName),
			fmt.Sprintf("%s把球踢出危险区域！", ev.PlayerName),
			fmt.Sprintf("%s头球解围！化解了险情！", ev.PlayerName),
			fmt.Sprintf("%s把球解围出底线！", ev.PlayerName),
			fmt.Sprintf("%s大脚把球开出禁区！", ev.PlayerName),
			fmt.Sprintf("%s在门线上把球解围出去！", ev.PlayerName),
			fmt.Sprintf("%s关键解围！化解了这次危机！", ev.PlayerName),
			fmt.Sprintf("%s把球顶出危险区域！", ev.PlayerName),
			fmt.Sprintf("%s在混战中把球解围！", ev.PlayerName),
			fmt.Sprintf("%s一脚解围，化解了险情！", ev.PlayerName),
		})
	case config.EventGoal:
		scoreStr := ""
		if ev.Score != nil {
			scoreStr = fmt.Sprintf("%d-%d！", ev.Score.Home, ev.Score.Away)
		}
		analysis := ng.goalAnalysis(ev)
		return ng.pick([]string{
			fmt.Sprintf("%s%s", scoreStr, analysis),
			fmt.Sprintf("%s进球了！%s", scoreStr, analysis),
			fmt.Sprintf("%s球进了！%s", scoreStr, analysis),
			fmt.Sprintf("%s比分改写！%s", scoreStr, analysis),
		})
	case config.EventGoalCelebration:
		return ng.pick([]string{
			fmt.Sprintf("%s冲向角旗杆庆祝！队友们纷纷围了上来！", ev.PlayerName),
			fmt.Sprintf("%s张开双臂接受球迷的欢呼！", ev.PlayerName),
			fmt.Sprintf("%s滑跪庆祝！全场球迷疯狂呐喊！", ev.PlayerName),
			fmt.Sprintf("%s和队友们拥抱在一起！这是属于他们的时刻！", ev.PlayerName),
			fmt.Sprintf("%s指天庆祝！这个进球意义重大！", ev.PlayerName),
			fmt.Sprintf("看台上彩带飞舞！%s的庆祝激情四溢！", ev.PlayerName),
			fmt.Sprintf("%s脱衣庆祝！被裁判出示黄牌也无所谓！", ev.PlayerName),
			fmt.Sprintf("%s跑向看台和球迷互动！全场气氛达到顶点！", ev.PlayerName),
			fmt.Sprintf("%s做出标志性庆祝动作！球迷疯狂模仿！", ev.PlayerName),
			fmt.Sprintf("%s和替补席的队友们击掌相庆！团队的胜利！", ev.PlayerName),
			fmt.Sprintf("%s双膝跪地，双手指天！感恩的庆祝！", ev.PlayerName),
			fmt.Sprintf("%s被队友们压在身下！欢乐的叠罗汉！", ev.PlayerName),
		})
	case config.EventOwnGoal:
		return ng.pick([]string{
			fmt.Sprintf("😱 乌龙球！%s不慎将球碰入自家大门！", ev.PlayerName),
			fmt.Sprintf("😱 太不幸了！%s自摆乌龙！", ev.PlayerName),
		})
	case config.EventKeeperSave:
		// Keeper save is narrated within the shot event; skip redundant text
		return ""
	case config.EventKeeperClaim:
		// Keeper claim is implied by the shot result; skip redundant text
		return ""
	case config.EventCorner:
		return ng.pick([]string{
			fmt.Sprintf("球出了底线，%s获得角球机会。", ev.Team),
			fmt.Sprintf("%s赢得一个角球！", ev.Team),
			fmt.Sprintf("皮球出了底线，裁判判罚角球，%s来主罚。", ev.Team),
			fmt.Sprintf("%s获得角球机会，准备进攻。", ev.Team),
			fmt.Sprintf("角球！%s准备在角球区开球。", ev.Team),
			fmt.Sprintf("%s的传中造成角球，获得一次定位球机会。", ev.Team),
			fmt.Sprintf("球被碰出底线，%s获得角球。", ev.Team),
			fmt.Sprintf("%s赢得角球，禁区内双方球员正在卡位。", ev.Team),
			fmt.Sprintf("裁判指向角球区！%s获得一次绝佳的进攻机会。", ev.Team),
			fmt.Sprintf("底线附近的混战，球最终被碰出界，%s的角球。", ev.Team),
			fmt.Sprintf("看台上一片欢呼，%s又拿到一个角球。", ev.Team),
			fmt.Sprintf("角球！%s的球迷开始高声呐喊。", ev.Team),
			fmt.Sprintf("裁判鸣哨，%s准备主罚这个战术角球。", ev.Team),
			fmt.Sprintf("%s获得角球，后卫们高举双手提醒队友注意防守。", ev.Team),
			fmt.Sprintf("球从底线滚出，%s获得角球，这是破门的好机会。", ev.Team),
		})
	case config.EventFoul:
		isBox := ev.Zone == "[0,1]"
		if ev.Result == "no_call" {
			if isBox {
				return ng.pick([]string{
					fmt.Sprintf("%s禁区内倒地，裁判认为没有犯规。", ev.OpponentName),
					fmt.Sprintf("%s在禁区内疑似被%s放倒，裁判示意比赛继续。", ev.OpponentName, ev.PlayerName),
					fmt.Sprintf("%s在禁区内倒地，但裁判没有表示。", ev.OpponentName),
					fmt.Sprintf("%s疑似被%s侵犯，裁判示意比赛继续。", ev.OpponentName, ev.PlayerName),
					fmt.Sprintf("%s向裁判摊手抗议，但裁判摇摇头表示没有犯规。", ev.OpponentName),
					fmt.Sprintf("%s躺在禁区内举手示意，裁判不予理会。", ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s摔倒了，但裁判没有吹！", ev.OpponentName),
				fmt.Sprintf("%s疑似被%s侵犯，裁判示意比赛继续。", ev.OpponentName, ev.PlayerName),
				fmt.Sprintf("%s向裁判投诉，主裁判示意比赛继续进行。", ev.OpponentName),
				fmt.Sprintf("%s倒地后不满地捶了一下草皮，裁判没有表示。", ev.OpponentName),
				fmt.Sprintf("场边%s的教练冲向第四官员大声抗议。", ev.Team),
			})
		}
		if ev.Result == "yellow" {
			if isBox {
				return ng.pick([]string{
					fmt.Sprintf("禁区内犯规！%s对%s凶狠犯规，吃到黄牌！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s在禁区内拉倒%s，裁判出示黄牌并指向点球点！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s在禁区内对%s犯规！黄牌+点球！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s放倒%s，裁判出示黄牌并判罚点球！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s无奈地摊开双手，裁判坚持黄牌+点球的判罚。", ev.PlayerName),
					fmt.Sprintf("%s的队友围上来向裁判求情，但黄牌已经掏出。", ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s对%s凶狠犯规！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s拉倒了%s，这是一个明显的犯规！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s从背后铲倒%s，裁判果断出示黄牌！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s战术犯规阻止%s突破，吃到黄牌。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("裁判向%s出示黄牌！%s一脸无辜地向裁判解释。", ev.PlayerName, ev.PlayerName),
				fmt.Sprintf("%s凶狠放铲，裁判掏牌警告！", ev.PlayerName),
				fmt.Sprintf("%s对%s的犯规引发双方球员口角，裁判出示黄牌平息事态。", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "red" {
			if isBox {
				return ng.pick([]string{
					fmt.Sprintf("%s在禁区内严重犯规！红牌罚下并判罚点球！", ev.PlayerName),
					fmt.Sprintf("禁区内恶劣犯规！%s放倒%s，直接红牌！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s被红牌罚下！还判了点球！", ev.PlayerName),
					fmt.Sprintf("%s的恶劣犯规！红牌+点球！", ev.PlayerName),
					fmt.Sprintf("%s跪在草皮上双手抱头，队友们纷纷上前理论。", ev.PlayerName),
					fmt.Sprintf("裁判掏出红牌！%s瘫坐在地上，仿佛不敢相信。", ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s对%s严重犯规！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s凶狠地放倒了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("裁判直接掏出红牌！%s被驱逐出场！", ev.PlayerName),
				fmt.Sprintf("%s的飞铲亮出鞋底，红牌毫无疑问！", ev.PlayerName),
				fmt.Sprintf("%s冲向裁判大声抗议，队友赶紧把他拉开。", ev.PlayerName),
				fmt.Sprintf("%s双手抱头跪地，裁判不为所动，红牌！", ev.PlayerName),
				fmt.Sprintf("主裁判毫不犹豫地出示红牌，%s低着头走向更衣室。", ev.PlayerName),
			})
		}
		// No card, but foul called
		if isBox {
			return ng.pick([]string{
				fmt.Sprintf("禁区内犯规！%s对%s犯规，裁判指向点球点！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在禁区内放倒%s，点球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s拉倒%s，裁判果断判罚点球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的防守动作过大，裁判鸣哨指向点球点！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s对%s犯规了！裁判判罚任意球！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s拉倒了%s，裁判鸣哨，任意球！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s对%s凶狠犯规！裁判指向犯规地点，任意球！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s战术犯规拉倒%s，裁判吹停比赛。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s背后放铲，裁判赶紧吹哨制止冲突。", ev.PlayerName),
			fmt.Sprintf("%s愤怒地向裁判投诉，但犯规判罚不会改变。", ev.PlayerName),
			fmt.Sprintf("%s从侧后方绊倒%s，裁判判罚任意球。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("双方球员围向裁判理论，%s的犯规很明确。", ev.PlayerName),
		})
	case config.EventFreeKick:
		switch ev.Detail {
		case "penalty":
			if ev.Result == "goal" {
				scoreStr := ""
				if ev.Score != nil {
					scoreStr = fmt.Sprintf("%d-%d！", ev.Score.Home, ev.Score.Away)
				}
				situation := ng.scoreSituation(ev)
				return ng.pick([]string{
					fmt.Sprintf("%s点球破门！%s冷静推射，门将判断错了方向！%s", scoreStr, ev.PlayerName, situation),
					fmt.Sprintf("%s%s稳稳命中点球！%s", scoreStr, ev.PlayerName, situation),
					fmt.Sprintf("%s%s罚进点球！一蹴而就！%s", scoreStr, ev.PlayerName, situation),
					fmt.Sprintf("%s%s点球命中！门将扑错了方向！%s", scoreStr, ev.PlayerName, situation),
					fmt.Sprintf("%s%s点球罚进！冷静得让人害怕！%s", scoreStr, ev.PlayerName, situation),
					fmt.Sprintf("%s%s助跑后一记劲射，门将鞭长莫及！%s", scoreStr, ev.PlayerName, situation),
					fmt.Sprintf("%s%s骗过门将，轻松推射入网！%s", scoreStr, ev.PlayerName, situation),
				})
			}
			if ev.Result == "saved" {
				return ng.pick([]string{
					fmt.Sprintf("点球被扑出！%s的射门被门将%s神勇化解！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的点球被%s扑出！太可惜了！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的点球被%s判断对了方向，神扑！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的点球力量太正，%s稳稳抱住！", ev.PlayerName, ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("点球罚丢了！%s的射门偏出了球门！", ev.PlayerName),
				fmt.Sprintf("%s的点球打飞了！", ev.PlayerName),
				fmt.Sprintf("%s的点球击中立柱弹出！运气太差了！", ev.PlayerName),
				fmt.Sprintf("%s助跑后一脚踢飞，全场一片叹息。", ev.PlayerName),
			})
		case "cross":
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出精准任意球传中，球飞向禁区！", ev.PlayerName),
					fmt.Sprintf("%s的任意球传中划出一道美妙弧线！", ev.PlayerName),
					fmt.Sprintf("%s的传中越过人墙，禁区内一片混战！", ev.PlayerName),
					fmt.Sprintf("皮球在空中划出弧线，%s的任意球传中找到了禁区内的队友！", ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球传中被%s解围。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传中任意球被%s顶出危险区域。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传中被%s抢先一步头球顶出。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传中意图太明显，被%s轻松拦截。", ev.PlayerName, ev.OpponentName),
			})
		case "shot":
			if ev.Result == "goal" {
				return ng.pick([]string{
					fmt.Sprintf("世界波！%s的直接任意球直挂死角！", ev.PlayerName),
					fmt.Sprintf("任意球大师！%s一脚精准制导破门得分！", ev.PlayerName),
					fmt.Sprintf("%s的任意球绕过人墙直挂死角！门将毫无反应！", ev.PlayerName),
					fmt.Sprintf("皮球像长了眼睛一样钻入球门！%s的任意球绝技！", ev.PlayerName),
					fmt.Sprintf("%s助跑后起脚，皮球越过人墙下坠入网！", ev.PlayerName),
				})
			}
			if ev.Result == "saved" {
				return ng.pick([]string{
					fmt.Sprintf("%s的任意球角度刁钻，可惜被%s扑出！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的任意球绕过人墙，被%s奋力挡出！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的任意球势大力沉，%s单掌托出横梁！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的落叶球被%s飞身扑出，精彩的对决！", ev.PlayerName, ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球打在了人墙上！", ev.PlayerName),
				fmt.Sprintf("%s的任意球力量过大，偏出了球门！", ev.PlayerName),
				fmt.Sprintf("%s的任意球被人墙中的%s用身体挡出。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的射门打在人墙上弹出，错失良机。", ev.PlayerName),
			})
		case "long_pass":
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出任意球长传，%s接球后展开进攻！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s大脚开出任意球，%s在边路控制球权。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球长传被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的长传意图被%s识破，球权易手。", ev.PlayerName, ev.OpponentName),
			})
		default: // short pass
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出任意球短传，%s接球组织。", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s轻轻一拨，%s跟上接球重新组织。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球短传被%s断下！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的短传配合出现失误，%s抢断成功。", ev.PlayerName, ev.OpponentName),
			})
		}
	case config.EventYellowCard:
		return ng.pick([]string{
			fmt.Sprintf("裁判向%s出示黄牌！", ev.PlayerName),
			fmt.Sprintf("主裁判掏出了黄牌，%s被警告。", ev.PlayerName),
			fmt.Sprintf("黄牌！%s的犯规动作过大，裁判出示黄牌警告。", ev.PlayerName),
			fmt.Sprintf("%s向裁判摊手解释，但黄牌已经掏出来了。", ev.PlayerName),
			fmt.Sprintf("%s一脸不满，嘴里嘟囔着走向一边。", ev.PlayerName),
			fmt.Sprintf("裁判对%s出示黄牌，双方球员围上来理论。", ev.PlayerName),
			fmt.Sprintf("%s的队友赶紧把他拉开，避免事态升级。", ev.PlayerName),
			fmt.Sprintf("%s双手叉腰站在原地，显然对判罚很不服气。", ev.PlayerName),
		})
	case config.EventRedCard:
		return ng.pick([]string{
			fmt.Sprintf("红牌！%s被直接罚下！", ev.PlayerName),
			fmt.Sprintf("主裁判出示红牌，%s被罚出场！", ev.PlayerName),
			fmt.Sprintf("%s冲向裁判大声抗议，队友赶紧把他推开。", ev.PlayerName),
			fmt.Sprintf("%s跪在草皮上双手抱头，不敢相信这个判罚。", ev.PlayerName),
			fmt.Sprintf("%s低着头走向球员通道，全场球迷一片哗然。", ev.PlayerName),
			fmt.Sprintf("%s愤怒地摘下队长袖标摔在地上，红牌！", ev.PlayerName),
			fmt.Sprintf("场边%s的教练激动地和第四官员理论。", ev.Team),
			fmt.Sprintf("%s的队友们围着裁判求情，但红牌无法改变。", ev.PlayerName),
		})
	case config.EventOffside:
		return ng.pick([]string{
			fmt.Sprintf("越位！%s的跑位早了半步。", ev.PlayerName),
			fmt.Sprintf("边旗举起！%s越位了。", ev.PlayerName),
		})
	case config.EventSubstitution:
		return ng.pick([]string{
			fmt.Sprintf("换人调整！%s下场，%s替补登场。", ev.Player2Name, ev.PlayerName),
			fmt.Sprintf("%s被换下，%s登场，教练做出战术调整。", ev.Player2Name, ev.PlayerName),
			fmt.Sprintf("场边第四官员举牌，%s下场，%s替补上阵。", ev.Player2Name, ev.PlayerName),
			fmt.Sprintf("%s步履蹒跚地走下场，%s热身完毕登场。", ev.Player2Name, ev.PlayerName),
			fmt.Sprintf("%s和%s完成换人交接，掌声送给下场的%s。", ev.Player2Name, ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("教练对阵容进行调整，%s下场，%s登场加强进攻。", ev.Player2Name, ev.PlayerName),
			fmt.Sprintf("%s体能耗尽被换下，%s登场为球队注入新鲜血液。", ev.Player2Name, ev.PlayerName),
			fmt.Sprintf("场边球迷为下场的%s鼓掌，%s替补登场。", ev.Player2Name, ev.PlayerName),
		})
	case config.EventHalftime:
		return fmt.Sprintf("上半场结束！比分 %d-%d", ev.Score.Home, ev.Score.Away)
	case config.EventFulltime:
		return fmt.Sprintf("全场比赛结束！最终比分 %d-%d", ev.Score.Home, ev.Score.Away)
	case config.EventAddedTime:
		return fmt.Sprintf("第四官员举牌示意，下半场伤停补时 %.0f 分钟！", ev.ExtraValue)

	// ===== Phase 1: Simple 1v1 events =====
	case config.EventSwitchPlay:
		if ev.Result == "success" {
			if ev.Player2Name != "" {
				return ng.pick([]string{
					fmt.Sprintf("%s一记大范围横传，把球转移到另一侧交给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("左右路调度！%s大范围转移找到%s。", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s观察了一下，选择把球横向转移给%s。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s一记大范围横传，把球转移到另一侧！", ev.PlayerName),
				fmt.Sprintf("左右路调度！%s大范围转移找队友。", ev.PlayerName),
				fmt.Sprintf("%s观察了一下，选择把球横向转移。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的横传被%s拦截下来。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s试图大范围转移，被%s断下。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventLobPass:
		if ev.Result == "success" {
			if ev.Player2Name != "" {
				return ng.pick([]string{
					fmt.Sprintf("%s送出一脚挑传，球越过防线飞向禁区，%s高速插上！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("漂亮的挑传！%s的传球越过防守球员头顶，%s准备争顶！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s送出一脚挑传，球越过防线飞向禁区！", ev.PlayerName),
				fmt.Sprintf("漂亮的挑传！%s的传球越过防守球员头顶！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的挑传被%s头球解围。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s试图挑传身后，被%s预判拦截。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventPassOverTop:
		if ev.Result == "success" {
			if ev.Player2Name != "" {
				return ng.pick([]string{
					fmt.Sprintf("%s一脚过顶球，皮球越过防线，%s高速插上！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的直长传越过防守，%s甩开防线单刀了！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s一脚过顶球，皮球越过防线！", ev.PlayerName),
				fmt.Sprintf("%s的直长传越过防守，队友高速插上！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的过顶球被%s头球顶下。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s试图长传打身后，被%s解围。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventBlockPass:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s提前预判传球路线，成功断球！", ev.PlayerName),
				fmt.Sprintf("%s封堵了传球线路，从%s脚下断球！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s试图封堵传球，但%s还是把球传出去了。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s预判失误，%s的传球穿了过去。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventOneOnOne:
		if ev.Result == "goal" {
			scoreStr := ""
			if ev.Score != nil {
				scoreStr = fmt.Sprintf("%d-%d！", ev.Score.Home, ev.Score.Away)
			}
			situation := ng.scoreSituation(ev)
			return ng.pick([]string{
				fmt.Sprintf("%s单刀！%s冷静推射破门！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s晃过门将，轻松推射入网！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s单刀赴会，冷静施射得手！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s面对门将，一个假动作后推射空门！%s", scoreStr, ev.PlayerName, situation),
				fmt.Sprintf("%s%s单刀球进了！完美的个人表演！%s", scoreStr, ev.PlayerName, situation),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("单刀机会！%s的射门被%s扑出！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s面对%s一脚射门，可惜被扑出。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventCoverDefense:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s及时补位，封堵了进攻线路！", ev.PlayerName),
				fmt.Sprintf("关键补位！%s的预判让进攻无功而返。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s试图补位，但没能阻止进攻。", ev.PlayerName),
			fmt.Sprintf("%s的补位慢了半拍，进攻继续。", ev.PlayerName),
		})
	case config.EventShotBlock:
		// Shot block is narrated within the close_shot event; skip redundant text
		return ""

	// ===== Phase 2: Medium complexity events =====
	case config.EventGoalKick:
		if ev.Result == "success" {
			if ev.Player2Name != "" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出球门球，%s在中场稳稳拿住球。", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s大脚开出球门球，%s接球组织进攻。", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s一记长传直接找到前场的%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s深吸一口气，大脚将球送到%s脚下。", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("皮球高高飞起，%s准确判断落点，将球控制在脚下。", ev.Player2Name),
					fmt.Sprintf("%s开出球门球，皮球越过中场，%s背身拿球做墙。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s开出球门球，球飞向中场。", ev.PlayerName),
				fmt.Sprintf("%s大脚开出球门球，发动进攻。", ev.PlayerName),
				fmt.Sprintf("%s选择稳妥处理，将球开向边路。", ev.PlayerName),
				fmt.Sprintf("%s助跑几步，一脚将球踢向中圈。", ev.PlayerName),
				fmt.Sprintf("%s观察了一下，将球大脚开出。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的球门球被%s intercept！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s开出球门球，但被%s断下。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的传球意图太明显，%s提前卡位将球断走。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s开出球门球，皮球在中场被%s截获。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventPassOut:
		return ng.pick([]string{
			fmt.Sprintf("%s的传球出了边线。", ev.PlayerName),
			fmt.Sprintf("%s传球力度过大，球出了底线。", ev.PlayerName),
			fmt.Sprintf("%s的传球直接出了边线。", ev.PlayerName),
			fmt.Sprintf("%s传球失误，皮球滚出了底线。", ev.PlayerName),
			fmt.Sprintf("%s的传球出了界外。", ev.PlayerName),
		})
	case config.EventThrowIn:
		if ev.Result == "success" {
			if ev.Player2Name != "" {
				return ng.pick([]string{
					fmt.Sprintf("%s手抛球快发，找到%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s掷出界外球，%s稳稳接球。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s手抛球快发，找到队友！", ev.PlayerName),
				fmt.Sprintf("%s掷出界外球， teammates 接球。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的界外球被%s断下。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s掷出界外球，但球权被%s拿到。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventKeeperShortPass:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s选择短传发动，%s稳稳拿住球。", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s参与后场传导，短传给%s。", ev.PlayerName, ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的短传出现失误，被%s断球！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("前锋逼抢%s！%s被迫仓促出球。", ev.PlayerName, ev.PlayerName),
		})
	case config.EventKeeperThrow:
		if ev.Result == "success" {
			if ev.Player2Name != "" {
				return ng.pick([]string{
					fmt.Sprintf("%s快速手抛球发动，%s接球推进！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s手抛球快发，%s迅速带球向前。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s快速手抛球发动，抓住反击机会！", ev.PlayerName),
				fmt.Sprintf("%s手抛球快发，队友迅速推进。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的手抛球被%s拦截。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s快速手抛球，但被%s识破。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventCounterAttack:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("快速反击！%s高速带球推进！", ev.PlayerName),
				fmt.Sprintf("%s抓住机会发动反击，速度飞快！", ev.PlayerName),
				fmt.Sprintf("反击！%s带球长驱直入！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("反击被%s终结！%s断球成功。", ev.OpponentName, ev.OpponentName),
			fmt.Sprintf("%s的反击被%s拦截下来。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventMidBreak:
		return fmt.Sprintf("中场休息。比分 %d-%d", ev.Score.Home, ev.Score.Away)
	case config.EventSecondHalfStart:
		return fmt.Sprintf("下半场开始！比分 %d-%d", ev.Score.Home, ev.Score.Away)

	// ===== Phase 3: Multi-player events =====
	case config.EventOverlap:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("边后卫%s套边插上，和%s做了一次漂亮的二过一！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s沿边路套上，和%s形成配合！", ev.PlayerName, ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s套边被%s识破，球被断下！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的套边配合被%s拦截。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventTrianglePass:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("漂亮的三角传递！%s和队友打出行云流水般的配合！", ev.PlayerName),
				fmt.Sprintf("%s和队友的三角配合撕开了防线！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("三角传递被%s识破，球被断下！", ev.OpponentName),
			fmt.Sprintf("%s的三角配合被%s拦截。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventOneTwo:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("二过一！%s和%s打出撞墙配合！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s把球给%s，%s回做，配合撕开防线！", ev.PlayerName, ev.Player2Name, ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("二过一被%s拦截！", ev.OpponentName),
			fmt.Sprintf("%s的撞墙配合被%s识破。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventCrossRun:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s和%s交叉跑位，防守球员被甩开了！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("漂亮的交叉跑位！%s和%s互换位置，防线出现空当。", ev.PlayerName, ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("交叉跑位被%s识破，球被断下！", ev.OpponentName),
			fmt.Sprintf("%s和%s的换位被%s看穿。", ev.PlayerName, ev.Player2Name, ev.OpponentName),
		})
	case config.EventDoubleTeam:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("包夹！%s和%s合力断下%s的球！", ev.PlayerName, ev.Player2Name, ev.OpponentName),
				fmt.Sprintf("%s和%s双人包夹，%s无处可逃！", ev.PlayerName, ev.Player2Name, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s和%s的包夹被%s突破！", ev.PlayerName, ev.Player2Name, ev.OpponentName),
			fmt.Sprintf("%s从包夹中杀出！", ev.OpponentName),
		})
	case config.EventPressTogether:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s和%s协同逼抢，从%s脚下断球！", ev.PlayerName, ev.Player2Name, ev.OpponentName),
				fmt.Sprintf("双人逼抢！%s和%s合力压迫%s。", ev.PlayerName, ev.Player2Name, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s和%s的逼抢被%s化解。", ev.PlayerName, ev.Player2Name, ev.OpponentName),
			fmt.Sprintf("%s冷静摆脱%s和%s的逼抢。", ev.OpponentName, ev.PlayerName, ev.Player2Name),
		})

	// ===== Phase 3.5: Build-up / possession events =====
	case config.EventHoldBall:
		return ng.pick([]string{
			fmt.Sprintf("%s在原地控球寻找队友。", ev.PlayerName),
			fmt.Sprintf("%s护住球等待支援。", ev.PlayerName),
			fmt.Sprintf("%s观察场上局势，暂时没有好的传球线路。", ev.PlayerName),
			fmt.Sprintf("%s背身拿球，稳住节奏。", ev.PlayerName),
		})
	case config.EventPivotPass:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("中场枢纽%s横向转移，%s接球组织。", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s在中场从容分球给%s，节奏稳了下来。", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("%s作为中场核心，把球横向调度给%s。", ev.PlayerName, ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的横向转移被%s拦截。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s试图横向分球，但被%s识破。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventBuildUp:
		if ev.Result == "success" {
			if ev.Detail != "" && ev.Detail != ev.PlayerName && ev.Detail != ev.Player2Name {
				return ng.pick([]string{
					fmt.Sprintf("%s→%s→%s，后场耐心传导，球终于来到%s脚下。", ev.PlayerName, ev.Detail, ev.Player2Name, ev.Player2Name),
					fmt.Sprintf("后场三人组连续倒脚，%s把球传给%s。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s和%s在后场做着耐心的传导。", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("后场连续传递，球来到%s脚下。", ev.Player2Name),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的后场传导被%s断下！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("后场传球被%s预判拦截，球权易手。", ev.OpponentName),
		})

	// ===== Phase 4: Injury & rare events =====
	case config.EventMinorInjury:
		return ng.pick([]string{
			fmt.Sprintf("%s在对抗中受了轻伤，但仍坚持比赛。", ev.PlayerName),
			fmt.Sprintf("%s被%s犯规后有些不适。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventMajorInjury:
		return ng.pick([]string{
			fmt.Sprintf("%s严重受伤！队医进场！", ev.PlayerName),
			fmt.Sprintf("%s在一次凶狠的拼抢中受伤倒地！", ev.PlayerName),
		})
	case config.EventDropBall:
		if ev.Result == "success" {
			return fmt.Sprintf("坠球恢复，%s抢先拿到球权。", ev.PlayerName)
		}
		return fmt.Sprintf("坠球恢复，%s拿到球权。", ev.OpponentName)

	// ===== Narrative stage events =====
	case config.EventPenaltySetup:
		return ng.pick([]string{
			fmt.Sprintf("%s抱着球走向点球点，全场屏住了呼吸。", ev.PlayerName),
			fmt.Sprintf("裁判指向点球点！%s准备主罚！", ev.PlayerName),
			fmt.Sprintf("%s把球放在点球点上，后退几步准备助跑。", ev.PlayerName),
			fmt.Sprintf("点球！%s深吸一口气，走向罚球点。", ev.PlayerName),
		})
	case config.EventPenaltyFocus:
		return ng.pick([]string{
			fmt.Sprintf("%s和%s对视着，空气中弥漫着紧张的气氛。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s在门线上左右移动，试图干扰%s。", ev.OpponentName, ev.PlayerName),
			fmt.Sprintf("%s紧闭双眼，然后又睁开，目光锁定球门。", ev.PlayerName),
			fmt.Sprintf("%s做了一个深呼吸，助跑准备——", ev.PlayerName),
			fmt.Sprintf("看台上有人在吹口哨，%s不为所动。", ev.PlayerName),
			fmt.Sprintf("%s弯下腰系了系鞋带，站起身来，开始助跑！", ev.PlayerName),
		})
	case config.EventFreeKickSetup:
		return ng.pick([]string{
			fmt.Sprintf("%s把皮球摆好位置，人墙正在组织。", ev.PlayerName),
			fmt.Sprintf("裁判在丈量人墙距离，%s等待着。", ev.PlayerName),
			fmt.Sprintf("%s站在球前，目光扫视着禁区内的人群。", ev.PlayerName),
			fmt.Sprintf("人墙排好了，%s后退几步，准备助跑。", ev.PlayerName),
			fmt.Sprintf("%s弯腰调整球的位置，人墙里的球员紧张地护住要害。", ev.PlayerName),
			fmt.Sprintf("%s退后几步，深呼吸，目光锁定球门。", ev.PlayerName),
			fmt.Sprintf("裁判用喷雾画线，人墙后退，%s准备起脚。", ev.PlayerName),
			fmt.Sprintf("%s在球前踱步，寻找最佳射门角度。", ev.PlayerName),
			fmt.Sprintf("人墙里的%s双手护住面部，%s开始助跑准备。", ev.OpponentName, ev.PlayerName),
			fmt.Sprintf("%s和队友低声交流，似乎在谋划一次战术配合。", ev.PlayerName),
		})
	case config.EventFreeKickFocus:
		return ng.pick([]string{
			fmt.Sprintf("%s深吸一口气，开始助跑！", ev.PlayerName),
			fmt.Sprintf("%s目光坚定，助跑两步——", ev.PlayerName),
			fmt.Sprintf("%s调整好步伐，准备起脚！", ev.PlayerName),
			fmt.Sprintf("全场屏息凝神，%s助跑射门！", ev.PlayerName),
			fmt.Sprintf("%s起脚了！皮球飞向球门！", ev.PlayerName),
			fmt.Sprintf("%s助跑后起脚，这球势大力沉！", ev.PlayerName),
			fmt.Sprintf("%s的射门像出膛炮弹一样飞向球门！", ev.PlayerName),
			fmt.Sprintf("%s一脚兜射，皮球带着强烈旋转飞向死角！", ev.PlayerName),
		})
	case config.EventCornerSetup:
		return ng.pick([]string{
			fmt.Sprintf("%s把角球旗边的皮球摆好，禁区内双方球员正在卡位。", ev.PlayerName),
			fmt.Sprintf("角球区，%s举起一只手示意队友跑位。", ev.PlayerName),
			fmt.Sprintf("禁区内一片推搡，%s准备开出角球。", ev.PlayerName),
			fmt.Sprintf("%s退后两步，目光扫向禁区内的队友。", ev.PlayerName),
			fmt.Sprintf("%s在角球区踩了踩草皮，后卫们互相拉扯着球衣。", ev.PlayerName),
			fmt.Sprintf("%s举起双手示意战术，前锋们开始交叉跑位。", ev.PlayerName),
			fmt.Sprintf("禁区内人挤人，%s寻找着最合理的传球路线。", ev.PlayerName),
			fmt.Sprintf("%s把球摆在角球区，主队球迷发出巨大的呐喊声。", ev.PlayerName),
			fmt.Sprintf("%s退后几步准备助跑，禁区内双方球员互相推搡。", ev.PlayerName),
			fmt.Sprintf("%s低头调整球的位置，后卫们高高跃起准备争顶。", ev.PlayerName),
		})
	case config.EventThrowInSetup:
		return ng.pick([]string{
			fmt.Sprintf("%s走到边线外，双手托起皮球。", ev.PlayerName),
			fmt.Sprintf("%s把球在裤子上擦了擦，寻找接应队友。", ev.PlayerName),
			fmt.Sprintf("边线球，%s双手举过头顶准备掷出。", ev.PlayerName),
		})
	case config.EventGoalKickSetup:
		return ng.pick([]string{
			fmt.Sprintf("%s在小禁区内摆好皮球，队友们拉开空间。", ev.PlayerName),
			fmt.Sprintf("%s拍了拍球，示意队友准备接应。", ev.PlayerName),
			fmt.Sprintf("球门球，%s准备大脚开出。", ev.PlayerName),
			fmt.Sprintf("%s弯腰调整了一下球的位置，后防线在招手要球。", ev.PlayerName),
			fmt.Sprintf("%s戴上手套，左右观察队友跑位。", ev.PlayerName),
			fmt.Sprintf("%s将球摆定，对方前锋识趣地退到禁区外。", ev.PlayerName),
			fmt.Sprintf("%s在小禁区里踩了踩草皮，抬头寻找接应点。", ev.PlayerName),
			fmt.Sprintf("裁判示意球门球，%s抱起球走到小禁区角上。", ev.PlayerName),
			fmt.Sprintf("%s整理了一下手套，队友们正在回撤接应。", ev.PlayerName),
			fmt.Sprintf("%s把球按在草皮上，风有点大，他退后两步准备助跑。", ev.PlayerName),
		})
	}
	return ""
}

func (ng *NarrativeGenerator) pick(options []string) string {
	if len(options) == 0 {
		return ""
	}
	return options[ng.r.IntN(len(options))]
}

func FormatMinute(m float64) string {
	min := int(m)
	sec := int((m - float64(min)) * 60)
	return fmt.Sprintf("%d'%02d\"", min, sec)
}
