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
		return ng.pick([]string{
			fmt.Sprintf("球权转换！%s断球成功！", ev.Team),
			fmt.Sprintf("%s夺回球权，迅速转入进攻！", ev.Team),
			fmt.Sprintf("%s从对方脚下抢到球，展开反击！", ev.PlayerName),
		})
	case config.EventBackPass:
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s出人意料地送出一记向后的直塞！", ev.PlayerName),
					fmt.Sprintf("%s的传球角度刁钻，让防守球员措手不及。", ev.PlayerName),
				})
			}
			return ng.pick([]string{
				fmt.Sprintf("%s试图送出刁钻的向后直塞，但被%s识破拦截。", ev.PlayerName, ev.OpponentName),
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
		})
	case config.EventMidPass:
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s在中场送出一脚手术刀般的传球！", ev.PlayerName),
					fmt.Sprintf("%s的直塞穿透了中场防线！", ev.PlayerName),
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
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s送出一脚穿透性短传！", ev.PlayerName),
					fmt.Sprintf("%s在狭小空间里完成了一脚精妙的短传配合！", ev.PlayerName),
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
		})
	case config.EventLongPass:
		if ev.Detail == "aggressive" {
			if ev.Result == "success" {
				return ng.pick([]string{
					fmt.Sprintf("%s一脚大范围转移，试图直接撕开防线！", ev.PlayerName),
					fmt.Sprintf("%s的精准长传找到了前场空当！", ev.PlayerName),
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
	case config.EventThroughBall:
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
				return ng.pick([]string{
					fmt.Sprintf("%s抢点成功，头球把球摆渡给%s！", ev.PlayerName, ev.Player2Name),
					fmt.Sprintf("%s高高跃起头球争顶，把球顶给插上的%s！", ev.PlayerName, ev.Player2Name),
				})
			}
			return fmt.Sprintf("%s头球争顶成功，把球摆渡给%s。", ev.PlayerName, ev.Player2Name)
		}
		return fmt.Sprintf("%s争顶失败，%s控制住了球权。", ev.PlayerName, ev.OpponentName)
	case config.EventCloseShot:
		if ev.Result == "goal" {
			return ng.pick([]string{
				fmt.Sprintf("%s禁区射门——球进了！！！", ev.PlayerName),
				fmt.Sprintf("%s冷静推射破门！比分改写！", ev.PlayerName),
				fmt.Sprintf("%s势大力沉的射门！球应声入网！", ev.PlayerName),
			})
		}
		if ev.Result == "saved" {
			return fmt.Sprintf("%s禁区射门！%s做出精彩扑救！", ev.PlayerName, ev.OpponentName)
		}
		if ev.Result == "blocked" {
			return fmt.Sprintf("%s射门被%s封堵了出去。", ev.PlayerName, ev.OpponentName)
		}
		if ev.Result == "woodwork" {
			return ng.pick([]string{
				fmt.Sprintf("%s射门击中门框弹出！差之毫厘！", ev.PlayerName),
				fmt.Sprintf("%s一脚劲射砸在立柱上！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s射门偏出了立柱。", ev.PlayerName),
			fmt.Sprintf("%s一脚打飞，皮球直奔角旗杆。", ev.PlayerName),
			fmt.Sprintf("%s的射门高出了横梁。", ev.PlayerName),
		})
	case config.EventLongShot:
		if ev.Result == "goal" {
			return ng.pick([]string{
				fmt.Sprintf("%s远射——世界波！！！球进了！！！", ev.PlayerName),
				fmt.Sprintf("%s禁区外一脚重炮，皮球直挂死角！", ev.PlayerName),
			})
		}
		if ev.Result == "saved" {
			return fmt.Sprintf("%s远射！%s飞身将球扑出！", ev.PlayerName, ev.OpponentName)
		}
		if ev.Result == "woodwork" {
			return ng.pick([]string{
				fmt.Sprintf("%s远射击中横梁弹出！太可惜了！", ev.PlayerName),
				fmt.Sprintf("%s一脚重炮砸在立柱上！", ev.PlayerName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s远射高出横梁。", ev.PlayerName),
			fmt.Sprintf("%s这脚远射放了高射炮。", ev.PlayerName),
			fmt.Sprintf("%s的远射偏出了球门。", ev.PlayerName),
		})
	case config.EventTackle:
		if ev.Result == "success" {
			return ng.pick([]string{
				fmt.Sprintf("%s干净利落地铲断了%s的带球！", ev.PlayerName, ev.OpponentName),
				fmt.Sprintf("%s上抢成功，从%s脚下断球！", ev.PlayerName, ev.OpponentName),
			})
		}
		return ng.pick([]string{
			fmt.Sprintf("%s铲球失败，%s继续推进。", ev.PlayerName, ev.OpponentName),
		})
	case config.EventIntercept:
		return fmt.Sprintf("%s预判准确，拦截了对方的传球。", ev.PlayerName)
	case config.EventClearance:
		return fmt.Sprintf("%s大脚解围，化解了险情。", ev.PlayerName)
	case config.EventGoal:
		return ng.pick([]string{
			fmt.Sprintf("🎉 进球！%s打破了僵局！", ev.PlayerName),
			fmt.Sprintf("🎉 %s建功！球队取得领先！", ev.PlayerName),
			fmt.Sprintf("🎉 球进了！%s的进球让全场沸腾！", ev.PlayerName),
		})
	case config.EventOwnGoal:
		return ng.pick([]string{
			fmt.Sprintf("😱 乌龙球！%s不慎将球碰入自家大门！", ev.PlayerName),
			fmt.Sprintf("😱 太不幸了！%s自摆乌龙！", ev.PlayerName),
		})
	case config.EventKeeperSave:
		return ng.pick([]string{
			fmt.Sprintf("%s做出关键扑救！", ev.PlayerName),
			fmt.Sprintf("%s神勇发挥，将球拒之门外！", ev.PlayerName),
		})
	case config.EventKeeperClaim:
		return ng.pick([]string{
			fmt.Sprintf("%s出击将球稳稳摘下。", ev.PlayerName),
			fmt.Sprintf("%s控制住球权。", ev.PlayerName),
		})
	case config.EventCorner:
		return fmt.Sprintf("球出了底线，%s获得角球机会。", ev.Team)
	case config.EventFoul:
		if ev.Result == "yellow" {
			return fmt.Sprintf("%s对%s犯规，裁判出示黄牌！", ev.PlayerName, ev.OpponentName)
		}
		if ev.Result == "red" {
			return fmt.Sprintf("%s对%s严重犯规，红牌！", ev.PlayerName, ev.OpponentName)
		}
		return fmt.Sprintf("%s对%s犯规了！", ev.PlayerName, ev.OpponentName)
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
		return fmt.Sprintf("裁判向%s出示黄牌！", ev.PlayerName)
	case config.EventRedCard:
		return fmt.Sprintf("红牌！%s被直接罚下！", ev.PlayerName)
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
