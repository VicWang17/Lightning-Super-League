package engine

import (
	"fmt"
	"math/rand/v2"

	"match-engine/internal/config"
	"match-engine/internal/domain"
)

// NarrativeGenerator produces commentary text
type NarrativeGenerator struct {
	r           *rand.Rand
	lastEvent   string // tracks previous event type for chain-aware narratives
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

	// Add momentum flavor
	if momentum > 0.15 {
		base += ng.pick([]string{"", " " + ev.Team + "势头正盛！", " " + ev.Team + "完全掌控了比赛节奏！"})
	} else if momentum < -0.15 {
		base += ng.pick([]string{"", " " + ev.Team + "似乎有些力不从心。", " " + ev.Team + "需要振作起来。"})
	}
	// Add control flavor for key zones
	if ctrl > 0.6 && zone[0] == 1 {
		base += ng.pick([]string{"", " " + ev.Team + "几乎控制了中场，从容组织进攻。"})
	}
	if ctrl > 0.6 && zone[0] == 0 {
		base += ng.pick([]string{"", " " + ev.Team + "在前场形成了围攻之势！"})
	}
	if ctrl < -0.3 && zone[0] == 2 && ev.Result == "success" {
		base += ng.pick([]string{"", " 防线被撕扯开了，有机会！", " 后防空虚，这是机会！"})
	}
	return base
}

