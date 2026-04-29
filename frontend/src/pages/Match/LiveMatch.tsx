import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { 
  ChevronRight,
  Zap
} from '../../components/ui/pixel-icons'

// Mock 比赛事件
const mockEvents = [
  { time: 0, type: 'kickoff', text: '比赛开始！雷霆龙骑 vs 南海蛟龙' },
  { time: 3, type: 'normal', text: '刘洋在中场拿球，尝试组织进攻' },
  { time: 8, type: 'normal', text: '南海蛟龙获得角球机会，被王强双拳击出' },
  { time: 15, type: 'goal', text: '🎉 进球！赵雷接到陈浩传中，头球破门！' },
  { time: 16, type: 'normal', text: '比分变为 1:0，雷霆龙骑取得领先' },
  { time: 23, type: 'normal', text: '南海蛟龙加强逼抢，试图扳平比分' },
  { time: 31, type: 'yellow', text: '黄牌！张伟战术犯规，阻止对方反击' },
  { time: 38, type: 'normal', text: '上半场比赛进入最后阶段' },
  { time: 42, type: 'goal', text: '🎉 进球！陈浩禁区外远射，世界波！' },
  { time: 45, type: 'half', text: '上半场结束，雷霆龙骑 2:0 南海蛟龙' },
  { time: 46, type: 'kickoff', text: '下半场开始' },
  { time: 52, type: 'normal', text: '南海蛟龙换人，加强进攻' },
  { time: 61, type: 'goal', text: '⚽ 南海蛟龙扳回一球，比分 2:1' },
  { time: 68, type: 'normal', text: '雷霆龙骑收缩防线，稳守反击' },
  { time: 75, type: 'normal', text: '比赛进入最后15分钟' },
  { time: 82, type: 'yellow', text: '黄牌！南海蛟龙球员铲球犯规' },
  { time: 88, type: 'normal', text: '伤停补时3分钟' },
  { time: 90, type: 'full', text: '全场比赛结束！雷霆龙骑 2:1 南海蛟龙' },
]

const mockStats = {
  possession: [52, 48],
  shots: [12, 9],
  shotsOn: [6, 4],
  corners: [5, 4],
  fouls: [8, 10],
}

export default function LiveMatch() {
  const [currentTime, setCurrentTime] = useState(0)
  const [events, setEvents] = useState<typeof mockEvents>([])
  const [score, setScore] = useState({ home: 0, away: 0 })
  const [isLive, setIsLive] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isLive) return
    
    const interval = setInterval(() => {
      setCurrentTime(prev => {
        const next = prev + 1
        const newEvents = mockEvents.filter(e => e.time === next)
        
        newEvents.forEach(ev => {
          if (ev.type === 'goal') {
            if (ev.text.includes('雷霆龙骑') || ev.text.includes('陈浩') || ev.text.includes('赵雷')) {
              setScore(s => ({ ...s, home: s.home + 1 }))
            } else {
              setScore(s => ({ ...s, away: s.away + 1 }))
            }
          }
        })
        
        setEvents(prevEvents => [...prevEvents, ...newEvents])
        
        if (next >= 90) {
          setIsLive(false)
        }
        
        return next
      })
    }, 500) // 加速模拟：0.5秒 = 1分钟

    return () => clearInterval(interval)
  }, [isLive])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events])

  return (
    <div className="space-y-6 max-w-[1200px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">比赛直播</h1>
          {isLive && (
            <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs border border-red-500/30 animate-pixel-blink">
              ● LIVE
            </span>
          )}
        </div>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white transition-colors">
          返回赛程 →
        </Link>
      </div>

      {/* 比分牌 */}
      <div className="card bg-[#0D4A4D]/20 border-[#0D7377]/30">
        <div className="flex items-center justify-center gap-6 py-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center mx-auto mb-2 shadow-pixel-green">
              <span className="text-2xl">🐉</span>
            </div>
            <p className="text-sm font-bold">雷霆龙骑</p>
          </div>
          
          <div className="text-center px-8">
            <div className="pixel-scoreboard">
              <span className="score-home">{score.home}</span>
              <span className="score-divider">:</span>
              <span className="score-away">{score.away}</span>
            </div>
            <p className="text-sm text-[#0D7377] font-bold mt-2">
              {currentTime < 45 ? `上半场 ${currentTime}'` : 
               currentTime === 45 ? '中场休息' :
               currentTime < 90 ? `下半场 ${currentTime}'` : '全场结束'}
            </p>
          </div>
          
          <div className="text-center">
            <div className="w-16 h-16 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
              <span className="text-2xl">🌊</span>
            </div>
            <p className="text-sm font-bold">南海蛟龙</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 文字直播 */}
        <div className="lg:col-span-2 card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#0D7377]" />
            文字直播
          </h3>
          <div 
            ref={scrollRef}
            className="space-y-2 max-h-[500px] overflow-y-auto pr-2"
          >
            {events.length === 0 && (
              <p className="text-sm text-[#4B4B6A] text-center py-8">比赛即将开始...</p>
            )}
            {events.map((ev, i) => (
              <div 
                key={i} 
                className={clsx(
                  'flex items-start gap-3 p-2 border-l-2',
                  ev.type === 'goal' ? 'bg-yellow-500/10 border-yellow-500' :
                  ev.type === 'yellow' ? 'bg-yellow-500/5 border-yellow-500' :
                  ev.type === 'red' ? 'bg-red-500/10 border-red-500' :
                  ev.type === 'half' || ev.type === 'full' ? 'bg-[#0D7377]/10 border-[#0D7377]' :
                  'border-[#2D2D44]'
                )}
              >
                <span className="text-xs text-[#4B4B6A] font-mono w-8">{ev.time}'</span>
                <span className={clsx(
                  'text-sm',
                  ev.type === 'goal' ? 'text-yellow-400 font-bold' :
                  ev.type === 'half' || ev.type === 'full' ? 'text-[#0D7377] font-bold' :
                  'text-[#E2E2F0]'
                )}>
                  {ev.text}
                </span>
              </div>
            ))}
            {isLive && <div className="animate-pulse text-xs text-[#4B4B6A]">实时更新中...</div>}
          </div>
        </div>

        {/* 数据统计 */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">数据统计</h3>
            <div className="space-y-4">
              <StatRow label="控球率" home={mockStats.possession[0]} away={mockStats.possession[1]} unit="%" />
              <StatRow label="射门" home={mockStats.shots[0]} away={mockStats.shots[1]} />
              <StatRow label="射正" home={mockStats.shotsOn[0]} away={mockStats.shotsOn[1]} />
              <StatRow label="角球" home={mockStats.corners[0]} away={mockStats.corners[1]} />
              <StatRow label="犯规" home={mockStats.fouls[0]} away={mockStats.fouls[1]} />
            </div>
          </div>

          {!isLive && (
            <Link 
              to="/match/post"
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              <ChevronRight className="w-4 h-4" />
              查看赛后统计
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

function StatRow({ label, home, away, unit = '' }: { label: string; home: number; away: number; unit?: string }) {
  const total = home + away
  const homePct = total > 0 ? (home / total) * 100 : 50
  
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-bold text-white">{home}{unit}</span>
        <span className="text-xs text-[#8B8BA7]">{label}</span>
        <span className="text-sm font-bold text-white">{away}{unit}</span>
      </div>
      <div className="flex h-2">
        <div className="bg-[#0D7377]" style={{ width: `${homePct}%` }} />
        <div className="bg-[#4B4B6A]" style={{ width: `${100 - homePct}%` }} />
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