func (ng *NarrativeGenerator) generateBase(ev domain.MatchEvent) string {
	switch ev.Type {
	case config.EventKickoff:
		if ev.Minute < 1.0 {
			return fmt.Sprintf("比赛开始！%s 对阵 %s", ev.Team, ev.OpponentName)
		}
		return fmt.Sprintf("中圈开球！%s重新组织进攻。", ev.Team)
	case config.EventTurnover:
		if ev.PlayerName != "" {
			return ng.pick([]string{
				fmt.Sprintf("球权来到%s队这边，%s拿球组织。", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s队展开反击，%s带球推进！", ev.Team, ev.PlayerName),
				fmt.Sprintf("%s夺回球权，%s迅速转入进攻！", ev.Team, ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("球权来到%s队这边。", ev.Team),
			fmt.Sprintf("%s队展开反击。", ev.Team),
			fmt.Sprintf("%s夺回球权，迅速转入进攻！", ev.Team),
		})
	case config.EventBackPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s在后场稳稳拿住球。", ev.PlayerName),
				fmt.Sprintf("%s在后场控球观察局势。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s出人意料地送出一记向后的直传给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的传球角度刁钻，%s在后场稳稳拿住球。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图送出刁钻的向后直传，但被%s识破拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险回传被%s断下！", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s的回传出现失误，被%s断球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在后场的传球被%s拦截。", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s在后场控球，稳稳地把球交给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s面对逼抢，冷静分球给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s在后场做着传导。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s在后场耐心倒脚，将球传给%s。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventMidPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s在中场拿球观察。", ev.PlayerName),
				fmt.Sprintf("%s在中场控球寻找机会。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s在中场送出一脚手术刀般的传球，%s接球转身！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的直塞穿透了中场防线，%s高速插上！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图直塞穿透防线，被%s精准预判拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险传球被%s断下！", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s在中场的传球被%s断下。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的分球出现失误，球权易手。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s在中场控球，不断观察寻找传球线路。", ev.PlayerName),
			fmt.Sprintf("中场核心%s把球分给了%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s在中场进行着耐心的传递。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventShortPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s在原地控球寻找队友。", ev.PlayerName),
				fmt.Sprintf("%s护住球等待支援。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s送出一脚穿透性短传给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s在狭小空间里和%s完成了一脚精妙的短传配合！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图送出穿透性短传，被%s贴身拦截。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险短传被%s识破，球权丢失。", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s的短传被%s抢断。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传球出现失误，球落到对方脚下。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s选择了一个安全的短传，交给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("面对逼抢，%s冷静地把球回给%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s和%s做了一次简单的倒脚配合。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s一脚短传找到%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s与%s打出撞墙配合。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventLongPass:
		if ev.PlayerName == ev.Player2Name {
			return ng.pick([]string{
				fmt.Sprintf("%s观察后选择长传转移。", ev.PlayerName),
				fmt.Sprintf("%s大脚调度寻找空当。", ev.PlayerName),
			})
		}
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s一脚大范围转移，%s在边路接球！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s的精准长传找到了%s！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的大范围转移被%s头球解围。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的冒险长传飞出边线，球权易手。", ev.PlayerName),
			})
		}
		if ev.Result == "fail" {
			return ng.pick([]string{
				fmt.Sprintf("%s的长传被%s预判解围。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的大脚长传落点不佳，被对方拿到。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s一记长传，试图把球直接送到前场找到%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s大脚长传调度，寻找前场的%s。", ev.PlayerName, ev.Player2Name),
			fmt.Sprintf("%s试图用长传找到%s，撕开防线。", ev.PlayerName, ev.Player2Name),
		})
	case config.EventWingBreak:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s在边路带球突破，晃过了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("边路1v1！%s用速度强吃了%s！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s一个漂亮的假动作，完全晃开了%s！", ev.PlayerName, ev.OpponentName),
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
			})
		}
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s送出一脚直塞球，试图找到前方的%s！", ev.PlayerName, ev.Player2Name),
				fmt.Sprintf("手术刀般的直塞！%s的传球撕开了防线，%s单刀了！", ev.PlayerName, ev.Player2Name),
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
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s传中，被%s头球解围。", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s的传中被%s拦截。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventHeader:
		if ev.Result == "goal" {
			return ng.pick([]string{
				fmt.Sprintf("%s力压后卫头球攻门——球进了！！！", ev.PlayerName),
				fmt.Sprintf("头球！%s甩头攻门，球应声入网！", ev.PlayerName),
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
		})
	case config.EventCloseShot:
		if ev.Result == "goal" {
			return ng.pick([]string{
				fmt.Sprintf("球进了！！！%s的射门洞穿网窝！", ev.PlayerName),
				fmt.Sprintf("进了！%s冷静推射破门！", ev.PlayerName),
				fmt.Sprintf("应声入网！%s的射门让门将毫无反应！", ev.PlayerName),
			})
		}
		if ev.Result == "saved" {
			return ng.pick([]string{
				fmt.Sprintf("被%s扑出！太精彩了！", ev.OpponentName),
				fmt.Sprintf("%s神勇扑救！皮球被挡了出去！", ev.OpponentName),
			})
		}
		if ev.Result == "blocked" {
			return ng.pick([]string{
				fmt.Sprintf("被%s封堵了出去！", ev.OpponentName),
				fmt.Sprintf("%s奋不顾身地用身体挡住了射门！", ev.OpponentName),
			})
		}
		if ev.Result == "woodwork" {
			return ng.pick([]string{
				fmt.Sprintf("击中门框弹出！差之毫厘！"),
				fmt.Sprintf("哐当一声！皮球砸在立柱上弹了出来！"),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("偏出了立柱..."),
			fmt.Sprintf("高出了横梁！"),
		})
	case config.EventLongShot:
		if ev.Result == "goal" {
			return ng.pick([]string{
				fmt.Sprintf("世界波！！！皮球直挂死角！%s！", ev.PlayerName),
				fmt.Sprintf("进了！！！%s这脚远射简直不可思议！", ev.PlayerName),
			})
		}
		if ev.Result == "saved" {
			return ng.pick([]string{
				fmt.Sprintf("%s飞身将球托出横梁！", ev.OpponentName),
				fmt.Sprintf("%s一个侧扑，把球挡了出去！", ev.OpponentName),
			})
		}
		if ev.Result == "woodwork" {
			return ng.pick([]string{
				fmt.Sprintf("击中横梁弹出！太可惜了！"),
				fmt.Sprintf("哐！皮球狠狠砸在立柱上！"),
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
		})
	case config.EventClearance:
		return fmt.Sprintf("%s大脚解围，化解了险情。", ev.PlayerName)
	case config.EventGoal:
		return ng.pick([]string{
			fmt.Sprintf("进球！%s打破了僵局！", ev.PlayerName),
			fmt.Sprintf("%s建功！球队取得领先！", ev.PlayerName),
			fmt.Sprintf("球进了！%s的进球让全场沸腾！", ev.PlayerName),
		})
	case config.EventGoalCelebration:
		return ng.pick([]string{
			fmt.Sprintf("%s冲向角旗杆庆祝！队友们纷纷围了上来！", ev.PlayerName),
			fmt.Sprintf("%s张开双臂接受球迷的欢呼！", ev.PlayerName),
			fmt.Sprintf("%s滑跪庆祝！全场球迷疯狂呐喊！", ev.PlayerName),
			fmt.Sprintf("%s和队友们拥抱在一起！这是属于他们的时刻！", ev.PlayerName),
			fmt.Sprintf("%s指天庆祝！这个进球意义重大！", ev.PlayerName),
			fmt.Sprintf("看台上彩带飞舞！%s的庆祝激情四溢！", ev.PlayerName),
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
		return fmt.Sprintf("球出了底线，%s获得角球机会。", ev.Team)
	case config.EventFoul:
		isBox := ev.Zone == "[0,1]"
		if ev.Result == "no_call" {
			if isBox {
				return ng.pick([]string{
					fmt.Sprintf("%s禁区内倒地，裁判认为没有犯规。", ev.OpponentName),
					fmt.Sprintf("%s在禁区内疑似被%s放倒，裁判示意比赛继续。", ev.OpponentName, ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s摔倒了，但裁判没有吹！", ev.OpponentName),
				fmt.Sprintf("%s疑似被%s侵犯，裁判示意比赛继续。", ev.OpponentName, ev.PlayerName),
			})
		}
		if ev.Result == "yellow" {
			if isBox {
				return ng.pick([]string{
					fmt.Sprintf("禁区内犯规！%s对%s凶狠犯规，吃到黄牌！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s在禁区内拉倒%s，裁判出示黄牌并指向点球点！", ev.PlayerName, ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s对%s凶狠犯规！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s拉倒了%s，这是一个明显的犯规！", ev.PlayerName, ev.OpponentName),
			})
		}
		if ev.Result == "red" {
			if isBox {
				return ng.pick([]string{
					fmt.Sprintf("%s在禁区内严重犯规！红牌罚下并判罚点球！", ev.PlayerName),
					fmt.Sprintf("禁区内恶劣犯规！%s放倒%s，直接红牌！", ev.PlayerName, ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s对%s严重犯规！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s凶狠地放倒了%s！", ev.PlayerName, ev.OpponentName),
			})
		}
		// No card, but foul called
		if isBox {
			return ng.pick([]string{
				fmt.Sprintf("禁区内犯规！%s对%s犯规，裁判指向点球点！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s在禁区内放倒%s，点球！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s对%s犯规了！裁判判罚任意球！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s拉倒了%s，裁判鸣哨，任意球！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s对%s凶狠犯规！裁判指向犯规地点，任意球！", ev.PlayerName, ev.OpponentName),
		})
	case config.EventFreeKick:
		switch ev.Detail {
		case "penalty":
			if ev.Result == "goal" {
				return ng.pick([]string{
					fmt.Sprintf("点球破门！%s冷静推射，门将判断错了方向！", ev.PlayerName),
					fmt.Sprintf("%s稳稳命中点球！比分改写！", ev.PlayerName),
				})
			}
			if ev.Result == "saved" {
				return ng.pick([]string{
					fmt.Sprintf("点球被扑出！%s的射门被门将%s神勇化解！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的点球被%s扑出！太可惜了！", ev.PlayerName, ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("点球罚丢了！%s的射门偏出了球门！", ev.PlayerName),
				fmt.Sprintf("%s的点球打飞了！", ev.PlayerName),
			})
		case "cross":
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出精准任意球传中，球飞向禁区！", ev.PlayerName),
					fmt.Sprintf("%s的任意球传中划出一道美妙弧线！", ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球传中被%s解围。", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s的传中任意球被%s顶出危险区域。", ev.PlayerName, ev.OpponentName),
			})
		case "shot":
			if ev.Result == "goal" {
				return ng.pick([]string{
					fmt.Sprintf("世界波！%s的直接任意球直挂死角！", ev.PlayerName),
					fmt.Sprintf("任意球大师！%s一脚精准制导破门得分！", ev.PlayerName),
				})
			}
			if ev.Result == "saved" {
				return ng.pick([]string{
					fmt.Sprintf("%s的任意球角度刁钻，可惜被%s扑出！", ev.PlayerName, ev.OpponentName),
					fmt.Sprintf("%s的任意球绕过人墙，被%s奋力挡出！", ev.PlayerName, ev.OpponentName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球打在了人墙上！", ev.PlayerName),
				fmt.Sprintf("%s的任意球力量过大，偏出了球门！", ev.PlayerName),
			})
		case "long_pass":
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出任意球长传，%s接球后展开进攻！", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球长传被%s断下！", ev.PlayerName, ev.OpponentName),
			})
		default: // short pass
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s开出任意球短传，%s接球组织。", ev.PlayerName, ev.Player2Name),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s的任意球短传被%s断下！", ev.PlayerName, ev.OpponentName),
			})
		}
	case config.EventYellowCard:
		return ng.pick([]string{
			fmt.Sprintf("裁判向%s出示黄牌！", ev.PlayerName),
			fmt.Sprintf("主裁判掏出了黄牌，%s被警告。", ev.PlayerName),
		})
	case config.EventRedCard:
		return ng.pick([]string{
			fmt.Sprintf("红牌！%s被直接罚下！", ev.PlayerName),
			fmt.Sprintf("主裁判出示红牌，%s被罚出场！", ev.PlayerName),
		})
	case config.EventOffside:
		return ng.pick([]string{
			fmt.Sprintf("越位！%s的跑位早了半步。", ev.PlayerName),
			fmt.Sprintf("边旗举起！%s越位了。", ev.PlayerName),
		})
	case config.EventSubstitution:
		return fmt.Sprintf("换人调整！%s下场，%s替补登场。", ev.Player2Name, ev.PlayerName)
	case config.EventHalftime:
		return fmt.Sprintf("上半场结束！比分 %d-%d", ev.Score.Home, ev.Score.Away)
	case config.EventFulltime:
		return fmt.Sprintf("全场比赛结束！最终比分 %d-%d", ev.Score.Home, ev.Score.Away)

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
			return ng.pick([]string{
				fmt.Sprintf("单刀！%s冷静推射破门！", ev.PlayerName),
				fmt.Sprintf("%s晃过门将，轻松推射入网！", ev.PlayerName),
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
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s开出球门球，球飞向中场。", ev.PlayerName),
				fmt.Sprintf("%s大脚开出球门球，发动进攻。", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s的球门球被%s intercept！", ev.PlayerName, ev.OpponentName),
			fmt.Sprintf("%s开出球门球，但被%s断下。", ev.PlayerName, ev.OpponentName),
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
		})
	case config.EventCornerSetup:
		return ng.pick([]string{
			fmt.Sprintf("%s把角球旗边的皮球摆好，禁区内双方球员正在卡位。", ev.PlayerName),
			fmt.Sprintf("角球区，%s举起一只手示意队友跑位。", ev.PlayerName),
			fmt.Sprintf("禁区内一片推搡，%s准备开出角球。", ev.PlayerName),
			fmt.Sprintf("%s退后两步，目光扫向禁区内的队友。", ev.PlayerName),
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
